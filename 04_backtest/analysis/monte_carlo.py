"""
monte_carlo.py — Simulação de Monte Carlo para projeção de banca.
Projeta distribuição de resultados futuros dado o edge estimado.
"""
from __future__ import annotations
import json, logging
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

logger = logging.getLogger("matchflow.backtest.monte_carlo")

def monte_carlo_bankroll(
    edge_per_bet: float,        # CLV médio estimado (ex: 0.03 = 3%)
    bets_per_week: float,       # frequência de apostas por semana
    kelly_fraction: float,      # agressividade das stakes (ex: 0.25)
    initial_bankroll: float,    # banca inicial
    simulations: int = 10_000,  # número de simulações
    weeks: int = 26,            # horizonte temporal (26 = 6 meses)
    odds_mean: float = 1.85,    # odd média das apostas
    odds_std: float = 0.20,     # desvio padrão das odds
    seed: int = 42,
) -> dict[str, Any]:
    """
    Roda N simulações de Monte Carlo do crescimento da banca.

    Returns:
        dict com percentis, probabilidade de ruína, Kelly ótimo
    """
    rng = np.random.default_rng(seed)
    total_bets = int(bets_per_week * weeks)

    # Converter CLV em win probability para uma odd típica
    # CLV = (prob × odds) - 1  →  prob = (1 + clv) / odds
    win_prob = (1 + edge_per_bet) / odds_mean
    win_prob = max(0.01, min(0.99, win_prob))

    final_bankrolls = []
    ruin_count = 0
    all_curves = []
    RUIN_THRESHOLD = 0.1  # < 10% da banca inicial = ruína

    for _ in range(simulations):
        bankroll = initial_bankroll
        curve = [bankroll]
        ruined = False

        for _ in range(total_bets):
            if bankroll < initial_bankroll * RUIN_THRESHOLD:
                ruined = True
                break

            # Odd aleatória em torno da média
            bet_odds = max(1.05, rng.normal(odds_mean, odds_std))

            # Recalcular Kelly com banca atual
            b = bet_odds - 1.0
            q = 1.0 - win_prob
            kelly_full = (b * win_prob - q) / b if b > 0 else 0.0
            stake_pct = max(0, min(0.05, kelly_full * kelly_fraction))
            stake = bankroll * stake_pct

            # Resultado
            if rng.random() < win_prob:
                bankroll += stake * (bet_odds - 1.0)
            else:
                bankroll -= stake

            curve.append(bankroll)

        final_bankrolls.append(bankroll if not ruined else initial_bankroll * RUIN_THRESHOLD)
        if ruined:
            ruin_count += 1
        if len(all_curves) < 100:  # Guardar apenas 100 curvas para visualização
            all_curves.append(curve[:min(len(curve), 200)])

    arr = np.array(final_bankrolls)

    # Calcular Kelly ótimo (maximiza crescimento logarítmico esperado)
    # Kelly ótimo = (win_prob × odds - 1) / (odds - 1)
    b = odds_mean - 1.0
    q = 1.0 - win_prob
    kelly_optimal_full = max(0, (b * win_prob - q) / b) if b > 0 else 0.0
    kelly_optimal_quarter = kelly_optimal_full * 0.25

    # Tempo esperado para dobrar banca (meses)
    if kelly_optimal_full > 0:
        bets_to_double = np.log(2) / (bets_per_week * 52 / 12 * np.log(1 + kelly_optimal_full * edge_per_bet + 1e-9))
        months_to_double = bets_to_double
    else:
        months_to_double = None

    return {
        "ok": True,
        "simulations": simulations,
        "weeks": weeks,
        "initial_bankroll": initial_bankroll,
        "inputs": {
            "edge_per_bet": edge_per_bet,
            "bets_per_week": bets_per_week,
            "kelly_fraction": kelly_fraction,
            "odds_mean": odds_mean,
            "win_probability": round(win_prob, 4),
        },
        "projections": {
            "p10": round(float(np.percentile(arr, 10)), 2),
            "p25": round(float(np.percentile(arr, 25)), 2),
            "p50_median": round(float(np.percentile(arr, 50)), 2),
            "p75": round(float(np.percentile(arr, 75)), 2),
            "p90": round(float(np.percentile(arr, 90)), 2),
            "mean": round(float(np.mean(arr)), 2),
            "std": round(float(np.std(arr)), 2),
        },
        "risk": {
            "ruin_probability": round(ruin_count / simulations, 4),
            "ruin_probability_pct": round(ruin_count / simulations * 100, 2),
            "ruin_threshold": RUIN_THRESHOLD,
            "prob_below_start": round(float((arr < initial_bankroll).mean()), 4),
            "prob_doubling": round(float((arr >= initial_bankroll * 2).mean()), 4),
        },
        "kelly": {
            "optimal_full": round(kelly_optimal_full, 4),
            "optimal_quarter": round(kelly_optimal_quarter, 4),
            "used_fraction": kelly_fraction,
            "suggested_fraction": 0.25 if edge_per_bet < 0.05 else 0.30,
        },
        "time": {
            "months_to_double_estimate": round(months_to_double, 1) if months_to_double else None,
            "horizon_weeks": weeks,
            "total_bets_simulated": total_bets,
        },
        "sample_curves": all_curves[:20],  # 20 curvas para visualização
    }

