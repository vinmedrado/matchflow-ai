from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from backend.core.logging_config import configure_logging, get_logger
from backend.core.storage import safe_write_dataframe
from backend.services.data_engine.providers.flashscore import run_flashscore_sync

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config" / "data_engine_config.json"

configure_logging()
logger = get_logger("matchflow.run_data_engine_pipeline")


def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    logger.info("MATCHFLOW DATA ENGINE PIPELINE START")
    try:
        config = load_config()
        result = run_flashscore_sync()
        output_path = ROOT / config.get("processed_output_path", "data/processed/data_engine_base.parquet")
        records = result.get("records") or result.get("matches") or []
        if records:
            import pandas as pd
            df = pd.DataFrame(records)
            safe_write_dataframe(df, output_path, also_write_csv=True)
        logger.info("Internal FlashScore provider completed: %s", result)
        return 0 if result.get("ok", True) else 1
    except Exception as exc:  # noqa: BLE001
        logger.exception("DATA ENGINE PIPELINE FAILED: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
