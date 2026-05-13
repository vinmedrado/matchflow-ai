
from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REFINEMENT_DIR = PROJECT_ROOT / "data" / "backtest" / "refinement"


def _load_runner():
    script = PROJECT_ROOT / "04_backtest" / "run_refinement.py"
    spec = importlib.util.spec_from_file_location("run_refinement_test", script)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_refinement_outputs_are_generated_and_non_empty_files():
    module = _load_runner()
    outputs = module.run_refinement()
    expected = [
        "refined_strategy_candidates.csv",
        "rejected_strategy_candidates.csv",
        "threshold_candidates.csv",
        "market_refinement_matrix.csv",
        "league_refinement_matrix.csv",
        "odds_refinement_matrix.csv",
        "refinement_risk_report.csv",
        "refinement_insights.txt",
    ]
    for filename in expected:
        path = REFINEMENT_DIR / filename
        assert path.exists(), filename
        assert path.stat().st_size > 0, filename
    assert "rejected_strategy_candidates" in outputs


def test_low_sample_strategy_is_rejected():
    df = pd.read_csv(REFINEMENT_DIR / "rejected_strategy_candidates.csv")
    assert not df.empty
    assert df["rejection_reasons"].str.contains("LOW_SAMPLE", regex=False).any()


def test_no_low_sample_strategy_is_marked_keep():
    risk = pd.read_csv(REFINEMENT_DIR / "refinement_risk_report.csv")
    if not risk.empty:
        bad = risk[(risk["sample_status"] == "LOW_SAMPLE") & (risk["final_recommendation"] == "KEEP")]
        assert bad.empty


def test_odds_range_classification_values_are_valid():
    df = pd.read_csv(REFINEMENT_DIR / "odds_refinement_matrix.csv")
    assert set(df["classification"]).issubset({"FAVORABLE", "NEUTRAL", "RISKY", "AVOID"})


def test_market_refinement_classification_values_are_valid():
    df = pd.read_csv(REFINEMENT_DIR / "market_refinement_matrix.csv")
    assert set(df["classification"]).issubset({"KEEP", "WATCH", "DISCARD"})


def test_refinement_insights_are_objective():
    text = (REFINEMENT_DIR / "refinement_insights.txt").read_text(encoding="utf-8")
    assert "Total de estratégias candidatas KEEP" in text
    assert "Estratégias rejeitadas" in text
    assert "Threshold candidates" not in text or "não otimiza" in text.lower()
