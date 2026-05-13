"""
performance_attributor.py — Decomposição de performance em habilidade vs variância.
Responde a pergunta mais importante: estou ganhando por skill ou por sorte?
"""
from __future__ import annotations
import json, logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

logger = logging.getLogger("matchflow.decision_engine.performance_attributor")

def decompose_performance(trades_df: pd.DataFrame) -> dict[str, Any]:
    """
    Decompõe resultados em componentes de habilidade e variância.

    Componentes:
    - skill_component: CLV acumulado (o que você MERECIA ganhar)
    - variance_component: diferença entre resultado real e CLV esperado
    - brier_score: qualidade das probabilidades ML
    - timing_edge: contribuição do timing de entrada

    Args:
        trades_df: DataFrame com colunas: profit, stake, clv, ml_probability,
                   is_win, odds, expected_resolution_date

    Returns:
        dict com decomposição completa
    """
    if trades_df.empty:
        return {"ok": False, "reason": "NO_TRADES", "total_roi": 0.0}

    df = trades_df.copy()
    n = len(df)

    # Métricas básicas
    if "profit" in df.columns and "stake" in df.columns:
        df["profit"] = pd.to_numeric(df["profit"], errors="coerce").fillna(0)
        df["stake"] = pd.to_numeric(df["stake"], errors="coerce").fillna(1)
        total_profit = float(df["profit"].sum())
        total_stake = float(df["stake"].sum())
        total_roi = total_profit / total_stake if total_stake > 0 else 0.0
    else:
        total_profit = 0.0
        total_roi = 0.0

    # Componente de habilidade (CLV)
    clv_available = "clv" in df.columns and df["clv"].notna().sum() > n * 0.3
    if clv_available:
        clv_values = df["clv"].dropna()
        skill_roi = float(clv_values.mean())
        variance_roi = total_roi - skill_roi
        is_skill_based = skill_roi > 0.01
    else:
        skill_roi = None
        variance_roi = None
        is_skill_based = None

    # Calibração das probabilidades (Brier Score)
    brier_result = {}
    if "ml_probability" in df.columns and "is_win" in df.columns:
        probs = df["ml_probability"].dropna()
        outcomes = df.loc[probs.index, "is_win"].fillna(0).astype(float)
        if len(probs) > 10:
            brier = float(np.mean((probs.values - outcomes.values) ** 2))
            brier_result = {
                "brier_score": round(brier, 4),
                "is_well_calibrated": brier < 0.25,
                "calibration_grade": _brier_grade(brier),
            }

    # Win rate e expectativas
    if "is_win" in df.columns:
        wins = int(df["is_win"].fillna(0).astype(bool).sum())
        win_rate = wins / n if n > 0 else 0.0
    else:
        wins = 0
        win_rate = 0.0

    # Expectativa de longo prazo
    expected_roi_conservative = skill_roi * 0.7 if skill_roi else None

    # ROI por estratégia
    by_strategy = {}
    if "strategy" in df.columns and "market" in df.columns:
        for (strat, mkt), grp in df.groupby(["strategy", "market"]):
            key = f"{strat}/{mkt}"
            g_profit = grp["profit"].sum() if "profit" in grp.columns else 0
            g_stake = grp["stake"].sum() if "stake" in grp.columns else len(grp)
            by_strategy[key] = {
                "trades": len(grp),
                "roi": round(float(g_profit / g_stake) if g_stake > 0 else 0, 4),
                "win_rate": round(float(grp["is_win"].fillna(0).mean()) if "is_win" in grp.columns else 0, 3),
            }

    # Verificar deterioração de edge
    edge_deteriorating = False
    recent_skill_roi = None
    if clv_available and "date" in df.columns:
        df["_date"] = pd.to_datetime(df["date"], errors="coerce")
        recent = df[df["_date"] >= df["_date"].max() - pd.Timedelta(days=30)]
        if len(recent) >= 10 and "clv" in recent.columns:
            recent_skill_roi = float(recent["clv"].dropna().mean())
            edge_deteriorating = recent_skill_roi < -0.02

    return {
        "ok": True,
        "total_trades": n,
        "wins": wins,
        "losses": n - wins,
        "win_rate": round(win_rate, 4),
        "total_profit": round(total_profit, 4),
        "total_roi": round(total_roi, 4),
        "total_roi_pct": round(total_roi * 100, 2),

        # Decomposição skill vs variância
        "skill_component": {
            "available": clv_available,
            "skill_roi": round(skill_roi, 4) if skill_roi is not None else None,
            "skill_roi_pct": round(skill_roi * 100, 2) if skill_roi is not None else None,
            "variance_roi": round(variance_roi, 4) if variance_roi is not None else None,
            "is_skill_based": is_skill_based,
            "description": "Habilidade medida por CLV acumulado" if clv_available else "CLV não disponível — coletando odds de fechamento",
        },

        # Calibração
        "calibration": brier_result,

        # Edge deterioration
        "edge_health": {
            "edge_deteriorating": edge_deteriorating,
            "recent_clv_30d": round(recent_skill_roi, 4) if recent_skill_roi is not None else None,
            "recommendation": _edge_recommendation(edge_deteriorating, skill_roi, n),
        },

        # Projeção conservadora
        "expected_long_term_roi_pct": round(expected_roi_conservative * 100, 2) if expected_roi_conservative else None,

        # Por estratégia
        "by_strategy": by_strategy,

        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

def _brier_grade(brier: float) -> str:
    if brier < 0.10: return "EXCELLENT"
    if brier < 0.20: return "GOOD"
    if brier < 0.25: return "ACCEPTABLE"
    return "POOR"

def _edge_recommendation(deteriorating: bool, skill_roi: float | None, n: int) -> str:
    if n < 50:
        return "COLETAR_MAIS_DADOS: amostra insuficiente para conclusões"
    if deteriorating:
        return "REDUZIR_STAKES: edge deteriorando, investigar modelo"
    if skill_roi is None:
        return "AGUARDAR_CLV: coletar odds de fechamento para análise"
    if skill_roi > 0.04:
        return "CONTINUAR: edge forte e consistente"
    if skill_roi > 0.01:
        return "MONITORAR: edge positivo mas modesto"
    if skill_roi > -0.01:
        return "AVALIAR: edge neutro, revisar estratégias"
    return "PAUSAR: edge negativo, revisar sistema"

def generate_performance_report(root: Path | None = None) -> dict[str, Any]:
    """Gera relatório completo de performance e salva."""
    root = root or Path.cwd()
    signals_path = root / "data/paper_trading/paper_signals.csv"
    output_dir = root / "data/performance"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not signals_path.exists():
        return {"ok": False, "reason": "NO_SIGNALS"}

    df = pd.read_csv(signals_path)
    result = decompose_performance(df)

    out_path = output_dir / "performance_attribution.json"
    out_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    logger.info("Performance attribution salvo: %s trades, skill_roi=%s%%",
                result.get("total_trades"), result.get("skill_component", {}).get("skill_roi_pct"))
    return result

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
    result = generate_performance_report()
    print(json.dumps(result, indent=2, default=str))
