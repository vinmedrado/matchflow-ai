from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from backend.core.cache import file_cache
from backend.core.config import get_settings, resolve_project_path
from backend.core.logging_config import get_logger

logger = get_logger("matchflow.quality_service")


def report_path() -> Path:
    settings = get_settings()
    return resolve_project_path(settings["data"]["quality_report_path"])


def get_quality_report() -> Dict[str, Any]:
    path = report_path()
    report, cache_meta = file_cache.get_json("quality_report", path)
    if not report:
        logger.warning("Relatório de qualidade ausente ou inválido: %s", path)
        return {
            "available": False,
            "message": "Relatório de qualidade não encontrado ou inválido.",
            "path": str(path),
            "cache": cache_meta,
        }
    report.setdefault("available", True)
    report["cache"] = cache_meta
    logger.info("Relatório de qualidade carregado: path=%s cache=%s", path, cache_meta.get("cache_status"))
    return report
