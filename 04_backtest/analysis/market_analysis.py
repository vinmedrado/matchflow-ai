
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .common import clean_float, compute_group_metrics, resolve_path
from backend.core.logging_config import get_logger

logger = get_logger("matchflow.backtest.market_analysis")


def build_market_performance(detailed: pd.DataFrame, output_path: str | Path = "data/backtest/analysis/market_performance.csv") -> pd.DataFrame:
    if "market" not in detailed.columns:
        raise ValueError("Column 'market' is required for market performance analysis.")

    rows = []
    for market, group in detailed.groupby("market", dropna=False):
        metrics = compute_group_metrics(group)
        metrics["market"] = str(market)
        rows.append(metrics)

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values(["roi", "profit_factor", "total_trades"], ascending=[False, False, False]).reset_index(drop=True)
        result["roi_percent"] = result["roi"].apply(lambda value: clean_float(value * 100))

    output_file = resolve_path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_file, index=False)

    logger.info("Market performance salvo: %s | linhas=%s", output_file, len(result))
    return result
