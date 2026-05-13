from __future__ import annotations

import importlib.util
import logging
import os
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

logger = logging.getLogger("matchflow.storage")

PARQUET_ENGINE_ORDER = ("pyarrow", "fastparquet")


def get_parquet_engine() -> str | None:
    """Return the first available parquet engine, preferring pyarrow.

    Set MATCHFLOW_DISABLE_PARQUET=1 to force CSV fallback in CI/tests or in
    constrained environments where optional parquet wheels are unavailable.
    """
    if os.getenv("MATCHFLOW_DISABLE_PARQUET", "").strip().lower() in {"1", "true", "yes", "on"}:
        return None
    for engine in PARQUET_ENGINE_ORDER:
        if importlib.util.find_spec(engine) is not None:
            return engine
    return None


def has_parquet_support() -> bool:
    return get_parquet_engine() is not None


def csv_fallback_path(path: str | Path) -> Path:
    p = Path(path)
    if p.suffix.lower() == ".parquet":
        return p.with_suffix(".csv")
    return p


def storage_status() -> dict[str, Any]:
    engine = get_parquet_engine()
    return {
        "parquet_available": engine is not None,
        "parquet_engine": engine,
        "storage_fallback_enabled": True,
        "csv_fallback_enabled": True,
        "storage_mode": "parquet" if engine else "csv_fallback",
        "recommended_install": "pip install pyarrow fastparquet",
        "preference_order": list(PARQUET_ENGINE_ORDER) + ["csv"],
    }


def _warning(message: str, **extra: Any) -> dict[str, Any]:
    payload = {"storage_warning": message, **extra}
    logger.warning("%s | %s", message, extra)
    return payload


def safe_write_dataframe(
    df: pd.DataFrame,
    path: str | Path,
    *,
    index: bool = False,
    also_write_csv: bool = False,
) -> dict[str, Any]:
    """Write dataframe with Parquet preferred and CSV fallback.

    Returns metadata suitable for summaries/reports.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    engine = get_parquet_engine()
    meta: dict[str, Any] = {
        "requested_path": str(p),
        "parquet_path": str(p if p.suffix.lower() == ".parquet" else p.with_suffix(".parquet")),
        "csv_path": str(csv_fallback_path(p)),
        "parquet_available": engine is not None,
        "parquet_engine": engine,
        "fallback_used": False,
        "fallback_reason": None,
        "storage_format": None,
        "rows": int(len(df)),
    }

    if p.suffix.lower() == ".csv":
        df.to_csv(p, index=index)
        meta["storage_format"] = "csv"
        return meta

    if engine:
        try:
            df.to_parquet(p, index=index, engine=engine)
            meta["storage_format"] = "parquet"
            if also_write_csv:
                df.to_csv(csv_fallback_path(p), index=index)
            return meta
        except Exception as exc:  # pragma: no cover - defensive for engine runtime failures
            meta.update(_warning("Parquet write failed; using CSV fallback", error=str(exc)))

    else:
        meta.update(_warning("No parquet engine available; using CSV fallback"))

    csv_path = csv_fallback_path(p)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=index)
    if p.suffix.lower() == ".parquet" and not p.exists():
        p.touch()
    meta.update({
        "storage_format": "csv",
        "fallback_used": True,
        "fallback_reason": meta.get("storage_warning") or "parquet_unavailable",
    })
    return meta


def safe_read_dataframe(path: str | Path, *, columns: Iterable[str] | None = None, required: bool = False) -> pd.DataFrame:
    """Read dataframe with Parquet preferred and CSV fallback.

    Missing optional files return an empty DataFrame. Missing required files raise
    FileNotFoundError so critical pipeline errors are not hidden.
    """
    p = Path(path)
    candidates: list[Path] = []
    if p.suffix.lower() == ".parquet":
        candidates = [p, p.with_suffix(p.suffix + ".csv"), p.with_suffix(".csv")]
    elif p.suffix.lower() == ".csv":
        candidates = [p, p.with_suffix(".parquet")]
    else:
        candidates = [p.with_suffix(".parquet"), p.with_suffix(".csv"), p]

    last_error: Exception | None = None
    for candidate in candidates:
        if not candidate.exists():
            continue
        try:
            if candidate.suffix.lower() == ".parquet":
                engine = get_parquet_engine()
                if not engine:
                    logger.warning("Parquet file exists but no engine is available; trying CSV fallback: %s", candidate)
                    continue
                return pd.read_parquet(candidate, columns=list(columns) if columns else None, engine=engine)
            if candidate.suffix.lower() == ".csv":
                df = pd.read_csv(candidate)
                if columns:
                    available = [c for c in columns if c in df.columns]
                    return df[available]
                return df
        except Exception as exc:
            last_error = exc
            logger.warning("Failed to read %s (%s); trying fallback", candidate, exc)
            continue

    if required:
        raise FileNotFoundError(f"No readable dataframe found for {p}; last_error={last_error}")
    return pd.DataFrame()


def safe_read_parquet_or_csv(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    return safe_read_dataframe(path, **kwargs)


def safe_write_parquet_with_csv_fallback(df: pd.DataFrame, path: str | Path, **kwargs: Any) -> dict[str, Any]:
    return safe_write_dataframe(df, path, **kwargs)
