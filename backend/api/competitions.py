from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/competitions", tags=["competitions"])


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    if path.suffix == ".parquet":
        return safe_read_dataframe(path)
    if path.suffix == ".csv":
        return pd.read_csv(path)
    return pd.DataFrame()


def _base_matches() -> pd.DataFrame:
    candidates = [
        _root() / "data/processed/base_data_engine.parquet",
        _root() / "data/ops/future_games_snapshot.parquet",
    ]
    for path in candidates:
        df = _read(path)
        if not df.empty and "league" in df.columns:
            return df
    return pd.DataFrame()


def _team_dataset() -> pd.DataFrame:
    return _read(_root() / "data/features/team_dataset.parquet")


def _clean_number(value: Any, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return default
        return int(value)
    except Exception:
        return default


@router.get("/overview")
def overview() -> dict[str, Any]:
    base = _base_matches()
    team = _team_dataset()
    source = team if not team.empty and "league" in team.columns else base
    if source.empty:
        return {"ok": True, "data": {"leagues": [], "total_leagues": 0, "total_matches": 0}}

    leagues = []
    for league, group in source.groupby("league", dropna=True):
        if not str(league).strip():
            continue
        teams = set()
        for col in ["team_name", "home_team", "away_team"]:
            if col in group.columns:
                teams.update(group[col].dropna().astype(str).tolist())
        dates = pd.to_datetime(group["date"], errors="coerce") if "date" in group.columns else pd.Series([], dtype="datetime64[ns]")
        leagues.append({
            "league": str(league),
            "matches": int(group["match_key"].nunique()) if "match_key" in group.columns else int(len(group)),
            "teams": len(teams),
            "date_min": str(dates.min().date()) if len(dates.dropna()) else None,
            "date_max": str(dates.max().date()) if len(dates.dropna()) else None,
        })
    leagues.sort(key=lambda item: (item["league"] or "").lower())
    return {"ok": True, "data": {"leagues": leagues, "total_leagues": len(leagues), "total_matches": int(sum(x["matches"] for x in leagues))}}


@router.get("/detail")
def detail(league: str = Query(..., min_length=1)) -> dict[str, Any]:
    base = _base_matches()
    team = _team_dataset()
    standings: list[dict[str, Any]] = []

    if not team.empty and "league" in team.columns:
        tg = team[team["league"].astype(str) == league].copy()
        if not tg.empty:
            for team_key, group in tg.groupby("team_key" if "team_key" in tg.columns else "team_name"):
                name = str(group.get("team_name", pd.Series([team_key])).dropna().iloc[0]) if len(group) else str(team_key)
                gf = group.get("goals_for_ft", pd.Series(dtype=float)).fillna(0).sum()
                ga = group.get("goals_against_ft", pd.Series(dtype=float)).fillna(0).sum()
                standings.append({
                    "team_key": str(team_key),
                    "team_name": name,
                    "matches": int(len(group)),
                    "points": _clean_number(group.get("points", pd.Series(dtype=float)).fillna(0).sum()),
                    "wins": _clean_number(group.get("win", pd.Series(dtype=float)).fillna(0).sum()),
                    "draws": _clean_number(group.get("draw", pd.Series(dtype=float)).fillna(0).sum()),
                    "losses": _clean_number(group.get("loss", pd.Series(dtype=float)).fillna(0).sum()),
                    "goals_for": _clean_number(gf),
                    "goals_against": _clean_number(ga),
                    "goal_diff": _clean_number(gf - ga),
                })
            standings.sort(key=lambda r: (r["points"], r["goal_diff"], r["goals_for"]), reverse=True)

    recent_matches: list[dict[str, Any]] = []
    if not base.empty and "league" in base.columns:
        bg = base[base["league"].astype(str) == league].copy()
        if not bg.empty:
            if "date" in bg.columns:
                bg["_date"] = pd.to_datetime(bg["date"], errors="coerce")
                bg = bg.sort_values("_date", ascending=False)
            cols = [c for c in ["event_id", "match_key", "date", "home_team", "away_team", "goals_home_ft", "goals_away_ft", "source_layer"] if c in bg.columns]
            recent_matches = bg[cols].head(30).fillna("").to_dict(orient="records")

    return {"ok": True, "data": {"league": league, "standings": standings, "recent_matches": recent_matches, "upcoming_matches": []}}
