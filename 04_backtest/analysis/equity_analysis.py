
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .common import clean_float, max_drawdown_from_equity, resolve_path, safe_div
from backend.core.logging_config import get_logger

logger = get_logger("matchflow.backtest.equity_analysis")


def build_equity_analysis(
    detailed: pd.DataFrame,
    equity: pd.DataFrame,
    output_path: str | Path = "data/backtest/analysis/equity_analysis.csv",
) -> pd.DataFrame:
    if equity is not None and not equity.empty:
        source = equity.copy()
    else:
        source = detailed.copy()

    if source.empty:
        result = pd.DataFrame()
    else:
        date_col = "date" if "date" in source.columns else None
        equity_col = _detect_equity_column(source)
        if equity_col is None:
            result = pd.DataFrame()
        else:
            source[equity_col] = pd.to_numeric(source[equity_col], errors="coerce")
            source = source.dropna(subset=[equity_col]).reset_index(drop=True)
            first_equity = float(source[equity_col].iloc[0]) if not source.empty else 0.0
            last_equity = float(source[equity_col].iloc[-1]) if not source.empty else 0.0
            growth = last_equity - first_equity
            cumulative_return = safe_div(growth, first_equity)
            returns = source[equity_col].pct_change().replace([float("inf"), -float("inf")], 0).fillna(0)
            result = pd.DataFrame([{
                "initial_equity": clean_float(first_equity),
                "final_equity": clean_float(last_equity),
                "equity_growth": clean_float(growth),
                "cumulative_return": clean_float(cumulative_return),
                "volatility": clean_float(float(returns.std(ddof=0)) if len(returns) > 1 else 0.0),
                "max_drawdown": clean_float(max_drawdown_from_equity(source[equity_col])),
                "total_points": int(len(source)),
                "start_date": str(pd.to_datetime(source[date_col]).min().date()) if date_col and date_col in source.columns else None,
                "end_date": str(pd.to_datetime(source[date_col]).max().date()) if date_col and date_col in source.columns else None,
            }])

    output_file = resolve_path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_file, index=False)

    logger.info("Equity analysis salvo: %s | linhas=%s", output_file, len(result))
    return result


def _detect_equity_column(df: pd.DataFrame) -> str | None:
    for candidate in ["equity_curve", "bankroll_after", "bankroll"]:
        if candidate in df.columns:
            return candidate
    return None
