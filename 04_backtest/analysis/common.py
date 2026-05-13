
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import pyarrow.parquet as pq

from backend.core.logging_config import get_logger

logger = get_logger("matchflow.backtest.analysis")


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_path(path: str | Path) -> Path:
    path_obj = Path(path)
    return path_obj if path_obj.is_absolute() else project_root() / path_obj


def safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0 or pd.isna(denominator):
        return 0.0
    return float(numerator) / float(denominator)


def clean_float(value: Any, digits: int = 6) -> float:
    if value is None or pd.isna(value):
        return 0.0
    if isinstance(value, float) and (math.isinf(value) or math.isnan(value)):
        return 0.0
    return round(float(value), digits)


def profit_factor(profits: pd.Series) -> float:
    gross_profit = float(profits[profits > 0].sum())
    gross_loss = abs(float(profits[profits < 0].sum()))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def max_drawdown_from_equity(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    curve = pd.to_numeric(equity, errors="coerce").ffill().fillna(0.0)
    running_max = curve.cummax()
    drawdown = curve - running_max
    return float(drawdown.min())


def max_losing_streak(results: pd.Series) -> int:
    max_streak = 0
    current = 0
    for value in results:
        is_loss = str(value).lower() in {"loss", "false", "0"} or value is False
        if is_loss:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return int(max_streak)


def compute_group_metrics(group: pd.DataFrame) -> Dict[str, Any]:
    total_trades = int(len(group))
    wins = int(group["is_win"].astype(bool).sum()) if "is_win" in group.columns else 0
    losses = total_trades - wins
    stake_total = float(group["stake"].sum()) if "stake" in group.columns else float(total_trades)
    total_profit = float(group["profit"].sum()) if "profit" in group.columns else 0.0
    avg_profit = safe_div(total_profit, total_trades)
    roi = safe_div(total_profit, stake_total)
    win_rate = safe_div(wins, total_trades)
    loss_rate = safe_div(losses, total_trades)
    avg_odds = float(pd.to_numeric(group.get("odd", pd.Series(dtype=float)), errors="coerce").mean()) if "odd" in group.columns else 0.0
    pf = profit_factor(pd.to_numeric(group.get("profit", pd.Series(dtype=float)), errors="coerce").fillna(0.0))
    if "equity_curve" in group.columns:
        max_dd = max_drawdown_from_equity(group["equity_curve"])
    elif "bankroll_after" in group.columns:
        max_dd = max_drawdown_from_equity(group["bankroll_after"])
    else:
        max_dd = 0.0
    return {
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": clean_float(win_rate),
        "loss_rate": clean_float(loss_rate),
        "stake_total": clean_float(stake_total),
        "total_profit": clean_float(total_profit),
        "avg_return": clean_float(avg_profit),
        "roi": clean_float(roi),
        "profit_factor": clean_float(pf),
        "max_drawdown": clean_float(max_dd),
        "avg_odds": clean_float(avg_odds),
    }


def load_backtest_inputs(
    detailed_path: str | Path = "data/backtest/results/detailed_results.parquet",
    summary_path: str | Path = "data/backtest/results/summary_results.csv",
    equity_path: str | Path = "data/backtest/results/equity_curve.csv",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    detailed_file = resolve_path(detailed_path)
    summary_file = resolve_path(summary_path)
    equity_file = resolve_path(equity_path)

    if not detailed_file.exists():
        raise FileNotFoundError(f"Detailed backtest results not found: {detailed_file}")

    detailed = pq.read_table(detailed_file).to_pandas()
    summary = pd.read_csv(summary_file) if summary_file.exists() else pd.DataFrame()
    equity = pd.read_csv(equity_file) if equity_file.exists() else pd.DataFrame()

    if detailed.empty:
        raise ValueError(f"Detailed backtest results are empty: {detailed_file}")

    detailed["date"] = pd.to_datetime(detailed.get("date"), errors="coerce")
    detailed = detailed.sort_values([col for col in ["date", "market", "strategy"] if col in detailed.columns]).reset_index(drop=True)

    logger.info(
        "Backtest inputs carregados: detailed_rows=%s summary_rows=%s equity_rows=%s",
        len(detailed),
        len(summary),
        len(equity),
    )
    return detailed, summary, equity
