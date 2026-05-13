from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .config import project_root

STATE_PATH = project_root() / "data" / "data_engine" / "state" / "flashscore_state.json"

def _base_state() -> dict[str, Any]:
    return {
        "provider": "flashscore",
        "current_index": 0,
        "processed_leagues": [],
        "processed_matches": [],
        "failed_leagues": [],
        "failed_matches": [],
        "retry_count": 0,
        "last_error": None,
        "last_successful_page": None,
        "last_successful_league": None,
        "mode": "internal",
        "provider_status": "not_started",
        "provider_health": "not_started",
    }

def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return _base_state()
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        base = _base_state(); base.update(state); return base
    except Exception:
        state = _base_state(); state["state_warning"] = "state_reset_after_invalid_json"; return state

def save_state(state: dict[str, Any]) -> Path:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    return STATE_PATH

def update_after_sync(*, processed_leagues: list[str], processed_matches: list[str], failed_leagues: list[str], test_mode: bool, batch_size: int | None, start_date: str, end_date: str, mode: str, provider_status: str, last_error: str | None = None, failed_matches: list[str] | None = None, last_successful_page: str | None = None, provider_health: str | None = None) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    state = load_state()
    failed_matches = failed_matches or []
    if processed_leagues:
        last_successful_league = processed_leagues[-1]
    else:
        last_successful_league = state.get("last_successful_league")
    state.update({
        "provider": "flashscore",
        "last_successful_run": now if provider_status in {"success", "empty_success"} and not failed_leagues else state.get("last_successful_run"),
        "last_run": now,
        "processed_leagues": processed_leagues,
        "current_index": len(processed_leagues),
        "failed_leagues": failed_leagues,
        "failed_matches": failed_matches,
        "processed_matches": sorted(set(state.get("processed_matches", []) + processed_matches)),
        "retry_count": int(state.get("retry_count", 0)) + (1 if failed_leagues or failed_matches or last_error else 0),
        "last_error": last_error,
        "last_successful_page": last_successful_page,
        "last_successful_league": last_successful_league,
        "start_date": start_date,
        "end_date": end_date,
        "test_mode": test_mode,
        "batch_size": batch_size,
        "mode": mode,
        "provider_status": provider_status,
        "provider_health": provider_health or provider_status,
    })
    save_state(state)
    return state
