from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKTEST_ROOT = PROJECT_ROOT / "04_backtest"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKTEST_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKTEST_ROOT))

from analysis.deep_performance_analyzer import DeepPerformanceAnalyzer
from analysis.odds_range_analysis import classify_odd
from analysis.temporal_analysis import build_rolling_roi_analysis


def test_low_sample_strategy_is_never_reliable():
    analyzer = DeepPerformanceAnalyzer()
    data = pd.DataFrame(
        {
            "strategy": ["s1"] * 3,
            "market": ["goals"] * 3,
            "league": ["L"] * 3,
            "date": pd.date_range("2024-01-01", periods=3),
            "profit": [1.0, 1.0, -1.0],
            "stake": [1.0, 1.0, 1.0],
            "odd": [2.0, 2.0, 2.0],
            "is_win": [True, True, False],
        }
    )
    result = analyzer.build_qualified_strategies(data)
    assert result.iloc[0]["sample_class"] == "LOW_SAMPLE"
    assert bool(result.iloc[0]["is_edge_reliable"]) is False


def test_odds_ranges_classify_correctly():
    ranges = [[1.20, 1.49], [1.50, 1.79], [1.80, 2.09], [2.10, 2.49], [2.50, None]]
    assert classify_odd(1.20, ranges) == "1.20-1.49"
    assert classify_odd(1.75, ranges) == "1.50-1.79"
    assert classify_odd(2.90, ranges) == "2.50+"
    assert classify_odd("bad", ranges) == "INVALID"


def test_rolling_roi_calculates_expected_window():
    data = pd.DataFrame(
        {
            "strategy": ["s1"] * 4,
            "market": ["goals"] * 4,
            "date": pd.date_range("2024-01-01", periods=4),
            "profit": [1.0, -1.0, 1.0, 1.0],
            "stake": [1.0, 1.0, 1.0, 1.0],
            "odd": [2.0] * 4,
            "is_win": [True, False, True, True],
        }
    )
    result = build_rolling_roi_analysis(data, {"rolling_windows": [2]})
    assert result.iloc[0]["windows_count"] == 3
    assert result.iloc[0]["rolling_roi_min"] == 0.0
    assert result.iloc[0]["rolling_roi_max"] == 1.0


def test_generated_deep_files_are_not_empty():
    analyzer = DeepPerformanceAnalyzer()
    outputs = analyzer.run()
    for name, df in outputs.items():
        assert not df.empty, name

    deep_dir = PROJECT_ROOT / "data/backtest/analysis/deep"
    expected = [
        "qualified_strategies.csv",
        "market_odds_range_analysis.csv",
        "league_market_matrix.csv",
        "temporal_performance.csv",
        "rolling_roi_analysis.csv",
        "consistency_score.csv",
        "risk_flags.csv",
        "deep_insights.txt",
    ]
    for filename in expected:
        path = deep_dir / filename
        assert path.exists(), filename
        assert path.stat().st_size > 0, filename


def test_consistency_score_between_zero_and_100():
    analyzer = DeepPerformanceAnalyzer()
    analyzer.run()
    df = pd.read_csv(PROJECT_ROOT / "data/backtest/analysis/deep/consistency_score.csv")
    assert ((df["consistency_score"] >= 0) & (df["consistency_score"] <= 100)).all()


def test_risk_flags_include_low_sample_or_overfitting():
    analyzer = DeepPerformanceAnalyzer()
    analyzer.run()
    flags = pd.read_csv(PROJECT_ROOT / "data/backtest/analysis/deep/risk_flags.csv")
    assert "flag" in flags.columns
    assert {"LOW_SAMPLE_SIZE", "POSSIBLE_OVERFITTING"}.intersection(set(flags["flag"]))


def test_deep_analysis_endpoint_works():
    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)
    login = client.post("/api/auth/login", json={"email": "admin@matchflow.local", "password": "admin123"})
    token = login.json()["access_token"]
    response = client.get("/api/backtest/deep-analysis-summary", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["deep_analysis_available"] is True
    assert "risk_flags_count" in payload["data"]
