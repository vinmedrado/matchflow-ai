from __future__ import annotations

import importlib.util
from pathlib import Path


def main() -> None:
    script_path = Path(__file__).resolve().parent / "05_paper_trading" / "run_paper_trading.py"
    spec = importlib.util.spec_from_file_location("matchflow_run_paper_trading", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load paper trading runner: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()


if __name__ == "__main__":
    main()
