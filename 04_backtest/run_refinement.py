
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKTEST_ROOT = Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKTEST_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKTEST_ROOT))

from backend.core.logging_config import configure_logging, get_logger
from refinement.strategy_refinement_pipeline import StrategyRefinementPipeline

configure_logging()
logger = get_logger("matchflow.backtest.run_refinement")


def run_refinement() -> Dict[str, pd.DataFrame]:
    logger.info("Executando pipeline de refinamento estratégico")
    pipeline = StrategyRefinementPipeline(PROJECT_ROOT)
    outputs = pipeline.run()
    logger.info("Pipeline de refinamento concluído")
    return outputs


def main() -> None:
    run_refinement()


if __name__ == "__main__":
    main()
