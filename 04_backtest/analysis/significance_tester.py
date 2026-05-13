"""
significance_tester.py — Testes de significância estatística para edge.
Bloqueia estratégias sem significância comprovada (mín. 300 trades, p < 0.05).
"""
from __future__ import annotations
import json, logging
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

try:
    from scipy import stats
    _SCIPY_OK = True
except ImportError:
    _SCIPY_OK = False

logger = logging.getLogger("matchflow.backtest.significance_tester")

MIN_TRADES_THRESHOLD = 300
P_VALUE_THRESHOLD = 0.05
MIN_CLV_THRESHOLD = 0.02    # 2% CLV mínimo para considerar edge
MIN_BRIER_SCORE = 0.25      # < 0.25 = boa calibração

def validate_edge_statistical(
    trades: list[dict] | pd.DataFrame,
    min_trades: int = MIN_TRADES_THRESHOLD,
    min_clv: float = MIN_CLV_THRESHOLD,
    p_threshold: float = P_VALUE_THRESHOLD,
) -> dict[str, Any]:
    """
    Testa se o edge de uma estratégia é estatisticamente significativo.

    Args:
        trades: Lista/DataFrame de trades com campo 'clv' (ou 'profit')
        min_trades: Mínimo de trades necessários
        min_clv: CLV médio mínimo para considerar válido
        p_threshold: Nível de significância

    Returns:
        dict com is_significant, z_score, p_value, reasoning
    """
    if isinstance(trades, pd.DataFrame):
        df = trades.copy()
    else:
        df = pd.DataFrame(trades)

    n = len(df)
    if n < min_trades:
        required = min_trades - n
        return {
            "is_significant": False,
            "reason": f"INSUFFICIENT_SAMPLE",
            "trades": n,
            "required_additional_trades": required,
            "message": f"Necessário {min_trades} trades (atual: {n}, faltam {required})",
            "p_value": None,
            "z_score": None,
            "mean_clv": None,
            "confidence_interval_95": None,
        }

    # Usar CLV se disponível, senão usar ROI por trade
    if "clv" in df.columns and df["clv"].notna().sum() > min_trades * 0.5:
        values = df["clv"].dropna().values
        metric_name = "CLV"
    elif "profit" in df.columns and "stake" in df.columns:
        df["roi_per_trade"] = df["profit"] / df["stake"].replace(0, np.nan)
        values = df["roi_per_trade"].dropna().values
        metric_name = "ROI_per_trade"
    elif "is_win" in df.columns:
        values = df["is_win"].astype(float).values
        metric_name = "win_rate"
    else:
        return {"is_significant": False, "reason": "NO_METRIC_COLUMN", "trades": n}

    if not _SCIPY_OK:
        # Fallback manual sem scipy
        mean_val = float(np.mean(values))
        std_val = float(np.std(values, ddof=1))
        se = std_val / np.sqrt(len(values))
        z = mean_val / se if se > 0 else 0.0
        # Approximação normal para p-value (bilateral)
        p_approx = 2 * (1 - _norm_cdf(abs(z)))
        is_sig = p_approx < p_threshold and mean_val > min_clv
        return {
            "is_significant": is_sig,
            "trades": n,
            "mean_clv": round(mean_val, 4),
            "z_score": round(z, 3),
            "p_value": round(p_approx, 4),
            "metric": metric_name,
            "reason": "SIGNIFICANT" if is_sig else ("LOW_CLV" if mean_val <= min_clv else "NOT_SIGNIFICANT"),
            "confidence_interval_95": None,
            "note": "Scipy não disponível — usando aproximação normal",
        }

    t_stat, p_value = stats.ttest_1samp(values, popmean=0)
    mean_val = float(np.mean(values))
    ci = stats.t.interval(0.95, len(values) - 1, loc=mean_val, scale=stats.sem(values))

    is_significant = (
        p_value < p_threshold and
        mean_val > min_clv and
        t_stat > 0
    )

    reason = "SIGNIFICANT"
    if not is_significant:
        if mean_val <= 0:
            reason = "NEGATIVE_EDGE"
        elif mean_val <= min_clv:
            reason = "BELOW_MIN_CLV"
        else:
            reason = "NOT_SIGNIFICANT"

    # Calcular trades necessários para significância (se ainda não é sig)
    required_for_sig = None
    if not is_significant and mean_val > 0:
        # n_required ≈ (z_alpha * sigma / mu)^2
        sigma = float(np.std(values, ddof=1))
        if sigma > 0 and mean_val > 0:
            z_alpha = 1.645  # 95% one-tailed
            required_for_sig = int(np.ceil((z_alpha * sigma / mean_val) ** 2))

    return {
        "is_significant": is_significant,
        "reason": reason,
        "trades": n,
        "mean_clv": round(mean_val, 4),
        "mean_clv_pct": round(mean_val * 100, 2),
        "z_score": round(float(t_stat), 3),
        "p_value": round(float(p_value), 4),
        "confidence_interval_95": [round(float(ci[0]), 4), round(float(ci[1]), 4)],
        "metric": metric_name,
        "required_trades_for_significance": required_for_sig,
        "probability_of_luck": round(float(p_value) * 100, 2),
    }

