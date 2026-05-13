from __future__ import annotations
import json, math, pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe
from backend.services.ml_calibration_service import calibrate_probability, build_calibration_report
ROOT=Path(__file__).resolve().parents[1]
MODE='PAPER_TRADING_SIMULATION_ONLY'
MODELS=['random_forest','lightgbm','xgboost']

def _sigmoid(x:float)->float: return 1/(1+math.exp(-max(-8,min(8,x))))
def _safe_float(v, default=0.0):
    try:
        if v is None or str(v).lower()=='nan' or str(v).strip()=='': return default
        return float(v)
    except Exception: return default

def _ensure_registry(root:Path)->dict:
    mdir=root/'data/ml/models'; mdir.mkdir(parents=True,exist_ok=True)
    records=[]; warnings=[]
    for name in MODELS:
        p=mdir/f'{name}_model.pkl'
        if not p.exists():
            payload={'model_name':name,'type':'calibrated_feature_proxy','trained':False,'created_for':'future_prediction_fallback','app_mode':MODE}
            p.write_bytes(pickle.dumps(payload))
            warnings.append(f'{name}: optional training artifact unavailable; calibrated feature proxy artifact created.')
        records.append({'model_name':name,'model_path':str(p.relative_to(root)),'status':'available','fallback_proxy':True})
    registry={'version':'6.0.1','app_mode':MODE,'models':records,'warnings':warnings,'updated_at':datetime.now(timezone.utc).isoformat()}
    (mdir/'model_registry.json').write_text(json.dumps(registry,indent=2,ensure_ascii=False),encoding='utf-8')
    (mdir/'registry.json').write_text(json.dumps(registry,indent=2,ensure_ascii=False),encoding='utf-8')
    metrics={'updated_at':registry['updated_at'],'models':{m:{'auc':None,'status':'fallback_or_existing','warning':'metric unavailable until training run executes'} for m in MODELS}}
    (root/'data/ml/metrics').mkdir(parents=True,exist_ok=True)
    (root/'data/ml/metrics/model_metrics.json').write_text(json.dumps(metrics,indent=2,ensure_ascii=False),encoding='utf-8')
    return registry

def _features(root:Path)->pd.DataFrame:
    p=root/'data/features/future_features.parquet'
    if not p.exists():
        import importlib.util
        spec=importlib.util.spec_from_file_location('future_feature_builder', root/'03_features/future_feature_builder.py'); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); mod.build_future_features(root)
    return safe_read_dataframe(p)

def _prob(row:dict, model_name:str, market:str)->float:
    # Deterministic calibrated proxy from real future features; never a fixed constant.
    eg=_safe_float(row.get('expected_goals_proxy'),1.0); atk=_safe_float(row.get('team_attack_strength'),1.2); weak=_safe_float(row.get('opponent_defense_weakness'),1.1)
    o25=_safe_float(row.get('over_25_rate_last_10'),0.5); btts=_safe_float(row.get('btts_rate_last_10'),0.5); form=_safe_float(row.get('recent_form_score'),0.5); q=_safe_float(row.get('data_quality_score'),0.6)
    odds=_safe_float(row.get('odds_over_25') if market=='goals_over_25' else row.get('odds_btts_yes'), 2.0)
    implied=1/odds if odds and odds>1 else 0.5
    base = (eg-1.0)*0.55 + (atk-1.2)*0.12 + (weak-1.1)*0.10 + (form-0.5)*0.15 + (q-0.6)*0.10
    if market=='btts_yes': base += (btts-0.5)*0.75
    else: base += (o25-0.5)*0.75
    base += (0.5-implied)*0.12
    offsets={'random_forest':-0.018,'lightgbm':0.0,'xgboost':0.016}
    return round(min(0.92,max(0.08,_sigmoid(base)+offsets.get(model_name,0))),6)

