from __future__ import annotations

__test__ = False
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from backend.core.auth import user_can
from backend.services.test_lab_service import test_lab_status, run_test_lab, test_lab_report, test_lab_candidates
router=APIRouter(prefix="/api/test-lab",tags=["test-lab"]); MODE="PAPER_TRADING_SIMULATION_ONLY"
def forbidden(message): return JSONResponse(status_code=403,content={"ok":False,"mode":MODE,"error":{"code":"FORBIDDEN","message":message}})
@router.get("/status")
def status(): return {"ok":True,"mode":MODE,"data":test_lab_status()}
@router.post("/run")
def run(request:Request):
    user=getattr(request.state,"user",None)
    if not user_can(user,"run_simulation"): return forbidden("Seu perfil local/dev não tem permissão para rodar simulações.")
    return {"ok":True,"mode":MODE,"data":run_test_lab()}
@router.get("/report")
def report(): return {"ok":True,"mode":MODE,"data":test_lab_report()}
@router.get("/candidates")
def candidates(): return {"ok":True,"mode":MODE,"data":test_lab_candidates()}
