from __future__ import annotations

from fastapi import APIRouter

from backend.core.logging_config import get_logger
from backend.services.dataset_service import advanced_dataset_summary, dataset_summary, team_dataset_summary

logger = get_logger("matchflow.api.datasets")
router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.get("/summary")
def get_dataset_summary():
    logger.info("Endpoint /api/datasets/summary chamado")
    return {"ok": True, "data": dataset_summary()}


@router.get("/team-summary")
def get_team_dataset_summary():
    logger.info("Endpoint /api/datasets/team-summary chamado")
    return {"ok": True, "data": team_dataset_summary()}


@router.get("/advanced-summary")
def get_advanced_dataset_summary():
    logger.info("Endpoint /api/datasets/advanced-summary chamado")
    return {"ok": True, "data": advanced_dataset_summary()}
