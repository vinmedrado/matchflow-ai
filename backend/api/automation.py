"""automation.py — API de automação com APP_MODE correto."""
from __future__ import annotations
from fastapi import APIRouter
from backend.services.automation_service import automation_history, automation_report, automation_status, run_automation_service, normalized_app_mode

router = APIRouter(prefix="/api/automation", tags=["automation"])

@router.get("/status")
def status():
    data = automation_status()
    return {"ok": True, "mode": normalized_app_mode(), "data": data}

@router.post("/run")
def run():
    return {"ok": True, "mode": normalized_app_mode(), "data": run_automation_service()}

@router.get("/history")
def history():
    return {"ok": True, "mode": normalized_app_mode(), "data": automation_history()}

@router.get("/report")
def report():
    return {"ok": True, "mode": normalized_app_mode(), "data": automation_report()}
