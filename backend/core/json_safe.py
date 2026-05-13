from __future__ import annotations

import math
from typing import Any

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None  # type: ignore


def json_safe(value: Any) -> Any:
    """Recursively convert values to strict JSON-compatible objects.

    NaN/inf/-inf are represented as None instead of being emitted as invalid
    JSON. This keeps API responses strict without hiding that fields are absent.
    """
    if value is None:
        return None
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(v) for v in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if np is not None:
        if isinstance(value, np.generic):
            return json_safe(value.item())
        try:
            if isinstance(value, np.ndarray):
                return json_safe(value.tolist())
        except Exception:
            pass
    if pd is not None:
        try:
            if value is pd.NaT:
                return None
            if pd.isna(value) and not isinstance(value, (str, bytes, bool)):
                return None
        except Exception:
            pass
        try:
            if hasattr(value, 'isoformat'):
                return value.isoformat()
        except Exception:
            pass
    return value
