from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.services.drift_monitoring_service import build_drift_report
from backend.services.ml_calibration_service import build_calibration_report
from backend.services.model_health_service import build_model_health_report

MODE = "PAPER_TRADING_SIMULATION_ONLY"


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def build_monitoring_alerts(root: Path | None = None) -> dict[str, Any]:
    root = Path(root) if root else project_root()
    drift = build_drift_report(root)
    calibration = build_calibration_report(root)
    health = build_model_health_report(root)
    alerts: list[dict[str, Any]] = []
    if drift.get("severity") in {"warning", "critical"}:
        alerts.append({"alert_type": "DRIFT", "severity": drift.get("severity"), "title": "Drift estatístico detectado", "reason": f"drift_score={drift.get('drift_score')}", "recommendation": drift.get("recommendation")})
    for model, rec in calibration.get("models", {}).items():
        if (rec.get("ece") is not None and rec.get("ece") > 0.12) or rec.get("calibration_quality_score", 1) < 0.45:
            alerts.append({"alert_type": "CALIBRATION", "severity": "warning", "title": f"Calibração fraca em {model}", "reason": f"ECE={rec.get('ece')} sample={rec.get('calibration_sample_size')}", "recommendation": "Aguardar mais liquidações ou reduzir peso do modelo."})
    for model, rec in health.get("models", {}).items():
        if rec.get("operational_status") in {"degraded", "unstable", "blocked"}:
            alerts.append({"alert_type": "MODEL_HEALTH", "severity": "critical" if rec.get("operational_status") == "blocked" else "warning", "title": f"Modelo {model} {rec.get('operational_status')}", "reason": f"health_score={rec.get('health_score')}", "recommendation": "Reduzir peso no ensemble e revisar drift/calibração."})
    payload = {"ok": True, "mode": MODE, "generated_at": datetime.now(timezone.utc).isoformat(), "total_alerts": len(alerts), "alerts": alerts}
    out = root / "data/monitoring/alerts.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return payload
