from __future__ import annotations

from typing import Any, Mapping

MODE = "PAPER_TRADING_SIMULATION_ONLY"


def build_explanation(row: Mapping[str, Any]) -> dict[str, Any]:
    score = float(row.get("decision_score", 0) or 0)
    flags = row.get("risk_flags") or []
    if isinstance(flags, str):
        flags = [item.strip() for item in flags.split(",") if item.strip()]

    strengths = []
    if str(row.get("rule_status", "")).upper() == "KEEP":
        strengths.append("Regra refinada classificada como KEEP.")
    if float(row.get("ml_probability", 0) or 0) >= 0.60:
        strengths.append("Probabilidade ML acima de 60%.")
    if float(row.get("ensemble_probability", 0) or 0) >= 0.60:
        strengths.append("Probabilidade ensemble acima de 60%.")
    if float(row.get("consistency_score", 0) or 0) >= 60:
        strengths.append("Consistency score mínimo atendido.")

    risks = list(flags) if flags else ["Nenhum risk flag crítico identificado no contexto disponível."]
    if score < 60:
        why = "Candidato mantido apenas para observação ou rejeitado pela combinação de score e risco."
    elif score < 80:
        why = "Candidato de simulação com confiança média, sujeito a validação contínua."
    else:
        why = "Candidato de simulação com score alto, sem conversão em ação real."

    return {
        "why_selected": why,
        "main_strengths": strengths or ["Sinal preservado para pesquisa comparativa."],
        "main_risks": risks,
        "data_quality_notes": row.get("data_quality_notes") or "Avaliar disponibilidade de odds, amostra e consistência antes de qualquer uso futuro.",
        "simulation_label": MODE,
    }
