"""
market_pricer.py — Cálculo de probabilidade justa e remoção de margem (vig).
Implementa métodos multiplicativo e aditivo para remoção de margem da casa.
A probabilidade justa é a base para todos os cálculos de EV corretos.
"""
from __future__ import annotations
import logging
from typing import Any
import pandas as pd

logger = logging.getLogger("matchflow.decision_engine.market_pricer")

def remove_vig_multiplicative(odds_list: list[float]) -> list[float]:
    """
    Remove a margem da casa multiplicativamente.
    Método mais preciso para mercados com distribuição simétrica.

    Exemplo:
        Over 2.5: 1.85, Under 2.5: 2.10
        probs brutas = [0.5405, 0.4762] → soma = 1.0167 (margem 1.67%)
        probs justas = [0.5316, 0.4684] → soma = 1.0000
    """
    if not odds_list or any(o <= 0 for o in odds_list):
        return [1.0 / len(odds_list)] * len(odds_list) if odds_list else []

    probs = [1.0 / o for o in odds_list]
    total = sum(probs)
    return [p / total for p in probs]

def remove_vig_additive(odds_list: list[float]) -> list[float]:
    """
    Remove a margem aditivamente (distribui margem uniformemente).
    Mais conservador, recomendado para mercados com favorito claro.
    """
    if not odds_list or any(o <= 0 for o in odds_list):
        return [1.0 / len(odds_list)] * len(odds_list) if odds_list else []

    probs = [1.0 / o for o in odds_list]
    total = sum(probs)
    vig = total - 1.0
    vig_per_outcome = vig / len(odds_list)
    return [max(0.001, p - vig_per_outcome) for p in probs]

def get_fair_probability(
    odds_over: float,
    odds_under: float,
    method: str = "multiplicative",
) -> tuple[float, float]:
    """
    Retorna (prob_over_justa, prob_under_justa) com margem removida.

    Args:
        odds_over: Odd do mercado Over (ex: 1.85)
        odds_under: Odd do mercado Under (ex: 2.10)
        method: "multiplicative" ou "additive"

    Returns:
        Tuple (fair_prob_over, fair_prob_under) normalizados para 1.0
    """
    if method == "additive":
        probs = remove_vig_additive([odds_over, odds_under])
    else:
        probs = remove_vig_multiplicative([odds_over, odds_under])
    return probs[0], probs[1]

def calculate_true_ev(
    ml_probability: float,
    odds_over: float,
    odds_under: float | None = None,
    method: str = "multiplicative",
) -> dict[str, float]:
    """
    Calcula Expected Value real comparando probabilidade ML com probabilidade JUSTA.

    Fórmula: True EV = (ml_prob - fair_prob) × (odds - 1)

    Diferente do EV ingênuo que compara contra odd bruta:
    - EV ingênuo: (ml_prob × odds) - 1  → ignora margem da casa, superestima edge
    - True EV: (ml_prob - fair_prob) × (odds - 1) → compara contra mercado eficiente

    Args:
        ml_probability: Probabilidade estimada pelo modelo ML (0-1)
        odds_over: Odd decimal do lado "over" ou seleção principal
        odds_under: Odd do lado oposto (para calcular probabilidade justa)
        method: Método de remoção de margem

    Returns:
        dict com true_ev, naive_ev, fair_probability, edge_over_market, vig_pct
    """
    # Odd bruta para EV ingênuo
    naive_ev = (ml_probability * odds_over) - 1.0

    # Probabilidade justa (removendo margem)
    if odds_under is not None and odds_under > 0:
        fair_prob, _ = get_fair_probability(odds_over, odds_under, method)
    else:
        # Sem odd oposta, estima margem típica de 5%
        implied_prob = 1.0 / odds_over
        estimated_vig = 0.05
        fair_prob = implied_prob * (1 - estimated_vig)

    # True EV: quanto o ML bate o mercado justo
    edge = ml_probability - fair_prob
    true_ev = edge * (odds_over - 1.0)

    # Margem da casa
    if odds_under is not None and odds_under > 0:
        vig_pct = (1.0 / odds_over + 1.0 / odds_under - 1.0) * 100
    else:
        vig_pct = None

    return {
        "true_ev": round(true_ev, 4),
        "naive_ev": round(naive_ev, 4),
        "fair_probability": round(fair_prob, 4),
        "ml_probability": round(ml_probability, 4),
        "edge_over_market": round(edge, 4),
        "edge_pct": round(edge * 100, 2),
        "vig_pct": round(vig_pct, 2) if vig_pct is not None else None,
        "is_value_bet": edge > 0.02,  # >2% acima do mercado justo
        "ev_grade": _grade_ev(true_ev, edge),
    }

def _grade_ev(true_ev: float, edge: float) -> str:
    """Classifica a qualidade do value bet."""
    if edge > 0.08 and true_ev > 0.05:
        return "PREMIUM_VALUE"
    if edge > 0.05 and true_ev > 0.03:
        return "HIGH_VALUE"
    if edge > 0.02 and true_ev > 0.01:
        return "VALUE"
    if edge > 0:
        return "MARGINAL"
    return "NO_VALUE"

def enrich_candidates_with_true_ev(candidates_df: pd.DataFrame) -> pd.DataFrame:
    """
    Enriquece DataFrame de candidatos com métricas de true EV.
    Espera colunas: ml_probability, odds (ou ensemble_probability).
    """
    if candidates_df.empty:
        return candidates_df

    df = candidates_df.copy()

    results = []
    for _, row in df.iterrows():
        ml_prob = float(row.get("ensemble_probability") or row.get("ml_probability") or 0.0)
        odds = float(row.get("odds") or 0.0)
        odds_opposite = float(row.get("odds_opposite") or row.get("odds_under") or 0.0)

        if ml_prob <= 0 or odds <= 0:
            results.append({
                "true_ev": None, "naive_ev": None, "fair_probability": None,
                "edge_over_market": None, "edge_pct": None, "vig_pct": None,
                "is_value_bet": False, "ev_grade": "UNKNOWN",
            })
            continue

        ev_data = calculate_true_ev(
            ml_probability=ml_prob,
            odds_over=odds,
            odds_under=odds_opposite if odds_opposite > 0 else None,
        )
        results.append(ev_data)

    ev_df = pd.DataFrame(results, index=df.index)
    for col in ev_df.columns:
        df[col] = ev_df[col]

    return df

if __name__ == "__main__":
    # Exemplo de uso
    print("=== Market Pricer Demo ===")

    # Over 2.5 a 1.85, Under 2.5 a 2.10
    over, under = 1.85, 2.10
    fair_over, fair_under = get_fair_probability(over, under)
    vig = (1/over + 1/under - 1) * 100

    print(f"\nOdds: Over {over} | Under {under}")
    print(f"Margem da casa (vig): {vig:.2f}%")
    print(f"Prob justa Over: {fair_over:.4f} ({fair_over*100:.2f}%)")
    print(f"Prob justa Under: {fair_under:.4f} ({fair_under*100:.2f}%)")

    # ML prevê 60% de prob para Over
    ev = calculate_true_ev(ml_probability=0.60, odds_over=1.85, odds_under=2.10)
    print(f"\nML prob: 60% | True EV: {ev['true_ev']:.4f} | Naive EV: {ev['naive_ev']:.4f}")
    print(f"Edge sobre mercado: {ev['edge_pct']:.2f}% | Grau: {ev['ev_grade']}")
