"""
result_settler.py — Liquidação automática de apostas pendentes.
Busca resultados reais e marca sinais como win/loss no paper trading.
"""
from __future__ import annotations
import json, logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

logger = logging.getLogger("matchflow.data_ops.result_settler")

def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]

def _evaluate_market(row: pd.Series, result: dict) -> tuple[bool | None, str]:
    """
    Avalia se uma aposta ganhou ou perdeu baseado no resultado real.
    Returns: (is_win, reason)
    """
    market = str(row.get("market", "")).lower()
    selection = str(row.get("selection", "")).lower()
    line = row.get("point") or row.get("line")

    gh = result.get("goals_home_ft")
    ga = result.get("goals_away_ft")

    if gh is None or ga is None:
        return None, "MISSING_SCORE"

    try:
        gh, ga = int(gh), int(ga)
        total = gh + ga
    except (TypeError, ValueError):
        return None, "INVALID_SCORE"

    if market in ("goals", "totals"):
        if line is None:
            return None, "MISSING_LINE"
        try:
            line_f = float(line)
        except (TypeError, ValueError):
            return None, "INVALID_LINE"
        # "Over X" = selection contém "over" ou é o home/away team
        if "over" in selection or selection == result.get("home_team", "").lower():
            return total > line_f, f"total={total} line={line_f}"
        else:
            return total < line_f, f"total={total} line={line_f}"

    if market == "btts":
        btts_result = gh > 0 and ga > 0
        if "yes" in selection:
            return btts_result, f"home={gh} away={ga}"
        return not btts_result, f"home={gh} away={ga}"

    if market in ("h2h", "1x2", "match_winner"):
        if "home" in selection or result.get("home_team", "").lower() in selection:
            return gh > ga, f"score={gh}-{ga}"
        if "away" in selection or result.get("away_team", "").lower() in selection:
            return ga > gh, f"score={gh}-{ga}"
        if "draw" in selection:
            return gh == ga, f"score={gh}-{ga}"

    return None, f"UNKNOWN_MARKET:{market}"

def _fetch_result_from_local(match_id: Any, historical_dir: Path) -> dict | None:
    """Tenta encontrar resultado nos dados históricos locais."""
    for parquet in historical_dir.glob("*.parquet"):
        try:
            df = safe_read_dataframe(parquet, columns=["match_id", "goals_home_ft", "goals_away_ft",
                                                    "home_team", "away_team", "match_status"])
            mask = df["match_id"].astype(str) == str(match_id)
            sub = df[mask & (df["match_status"] == "FINISHED")]
            if not sub.empty:
                return sub.iloc[0].to_dict()
        except Exception:
            continue
    return None

def _fetch_result_from_api(match_id: Any) -> dict | None:
    """Tenta buscar resultado via football-data.org API."""
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from football_data_connector import get_match_result
        return get_match_result(int(match_id))
    except Exception as exc:
        logger.debug("API fetch falhou para match %s: %s", match_id, exc)
        return None

