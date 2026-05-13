"""
odds_fetcher.py — Integração com The Odds API para odds em tempo real.
Gratuito: 500 requisições/mês. https://the-odds-api.com/
"""
from __future__ import annotations
import logging, os, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

try:
    import httpx
    _HTTPX_OK = True
except ImportError:
    _HTTPX_OK = False

logger = logging.getLogger("matchflow.data_ops.odds_fetcher")
BASE_URL = "https://api.the-odds-api.com/v4"

SPORT_MAP = {
    "BSA":  "soccer_brazil_campeonato",
    "PL":   "soccer_epl",
    "BL1":  "soccer_germany_bundesliga",
    "SA":   "soccer_italy_serie_a",
    "PD":   "soccer_spain_la_liga",
    "FL1":  "soccer_france_ligue_one",
    "CL":   "soccer_uefa_champs_league",
    "DED":  "soccer_netherlands_eredivisie",
    "PPL":  "soccer_portugal_primeira_liga",
}

MARKETS_MAP = {
    "goals":   ["totals"],        # over/under goals
    "btts":    ["btts"],          # both teams to score
    "h2h":     ["h2h"],           # 1X2
}

def _get_api_key() -> str:
    key = os.getenv("ODDS_API_KEY", "")
    if not key or key == "seu_token_aqui":
        raise ValueError("ODDS_API_KEY não configurada. Obtenha em https://the-odds-api.com/")
    return key

def _bookmakers_from_env() -> list[str]:
    env = os.getenv("ODDS_API_BOOKMAKERS", "pinnacle,betfair,bet365")
    return [b.strip() for b in env.split(",") if b.strip()]

def fetch_odds(sport_key: str, api_key: str, markets: list[str] | None = None,
               bookmakers: list[str] | None = None) -> list[dict]:
    if not _HTTPX_OK:
        return []
    if markets is None:
        markets = ["h2h", "totals", "btts"]
    if bookmakers is None:
        bookmakers = _bookmakers_from_env()

    url = f"{BASE_URL}/sports/{sport_key}/odds"
    params = {
        "apiKey": api_key,
        "regions": "eu",
        "markets": ",".join(markets),
        "bookmakers": ",".join(bookmakers),
        "oddsFormat": "decimal",
        "dateFormat": "iso",
    }
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, params=params)
        if resp.status_code == 422:
            logger.warning("Mercado não disponível para %s", sport_key)
            return []
        resp.raise_for_status()
        remaining = resp.headers.get("x-requests-remaining", "?")
        logger.info("%s: %s jogos com odds | requests restantes: %s", sport_key, len(resp.json()), remaining)
        return resp.json()
    except Exception as exc:
        logger.error("Falha odds %s: %s", sport_key, exc)
        return []

def _normalize_odds_event(event: dict) -> list[dict]:
    """Converte um evento da API em linhas normalizadas."""
    rows = []
    match_id = event.get("id")
    home = event.get("home_team", "")
    away = event.get("away_team", "")
    commence = event.get("commence_time", "")

    for bookie in event.get("bookmakers", []):
        bookmaker = bookie.get("key", "")
        for market in bookie.get("markets", []):
            mkey = market.get("key", "")
            last_update = market.get("last_update", "")
            for outcome in market.get("outcomes", []):
                rows.append({
                    "match_id": match_id,
                    "home_team": home,
                    "away_team": away,
                    "date": commence,
                    "bookmaker": bookmaker,
                    "market": mkey,
                    "selection": outcome.get("name"),
                    "point": outcome.get("point"),  # linha (ex: 2.5)
                    "odds_value": outcome.get("price"),
                    "last_update": last_update,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                })
    return rows

def fetch_all_odds(leagues: list[str] | None = None, api_key: str | None = None,
                   output_dir: Path | None = None) -> pd.DataFrame:
    """
    Busca odds de todas as ligas configuradas e salva snapshot.
    """
    key = api_key or _get_api_key()
    if leagues is None:
        env = os.getenv("FOOTBALL_DATA_LEAGUES", "PL,BL1,SA,PD,BSA")
        leagues = [l.strip() for l in env.split(",") if l.strip()]
    if output_dir is None:
        output_dir = Path("data/odds")
    output_dir.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict] = []
    for league in leagues:
        sport_key = SPORT_MAP.get(league)
        if not sport_key:
            logger.warning("Sport key desconhecido para liga %s", league)
            continue
        events = fetch_odds(sport_key, key)
        for event in events:
            all_rows.extend(_normalize_odds_event(event))
        time.sleep(1)

    if not all_rows:
        logger.warning("Nenhuma odd obtida.")
        return pd.DataFrame()

    df = pd.DataFrame(all_rows)
    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True).dt.tz_localize(None)
    df["odds_value"] = pd.to_numeric(df["odds_value"], errors="coerce")

    # Snapshot com timestamp
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    snap_path = output_dir / f"odds_snapshot_{ts}.parquet"
    safe_write_dataframe(df, snap_path, index=False)

    # Latest sempre sobrescreve
    latest_path = output_dir / "odds_latest.parquet"
    safe_write_dataframe(df, latest_path, index=False)
    logger.info("Odds salvas: %s linhas em %s", len(df), latest_path)
    return df

def get_best_odds(home_team: str, away_team: str, market: str, point: float | None = None,
                  selection: str | None = None, odds_df: pd.DataFrame | None = None) -> dict:
    """
    Retorna melhor odd disponível para um evento/mercado específico.
    Implementa line shopping automático.
    """
    if odds_df is None:
        latest = Path("data/odds/odds_latest.parquet")
        if not latest.exists():
            return {"best_odds": None, "best_bookmaker": None, "odds_comparison": {}}
        odds_df = safe_read_dataframe(latest)

    mask = (
        (odds_df["home_team"].str.lower() == home_team.lower()) &
        (odds_df["away_team"].str.lower() == away_team.lower()) &
        (odds_df["market"] == market)
    )
    if selection:
        mask &= odds_df["selection"].str.lower() == selection.lower()
    if point is not None:
        mask &= odds_df["point"] == point

    filtered = odds_df[mask].copy()
    if filtered.empty:
        return {"best_odds": None, "best_bookmaker": None, "odds_comparison": {}}

    comparison = (filtered.groupby("bookmaker")["odds_value"].max().to_dict())
    best_bookie = max(comparison, key=comparison.get)
    best_odds = comparison[best_bookie]

    # Pinnacle como referência de mercado
    pinnacle_odds = comparison.get("pinnacle")

    return {
        "best_odds": float(best_odds),
        "best_bookmaker": best_bookie,
        "pinnacle_odds": float(pinnacle_odds) if pinnacle_odds else None,
        "odds_comparison": comparison,
        "clv_potential": round((best_odds / pinnacle_odds - 1) * 100, 2) if pinnacle_odds else None,
    }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
    df = fetch_all_odds()
    print(f"Total linhas de odds: {len(df)}")
    if not df.empty:
        print(df[["home_team", "away_team", "market", "bookmaker", "odds_value"]].head(10))
