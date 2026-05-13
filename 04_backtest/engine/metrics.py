from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from backend.core.logging_config import get_logger

logger = get_logger("matchflow.backtest.metrics")


SUMMARY_COLUMNS = [
    "strategy",
    "market",
    "total_trades",
    "win_rate",
    "loss_rate",
    "stake_total",
    "total_profit",
    "roi",
    "avg_return",
    "profit_factor",
    "max_drawdown",
    "win_streak",
    "loss_streak",
    "bankroll_start",
    "bankroll_end",
    "sharpe_ratio",
]


def calculate_summary(simulated: pd.DataFrame) -> pd.DataFrame:
    if simulated.empty:
        logger.warning("Resumo de backtest solicitado sem resultados simulados.")
        return pd.DataFrame(columns=SUMMARY_COLUMNS)

    summaries: List[Dict[str, Any]] = []

    for (strategy, market), group in simulated.groupby(["strategy", "market"], dropna=False):
        group = group.reset_index(drop=True)
        profits = group["profit"].astype(float)
        wins = group["is_win"].astype(bool)
        stakes = group["stake"].astype(float) if "stake" in group.columns else pd.Series([1.0] * len(group))
        total_trades = int(len(group))
        win_count = int(wins.sum())
        loss_count = int(total_trades - win_count)

        gross_profit = float(profits[profits > 0].sum())
        gross_loss = abs(float(profits[profits < 0].sum()))
        stake_total = float(stakes.sum())
        total_profit = float(profits.sum())
        bankroll_start = float(group["bankroll_before"].iloc[0]) if "bankroll_before" in group.columns else 0.0
        bankroll_end = bankroll_start + total_profit

        summaries.append({
            "strategy": strategy,
            "market": market,
            "total_trades": total_trades,
            "win_rate": round(win_count / total_trades, 4) if total_trades else 0.0,
            "loss_rate": round(loss_count / total_trades, 4) if total_trades else 0.0,
            "stake_total": round(stake_total, 6),
            "total_profit": round(total_profit, 6),
            "roi": round(total_profit / stake_total, 6) if stake_total > 0 else 0.0,
            "avg_return": round(float(profits.mean()), 6) if total_trades else 0.0,
            "profit_factor": round(gross_profit / gross_loss, 6) if gross_loss > 0 else None,
            "max_drawdown": round(_max_drawdown_from_bankroll(group), 6),
            "win_streak": int(_max_streak(wins.tolist(), True)),
            "loss_streak": int(_max_streak(wins.tolist(), False)),
            "bankroll_start": round(bankroll_start, 6),
            "bankroll_end": round(bankroll_end, 6),
            "sharpe_ratio": _sharpe_ratio(profits),
        })

    result = pd.DataFrame(summaries).sort_values(["market", "strategy"]).reset_index(drop=True)
    logger.info("Métricas financeiras calculadas para estratégias=%s", len(result))
    return result


def _max_drawdown_from_bankroll(group: pd.DataFrame) -> float:
    if "bankroll_after" in group.columns:
        equity = group["bankroll_after"].astype(float).reset_index(drop=True)
    else:
        equity = group["profit"].astype(float).cumsum().reset_index(drop=True)

    peak = equity.cummax()
    drawdown = equity - peak
    if drawdown.empty:
        return 0.0
    return float(drawdown.min())


def _sharpe_ratio(profits: pd.Series) -> float | None:
    if len(profits) < 2:
        return None

    std = float(profits.std(ddof=0))
    if std == 0:
        return None

    return round(float(profits.mean()) / std, 6)


def _max_streak(values: List[bool], target: bool) -> int:
    best = 0
    current = 0
    for value in values:
        if value is target:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best
