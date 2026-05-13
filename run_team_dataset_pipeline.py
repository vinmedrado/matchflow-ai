from __future__ import annotations

import importlib.util
import logging
from pathlib import Path

from backend.core.logging_config import configure_logging, get_logger

PROJECT_ROOT = Path(__file__).resolve().parent
BUILDER_PATH = PROJECT_ROOT / "03_features" / "team_dataset_builder.py"

configure_logging()
logger = get_logger("matchflow.run_team_dataset_pipeline")


def load_builder():
    spec = importlib.util.spec_from_file_location("team_dataset_builder", BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load builder module from {BUILDER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    logger.info("=" * 72)
    logger.info("MATCHFLOW PATCH 2 - TEAM DATASET PIPELINE START")
    logger.info("Builder path: %s", BUILDER_PATH)
    try:
        module = load_builder()
        result = module.build_team_dataset(project_root=PROJECT_ROOT)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Team dataset pipeline failed: %s", exc)
        return 1

    logger.info("Team dataset pipeline completed successfully")
    logger.info("Input: %s", result.input_path)
    logger.info("Output: %s", result.output_path)
    logger.info("Report: %s", result.report_path)
    logger.info("Matches loaded: %s", result.matches_loaded)
    logger.info("Rows created: %s", result.rows_created)
    logger.info("Unique teams: %s", result.unique_teams)
    logger.info("Unique leagues: %s", result.unique_leagues)
    logger.info("Features created: %s", len(result.features_created))
    logger.info("Ignored source metrics: %s", result.ignored_features)
    logger.info("Anti-leakage: %s", "OK" if result.leakage_ok else "FAIL")
    logger.info("Execution time: %ss", result.execution_time_seconds)
    logger.info("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
