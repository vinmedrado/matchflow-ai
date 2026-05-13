
from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from backend.core.logging_config import get_logger
from refinement.common import risk_level_from_flags, safe_int

logger = get_logger("matchflow.backtest.refinement.report")


class RefinementReport:
    def build_risk_report(self, rejected_df: pd.DataFrame, refined_df: pd.DataFrame, flags_df: pd.DataFrame, qualified_df: pd.DataFrame) -> pd.DataFrame:
        columns = ["strategy", "market", "risk_flags", "sample_status", "dependency_risk", "temporal_instability", "overfitting_risk", "final_recommendation"]
        rows: List[Dict[str, Any]] = []
        combined = pd.concat([
            refined_df.assign(source_recommendation="KEEP") if not refined_df.empty else pd.DataFrame(),
            rejected_df.assign(source_recommendation="DISCARD") if not rejected_df.empty else pd.DataFrame(),
        ], ignore_index=True)

        if combined.empty:
            return pd.DataFrame(columns=columns)

        for _, row in combined.iterrows():
            strategy = str(row.get("strategy", ""))
            market = str(row.get("market", ""))
            strategy_flags = []
            if not flags_df.empty and "flag" in flags_df.columns:
                mask = flags_df.get("strategy", pd.Series(dtype=str)).astype(str) == strategy
                if "market" in flags_df.columns:
                    mask &= flags_df["market"].astype(str) == market
                strategy_flags = sorted(set(flags_df[mask]["flag"].astype(str).tolist()))
            row_flags = str(row.get("risk_flags", ""))
            if row_flags:
                strategy_flags = sorted(set(strategy_flags + [flag for flag in row_flags.split("|") if flag]))
            sample_status = self._sample_status(strategy, market, qualified_df, row)
            dependency_risk = "HIGH" if any(flag in {"LEAGUE_DEPENDENCY", "ODDS_RANGE_DEPENDENCY"} for flag in strategy_flags) else "LOW"
            temporal_instability = "HIGH" if any(flag in {"UNSTABLE_ROI", "NEGATIVE_ROLLING_ROI"} for flag in strategy_flags) else "LOW"
            overfitting_risk = risk_level_from_flags(strategy_flags)
            recommendation = str(row.get("recommendation", row.get("source_recommendation", "DISCARD")))
            if sample_status == "LOW_SAMPLE" and recommendation == "KEEP":
                recommendation = "DISCARD"
            rows.append({
                "strategy": strategy,
                "market": market,
                "risk_flags": "|".join(strategy_flags),
                "sample_status": sample_status,
                "dependency_risk": dependency_risk,
                "temporal_instability": temporal_instability,
                "overfitting_risk": overfitting_risk,
                "final_recommendation": recommendation,
            })
        out = pd.DataFrame(rows, columns=columns)
        logger.info("Refinement risk report gerado: linhas=%s", len(out))
        return out

    def _sample_status(self, strategy: str, market: str, qualified_df: pd.DataFrame, row: pd.Series) -> str:
        if not qualified_df.empty and "sample_class" in qualified_df.columns:
            mask = qualified_df.get("strategy", pd.Series(dtype=str)).astype(str) == strategy
            if "market" in qualified_df.columns:
                mask &= qualified_df["market"].astype(str) == market
            matched = qualified_df[mask]
            if not matched.empty:
                return str(matched.iloc[0].get("sample_class", "UNKNOWN"))
        trades = safe_int(row.get("total_trades"))
        if trades < 50:
            return "LOW_SAMPLE"
        if trades < 100:
            return "ACCEPTABLE_SAMPLE"
        return "STRONG_SAMPLE"

    def build_insights(
        self,
        refined_df: pd.DataFrame,
        rejected_df: pd.DataFrame,
        threshold_df: pd.DataFrame,
        market_df: pd.DataFrame,
        league_df: pd.DataFrame,
        odds_df: pd.DataFrame,
        risk_df: pd.DataFrame,
    ) -> str:
        lines: List[str] = []
        lines.append("MatchFlow Analytics — Patch 4.3 Strategy Refinement")
        lines.append("Objetivo: separar candidatos reais de ruído estatístico sem alterar backtest, lucro, banca ou estratégias.")
        lines.append("")
        lines.append(f"Total de estratégias candidatas KEEP: {len(refined_df)}")
        lines.append(f"Total de estratégias rejeitadas: {len(rejected_df)}")
        lines.append(f"Total de filtros candidatos sugeridos: {len(threshold_df)}")
        lines.append("")

        if refined_df.empty:
            lines.append("Estratégia candidata:")
            lines.append("- Nenhuma estratégia passou todos os critérios mínimos. Isso é correto quando a amostra é baixa, o drawdown é alto ou a estabilidade temporal é fraca.")
        else:
            lines.append("Estratégias candidatas:")
            for _, row in refined_df.head(10).iterrows():
                lines.append(f"- strategy: {row.get('strategy')} | market: {row.get('market')} | ROI: {float(row.get('roi', 0))*100:.2f}% | Trades: {int(row.get('total_trades', 0))} | PF: {float(row.get('profit_factor', 0)):.2f} | Max DD: {float(row.get('max_drawdown', 0)):.2f}% | Score: {float(row.get('consistency_score', 0)):.1f} | Recomendação: KEEP")
        lines.append("")

        lines.append("Estratégias rejeitadas principais:")
        if rejected_df.empty:
            lines.append("- Nenhuma rejeição registrada.")
        else:
            for _, row in rejected_df.head(10).iterrows():
                lines.append(f"- strategy: {row.get('strategy')} | market: {row.get('market')} | Trades: {int(row.get('total_trades', 0))} | ROI: {float(row.get('roi', 0))*100:.2f}% | Motivo: {row.get('rejection_reasons')}")
        lines.append("")

        lines.append("Mercados:")
        if market_df.empty:
            lines.append("- Sem dados suficientes para classificar mercados.")
        else:
            for _, row in market_df.head(10).iterrows():
                lines.append(f"- market: {row.get('market')} | class: {row.get('classification')} | ROI: {float(row.get('roi', 0))*100:.2f}% | Trades: {int(row.get('total_trades', 0))} | PF: {float(row.get('profit_factor', 0)):.2f}")
        lines.append("")

        lines.append("Faixas de odds favoráveis:")
        favorable = odds_df[odds_df.get("classification", "") == "FAVORABLE"] if not odds_df.empty else pd.DataFrame()
        if favorable.empty:
            lines.append("- Nenhuma faixa de odds foi classificada como FAVORABLE com os critérios atuais.")
        else:
            for _, row in favorable.head(10).iterrows():
                lines.append(f"- market: {row.get('market')} | odds_range: {row.get('odds_range')} | ROI: {float(row.get('roi', 0))*100:.2f}% | Trades: {int(row.get('total_trades', 0))}")
        lines.append("")

        lines.append("Riscos principais:")
        if risk_df.empty:
            lines.append("- Nenhum risco consolidado foi gerado.")
        else:
            for _, row in risk_df.head(10).iterrows():
                lines.append(f"- strategy: {row.get('strategy')} | sample: {row.get('sample_status')} | dependency: {row.get('dependency_risk')} | temporal: {row.get('temporal_instability')} | overfitting: {row.get('overfitting_risk')} | final: {row.get('final_recommendation')}")
        lines.append("")

        lines.append("Nota crítica:")
        lines.append("- Threshold candidates são apenas sugestões de investigação. O sistema NÃO otimiza automaticamente filtros e NÃO transforma amostra pequena em edge confiável.")
        lines.append("- Estratégias com LOW_SAMPLE não devem ser tratadas como KEEP.")
        return "\n".join(lines) + "\n"
