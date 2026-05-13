from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MODE = "PAPER_TRADING_SIMULATION_ONLY"


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_json(path: Path, default: Any | None = None) -> Any:
    if default is None:
        default = {}
    try:
        if not path.exists() or path.stat().st_size == 0:
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def run_monitoring_service() -> dict[str, Any]:
    root = project_root()
    import sys
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from matchflow_imports import import_from_dir
    module = import_from_dir("matchflow_monitoring", root / "10_monitoring", "run_monitoring")
    return module.run_monitoring(root)


def monitoring_status() -> dict[str, Any]:
    data = _read_json(project_root() / "data/monitoring/monitoring_status.json", {})
    if not data:
        data = {"ok": True, "mode": MODE, "overall_status": "NOT_RUN", "risk_level": "UNKNOWN", "message": "Monitoramento ainda não foi executado."}
    data["mode"] = MODE
    return data


def monitoring_alerts() -> dict[str, Any]:
    data = _read_json(project_root() / "data/monitoring/alerts.json", {})
    if not data:
        data = {"ok": True, "mode": MODE, "total_alerts": 0, "alerts": []}
    data["mode"] = MODE
    return data


def monitoring_drift() -> dict[str, Any]:
    from backend.services.drift_monitoring_service import build_drift_report
    data = build_drift_report(project_root())
    data["mode"] = MODE
    data["drift_detected"] = data.get("drift_level") in {"medium", "high"}
    return data


def monitoring_anomalies() -> dict[str, Any]:
    data = _read_json(project_root() / "data/monitoring/anomaly_report.json", {})
    if not data:
        data = {"ok": True, "mode": MODE, "anomalies_detected": False, "anomalies": []}
    data["mode"] = MODE
    return data
