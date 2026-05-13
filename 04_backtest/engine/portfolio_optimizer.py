"""
portfolio_optimizer.py — Kelly Multivariado com correlação entre apostas.
Quando há 2+ apostas simultâneas, otimiza alocação considerando correlação.
Goals Over 2.5 e BTTS Yes no mesmo jogo são ~0.7 correlacionados.
Apostar ambos sem correção = sobrealocar capital no mesmo evento.
"""
from __future__ import annotations
import logging
from typing import Any
import numpy as np
import pandas as pd

logger = logging.getLogger("matchflow.backtest.portfolio_optimizer")

# Correlações estimadas entre mercados no mesmo jogo
MARKET_CORRELATIONS = {
    ("btts", "goals"):    0.72,
    ("corners", "goals"): 0.35,
    ("goals", "shots"):   0.45,
    ("btts", "corners"):  0.28,
    ("btts", "shots"):    0.38,
    ("corners", "shots"): 0.40,
}

def _get_correlation(market_a: str, market_b: str) -> float:
    key = tuple(sorted([market_a.lower(), market_b.lower()]))
    return MARKET_CORRELATIONS.get(key, 0.15)


def build_correlation_matrix(markets: list[str]) -> np.ndarray:
    """Constrói matriz de correlação NxN para lista de mercados."""
    n = len(markets)
    matrix = np.eye(n)  # diagonal = 1.0
    for i in range(n):
        for j in range(i + 1, n):
            corr = _get_correlation(markets[i], markets[j])
            matrix[i, j] = corr
            matrix[j, i] = corr
    return matrix


def portfolio_kelly(
    probabilities: list[float],
    odds: list[float],
    markets: list[str],
    bankroll: float = 1000.0,
    max_total_exposure: float = 0.15,  # máx 15% da banca no total
    max_per_bet: float = 0.05,          # máx 5% por aposta
    kelly_fraction: float = 0.25,
) -> dict[str, Any]:
    """
    Otimiza stakes considerando correlação entre apostas simultâneas.

    Minimiza -log_growth (equivale a maximizar Kelly multivariado)
    sujeito a: sum(stakes) <= max_total_exposure, stakes >= 0.

    Args:
        probabilities: lista de probabilidades ML (0-1)
        odds: lista de odds decimais
        markets: lista de nomes de mercados (para correlação)
        bankroll: banca atual
        max_total_exposure: exposição máxima total como fração da banca
        max_per_bet: exposição máxima por aposta como fração da banca
        kelly_fraction: fração do Kelly full

    Returns:
        dict com stakes_pct (frações da banca), stakes_units, correlation_matrix
    """
    n = len(probabilities)
    if n == 0:
        return {"stakes_pct": [], "stakes_units": [], "method": "empty"}

    if n == 1:
        # Uma aposta: Kelly simples
        prob, odd = probabilities[0], odds[0]
        if odd <= 1 or prob <= 0:
            return {"stakes_pct": [0.0], "stakes_units": [0.0], "method": "single_kelly"}
        b = odd - 1.0
        kelly = max(0, (b * prob - (1 - prob)) / b) * kelly_fraction
        stake_pct = max(0.0, min(max_per_bet, kelly))
        return {
            "stakes_pct": [stake_pct],
            "stakes_units": [bankroll * stake_pct],
            "method": "single_kelly",
        }

    # Multi-bet: tentar otimização com scipy
    try:
        from scipy.optimize import minimize
        correlation_matrix = build_correlation_matrix(markets)

        # EV por aposta
        evs = []
        for prob, odd in zip(probabilities, odds):
            b = odd - 1.0
            q = 1.0 - prob
            kelly_full = max(0, (b * prob - q) / b) if b > 0 else 0.0
            evs.append(kelly_full * kelly_fraction)

        def neg_log_growth(stakes: np.ndarray) -> float:
            """Função objetivo: -E[log(1 + resultado)]."""
            total_stake = np.sum(stakes)
            if total_stake <= 0:
                return 0.0
            # Simplificado: soma ponderada pelo EV ajustado por correlação
            adjusted_evs = []
            for i in range(n):
                ev_adj = evs[i]
                for j in range(n):
                    if i != j:
                        corr = correlation_matrix[i, j]
                        # Reduz EV quando há alta correlação com outra aposta já alocada
                        ev_adj -= 0.5 * corr * stakes[j] * evs[j]
                adjusted_evs.append(ev_adj)
            return -float(np.dot(stakes, adjusted_evs))

        x0 = np.array([min(max_per_bet / 2, evs[i]) for i in range(n)])
        bounds = [(0.0, max_per_bet)] * n
        constraints = [
            {"type": "ineq", "fun": lambda s: max_total_exposure - np.sum(s)},
        ]

        result = minimize(
            neg_log_growth, x0=x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 500, "ftol": 1e-8},
        )

        if result.success:
            stakes_pct = [max(0.0, round(float(s), 4)) for s in result.x]
        else:
            logger.debug("Otimização não convergiu: %s — usando Kelly independente", result.message)
            stakes_pct = [min(max_per_bet, e) for e in evs]

    except ImportError:
        logger.debug("scipy não disponível — usando Kelly independente com cap de correlação")
        # Fallback: Kelly independente com penalidade de correlação
        correlation_matrix = build_correlation_matrix(markets)
        base_stakes = []
        for prob, odd in zip(probabilities, odds):
            b = odd - 1.0 if odd > 1 else 0.001
            q = 1.0 - prob
            kelly = max(0, (b * prob - q) / b) * kelly_fraction if b > 0 else 0.0
            base_stakes.append(min(max_per_bet, kelly))

        # Reduzir apostas altamente correlacionadas
        stakes_pct = base_stakes.copy()
        for i in range(n):
            for j in range(i + 1, n):
                corr = correlation_matrix[i, j]
                if corr > 0.6:  # Alta correlação
                    # Reduzir a menor das duas apostas
                    if stakes_pct[i] < stakes_pct[j]:
                        stakes_pct[i] *= (1 - corr * 0.5)
                    else:
                        stakes_pct[j] *= (1 - corr * 0.5)

        # Normalizar se exceder limite total
        total = sum(stakes_pct)
        if total > max_total_exposure:
            factor = max_total_exposure / total
            stakes_pct = [s * factor for s in stakes_pct]

    stakes_units = [bankroll * pct for pct in stakes_pct]
    total_exposure = sum(stakes_pct)

    # Verificar se algum par está muito correlacionado
    high_corr_pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            corr = _get_correlation(markets[i], markets[j]) if i < len(markets) and j < len(markets) else 0
            if corr > 0.6:
                high_corr_pairs.append((markets[i], markets[j], round(corr, 2)))

    return {
        "stakes_pct": [round(s, 4) for s in stakes_pct],
        "stakes_units": [round(s, 2) for s in stakes_units],
        "total_exposure_pct": round(total_exposure, 4),
        "total_exposure_units": round(sum(stakes_units), 2),
        "method": "portfolio_kelly_optimized" if n > 1 else "single_kelly",
        "high_correlation_pairs": high_corr_pairs,
        "warning": "Apostas altamente correlacionadas detectadas — stakes reduzidas" if high_corr_pairs else None,
        "n_bets": n,
    }


