from __future__ import annotations

from fastapi import APIRouter

from backend.core.logging_config import get_logger
from backend.core.json_safe import json_safe
from backend.services.backtest_service import backtest_analysis_summary, backtest_deep_analysis_summary, backtest_refinement_summary, backtest_summary

logger = get_logger("matchflow.api.backtest")
router = APIRouter(prefix="/api/backtest", tags=["backtest"])


@router.get("/summary")
def get_backtest_summary():
    logger.info("Endpoint /api/backtest/summary chamado")
    return {"ok": True, "data": json_safe(backtest_summary())}



@router.get("/analysis-summary")
def get_backtest_analysis_summary():
    logger.info("Endpoint /api/backtest/analysis-summary chamado")
    return {"ok": True, "data": json_safe(backtest_analysis_summary())}



@router.get("/deep-analysis-summary")
def get_backtest_deep_analysis_summary():
    logger.info("Endpoint /api/backtest/deep-analysis-summary chamado")
    return {"ok": True, "data": json_safe(backtest_deep_analysis_summary())}



@router.get("/refinement-summary")
def get_backtest_refinement_summary():
    logger.info("Endpoint /api/backtest/refinement-summary chamado")
    return {"ok": True, "data": json_safe(backtest_refinement_summary())}
