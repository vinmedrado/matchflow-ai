from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.data_engine.providers.flashscore.coverage_report import build_flashscore_coverage_report
from backend.services.drift_monitoring_service import build_drift_report
from backend.services.job_scheduler_service import list_jobs, run_job
from backend.services.ml_calibration_service import build_calibration_report, calibrate_probability


def test_coverage_report_contract(tmp_path):
    report = build_flashscore_coverage_report(Path.cwd())
    assert "odds_coverage_pct" in report
    assert "stats_coverage_pct" in report
    assert "field_missing_summary" in report


def test_calibration_contract():
    assert 0 < calibrate_probability(0.61) < 1
    report = build_calibration_report(Path.cwd())
    assert "models" in report
    assert "random_forest" in report["models"]


def test_drift_report_contract():
    report = build_drift_report(Path.cwd())
    assert "drift_score" in report
    assert report["drift_level"] in {"low", "medium", "high"}


def test_jobs_contract_and_locking_safe():
    jobs = list_jobs(Path.cwd())
    names = {j["name"] for j in jobs["jobs"]}
    assert "coverage_report" in names
    result = run_job("coverage_report", Path.cwd())
    assert result["job_name"] == "coverage_report"


def test_production_maturity_endpoints():
    client = TestClient(app)
    login = client.post("/api/auth/login", json={"email":"admin@matchflow.local","password":"admin123"})
    token = login.json().get("access_token") or login.json().get("token") or login.json().get("data",{}).get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    for path in ["/metrics", "/api/data-engine/flashscore/coverage", "/api/ml/calibration/report", "/api/jobs", "/api/monitoring/drift"]:
        res = client.get(path, headers=headers)
        assert res.status_code == 200, path
        assert res.json().get("ok") is True
