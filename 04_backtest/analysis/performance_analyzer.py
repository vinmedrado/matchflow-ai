
from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd

from .common import clean_float, compute_group_metrics, load_backtest_inputs, resolve_path
from .drawdown_analysis import build_drawdown_analysis
from .equity_analysis import build_equity_analysis
from .league_analysis import build_league_performance
from .market_analysis import build_market_performance
from backend.core.logging_config import get_logger

logger = get_logger("matchflow.backtest.performance_analyzer")


class BacktestPerformanceAnalyzer:
    def __init__(self, output_dir: str | Path = "data/backtest/analysis") -> None:
        self.output_dir = resolve_path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> Dict[str, pd.DataFrame]:
        logger.info("Iniciando análise profissional dos resultados de backtest")

        detailed, summary, equity = load_backtest_inputs()

        market_performance = build_market_performance(detailed, self.output_dir / "market_performance.csv")
        league_performance = build_league_performance(detailed, self.output_dir / "league_performance.csv")
        strategy_ranking = self.build_strategy_ranking(detailed, self.output_dir / "strategy_ranking.csv")
        drawdown_analysis = build_drawdown_analysis(detailed, self.output_dir / "drawdown_analysis.csv")
        equity_analysis = build_equity_analysis(detailed, equity, self.output_dir / "equity_analysis.csv")
        insights = self.build_insights(market_performance, league_performance, strategy_ranking, drawdown_analysis, equity_analysis)
        (self.output_dir / "insights.txt").write_text(insights, encoding="utf-8")

        logger.info("Análise de backtest concluída: output_dir=%s", self.output_dir)

        return {
            "market_performance": market_performance,
            "league_performance": league_performance,
            "strategy_ranking": strategy_ranking,
            "drawdown_analysis": drawdown_analysis,
            "equity_analysis": equity_analysis,
        }

    def build_strategy_ranking(self, detailed: pd.DataFrame, output_path: str | Path) -> pd.DataFrame:
        rows = []
        for keys, group in detailed.groupby(["strategy", "market"], dropna=False):
            metrics = compute_group_metrics(group)
            drawdown_penalty = abs(float(metrics.get("max_drawdown", 0.0)))
            consistency_score = float(metrics.get("roi", 0.0)) + float(metrics.get("profit_factor", 0.0)) - (drawdown_penalty / 100.0)
            metrics.update({
                "strategy": str(keys[0]),
                "market": str(keys[1]),
                "consistency_score": clean_float(consistency_score),
            })
            rows.append(metrics)

        result = pd.DataFrame(rows)
        if not result.empty:
            result = result.sort_values(
                ["roi", "profit_factor", "consistency_score", "total_trades"],
                ascending=[False, False, False, False],
            ).reset_index(drop=True)
            result.insert(0, "rank", range(1, len(result) + 1))

        output_file = resolve_path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(output_file, index=False)

        logger.info("Strategy ranking salvo: %s | linhas=%s", output_file, len(result))
        return result

    def build_insights(
        self,
        market_performance: pd.DataFrame,
        league_performance: pd.DataFrame,
        strategy_ranking: pd.DataFrame,
        drawdown_analysis: pd.DataFrame,
        equity_analysis: pd.DataFrame,
    ) -> str:
        lines = [
            "MATCHFLOW ANALYTICS - BACKTEST PERFORMANCE INSIGHTS",
            "=" * 64,
            "",
        ]

        if not market_performance.empty:
            best_market = market_performance.iloc[0]
            worst_market = market_performance.sort_values("roi", ascending=True).iloc[0]
            lines.extend([
                f"Melhor mercado: {best_market.get('market')} | ROI={float(best_market.get('roi', 0))*100:.2f}% | Trades={int(best_market.get('total_trades', 0))}",
                f"Pior mercado: {worst_market.get('market')} | ROI={float(worst_market.get('roi', 0))*100:.2f}% | Trades={int(worst_market.get('total_trades', 0))}",
                "",
            ])

        if not league_performance.empty:
            top_leagues = league_performance.head(5)
            lines.append("Ligas mais lucrativas:")
            for _, row in top_leagues.iterrows():
                lines.append(f"- {row.get('league')}: ROI={float(row.get('roi', 0))*100:.2f}% | Trades={int(row.get('total_trades', 0))}")
            lines.append("")

        if not strategy_ranking.empty:
            top_strategy = strategy_ranking.iloc[0]
            lines.extend([
                f"Estratégia mais consistente: {top_strategy.get('strategy')} ({top_strategy.get('market')})",
                f"- ROI={float(top_strategy.get('roi', 0))*100:.2f}% | PF={float(top_strategy.get('profit_factor', 0)):.2f} | DD={float(top_strategy.get('max_drawdown', 0)):.2f}",
                "",
            ])

        if not drawdown_analysis.empty:
            worst_dd = drawdown_analysis.iloc[0]
            lines.extend([
                "Alerta de risco:",
                f"- Pior drawdown: {float(worst_dd.get('max_drawdown', 0)):.2f} em {worst_dd.get('strategy')} / {worst_dd.get('market')}",
                f"- Maior sequência negativa: {int(worst_dd.get('max_losing_streak', 0))}",
                "",
            ])

        if not equity_analysis.empty:
            eq = equity_analysis.iloc[0]
            lines.extend([
                "Equity:",
                f"- Crescimento da banca: {float(eq.get('equity_growth', 0)):.2f}",
                f"- Retorno acumulado: {float(eq.get('cumulative_return', 0))*100:.2f}%",
                f"- Volatilidade: {float(eq.get('volatility', 0))*100:.2f}%",
                "",
            ])

        lines.extend([
            "Observação:",
            "- Esta análise apenas interpreta resultados de backtest já calculados.",
            "- Nenhuma regra de estratégia, lucro, odds ou simulação foi alterada neste patch.",
        ])
        return "\n".join(lines)
