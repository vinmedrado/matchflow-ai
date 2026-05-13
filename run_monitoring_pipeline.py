from __future__ import annotations

import importlib.util
import logging
from pathlib import Path

from backend.core.logging_config import configure_logging

configure_logging()
logger = logging.getLogger("matchflow.run_monitoring_pipeline")


def main() -> None:
    root = Path(__file__).resolve().parent
    module_path = root / "10_monitoring" / "run_monitoring.py"
    spec = importlib.util.spec_from_file_location("matchflow_monitoring_runner", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    result = module.run_monitoring(root)
    logger.info("Monitoramento finalizado: alerts=%s status=%s", result.get("alerts", {}).get("total_alerts"), result.get("status", {}).get("overall_status"))


if __name__ == "__main__":
    main()
