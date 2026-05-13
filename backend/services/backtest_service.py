from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pandas as pd

from backend.core.logging_config import get_logger

logger = get_logger("matchflow.backtest_service")


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_local_path(path: str | Path) -> Path:
    path_obj = Path(path)
    return path_obj if path_obj.is_absolute() else project_root() / path_obj


def backtest_summary(path: str | Path = "data/backtest/results/summary_results.csv") -> Dict[str, Any]:
    summary_path = resolve_local_path(path)
    equity_path = resolve_local_path("data/backtest/results/equity_curve.csv")

    if not summary_path.exists():
        logger.warning("Resumo de backtest ausente: %s", summary_path)
        return {
            "file_exists": False,
            "strategies": [],
            "total_strategies": 0,
            "total_trades": 0,
            "total_profit": 0.0,
            "roi": 0.0,
            "best_strategy": None,
            "equity_curve_exists": equity_path.exists(),
            "path": str(summary_path),
            "message": f"Backtest summary not found: {summary_path}",
        }

    try:
        df = pd.read_csv(summary_path)
    except Exception as exc:
        logger.error("Falha ao ler resumo de backtest %s: %s", summary_path, exc)
        return {
            "file_exists": True,
            "strategies": [],
            "total_strategies": 0,
            "total_trades": 0,
            "total_profit": 0.0,
            "roi": 0.0,
            "best_strategy": None,
            "equity_curve_exists": equity_path.exists(),
            "path": str(summary_path),
            "message": f"Backtest summary invalid: {exc}",
        }

    if df.empty:
        logger.warning("Resumo de backtest vazio: %s", summary_path)
        return {
            "file_exists": True,
            "strategies": [],
            "total_strategies": 0,
            "total_trades": 0,
            "total_profit": 0.0,
            "roi": 0.0,
            "best_strategy": None,
            "equity_curve_exists": equity_path.exists(),
            "path": str(summary_path),
            "message": "Backtest summary is empty.",
        }

    records = df.to_dict(orient="records")
    total_trades = int(df["total_trades"].sum()) if "total_trades" in df.columns else 0
    total_profit = float(df["total_profit"].sum()) if "total_profit" in df.columns else 0.0
    total_stake = float(df["stake_total"].sum()) if "stake_total" in df.columns else 0.0
    roi = total_profit / total_stake if total_stake > 0 else 0.0

    best_strategy = None
    if "roi" in df.columns and "strategy" in df.columns:
        best_row = df.sort_values(["roi", "total_trades"], ascending=[False, False]).iloc[0]
        best_strategy = {
            "strategy": str(best_row.get("strategy")),
            "market": str(best_row.get("market", "")),
            "roi": float(best_row.get("roi", 0.0)),
            "win_rate": float(best_row.get("win_rate", 0.0)),
            "total_trades": int(best_row.get("total_trades", 0)),
            "total_profit": float(best_row.get("total_profit", 0.0)),
        }

    logger.info(
        "Resumo financeiro de backtest carregado: estratégias=%s trades=%s lucro=%.4f roi=%.4f",
        len(records),
        total_trades,
        total_profit,
        roi,
    )
    return {
        "file_exists": True,
        "strategies": records,
        "total_strategies": int(len(records)),
        "total_trades": total_trades,
        "total_profit": round(total_profit, 6),
        "roi": round(roi, 6),
        "best_strategy": best_strategy,
        "equity_curve_exists": equity_path.exists(),
        "equity_curve_path": str(equity_path),
        "path": str(summary_path),
    }



