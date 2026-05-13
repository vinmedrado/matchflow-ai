from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd
from backend.core.storage import safe_write_dataframe
from .config import project_root

MIN_COLUMNS = [
    "provider","source","is_demo_data","flashscore_match_id","match_id","league","season","match_date","kickoff_time",
    "home_team","away_team","status","goals_home_ft","goals_away_ft","goals_home_ht","goals_away_ht",
    "corners_home","corners_away","shots_home","shots_away","shots_on_target_home","shots_on_target_away",
    "xg_home","xg_away","goal_minutes_home","goal_minutes_away","odds_home","odds_draw","odds_away","odds_over_05","odds_under_05","odds_over_15","odds_under_15","odds_over_25","odds_under_25","odds_btts_yes","odds_btts_no",
    "provider_warnings","data_quality_score","canonical_home_team_id","canonical_away_team_id","canonical_league_id",
    "match_identity_key","mapping_confidence","identity_confidence","duplicate_status","conflict_flags","final_data_quality_score"
]

def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in MIN_COLUMNS:
        if col not in out.columns:
            out[col] = None
    if "match_id" in out.columns and "flashscore_match_id" in out.columns:
        out["match_id"] = out["match_id"].fillna(out["flashscore_match_id"])
    return out

def write_outputs(df: pd.DataFrame, report: dict[str, Any] | None = None) -> dict[str, Any]:
    root = project_root()
    raw = root / "data" / "raw"
    reports = root / "data" / "reports"
    raw.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    df = _ensure_columns(df)
    parquet = raw / "flashscore_matches.parquet"
    csv = raw / "flashscore_matches.csv"
    odds = raw / "flashscore_odds.parquet"
    stats = raw / "flashscore_stats.parquet"
    matches_storage = safe_write_dataframe(df, parquet, index=False, also_write_csv=True)
    odds_cols = [c for c in df.columns if c.startswith("odds_") or c in {"match_id", "flashscore_match_id", "match_identity_key", "provider", "source", "is_demo_data"}]
    odds_storage = safe_write_dataframe(df[odds_cols], odds, index=False)
    stat_cols = [c for c in df.columns if c in {"match_id", "flashscore_match_id", "match_identity_key", "corners_home", "corners_away", "shots_home", "shots_away", "shots_on_target_home", "shots_on_target_away", "xg_home", "xg_away", "goal_minutes_home", "goal_minutes_away", "provider", "source", "is_demo_data"}]
    stats_storage = safe_write_dataframe(df[stat_cols], stats, index=False)
    payload = {
        "ok": True,
        "provider": "flashscore",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_records": int(len(df)),
        "demo_records": int(df["is_demo_data"].astype(str).str.lower().isin({"true","1","yes"}).sum()) if "is_demo_data" in df.columns else 0,
        "outputs": {"matches_parquet": str(parquet.relative_to(root)), "matches_csv": str(csv.relative_to(root)), "odds_parquet": str(odds.relative_to(root)), "stats_parquet": str(stats.relative_to(root))},
        "report": report or {},
        "storage": {"matches": matches_storage, "odds": odds_storage, "stats": stats_storage},
    }
    report_path = reports / "flashscore_sync_report.json"
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload
