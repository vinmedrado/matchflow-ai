from __future__ import annotations

import importlib.util
import json
import logging
from pathlib import Path


def _load_decision_engine(root: Path):
    path = root / "09_decision_engine" / "decision_engine.py"
    spec = importlib.util.spec_from_file_location("matchflow_decision_engine", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
    root = Path(__file__).resolve().parent
    module = _load_decision_engine(root)
    result = module.run_decision_engine(root)
    print(json.dumps(result, indent=2, ensure_ascii=False))
