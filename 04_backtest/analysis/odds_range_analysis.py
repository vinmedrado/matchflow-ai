from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from .deep_performance_analyzer import compute_metrics
from backend.core.logging_config import get_logger

logger = get_logger("matchflow.backtest.odds_range_analysis")


def _range_label(low: float, high: float | None) -> str:
    return f"{low:.2f}+" if high is None else f"{low:.2f}-{high:.2f}"


def classify_odd(value: float, odds_ranges: List[List[float | None]]) -> str:
    try:
        odd = float(value)
    except (TypeError, ValueError):
        return "INVALID"

    for low, high in odds_ranges:
        low_float = float(low)
        if high is None and odd >= low_float:
            return _range_label(low_float, None)
        if high is not None and low_float <= odd <= float(high):
            return _range_label(low_float, float(high))
    return "OUT_OF_RANGE"


def build_market_odds_range_analysis(detailed: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    odds_ranges = config.get("odds_ranges", [[1.20, 1.49], [1.50, 1.79], [1.80, 2.09], [2.10, 2.49], [2.50, None]])
    working = detailed.copy()
    working["odds_range"] = working["odd"].apply(lambda value: classify_odd(value, odds_ranges))
    working = working[working["odds_range"] != "INVALID"].copy()

    rows: list[dict[str, object]] = []
    for (market, odds_range), group in working.groupby(["market", "odds_range"], dropna=False):
        metrics = compute_metrics(group.sort_values("date"))
        rows.append({"market": market, "odds_range": odds_range, **metrics})

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values(["market", "odds_range"]).reset_index(drop=True)

    logger.info("Análise por faixa de odds gerada: linhas=%s", len(result))
    return result
