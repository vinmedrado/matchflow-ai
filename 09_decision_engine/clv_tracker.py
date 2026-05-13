"""
clv_tracker.py — Closing Line Value tracker.
CLV é a métrica definitiva para medir se você tem edge real no mercado.
CLV > 0 de forma consistente = você está batendo o mercado.
"""
from __future__ import annotations
import json, logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

logger = logging.getLogger("matchflow.decision_engine.clv_tracker")

def calculate_clv(odds_entry: float, odds_closing: float) -> float:
    """
    Closing Line Value = % de quanto suas odds estão acima das de fechamento.

    CLV positivo = você apostou com odds melhores que o mercado eficiente.
    CLV negativo = você apostou com odds piores (perdendo valor antes do jogo).

    Exemplo:
        Você apostou a 1.85, fechou em 1.72
        CLV = (1.85 / 1.72) - 1 = +7.56% (você bateu o mercado)
    """
    if odds_entry <= 0 or odds_closing <= 0:
        return 0.0
    return (odds_entry / odds_closing) - 1.0

def categorize_clv(clv: float) -> str:
    if clv >= 0.08:
        return "EXCELLENT"
    if clv >= 0.04:
        return "GOOD"
    if clv >= 0.01:
        return "MARGINAL"
    if clv >= -0.01:
        return "NEUTRAL"
    if clv >= -0.05:
        return "BAD"
    return "TERRIBLE"

def update_clv_for_settled_bets(root: Path | None = None) -> dict[str, Any]:
    """
    Busca odds de fechamento para apostas liquidadas e calcula CLV.
    Atualiza paper_signals.csv com campo clv.
    """
    root = root or Path.cwd()
    signals_path = root / "data/paper_trading/paper_signals.csv"
    clv_path = root / "data/performance/clv_history.parquet"
    odds_latest = root / "data/odds/odds_latest.parquet"

    if not signals_path.exists():
        return {"ok": False, "reason": "NO_SIGNALS"}

    signals = pd.read_csv(signals_path)
    if signals.empty:
        return {"ok": True, "updated": 0}

    # Carregar odds mais recentes como proxy de fechamento
    closing_odds_df = None
    if odds_latest.exists():
        try:
            closing_odds_df = safe_read_dataframe(odds_latest)
        except Exception:
            pass

    updated = 0
    clv_records = []

    for idx, row in signals.iterrows():
        if row.get("status") not in ("WIN", "LOSS", "SETTLED"):
            continue
        if pd.notna(row.get("clv")):
            continue  # Já calculado

        odds_entry = float(row.get("odd") or row.get("odds_value") or 0)
        if odds_entry <= 0:
            continue

        # Tentar buscar odds de fechamento
        odds_closing = None
        if closing_odds_df is not None:
            home = str(row.get("home_team") or row.get("team_name") or "")
            away = str(row.get("away_team") or row.get("opponent_name") or "")
            market = str(row.get("market") or "")
            mask = (
                (closing_odds_df["home_team"].str.lower() == home.lower()) &
                (closing_odds_df["away_team"].str.lower() == away.lower()) &
                (closing_odds_df["market"] == market) &
                (closing_odds_df["bookmaker"] == "pinnacle")
            )
            sub = closing_odds_df[mask]
            if not sub.empty:
                odds_closing = float(sub["odds_value"].mean())

        if odds_closing is None:
            continue

        clv = calculate_clv(odds_entry, odds_closing)
        signals.at[idx, "clv"] = round(clv, 4)
        signals.at[idx, "clv_category"] = categorize_clv(clv)
        signals.at[idx, "odds_closing"] = round(odds_closing, 3)
        updated += 1

        clv_records.append({
            "signal_id": row.get("signal_id"),
            "date": row.get("date"),
            "market": row.get("market"),
            "strategy": row.get("strategy"),
            "league": row.get("league"),
            "odds_entry": odds_entry,
            "odds_closing": odds_closing,
            "clv": clv,
            "clv_category": categorize_clv(clv),
            "is_win": row.get("is_win"),
            "profit": row.get("profit"),
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        })

    if updated > 0:
        signals.to_csv(signals_path, index=False)

        clv_path.parent.mkdir(parents=True, exist_ok=True)
        if clv_records:
            new_clv = pd.DataFrame(clv_records)
            if clv_path.exists():
                existing = safe_read_dataframe(clv_path)
                combined = pd.concat([existing, new_clv], ignore_index=True)
                combined = combined.drop_duplicates(subset=["signal_id"], keep="last")
                safe_write_dataframe(combined, clv_path, index=False)
            else:
                safe_write_dataframe(new_clv, clv_path, index=False)

    return {"ok": True, "updated": updated, "signals_path": str(signals_path)}

def get_clv_metrics(root: Path | None = None, days: int = 30) -> dict[str, Any]:
    """
    Calcula métricas de CLV para o dashboard e alertas.
    A métrica mais importante: CLV rolling 30 dias.
    """
    root = root or Path.cwd()
    clv_path = root / "data/performance/clv_history.parquet"

    if not clv_path.exists():
        return {"ok": False, "reason": "NO_CLV_HISTORY", "mean_clv": 0.0}

    try:
        df = safe_read_dataframe(clv_path)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "mean_clv": 0.0}

    if df.empty or "clv" not in df.columns:
        return {"ok": True, "total_tracked": 0, "mean_clv": 0.0}

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=days)
    recent = df[df["date"] >= cutoff].copy()

    clv_values = df["clv"].dropna()
    recent_clv = recent["clv"].dropna() if not recent.empty else pd.Series(dtype=float)

    mean_clv_all = float(clv_values.mean()) if len(clv_values) > 0 else 0.0
    mean_clv_recent = float(recent_clv.mean()) if len(recent_clv) > 0 else 0.0

    # Verificar deterioração de edge
    edge_deteriorating = (
        len(recent_clv) >= 10 and
        mean_clv_recent < -0.02
    )

    by_market = {}
    if "market" in df.columns:
        for market, grp in df.groupby("market"):
            mc = grp["clv"].dropna()
            by_market[market] = {
                "mean_clv": round(float(mc.mean()) if len(mc) > 0 else 0.0, 4),
                "count": int(len(mc)),
                "positive_clv_rate": round(float((mc > 0).mean()) if len(mc) > 0 else 0.0, 3),
            }

    return {
        "ok": True,
        "total_tracked": int(len(clv_values)),
        "mean_clv_all_time": round(mean_clv_all, 4),
        "mean_clv_all_time_pct": round(mean_clv_all * 100, 2),
        "mean_clv_last_30d": round(mean_clv_recent, 4),
        "mean_clv_last_30d_pct": round(mean_clv_recent * 100, 2),
        "positive_clv_rate": round(float((clv_values > 0).mean()), 3) if len(clv_values) > 0 else 0.0,
        "edge_deteriorating": edge_deteriorating,
        "is_beating_market": mean_clv_all > 0.01 and len(clv_values) >= 50,
        "by_market": by_market,
        "days_analyzed": days,
    }

def get_rolling_clv(root: Path | None = None, window_days: int = 7) -> float | None:
    """Retorna CLV médio dos últimos N dias (para adaptive_kelly_multiplier)."""
    metrics = get_clv_metrics(root, days=window_days)
    return metrics.get("mean_clv_last_30d")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
    metrics = get_clv_metrics()
    print(json.dumps(metrics, indent=2))
