"""DEPRECATED LEGACY COMPATIBILITY.

This file is preserved only so old imports keep working. The production Data
Engine uses the internal provider at backend/services/data_engine/providers/flashscore/.

The bridge now delegates only to the internal provider and never reads an
separate repository.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def get_bridge_status(saas_root: Path | None = None) -> Dict[str, Any]:
    root = saas_root or PROJECT_ROOT
    provider_path = root / "backend/services/data_engine/providers/flashscore"
    report_path = root / "data/reports/flashscore_sync_report.json"
    return {
        "status": "READY" if provider_path.exists() else "MISSING",
        "provider": "internal_flashscore_provider",
        "provider_path": str(provider_path),
        "report_path": str(report_path),
        "report_exists": report_path.exists(),
        "internal_provider": True,
        "uses_external_repo": False,
        "is_using_external_repo": False,
    }


def run_flashscore_bridge(saas_root: Path | None = None) -> Dict[str, Any]:
    from backend.services.data_engine.providers.flashscore import run_flashscore_sync

    result = run_flashscore_sync()
    return {
        "status": "OK" if result.get("ok", True) else "FAILED",
        "provider": "internal_flashscore_provider",
        "rows": result.get("total_records", result.get("rows", 0)),
        "internal_provider": True,
        "uses_external_repo": False,
        "is_using_external_repo": False,
        "result": result,
    }


if __name__ == "__main__":
    print(run_flashscore_bridge())
