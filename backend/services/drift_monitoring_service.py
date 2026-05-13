from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

MODE = "PAPER_TRADING_SIMULATION_ONLY"


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _safe_read(path: Path) -> pd.DataFrame:
    try:
        if path.exists():
            return pd.read_csv(path) if path.suffix.lower() == ".csv" else safe_read_dataframe(path)
    except Exception:
        pass
    return pd.DataFrame()


def _hist(series: pd.Series, bins: int = 10) -> list[float]:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return [1.0 / bins] * bins
    lo, hi = float(s.min()), float(s.max())
    if lo == hi:
        return [1.0] + [0.0] * (bins - 1)
    counts = pd.cut(s, bins=bins, labels=False, include_lowest=True).value_counts().reindex(range(bins), fill_value=0).sort_index().astype(float)
    total = float(counts.sum()) or 1.0
    return (counts / total).tolist()


def psi(current: list[float], baseline: list[float]) -> float:
    eps = 1e-6
    return round(sum((c - b) * math.log((c + eps) / (b + eps)) for c, b in zip(current, baseline)), 6)


def js_divergence(current: list[float], baseline: list[float]) -> float:
    eps = 1e-12
    m = [(c + b) / 2 for c, b in zip(current, baseline)]
    def kl(a, b):
        return sum((x + eps) * math.log((x + eps) / (y + eps)) for x, y in zip(a, b))
    return round((kl(current, m) + kl(baseline, m)) / 2, 6)


def ks_statistic(current: pd.Series, baseline: pd.Series) -> float:
    a = pd.to_numeric(current, errors="coerce").dropna().sort_values().tolist()
    b = pd.to_numeric(baseline, errors="coerce").dropna().sort_values().tolist()
    if not a or not b:
        return 0.0
    values = sorted(set(a + b))
    ia = ib = 0; n = len(a); m = len(b); d = 0.0
    for v in values:
        while ia < n and a[ia] <= v: ia += 1
        while ib < m and b[ib] <= v: ib += 1
        d = max(d, abs(ia / n - ib / m))
    return round(d, 6)


def _split_baseline_current(df: pd.DataFrame, date_col: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df.empty or len(df) < 4:
        return df, df
    if date_col and date_col in df.columns:
        sorted_df = df.sort_values(date_col)
    else:
        sorted_df = df.reset_index(drop=True)
    cut = max(1, int(len(sorted_df) * 0.7))
    return sorted_df.iloc[:cut].copy(), sorted_df.iloc[cut:].copy()


def _severity(score: float) -> str:
    if score >= 0.45: return "critical"
    if score >= 0.2: return "warning"
    return "info"


def _level(score: float) -> str:
    if score >= 0.45: return "high"
    if score >= 0.2: return "medium"
    return "low"


def _drift_for_column(df: pd.DataFrame, col: str, drift_type: str, entity: str | None = None) -> dict[str, Any] | None:
    if col not in df.columns or len(df) < 4:
        return None
    baseline, current = _split_baseline_current(df, "match_date" if "match_date" in df.columns else None)
    if baseline.empty or current.empty:
        return None
    base_hist = _hist(baseline[col]); curr_hist = _hist(current[col])
    psi_score = psi(curr_hist, base_hist)
    js = js_divergence(curr_hist, base_hist)
    ks = ks_statistic(current[col], baseline[col])
    score = round(min(1.0, psi_score * 0.45 + js * 1.2 + ks * 0.35), 6)
    return {
        "drift_type": drift_type,
        "feature_model_market": entity or col,
        "column": col,
        "current_distribution": curr_hist,
        "baseline_distribution": base_hist,
        "psi": psi_score,
        "ks_statistic": ks,
        "jensen_shannon": js,
        "drift_score": score,
        "severity": _severity(score),
        "recommendation": "Review recent window and reduce confidence if persistent." if score >= 0.2 else "Continue monitoring.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def build_drift_report(root: Path | None = None) -> dict[str, Any]:
    root = Path(root) if root else project_root()
    features = _safe_read(root / "data/features/future_features.parquet")
    preds = _safe_read(root / "data/ml/predictions/future_predictions.parquet")
    settled = _safe_read(root / "data/ml/settled_predictions.parquet")
    checks: list[dict[str, Any]] = []
    for col in ["expected_goals_proxy", "over_25_rate_last_10", "btts_rate_last_10", "recent_form_score", "data_quality_score", "feature_completeness_score"]:
        item = _drift_for_column(features, col, "feature_drift")
        if item: checks.append(item)
    for col in ["ensemble_probability", "calibrated_ensemble_probability", "confidence_score", "model_agreement_score", "disagreement_score", "ensemble_entropy"]:
        item = _drift_for_column(preds, col, "prediction_confidence_drift")
        if item: checks.append(item)
    if not settled.empty:
        for col in ["realized_roi", "prediction_correct", "calibrated_probability"]:
            item = _drift_for_column(settled, col, "performance_calibration_drift")
            if item: checks.append(item)
    max_score = max([float(c.get("drift_score", 0)) for c in checks], default=0.0)
    affected_features = sorted({c.get("column") for c in checks if c.get("severity") != "info" and c.get("drift_type") == "feature_drift"})
    affected_models = sorted({c.get("column") for c in checks if c.get("severity") != "info" and "prediction" in c.get("drift_type", "")})
    affected_leagues = sorted(set(preds.get("league", pd.Series(dtype=str)).dropna().astype(str).head(20).tolist())) if not preds.empty else []
    payload = {
        "ok": True,
        "mode": MODE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "drift_score": round(max_score, 6),
        "drift_level": _level(max_score),
        "severity": _severity(max_score),
        "affected_features": affected_features,
        "affected_models": affected_models,
        "affected_leagues": affected_leagues,
        "affected_markets": sorted(set(preds.get("market", pd.Series(dtype=str)).dropna().astype(str).tolist())) if not preds.empty else [],
        "recommendation": "Continue monitoring" if max_score < 0.2 else "Review calibration, recent data quality, and ensemble weights before promoting new signals.",
        "checks": checks,
        "statistical_methods": ["PSI", "KS", "Jensen-Shannon", "rolling_window_split"],
    }
    out_dir = root / "data/monitoring"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "drift_report.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    hist_path = out_dir / "drift_history.parquet"
    hist = pd.DataFrame([{"timestamp": payload["timestamp"], "drift_score": payload["drift_score"], "drift_level": payload["drift_level"], "severity": payload["severity"]}])
    if hist_path.exists():
        old = _safe_read(hist_path)
        hist = pd.concat([old, hist], ignore_index=True)
    safe_write_dataframe(hist, hist_path, index=False)
    alerts = [{"alert_type": "DRIFT", "severity": c["severity"], "reason": c["feature_model_market"], "drift_score": c["drift_score"], "recommendation": c["recommendation"]} for c in checks if c.get("severity") != "info"]
    (out_dir / "drift_alerts.json").write_text(json.dumps({"ok": True, "mode": MODE, "alerts": alerts, "generated_at": payload["timestamp"]}, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return payload


__all__ = ["build_drift_report", "psi", "ks_statistic", "js_divergence"]
