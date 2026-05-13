from __future__ import annotations

from typing import Any, Dict

import pandas as pd


def _fmt_pct(value: float) -> str:
    return f"{float(value) * 100:.2f}%"


def build_deep_insights(
    qualified: pd.DataFrame,
    odds_ranges: pd.DataFrame,
    league_market: pd.DataFrame,
    rolling: pd.DataFrame,
    consistency: pd.DataFrame,
    risk_flags: pd.DataFrame,
    config: Dict[str, Any],
) -> str:
    lines: list[str] = []
    lines.append("MATCHFLOW ANALYTICS — DEEP BACKTEST ANALYSIS")
    lines.append("=" * 72)
    lines.append("")
    lines.append("Objetivo: identificar se existe edge real ou apenas ruído estatístico.")
    lines.append("Regra crítica: estratégias com LOW_SAMPLE não devem ser tratadas como edge confiável.")
    lines.append("")

    if qualified.empty:
        lines.append("Nenhuma estratégia qualificada foi encontrada.")
        return "\n".join(lines)

    reliable = qualified[qualified["is_edge_reliable"] == True].copy()
    low_sample = qualified[qualified["sample_class"] == "LOW_SAMPLE"].copy()

    lines.append("1) Estratégias mais consistentes")
    if reliable.empty:
        lines.append("- Nenhuma estratégia atingiu simultaneamente amostra mínima, ROI positivo e profit factor mínimo.")
        lines.append("- Isso NÃO significa que o sistema falhou; significa que ainda não há evidência estatística suficiente de edge.")
    else:
        for _, row in reliable.head(5).iterrows():
            lines.append(
                f"- {row['strategy']} / {row['market']}: trades={int(row['total_trades'])}, ROI={_fmt_pct(row['roi'])}, PF={float(row['profit_factor']):.2f}, amostra={row['sample_class']}."
            )
    lines.append("")

    lines.append("2) Estratégias que devem ser descartadas ou não promovidas ainda")
    if low_sample.empty:
        lines.append("- Nenhuma estratégia ficou abaixo da amostra mínima.")
    else:
        for _, row in low_sample.head(10).iterrows():
            lines.append(
                f"- {row['strategy']} / {row['market']}: LOW_SAMPLE com {int(row['total_trades'])} trades. Risco alto de falso edge."
            )
    lines.append("")

    lines.append("3) Faixas de odds com melhor comportamento")
    if odds_ranges.empty:
        lines.append("- Não há dados suficientes por faixa de odds.")
    else:
        best_odds = odds_ranges.sort_values(["roi", "profit_factor", "total_trades"], ascending=[False, False, False]).head(5)
        for _, row in best_odds.iterrows():
            lines.append(
                f"- Mercado {row['market']} odds {row['odds_range']}: trades={int(row['total_trades'])}, ROI={_fmt_pct(row['roi'])}, PF={float(row['profit_factor']):.2f}."
            )
    lines.append("")

    lines.append("4) Dependência de liga/mercado")
    if league_market.empty:
        lines.append("- Não há matriz liga x mercado disponível.")
    else:
        candidates = league_market[league_market["risk_level"] == "HIGH_EDGE_CANDIDATE"].head(5)
        if candidates.empty:
            lines.append("- Nenhuma combinação liga x mercado atingiu critério de HIGH_EDGE_CANDIDATE.")
        else:
            for _, row in candidates.iterrows():
                lines.append(
                    f"- {row['league']} / {row['market']}: trades={int(row['total_trades'])}, ROI={_fmt_pct(row['roi'])}, PF={float(row['profit_factor']):.2f}."
                )
    lines.append("")

    lines.append("5) Alertas de risco")
    if risk_flags.empty:
        lines.append("- Nenhum risco crítico foi gerado. Ainda assim, valide amostra e estabilidade antes de qualquer conclusão.")
    else:
        flags_count = risk_flags["flag"].value_counts().to_dict()
        for flag, count in flags_count.items():
            lines.append(f"- {flag}: {count} ocorrência(s).")
        high = risk_flags[risk_flags["severity"] == "HIGH"].head(8)
        for _, row in high.iterrows():
            lines.append(f"  • {row['strategy']} / {row['market']}: {row['message']}")
    lines.append("")

    lines.append("6) Risco de falso edge")
    if not low_sample.empty:
        lines.append("- Existe risco material de falso edge porque parte das estratégias tem amostra abaixo do mínimo configurado.")
    if not rolling.empty and (rolling["negative_windows_pct"] > 0.40).any():
        lines.append("- Algumas estratégias têm muitas janelas móveis negativas, sugerindo instabilidade temporal.")
    lines.append("- Use este relatório como filtro de qualidade estatística, não como recomendação operacional.")
    lines.append("")
    lines.append("Próximo passo recomendado: aumentar amostra histórica por liga/mercado antes de promover qualquer estratégia para produção.")
    return "\n".join(lines)
