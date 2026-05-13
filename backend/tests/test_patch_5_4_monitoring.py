from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_runner():
    path = root() / "10_monitoring" / "run_monitoring.py"
    spec = importlib.util.spec_from_file_location("monitoring_runner_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_monitoring_outputs_are_generated():
    module = load_runner()
    result = module.run_monitoring(root())
    assert result["mode"] == "PAPER_TRADING_SIMULATION_ONLY"
    for rel in [
        "data/monitoring/alerts.json",
        "data/monitoring/monitoring_status.json",
        "data/monitoring/drift_report.json",
        "data/monitoring/anomaly_report.json",
        "data/monitoring/monitoring_journal.md",
    ]:
        path = root() / rel
        assert path.exists()
        assert path.stat().st_size > 0


def test_alerts_are_useful_and_structured():
    module = load_runner()
    module.run_monitoring(root())
    payload = json.loads((root() / "data/monitoring/alerts.json").read_text(encoding="utf-8"))
    assert payload["mode"] == "PAPER_TRADING_SIMULATION_ONLY"
    assert "total_alerts" in payload
    assert isinstance(payload["alerts"], list)
    for alert in payload["alerts"]:
        assert alert["category"] in {"DATA", "PERFORMANCE", "ML", "DECISION_ENGINE", "SYSTEM"}
        assert alert["severity"] in {"LOW", "MEDIUM", "HIGH"}
        assert alert["message"]
        assert alert["next_step"]


def test_drift_and_anomalies_have_boolean_flags():
    module = load_runner()
    module.run_monitoring(root())
    drift = json.loads((root() / "data/monitoring/drift_report.json").read_text(encoding="utf-8"))
    anomalies = json.loads((root() / "data/monitoring/anomaly_report.json").read_text(encoding="utf-8"))
    assert isinstance(drift["drift_detected"], bool)
    assert isinstance(anomalies["anomalies_detected"], bool)


def _auth_headers(client: TestClient) -> dict[str, str]:
    r = client.post("/api/auth/login", json={"email": "admin@matchflow.local", "password": "admin123"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_monitoring_endpoints_work():
    client = TestClient(app)
    headers = _auth_headers(client)
    client.post("/api/monitoring/run", headers=headers)
    for path in ["/api/monitoring/status", "/api/monitoring/alerts", "/api/monitoring/drift", "/api/monitoring/anomalies"]:
        res = client.get(path, headers=headers)
        assert res.status_code == 200
        body = res.json()
        assert body["mode"] == "PAPER_TRADING_SIMULATION_ONLY"
        assert body["ok"] is True
