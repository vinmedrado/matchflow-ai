"""DEPRECATED LEGACY COMPATIBILITY.

This module is kept only for backward-compatible imports from older Data Ops
routes. The production Data Engine uses the internal provider at
backend/services/data_engine/providers/flashscore/.

Only internal provider calls are executed here.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def get_engine_status(saas_root: Path | None = None) -> Dict[str, Any]:
    root = saas_root or PROJECT_ROOT
    provider_path = root / "backend/services/data_engine/providers/flashscore"
    outputs = [
        root / "data/raw/flashscore_matches.parquet",
        root / "data/raw/flashscore_matches.csv",
        root / "data/reports/flashscore_sync_report.json",
    ]
    ready_outputs = [str(p.relative_to(root)) for p in outputs if p.exists()]
    return {
        "status": "READY" if provider_path.exists() else "MISSING",
        "engine_status": "ENGINE_READY" if provider_path.exists() else "ENGINE_MISSING",
        "engine_path": str(provider_path),
        "internal_provider": True,
        "uses_external_repo": False,
        "is_using_external_repo": False,
        "outputs_ready": ready_outputs,
        "message": "Internal FlashScore provider is the active MatchFlow Data Engine.",
    }


def run_engine(saas_root: Path | None = None, mode: str = "incremental", days_back: int = 7, stream_logs: bool = False) -> Dict[str, Any]:
    from backend.services.data_engine.providers.flashscore import run_flashscore_sync

    result = run_flashscore_sync()
    return {
        "ok": bool(result.get("ok", True)),
        "mode": mode,
        "days_back": days_back,
        "internal_provider": True,
        "uses_external_repo": False,
        "is_using_external_repo": False,
        "result": result,
    }


if __name__ == "__main__":
    print(run_engine())
