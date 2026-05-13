from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/product", tags=["product"])


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}


def _backtest_health() -> dict[str, Any]:
    summary = _read_csv(_root() / "data/backtest/results/summary_results.csv")
    detailed_path = _root() / "data/backtest/results/detailed_results.parquet"
    detailed = safe_read_dataframe(detailed_path) if detailed_path.exists() else pd.DataFrame()
    total_trades = int(summary["total_trades"].sum()) if not summary.empty and "total_trades" in summary.columns else 0
    league_count = int(detailed["league"].nunique()) if not detailed.empty and "league" in detailed.columns else 0
    team_count = int(detailed["team_key"].nunique()) if not detailed.empty and "team_key" in detailed.columns else 0
    market_count = int(detailed["market"].nunique()) if not detailed.empty and "market" in detailed.columns else 0
    sample_level = "fraca" if total_trades < 100 else "média" if total_trades < 1000 else "forte"
    recommendations = []
    if total_trades < 100:
        recommendations.append("Aumentar amostra antes de confiar em ROI por estratégia.")
    if league_count <= 1:
        recommendations.append("Separar backtest por liga para reduzir viés de campeonato.")
    if team_count > 0:
        recommendations.append("Criar thresholds por time usando forma recente, liga e mercado.")
    if market_count > 1:
        recommendations.append("Comparar mercados separadamente: gols, escanteios, BTTS e chutes não devem compartilhar a mesma regra.")
    return {
        "total_trades": total_trades,
        "league_count": league_count,
        "team_count": team_count,
        "market_count": market_count,
        "sample_level": sample_level,
        "is_ready_for_ml": total_trades >= 100 and league_count >= 2,
        "recommended_next_step": "Backtest por time + liga antes de alimentar produção ML." if total_trades < 1000 else "ML pode usar backtest como camada de validação.",
        "recommendations": recommendations,
    }


@router.get("/audit")
def audit() -> dict[str, Any]:
    root = _root()
    backtest = _backtest_health()
    engine_state = _read_json(root / "data/automation/engine_run_state.json")
    readiness = 45
    if (root / "data/processed/base_data_engine.parquet").exists(): readiness += 10
    if (root / "data/features/team_dataset_advanced.parquet").exists(): readiness += 10
    if backtest["total_trades"] > 0: readiness += 10
    if (root / "data/ml/models/registry.json").exists(): readiness += 10
    if (root / "data/decision_engine/decision_candidates.csv").exists(): readiness += 10
    readiness = min(readiness, 95)
    return {"ok": True, "data": {
        "readiness_score": readiness,
        "readiness_label": "produto técnico forte, ainda precisa polish comercial" if readiness < 85 else "pronto para demo premium",
        "backtest": backtest,
        "data_engine": {"last_run": engine_state, "internal_provider": "backend/services/data_engine/providers/flashscore", "uses_external_repo": False},
        "multi_user": {"status": "local-dev", "next_step": "persistir usuários, perfis, organizações e permissões em banco."},
        "language": {"supported": ["pt", "en", "es"], "mode": "frontend dictionary"},
    }}


@router.get("/backtest-health")
def backtest_health() -> dict[str, Any]:
    return {"ok": True, "data": _backtest_health()}


@router.get("/bankroll-policy")
def bankroll_policy(bankroll: float = Query(1000, gt=0), risk_profile: str = Query("balanced")) -> dict[str, Any]:
    profile = risk_profile.lower()
    if profile not in {"conservative", "balanced", "aggressive"}:
        profile = "balanced"
    factors = {"conservative": 0.15, "balanced": 0.25, "aggressive": 0.35}
    max_unit = {"conservative": 0.01, "balanced": 0.015, "aggressive": 0.025}
    method = "fractional_kelly" if bankroll >= 300 else "flat_stake_controlled"
    return {"ok": True, "data": {
        "bankroll": bankroll,
        "risk_profile": profile,
        "recommended_method": method,
        "kelly_fraction": factors[profile],
        "max_stake_pct": max_unit[profile],
        "max_stake_value": round(bankroll * max_unit[profile], 2),
        "rules": [
            "Usar Kelly fracionado apenas quando houver probabilidade calibrada e amostra suficiente.",
            "Usar stake fixa controlada quando a banca for pequena ou o edge ainda estiver em validação.",
            "Bloquear aumento de stake em drawdown ou baixa confiança do modelo.",
        ],
    }}
