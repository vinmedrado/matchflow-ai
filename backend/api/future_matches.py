from __future__ import annotations
import json
from pathlib import Path
from fastapi import APIRouter
import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe
router = APIRouter(prefix='/api/future-matches', tags=['future-matches'])

def _root() -> Path: return Path(__file__).resolve().parents[2]

@router.get('/snapshot')
def future_matches_snapshot(limit: int = 200):
    root=_root(); p=root/'data/future_matches/future_matches_snapshot.parquet'
    if not p.exists():
        import importlib.util
        spec=importlib.util.spec_from_file_location('future_matches_pipeline', root/'07_data_ops/future_matches_pipeline.py')
        mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); mod.build_future_matches_snapshot(root)
    rows=safe_read_dataframe(p).head(limit).fillna('').to_dict(orient='records') if p.exists() else []
    sp=root/'data/future_matches/future_matches_summary.json'
    summary=json.loads(sp.read_text(encoding='utf-8')) if sp.exists() else {}
    return {'ok': True, 'mode':'PAPER_TRADING_SIMULATION_ONLY', 'summary':summary, 'data':rows}
