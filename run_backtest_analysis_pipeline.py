
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
from run_analysis import run_analysis

configure_logging()
logger = get_logger("matchflow.run_backtest_analysis_pipeline")


def main() -> None:
    logger.info("Iniciando pipeline de análise de backtest")
    outputs = run_analysis()
    logger.info("Pipeline de análise finalizado: outputs=%s", list(outputs.keys()))


if __name__ == "__main__":
    main()
