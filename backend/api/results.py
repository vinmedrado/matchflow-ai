from __future__ import annotations
from fastapi import APIRouter, Depends
import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe
from pathlib import Path
from backend.core.authz import require_permission
from backend.services.settled_results_service import build_all_settled_results, settled_summary, project_root
router=APIRouter(prefix="/api/results", tags=["results"]); MODE="PAPER_TRADING_SIMULATION_ONLY"
def _rows(path: Path, limit: int):
    try:
        if not path.exists(): return []
        df=pd.read_csv(path) if path.suffix==".csv" else safe_read_dataframe(path); return df.head(limit).fillna("").to_dict(orient="records")
    except Exception: return []
@router.get("/settled/real")
def get_real_settled(limit:int=200, user: dict = Depends(require_permission("view_reports"))):
    root=project_root(); build_all_settled_results(root); return {"ok":True,"mode":MODE,"source_type":"real","data":_rows(root/"data/results/real_settled_results.parquet",limit)}
@router.get("/settled/summary")
def get_settled_summary(user: dict = Depends(require_permission("view_reports"))): return {"ok":True,"mode":MODE,"data":settled_summary(project_root())}
