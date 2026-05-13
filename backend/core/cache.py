from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from backend.core.storage import safe_read_dataframe

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    value: Any
    path: Path
    modified_at: float
    loaded_at: float
    load_time_ms: float
    status: str


class FileCache:
    def __init__(self) -> None:
        self._items: dict[str, CacheEntry] = {}

    def _mtime(self, path: Path) -> Optional[float]:
        try:
            return path.stat().st_mtime
        except FileNotFoundError:
            return None

    def get_parquet(self, key: str, path: Path) -> tuple[Optional[pd.DataFrame], dict]:
        return self._get(key, path, lambda p: safe_read_dataframe(p, required=True))

    def get_json(self, key: str, path: Path) -> tuple[Optional[dict], dict]:
        return self._get(key, path, lambda p: json.loads(p.read_text(encoding="utf-8")))

    def _get(self, key: str, path: Path, loader) -> tuple[Any, dict]:
        path = Path(path)
        mtime = self._mtime(path)
        if mtime is None:
            logger.warning("Cache miss: arquivo não encontrado | key=%s | path=%s", key, path)
            self._items.pop(key, None)
            return None, {"cache_status": "miss", "reason": "file_not_found", "load_time_ms": 0}

        current = self._items.get(key)
        if current and current.path == path and current.modified_at == mtime:
            logger.info("Cache hit | key=%s | path=%s", key, path)
            return current.value, {"cache_status": "hit", "load_time_ms": round(current.load_time_ms, 2)}

        start = time.perf_counter()
        try:
            value = loader(path)
        except Exception as exc:
            logger.exception("Falha ao carregar arquivo em cache | key=%s | path=%s | error=%s", key, path, exc)
            return None, {"cache_status": "error", "reason": str(exc), "load_time_ms": 0}

        load_time_ms = (time.perf_counter() - start) * 1000
        self._items[key] = CacheEntry(
            value=value,
            path=path,
            modified_at=mtime,
            loaded_at=time.time(),
            load_time_ms=load_time_ms,
            status="loaded",
        )
        logger.info("Cache miss -> loaded | key=%s | path=%s | %.2fms", key, path, load_time_ms)
        return value, {"cache_status": "miss", "load_time_ms": round(load_time_ms, 2)}

    def clear(self) -> None:
        self._items.clear()


file_cache = FileCache()
