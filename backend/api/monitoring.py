from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.services.monitoring_service import (
    monitoring_alerts,
    monitoring_anomalies,
    monitoring_drift,
    monitoring_status,
    run_monitoring_service,
)

from backend.core.authz import require_permission

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])
MODE = "PAPER_TRADING_SIMULATION_ONLY"


@router.get("/status")
def status(user: dict = Depends(require_permission("view_monitoring"))):
    return {"ok": True, "mode": MODE, "data": monitoring_status()}


@router.get("/alerts")
def alerts(user: dict = Depends(require_permission("view_monitoring"))):
    from backend.services.monitoring_alert_service import build_monitoring_alerts
    return {"ok": True, "mode": MODE, "data": build_monitoring_alerts()}


@router.get("/drift")
def drift(user: dict = Depends(require_permission("view_monitoring"))):
    return {"ok": True, "mode": MODE, "data": monitoring_drift()}


@router.get("/anomalies")
def anomalies(user: dict = Depends(require_permission("view_monitoring"))):
    return {"ok": True, "mode": MODE, "data": monitoring_anomalies()}


@router.post("/run")
def run(user: dict = Depends(require_permission("run_jobs"))):
    return {"ok": True, "mode": MODE, "data": run_monitoring_service()}


@router.get("/evidence-alerts")
def evidence_alerts(user: dict = Depends(require_permission("view_monitoring"))):
    from backend.services.evidence_alert_service import build_evidence_alerts
    return {"ok": True, "mode": MODE, "data": build_evidence_alerts()}
