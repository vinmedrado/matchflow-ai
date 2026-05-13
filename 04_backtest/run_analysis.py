
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

from analysis.performance_analyzer import BacktestPerformanceAnalyzer
from backend.core.logging_config import configure_logging, get_logger

configure_logging()
logger = get_logger("matchflow.backtest.run_analysis")


def run_analysis() -> Dict[str, pd.DataFrame]:
    logger.info("Executando análise de performance de backtest")
    analyzer = BacktestPerformanceAnalyzer()
    outputs = analyzer.run()
    logger.info(
        "Análise concluída: market=%s league=%s strategies=%s",
        len(outputs.get("market_performance", [])),
        len(outputs.get("league_performance", [])),
        len(outputs.get("strategy_ranking", [])),
    )
    return outputs


def main() -> None:
    run_analysis()


if __name__ == "__main__":
    main()
