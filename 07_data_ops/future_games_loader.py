from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from common import FUTURE_SNAPSHOT_PATH, load_config, utc_now_iso  # type: ignore
    from data_ops_state import update_state  # type: ignore
    from future_games_discovery import discover_future_games  # type: ignore
else:
    from .common import FUTURE_SNAPSHOT_PATH, load_config, utc_now_iso
    from .data_ops_state import update_state
    from .future_games_discovery import discover_future_games

logger = logging.getLogger("matchflow.data_ops.future_games_loader")

COLUMN_ALIASES = {
    "event_id": "match_id", "match_id": "match_id", "game_id": "match_id", "id_jogo": "match_id",
    "date": "date", "data": "date", "match_date": "date",
    "league": "league", "liga": "league", "competition": "league",
    "home": "home_team", "home_team": "home_team", "mandante": "home_team",
    "away": "away_team", "away_team": "away_team", "visitante": "away_team",
    "odds": "odds", "odd": "odds", "price": "odds",
}
OUTPUT_COLUMNS = ["match_id", "date", "league", "home_team", "away_team", "odds", "source_file"]


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {}
    for col in df.columns:
        key = str(col).strip().lower().replace(" ", "_")
        renamed[col] = COLUMN_ALIASES.get(key, key)
    df = df.rename(columns=renamed)
    for col in OUTPUT_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def _load_json(path: Path) -> pd.DataFrame:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return pd.DataFrame(raw)
    if isinstance(raw, dict):
        for key in ["data", "matches", "events", "games"]:
            if isinstance(raw.get(key), list):
                return pd.DataFrame(raw[key])
        return pd.DataFrame([raw])
    return pd.DataFrame()


def _load_jsonl(path: Path) -> pd.DataFrame:
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return pd.DataFrame(records)


def _load_file(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".json":
        return _load_json(path)
    if path.suffix.lower() == ".jsonl":
        return _load_jsonl(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() == ".parquet":
        return safe_read_dataframe(path)
    return pd.DataFrame()


def load_future_games_snapshot(config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    config = config or load_config()
    discovery = discover_future_games(config=config)
    data_files = [Path(p) for p in discovery.get("data_files", [])]
    frames: List[pd.DataFrame] = []
    failed: List[Dict[str, str]] = []
    for path in data_files:
        try:
            df = _load_file(path)
            if df.empty:
                logger.warning("Arquivo futuro vazio ignorado: %s", path)
                continue
            df = _normalize_columns(df)
            df["source_file"] = str(path)
            frames.append(df)
        except Exception as exc:
            logger.error("Falha ao carregar futuro %s: %s", path, exc)
            failed.append({"file": str(path), "error": str(exc)})

    if frames:
        snapshot = pd.concat(frames, ignore_index=True)
        snapshot = snapshot[OUTPUT_COLUMNS + [c for c in snapshot.columns if c not in OUTPUT_COLUMNS]]
        status = "FUTURE_GAMES_SNAPSHOT_READY"
    else:
        snapshot = pd.DataFrame(columns=OUTPUT_COLUMNS)
        status = discovery.get("future_games_status", "FUTURE_GAMES_NO_DATA_FILES")

    FUTURE_SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    safe_write_dataframe(snapshot, FUTURE_SNAPSHOT_PATH, index=False)
    update_state(
        future_games_path=discovery.get("future_games_path"),
        future_games_status=status,
        future_games_files_count=len(data_files),
    )
    report = {
        "loaded_at": utc_now_iso(),
        "status": status,
        "rows": int(len(snapshot)),
        "files_loaded": len(frames),
        "files_failed": len(failed),
        "failed_files": failed,
        "snapshot_path": str(FUTURE_SNAPSHOT_PATH),
        "source_status": discovery.get("future_games_status"),
        "messages": discovery.get("messages", []),
    }
    logger.info("Snapshot jogos futuros status=%s rows=%s files=%s", status, len(snapshot), len(frames))
    return report
