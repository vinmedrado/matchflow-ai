from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Request, Depends

from backend.core.config import get_settings
from backend.core.logging_config import get_logger
from backend.services.dataset_service import dataset_path, get_dataset_summary
from backend.services.quality_service import report_path
from backend.services.ollama_service import OllamaService
from backend.core.storage import storage_status
from backend.core.authz import require_permission

logger = get_logger("matchflow.api.system")
router = APIRouter(prefix="/api/system", tags=["system"])


def _file_info(path: Path) -> dict:
    if not path.exists():
        logger.warning("Arquivo de status não encontrado: %s", path)
        return {"available": False, "size_mb": 0, "last_modified": None}
    stat = path.stat()
    return {
        "available": True,
        "size_mb": round(stat.st_size / (1024 * 1024), 4),
        "last_modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }


@router.get("/status")
def system_status(request: Request, user: dict = Depends(require_permission("view_system_status"))) -> dict:
    logger.info("Endpoint /api/system/status chamado")
    settings = get_settings()
    ds_summary = get_dataset_summary()
    ds_info = _file_info(dataset_path())
    qr_info = _file_info(report_path())
    ollama = OllamaService()
    uptime = None
    if hasattr(request.app.state, "started_at"):
        uptime = round((datetime.now(timezone.utc) - request.app.state.started_at).total_seconds(), 2)

    data = {
        "api_status": "online",
        "dataset_available": ds_info["available"],
        "dataset_rows": ds_summary.get("total_records", 0),
        "dataset_file_size_mb": ds_info["size_mb"],
        "dataset_last_modified": ds_info["last_modified"],
        "dataset_load_time_ms": ds_summary.get("cache", {}).get("load_time_ms", 0),
        "cache_status": ds_summary.get("cache", {}).get("cache_status", "unknown"),
        "quality_report_available": qr_info["available"],
        "quality_report_last_modified": qr_info["last_modified"],
        "ollama_available": ollama.ping(),
        "ollama_model": ollama.model,
        "app_version": settings.get("app", {}).get("version", "2.0.2"),
        "environment": settings.get("environment", "local"),
        "api_uptime": uptime,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "storage": storage_status(),
    }
    logger.info(
        "System status: dataset=%s rows=%s quality=%s ollama=%s cache=%s",
        data["dataset_available"],
        data["dataset_rows"],
        data["quality_report_available"],
        data["ollama_available"],
        data["cache_status"],
    )
    return {"ok": True, "data": data}
