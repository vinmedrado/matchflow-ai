"""
decision_score.py — Score de decisão enriquecido com True EV, CLV e Kelly.
Suporta APP_MODE=PAPER_TRADING_SIMULATION_ONLY | LIVE_RESEARCH via variável de ambiente.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Any, Mapping

_CURRENT_DIR = Path(__file__).resolve().parent
if str(_CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(_CURRENT_DIR))

try:
    from confidence_engine import confidence_band
    from risk_adjuster import adjust_score, parse_flags
except ImportError:
    from .confidence_engine import confidence_band
    from .risk_adjuster import adjust_score, parse_flags

# APP_MODE controlado por variável de ambiente
_APP_MODE = os.getenv("APP_MODE", "PAPER_TRADING_SIMULATION_ONLY").upper()
MODE = "LIVE_RESEARCH" if _APP_MODE == "LIVE_RESEARCH" else "PAPER_TRADING_SIMULATION_ONLY"
IS_LIVE = MODE == "LIVE_RESEARCH"


def _f(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except Exception:
        return default


def _score_probability(ml: float, ensemble: float) -> float:
    probs = [p for p in [ml, ensemble] if 0 < p <= 1]
    avg = sum(probs) / len(probs) if probs else 0.0
    return max(0.0, min(20.0, avg * 20.0))  # max 20pts


def _score_true_ev(true_ev: float, edge_pct: float) -> float:
    """Score baseado em True EV (após remoção de vig) — principal diferencial."""
    if true_ev >= 0.08:
        return 20.0   # EV excepcional
    if true_ev >= 0.05:
        return 16.0   # EV alto
    if true_ev >= 0.03:
        return 12.0   # Bom value
    if true_ev >= 0.01:
        return 7.0    # Value marginal
    if true_ev > 0:
        return 3.0    # EV positivo mínimo
    return 0.0        # Sem edge real


def _score_market_movement(movement_type: str, steam: bool) -> float:
    """Score baseado em movimento de odds (sharp money)."""
    if steam:
        return 10.0   # Steam move = dinheiro profissional confirmado
    if movement_type == "SHARP_MOVEMENT":
        return 7.0
    if movement_type == "LATE_SHARP":
        return 5.0
    if movement_type == "SIGNIFICANT_MOVEMENT":
        return 3.0
    if movement_type == "PUBLIC_MONEY":
        return -3.0   # Público apostando = sinal de over (odds caindo por volume)
    return 0.0


def _score_sample(sample_size: float) -> float:
    """Score mínimo de 300 trades para edge válido."""
    if sample_size >= 500:
        return 10.0
    if sample_size >= 300:
        return 8.0    # Threshold mínimo de significância
    if sample_size >= 100:
        return 4.0
    if sample_size > 0:
        return 1.0
    return 0.0


def _score_quality(value: Any, positive: set, neutral: set) -> float:
    text = str(value or "").upper()
    if any(l in text for l in positive):
        return 8.0
    if any(l in text for l in neutral):
        return 4.0
    return 0.0


def calculate_decision_score(row: Mapping[str, Any]) -> dict[str, Any]:
    rule_status = str(row.get("rule_status") or "").upper()
    ml_prob = _f(row.get("ml_probability"))
    ensemble_prob = _f(row.get("ensemble_probability"))
    consistency = _f(row.get("consistency_score"))
    sample_size = _f(row.get("sample_size"))
    risk_flags = parse_flags(row.get("risk_flags"))
    true_ev = _f(row.get("true_ev"))
    edge_pct = _f(row.get("edge_pct"))
    movement_type = str(row.get("movement_type") or "NEUTRAL")
    steam = bool(row.get("steam_detected", False))
    odds = _f(row.get("odds"))

    score = 0.0

    # 1. Regras (25pts max)
    score += 25.0 if rule_status == "KEEP" else 10.0 if rule_status == "WATCH" else 0.0

    # 2. Probabilidade ML (20pts max)
    score += _score_probability(ml_prob, ensemble_prob)

    # 3. True EV com vig removida (20pts max) — PRINCIPAL DIFERENCIAL
    score += _score_true_ev(true_ev, edge_pct)

    # 4. Consistência histórica (15pts max)
    score += max(0.0, min(15.0, consistency * 0.15))

    # 5. Amostra (10pts max)
    score += _score_sample(sample_size)

    # 6. Movimento de odds / sharp money (10pts max)
    score += _score_market_movement(movement_type, steam)

    # 7. Qualidade das odds e liga (8pts max + 4pts)
    score += _score_quality(row.get("odds_range_quality"), {"FAVORABLE", "POSITIVE"}, {"NEUTRAL"})
    score += _score_quality(row.get("league_market_quality"), {"STRONG", "HIGH_EDGE", "ACCEPTABLE"}, {"NEUTRAL"}) * 0.5

    # Penalty: odds abaixo de 1.40 (retorno insuficiente)
    if odds > 0 and odds < 1.40:
        score -= 5.0

    # Paper trading status
    if str(row.get("paper_trading_status") or "").upper() in {"HEALTHY", "ACTIVE", "OK"}:
        score += 3.0

    adjusted_score, parsed_flags = adjust_score(score, risk_flags)
    adjusted_score = round(max(0.0, min(100.0, adjusted_score)), 2)
    band = confidence_band(adjusted_score)

    # action_required: apenas HIGH_CONFIDENCE + kelly > 0 + true_ev > 0
    kelly_pct = _f(row.get("kelly_stake_pct"))
    action_required = (
        IS_LIVE and
        "HIGH_CONFIDENCE" in band and
        kelly_pct > 0 and
        true_ev > 0.02
    )

    recommendation = band if band in {"WATCH_ONLY", "REJECTED"} else "SIMULATION_CANDIDATE"

    return {
        "decision_score": adjusted_score,
        "confidence_band": band,
        "recommendation_type": recommendation,
        "risk_flags": parsed_flags,
        "action_required": action_required,
        "mode": MODE,
    }
