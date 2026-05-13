"""
kelly_calculator.py — Kelly Criterion Simples e Fracionado.
Gestão de banca dinâmica baseada em probabilidade ML vs odds reais.
"""
from __future__ import annotations
import logging
import os
import numpy as np
from typing import Any
import pandas as pd

logger = logging.getLogger("matchflow.backtest.kelly_calculator")

def kelly_fraction(
    prob: float,
    odds: float,
    fraction: float | None = None,
    min_stake_pct: float = 0.005,
    max_stake_pct: float | None = None,
) -> float:
    """
    Kelly Criterion fracionado.

    Fórmula: f* = (b × p - q) / b   onde b = odds-1, q = 1-p
    Kelly fracionado: stake = f* × fraction

    Args:
        prob: Probabilidade estimada pelo ML (0-1)
        odds: Odd decimal (ex: 1.85)
        fraction: Fração do Kelly full (padrão: KELLY_FRACTION env, 0.25 = Quarter Kelly)
        min_stake_pct: Stake mínimo como % da banca
        max_stake_pct: Stake máximo como % da banca

    Returns:
        Fração da banca a apostar (0 a max_stake_pct)
    """
    if fraction is None:
        try:
            fraction = float(os.getenv("KELLY_FRACTION", "0.25"))
        except (TypeError, ValueError):
            fraction = 0.25

    if max_stake_pct is None:
        try:
            max_stake_pct = float(os.getenv("MAX_STAKE_PCT", "0.05"))
        except (TypeError, ValueError):
            max_stake_pct = 0.05

    if prob <= 0 or prob >= 1 or odds <= 1.0:
        return 0.0

    b = odds - 1.0
    q = 1.0 - prob
    kelly_full = (b * prob - q) / b

    if kelly_full <= 0:
        return 0.0  # Sem edge, não apostar

    stake = kelly_full * fraction
    stake = max(min_stake_pct, min(max_stake_pct, stake))
    return round(stake, 4)

def kelly_stake_units(
    prob: float,
    odds: float,
    bankroll: float,
    fraction: float | None = None,
) -> dict[str, float]:
    """
    Calcula stake em unidades monetárias.

    Returns:
        dict com stake_pct, stake_units, expected_profit, expected_loss
    """
    stake_pct = kelly_fraction(prob, odds, fraction)
    stake_units = bankroll * stake_pct
    expected_profit = stake_units * (odds - 1.0) * prob - stake_units * (1.0 - prob)

    return {
        "stake_pct": stake_pct,
        "stake_units": round(stake_units, 2),
        "expected_profit": round(expected_profit, 2),
        "kelly_full": round((odds - 1.0) * prob - (1.0 - prob)) / (odds - 1.0) if odds > 1 else 0.0,
        "bankroll": bankroll,
    }

def adaptive_kelly_multiplier(
    current_drawdown_pct: float,
    rolling_clv_7d: float | None = None,
    model_confidence: float = 1.0,
) -> float:
    """
    Modificador adaptativo do Kelly baseado em condições de banca.
    Reduz stakes automaticamente quando sistema está em dificuldade.

    Args:
        current_drawdown_pct: Drawdown atual como decimal (ex: 0.15 = 15%)
        rolling_clv_7d: CLV médio dos últimos 7 dias (None = não disponível)
        model_confidence: Confiança do ensemble (0-1)

    Returns:
        Multiplicador (0-1) aplicado ao Kelly
    """
    multiplier = 1.0

    # Proteção por drawdown
    if current_drawdown_pct >= 0.25:
        multiplier *= 0.0   # Hard stop
        logger.warning("HARD STOP: drawdown %.1f%% ≥ 25%%. Stakes zeradas.", current_drawdown_pct * 100)
    elif current_drawdown_pct > 0.19:
        multiplier *= 0.25  # Modo sobrevivência
        logger.warning("Modo sobrevivência: drawdown %.1f%%", current_drawdown_pct * 100)
    elif current_drawdown_pct > 0.09:
        multiplier *= 0.50  # Modo defensivo
        logger.info("Modo defensivo: drawdown %.1f%%", current_drawdown_pct * 100)

    # Edge deterioration: CLV negativo = edge se deteriorou
    if rolling_clv_7d is not None and rolling_clv_7d < -0.02:
        multiplier *= 0.50
        logger.warning("Edge deterioração detectada: CLV 7d = %.2f%%", rolling_clv_7d * 100)

    # Incerteza do modelo
    if model_confidence < 0.55:
        multiplier *= 0.75
        logger.info("Confiança do modelo baixa: %.2f", model_confidence)

    return max(0.0, min(1.0, multiplier))

def calculate_kelly_for_candidates(
    candidates_df: pd.DataFrame,
    bankroll: float | None = None,
    current_drawdown: float = 0.0,
    rolling_clv_7d: float | None = None,
) -> pd.DataFrame:
    """
    Calcula Kelly para todos os candidatos do decision engine.
    Adiciona colunas: kelly_stake_pct, kelly_stake_units, adaptive_multiplier.
    """
    if candidates_df.empty:
        return candidates_df

    if bankroll is None:
        try:
            bankroll = float(os.getenv("INITIAL_BANKROLL", "1000.0"))
        except (TypeError, ValueError):
            bankroll = 1000.0

    df = candidates_df.copy()
    adaptive_mult = adaptive_kelly_multiplier(current_drawdown, rolling_clv_7d)

    kelly_pcts = []
    kelly_units = []

    for _, row in df.iterrows():
        prob = float(row.get("ensemble_probability") or row.get("ml_probability") or 0.0)
        odds = float(row.get("odds") or 0.0)
        true_ev = float(row.get("true_ev") or row.get("edge_over_market") or 0.0)

        # Só apostar se houver edge real (true_ev > 0)
        if true_ev <= 0.0 and prob > 0 and odds > 0:
            kelly_pcts.append(0.0)
            kelly_units.append(0.0)
            continue

        base_kelly = kelly_fraction(prob, odds) if prob > 0 and odds > 1 else 0.0
        adjusted_kelly = base_kelly * adaptive_mult
        units = bankroll * adjusted_kelly

        kelly_pcts.append(round(adjusted_kelly, 4))
        kelly_units.append(round(units, 2))

    df["kelly_stake_pct"] = kelly_pcts
    df["kelly_stake_units"] = kelly_units
    df["adaptive_multiplier"] = adaptive_mult
    df["action_required"] = (
        (df.get("confidence_band", "") == "HIGH_CONFIDENCE_SIMULATION") &
        (df["kelly_stake_pct"] > 0) &
        (df.get("true_ev", 0) > 0.02)
    )

    return df

if __name__ == "__main__":
    print("=== Kelly Calculator Demo ===")
    prob, odds = 0.58, 1.85
    stake = kelly_fraction(prob, odds, fraction=0.25)
    info = kelly_stake_units(prob, odds, bankroll=1000.0)
    print(f"\nML prob: {prob:.0%} | Odds: {odds}")
    print(f"Quarter Kelly stake: {stake:.2%} da banca")
    print(f"Stake em R$: R${info['stake_units']:.2f}")
    print(f"Expected profit: R${info['expected_profit']:.2f}")

    print("\n--- Adaptive Kelly ---")
    print(f"Drawdown 0%:  mult={adaptive_kelly_multiplier(0.00):.2f}")
    print(f"Drawdown 10%: mult={adaptive_kelly_multiplier(0.10):.2f}")
    print(f"Drawdown 20%: mult={adaptive_kelly_multiplier(0.20):.2f}")
    print(f"Drawdown 25%: mult={adaptive_kelly_multiplier(0.25):.2f}")
