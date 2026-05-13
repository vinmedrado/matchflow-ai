from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from pipeline_orchestrator import run_data_ops_pipeline  # type: ignore
else:
    from .pipeline_orchestrator import run_data_ops_pipeline

try:
    from backend.core.logging_config import configure_logging
except Exception:  # pragma: no cover - fallback para execução isolada
    def configure_logging() -> None:
        logging.basicConfig(
            level=logging.INFO,
            format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

logger = logging.getLogger("matchflow.data_ops.run_data_ops")


def run_data_ops(root: Path | str | None = None) -> dict[str, Any]:
    """
    Entrypoint estável para automação externa.

    Mantém compatibilidade com:
    - python 07_data_ops/run_data_ops.py
    - import dinâmico pelo 11_automation/job_runner.py
    - execução em Windows, sem depender de package install.
    """
    configure_logging()
    previous_cwd = Path.cwd()
    target_root = Path(root).resolve() if root is not None else previous_cwd
    try:
        if target_root.exists():
            os.chdir(target_root)
        logger.info("Iniciando Data Ops via entrypoint run_data_ops. root=%s", target_root)
        report = run_data_ops_pipeline()
        status = report.get("final_status")
        engine_status = report.get("check", {}).get("engine", {}).get("engine_status")
        future_status = report.get("future_games_snapshot", {}).get("status")
        result = {
            "ok": status in {"READY", "PARTIAL_READY"},
            "status": status,
            "engine_status": engine_status,
            "future_games_status": future_status,
            "report": "data/ops/incremental_run_report.json",
        }
        logger.info("Data Ops finalizado. status=%s engine_status=%s future_games_status=%s", status, engine_status, future_status)
        return result
    finally:
        os.chdir(previous_cwd)


def main() -> dict[str, Any]:
    result = run_data_ops(Path.cwd())
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


if __name__ == "__main__":
    output = main()
    raise SystemExit(0 if output.get("status") in {"READY", "PARTIAL_READY"} else 2)