def validate_brier_score(probabilities: list[float], outcomes: list[int]) -> dict[str, Any]:
    """
    Calcula Brier Score para avaliar calibração do modelo ML.
    Brier Score < 0.25 = boa calibração (melhor que aleatório).
    Brier Score próximo de 0 = calibração perfeita.
    """
    if len(probabilities) != len(outcomes) or len(probabilities) == 0:
        return {"brier_score": None, "calibration_grade": "UNKNOWN"}

    probs = np.array(probabilities, dtype=float)
    outs = np.array(outcomes, dtype=float)
    brier = float(np.mean((probs - outs) ** 2))

    if brier < 0.10:
        grade = "EXCELLENT"
    elif brier < 0.20:
        grade = "GOOD"
    elif brier < 0.25:
        grade = "ACCEPTABLE"
    elif brier < 0.33:
        grade = "POOR"
    else:
        grade = "RANDOM"

    return {
        "brier_score": round(brier, 4),
        "calibration_grade": grade,
        "is_well_calibrated": brier < MIN_BRIER_SCORE,
        "random_baseline": 0.25,
        "trades": len(probabilities),
    }

def run_significance_gate(
    strategy_name: str,
    market: str,
    trades_df: pd.DataFrame,
    probabilities: list[float] | None = None,
    outcomes: list[int] | None = None,
) -> dict[str, Any]:
    """
    Gate de significância: uma estratégia só passa se satisfizer todos os critérios.
    """
    edge_test = validate_edge_statistical(trades_df)
    brier = {}
    if probabilities and outcomes:
        brier = validate_brier_score(probabilities, outcomes)

    gate_pass = (
        edge_test.get("is_significant", False) and
        (not brier or brier.get("is_well_calibrated", True))
    )

    result = {
        "strategy": strategy_name,
        "market": market,
        "gate_pass": gate_pass,
        "edge_test": edge_test,
        "brier_test": brier,
        "verdict": "VALIDATED" if gate_pass else "REJECTED",
        "rejection_reason": None if gate_pass else _build_rejection_reason(edge_test, brier),
    }
    logger.info(
        "Significance gate: %s/%s → %s (trades=%s, p=%.4f)",
        strategy_name, market, result["verdict"],
        edge_test.get("trades"), edge_test.get("p_value") or 0,
    )
    return result

def _build_rejection_reason(edge_test: dict, brier: dict) -> str:
    reasons = []
    if not edge_test.get("is_significant"):
        reasons.append(edge_test.get("reason", "NOT_SIGNIFICANT"))
    if brier and not brier.get("is_well_calibrated", True):
        reasons.append(f"POOR_CALIBRATION:{brier.get('calibration_grade')}")
    return " | ".join(reasons)

def _norm_cdf(x: float) -> float:
    """Aproximação da CDF normal para fallback sem scipy."""
    t = 1.0 / (1.0 + 0.2316419 * abs(x))
    poly = t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))))
    return 1.0 - (1.0 / np.sqrt(2 * np.pi)) * np.exp(-x * x / 2) * poly

def analyze_all_strategies(root: Path | None = None) -> dict[str, Any]:
    """Roda o significance gate em todas as estratégias do backtest."""
    root = root or Path.cwd()
    refinement_path = root / "data/backtest/refinement/refined_strategy_candidates.csv"
    signals_path = root / "data/paper_trading/paper_signals.csv"
    output_dir = root / "data/backtest/analysis/significance"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not refinement_path.exists():
        return {"ok": False, "reason": "NO_REFINEMENT_DATA"}

    strategies = pd.read_csv(refinement_path)
    signals = pd.read_csv(signals_path) if signals_path.exists() else pd.DataFrame()

    results = []
    for _, strat in strategies.iterrows():
        name = str(strat.get("strategy", ""))
        market = str(strat.get("market", ""))
        strat_signals = signals[
            (signals.get("strategy") == name) & (signals.get("market") == market)
        ] if not signals.empty and "strategy" in signals.columns else pd.DataFrame()

        gate = run_significance_gate(name, market, strat_signals)
        results.append(gate)

    results_df = pd.DataFrame([{
        "strategy": r["strategy"],
        "market": r["market"],
        "gate_pass": r["gate_pass"],
        "verdict": r["verdict"],
        "trades": r["edge_test"].get("trades"),
        "mean_clv_pct": r["edge_test"].get("mean_clv_pct"),
        "p_value": r["edge_test"].get("p_value"),
        "rejection_reason": r.get("rejection_reason"),
    } for r in results])

    results_df.to_csv(output_dir / "significance_gate_results.csv", index=False)
    summary = {
        "ok": True,
        "total_strategies": len(results),
        "validated": sum(1 for r in results if r["gate_pass"]),
        "rejected": sum(1 for r in results if not r["gate_pass"]),
    }
    (output_dir / "significance_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
    import random
    random.seed(42)
    fake_trades = pd.DataFrame({
        "clv": [random.gauss(0.03, 0.15) for _ in range(400)],
        "profit": [random.gauss(0.5, 3) for _ in range(400)],
        "stake": [1.0] * 400,
    })
    result = validate_edge_statistical(fake_trades)
    print(json.dumps(result, indent=2))
