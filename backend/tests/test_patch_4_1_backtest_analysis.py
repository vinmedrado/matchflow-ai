
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def test_backtest_analysis_files_exist_and_are_not_empty():
    analysis_dir = ROOT / "data/backtest/analysis"

    expected_files = [
        "market_performance.csv",
        "league_performance.csv",
        "strategy_ranking.csv",
        "drawdown_analysis.csv",
        "equity_analysis.csv",
        "insights.txt",
    ]

    for file_name in expected_files:
        path = analysis_dir / file_name
        assert path.exists(), f"Missing analysis output: {path}"
        assert path.stat().st_size > 0, f"Empty analysis output: {path}"


def test_market_performance_metrics_are_consistent():
    path = ROOT / "data/backtest/analysis/market_performance.csv"
    df = pd.read_csv(path)

    required_columns = {
        "market",
        "total_trades",
        "win_rate",
        "roi",
        "profit_factor",
        "max_drawdown",
        "avg_odds",
    }

    assert required_columns.issubset(df.columns)
    assert not df.empty
    assert (df["total_trades"] > 0).all()
    assert df["win_rate"].between(0, 1).all()


def test_strategy_ranking_is_ordered_by_roi_and_profit_factor():
    path = ROOT / "data/backtest/analysis/strategy_ranking.csv"
    df = pd.read_csv(path)

    assert not df.empty
    assert "rank" in df.columns
    assert "roi" in df.columns
    assert "profit_factor" in df.columns

    ordered = df.sort_values(
        ["roi", "profit_factor", "consistency_score", "total_trades"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)

    assert df["strategy"].tolist() == ordered["strategy"].tolist()
    assert df["rank"].tolist() == list(range(1, len(df) + 1))


def test_insights_contains_clear_performance_intelligence():
    path = ROOT / "data/backtest/analysis/insights.txt"
    content = path.read_text(encoding="utf-8")

    assert "Melhor mercado" in content
    assert "Pior mercado" in content
    assert "Ligas mais lucrativas" in content
    assert "Alerta de risco" in content
