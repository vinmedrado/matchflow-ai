from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
BACKTEST_ROOT = PROJECT_ROOT / "04_backtest"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKTEST_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKTEST_ROOT))

from backend.core.logging_config import configure_logging, get_logger
from run_backtest import run_backtest

configure_logging()
logger = get_logger("matchflow.run_backtest_pipeline")


def main() -> None:
    logger.info("Executando pipeline de backtest multi-mercado")
    detailed, summary = run_backtest()
    logger.info("Pipeline finalizado: detailed_rows=%s summary_rows=%s", len(detailed), len(summary))


if __name__ == "__main__":
    main()
