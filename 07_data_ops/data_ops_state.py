from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
try:
    from .common import STATE_PATH, ensure_ops_dirs, load_json, utc_now_iso, write_json
except ImportError:
    from common import STATE_PATH, ensure_ops_dirs, load_json, utc_now_iso, write_json
DEFAULT_STATE: Dict[str, Any] = {"last_discovery_at": None, "last_engine_sync": None, "engine_path": None, "engine_status": "UNKNOWN", "engine_files_count": 0, "future_games_path": None, "future_games_status": "UNKNOWN", "future_games_files_count": 0, "processed_files": {}, "last_paper_trading_update": None, "last_ml_prediction_update": None}
def load_state(path: Path = STATE_PATH) -> Dict[str, Any]:
    ensure_ops_dirs(); state = load_json(path, DEFAULT_STATE.copy()); merged = DEFAULT_STATE.copy();
    if isinstance(state, dict): merged.update(state)
    return merged
def save_state(state: Dict[str, Any], path: Path = STATE_PATH) -> Dict[str, Any]:
    ensure_ops_dirs(); state["updated_at"] = utc_now_iso(); write_json(path, state); return state
def update_state(**updates: Any) -> Dict[str, Any]:
    state = load_state(); state.update(updates); return save_state(state)