def optimize_daily_portfolio(candidates_df: pd.DataFrame, bankroll: float = 1000.0) -> pd.DataFrame:
    """
    Aplica Portfolio Kelly nos candidatos do dia agrupados por data.
    Substitui kelly individual quando há múltiplas apostas simultâneas.
    """
    if candidates_df.empty:
        return candidates_df

    df = candidates_df.copy()

    # Apenas candidatos HIGH_CONFIDENCE com kelly > 0
    if "confidence_band" in df.columns:
        active = df[
            df["confidence_band"].str.contains("HIGH_CONFIDENCE", na=False) &
            (df.get("kelly_stake_pct", 0) > 0)
        ].copy()
    else:
        active = df.copy()

    if len(active) <= 1:
        return df  # Uma ou zero apostas: Kelly individual já está correto

    # Agrupar por data
    date_col = "date" if "date" in active.columns else None
    if date_col:
        for date_val, group in active.groupby(date_col):
            if len(group) < 2:
                continue

            probs = group["ensemble_probability"].fillna(0).tolist()
            odds_list = group["odds"].fillna(0).tolist()
            markets = group["market"].fillna("unknown").tolist()

            result = portfolio_kelly(probs, odds_list, markets, bankroll=bankroll)

            for i, idx in enumerate(group.index):
                if i < len(result["stakes_pct"]):
                    df.at[idx, "kelly_stake_pct"] = result["stakes_pct"][i]
                    df.at[idx, "kelly_stake_units"] = result["stakes_units"][i]
                    df.at[idx, "portfolio_optimized"] = True

    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
    probs = [0.58, 0.62, 0.55]
    odds_ = [1.85, 2.10, 1.75]
    markets_ = ["goals", "btts", "corners"]
    result = portfolio_kelly(probs, odds_, markets_, bankroll=1000.0)
    import json
    print(json.dumps(result, indent=2))
