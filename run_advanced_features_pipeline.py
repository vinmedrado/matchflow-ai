from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

from backend.core.logging_config import configure_logging, get_logger

PROJECT_ROOT = Path(__file__).resolve().parent
BUILDER_PATH = PROJECT_ROOT / "03_features" / "advanced_features_builder.py"

configure_logging()
logger = get_logger("matchflow.run_advanced_features_pipeline")


EXPECTED_OUTPUT_COLUMNS = [
    "win_streak",
    "loss_streak",
    "unbeaten_streak",
    "points_last_5",
    "points_trend",
    "goals_std_last_5",
    "shots_std_last_5",
    "corners_std_last_5",
    "goals_vs_league_avg",
    "shots_vs_league_avg",
    "corners_vs_league_avg",
    "goals_per_shot",
    "goals_per_shot_on_target",
    "shots_on_target_ratio",
    "pressure_index",
    "pressure_avg_last_5",
    "attack_vs_defense_ratio",
    "team_attack_strength",
    "opponent_defense_weakness",
    "goal_trend",
    "expected_goals_proxy",
    "corners_trend",
    "high_corner_flag",
    "high_shots_flag",
    "low_conversion_flag",
]


def validate_generated_output(output_path: Path) -> None:
    if not output_path.exists():
        raise FileNotFoundError(f"Advanced dataset was not generated: {output_path}")
    if output_path.stat().st_size == 0:
        raise ValueError(f"Advanced dataset was generated but is empty: {output_path}")

    df = safe_read_dataframe(output_path)
    if df.empty:
        raise ValueError("Advanced dataset parquet contains zero rows.")

    missing = [column for column in EXPECTED_OUTPUT_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Advanced dataset missing expected columns: {missing}")

    logger.info(
        "Advanced dataset output validation OK: linhas=%s colunas=%s path=%s",
        len(df),
        len(df.columns),
        output_path,
    )



def load_builder():
    spec = importlib.util.spec_from_file_location("advanced_features_builder", BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load advanced features builder from {BUILDER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    logger.info("=" * 72)
    logger.info("MATCHFLOW PATCH 3.0 - ADVANCED FEATURES PIPELINE START")
    logger.info("Builder path: %s", BUILDER_PATH)
    try:
        module = load_builder()
        result = module.build_advanced_features(project_root=PROJECT_ROOT)
        validate_generated_output(result.output_path)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Advanced features pipeline failed: %s", exc)
        return 1

    logger.info("Advanced features pipeline completed successfully")
    logger.info("Input: %s", result.input_path)
    logger.info("Output: %s", result.output_path)
    logger.info("Report: %s", result.report_path)
    logger.info("Rows created: %s", result.rows_created)
    logger.info("Features created: %s", result.total_features_created)
    logger.info("Anti-leakage: %s", "OK" if result.leakage_ok else "FAIL")
    logger.info("Execution time: %ss", result.execution_time_seconds)
    logger.info("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
