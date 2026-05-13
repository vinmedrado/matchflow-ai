
from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from backend.core.logging_config import get_logger
from refinement.common import safe_int

logger = get_logger("matchflow.backtest.refinement.threshold_refiner")


class ThresholdRefiner:
    """Suggest candidate filters without automatic optimization.

    The suggestions are evidence summaries only. They do not modify strategies,
    thresholds, bankroll rules or backtest calculation.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        self.min_sample = max(25, int(config.get("min_trades_for_candidate", 100)) // 2)

    def run(self, odds_matrix: pd.DataFrame, league_matrix: pd.DataFrame, consistency_df: pd.DataFrame) -> pd.DataFrame:
        columns = ["strategy", "market", "suggested_filter", "reason", "expected_risk", "supporting_sample_size"]
        rows: List[Dict[str, Any]] = []

        favorable_odds = odds_matrix[odds_matrix.get("classification", "") == "FAVORABLE"] if not odds_matrix.empty else pd.DataFrame()
        for _, row in favorable_odds.iterrows():
            rows.append({
                "strategy": "ANY_STRATEGY_IN_MARKET",
                "market": row.get("market", ""),
                "suggested_filter": f"odds_range={row.get('odds_range', '')}",
                "reason": f"Odds band classified as FAVORABLE; ROI={row.get('roi', 0)} PF={row.get('profit_factor', 0)}",
                "expected_risk": "MEDIUM" if safe_int(row.get("total_trades")) < 100 else "LOW",
                "supporting_sample_size": safe_int(row.get("total_trades")),
            })

        strong_leagues = league_matrix[league_matrix.get("classification", "") == "STRONG_CANDIDATE"] if not league_matrix.empty else pd.DataFrame()
        for _, row in strong_leagues.iterrows():
            rows.append({
                "strategy": "ANY_STRATEGY_IN_MARKET",
                "market": row.get("market", ""),
                "suggested_filter": f"league={row.get('league', '')}",
                "reason": f"League-market pair classified as STRONG_CANDIDATE; ROI={row.get('roi', 0)} PF={row.get('profit_factor', 0)}",
                "expected_risk": "MEDIUM" if safe_int(row.get("total_trades")) < 100 else "LOW",
                "supporting_sample_size": safe_int(row.get("total_trades")),
            })

        if not consistency_df.empty:
            top_consistency = consistency_df.sort_values(["consistency_score", "total_trades"], ascending=[False, False]).head(5)
            for _, row in top_consistency.iterrows():
                rows.append({
                    "strategy": row.get("strategy", ""),
                    "market": row.get("market", ""),
                    "suggested_filter": "manual_review_required",
                    "reason": f"High consistency score candidate; score={row.get('consistency_score', 0)}",
                    "expected_risk": "HIGH" if safe_int(row.get("total_trades")) < self.min_sample else "MEDIUM",
                    "supporting_sample_size": safe_int(row.get("total_trades")),
                })

        out = pd.DataFrame(rows, columns=columns).drop_duplicates()
        logger.info("Threshold candidates gerados sem otimização automática: linhas=%s", len(out))
        return out