def run_scenario_analysis(
    clv_scenarios: list[float],
    initial_bankroll: float = 1000.0,
    bets_per_week: float = 5.0,
    kelly_fraction: float = 0.25,
    weeks: int = 26,
) -> list[dict]:
    """
    Roda análise de cenários para diferentes níveis de edge.
    """
    results = []
    for clv in clv_scenarios:
        result = monte_carlo_bankroll(
            edge_per_bet=clv,
            bets_per_week=bets_per_week,
            kelly_fraction=kelly_fraction,
            initial_bankroll=initial_bankroll,
            weeks=weeks,
            simulations=5000,
        )
        results.append({
            "clv_pct": round(clv * 100, 1),
            "median_6m": result["projections"]["p50_median"],
            "ruin_prob_pct": result["risk"]["ruin_probability_pct"],
            "prob_doubling_pct": round(result["risk"]["prob_doubling"] * 100, 1),
        })
    return results

def save_monte_carlo_report(root: Path | None = None) -> dict[str, Any]:
    """
    Gera e salva relatório de Monte Carlo baseado no edge atual.
    """
    root = root or Path.cwd()
    output_dir = root / "data/performance"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Tentar carregar CLV real
    clv_path = root / "data/performance/clv_history.parquet"
    edge = 0.03  # default conservador
    try:
        if clv_path.exists():
            clv_df = safe_read_dataframe(clv_path)
            if not clv_df.empty and "clv" in clv_df.columns:
                edge = float(clv_df["clv"].dropna().mean())
                edge = max(-0.05, min(0.15, edge))  # sanity check
    except Exception:
        pass

    try:
        bankroll = float(__import__("os").getenv("INITIAL_BANKROLL", "1000.0"))
    except Exception:
        bankroll = 1000.0

    result = monte_carlo_bankroll(
        edge_per_bet=edge,
        bets_per_week=5.0,
        kelly_fraction=0.25,
        initial_bankroll=bankroll,
    )

    scenarios = run_scenario_analysis(
        clv_scenarios=[-0.01, 0.0, 0.02, 0.03, 0.05, 0.08],
        initial_bankroll=bankroll,
    )
    result["scenarios"] = scenarios

    out_path = output_dir / "monte_carlo_report.json"
    out_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    logger.info("Monte Carlo report salvo em %s (edge=%.2f%%)", out_path, edge * 100)
    return result

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
    result = monte_carlo_bankroll(
        edge_per_bet=0.035,
        bets_per_week=5,
        kelly_fraction=0.25,
        initial_bankroll=1000.0,
    )
    print(json.dumps({
        "projections": result["projections"],
        "risk": result["risk"],
        "kelly": result["kelly"],
    }, indent=2))
