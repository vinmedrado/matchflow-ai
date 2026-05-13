from pathlib import Path
import pandas as pd
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.settled_results_service import build_all_settled_results, actual_result_for_market
from backend.services.ml_calibration_service import build_calibration_report
from backend.services.model_health_service import build_model_health_report
from backend.services.evidence_alert_service import build_evidence_alerts

def test_actual_result_market_calculation():
    row={"goals_home_ft":2,"goals_away_ft":1,"corners_home":6,"corners_away":4}
    assert actual_result_for_market(row,"over_25")==1
    assert actual_result_for_market(row,"under_25")==0
    assert actual_result_for_market(row,"btts_yes")==1
    assert actual_result_for_market(row,"home_win")==1
    assert actual_result_for_market(row,"corners_over_95")==1

def test_settled_results_are_source_separated(tmp_path: Path):
    root=tmp_path; (root/"data/raw").mkdir(parents=True); (root/"data/ml/predictions").mkdir(parents=True)
    pd.DataFrame([{"match_identity_key":"m1","match_date":"2026-01-01","league":"EPL","home_team":"A","away_team":"B","status":"FINISHED","goals_home_ft":2,"goals_away_ft":1,"is_demo_data":False,"data_quality_score":0.9},{"match_identity_key":"demo1","status":"FINISHED","goals_home_ft":3,"goals_away_ft":0,"is_demo_data":True}]).to_parquet(root/"data/raw/flashscore_matches.parquet",index=False)
    pd.DataFrame([{"match_identity_key":"m1","market":"over_25","ensemble_probability":0.64,"calibrated_ensemble_probability":0.61,"odds":1.9}]).to_parquet(root/"data/ml/predictions/future_predictions.parquet",index=False)
    summary=build_all_settled_results(root); assert summary["real"]["real_settled_results"]>=1
    real=pd.read_parquet(root/"data/results/real_settled_results.parquet")
    assert set(real["settlement_source_type"])=={"real"}; assert "demo1" not in set(real["match_identity_key"].astype(str))

def test_calibration_is_not_real_when_sample_is_small(tmp_path: Path):
    root=tmp_path; (root/"data/raw").mkdir(parents=True); (root/"data/ml/predictions").mkdir(parents=True)
    pd.DataFrame([{"match_identity_key":"m1","status":"FINISHED","goals_home_ft":1,"goals_away_ft":1,"is_demo_data":False}]).to_parquet(root/"data/raw/flashscore_matches.parquet",index=False)
    pd.DataFrame([{"match_identity_key":"m1","market":"btts_yes","ensemble_probability":0.7}]).to_parquet(root/"data/ml/predictions/future_predictions.parquet",index=False)
    report=build_calibration_report(root)
    assert report["is_real_calibration"] is False
    assert report["calibration_mode"]=="fallback"
    assert report["calibration_source"]=="insufficient_real_settled_results"
    assert report["uses_backtest_data"] is False and report["uses_paper_data"] is False and report["uses_demo_data"] is False

def test_model_health_and_evidence_alerts_are_source_aware(tmp_path: Path):
    root=tmp_path; (root/"data/raw").mkdir(parents=True); (root/"data/ml/predictions").mkdir(parents=True)
    pd.DataFrame(columns=["match_identity_key","status","goals_home_ft","goals_away_ft"]).to_parquet(root/"data/raw/flashscore_matches.parquet",index=False)
    pd.DataFrame(columns=["match_identity_key","market","ensemble_probability"]).to_parquet(root/"data/ml/predictions/future_predictions.parquet",index=False)
    health=build_model_health_report(root); assert health["source_aware"] is True
    for item in health["models"].values():
        assert "health_source_type" in item and "real_evidence_score" in item
        assert item["reliability_status"] in {"real_verified","fallback_only","insufficient_evidence"}
    alerts=build_evidence_alerts(root); assert any(a["code"]=="REAL_CALIBRATION_UNAVAILABLE" for a in alerts["alerts"])

def test_results_and_evidence_endpoints():
    client=TestClient(app); token=client.post("/api/auth/login",json={"email":"admin@matchflow.local","password":"admin123"}).json()["access_token"]; h={"Authorization":f"Bearer {token}"}
    assert client.get("/api/results/settled/summary",headers=h).status_code==200
    assert client.get("/api/results/settled/real",headers=h).status_code==200
    assert client.get("/api/monitoring/evidence-alerts",headers=h).status_code==200
