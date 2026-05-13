from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

from backend.services.ml_calibration_service import build_calibration_report
from backend.services.drift_monitoring_service import build_drift_report

MODE = "PAPER_TRADING_SIMULATION_ONLY"
MODELS = ["random_forest", "lightgbm", "xgboost"]


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_frame(path: Path) -> pd.DataFrame:
    try:
        if path.exists():
            return safe_read_dataframe(path)
    except Exception:
        pass
    return pd.DataFrame()


def _safe(v: Any, default: float = 0.0) -> float:
    try:
        x = float(v)
        if pd.isna(x):
            return default
        return x
    except Exception:
        return default


def _status(score: float) -> str:
    if score >= 0.75: return "healthy"
    if score >= 0.55: return "warning"
    if score >= 0.35: return "degraded"
    if score >= 0.2: return "unstable"
    return "blocked"


def build_model_health_report(root: Path | None = None) -> dict[str, Any]:
    root = Path(root) if root else project_root()
    calibration = build_calibration_report(root)
    drift = build_drift_report(root)
    settled = _read_frame(root / "data/ml/settled_predictions.parquet")
    real_settled = settled[(settled.get("settlement_source_type", pd.Series(dtype=str)).astype(str) == "real")] if not settled.empty else pd.DataFrame()
    preds = _read_frame(root / "data/ml/predictions/future_predictions.parquet")
    reports: dict[str, Any] = {}
    for model in MODELS:
        cal = calibration.get("models", {}).get(model, {})
        sub_all = settled[settled.get("model_name", pd.Series(dtype=str)).astype(str) == model] if not settled.empty else pd.DataFrame()
        sub = real_settled[real_settled.get("model_name", pd.Series(dtype=str)).astype(str) == model] if not real_settled.empty else pd.DataFrame()
        source_counts = sub_all.get("settlement_source_type", pd.Series(dtype=str)).value_counts().to_dict() if not sub_all.empty else {}
        recent_accuracy = None
        recent_roi = None
        if not sub.empty:
            recent_accuracy = round(float(pd.to_numeric(sub.get("prediction_correct"), errors="coerce").fillna(0).tail(100).mean()), 6)
            if "realized_roi" in sub.columns:
                recent_roi = round(float(pd.to_numeric(sub["realized_roi"], errors="coerce").dropna().tail(100).mean()), 6) if pd.to_numeric(sub["realized_roi"], errors="coerce").dropna().size else None
        stability = 0.65
        if not preds.empty and f"{model}_probability" in preds.columns:
            p = pd.to_numeric(preds[f"{model}_probability"], errors="coerce").dropna()
            if len(p):
                stability = max(0.0, min(1.0, 1.0 - float(p.std()) * 2.0))
        calibration_quality = _safe(cal.get("calibration_quality_score"), 0.35)
        real_evidence_score = min(1.0, len(sub) / 30.0) if len(sub) else 0.0
        fallback_evidence_score = min(1.0, max(0, len(sub_all) - len(sub)) / 30.0) if len(sub_all) else 0.0
        if real_evidence_score >= 1.0:
            health_source_type = "real"; reliability_status = "real_verified"
        elif fallback_evidence_score > 0:
            health_source_type = "fallback"; reliability_status = "fallback_only"
        else:
            health_source_type = "unknown"; reliability_status = "insufficient_evidence"
        drift_risk = _safe(drift.get("drift_score"), 0.0)
        reliability = _safe(cal.get("reliability_score"), calibration_quality)
        prediction_quality = 0.5 * reliability + 0.3 * stability + 0.2 * (recent_accuracy if recent_accuracy is not None else 0.5)
        health = max(0.0, min(1.0, prediction_quality * 0.45 + calibration_quality * 0.25 + (1 - drift_risk) * 0.2 + stability * 0.1))
        reports[model] = {
            "prediction_quality_score": round(prediction_quality, 6),
            "health_source_type": health_source_type,
            "real_evidence_score": round(real_evidence_score, 6),
            "fallback_evidence_score": round(fallback_evidence_score, 6),
            "evidence_quality": reliability_status,
            "reliability_status": reliability_status,
            "source_type_breakdown": source_counts,
            "calibration_quality_score": round(calibration_quality, 6),
            "drift_risk_score": round(drift_risk, 6),
            "reliability_score": round(reliability, 6),
            "stability_score": round(stability, 6),
            "recent_roi": recent_roi,
            "recent_accuracy": recent_accuracy,
            "confidence_health": round(max(0.0, min(1.0, reliability * 0.6 + stability * 0.4)), 6),
            "model_weight_multiplier": round(max(0.25, min(1.0, health)), 6),
            "operational_status": _status(health),
            "health_score": round(health, 6),
        }
    payload = {"ok": True, "mode": MODE, "generated_at": datetime.now(timezone.utc).isoformat(), "models": reports, "global_status": _status(sum(v["health_score"] for v in reports.values()) / max(1, len(reports))), "source_aware": True}
    out = root / "data/ml/model_health.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return payload
