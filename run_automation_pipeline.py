from __future__ import annotations

from pathlib import Path

from matchflow_imports import import_from_dir


def main() -> None:
    root = Path(__file__).resolve().parent
    module = import_from_dir("matchflow_automation", root / "11_automation", "run_automation")
    result = module.run_automation(root)
    print("Automation Simulation Finished")
    print(f"Status: {result.get('status')}")
    print(f"Mode: {result.get('mode')}")
    print("Nenhuma aposta real foi executada.")


if __name__ == "__main__":
    main()
