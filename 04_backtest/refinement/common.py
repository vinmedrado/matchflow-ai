
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pandas as pd


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def backtest_root() -> Path:
    return Path(__file__).resolve().parents[1]


def data_path(*parts: str) -> Path:
    return project_root().joinpath(*parts)


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return default
        return int(float(value))
    except Exception:
        return default


def normalize_pct(value: Any) -> float:
    number = safe_float(value, 0.0)
    if abs(number) > 1.5:
        return number / 100.0
    return number


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    import json
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(df: pd.DataFrame, path: Path) -> None:
    ensure_dir(path.parent)
    df.to_csv(path, index=False)


def risk_level_from_flags(flags: list[str]) -> str:
    severe = {"LOW_SAMPLE_SIZE", "HIGH_DRAWDOWN", "POSSIBLE_OVERFITTING"}
    if any(flag in severe for flag in flags):
        return "HIGH"
    if flags:
        return "MEDIUM"
    return "LOW"
