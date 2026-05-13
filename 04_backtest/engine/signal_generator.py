from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence, Tuple

import pandas as pd

from backend.core.logging_config import get_logger

logger = get_logger("matchflow.backtest.signal_generator")


IDENTITY_COLUMNS = [
    "event_id",
    "match_key",
    "date",
    "league",
    "season",
    "team_key",
    "team_name",
    "opponent_key",
    "opponent_name",
    "side",
]


CURRENT_RESULT_COLUMNS = [
    "goals_for_ft",
    "goals_against_ft",
    "total_goals_ft",
    "shots_for",
    "shots_against",
    "corners_for",
    "corners_against",
]


def _value(row: pd.Series, column: str) -> float | None:
    if column not in row.index:
        return None
    value = row[column]
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _passes_thresholds(row: pd.Series, thresholds: Dict[str, Any]) -> bool:
    for column, threshold in thresholds.items():
        if column.endswith("_max"):
            base_column = column[:-4]
            value = _value(row, base_column)
            if value is None or value > float(threshold):
                return False
            continue

        value = _value(row, column)
        if value is None or value < float(threshold):
            return False
    return True


def _resolve_odd(row: pd.Series, aliases: Sequence[str], min_odds: float) -> Tuple[float | None, str | None]:
    """Resolve the first valid odd available for a market.

    Trades without real odds are ignored. This keeps the backtest financial
    and prevents synthetic profit assumptions.
    """

    for column in aliases:
        if column not in row.index:
            continue

        odd = _value(row, column)
        if odd is None:
            continue

        if odd < min_odds:
            return None, column

        return odd, column

    return None, None


def generate_signals(
    df: pd.DataFrame,
    strategies: Iterable[Dict[str, Any]],
    min_odds: float = 1.2,
) -> pd.DataFrame:
    """Generate candidate trades using shifted historical features and real odds.

    This function does not calculate historical features and does not use future
    rows. It reads only already-shifted feature columns and current-row market
    outcome columns needed to settle the trade. If a valid odd is unavailable,
    the candidate signal is ignored.
    """

    if df.empty:
        logger.warning("Dataset avançado vazio recebido para geração de sinais.")
        return pd.DataFrame()

    signals: List[Dict[str, Any]] = []
    strategy_list = list(strategies)
    ignored_no_odds = 0
    ignored_thresholds = 0

    logger.info(
        "Iniciando geração de sinais financeiros: linhas=%s estratégias=%s min_odds=%s",
        len(df),
        len(strategy_list),
        min_odds,
    )

    for _, row in df.iterrows():
        for strategy in strategy_list:
            thresholds = strategy.get("thresholds", {})
            if not _passes_thresholds(row, thresholds):
                ignored_thresholds += 1
                continue

            odds_aliases = strategy.get("odds_aliases", [])
            odd, odds_column = _resolve_odd(row, odds_aliases, min_odds=min_odds)
            if odd is None:
                ignored_no_odds += 1
                continue

            signal = {column: row.get(column) for column in IDENTITY_COLUMNS if column in row.index}
            signal.update({
                "strategy": strategy["strategy"],
                "market": strategy["market"],
                "selection": strategy.get("selection"),
                "line": strategy.get("line"),
                "odd": float(odd),
                "odds_column": odds_column,
                "signal_strength": _signal_strength(row, thresholds),
            })

            for current_col in CURRENT_RESULT_COLUMNS:
                if current_col in row.index:
                    signal[current_col] = row.get(current_col)

            signals.append(signal)

    result = pd.DataFrame(signals)
    logger.info(
        "Sinais financeiros gerados: %s | ignorados_sem_odds=%s | ignorados_threshold=%s",
        len(result),
        ignored_no_odds,
        ignored_thresholds,
    )
    return result


def _signal_strength(row: pd.Series, thresholds: Dict[str, Any]) -> float:
    if not thresholds:
        return 0.0

    scores: List[float] = []
    for column, threshold in thresholds.items():
        if column.endswith("_max"):
            continue
        value = _value(row, column)
        if value is None:
            continue
        threshold_float = float(threshold)
        if threshold_float == 0:
            continue
        scores.append(value / threshold_float)

    if not scores:
        return 0.0
    return round(float(sum(scores) / len(scores)), 4)
