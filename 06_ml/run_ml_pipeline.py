from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
import sys

try:
    from backend.core.logging_config import configure_logging, get_logger
except Exception:  # pragma: no cover
    import logging
    logging.basicConfig(level=logging.INFO)
    def configure_logging(*args, **kwargs):
        return None
    def get_logger(name: str):
        return logging.getLogger(name)

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from .dataset_builder import MLDatasetBuilder
    from .model_trainer import ModelTrainer
except Exception:  # pragma: no cover
    from dataset_builder import MLDatasetBuilder
    from model_trainer import ModelTrainer

logger = get_logger("matchflow.ml.pipeline")

def project_root() -> Path:
    return Path(__file__).resolve().parents[1]

def load_config(root: Path) -> Dict[str, Any]:
    path = root / "config/ml_config.json"
    if not path.exists():
        raise FileNotFoundError(f"ML config not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def run() -> Dict[str, Any]:
    configure_logging()
    root = project_root()
    config = load_config(root)
    logger.info("Iniciando pipeline ML Foundation 5.0")
    dataset = MLDatasetBuilder(root, config).build()
    result = ModelTrainer(root, config).train_all(dataset)
    logger.info("Pipeline ML Foundation finalizado")
    return result

if __name__ == "__main__":
    run()