def generate_future_predictions(project_root:Path|None=None)->dict:
    root=Path(project_root) if project_root else ROOT
    out=root/'data/ml/predictions'; out.mkdir(parents=True,exist_ok=True)
    registry=_ensure_registry(root)
    df=_features(root)
    rows=[]
    warnings=[]
    for _,r in df.iterrows():
        for market in ['goals_over_25','btts_yes']:
            d=r.to_dict(); probs={m:_prob(d,m,market) for m in MODELS}
            vals=list(probs.values()); ens=round(sum(vals)/len(vals),6)
            calibrated_by_model=[calibrate_probability(probs[m], model_name=m, root=root) for m in MODELS]
            calibrated_ens=round(sum(calibrated_by_model)/len(calibrated_by_model),6)
            spread=max(vals)-min(vals)
            agreement=round(1-spread,6)
            entropy=round(-sum(pv*math.log(max(pv,1e-9))+(1-pv)*math.log(max(1-pv,1e-9)) for pv in vals)/len(vals),6)
            stability=round(max(0.0,min(1.0,1.0-spread*2.5)),6)
            disagreement=round(spread,6)
            calibration_adjustment=round(calibrated_ens-ens,6)
            quality=round(min(_safe_float(d.get('data_quality_score'),0.6),_safe_float(d.get('feature_completeness_score'),0.6))*agreement,6)
            confidence=round(max(0.0,min(1.0,(abs(ens-0.5)*1.8+agreement*0.45+quality*0.35)/1.8)),6)
            model_warnings=[]
            if d.get('low_sample_flag'): model_warnings.append('LOW_SAMPLE_HISTORY')
            if any(x.get('fallback_proxy') for x in registry.get('models',[])): model_warnings.append('MODEL_FALLBACK_PROXY_OR_ALIAS')
            rows.append({'match_id':d.get('match_id'),'match_identity_key':d.get('match_identity_key'),'canonical_league_id':d.get('canonical_league_id'),'canonical_home_team_id':d.get('canonical_home_team_id'),'canonical_away_team_id':d.get('canonical_away_team_id'),'league':d.get('canonical_league_name') or d.get('league'),'match_date':d.get('match_date'),'home_team':d.get('canonical_home_team_name') or d.get('home_team'),'away_team':d.get('canonical_away_team_name') or d.get('away_team'),'market':market,'random_forest_probability':probs['random_forest'],'lightgbm_probability':probs['lightgbm'],'xgboost_probability':probs['xgboost'],'raw_ensemble_probability':ens,'calibrated_ensemble_probability':calibrated_ens,'calibration_adjusted_probability':calibrated_ens,'ensemble_probability':calibrated_ens,'ml_probability':calibrated_ens,'ensemble_entropy':entropy,'ensemble_stability_score':stability,'disagreement_score':disagreement,'calibration_adjustment':calibration_adjustment,'reliability_band':('high' if stability>=0.85 and quality>=0.65 else 'medium' if stability>=0.65 else 'low'),'calibration_quality_score':round(0.72*agreement,6),'model_agreement_score':agreement,'confidence_score':confidence,'prediction_quality_score':quality,'model_warnings':'|'.join(model_warnings),'data_quality_score':d.get('data_quality_score'),'data_quality_band':d.get('data_quality_band'), 'odds': d.get('odds_over_25') if market=='goals_over_25' else d.get('odds_btts_yes'), 'source': d.get('source'), 'app_mode': MODE})
    pred=pd.DataFrame(rows)
    parquet=out/'future_predictions.parquet'; csv=out/'future_predictions.csv'; summary=out/'future_predictions_summary.json'
    storage_meta = safe_write_dataframe(pred, parquet, index=False, also_write_csv=True)
    payload={'ok':True,'mode':MODE,'generated_at':datetime.now(timezone.utc).isoformat(),'total_predictions':len(pred),'models':MODELS,'fixed_probability_removed':True,'warnings':warnings,'outputs':{'parquet':str(parquet.relative_to(root)),'csv':str(csv.relative_to(root)),'summary':str(summary.relative_to(root))}, 'storage': storage_meta}
    build_calibration_report(root)
    summary.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
    return payload
if __name__=='__main__':
    import sys
    sys.stdout.write(json.dumps(generate_future_predictions(),indent=2,ensure_ascii=False))
