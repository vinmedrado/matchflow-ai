from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from common import SYNC_REPORT_PATH, utc_now_iso, write_json  # type: ignore
    from data_ops_state import load_state, save_state  # type: ignore
    from engine_discovery import discover_engine  # type: ignore
else:
    from .common import SYNC_REPORT_PATH, utc_now_iso, write_json
    from .data_ops_state import load_state, save_state
    from .engine_discovery import discover_engine

logger = logging.getLogger("matchflow.data_ops.engine_sync")


def sync_engine_outputs(config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Record internal provider readiness without copying from separate repos."""
    discovery = discover_engine(config=config or {}, write_report=False)
    state = load_state()
    state.update({
        "last_engine_sync": utc_now_iso(),
        "engine_path": discovery.get("engine_path"),
        "engine_status": discovery.get("engine_status"),
        "engine_files_count": discovery.get("engine_files_count", 0),
        "internal_provider": True,
    })
    save_state(state)
    report = {
        "synced_at": state["last_engine_sync"],
        "status": "SYNCED" if discovery.get("engine_status") == "ENGINE_READY" else "SKIPPED",
        "engine_path": discovery.get("engine_path"),
        "total_files_seen": discovery.get("engine_files_count", 0),
        "new_files": [],
        "changed_files": [],
        "unchanged_files_count": discovery.get("engine_files_count", 0),
        "internal_provider": True,
        "uses_external_repo": False,
    }
    write_json(SYNC_REPORT_PATH, report)
    logger.info("Internal provider sync status recorded: %s", report["status"])
    return report
