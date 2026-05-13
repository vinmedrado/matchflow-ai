from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

from backend.core.logging_config import get_logger

logger = get_logger("matchflow.backtest.deep_performance_analyzer")


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_path(path: str | Path) -> Path:
    path_obj = Path(path)
    return path_obj if path_obj.is_absolute() else PROJECT_ROOT / path_obj


def load_config(path: str | Path = "04_backtest/config/deep_analysis_config.json") -> Dict[str, Any]:
    config_path = resolve_path(path)
    if not config_path.exists():
        logger.warning("Configuração deep analysis não encontrada. Usando defaults: %s", config_path)
        return {
            "min_trades_default": 50,
            "min_trades_strong": 100,
            "max_drawdown_warning": -20,
            "profit_factor_min": 1.05,
            "roi_min": 0.01,
            "rolling_windows": [25, 50, 100],
            "odds_ranges": [[1.20, 1.49], [1.50, 1.79], [1.80, 2.09], [2.10, 2.49], [2.50, None]],
        }
    return json.loads(config_path.read_text(encoding="utf-8"))


def load_inputs(
    detailed_path: str | Path = "04_backtest/results/detailed/detailed_results.parquet",
    summary_path: str | Path = "04_backtest/results/summary/summary_results.csv",
    equity_path: str | Path = "04_backtest/results/summary/equity_curve.csv",
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    detailed_file = resolve_path(detailed_path)
    summary_file = resolve_path(summary_path)
    equity_file = resolve_path(equity_path)

    if not detailed_file.exists():
        raise FileNotFoundError(f"Detailed backtest results not found: {detailed_file}")

    detailed = safe_read_dataframe(detailed_file)
    summary = pd.read_csv(summary_file) if summary_file.exists() else pd.DataFrame()
    equity = pd.read_csv(equity_file) if equity_file.exists() else pd.DataFrame()

    if "date" in detailed.columns:
        detailed["date"] = pd.to_datetime(detailed["date"], errors="coerce")
    if "is_win" in detailed.columns:
        detailed["is_win"] = detailed["is_win"].astype(bool)
    for col in ["profit", "stake", "odd"]:
        if col in detailed.columns:
            detailed[col] = pd.to_numeric(detailed[col], errors="coerce")

    profit_value = detailed.get("profit")
    if profit_value is None:
        detailed["profit"] = 0.0
    else:
        detailed["profit"] = pd.Series(profit_value, index=detailed.index).fillna(0.0) if not hasattr(profit_value, "fillna") else profit_value.fillna(0.0)

    stake_value = detailed.get("stake")
    if stake_value is None:
        detailed["stake"] = 1.0
    else:
        detailed["stake"] = pd.Series(stake_value, index=detailed.index).fillna(1.0) if not hasattr(stake_value, "fillna") else stake_value.fillna(1.0)
    detailed["odd"] = detailed.get("odd", pd.NA)

    logger.info(
        "Entradas deep analysis carregadas: detailed_rows=%s summary_rows=%s equity_rows=%s",
        len(detailed),
        len(summary),
        len(equity),
    )
    return detailed, summary, equity


def safe_profit_factor(profit: pd.Series) -> float:
    gains = float(profit[profit > 0].sum())
    losses = abs(float(profit[profit < 0].sum()))
    if losses == 0:
        return round(gains, 6) if gains > 0 else 0.0
    return round(gains / losses, 6)


def max_drawdown_from_profit(profit: pd.Series) -> float:
    equity = profit.fillna(0.0).cumsum()
    running_max = equity.cummax()
    drawdown = equity - running_max
    return round(float(drawdown.min()), 6) if not drawdown.empty else 0.0


def compute_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "roi": 0.0,
            "profit_factor": 0.0,
            "avg_profit": 0.0,
            "total_profit": 0.0,
            "stake_total": 0.0,
            "max_drawdown": 0.0,
            "avg_odds": 0.0,
        }

    stake_total = float(df["stake"].sum()) if "stake" in df.columns else float(len(df))
    total_profit = float(df["profit"].sum())
    win_rate = float(df["is_win"].mean()) if "is_win" in df.columns and len(df) else 0.0
    roi = total_profit / stake_total if stake_total > 0 else 0.0
    avg_odds = float(df["odd"].mean()) if "odd" in df.columns and df["odd"].notna().any() else 0.0

    return {
        "total_trades": int(len(df)),
        "win_rate": round(win_rate, 6),
        "roi": round(roi, 6),
        "profit_factor": safe_profit_factor(df["profit"]),
        "avg_profit": round(float(df["profit"].mean()), 6),
        "total_profit": round(total_profit, 6),
        "stake_total": round(stake_total, 6),
        "max_drawdown": max_drawdown_from_profit(df["profit"]),
        "avg_odds": round(avg_odds, 6),
    }


def classify_sample(total_trades: int, min_default: int, min_strong: int) -> str:
    if total_trades >= min_strong:
        return "STRONG_SAMPLE"
    if total_trades >= min_default:
        return "ACCEPTABLE_SAMPLE"
    return "LOW_SAMPLE"


