from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKTEST_ROOT = PROJECT_ROOT / "04_backtest"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKTEST_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKTEST_ROOT))

from engine.metrics import calculate_summary
from engine.signal_generator import generate_signals
from engine.simulation_engine import build_equity_curve, simulate_signals


def sample_advanced_dataset() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "event_id": "1",
            "match_key": "m1",
            "date": "2024-01-01",
            "league": "League A",
            "season": "2024",
            "team_key": "team_a",
            "team_name": "Team A",
            "opponent_key": "team_b",
            "opponent_name": "Team B",
            "side": "home",
            "goals_for_ft": 2,
            "goals_against_ft": 1,
            "total_goals_ft": 3,
            "shots_for": 12,
            "shots_against": 7,
            "corners_for": 6,
            "corners_against": 4,
            "goals_for_ft_avg_last_5": 1.8,
            "shots_avg_last_5": 11.0,
            "pressure_avg_last_5": 12.0,
            "expected_goals_proxy": 0.8,
            "corners_avg_last_5": 5.0,
            "shots_on_target_avg_last_5": 4.0,
            "high_shots_flag": 1,
            "team_attack_strength": 0.9,
            "opponent_defense_weakness": 0.9,
            "attack_vs_defense_ratio": 1.1,
            "odds_over_2_5": 2.10,
            "odds_shots": 1.85,
            "odds_corners": 1.92,
            "odds_btts": 1.75,
        },
        {
            "event_id": "2",
            "match_key": "m2",
            "date": "2024-01-02",
            "league": "League A",
            "season": "2024",
            "team_key": "team_c",
            "team_name": "Team C",
            "opponent_key": "team_d",
            "opponent_name": "Team D",
            "side": "home",
            "goals_for_ft": 0,
            "goals_against_ft": 1,
            "total_goals_ft": 1,
            "shots_for": 6,
            "shots_against": 10,
            "corners_for": 2,
            "corners_against": 6,
            "goals_for_ft_avg_last_5": 1.8,
            "shots_avg_last_5": 11.0,
            "pressure_avg_last_5": 12.0,
            "expected_goals_proxy": 0.8,
            "odds_over_2_5": 2.00,
        },
    ])


def test_signal_generation_requires_valid_odds():
    df = sample_advanced_dataset()
    strategies = [{
        "strategy": "goals_over_2_5",
        "market": "goals",
        "selection": "over",
        "line": 2.5,
        "odds_aliases": ["odds_over_2_5"],
        "thresholds": {
            "goals_for_ft_avg_last_5": 1.0,
            "shots_avg_last_5": 8.0,
            "pressure_avg_last_5": 9.0,
        },
    }]

    signals = generate_signals(df, strategies, min_odds=1.2)

    assert len(signals) == 2
    assert "odd" in signals.columns
    assert signals.iloc[0]["odd"] == 2.10


def test_signal_generation_ignores_missing_odds():
    df = sample_advanced_dataset().drop(columns=["odds_over_2_5"])
    strategies = [{
        "strategy": "goals_over_2_5",
        "market": "goals",
        "selection": "over",
        "line": 2.5,
        "odds_aliases": ["odds_over_2_5"],
        "thresholds": {"goals_for_ft_avg_last_5": 1.0},
    }]

    signals = generate_signals(df, strategies, min_odds=1.2)

    assert signals.empty


def test_financial_profit_and_bankroll_are_correct():
    df = sample_advanced_dataset()
    strategies = [{
        "strategy": "goals_over_2_5",
        "market": "goals",
        "selection": "over",
        "line": 2.5,
        "odds_aliases": ["odds_over_2_5"],
        "thresholds": {"goals_for_ft_avg_last_5": 1.0},
    }]
    signals = generate_signals(df, strategies)
    simulated = simulate_signals(signals, {"simulation": {"initial_bankroll": 100.0, "stake": 1.0, "min_odds": 1.2}})

    assert len(simulated) == 2
    assert round(float(simulated.iloc[0]["profit"]), 2) == 1.10
    assert round(float(simulated.iloc[1]["profit"]), 2) == -1.00
    assert round(float(simulated.iloc[-1]["bankroll_after"]), 2) == 100.10
    assert round(float(simulated.iloc[-1]["cumulative_profit"]), 2) == 0.10


def test_roi_is_consistent():
    df = sample_advanced_dataset()
    strategies = [{
        "strategy": "goals_over_2_5",
        "market": "goals",
        "selection": "over",
        "line": 2.5,
        "odds_aliases": ["odds_over_2_5"],
        "thresholds": {"goals_for_ft_avg_last_5": 1.0},
    }]
    signals = generate_signals(df, strategies)
    simulated = simulate_signals(signals, {"simulation": {"initial_bankroll": 100.0, "stake": 1.0, "min_odds": 1.2}})
    summary = calculate_summary(simulated)

    assert len(summary) == 1
    assert summary.iloc[0]["total_trades"] == 2
    assert round(float(summary.iloc[0]["total_profit"]), 2) == 0.10
    assert round(float(summary.iloc[0]["roi"]), 2) == 0.05


def test_equity_curve_output_columns():
    df = sample_advanced_dataset()
    strategies = [{
        "strategy": "goals_over_2_5",
        "market": "goals",
        "selection": "over",
        "line": 2.5,
        "odds_aliases": ["odds_over_2_5"],
        "thresholds": {"goals_for_ft_avg_last_5": 1.0},
    }]
    signals = generate_signals(df, strategies)
    simulated = simulate_signals(signals, {"simulation": {"initial_bankroll": 100.0, "stake": 1.0}})
    curve = build_equity_curve(simulated)

    assert not curve.empty
    assert "bankroll_after" in curve.columns
    assert "drawdown" in curve.columns
