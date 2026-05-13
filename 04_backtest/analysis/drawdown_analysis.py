
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .common import clean_float, max_drawdown_from_equity, max_losing_streak, resolve_path
from backend.core.logging_config import get_logger

logger = get_logger("matchflow.backtest.drawdown_analysis")


def _worst_drawdown_period(df: pd.DataFrame) -> tuple[str | None, str | None, float]:
    if df.empty:
        return None, None, 0.0

    equity_col = "equity_curve" if "equity_curve" in df.columns else "bankroll_after"
    if equity_col not in df.columns:
        return None, None, 0.0

    ordered = df.sort_values("date").reset_index(drop=True).copy()
    ordered[equity_col] = pd.to_numeric(ordered[equity_col], errors="coerce").ffill()
    ordered["running_max"] = ordered[equity_col].cummax()
    ordered["drawdown"] = ordered[equity_col] - ordered["running_max"]

    if ordered["drawdown"].empty:
        return None, None, 0.0

    trough_idx = int(ordered["drawdown"].idxmin())
    peak_candidates = ordered.loc[:trough_idx]
    if peak_candidates.empty:
        return None, None, clean_float(ordered.loc[trough_idx, "drawdown"])

    peak_idx = int(peak_candidates[equity_col].idxmax())
    start = ordered.loc[peak_idx, "date"]
    end = ordered.loc[trough_idx, "date"]
    return str(pd.to_datetime(start).date()) if pd.notna(start) else None, str(pd.to_datetime(end).date()) if pd.notna(end) else None, clean_float(ordered.loc[trough_idx, "drawdown"])


def build_drawdown_analysis(detailed: pd.DataFrame, output_path: str | Path = "data/backtest/analysis/drawdown_analysis.csv") -> pd.DataFrame:
    rows = []

    group_cols = ["market", "strategy"]
    for keys, group in detailed.groupby(group_cols, dropna=False):
        start, end, max_dd = _worst_drawdown_period(group)
        rows.append({
            "market": str(keys[0]),
            "strategy": str(keys[1]),
            "max_drawdown": clean_float(max_dd),
            "worst_period_start": start,
            "worst_period_end": end,
            "max_losing_streak": max_losing_streak(group.get("result", pd.Series(dtype=str))),
            "recovery_after_worst_drawdown": _calculate_recovery(group, end),
        })

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values(["max_drawdown", "max_losing_streak"], ascending=[True, False]).reset_index(drop=True)

    output_file = resolve_path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_file, index=False)

    logger.info("Drawdown analysis salvo: %s | linhas=%s", output_file, len(result))
    return result


def _calculate_recovery(group: pd.DataFrame, trough_date: str | None) -> str:
    if trough_date is None or group.empty:
        return "unknown"

    equity_col = "equity_curve" if "equity_curve" in group.columns else "bankroll_after"
    if equity_col not in group.columns:
        return "unknown"

    ordered = group.sort_values("date").reset_index(drop=True).copy()
    ordered[equity_col] = pd.to_numeric(ordered[equity_col], errors="coerce").ffill()
    trough_ts = pd.to_datetime(trough_date, errors="coerce")
    if pd.isna(trough_ts):
        return "unknown"

    before = ordered[ordered["date"] <= trough_ts]
    after = ordered[ordered["date"] > trough_ts]

    if before.empty or after.empty:
        return "not_recovered"

    previous_peak = float(before[equity_col].cummax().max())
    recovered = after[after[equity_col] >= previous_peak]
    if recovered.empty:
        return "not_recovered"

    recovery_date = pd.to_datetime(recovered.iloc[0]["date"]).date()
    return str(recovery_date)
