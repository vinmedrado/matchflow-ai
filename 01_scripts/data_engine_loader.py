"""DEPRECATED LEGACY COMPATIBILITY.

This module is kept only for migration history and backward-compatible imports.
The production Data Engine uses the internal provider at
backend/services/data_engine/providers/flashscore/.

Only internal generated outputs are read by this compatibility loader.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

import pandas as pd

from backend.core.storage import safe_read_dataframe

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DataEngineLoader:
    """Compatibility loader backed by MatchFlow's internal FlashScore outputs."""

    def __init__(self, config: Dict[str, Any] | None = None, football_saas_root: Path | None = None) -> None:
        self.config = config or {}
        self.root = football_saas_root or PROJECT_ROOT

    def _read_internal_output(self) -> pd.DataFrame:
        candidates = [
            self.root / "data/raw/flashscore_matches.parquet",
            self.root / "data/raw/flashscore_matches.csv",
            self.root / "data/processed/data_engine_base.parquet",
            self.root / "data/processed/data_engine_base.csv",
        ]
        for path in candidates:
            if path.exists():
                return safe_read_dataframe(path)
        return pd.DataFrame()

    def run(self) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        df = self._read_internal_output()
        stats = {
            "files_found": 1 if len(df) else 0,
            "files_loaded": 1 if len(df) else 0,
            "files_failed": 0,
            "raw_records": int(len(df)),
            "processed_records": int(len(df)),
            "duplicates_removed_event_id": 0,
            "duplicates_removed_match_key": 0,
            "quality_gate": "PASS" if len(df) else "NO_INTERNAL_OUTPUTS_YET",
            "internal_provider": True,
            "uses_external_repo": False,
        }
        return df, stats
