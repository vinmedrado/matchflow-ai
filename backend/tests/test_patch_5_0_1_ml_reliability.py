from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_dataset_builder_uses_future_target_shift() -> None:
    source = _read("06_ml/dataset_builder.py")
    assert "X(t) -> y(t+1)" in source or "X_t_to_y_t_plus_1" in source
    assert "shift(-self.horizon)" in source
    assert "groupby(\"team_key\"" in source


def test_model_trainer_uses_walk_forward_validation() -> None:
    source = _read("06_ml/model_trainer.py")
    assert "_walk_forward_splits" in source
    assert "validation\": \"walk_forward\"" in source
    assert "train_df[\"date\"].max() <= test_df[\"date\"].min()" in source


def test_evaluator_has_calibration_metrics() -> None:
    source = _read("06_ml/evaluator.py")
    assert "brier_score" in source
    assert "calibration_error" in source
    assert "probability_distribution" in source


def test_predictions_are_enriched_with_market_odds_and_strategy() -> None:
    source = _read("06_ml/model_trainer.py")
    assert "pred_df[\"market\"]" in source
    assert "pred_df[\"odds\"]" in source
    assert "pred_df[\"strategy_associated\"]" in source
    assert "research_only" in source


def test_ml_vs_rules_comparison_is_created() -> None:
    source = _read("06_ml/model_trainer.py")
    assert "ml_vs_rules_comparison.csv" in source
    assert "_build_comparison_records" in source
    assert "ML probabilities are not operational signals" in source


def test_feature_selector_excludes_targets_and_current_outcomes() -> None:
    source = _read("06_ml/feature_selector.py")
    assert "LEAKAGE_PREFIXES" in source
    assert "target_" in source
    assert "SAFE_PATTERNS" in source
    assert "goals_for_ft" in source
    assert "corners_for" in source


def test_versions_are_5_0_1() -> None:
    app = json.loads((ROOT / "config/app_config.json").read_text(encoding="utf-8"))
    pkg = json.loads((ROOT / "frontend/package.json").read_text(encoding="utf-8"))
    assert app["app"]["version"] == "5.0.1"
    assert pkg["version"] == "5.0.1"


def test_no_operational_ml_signal_generation() -> None:
    ml_files = [
        "06_ml/dataset_builder.py",
        "06_ml/model_trainer.py",
        "06_ml/evaluator.py",
        "06_ml/feature_selector.py",
    ]
    forbidden = ["place_bet", "stake", "bankroll_update", "send_signal_to_bookmaker"]
    combined = "\n".join(_read(path) for path in ml_files)
    for term in forbidden:
        assert term not in combined
