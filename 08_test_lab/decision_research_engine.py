from __future__ import annotations
from pathlib import Path
import json, math
import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe
MODE='PAPER_TRADING_SIMULATION_ONLY'
ALLOWED={'SIMULATION_CANDIDATE','WATCH_ONLY','REJECTED'}
FORBIDDEN={'BET','APOSTAR','REAL_ENTRY','STAKE_NOW','REAL_TRADE'}

def read_future(root:Path):
    pred=root/'data/ml/predictions/future_predictions.parquet'
    if pred.exists():
        try: return safe_read_dataframe(pred).to_dict(orient='records')
        except Exception: pass
    rows=[]
    for p in (root/'jogos_futuros').glob('*.jsonl'):
        for line in p.read_text(encoding='utf-8').splitlines():
            if line.strip(): rows.append(json.loads(line))
    return rows

def _safe_float(v, default=0.0):
    try:
        if v is None or str(v).strip()=='' or str(v).lower()=='nan': return default
        return float(v)
    except Exception: return default

def _ev(prob, odds):
    odds=_safe_float(odds,0); prob=_safe_float(prob,0)
    return round(prob*odds-1,6) if odds>1 else None

def build_simulated_candidates(root:Path,max_candidates:int=50):
    rows=[]; source=read_future(root)
    if not source:
        # Generate upstream predictions if missing.
        import importlib.util
        spec=importlib.util.spec_from_file_location('future_predictor', root/'06_ml/future_predictor.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); m.generate_future_predictions(root)
        source=read_future(root)
    for g in source[:max_candidates]:
        p=_safe_float(g.get('ensemble_probability') or g.get('ml_probability'),0.0)
        odds=_safe_float(g.get('odds') or g.get('odds_over_25') or g.get('odds_btts_yes') or g.get('odds_goals'),0.0)
        risk=[]
        if _safe_float(g.get('data_quality_score'),0.0)<0.6: risk.append('LOW_DATA_QUALITY')
        if 'LOW_SAMPLE' in str(g.get('model_warnings','')): risk.append('LOW_SAMPLE_SIZE')
        ev=_ev(p,odds)
        rec='SIMULATION_CANDIDATE' if p>=0.54 and (ev is None or ev>-0.05) else 'WATCH_ONLY'
        rows.append({'match_id':g.get('match_id'),'match_identity_key':g.get('match_identity_key'),'canonical_league_id':g.get('canonical_league_id'),'canonical_home_team_id':g.get('canonical_home_team_id'),'canonical_away_team_id':g.get('canonical_away_team_id'),'date':g.get('match_date') or g.get('date'),'league':g.get('league'),'home_team':g.get('home_team'),'away_team':g.get('away_team'),'market':g.get('market','goals_over_25'),'strategy':'ML_ENSEMBLE_REFINED_RESEARCH','rule_status':'KEEP' if rec=='SIMULATION_CANDIDATE' else 'WATCH','ml_probability':p,'ensemble_probability':p,'random_forest_probability':g.get('random_forest_probability'),'lightgbm_probability':g.get('lightgbm_probability'),'xgboost_probability':g.get('xgboost_probability'),'model_agreement_score':g.get('model_agreement_score'),'odds':odds,'true_ev':ev,'backtest_roi':g.get('backtest_roi',0.0),'backtest_winrate':g.get('backtest_winrate',0.0),'sample_size':g.get('sample_size',0),'data_quality_score':g.get('data_quality_score'),'data_quality_band':g.get('data_quality_band'),'risk_flags':' | '.join(risk),'confidence_band':'MEDIUM_CONFIDENCE_SIMULATION' if p>=0.58 else 'WATCH_ONLY','recommendation_type':rec,'paper_trading_mode':MODE,'mode':MODE,'explanation':'Candidate generated from future_predictions ensemble; manual confirmation required; simulation only.'})
    validate_candidates(rows)
    out=root/'data/test_lab'; out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(out/'simulated_candidates.csv',index=False)
    (out/'test_lab_report.json').write_text(json.dumps({'ok':True,'mode':MODE,'total_candidates':len(rows),'source':'data/ml/predictions/future_predictions.parquet','fixed_probability_removed':True},indent=2),encoding='utf-8')
    return rows

def validate_candidates(rows):
    for r in rows:
        if r.get('recommendation_type') not in ALLOWED: raise ValueError('invalid recommendation_type')
        text=' '.join(map(str,r.values())).upper()
        for term in FORBIDDEN:
            if term in text: raise ValueError(f'Forbidden operational term found: {term}')
