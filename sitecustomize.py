"""Runtime storage compatibility for local scripts and legacy modules.

This module is loaded automatically by Python when the project root is on
PYTHONPATH. It keeps legacy direct pandas parquet calls from crashing in lean
environments while the main code uses backend.core.storage explicitly.
"""
from __future__ import annotations

from pathlib import Path
import logging

try:
    import pandas as _pd
except Exception:  # pragma: no cover
    _pd = None

_logger = logging.getLogger("matchflow.storage.compat")

if _pd is not None and not getattr(_pd, "_matchflow_parquet_compat", False):
    _original_read_parquet = _pd.read_parquet
    _original_to_parquet = _pd.DataFrame.to_parquet

    def _csv_path(path):
        p = Path(path)
        return p.with_suffix(".csv") if p.suffix.lower() == ".parquet" else p

    def _is_engine_error(exc: Exception) -> bool:
        text = str(exc).lower()
        return any(x in text for x in ["pyarrow", "fastparquet", "parquet engine", "unable to find a usable engine"])

    def _safe_read_parquet(path, *args, **kwargs):
        try:
            return _original_read_parquet(path, *args, **kwargs)
        except Exception as exc:
            csv = _csv_path(path)
            if csv.exists() and (_is_engine_error(exc) or not Path(path).exists()):
                _logger.warning("Parquet read fallback to CSV: %s -> %s (%s)", path, csv, exc)
                columns = kwargs.get("columns")
                df = _pd.read_csv(csv)
                if columns:
                    cols = [c for c in columns if c in df.columns]
                    return df[cols]
                return df
            raise

    def _safe_to_parquet(self, path, *args, **kwargs):
        try:
            return _original_to_parquet(self, path, *args, **kwargs)
        except Exception as exc:
            if _is_engine_error(exc):
                csv = _csv_path(path)
                csv.parent.mkdir(parents=True, exist_ok=True)
                index = bool(kwargs.get("index", False))
                _logger.warning("Parquet write fallback to CSV: %s -> %s (%s)", path, csv, exc)
                return self.to_csv(csv, index=index)
            raise

    _pd.read_parquet = _safe_read_parquet
    _pd.DataFrame.to_parquet = _safe_to_parquet
    _pd._matchflow_parquet_compat = True
