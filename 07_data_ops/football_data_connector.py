"""
football_data_connector.py — Integração com football-data.org API.
Dados históricos reais para múltiplas ligas e temporadas.
"""
from __future__ import annotations
import logging, os, time
from pathlib import Path
from typing import Any
import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

try:
    import httpx
    _HTTPX_OK = True
except ImportError:
    _HTTPX_OK = False

logger = logging.getLogger("matchflow.data_ops.football_data_connector")
BASE_URL = "https://api.football-data.org/v4"

LEAGUE_MAP = {
    "PL": "Premier League", "BL1": "Bundesliga", "SA": "Serie A",
    "PD": "La Liga", "FL1": "Ligue 1", "BSA": "Brasileiro Serie A",
    "CL": "Champions League", "PPL": "Primeira Liga", "DED": "Eredivisie",
}

def _get_api_key() -> str:
    key = os.getenv("FOOTBALL_DATA_API_KEY", "")
    if not key or key == "seu_token_aqui":
        raise ValueError("FOOTBALL_DATA_API_KEY não configurada. Obtenha em https://www.football-data.org/client/register")
    return key

def _nested(d: dict, key: str) -> Any:
    parts = key.split(".")
    val = d
    for p in parts:
        val = val.get(p) if isinstance(val, dict) else None
    return val

def _flatten_match(match: dict) -> dict:
    row = {
        "match_id": _nested(match, "id"),
        "date": _nested(match, "utcDate"),
        "league": _nested(match, "competition.name"),
        "competition_code": _nested(match, "competition.code") or "",
        "home_team": _nested(match, "homeTeam.name"),
        "away_team": _nested(match, "awayTeam.name"),
        "home_team_id": _nested(match, "homeTeam.id"),
        "away_team_id": _nested(match, "awayTeam.id"),
        "goals_home_ft": _nested(match, "score.fullTime.home"),
        "goals_away_ft": _nested(match, "score.fullTime.away"),
        "goals_home_ht": _nested(match, "score.halfTime.home"),
        "goals_away_ht": _nested(match, "score.halfTime.away"),
        "match_status": match.get("status"),
        "matchday": match.get("matchday"),
        "season": _nested(match, "season.startDate"),
        "source": "football-data.org",
    }
    gh, ga = row.get("goals_home_ft"), row.get("goals_away_ft")
    if gh is not None and ga is not None:
        try:
            gh, ga = int(gh), int(ga)
            row["total_goals_ft"] = gh + ga
            row["btts"] = gh > 0 and ga > 0
            row["over_1_5"] = gh + ga > 1
            row["over_2_5"] = gh + ga > 2
            row["over_3_5"] = gh + ga > 3
            row["result"] = "H" if gh > ga else ("A" if ga > gh else "D")
        except Exception:
            pass
    return row

def fetch_matches(league_code: str, season: int, api_key: str, status: str = "FINISHED") -> list[dict]:
    if not _HTTPX_OK:
        logger.error("httpx não instalado. Execute: pip install httpx")
        return []
    url = f"{BASE_URL}/competitions/{league_code}/matches"
    headers = {"X-Auth-Token": api_key}
    params = {"season": season, "status": status}
    try:
        logger.info("Buscando %s/%s...", league_code, season)
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, headers=headers, params=params)
        if resp.status_code == 429:
            logger.warning("Rate limit. Aguardando 65s...")
            time.sleep(65)
            with httpx.Client(timeout=30) as client:
                resp = client.get(url, headers=headers, params=params)
        if resp.status_code == 403:
            logger.error("Acesso negado para %s. Verifique plano da API key.", league_code)
            return []
        resp.raise_for_status()
        matches = resp.json().get("matches", [])
        logger.info("  → %s jogos (%s/%s)", len(matches), league_code, season)
        time.sleep(6.5)
        return matches
    except Exception as exc:
        logger.error("Falha %s/%s: %s", league_code, season, exc)
        return []

def fetch_historical_data(api_key: str | None = None, leagues: list[str] | None = None,
                           seasons: list[int] | None = None, output_dir: Path | None = None) -> pd.DataFrame:
    key = api_key or _get_api_key()
    if leagues is None:
        env = os.getenv("FOOTBALL_DATA_LEAGUES", "PL,BL1,SA,PD,BSA")
        leagues = [l.strip() for l in env.split(",") if l.strip()]
    if seasons is None:
        env = os.getenv("FOOTBALL_DATA_SEASONS", "2022,2023,2024")
        seasons = [int(s.strip()) for s in env.split(",") if s.strip().isdigit()]
    if output_dir is None:
        output_dir = Path("data/raw/historical")
    output_dir.mkdir(parents=True, exist_ok=True)

    all_frames: list[pd.DataFrame] = []
    for league in leagues:
        frames = []
        for season in seasons:
            raw = fetch_matches(league, season, key)
            if not raw:
                continue
            df = pd.DataFrame([_flatten_match(m) for m in raw])
            df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True).dt.tz_localize(None)
            frames.append(df)
        if frames:
            league_df = pd.concat(frames, ignore_index=True)
            league_df = league_df[league_df["match_status"] == "FINISHED"].copy()
            path = output_dir / f"{league.lower()}_historical.parquet"
            safe_write_dataframe(league_df, path, index=False)
            logger.info("Salvo %s: %s jogos", path.name, len(league_df))
            all_frames.append(league_df)

    if not all_frames:
        logger.warning("Nenhum dado obtido. Verifique API key.")
        return pd.DataFrame()

    consolidated = pd.concat(all_frames, ignore_index=True).sort_values("date").reset_index(drop=True)
    out_path = output_dir / "all_leagues_historical.parquet"
    safe_write_dataframe(consolidated, out_path, index=False)
    logger.info("Consolidado: %s jogos em %s", len(consolidated), out_path)
    return consolidated

def fetch_upcoming_matches(league_code: str, api_key: str | None = None) -> pd.DataFrame:
    if not _HTTPX_OK:
        return pd.DataFrame()
    key = api_key or _get_api_key()
    url = f"{BASE_URL}/competitions/{league_code}/matches"
    headers = {"X-Auth-Token": key}
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, headers=headers, params={"status": "SCHEDULED"})
        resp.raise_for_status()
        rows = [_flatten_match(m) for m in resp.json().get("matches", [])]
        df = pd.DataFrame(rows) if rows else pd.DataFrame()
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True).dt.tz_localize(None)
        return df
    except Exception as exc:
        logger.error("Falha upcoming %s: %s", league_code, exc)
        return pd.DataFrame()

def get_match_result(match_id: int, api_key: str | None = None) -> dict | None:
    if not _HTTPX_OK:
        return None
    key = api_key or _get_api_key()
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{BASE_URL}/matches/{match_id}", headers={"X-Auth-Token": key})
        resp.raise_for_status()
        return _flatten_match(resp.json().get("match", resp.json()))
    except Exception as exc:
        logger.warning("Falha resultado match %s: %s", match_id, exc)
        return None

if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
    df = fetch_historical_data()
    print(f"Total jogos: {len(df)}")
