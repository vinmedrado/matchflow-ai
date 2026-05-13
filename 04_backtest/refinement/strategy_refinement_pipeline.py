
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pandas as pd

from backend.core.logging_config import get_logger
from refinement.common import data_path, load_csv, read_config, write_csv
from refinement.league_refiner import LeagueRefiner
from refinement.market_refiner import MarketRefiner
from refinement.odds_refiner import OddsRefiner
from refinement.refinement_report import RefinementReport
from refinement.strategy_refiner import StrategyRefiner
from refinement.threshold_refiner import ThresholdRefiner

logger = get_logger("matchflow.backtest.refinement.strategy_refinement_pipeline")


class StrategyRefinementPipeline:
    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or data_path().resolve()
        self.config_path = self.project_root / "04_backtest" / "config" / "refinement_config.json"
        self.output_dir = self.project_root / "data" / "backtest" / "refinement"
        self.config: Dict[str, Any] = read_config(self.config_path)

    def run(self) -> Dict[str, pd.DataFrame]:
        logger.info("Iniciando refinamento estratégico Patch 4.3")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        summary = load_csv(self.project_root / "data" / "backtest" / "results" / "summary_results.csv")
        market_performance = load_csv(self.project_root / "data" / "backtest" / "analysis" / "market_performance.csv")
        qualified = load_csv(self.project_root / "data" / "backtest" / "analysis" / "deep" / "qualified_strategies.csv")
        odds = load_csv(self.project_root / "data" / "backtest" / "analysis" / "deep" / "market_odds_range_analysis.csv")
        league_market = load_csv(self.project_root / "data" / "backtest" / "analysis" / "deep" / "league_market_matrix.csv")
        rolling = load_csv(self.project_root / "data" / "backtest" / "analysis" / "deep" / "rolling_roi_analysis.csv")
        consistency = load_csv(self.project_root / "data" / "backtest" / "analysis" / "deep" / "consistency_score.csv")
        flags = load_csv(self.project_root / "data" / "backtest" / "analysis" / "deep" / "risk_flags.csv")

        if summary.empty:
            logger.warning("summary_results.csv ausente ou vazio; refinamento ficará sem candidatos")

        strategy_refiner = StrategyRefiner(self.config)
        refined, rejected = strategy_refiner.refine(summary, consistency, rolling, flags)

        market_matrix = MarketRefiner(self.config).run(market_performance)
        league_matrix = LeagueRefiner(self.config).run(league_market)
        odds_matrix = OddsRefiner(self.config).run(odds)
        thresholds = ThresholdRefiner(self.config).run(odds_matrix, league_matrix, consistency)

        report = RefinementReport()
        risk_report = report.build_risk_report(rejected, refined, flags, qualified)
        insights = report.build_insights(refined, rejected, thresholds, market_matrix, league_matrix, odds_matrix, risk_report)

        outputs = {
            "refined_strategy_candidates": refined,
            "rejected_strategy_candidates": rejected,
            "threshold_candidates": thresholds,
            "market_refinement_matrix": market_matrix,
            "league_refinement_matrix": league_matrix,
            "odds_refinement_matrix": odds_matrix,
            "refinement_risk_report": risk_report,
        }
        for name, df in outputs.items():
            write_csv(df, self.output_dir / f"{name}.csv")
        (self.output_dir / "refinement_insights.txt").write_text(insights, encoding="utf-8")

        logger.info(
            "Refinamento estratégico concluído: keep=%s rejected=%s thresholds=%s risks=%s",
            len(refined), len(rejected), len(thresholds), len(risk_report),
        )
        return outputs
