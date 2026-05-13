from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.drift_monitoring_service import build_drift_report, js_divergence, ks_statistic, psi
from backend.services.job_scheduler_service import list_jobs, run_job
from backend.services.ml_calibration_service import build_calibration_report, calibrate_probability
from backend.services.ml_reliability_service import reliability_bins, sync_settled_predictions
from backend.services.model_health_service import build_model_health_report
from backend.services.monitoring_alert_service import build_monitoring_alerts


def _seed_reliability_dataset(root: Path) -> None:
    pred_dir = root / "data/ml/predictions"
    pred_dir.mkdir(parents=True, exist_ok=True)
    pred = pd.DataFrame([
        {"match_identity_key": f"m{i}", "match_id": f"m{i}", "market": "goals_over_25", "league": "Demo", "match_date": f"2026-01-{(i%20)+1:02d}", "random_forest_probability": 0.45 + (i % 10) * 0.04, "lightgbm_probability": 0.46 + (i % 10) * 0.035, "xgboost_probability": 0.44 + (i % 10) * 0.045, "raw_ensemble_probability": 0.45 + (i % 10) * 0.04, "ensemble_probability": 0.45 + (i % 10) * 0.04, "confidence_score": 0.5 + (i % 7) * 0.05, "model_agreement_score": 0.9, "data_quality_score": 0.8}
        for i in range(40)
    ])
    pred.to_parquet(pred_dir / "future_predictions.parquet", index=False)
    pred.to_csv(pred_dir / "future_predictions.csv", index=False)
    paper_dir = root / "data/paper_trading"
    paper_dir.mkdir(parents=True, exist_ok=True)
    paper = pd.DataFrame([
        {"signal_id": f"s{i}", "match_identity_key": f"m{i}", "match_id": f"m{i}", "market": "goals_over_25", "league": "Demo", "date": f"2026-01-{(i%20)+1:02d}", "status": "WIN" if i % 3 else "LOSS", "is_win": bool(i % 3), "odd": 1.9, "stake": 1.0, "profit": 0.9 if i % 3 else -1.0, "confidence_score": 0.5 + (i % 7) * 0.05, "decision_score": 0.55 + (i % 8) * 0.04, "data_quality_score": 0.8, "settled_at": "2026-02-01T00:00:00Z"}
        for i in range(40)
    ])
    paper.to_csv(paper_dir / "paper_signals.csv", index=False)
    feat_dir = root / "data/features"
    feat_dir.mkdir(parents=True, exist_ok=True)
    feat = pd.DataFrame([
        {"match_identity_key": f"m{i}", "match_date": f"2026-01-{(i%20)+1:02d}", "expected_goals_proxy": 0.8 + i * 0.01, "over_25_rate_last_10": 0.3 + (i % 10) * 0.05, "btts_rate_last_10": 0.35 + (i % 8) * 0.04, "recent_form_score": 0.4 + (i % 6) * 0.07, "data_quality_score": 0.8, "feature_completeness_score": 0.75}
        for i in range(40)
    ])
    feat.to_parquet(feat_dir / "future_features.parquet", index=False)
    raw_dir = root / "data/raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw = pd.DataFrame([
        {"match_identity_key": f"m{i}", "match_date": f"2026-01-{(i%20)+1:02d}", "league": "Demo", "home_team": f"Home {i}", "away_team": f"Away {i}", "status": "FINISHED", "goals_home_ft": 2 if i % 3 else 0, "goals_away_ft": 1, "is_demo_data": False, "data_quality_score": 0.85}
        for i in range(40)
    ])
    raw.to_parquet(raw_dir / "flashscore_matches.parquet", index=False)


def test_settled_predictions_and_real_calibration(tmp_path):
    _seed_reliability_dataset(tmp_path)
    sync = sync_settled_predictions(tmp_path)
    assert sync["settled_predictions"] >= 40
    report = build_calibration_report(tmp_path)
    rf = report["models"]["random_forest"]
    assert rf["calibration_sample_size"] >= 40
    assert rf["brier_score"] is not None
    assert rf["ece"] is not None
    assert (tmp_path / "data/ml/calibration/reliability_bins.csv").exists()
    assert 0 < calibrate_probability(0.7, model_name="random_forest", root=tmp_path) < 1


def test_reliability_metrics_and_drift_statistics():
    bins = reliability_bins([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1], bins=2)
    assert len(bins) == 2
    assert psi([0.7, 0.3], [0.5, 0.5]) > 0
    assert js_divergence([0.7, 0.3], [0.5, 0.5]) > 0
    assert ks_statistic(pd.Series([1, 2, 3]), pd.Series([1, 1, 1])) >= 0


def test_advanced_drift_model_health_alerts_and_jobs(tmp_path):
    _seed_reliability_dataset(tmp_path)
    build_calibration_report(tmp_path)
    drift = build_drift_report(tmp_path)
    assert "statistical_methods" in drift
    assert "checks" in drift
    health = build_model_health_report(tmp_path)
    assert health["models"]["random_forest"]["operational_status"] in {"healthy", "warning", "degraded", "unstable", "blocked"}
    alerts = build_monitoring_alerts(tmp_path)
    assert alerts["ok"] is True
    jobs = list_jobs(tmp_path)
    names = {j["name"] for j in jobs["jobs"]}
    assert {"calibration_refresh", "drift_analysis", "model_health_analysis", "settled_predictions_sync"} <= names
    assert run_job("settled_predictions_sync", tmp_path)["ok"] is True


def test_monitoring_endpoints_include_quantitative_reliability():
    client = TestClient(app)
    login = client.post("/api/auth/login", json={"email": "admin@matchflow.local", "password": "admin123"})
    token = login.json().get("access_token") or login.json().get("token") or login.json().get("data", {}).get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    for path in ["/api/ml/calibration/report", "/api/ml/model-health", "/api/monitoring/drift", "/api/monitoring/alerts"]:
        res = client.get(path, headers=headers)
        assert res.status_code == 200, path
        assert res.json().get("ok") is True
