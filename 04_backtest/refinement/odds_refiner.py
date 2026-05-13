
from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from backend.core.logging_config import get_logger
from refinement.common import normalize_pct, safe_float, safe_int

logger = get_logger("matchflow.backtest.refinement.odds_refiner")


class OddsRefiner:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.min_trades = max(25, int(config.get("min_trades_for_candidate", 100)) // 2)
        self.min_roi = float(config.get("min_roi_candidate", 0.02))
        self.min_pf = float(config.get("min_profit_factor_candidate", 1.10))

    def run(self, odds_df: pd.DataFrame) -> pd.DataFrame:
        columns = ["market", "odds_range", "total_trades", "roi", "profit_factor", "avg_profit", "classification", "reason"]
        if odds_df.empty:
            return pd.DataFrame(columns=columns)
        rows = []
        for _, row in odds_df.iterrows():
            trades = safe_int(row.get("total_trades"))
            roi = normalize_pct(row.get("roi"))
            pf = safe_float(row.get("profit_factor"))
            avg_profit = safe_float(row.get("avg_profit"))
            if trades < self.min_trades:
                label, reason = "AVOID", "LOW_SAMPLE"
            elif roi >= self.min_roi and pf >= self.min_pf and avg_profit > 0:
                label, reason = "FAVORABLE", "Positive ROI/PF/avg profit with enough trades"
            elif roi >= 0 and pf >= 1:
                label, reason = "NEUTRAL", "Positive but not strong"
            elif roi > -0.03:
                label, reason = "RISKY", "Weak or unstable odds band"
            else:
                label, reason = "AVOID", "Negative odds band"
            rows.append({
                "market": row.get("market", ""),
                "odds_range": row.get("odds_range", ""),
                "total_trades": trades,
                "roi": round(roi, 6),
                "profit_factor": round(pf, 6),
                "avg_profit": round(avg_profit, 6),
                "classification": label,
                "reason": reason,
            })
        out = pd.DataFrame(rows, columns=columns)
        logger.info("Odds refinement gerado: linhas=%s", len(out))
        return out