def backtest_analysis_summary(analysis_dir: str | Path = "data/backtest/analysis") -> Dict[str, Any]:
    """Return a compact professional summary from generated backtest analysis files."""
    directory = resolve_local_path(analysis_dir)
    market_path = directory / "market_performance.csv"
    league_path = directory / "league_performance.csv"
    strategy_path = directory / "strategy_ranking.csv"
    drawdown_path = directory / "drawdown_analysis.csv"
    equity_path = directory / "equity_analysis.csv"
    insights_path = directory / "insights.txt"

    required = [market_path, league_path, strategy_path, drawdown_path, equity_path]
    missing = [str(path) for path in required if not path.exists()]

    if missing:
        logger.warning("Análise de backtest incompleta ou ausente: missing=%s", missing)
        return {
            "file_exists": False,
            "analysis_available": False,
            "missing_files": missing,
            "top_markets": [],
            "top_strategies": [],
            "best_league": None,
            "worst_drawdown": None,
            "overall_roi": 0.0,
            "insights": "",
            "message": "Backtest analysis files not found. Run python run_backtest_analysis_pipeline.py",
        }

    try:
        market_df = pd.read_csv(market_path)
        league_df = pd.read_csv(league_path)
        strategy_df = pd.read_csv(strategy_path)
        drawdown_df = pd.read_csv(drawdown_path)
        equity_df = pd.read_csv(equity_path)
        insights = insights_path.read_text(encoding="utf-8") if insights_path.exists() else ""
    except Exception as exc:
        logger.error("Falha ao ler análise de backtest: %s", exc)
        return {
            "file_exists": True,
            "analysis_available": False,
            "missing_files": [],
            "top_markets": [],
            "top_strategies": [],
            "best_league": None,
            "worst_drawdown": None,
            "overall_roi": 0.0,
            "insights": "",
            "message": f"Invalid backtest analysis files: {exc}",
        }

    top_markets = market_df.head(5).to_dict(orient="records") if not market_df.empty else []
    top_strategies = strategy_df.head(5).to_dict(orient="records") if not strategy_df.empty else []
    best_league = league_df.iloc[0].to_dict() if not league_df.empty else None
    worst_drawdown = drawdown_df.iloc[0].to_dict() if not drawdown_df.empty else None

    overall_roi = 0.0
    if not equity_df.empty and "cumulative_return" in equity_df.columns:
        overall_roi = float(equity_df.iloc[0].get("cumulative_return", 0.0))
    elif not market_df.empty and {"total_profit", "stake_total"}.issubset(set(market_df.columns)):
        stake = float(market_df["stake_total"].sum())
        overall_roi = float(market_df["total_profit"].sum()) / stake if stake > 0 else 0.0

    logger.info(
        "Resumo de análise de backtest carregado: top_markets=%s top_strategies=%s overall_roi=%.4f",
        len(top_markets),
        len(top_strategies),
        overall_roi,
    )

    return {
        "file_exists": True,
        "analysis_available": True,
        "missing_files": [],
        "top_markets": top_markets,
        "top_strategies": top_strategies,
        "best_league": best_league,
        "worst_drawdown": worst_drawdown,
        "overall_roi": round(overall_roi, 6),
        "insights": insights,
        "paths": {
            "market_performance": str(market_path),
            "league_performance": str(league_path),
            "strategy_ranking": str(strategy_path),
            "drawdown_analysis": str(drawdown_path),
            "equity_analysis": str(equity_path),
            "insights": str(insights_path),
        },
    }



def _read_optional_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        logger.warning("Arquivo deep analysis ausente: %s", path)
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception as exc:
        logger.error("Falha ao ler arquivo deep analysis %s: %s", path, exc)
        return pd.DataFrame()


def backtest_deep_analysis_summary(analysis_dir: str | Path = "data/backtest/analysis/deep") -> Dict[str, Any]:
    """Return compact summary from Patch 4.2 deep analysis outputs."""
    directory = resolve_local_path(analysis_dir)
    qualified_path = directory / "qualified_strategies.csv"
    odds_path = directory / "market_odds_range_analysis.csv"
    matrix_path = directory / "league_market_matrix.csv"
    consistency_path = directory / "consistency_score.csv"
    flags_path = directory / "risk_flags.csv"
    insights_path = directory / "deep_insights.txt"

    required = [qualified_path, odds_path, matrix_path, consistency_path, flags_path, insights_path]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        logger.warning("Deep analysis incompleta ou ausente: missing=%s", missing)
        return {
            "file_exists": False,
            "deep_analysis_available": False,
            "missing_files": missing,
            "top_qualified_strategies": [],
            "rejected_strategies": [],
            "risk_flags_count": {},
            "best_odds_range": None,
            "best_league_market_combinations": [],
            "consistency_score_top_10": [],
            "message": "Deep analysis files not found. Run python run_backtest_deep_analysis_pipeline.py",
        }

    qualified = _read_optional_csv(qualified_path)
    odds = _read_optional_csv(odds_path)
    matrix = _read_optional_csv(matrix_path)
    consistency = _read_optional_csv(consistency_path)
    flags = _read_optional_csv(flags_path)
    insights = insights_path.read_text(encoding="utf-8") if insights_path.exists() else ""

    top_qualified = []
    rejected = []
    if not qualified.empty:
        reliable_col = "is_edge_reliable"
        top_qualified = qualified[qualified.get(reliable_col, False) == True].head(10).to_dict(orient="records") if reliable_col in qualified.columns else []
        rejected = qualified[qualified.get("sample_class", "") == "LOW_SAMPLE"].head(10).to_dict(orient="records") if "sample_class" in qualified.columns else []

    best_odds_range = None
    if not odds.empty:
        best_odds_range = odds.sort_values(["roi", "profit_factor", "total_trades"], ascending=[False, False, False]).iloc[0].to_dict()

    best_league_market = []
    if not matrix.empty:
        best_league_market = matrix.sort_values(["risk_level", "roi", "profit_factor"], ascending=[True, False, False]).head(10).to_dict(orient="records")

    consistency_top = []
    if not consistency.empty:
        consistency_top = consistency.sort_values(["consistency_score", "total_trades"], ascending=[False, False]).head(10).to_dict(orient="records")

    flags_count = flags["flag"].value_counts().to_dict() if not flags.empty and "flag" in flags.columns else {}

    logger.info(
        "Resumo deep analysis carregado: qualified=%s rejected=%s flags=%s",
        len(top_qualified),
        len(rejected),
        len(flags),
    )

    return {
        "file_exists": True,
        "deep_analysis_available": True,
        "missing_files": [],
        "top_qualified_strategies": top_qualified,
        "rejected_strategies": rejected,
        "risk_flags_count": flags_count,
        "best_odds_range": best_odds_range,
        "best_league_market_combinations": best_league_market,
        "consistency_score_top_10": consistency_top,
        "insights": insights,
        "paths": {
            "qualified_strategies": str(qualified_path),
            "market_odds_range_analysis": str(odds_path),
            "league_market_matrix": str(matrix_path),
            "consistency_score": str(consistency_path),
            "risk_flags": str(flags_path),
            "deep_insights": str(insights_path),
        },
    }



