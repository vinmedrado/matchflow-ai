from __future__ import annotations

from fastapi import APIRouter

from backend.core.logging_config import get_logger
from backend.services.quality_service import get_quality_report

logger = get_logger("matchflow.api.data_quality")
router = APIRouter(prefix="/api/data-quality", tags=["data-quality"])


@router.get("/report")
def data_quality_report() -> dict:
    logger.info("Endpoint /api/data-quality/report chamado")
    return {"ok": True, "data": get_quality_report()}
