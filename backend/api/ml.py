from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.core.logging_config import get_logger
from backend.core.authz import require_permission
from backend.services.ml_service import ml_summary

logger = get_logger("matchflow.api.ml")
router = APIRouter(prefix="/api/ml", tags=["ml"])

@router.get("/summary")
def get_ml_summary(user: dict = Depends(require_permission("view_ml"))):
    logger.info("Endpoint /api/ml/summary chamado")
    return {"ok": True, "data": ml_summary()}


from backend.services.test_lab_service import calibration_summary, ensemble_summary
@router.get("/calibration-summary")
def get_calibration_summary(user: dict = Depends(require_permission("view_ml"))): return {"ok": True, "mode": "PAPER_TRADING_SIMULATION_ONLY", "data": calibration_summary()}
@router.get("/ensemble-summary")
def get_ensemble_summary(user: dict = Depends(require_permission("view_ml"))): return {"ok": True, "mode": "PAPER_TRADING_SIMULATION_ONLY", "data": ensemble_summary()}

import json as _json
from pathlib import Path as _Path
import pandas as _pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

def _api_root() -> _Path:
    return _Path(__file__).resolve().parents[2]

@router.get('/future-predictions')
def get_future_predictions(limit: int = 200, user: dict = Depends(require_permission("view_ml"))):
    root = _api_root()
    p = root / 'data/ml/predictions/future_predictions.parquet'
    if not p.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location('future_predictor', root / '06_ml/future_predictor.py')
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        mod.generate_future_predictions(root)
    rows = []
    if p.exists():
        rows = safe_read_dataframe(p).head(limit).fillna('').to_dict(orient='records')
    summary_path = root / 'data/ml/predictions/future_predictions_summary.json'
    summary = _json.loads(summary_path.read_text(encoding='utf-8')) if summary_path.exists() else {}
    return {'ok': True, 'mode': 'PAPER_TRADING_SIMULATION_ONLY', 'summary': summary, 'data': rows}

@router.get('/calibration/report')
def get_calibration_report(user: dict = Depends(require_permission("view_ml"))):
    from backend.services.ml_calibration_service import build_calibration_report
    return {'ok': True, 'mode': 'PAPER_TRADING_SIMULATION_ONLY', 'data': build_calibration_report(_api_root())}

@router.get('/model-health')
def get_model_health(user: dict = Depends(require_permission("view_ml"))):
    from backend.services.model_health_service import build_model_health_report
    return {'ok': True, 'mode': 'PAPER_TRADING_SIMULATION_ONLY', 'data': build_model_health_report(_api_root())}

@router.post('/settled-predictions/sync')
def sync_settled_predictions_endpoint(user: dict = Depends(require_permission("run_jobs"))):
    from backend.services.ml_reliability_service import sync_settled_predictions
    return {'ok': True, 'mode': 'PAPER_TRADING_SIMULATION_ONLY', 'data': sync_settled_predictions(_api_root())}
