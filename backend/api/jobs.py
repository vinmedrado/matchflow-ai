from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.core.authz import require_permission, require_job_run_permission, tenant_scope
from backend.core.saas_auth import user_can
from backend.services.job_scheduler_service import get_job, list_jobs, run_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
DEMO_ALLOWED_JOBS = {"future_matches_pipeline", "future_features", "future_predictions", "full_decision_pipeline", "drift_monitoring", "coverage_report"}

@router.get("")
def jobs(user: dict = Depends(require_permission("view_reports"))):
    scope = tenant_scope(user)
    return list_jobs(tenant_id=None if scope["is_admin"] else scope["tenant_id"], include_global=bool(scope["is_admin"]))

@router.get("/history")
def history(user: dict = Depends(require_permission("view_reports"))):
    scope = tenant_scope(user)
    return list_jobs(tenant_id=None if scope["is_admin"] else scope["tenant_id"], include_global=bool(scope["is_admin"]))

@router.post("/run/{job_name}")
def trigger(job_name: str, user: dict = Depends(require_job_run_permission)):
    scope = tenant_scope(user)
    if scope["is_demo"] and job_name not in DEMO_ALLOWED_JOBS:
        raise HTTPException(status_code=403, detail={"code": "DEMO_JOB_FORBIDDEN", "message": "Demo só pode executar jobs demo/simulation."})
    if job_name == "data_engine_sync" and not user_can(user, "run_data_engine"):
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Permissão run_data_engine exigida."})
    return run_job(job_name, tenant_id=str(scope["tenant_id"]), user_id=str(scope["user_id"]), is_demo=bool(scope["is_demo"]))

@router.get("/{job_id}")
def job_status(job_id: str, user: dict = Depends(require_permission("view_reports"))):
    scope = tenant_scope(user)
    return get_job(job_id, tenant_id=None if scope["is_admin"] else str(scope["tenant_id"]), include_global=bool(scope["is_admin"]))
