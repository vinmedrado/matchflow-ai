from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from backend.core.logging_config import get_logger

logger = get_logger("matchflow.backtest.consistency_analysis")


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def build_consistency_score(
    qualified: pd.DataFrame,
    rolling: pd.DataFrame,
    league_market: pd.DataFrame,
    config: Dict[str, Any],
) -> pd.DataFrame:
    if qualified.empty:
        return pd.DataFrame(columns=[
            "strategy", "market", "consistency_score", "sample_score", "roi_score",
            "profit_factor_score", "drawdown_score", "volatility_score", "temporal_stability_score",
        ])

    rows: List[Dict[str, Any]] = []
    max_drawdown_warning = abs(float(config.get("max_drawdown_warning", -20)))
    profit_factor_min = float(config.get("profit_factor_min", 1.05))
    roi_min = float(config.get("roi_min", 0.01))

    for _, row in qualified.iterrows():
        strategy = row["strategy"]
        market = row["market"]
        sample_class = row.get("sample_class", "LOW_SAMPLE")

        sample_score = {"LOW_SAMPLE": 10.0, "ACCEPTABLE_SAMPLE": 60.0, "STRONG_SAMPLE": 100.0}.get(sample_class, 10.0)
        roi = float(row.get("roi", 0.0))
        profit_factor = float(row.get("profit_factor", 0.0))
        drawdown = abs(float(row.get("max_drawdown", 0.0)))

        roi_score = _clamp((roi / max(roi_min, 0.0001)) * 30.0 if roi > 0 else 0.0)
        pf_score = _clamp((profit_factor / max(profit_factor_min, 0.0001)) * 30.0 if profit_factor > 1 else 0.0)
        drawdown_score = _clamp(100.0 - (drawdown / max(max_drawdown_warning, 1.0)) * 100.0)

        rolling_slice = rolling[(rolling["strategy"] == strategy) & (rolling["market"] == market)]
        if rolling_slice.empty:
            volatility_score = 20.0
            temporal_score = 20.0
        else:
            avg_std = float(rolling_slice["rolling_roi_std"].mean())
            negative_pct = float(rolling_slice["negative_windows_pct"].mean())
            volatility_score = _clamp(100.0 - avg_std * 100.0)
            temporal_score = _clamp(100.0 - negative_pct * 100.0)

        consistency_score = (
            sample_score * 0.30
            + roi_score * 0.20
            + pf_score * 0.20
            + drawdown_score * 0.15
            + volatility_score * 0.075
            + temporal_score * 0.075
        )

        rows.append({
            "strategy": strategy,
            "market": market,
            "sample_class": sample_class,
            "total_trades": int(row.get("total_trades", 0)),
            "roi": round(roi, 6),
            "profit_factor": round(profit_factor, 6),
            "max_drawdown": round(float(row.get("max_drawdown", 0.0)), 6),
            "consistency_score": round(_clamp(consistency_score), 2),
            "sample_score": round(sample_score, 2),
            "roi_score": round(roi_score, 2),
            "profit_factor_score": round(pf_score, 2),
            "drawdown_score": round(drawdown_score, 2),
            "volatility_score": round(volatility_score, 2),
            "temporal_stability_score": round(temporal_score, 2),
            "is_auxiliary_ranking_only": True,
        })

    result = pd.DataFrame(rows).sort_values(["consistency_score", "total_trades"], ascending=[False, False]).reset_index(drop=True)
    result.insert(0, "rank", range(1, len(result) + 1))
    logger.info("Consistency score gerado: linhas=%s", len(result))
    return result
