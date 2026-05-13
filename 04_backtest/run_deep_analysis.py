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

from analysis.deep_performance_analyzer import DeepPerformanceAnalyzer
from backend.core.logging_config import configure_logging, get_logger

configure_logging()
logger = get_logger("matchflow.backtest.run_deep_analysis")


def run_deep_analysis() -> Dict[str, pd.DataFrame]:
    logger.info("Executando deep analysis de performance")
    analyzer = DeepPerformanceAnalyzer()
    outputs = analyzer.run()
    logger.info(
        "Deep analysis concluída: qualified=%s risk_flags=%s consistency=%s",
        len(outputs.get("qualified_strategies", [])),
        len(outputs.get("risk_flags", [])),
        len(outputs.get("consistency_score", [])),
    )
    return outputs


def main() -> None:
    run_deep_analysis()


if __name__ == "__main__":
    main()
