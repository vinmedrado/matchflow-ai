"""DEPRECATED LEGACY COMPATIBILITY.

This module is kept only for backward-compatible imports from older Data Ops tests
and endpoints. The production Data Engine uses the internal provider at
backend/services/data_engine/providers/flashscore/.

It only reports the internal provider status.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from common import DISCOVERY_REPORT_PATH, supported_files, utc_now_iso, write_json  # type: ignore
else:
    from .common import DISCOVERY_REPORT_PATH, supported_files, utc_now_iso, write_json

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INTERNAL_PROVIDER_PATH = PROJECT_ROOT / "backend/services/data_engine/providers/flashscore"
INTERNAL_OUTPUT_CANDIDATES = [
    PROJECT_ROOT / "data/raw/flashscore_matches.parquet",
    PROJECT_ROOT / "data/raw/flashscore_matches.csv",
    PROJECT_ROOT / "data/reports/flashscore_sync_report.json",
]


def discover_engine(config: Dict[str, Any] | None = None, write_report: bool = True) -> Dict[str, Any]:
    """Return the operational status of the internal MatchFlow Data Engine.

    The legacy function name is intentionally preserved for import compatibility,
    but the implementation is fully internal and self-contained.
    """
    config = config or {}
    formats = config.get("accepted_file_formats", [".json", ".jsonl", ".csv", ".parquet"])
    provider_exists = INTERNAL_PROVIDER_PATH.exists()
    files = [path for path in INTERNAL_OUTPUT_CANDIDATES if path.exists() and path.is_file()]
    for rel in config.get("internal_output_candidates", []):
        base = PROJECT_ROOT / rel
        if base.is_dir():
            files.extend(supported_files(base, formats))
        elif base.exists() and base.is_file():
            files.append(base)
    unique_files = sorted({p.resolve() for p in files})
    status = "ENGINE_READY" if provider_exists else "ENGINE_MISSING"
    messages = [
        "Internal FlashScore provider is the active MatchFlow Data Engine.",
        "The internal provider is sufficient for pipeline, tests, demo, and API status.",
    ]
    if not unique_files:
        messages.append("Internal provider is available; run the sync or full decision pipeline to refresh generated outputs.")
    report = {
        "checked_at": utc_now_iso(),
        "engine_status": status,
        "engine_path": str(INTERNAL_PROVIDER_PATH),
        "engine_files_count": len(unique_files),
        "output_directories": [str(p.parent.relative_to(PROJECT_ROOT)) for p in unique_files],
        "checked_paths": [str(p.relative_to(PROJECT_ROOT)) for p in INTERNAL_OUTPUT_CANDIDATES],
        "messages": messages,
        "actionable_next_step": "Use python run_full_decision_pipeline.py or POST /api/data-engine/providers/flashscore/sync.",
        "internal_provider": True,
        "uses_external_repo": False,
        "is_using_external_repo": False,
    }
    if write_report:
        write_json(DISCOVERY_REPORT_PATH, report)
    return report


def main() -> int:
    report = discover_engine(write_report=True)
    print(report)
    return 0 if report["engine_status"] == "ENGINE_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
