
from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from backend.core.logging_config import get_logger
from refinement.common import normalize_pct, safe_float, safe_int

logger = get_logger("matchflow.backtest.refinement.market_refiner")


class MarketRefiner:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.min_trades = int(config.get("min_trades_for_candidate", 100))
        self.min_roi = float(config.get("min_roi_candidate", 0.02))
        self.min_pf = float(config.get("min_profit_factor_candidate", 1.10))
        self.max_dd_allowed = float(config.get("max_drawdown_allowed", -25))

    def run(self, market_df: pd.DataFrame) -> pd.DataFrame:
        if market_df.empty:
            return pd.DataFrame(columns=["market", "total_trades", "roi", "profit_factor", "max_drawdown", "classification", "reason"])
        rows = []
        for _, row in market_df.iterrows():
            trades = safe_int(row.get("total_trades"))
            roi = normalize_pct(row.get("roi"))
            pf = safe_float(row.get("profit_factor"))
            dd = safe_float(row.get("max_drawdown"))
            classification = "DISCARD"
            reasons = []
            if trades < self.min_trades:
                reasons.append("LOW_SAMPLE")
            if roi < 0:
                reasons.append("NEGATIVE_ROI")
            if pf < 1:
                reasons.append("PROFIT_FACTOR_BELOW_1")
            if dd < self.max_dd_allowed:
                reasons.append("HIGH_DRAWDOWN")
            if not reasons and roi >= self.min_roi and pf >= self.min_pf:
                classification = "KEEP"
                reasons.append("Meets ROI/PF/sample/drawdown criteria")
            elif trades >= self.min_trades and roi >= 0 and pf >= 1:
                classification = "WATCH"
                reasons.append("Positive but not strong enough for KEEP")
            rows.append({
                "market": row.get("market", ""),
                "total_trades": trades,
                "roi": round(roi, 6),
                "profit_factor": round(pf, 6),
                "max_drawdown": round(dd, 6),
                "classification": classification,
                "reason": "|".join(reasons),
            })
        out = pd.DataFrame(rows).sort_values(["classification", "roi", "profit_factor"], ascending=[True, False, False])
        logger.info("Market refinement gerado: linhas=%s", len(out))
        return out
