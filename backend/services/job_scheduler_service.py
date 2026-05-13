from __future__ import annotations

import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MODE = "PAPER_TRADING_SIMULATION_ONLY"

JOBS = {
    "data_engine_sync": {"description": "Run internal FlashScore Data Engine sync"},
    "future_matches_pipeline": {"description": "Generate future matches snapshot"},
    "future_features": {"description": "Generate future features"},
    "future_predictions": {"description": "Generate calibrated future ML predictions"},
    "full_decision_pipeline": {"description": "Run complete operational decision pipeline"},
    "drift_monitoring": {"description": "Build drift report"},
    "coverage_report": {"description": "Build FlashScore coverage report"},
    "calibration_refresh": {"description": "Sync settled predictions and refresh calibration artifacts"},
    "drift_analysis": {"description": "Run statistical drift analysis"},
    "model_health_analysis": {"description": "Build model health report"},
    "settled_predictions_sync": {"description": "Create settled predictions feedback dataset"},
    "real_settled_results_sync": {"description": "Sync real settled results from canonical FlashScore outcomes"},
    "calibration_real_refresh": {"description": "Refresh source-aware real calibration artifacts"},
    "evidence_quality_check": {"description": "Build evidence-quality alerts"},
}

def project_root() -> Path:
    return Path(__file__).resolve().parents[2]

def _history_path(root: Path, tenant_id: str | None = None) -> Path:
    if tenant_id:
        p = root / "data" / "tenants" / tenant_id / "jobs" / "job_history.json"
    else:
        p = root / "data/jobs/job_history.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _lock_path(root: Path, job_name: str, tenant_id: str | None = None) -> Path:
    p = root / (f"data/tenants/{tenant_id}/jobs/locks/{job_name}.lock" if tenant_id else f"data/jobs/locks/{job_name}.lock")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _read_history(root: Path, tenant_id: str | None = None) -> list[dict[str, Any]]:
    path = _history_path(root, tenant_id)
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    except Exception:
        return []

def _write_history(root: Path, history: list[dict[str, Any]], tenant_id: str | None = None) -> None:
    _history_path(root, tenant_id).write_text(json.dumps(history[-500:], indent=2, ensure_ascii=False, default=str), encoding="utf-8")

def list_jobs(root: Path | None = None, tenant_id: str | None = None, include_global: bool = False) -> dict[str, Any]:
    root = root or project_root()
    history = _read_history(root, tenant_id)
    if include_global:
        history = _read_history(root, None) + history
    return {"ok": True, "mode": MODE, "tenant_id": tenant_id, "jobs": [{"name": k, **v} for k, v in JOBS.items()], "last_runs": history[-20:]}

def run_job(job_name: str, root: Path | None = None, tenant_id: str | None = None, user_id: str | None = None, is_demo: bool = False) -> dict[str, Any]:
    root = root or project_root()
    if job_name not in JOBS:
        return {"ok": False, "error": "unknown_job", "available_jobs": sorted(JOBS)}
    lock = _lock_path(root, job_name, tenant_id)
    if lock.exists():
        return {"ok": False, "job_name": job_name, "status": "locked", "message": "Job already running or previous lock not cleared."}
    job_id = str(uuid.uuid4())
    started = datetime.now(timezone.utc).isoformat()
    lock.write_text(json.dumps({"job_id": job_id, "started_at": started}), encoding="utf-8")
    status = "success"; output: Any = {}; error = None
    try:
        if job_name == "coverage_report":
            from backend.services.data_engine.providers.flashscore.coverage_report import build_flashscore_coverage_report
            output = build_flashscore_coverage_report(root)
        elif job_name in {"drift_monitoring", "drift_analysis"}:
            from backend.services.drift_monitoring_service import build_drift_report
            output = build_drift_report(root)
        elif job_name == "calibration_refresh":
            from backend.services.ml_calibration_service import build_calibration_report
            output = build_calibration_report(root)
        elif job_name == "model_health_analysis":
            from backend.services.model_health_service import build_model_health_report
            output = build_model_health_report(root)
        elif job_name == "settled_predictions_sync":
            from backend.services.ml_reliability_service import sync_settled_predictions
            output = sync_settled_predictions(root)
        elif job_name == "real_settled_results_sync":
            from backend.services.settled_results_service import build_all_settled_results
            output = build_all_settled_results(root)
        elif job_name == "calibration_real_refresh":
            from backend.services.ml_calibration_service import build_calibration_report
            output = build_calibration_report(root)
        elif job_name == "evidence_quality_check":
            from backend.services.evidence_alert_service import build_evidence_alerts
            output = build_evidence_alerts(root)
        elif job_name == "future_predictions":
            import importlib.util
            spec = importlib.util.spec_from_file_location("future_predictor", root / "06_ml/future_predictor.py")
            mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
            output = mod.generate_future_predictions(root)
        elif job_name == "data_engine_sync":
            from backend.services.data_engine.providers.flashscore import run_flashscore_sync
            output = run_flashscore_sync(root)
        elif job_name == "future_features":
            import importlib.util
            spec = importlib.util.spec_from_file_location("future_feature_builder", root / "03_features/future_feature_builder.py")
            mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
            output = mod.build_future_features(root)
        elif job_name in {"future_matches_pipeline", "full_decision_pipeline"}:
            script = root / "run_full_decision_pipeline.py"
            proc = subprocess.run([sys.executable, str(script)], cwd=root, text=True, capture_output=True, timeout=180)
            status = "success" if proc.returncode == 0 else "failed"
            output = {"returncode": proc.returncode, "stdout_tail": proc.stdout[-2000:], "stderr_tail": proc.stderr[-2000:]}
        else:
            output = {"ok": True, "message": "No-op safe job."}
    except Exception as exc:
        status = "failed"; error = f"{type(exc).__name__}: {exc}"
    finally:
        try: lock.unlink()
        except Exception: pass
    record = {"job_id": job_id, "job_name": job_name, "tenant_id": tenant_id, "user_id": user_id, "created_by": user_id, "is_demo": is_demo, "run_id": job_id, "status": status, "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(), "error": error, "output": output}
    hist = _read_history(root, tenant_id); hist.append(record); _write_history(root, hist, tenant_id)
    return {"ok": status == "success", **record}

def get_job(job_id: str, root: Path | None = None, tenant_id: str | None = None, include_global: bool = False) -> dict[str, Any]:
    root = root or project_root()
    history = _read_history(root, tenant_id)
    if include_global:
        history = _read_history(root, None) + history
    for rec in reversed(history):
        if rec.get("job_id") == job_id:
            return {"ok": True, "data": rec}
    return {"ok": False, "error": "job_not_found", "job_id": job_id}
