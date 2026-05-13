from __future__ import annotations

from fastapi import APIRouter, Query, Depends

from backend.core.authz import require_permission
from backend.services.decision_engine_service import decision_candidates, decision_summary, run_decision_engine_service

router = APIRouter(prefix="/api/decision-engine", tags=["decision-engine"])
MODE = "PAPER_TRADING_SIMULATION_ONLY"


@router.get("/summary")
def summary(user: dict = Depends(require_permission("view_decision_engine"))):
    return {"ok": True, "mode": MODE, "data": decision_summary()}


@router.get("/candidates")
def candidates(limit: int = Query(default=100, ge=1, le=500), user: dict = Depends(require_permission("view_decision_engine"))):
    return {"ok": True, "mode": MODE, "data": decision_candidates(limit=limit)}


@router.post("/run")
def run(user: dict = Depends(require_permission("run_jobs"))):
    return {"ok": True, "mode": MODE, "data": run_decision_engine_service()}
