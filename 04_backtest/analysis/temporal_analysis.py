from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from .deep_performance_analyzer import compute_metrics
from backend.core.logging_config import get_logger

logger = get_logger("matchflow.backtest.temporal_analysis")


def _period_rows(detailed: pd.DataFrame, period_type: str, period_values: pd.Series) -> List[Dict[str, Any]]:
    working = detailed.copy()
    working["period"] = period_values.astype(str)
    rows: List[Dict[str, Any]] = []

    for (period, strategy, market), group in working.groupby(["period", "strategy", "market"], dropna=False):
        metrics = compute_metrics(group.sort_values("date"))
        rows.append({
            "period_type": period_type,
            "period": period,
            "strategy": strategy,
            "market": market,
            "trades": metrics["total_trades"],
            "roi": metrics["roi"],
            "profit": metrics["total_profit"],
            "drawdown": metrics["max_drawdown"],
            "win_rate": metrics["win_rate"],
        })
    return rows


def build_temporal_performance(detailed: pd.DataFrame) -> pd.DataFrame:
    working = detailed.dropna(subset=["date"]).copy()
    if working.empty:
        return pd.DataFrame(columns=["period_type", "period", "strategy", "market", "trades", "roi", "profit", "drawdown", "win_rate"])

    rows: List[Dict[str, Any]] = []
    rows.extend(_period_rows(working, "month", working["date"].dt.to_period("M")))
    rows.extend(_period_rows(working, "quarter", working["date"].dt.to_period("Q")))
    rows.extend(_period_rows(working, "year", working["date"].dt.year.astype(str)))

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values(["period_type", "period", "strategy", "market"]).reset_index(drop=True)

    logger.info("Análise temporal gerada: linhas=%s", len(result))
    return result


def build_rolling_roi_analysis(detailed: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
    windows = [int(window) for window in config.get("rolling_windows", [25, 50, 100])]
    rows: List[Dict[str, Any]] = []

    for (strategy, market), group in detailed.sort_values("date").groupby(["strategy", "market"], dropna=False):
        group = group.sort_values("date").reset_index(drop=True)
        for window in windows:
            rolling_profit = group["profit"].rolling(window=window, min_periods=window).sum()
            rolling_stake = group["stake"].rolling(window=window, min_periods=window).sum()
            rolling_roi = rolling_profit / rolling_stake.replace(0, pd.NA)
            valid = rolling_roi.dropna()

            if valid.empty:
                rows.append({
                    "strategy": strategy,
                    "market": market,
                    "window": window,
                    "windows_count": 0,
                    "rolling_roi_mean": 0.0,
                    "rolling_roi_min": 0.0,
                    "rolling_roi_max": 0.0,
                    "rolling_roi_std": 0.0,
                    "negative_windows_pct": 1.0,
                })
                continue

            rows.append({
                "strategy": strategy,
                "market": market,
                "window": window,
                "windows_count": int(len(valid)),
                "rolling_roi_mean": round(float(valid.mean()), 6),
                "rolling_roi_min": round(float(valid.min()), 6),
                "rolling_roi_max": round(float(valid.max()), 6),
                "rolling_roi_std": round(float(valid.std(ddof=0)), 6),
                "negative_windows_pct": round(float((valid < 0).mean()), 6),
            })

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values(["strategy", "market", "window"]).reset_index(drop=True)

    logger.info("Rolling ROI analysis gerada: linhas=%s", len(result))
    return result
