from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PAPER_ROOT = PROJECT_ROOT / "05_paper_trading"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PAPER_ROOT) not in sys.path:
    sys.path.insert(0, str(PAPER_ROOT))

from paper_engine import PaperTradingEngine
from signal_selector import PaperSignalSelector


def _config() -> dict:
    return {
        "initial_bankroll": 100.0,
        "fixed_stake": 1.0,
        "allowed_recommendations": ["KEEP"],
        "max_signals_per_day": 10,
        "min_consistency_score": 60,
        "min_sample_size": 100,
        "paper_only": True,
        "resolution_delay_days": 1,
        "signals_path": "data/paper_trading/paper_signals.csv",
        "results_path": "data/paper_trading/paper_results.csv",
        "equity_curve_path": "data/paper_trading/paper_equity_curve.csv",
        "summary_path": "data/paper_trading/paper_summary.json",
        "state_path": "data/paper_trading/paper_state.json",
    }


def _signal(signal_id: str = "s1") -> pd.DataFrame:
    return pd.DataFrame([
        {
            "signal_id": signal_id,
            "created_at": "2026-01-01T00:00:00Z",
            "paper_only": True,
            "status": "PENDING",
            "signal_date": "2026-01-01",
            "expected_resolution_date": "2026-01-02",
            "strategy": "Over 2.5 FT",
            "market": "goals",
            "recommendation": "KEEP",
            "team_key": "a",
            "team_name": "A",
            "opponent_key": "b",
            "opponent_name": "B",
            "league": "Test",
            "season": "2026",
            "date": "2026-01-01",
            "match_key": "m1",
            "side": "home",
            "odd": 2.0,
            "stake": 1.0,
            "consistency_score": 70,
            "supporting_sample_size": 120,
            "risk_flags": "",
            "source": "test",
            "total_goals_ft": 3,
            "goals_for_ft": 2,
            "goals_against_ft": 1,
        }
    ])


def test_new_signal_stays_pending_on_first_run(tmp_path: Path):
    engine = PaperTradingEngine(tmp_path, _config())
    signals, results, equity, summary = engine.run(_signal(), pd.Timestamp("2026-01-01"))
    assert len(signals) == 1
    assert signals.iloc[0]["status"] == "PENDING"
    assert results.empty
    assert summary["pending_signals"] == 1
    state = json.loads((tmp_path / "data/paper_trading/paper_state.json").read_text())
    assert state["active_signals"]


def test_signal_resolves_only_after_expected_resolution_date(tmp_path: Path):
    engine = PaperTradingEngine(tmp_path, _config())
    engine.run(_signal(), pd.Timestamp("2026-01-01"))
    signals, results, equity, summary = engine.run(pd.DataFrame(), pd.Timestamp("2026-01-02"))
    assert len(results) == 1
    assert bool(results.iloc[0]["is_win"]) is True
    assert float(results.iloc[0]["profit"]) == 1.0
    assert summary["settled_signals"] == 1
    assert summary["current_bankroll"] == 101.0


def test_running_twice_does_not_duplicate_signal(tmp_path: Path):
    engine = PaperTradingEngine(tmp_path, _config())
    engine.run(_signal(), pd.Timestamp("2026-01-01"))
    engine.run(_signal(), pd.Timestamp("2026-01-01"))
    signals = pd.read_csv(tmp_path / "data/paper_trading/paper_signals.csv")
    assert len(signals) == 1
    assert signals["signal_id"].nunique() == 1


def test_state_file_contains_required_keys(tmp_path: Path):
    engine = PaperTradingEngine(tmp_path, _config())
    state = engine.load_state()
    assert {"last_processed_date", "active_signals", "resolved_signals_ids"}.issubset(state.keys())


def test_selector_does_not_allow_discard(tmp_path: Path):
    refinement = tmp_path / "data/backtest/refinement"
    features = tmp_path / "data/features"
    refinement.mkdir(parents=True)
    features.mkdir(parents=True)
    pd.DataFrame([{"strategy": "Bad", "market": "goals", "recommendation": "DISCARD", "total_trades": 200, "consistency_score": 90}]).to_csv(refinement / "refined_strategy_candidates.csv", index=False)
    pd.DataFrame(columns=["strategy", "market", "risk_flags", "final_recommendation"]).to_csv(refinement / "refinement_risk_report.csv", index=False)
    pd.DataFrame([{"date": "2026-01-01", "match_key": "m1", "team_key": "a", "goal_trend": 1, "expected_goals_proxy": 1, "odds_over_2_5": 2.0}]).to_parquet(features / "team_dataset_advanced.parquet", index=False)
    selector = PaperSignalSelector(tmp_path, _config())
    signals = selector.select_signals(pd.Timestamp("2026-01-01"), None, set())
    assert signals.empty
