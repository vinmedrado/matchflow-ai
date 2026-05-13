from __future__ import annotations
import json, os, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

# Data Engine consolidation: canonical mapping, deduplication and quality scoring

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / 'data/future_matches'
OPS_OUT = ROOT / 'data/ops'

def _team_key(name: str) -> str:
    return ''.join(ch.lower() if ch.isalnum() else '_' for ch in str(name or '').strip()).strip('_')

def _safe_float(v: Any):
    try:
        if v is None or str(v).strip()=='' or str(v).lower()=='nan': return None
        return float(v)
    except Exception: return None

def _demo_rows() -> list[dict]:
    base = datetime.now(timezone.utc).date() + timedelta(days=1)
    teams=[('Premier League','Arsenal','Chelsea'),('La Liga','Barcelona','Valencia'),('Brasileiro Serie A','Palmeiras','Flamengo'),('Serie A','Inter','Roma'),('Bundesliga','Bayern Munich','Dortmund'),('Ligue 1','PSG','Lyon')]
    rows=[]
    for i,(lg,h,a) in enumerate(teams, start=1):
        q=0.72 - i*0.025
        rows.append({
            'match_id': f'demo_future_{i}', 'source':'demo/local', 'league':lg, 'season': str(base.year),
            'match_date': str(base + timedelta(days=i%4)), 'kickoff_time': f'{18+i%5:02d}:00',
            'home_team':h, 'away_team':a, 'home_team_key':_team_key(h), 'away_team_key':_team_key(a),
            'status':'SCHEDULED', 'odds_home': round(1.80+i*.07,2), 'odds_draw': round(3.20+i*.03,2), 'odds_away': round(3.80-i*.04,2),
            'odds_over_05':1.12, 'odds_under_05':6.0, 'odds_over_15':round(1.38+i*.01,2), 'odds_under_15':round(2.7-i*.02,2),
            'odds_over_25':round(1.78+i*.03,2), 'odds_under_25':round(1.95-i*.01,2), 'odds_btts_yes':round(1.75+i*.02,2), 'odds_btts_no':round(1.98-i*.01,2),
            'data_quality_score': round(q,3), 'provider_warnings':'DEMO_MODE: APIs externas não configuradas; dados fictícios marcados como demo/local.'
        })
    return rows



def _from_internal_flashscore() -> list[dict]:
    path = ROOT/'data/raw/flashscore_matches.parquet'
    if not path.exists():
        try:
            from backend.services.data_engine.providers.flashscore import run_flashscore_sync
            run_flashscore_sync(max_leagues=3, test_mode=True)
        except Exception:
            return []
    if not path.exists():
        return []
    try:
        df=safe_read_dataframe(path)
    except Exception:
        return []
    rows=[]
    for i,r in df.iterrows():
        h=str(r.get('home_team') or r.get('Home') or '')
        a=str(r.get('away_team') or r.get('Away') or '')
        if not h or not a: continue
        rows.append({
            'match_id': r.get('match_id', f'flashscore_{i}'), 'source': r.get('source','flashscore'), 'league': r.get('league','Unknown'), 'season': r.get('season',''),
            'match_date': str(r.get('match_date') or ''), 'kickoff_time': str(r.get('kickoff_time') or ''),
            'home_team': h, 'away_team': a, 'home_team_key': _team_key(h), 'away_team_key': _team_key(a), 'status': r.get('status','SCHEDULED'),
            'odds_home': _safe_float(r.get('odds_home') or r.get('Odd_H_FT')), 'odds_draw': _safe_float(r.get('odds_draw') or r.get('Odd_D_FT')), 'odds_away': _safe_float(r.get('odds_away') or r.get('Odd_A_FT')),
            'odds_over_05': _safe_float(r.get('odds_over_05')), 'odds_under_05': _safe_float(r.get('odds_under_05')),
            'odds_over_15': _safe_float(r.get('odds_over_15') or r.get('Odd_Over15_FT')), 'odds_under_15': _safe_float(r.get('odds_under_15') or r.get('Odd_Under15_FT')),
            'odds_over_25': _safe_float(r.get('odds_over_25') or r.get('Odd_Over25_FT')), 'odds_under_25': _safe_float(r.get('odds_under_25') or r.get('Odd_Under25_FT')),
            'odds_btts_yes': _safe_float(r.get('odds_btts_yes') or r.get('Odd_BTTS_Yes')), 'odds_btts_no': _safe_float(r.get('odds_btts_no') or r.get('Odd_BTTS_No')),
            'data_quality_score': _safe_float(r.get('data_quality_score')) or 0.82, 'provider_warnings': str(r.get('provider_warnings') or 'internal_flashscore_provider')
        })
    return rows

