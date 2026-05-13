"""
odds_monitor.py — Monitoramento de movimento de odds (sharp money detector).
Detecta steam moves, sharp money e movimentos de mercado significativos.
"""
from __future__ import annotations
import json, logging
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

logger = logging.getLogger("matchflow.data_ops.odds_monitor")

SHARP_MOVEMENT_THRESHOLD = 0.08   # 8% = sharp money
PUBLIC_MOVEMENT_THRESHOLD = 0.03  # <3% perto do jogo = public money
STEAM_BOOKMAKERS_MIN = 3          # mínimo de casas movendo na mesma direção = steam

def _load_snapshots(odds_dir: Path) -> list[pd.DataFrame]:
    snaps = sorted(odds_dir.glob("odds_snapshot_*.parquet"))
    frames = []
    for snap in snaps[-12:]:  # últimos 12 snapshots (~12h)
        try:
            frames.append(safe_read_dataframe(snap))
        except Exception:
            pass
    return frames

def _pct_change(opening: float, current: float) -> float:
    if opening <= 0:
        return 0.0
    return (opening - current) / opening  # positivo = odd caiu (mais apostas)

def classify_movement(pct_change: float, hours_to_kickoff: float) -> str:
    """
    Classifica movimento de odds:
    - SHARP: grande movimento com muito tempo para o jogo (informação)
    - STEAM: casas movendo juntas (informação profissional)
    - PUBLIC: pequeno movimento perto do jogo (volume)
    - NEUTRAL: sem movimento significativo
    """
    abs_chg = abs(pct_change)
    if abs_chg > SHARP_MOVEMENT_THRESHOLD and hours_to_kickoff > 24:
        return "SHARP_MOVEMENT"
    if abs_chg > SHARP_MOVEMENT_THRESHOLD and hours_to_kickoff <= 24:
        return "LATE_SHARP"
    if abs_chg < PUBLIC_MOVEMENT_THRESHOLD and hours_to_kickoff < 2:
        return "PUBLIC_MONEY"
    if abs_chg >= 0.04:
        return "SIGNIFICANT_MOVEMENT"
    return "NEUTRAL"

def detect_steam_move(match_id: str, market: str, selection: str,
                      snapshots: list[pd.DataFrame]) -> dict:
    """
    Steam move = múltiplas casas movendo na MESMA direção simultaneamente.
    É um dos sinais mais fortes de sharp money no mercado.
    """
    if len(snapshots) < 2:
        return {"steam_detected": False}

    first = snapshots[0]
    last = snapshots[-1]

    def get_odds(df: pd.DataFrame) -> dict:
        mask = (
            (df.get("match_id") == match_id) &
            (df.get("market") == market) &
            (df.get("selection").str.lower() == selection.lower())
        )
        return df[mask].groupby("bookmaker")["odds_value"].mean().to_dict()

    opening_odds = get_odds(first)
    current_odds = get_odds(last)

    moves = {}
    for bookie in set(opening_odds) & set(current_odds):
        o, c = opening_odds[bookie], current_odds[bookie]
        if o > 0 and c > 0:
            moves[bookie] = _pct_change(o, c)

    if len(moves) < STEAM_BOOKMAKERS_MIN:
        return {"steam_detected": False, "bookmakers_tracked": len(moves)}

    # Steam: maioria das casas na mesma direção
    positives = sum(1 for v in moves.values() if v > 0.02)
    negatives = sum(1 for v in moves.values() if v < -0.02)
    total = len(moves)
    same_direction = max(positives, negatives)
    steam = same_direction >= STEAM_BOOKMAKERS_MIN and same_direction / total >= 0.7

    direction = "DOWN" if positives > negatives else "UP"

    return {
        "steam_detected": steam,
        "direction": direction if steam else None,
        "bookmakers_moving": same_direction,
        "total_bookmakers": total,
        "avg_movement_pct": round(sum(moves.values()) / len(moves) * 100, 2) if moves else 0,
        "moves": moves,
    }

