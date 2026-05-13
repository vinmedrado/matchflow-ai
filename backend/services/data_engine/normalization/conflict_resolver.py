from __future__ import annotations
from pathlib import Path
import json
from typing import Any


def append_conflict(root: Path, conflict: dict[str, Any]) -> None:
    path = root / 'backend/services/data_engine/audit/conflicts_report.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    try: data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    except Exception: data = []
    data.append(conflict)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
