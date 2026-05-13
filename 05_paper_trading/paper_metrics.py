from __future__ import annotations

from typing import Any, Dict

import pandas as pd


def calculate_max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    running_max = equity.cummax()
    drawdown = equity - running_max
    return float(drawdown.min()) if not drawdown.empty else 0.0


def calculate_profit_factor(results: pd.DataFrame) -> float:
    if results.empty or "profit" not in results.columns:
        return 0.0
    wins = float(results.loc[results["profit"] > 0, "profit"].sum())
    losses = abs(float(results.loc[results["profit"] < 0, "profit"].sum()))
    if losses == 0:
        return wins if wins > 0 else 0.0
    return wins / losses


def build_summary(signals: pd.DataFrame, results: pd.DataFrame, equity: pd.DataFrame, initial_bankroll: float) -> Dict[str, Any]:
    total_signals = int(len(signals))
    settled_signals = int(len(results))
    pending_signals = max(total_signals - settled_signals, 0)
    wins = int(results["is_win"].sum()) if not results.empty and "is_win" in results.columns else 0
    total_profit = float(results["profit"].sum()) if not results.empty and "profit" in results.columns else 0.0
    total_stake = float(results["stake"].sum()) if not results.empty and "stake" in results.columns else 0.0
    current_bankroll = float(equity["bankroll"].iloc[-1]) if not equity.empty and "bankroll" in equity.columns else float(initial_bankroll + total_profit)
    win_rate = wins / settled_signals if settled_signals > 0 else 0.0
    roi = total_profit / total_stake if total_stake > 0 else 0.0
    max_drawdown = calculate_max_drawdown(equity["bankroll"]) if not equity.empty and "bankroll" in equity.columns else 0.0

    return {
        "paper_only": True,
        "total_signals": total_signals,
        "settled_signals": settled_signals,
        "pending_signals": pending_signals,
        "win_rate": round(win_rate, 6),
        "ROI": round(roi, 6),
        "roi": round(roi, 6),
        "profit_factor": round(calculate_profit_factor(results), 6),
        "max_drawdown": round(max_drawdown, 6),
        "initial_bankroll": round(float(initial_bankroll), 6),
        "current_bankroll": round(current_bankroll, 6),
        "total_profit": round(total_profit, 6),
        "total_stake": round(total_stake, 6),
    }
