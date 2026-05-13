from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

def main() -> None:
    root = Path(__file__).resolve().parent
    module_path = root / "06_ml" / "run_ml_pipeline.py"
    spec = importlib.util.spec_from_file_location("matchflow_ml_pipeline", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load ML pipeline module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["matchflow_ml_pipeline"] = module
    spec.loader.exec_module(module)
    module.run()

if __name__ == "__main__":
    main()
