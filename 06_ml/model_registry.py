from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

try:
    from backend.core.logging_config import get_logger
except Exception:  # pragma: no cover
    import logging
    logging.basicConfig(level=logging.INFO)
    def get_logger(name: str):
        return logging.getLogger(name)

logger = get_logger("matchflow.ml.model_registry")

class ModelRegistry:
    def __init__(self, project_root: Path, config: Dict[str, Any]) -> None:
        self.project_root = project_root
        self.models_dir = self.project_root / config.get("models_dir", "data/ml/models")
        self.registry_path = self.models_dir / "registry.json"
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, Any]:
        if not self.registry_path.exists():
            return {"version": "5.0.0", "models": []}
        try:
            return json.loads(self.registry_path.read_text(encoding="utf-8"))
        except Exception:
            return {"version": "5.0.0", "models": []}

    def register(self, record: Dict[str, Any]) -> None:
        payload = self.load()
        payload["version"] = "5.0.0"
        payload.setdefault("models", [])
        record = dict(record)
        record["registered_at"] = datetime.now(timezone.utc).isoformat()
        payload["models"].append(record)
        self.registry_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Modelo ML registrado: market=%s model=%s", record.get("market"), record.get("model_name"))
