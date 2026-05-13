from __future__ import annotations
import json
from pathlib import Path
from fastapi import APIRouter
router=APIRouter(prefix='/api/bankroll', tags=['bankroll'])

def _root()->Path: return Path(__file__).resolve().parents[2]
@router.get('/profiles')
def bankroll_profiles():
    p=_root()/'config/bankroll_profiles.json'
    data=json.loads(p.read_text(encoding='utf-8')) if p.exists() else {'profiles':{}}
    return {'ok': True, 'mode':'PAPER_TRADING_SIMULATION_ONLY', 'data': data}
