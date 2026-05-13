from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

MODE = "PAPER_TRADING_SIMULATION_ONLY"
logger = logging.getLogger("matchflow.monitoring")


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def safe_json(path: Path, default: Any | None = None) -> Any:
    if default is None:
        default = {}
    try:
        if not path.exists() or path.stat().st_size == 0:
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Falha ao ler JSON %s: %s", path, exc)
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def safe_csv(path: Path) -> pd.DataFrame:
    try:
        if not path.exists() or path.stat().st_size == 0:
            return pd.DataFrame()
        return pd.read_csv(path)
    except Exception as exc:
        logger.warning("Falha ao ler CSV %s: %s", path, exc)
        return pd.DataFrame()


def safe_parquet(path: Path) -> pd.DataFrame:
    try:
        if not path.exists() or path.stat().st_size == 0:
            return pd.DataFrame()
        return safe_read_dataframe(path)
    except Exception as exc:
        logger.warning("Falha ao ler Parquet %s: %s", path, exc)
        return pd.DataFrame()


def pct_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0 if current == 0 else 100.0
    return ((current - previous) / abs(previous)) * 100.0


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))