def build_odds_movement_report(root: Path | None = None) -> dict:
    """
    Gera relatório de movimento de odds para todos os jogos das próximas 48h.
    """
    root = root or Path.cwd()
    odds_dir = root / "data/odds"
    output_dir = root / "data/odds_monitor"
    output_dir.mkdir(parents=True, exist_ok=True)

    snapshots = _load_snapshots(odds_dir)
    if not snapshots:
        logger.warning("Nenhum snapshot de odds encontrado em %s", odds_dir)
        return {"ok": False, "reason": "NO_SNAPSHOTS"}

    latest = snapshots[-1]
    opening = snapshots[0]

    now = datetime.now(timezone.utc)
    report_rows = []

    for match_id in latest["match_id"].unique():
        match_data = latest[latest["match_id"] == match_id].iloc[0]
        kickoff = pd.to_datetime(match_data.get("date"), errors="coerce")
        if pd.isna(kickoff):
            continue

        hours_to_kickoff = (kickoff.replace(tzinfo=timezone.utc) - now).total_seconds() / 3600
        if hours_to_kickoff < 0 or hours_to_kickoff > 72:
            continue

        for market in latest[latest["match_id"] == match_id]["market"].unique():
            for selection in latest[
                (latest["match_id"] == match_id) & (latest["market"] == market)
            ]["selection"].unique():

                # Odds opening vs current (Pinnacle como referência)
                def _pinnacle_odds(df: pd.DataFrame) -> float | None:
                    mask = (
                        (df["match_id"] == match_id) &
                        (df["market"] == market) &
                        (df["selection"] == selection) &
                        (df["bookmaker"] == "pinnacle")
                    )
                    sub = df[mask]
                    if sub.empty:
                        return None
                    return float(sub["odds_value"].mean())

                o_pinnacle = _pinnacle_odds(opening)
                c_pinnacle = _pinnacle_odds(latest)

                if o_pinnacle is None or c_pinnacle is None:
                    continue

                pct = _pct_change(o_pinnacle, c_pinnacle)
                movement_type = classify_movement(pct, hours_to_kickoff)
                steam = detect_steam_move(match_id, market, selection, snapshots)

                report_rows.append({
                    "match_id": match_id,
                    "home_team": match_data.get("home_team"),
                    "away_team": match_data.get("away_team"),
                    "date": kickoff,
                    "hours_to_kickoff": round(hours_to_kickoff, 1),
                    "market": market,
                    "selection": selection,
                    "opening_odds_pinnacle": round(o_pinnacle, 3),
                    "current_odds_pinnacle": round(c_pinnacle, 3),
                    "movement_pct": round(pct * 100, 2),
                    "movement_type": movement_type,
                    "steam_detected": steam.get("steam_detected", False),
                    "steam_direction": steam.get("direction"),
                    "confidence_modifier": _get_confidence_modifier(movement_type, steam),
                    "analyzed_at": now.isoformat(),
                })

    report_df = pd.DataFrame(report_rows) if report_rows else pd.DataFrame()
    if not report_df.empty:
        safe_write_dataframe(report_df, output_dir / "odds_movement_report.parquet", index=False)
        report_df.to_csv(output_dir / "odds_movement_report.csv", index=False)

    summary = {
        "ok": True,
        "generated_at": now.isoformat(),
        "matches_analyzed": len(set(r["match_id"] for r in report_rows)),
        "sharp_movements": sum(1 for r in report_rows if r["movement_type"] in ("SHARP_MOVEMENT", "LATE_SHARP")),
        "steam_moves": sum(1 for r in report_rows if r.get("steam_detected")),
        "total_lines": len(report_rows),
    }
    (output_dir / "odds_movement_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("Relatório de movimento: %s linhas, %s sharp, %s steam",
                len(report_rows), summary["sharp_movements"], summary["steam_moves"])
    return summary

def _get_confidence_modifier(movement_type: str, steam: dict) -> float:
    """
    Modificador de confiança baseado no tipo de movimento.
    +0.15 = aumenta confiança quando sharp/steam confirma sinal do ML.
    -0.15 = reduz confiança quando sharp/steam vai contra o ML.
    """
    if steam.get("steam_detected"):
        return 0.15
    if movement_type == "SHARP_MOVEMENT":
        return 0.10
    if movement_type == "LATE_SHARP":
        return 0.08
    if movement_type == "PUBLIC_MONEY":
        return -0.05
    return 0.0

def get_movement_for_match(home_team: str, away_team: str, market: str,
                            root: Path | None = None) -> dict | None:
    """Consulta movimento de odds para um jogo específico."""
    root = root or Path.cwd()
    path = root / "data/odds_monitor/odds_movement_report.parquet"
    if not path.exists():
        return None
    try:
        df = safe_read_dataframe(path)
        mask = (
            (df["home_team"].str.lower() == home_team.lower()) &
            (df["away_team"].str.lower() == away_team.lower()) &
            (df["market"] == market)
        )
        sub = df[mask]
        if sub.empty:
            return None
        row = sub.iloc[0]
        return row.to_dict()
    except Exception:
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
    result = build_odds_movement_report()
    print(json.dumps(result, indent=2))
