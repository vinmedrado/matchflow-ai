
from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from backend.core.logging_config import get_logger
from refinement.common import normalize_pct, safe_float, safe_int

logger = get_logger("matchflow.backtest.refinement.league_refiner")


class LeagueRefiner:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.min_trades = int(config.get("min_trades_for_candidate", 100))
        self.min_roi = float(config.get("min_roi_candidate", 0.02))
        self.min_pf = float(config.get("min_profit_factor_candidate", 1.10))

    def run(self, league_market_df: pd.DataFrame) -> pd.DataFrame:
        columns = ["league", "market", "total_trades", "roi", "win_rate", "profit_factor", "classification", "reason"]
        if league_market_df.empty:
            return pd.DataFrame(columns=columns)
        rows = []
        for _, row in league_market_df.iterrows():
            trades = safe_int(row.get("total_trades"))
            roi = normalize_pct(row.get("roi"))
            pf = safe_float(row.get("profit_factor"))
            if trades < self.min_trades:
                label, reason = "DISCARD", "LOW_SAMPLE"
            elif roi >= self.min_roi and pf >= self.min_pf:
                label, reason = "STRONG_CANDIDATE", "Positive ROI/PF with sufficient sample"
            elif roi >= 0 and pf >= 1:
                label, reason = "ACCEPTABLE", "Positive but not strong"
            elif roi > -0.02:
                label, reason = "WEAK", "Near neutral but weak"
            else:
                label, reason = "DISCARD", "Negative performance"
            rows.append({
                "league": row.get("league", ""),
                "market": row.get("market", ""),
                "total_trades": trades,
                "roi": round(roi, 6),
                "win_rate": normalize_pct(row.get("win_rate")),
                "profit_factor": round(pf, 6),
                "classification": label,
                "reason": reason,
            })
        out = pd.DataFrame(rows, columns=columns)
        logger.info("League refinement gerado: linhas=%s", len(out))
        return out
