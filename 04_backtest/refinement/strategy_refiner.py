
from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pandas as pd

from backend.core.logging_config import get_logger
from refinement.common import normalize_pct, safe_float, safe_int

logger = get_logger("matchflow.backtest.refinement.strategy_refiner")


class StrategyRefiner:
    """Classify strategies as refined candidates or rejected candidates.

    This layer does not optimize thresholds and does not change backtest results.
    It only applies strict evidence filters on generated backtest/deep-analysis outputs.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.min_trades = int(config.get("min_trades_for_candidate", 100))
        self.min_roi = float(config.get("min_roi_candidate", 0.02))
        self.min_pf = float(config.get("min_profit_factor_candidate", 1.10))
        self.max_dd_allowed = float(config.get("max_drawdown_allowed", -25))
        self.max_negative_windows = float(config.get("max_negative_rolling_windows_pct", 40))
        self.min_score = float(config.get("min_consistency_score", 60))
        self.penalty_flags = set(config.get("overfitting_penalty_flags", []))

    def refine(
        self,
        summary_df: pd.DataFrame,
        consistency_df: pd.DataFrame,
        rolling_df: pd.DataFrame,
        flags_df: pd.DataFrame,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        if summary_df.empty:
            logger.warning("Refinamento sem summary_results; nenhum candidato será aprovado")
            return self._empty_refined(), self._empty_rejected()

        records: List[Dict[str, Any]] = []
        rejected: List[Dict[str, Any]] = []

        for _, row in summary_df.iterrows():
            strategy = str(row.get("strategy", ""))
            market = str(row.get("market", ""))
            key_filter = (consistency_df.get("strategy", pd.Series(dtype=str)).astype(str) == strategy)
            if "market" in consistency_df.columns:
                key_filter &= consistency_df["market"].astype(str) == market
            score_row = consistency_df[key_filter].head(1) if not consistency_df.empty else pd.DataFrame()

            roll_filter = (rolling_df.get("strategy", pd.Series(dtype=str)).astype(str) == strategy)
            if "market" in rolling_df.columns:
                roll_filter &= rolling_df["market"].astype(str) == market
            strategy_rolling = rolling_df[roll_filter] if not rolling_df.empty else pd.DataFrame()

            flag_filter = (flags_df.get("strategy", pd.Series(dtype=str)).astype(str) == strategy)
            if "market" in flags_df.columns:
                flag_filter &= flags_df["market"].astype(str) == market
            strategy_flags = flags_df[flag_filter] if not flags_df.empty else pd.DataFrame()
            flag_values = sorted(set(strategy_flags.get("flag", pd.Series(dtype=str)).astype(str).tolist()))

            total_trades = safe_int(row.get("total_trades"))
            roi = normalize_pct(row.get("roi"))
            profit_factor = safe_float(row.get("profit_factor"))
            max_drawdown = safe_float(row.get("max_drawdown"))
            consistency_score = safe_float(score_row.iloc[0].get("consistency_score", 0.0)) if not score_row.empty else 0.0
            negative_windows_pct = self._negative_windows_pct(strategy_rolling)

            reasons = self._rejection_reasons(
                total_trades=total_trades,
                roi=roi,
                profit_factor=profit_factor,
                max_drawdown=max_drawdown,
                consistency_score=consistency_score,
                negative_windows_pct=negative_windows_pct,
                flags=flag_values,
            )

            base = {
                "strategy": strategy,
                "market": market,
                "total_trades": total_trades,
                "roi": round(roi, 6),
                "profit_factor": round(profit_factor, 6),
                "max_drawdown": round(max_drawdown, 6),
                "negative_windows_pct": round(negative_windows_pct, 6),
                "consistency_score": round(consistency_score, 4),
                "risk_flags": "|".join(flag_values),
            }

            if reasons:
                rejected.append({**base, "rejection_reasons": "|".join(reasons), "recommendation": "DISCARD"})
            else:
                records.append({**base, "recommendation": "KEEP", "candidate_reason": "Passed strict sample, ROI, PF, drawdown, rolling stability and risk flag filters."})

        refined_df = pd.DataFrame(records, columns=self._refined_columns())
        rejected_df = pd.DataFrame(rejected, columns=self._rejected_columns())
        logger.info("Refinamento de estratégias concluído: keep=%s rejected=%s", len(refined_df), len(rejected_df))
        return refined_df, rejected_df

    def _negative_windows_pct(self, rolling_df: pd.DataFrame) -> float:
        if rolling_df.empty or "negative_windows_pct" not in rolling_df.columns:
            return 100.0
        value = float(rolling_df["negative_windows_pct"].max())
        return value * 100 if value <= 1 else value

    def _rejection_reasons(
        self,
        *,
        total_trades: int,
        roi: float,
        profit_factor: float,
        max_drawdown: float,
        consistency_score: float,
        negative_windows_pct: float,
        flags: List[str],
    ) -> List[str]:
        reasons: List[str] = []
        if total_trades < self.min_trades:
            reasons.append("LOW_SAMPLE")
        if roi < self.min_roi:
            reasons.append("ROI_BELOW_MIN")
        if profit_factor < self.min_pf:
            reasons.append("PROFIT_FACTOR_BELOW_MIN")
        if max_drawdown < self.max_dd_allowed:
            reasons.append("HIGH_DRAWDOWN")
        if negative_windows_pct > self.max_negative_windows:
            reasons.append("UNSTABLE_ROLLING_ROI")
        if consistency_score < self.min_score:
            reasons.append("LOW_CONSISTENCY_SCORE")
        severe_flags = sorted(set(flags).intersection(self.penalty_flags))
        if severe_flags:
            reasons.append("CRITICAL_FLAGS:" + ",".join(severe_flags))
        return reasons

    @staticmethod
    def _refined_columns() -> List[str]:
        return ["strategy", "market", "total_trades", "roi", "profit_factor", "max_drawdown", "negative_windows_pct", "consistency_score", "risk_flags", "recommendation", "candidate_reason"]

    @staticmethod
    def _rejected_columns() -> List[str]:
        return ["strategy", "market", "total_trades", "roi", "profit_factor", "max_drawdown", "negative_windows_pct", "consistency_score", "risk_flags", "rejection_reasons", "recommendation"]

    def _empty_refined(self) -> pd.DataFrame:
        return pd.DataFrame(columns=self._refined_columns())

    def _empty_rejected(self) -> pd.DataFrame:
        return pd.DataFrame(columns=self._rejected_columns())