def backtest_refinement_summary(refinement_dir: str | Path = "data/backtest/refinement") -> Dict[str, Any]:
    """Return compact summary from Patch 4.3 refinement outputs."""
    directory = resolve_local_path(refinement_dir)
    refined_path = directory / "refined_strategy_candidates.csv"
    rejected_path = directory / "rejected_strategy_candidates.csv"
    market_path = directory / "market_refinement_matrix.csv"
    league_path = directory / "league_refinement_matrix.csv"
    odds_path = directory / "odds_refinement_matrix.csv"
    risk_path = directory / "refinement_risk_report.csv"
    insights_path = directory / "refinement_insights.txt"

    required = [refined_path, rejected_path, market_path, league_path, odds_path, risk_path, insights_path]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        logger.warning("Refinement analysis incompleta ou ausente: missing=%s", missing)
        return {
            "file_exists": False,
            "refinement_available": False,
            "missing_files": missing,
            "refined_candidates_top_10": [],
            "rejected_count": 0,
            "markets": {"KEEP": [], "WATCH": [], "DISCARD": []},
            "favorable_odds_ranges": [],
            "strongest_league_market_pairs": [],
            "high_risk_strategies": [],
            "insights": "",
            "message": "Refinement files not found. Run python run_backtest_refinement_pipeline.py",
        }

    try:
        refined = _read_optional_csv(refined_path)
        rejected = _read_optional_csv(rejected_path)
        market = _read_optional_csv(market_path)
        league = _read_optional_csv(league_path)
        odds = _read_optional_csv(odds_path)
        risk = _read_optional_csv(risk_path)
        insights = insights_path.read_text(encoding="utf-8") if insights_path.exists() else ""
    except Exception as exc:
        logger.error("Falha ao ler refinement analysis: %s", exc)
        return {
            "file_exists": True,
            "refinement_available": False,
            "missing_files": [],
            "refined_candidates_top_10": [],
            "rejected_count": 0,
            "markets": {"KEEP": [], "WATCH": [], "DISCARD": []},
            "favorable_odds_ranges": [],
            "strongest_league_market_pairs": [],
            "high_risk_strategies": [],
            "insights": "",
            "message": f"Invalid refinement files: {exc}",
        }

    refined_top = refined.sort_values(["consistency_score", "roi", "total_trades"], ascending=[False, False, False]).head(10).to_dict(orient="records") if not refined.empty else []
    markets = {"KEEP": [], "WATCH": [], "DISCARD": []}
    if not market.empty and "classification" in market.columns:
        for label in markets:
            markets[label] = market[market["classification"] == label].head(10).to_dict(orient="records")
    favorable_odds = odds[odds.get("classification", "") == "FAVORABLE"].head(10).to_dict(orient="records") if not odds.empty and "classification" in odds.columns else []
    strongest_pairs = league[league.get("classification", "") == "STRONG_CANDIDATE"].head(10).to_dict(orient="records") if not league.empty and "classification" in league.columns else []
    high_risk = risk[risk.get("overfitting_risk", "") == "HIGH"].head(10).to_dict(orient="records") if not risk.empty and "overfitting_risk" in risk.columns else []

    logger.info(
        "Resumo refinement carregado: refined=%s rejected=%s favorable_odds=%s high_risk=%s",
        len(refined_top), len(rejected), len(favorable_odds), len(high_risk),
    )

    return {
        "file_exists": True,
        "refinement_available": True,
        "missing_files": [],
        "refined_candidates_top_10": refined_top,
        "rejected_count": int(len(rejected)),
        "markets": markets,
        "favorable_odds_ranges": favorable_odds,
        "strongest_league_market_pairs": strongest_pairs,
        "high_risk_strategies": high_risk,
        "insights": insights,
        "paths": {
            "refined_strategy_candidates": str(refined_path),
            "rejected_strategy_candidates": str(rejected_path),
            "market_refinement_matrix": str(market_path),
            "league_refinement_matrix": str(league_path),
            "odds_refinement_matrix": str(odds_path),
            "refinement_risk_report": str(risk_path),
            "refinement_insights": str(insights_path),
        },
    }