def required_columns() -> List[str]:
    return ["strategy", "market", "league", "profit", "stake", "odd", "is_win"]


class DeepPerformanceAnalyzer:
    def __init__(
        self,
        output_dir: str | Path = "data/backtest/analysis/deep",
        config_path: str | Path = "04_backtest/config/deep_analysis_config.json",
    ) -> None:
        self.output_dir = resolve_path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config = load_config(config_path)

    def validate_inputs(self, detailed: pd.DataFrame) -> None:
        missing = [col for col in required_columns() if col not in detailed.columns]
        if missing:
            raise ValueError(f"Detailed results missing required columns: {missing}")
        if detailed.empty:
            raise ValueError("Detailed results are empty. Deep analysis cannot run.")

    def build_qualified_strategies(self, detailed: pd.DataFrame) -> pd.DataFrame:
        min_default = int(self.config["min_trades_default"])
        min_strong = int(self.config["min_trades_strong"])
        rows: List[Dict[str, Any]] = []

        for (strategy, market), group in detailed.groupby(["strategy", "market"], dropna=False):
            metrics = compute_metrics(group.sort_values("date"))
            sample_class = classify_sample(metrics["total_trades"], min_default, min_strong)
            rows.append({
                "strategy": strategy,
                "market": market,
                **metrics,
                "sample_class": sample_class,
                "is_edge_reliable": bool(
                    sample_class != "LOW_SAMPLE"
                    and metrics["roi"] >= float(self.config["roi_min"])
                    and metrics["profit_factor"] >= float(self.config["profit_factor_min"])
                ),
            })

        result = pd.DataFrame(rows)
        if not result.empty:
            result = result.sort_values(["is_edge_reliable", "sample_class", "roi", "profit_factor"], ascending=[False, True, False, False])
        logger.info("Qualified strategies gerado: linhas=%s", len(result))
        return result

    def build_league_market_matrix(self, detailed: pd.DataFrame) -> pd.DataFrame:
        min_default = int(self.config["min_trades_default"])
        rows: List[Dict[str, Any]] = []
        for (league, market), group in detailed.groupby(["league", "market"], dropna=False):
            metrics = compute_metrics(group.sort_values("date"))
            if metrics["total_trades"] < min_default:
                risk = "LOW_SAMPLE"
            elif metrics["roi"] >= float(self.config["roi_min"]) and metrics["profit_factor"] >= float(self.config["profit_factor_min"]):
                risk = "HIGH_EDGE_CANDIDATE"
            elif metrics["roi"] < 0 or metrics["profit_factor"] < 1:
                risk = "WEAK"
            else:
                risk = "NEUTRAL"

            rows.append({
                "league": league,
                "market": market,
                **metrics,
                "risk_level": risk,
            })
        result = pd.DataFrame(rows)
        if not result.empty:
            result = result.sort_values(["risk_level", "roi", "profit_factor"], ascending=[True, False, False])
        logger.info("League x Market matrix gerada: linhas=%s", len(result))
        return result

    def run(self) -> Dict[str, pd.DataFrame]:
        logger.info("Iniciando deep analysis de backtest")
        detailed, summary, equity = load_inputs()
        self.validate_inputs(detailed)

        from .odds_range_analysis import build_market_odds_range_analysis
        from .temporal_analysis import build_temporal_performance, build_rolling_roi_analysis
        from .consistency_analysis import build_consistency_score
        from .risk_flags import build_risk_flags
        from .deep_insights import build_deep_insights

        qualified = self.build_qualified_strategies(detailed)
        odds_ranges = build_market_odds_range_analysis(detailed, self.config)
        league_market = self.build_league_market_matrix(detailed)
        temporal = build_temporal_performance(detailed)
        rolling = build_rolling_roi_analysis(detailed, self.config)
        consistency = build_consistency_score(qualified, rolling, league_market, self.config)
        risk_flags = build_risk_flags(qualified, odds_ranges, league_market, rolling, consistency, self.config)
        insights = build_deep_insights(qualified, odds_ranges, league_market, rolling, consistency, risk_flags, self.config)

        outputs = {
            "qualified_strategies": qualified,
            "market_odds_range_analysis": odds_ranges,
            "league_market_matrix": league_market,
            "temporal_performance": temporal,
            "rolling_roi_analysis": rolling,
            "consistency_score": consistency,
            "risk_flags": risk_flags,
        }

        for name, df in outputs.items():
            path = self.output_dir / f"{name}.csv"
            df.to_csv(path, index=False)
            logger.info("Arquivo deep analysis salvo: %s linhas=%s", path, len(df))

        insights_path = self.output_dir / "deep_insights.txt"
        insights_path.write_text(insights, encoding="utf-8")
        logger.info("Deep insights salvo: %s", insights_path)

        logger.info("Deep analysis concluída com sucesso")
        return outputs
