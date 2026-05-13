from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from backend.main import app


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PAPER_ROOT = PROJECT_ROOT / "05_paper_trading"


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, PAPER_ROOT / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_discard_never_generates_signal(tmp_path: Path):
    selector_mod = _load_module("signal_selector_test_discard", "signal_selector.py")
    refinement = tmp_path / "data/backtest/refinement"
    features = tmp_path / "data/features"
    refinement.mkdir(parents=True)
    features.mkdir(parents=True)

    pd.DataFrame([
        {"strategy": "bad", "market": "goals", "total_trades": 1000, "consistency_score": 90, "recommendation": "DISCARD", "risk_flags": ""}
    ]).to_csv(refinement / "refined_strategy_candidates.csv", index=False)
    pd.DataFrame([
        {"strategy": "bad", "market": "goals", "risk_flags": "", "final_recommendation": "DISCARD"}
    ]).to_csv(refinement / "refinement_risk_report.csv", index=False)
    pd.DataFrame([{
        "date": "2026-01-01", "team_key": "a", "team_name": "A", "opponent_key": "b", "opponent_name": "B",
        "league": "L", "season": "2026", "match_key": "m1", "side": "home", "goal_trend": 1.0, "expected_goals_proxy": 2.0,
        "odds_over_2_5": 1.8
    }]).to_parquet(features / "team_dataset_advanced.parquet", index=False)

    selector = selector_mod.PaperSignalSelector(tmp_path, {
        "allowed_recommendations": ["KEEP"], "min_consistency_score": 60, "min_sample_size": 100, "max_signals_per_day": 10, "fixed_stake": 1.0
    })
    signals = selector.select_signals()
    assert signals.empty


def test_keep_can_generate_signal(tmp_path: Path):
    selector_mod = _load_module("signal_selector_test_keep", "signal_selector.py")
    refinement = tmp_path / "data/backtest/refinement"
    features = tmp_path / "data/features"
    refinement.mkdir(parents=True)
    features.mkdir(parents=True)

    pd.DataFrame([
        {"strategy": "goals_over_2_5", "market": "goals", "total_trades": 150, "consistency_score": 75, "recommendation": "KEEP", "risk_flags": ""}
    ]).to_csv(refinement / "refined_strategy_candidates.csv", index=False)
    pd.DataFrame([
        {"strategy": "goals_over_2_5", "market": "goals", "risk_flags": "", "final_recommendation": "KEEP"}
    ]).to_csv(refinement / "refinement_risk_report.csv", index=False)
    pd.DataFrame([{
        "date": "2026-01-01", "team_key": "a", "team_name": "A", "opponent_key": "b", "opponent_name": "B",
        "league": "L", "season": "2026", "match_key": "m1", "side": "home", "goal_trend": 1.0, "expected_goals_proxy": 2.0,
        "odds_over_2_5": 1.8
    }]).to_parquet(features / "team_dataset_advanced.parquet", index=False)

    selector = selector_mod.PaperSignalSelector(tmp_path, {
        "allowed_recommendations": ["KEEP"], "min_consistency_score": 60, "min_sample_size": 100, "max_signals_per_day": 10, "fixed_stake": 1.0
    })
    signals = selector.select_signals()
    assert len(signals) == 1
    assert signals.iloc[0]["recommendation"] == "KEEP"


def test_min_sample_and_consistency_are_respected(tmp_path: Path):
    selector_mod = _load_module("signal_selector_test_filters", "signal_selector.py")
    refinement = tmp_path / "data/backtest/refinement"
    features = tmp_path / "data/features"
    refinement.mkdir(parents=True)
    features.mkdir(parents=True)
    pd.DataFrame([
        {"strategy": "low_sample", "market": "goals", "total_trades": 99, "consistency_score": 90, "recommendation": "KEEP", "risk_flags": ""},
        {"strategy": "low_score", "market": "goals", "total_trades": 150, "consistency_score": 59, "recommendation": "KEEP", "risk_flags": ""},
    ]).to_csv(refinement / "refined_strategy_candidates.csv", index=False)
    pd.DataFrame([
        {"strategy": "low_sample", "market": "goals", "risk_flags": "", "final_recommendation": "KEEP"},
        {"strategy": "low_score", "market": "goals", "risk_flags": "", "final_recommendation": "KEEP"},
    ]).to_csv(refinement / "refinement_risk_report.csv", index=False)
    pd.DataFrame([{"date": "2026-01-01", "team_key": "a", "goal_trend": 1, "expected_goals_proxy": 2, "odds_over_2_5": 1.8}]).to_parquet(features / "team_dataset_advanced.parquet", index=False)
    selector = selector_mod.PaperSignalSelector(tmp_path, {"allowed_recommendations": ["KEEP"], "min_consistency_score": 60, "min_sample_size": 100})
    assert selector.select_signals().empty


def test_bankroll_updates_correctly(tmp_path: Path):
    engine_mod = _load_module("paper_engine_test", "paper_engine.py")
    engine = engine_mod.PaperTradingEngine(tmp_path, {"initial_bankroll": 100.0, "fixed_stake": 1.0})
    signals = pd.DataFrame([
        {"signal_id": "s1", "status": "SETTLED", "strategy": "goals", "market": "goals", "odd": 2.0, "stake": 1.0, "recommendation": "KEEP", "date": "2026-01-01"},
    ])
    _, results, equity, summary = engine.run(signals)
    assert len(results) == 1
    assert summary["current_bankroll"] in (99.0, 101.0)
    assert not equity.empty


def test_paper_summary_json_is_generated():
    summary_path = PROJECT_ROOT / "data/paper_trading/paper_summary.json"
    assert summary_path.exists()
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    assert data["paper_only"] is True
    assert "total_signals" in data
    assert "current_bankroll" in data


def test_paper_trading_summary_endpoint():
    client = TestClient(app)
    login = client.post("/api/auth/login", json={"email": "admin@matchflow.local", "password": "admin123"})
    token = login.json()["access_token"]
    response = client.get("/api/paper-trading/summary", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert "total_signals" in data
    assert "current_bankroll" in data
    assert data["paper_only"] is True
