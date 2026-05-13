from __future__ import annotations

import json
import logging
from pathlib import Path
import importlib.util


def _load_runner():
    path = Path(__file__).resolve().parent / "decision_engine.py"
    spec = importlib.util.spec_from_file_location("matchflow_decision_engine", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
    module = _load_runner()
    result = module.run_decision_engine(Path(__file__).resolve().parents[1])
    print(json.dumps(result, indent=2, ensure_ascii=False))