def _from_existing_ops() -> list[dict]:
    path = ROOT/'data/ops/future_games_snapshot.parquet'
    if not path.exists(): return []
    try: df=safe_read_dataframe(path)
    except Exception: return []
    rows=[]
    for i,r in df.iterrows():
        h=str(r.get('home_team') or r.get('home') or '')
        a=str(r.get('away_team') or r.get('away') or '')
        if not h or not a: continue
        date = r.get('date') or r.get('match_date') or r.get('kickoff')
        rows.append({
            'match_id': r.get('match_id', f'ops_{i}'), 'source': r.get('source','flashscore'), 'league': r.get('league','Unknown'), 'season': r.get('season',''),
            'match_date': str(pd.to_datetime(date, errors='coerce').date()) if pd.notna(pd.to_datetime(date, errors='coerce')) else '', 'kickoff_time':'',
            'home_team':h, 'away_team':a, 'home_team_key':_team_key(h), 'away_team_key':_team_key(a), 'status': r.get('status','SCHEDULED'),
            'odds_home': _safe_float(r.get('odds_home') or r.get('Odd_H_FT')), 'odds_draw': _safe_float(r.get('odds_draw') or r.get('Odd_D_FT')), 'odds_away': _safe_float(r.get('odds_away') or r.get('Odd_A_FT')),
            'odds_over_05': _safe_float(r.get('odds_over_05')), 'odds_under_05': _safe_float(r.get('odds_under_05')),
            'odds_over_15': _safe_float(r.get('odds_over_15') or r.get('Odd_Over15_FT')), 'odds_under_15': _safe_float(r.get('odds_under_15') or r.get('Odd_Under15_FT')),
            'odds_over_25': _safe_float(r.get('odds_over_25') or r.get('Odd_Over25_FT') or r.get('odds_goals')), 'odds_under_25': _safe_float(r.get('odds_under_25') or r.get('Odd_Under25_FT')),
            'odds_btts_yes': _safe_float(r.get('odds_btts_yes') or r.get('Odd_BTTS_Yes')), 'odds_btts_no': _safe_float(r.get('odds_btts_no') or r.get('Odd_BTTS_No')),
            'data_quality_score': _safe_float(r.get('data_quality_score'),) or 0.65, 'provider_warnings':'loaded_from_local_ops_snapshot'
        })
    return rows

def build_future_matches_snapshot(project_root: Path|None=None) -> dict:
    global ROOT, OUT_DIR, OPS_OUT
    if project_root:
        ROOT=Path(project_root); OUT_DIR=ROOT/'data/future_matches'; OPS_OUT=ROOT/'data/ops'
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    warnings=[]; rows=[]
    if os.getenv('DATA_ENGINE_MODE','internal').lower() != 'demo':
        rows=_from_internal_flashscore() or _from_existing_ops()
    if not rows:
        rows=_demo_rows(); warnings.append('External API keys or local future snapshot unavailable; demo/local fallback used.')
    df=pd.DataFrame(rows)
    # standardize columns
    cols=['match_id','source','league','season','match_date','kickoff_time','home_team','away_team','home_team_key','away_team_key','status','odds_home','odds_draw','odds_away','odds_over_05','odds_under_05','odds_over_15','odds_under_15','odds_over_25','odds_under_25','odds_btts_yes','odds_btts_no','data_quality_score','provider_warnings']
    for c in cols:
        if c not in df: df[c]=None
    df=df[cols]
    try:
        from backend.services.data_engine.consolidation import canonicalize_matches
        df, consolidation_report = canonicalize_matches(df, ROOT)
    except Exception as exc:
        consolidation_report = {'error': str(exc), 'status': 'canonicalization_failed'}
        warnings.append(f'Data Engine consolidation failed: {exc}')
    parquet=OUT_DIR/'future_matches_snapshot.parquet'; csv=OUT_DIR/'future_matches_snapshot.csv'; summary=OUT_DIR/'future_matches_summary.json'
    storage_meta = safe_write_dataframe(df, parquet, index=False, also_write_csv=True)
    payload={'ok':True,'generated_at':datetime.now(timezone.utc).isoformat(),'total_matches':int(len(df)),'sources':sorted(df['source'].dropna().astype(str).unique().tolist()),'status':'ready' if len(df) else 'no_data','warnings':warnings,'consolidation': consolidation_report,'outputs':{'parquet':str(parquet.relative_to(ROOT)),'csv':str(csv.relative_to(ROOT)),'summary':str(summary.relative_to(ROOT))}}
    summary.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
    return payload

if __name__=='__main__':
    sys.stdout.write(json.dumps(build_future_matches_snapshot(),indent=2,ensure_ascii=False))
