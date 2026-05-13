from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import MODE, automation_dir, load_json, save_json, utc_now


def default_state() -> dict[str, Any]:
    return {
        "mode": MODE,
        "overall_status": "NOT_RUN",
        "last_run_at": None,
        "last_export_at": None,
        "last_report_at": None,
        "last_alert_dispatch_at": None,
        "last_job_status": None,
        "runs_count": 0,
    }


def state_path(root: Path) -> Path:
    return automation_dir(root) / "automation_state.json"


def load_state(root: Path) -> dict[str, Any]:
    data = load_json(state_path(root), default_state())
    merged = default_state()
    if isinstance(data, dict):
        merged.update(data)
    merged["mode"] = MODE
    return merged


def save_state(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    state["mode"] = MODE
    save_json(state_path(root), state)
    return state


def mark_run(root: Path, status: str) -> dict[str, Any]:
    state = load_state(root)
    state["overall_status"] = status
    state["last_run_at"] = utc_now()
    state["last_job_status"] = status
    state["runs_count"] = int(state.get("runs_count") or 0) + 1
    return save_state(root, state)


def mark_export(root: Path) -> dict[str, Any]:
    state = load_state(root)
    state["last_export_at"] = utc_now()
    return save_state(root, state)


def mark_report(root: Path) -> dict[str, Any]:
    state = load_state(root)
    state["last_report_at"] = utc_now()
    return save_state(root, state)


def mark_alert_dispatch(root: Path) -> dict[str, Any]:
    state = load_state(root)
    state["last_alert_dispatch_at"] = utc_now()
    return save_state(root, state)