def settle_pending_bets(root: Path | None = None) -> dict[str, Any]:
    """
    Liquida todas as apostas com status 'pending' cujo prazo já passou.

    Returns:
        dict com estatísticas da liquidação
    """
    root = root or _project_root()
    signals_path = root / "data/paper_trading/paper_signals.csv"
    historical_dir = root / "data/raw/historical"
    summary_path = root / "data/paper_trading/paper_summary.json"

    if not signals_path.exists():
        logger.info("Sem sinais para liquidar em %s", signals_path)
        return {"ok": True, "settled": 0, "pending": 0, "reason": "NO_SIGNALS_FILE"}

    try:
        df = pd.read_csv(signals_path)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    if df.empty or "status" not in df.columns:
        return {"ok": True, "settled": 0, "pending": 0}

    now = datetime.now(timezone.utc)
    pending_mask = df["status"].str.upper() == "PENDING"
    pending = df[pending_mask].copy()

    # Filtra apenas apostas cuja data de resolução já passou
    if "expected_resolution_date" in pending.columns:
        pending["_res_date"] = pd.to_datetime(pending["expected_resolution_date"], errors="coerce")
        pending = pending[pending["_res_date"].notna() & (pending["_res_date"] <= pd.Timestamp(now))]

    if pending.empty:
        return {"ok": True, "settled": 0, "pending": int(pending_mask.sum()),
                "message": "Nenhum sinal vencido para liquidar"}

    settled_count = 0
    win_count = 0
    loss_count = 0
    unsettled = []

    for idx, row in pending.iterrows():
        match_id = row.get("match_id") or row.get("match_key") or row.get("signal_id")

        # Tentar resultado local primeiro (sem consumir API)
        result = _fetch_result_from_local(match_id, historical_dir)

        # Fallback para API
        if result is None and match_id:
            result = _fetch_result_from_api(match_id)

        if result is None:
            unsettled.append(idx)
            continue

        is_win, reason = _evaluate_market(row, result)
        if is_win is None:
            unsettled.append(idx)
            logger.debug("Não foi possível avaliar sinal %s: %s", row.get("signal_id"), reason)
            continue

        # Atualizar registro
        df.at[idx, "status"] = "WIN" if is_win else "LOSS"
        df.at[idx, "is_win"] = is_win
        df.at[idx, "actual_score"] = f"{result.get('goals_home_ft')}-{result.get('goals_away_ft')}"
        df.at[idx, "settled_at"] = now.isoformat()
        df.at[idx, "settlement_reason"] = reason

        # Calcular P&L
        odd = float(row.get("odd", row.get("odds_value", 1.0)) or 1.0)
        stake = float(row.get("stake", 1.0) or 1.0)
        profit = stake * (odd - 1.0) if is_win else -stake
        df.at[idx, "profit"] = round(profit, 4)

        settled_count += 1
        if is_win:
            win_count += 1
        else:
            loss_count += 1

    # Salvar signals atualizados
    df.to_csv(signals_path, index=False)

    # Recalcular métricas do paper trading
    settled_df = df[df["status"].isin(["WIN", "LOSS"])].copy()
    if "profit" in settled_df.columns:
        settled_df["profit"] = pd.to_numeric(settled_df["profit"], errors="coerce").fillna(0)
        total_profit = float(settled_df["profit"].sum())
        total_trades = len(settled_df)
        total_wins = int((settled_df["status"] == "WIN").sum())
        win_rate = round(total_wins / total_trades, 4) if total_trades > 0 else 0.0

        initial_bankroll = 1000.0
        try:
            import os
            initial_bankroll = float(os.getenv("INITIAL_BANKROLL", "1000.0"))
        except Exception:
            pass

        roi = round(total_profit / (total_trades * 1.0), 4) if total_trades > 0 else 0.0

        new_summary = {
            "ok": True,
            "mode": "PAPER_TRADING",
            "updated_at": now.isoformat(),
            "total_trades": total_trades,
            "total_wins": total_wins,
            "total_losses": total_trades - total_wins,
            "win_rate": win_rate,
            "total_profit": round(total_profit, 4),
            "roi": roi,
            "current_bankroll": round(initial_bankroll + total_profit, 2),
            "pending_signals": int((df["status"] == "PENDING").sum()),
            "unsettled_count": len(unsettled),
        }
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(new_summary, indent=2, ensure_ascii=False), encoding="utf-8")

    result_summary = {
        "ok": True,
        "settled_now": settled_count,
        "wins_now": win_count,
        "losses_now": loss_count,
        "unsettled": len(unsettled),
        "total_pending_before": int(pending_mask.sum()),
        "settled_at": now.isoformat(),
    }
    logger.info("Liquidação: settled=%s wins=%s losses=%s unsettled=%s",
                settled_count, win_count, loss_count, len(unsettled))
    return result_summary

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
    r = settle_pending_bets()
    print(json.dumps(r, indent=2))
