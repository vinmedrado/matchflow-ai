from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from backend.core.logging_config import get_logger

logger = get_logger("matchflow.backtest.risk_flags")


def _add_flag(rows: List[Dict[str, Any]], strategy: str, market: str, flag: str, severity: str, message: str) -> None:
    rows.append({
        "strategy": strategy,
        "market": market,
        "flag": flag,
        "severity": severity,
        "message": message,
    })


def build_risk_flags(
    qualified: pd.DataFrame,
    odds_ranges: pd.DataFrame,
    league_market: pd.DataFrame,
    rolling: pd.DataFrame,
    consistency: pd.DataFrame,
    config: Dict[str, Any],
) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    max_drawdown_warning = float(config.get("max_drawdown_warning", -20))
    min_trades_default = int(config.get("min_trades_default", 50))

    for _, row in qualified.iterrows():
        strategy = str(row.get("strategy"))
        market = str(row.get("market"))
        total_trades = int(row.get("total_trades", 0))
        roi = float(row.get("roi", 0.0))
        drawdown = float(row.get("max_drawdown", 0.0))

        if total_trades < min_trades_default:
            _add_flag(rows, strategy, market, "LOW_SAMPLE_SIZE", "HIGH", f"Apenas {total_trades} trades. Não tratar como edge confiável.")
        if drawdown <= max_drawdown_warning:
            _add_flag(rows, strategy, market, "HIGH_DRAWDOWN", "HIGH", f"Drawdown {drawdown:.2f} abaixo do limite de alerta {max_drawdown_warning:.2f}.")

        roll = rolling[(rolling["strategy"] == strategy) & (rolling["market"] == market)]
        if not roll.empty:
            avg_negative = float(roll["negative_windows_pct"].mean())
            avg_std = float(roll["rolling_roi_std"].mean())
            if avg_negative > 0.40:
                _add_flag(rows, strategy, market, "NEGATIVE_ROLLING_ROI", "HIGH", f"{avg_negative:.0%} das janelas móveis ficaram negativas.")
            if avg_std > 0.20:
                _add_flag(rows, strategy, market, "UNSTABLE_ROI", "MEDIUM", f"Rolling ROI com volatilidade elevada: std média {avg_std:.4f}.")
        else:
            _add_flag(rows, strategy, market, "NEGATIVE_ROLLING_ROI", "MEDIUM", "Sem janelas móveis suficientes para comprovar estabilidade.")

        market_odds = odds_ranges[odds_ranges["market"] == market]
        if len(market_odds) > 1 and "total_profit" in market_odds.columns:
            total_abs_profit = float(market_odds["total_profit"].abs().sum())
            if total_abs_profit > 0:
                dependency = float(market_odds["total_profit"].abs().max() / total_abs_profit)
                if dependency >= 0.70:
                    _add_flag(rows, strategy, market, "ODDS_RANGE_DEPENDENCY", "MEDIUM", "Performance concentrada em uma faixa de odds.")

        lm = league_market[league_market["market"] == market]
        if len(lm) > 1 and "total_profit" in lm.columns:
            total_abs_profit = float(lm["total_profit"].abs().sum())
            if total_abs_profit > 0:
                dependency = float(lm["total_profit"].abs().max() / total_abs_profit)
                if dependency >= 0.70:
                    _add_flag(rows, strategy, market, "LEAGUE_DEPENDENCY", "MEDIUM", "Performance concentrada em poucas ligas.")

        if total_trades < min_trades_default and roi > 0:
            _add_flag(rows, strategy, market, "POSSIBLE_OVERFITTING", "HIGH", "ROI positivo com amostra baixa pode ser ruído estatístico.")

    result = pd.DataFrame(rows)
    if result.empty:
        result = pd.DataFrame(columns=["strategy", "market", "flag", "severity", "message"])
    else:
        severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        result["_severity_order"] = result["severity"].map(severity_order).fillna(9)
        result = result.sort_values(["_severity_order", "strategy", "market", "flag"]).drop(columns=["_severity_order"]).reset_index(drop=True)

    logger.info("Risk flags geradas: linhas=%s", len(result))
    return result
