from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

MODE = "PAPER_TRADING_SIMULATION_ONLY"
MARKETS = {"over_05","over_15","over_25","under_25","btts_yes","btts_no","home_win","draw","away_win","corners_over_85","corners_over_95"}

def project_root() -> Path:
    return Path(__file__).resolve().parents[2]

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _read_frame(path: Path) -> pd.DataFrame:
    try:
        if path.exists() or path.with_suffix(".csv").exists() or path.with_suffix(".parquet").exists():
            return safe_read_dataframe(path)
    except Exception:
        pass
    return pd.DataFrame()

def _write_frame(df: pd.DataFrame, parquet_path: Path, csv_path: Path | None=None) -> None:
    parquet_path.parent.mkdir(parents=True, exist_ok=True); safe_write_dataframe(df, parquet_path, index=False)
    if csv_path is not None: csv_path.parent.mkdir(parents=True, exist_ok=True); df.to_csv(csv_path, index=False)

def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding='utf-8')

def _safe_float(v: Any, default: float | None=None) -> float | None:
    try:
        if v is None or (isinstance(v,str) and not v.strip()): return default
        x=float(v)
        if math.isnan(x) or math.isinf(x): return default
        return x
    except Exception: return default

def _clip_prob(v: Any, default: float=0.5) -> float:
    x=_safe_float(v, default); x=default if x is None else x
    return max(0.001, min(0.999, float(x)))

def _bool_from_status(row: pd.Series) -> bool | None:
    status=str(row.get('status','')).upper()
    if status in {'WIN','WON','SETTLED_WIN'}: return True
    if status in {'LOSS','LOST','SETTLED_LOSS'}: return False
    val=row.get('is_win')
    if isinstance(val,bool): return val
    if str(val).lower() in {'true','1','yes'}: return True
    if str(val).lower() in {'false','0','no'}: return False
    return None

def normalize_market(market: Any, selection: Any=None, line: Any=None) -> str:
    m=str(market or '').lower().strip().replace(' ','_').replace('goals_','')
    s=str(selection or '').lower().strip(); line_f=_safe_float(line, None)
    if m in {'over_05','over05','o05'} or ('over' in s and line_f==0.5): return 'over_05'
    if m in {'over_15','over15','o15'} or ('over' in s and line_f==1.5): return 'over_15'
    if m in {'over_25','over25','o25','totals','goals','over_2_5'} or ('over' in s and (line_f==2.5 or line_f is None)): return 'over_25'
    if m in {'under_25','under25','u25','under_2_5'} or ('under' in s and (line_f==2.5 or line_f is None)): return 'under_25'
    if m in {'btts','btts_yes'} and (not s or 'yes' in s or 'sim' in s): return 'btts_yes'
    if m in {'btts_no'} or (m=='btts' and 'no' in s): return 'btts_no'
    if m in {'home_win','h','1'} or (m in {'1x2','h2h','match_winner'} and 'home' in s): return 'home_win'
    if m in {'draw','x'} or (m in {'1x2','h2h','match_winner'} and 'draw' in s): return 'draw'
    if m in {'away_win','a','2'} or (m in {'1x2','h2h','match_winner'} and 'away' in s): return 'away_win'
    if m in {'corners_over_85','corners_o85'} or ('corner' in m and 'over' in s and line_f==8.5): return 'corners_over_85'
    if m in {'corners_over_95','corners_o95'} or ('corner' in m and 'over' in s and (line_f==9.5 or line_f is None)): return 'corners_over_95'
    return m or 'unknown'

def actual_result_for_market(result_row: pd.Series | dict[str, Any], market: str) -> int | None:
    get=result_row.get if hasattr(result_row,'get') else dict(result_row).get
    def first_value(*names: str):
        for name in names:
            value=get(name)
            if value is not None and not (isinstance(value,float) and math.isnan(value)) and str(value)!='nan': return value
        return None
    gh=_safe_float(first_value('goals_home_ft','Goals_H_FT','home_goals'), None); ga=_safe_float(first_value('goals_away_ft','Goals_A_FT','away_goals'), None)
    if gh is None or ga is None: return None
    total=gh+ga
    if market=='over_05': return int(total>0.5)
    if market=='over_15': return int(total>1.5)
    if market=='over_25': return int(total>2.5)
    if market=='under_25': return int(total<2.5)
    if market=='btts_yes': return int(gh>0 and ga>0)
    if market=='btts_no': return int(not (gh>0 and ga>0))
    if market=='home_win': return int(gh>ga)
    if market=='draw': return int(gh==ga)
    if market=='away_win': return int(ga>gh)
    ch=_safe_float(first_value('corners_home','Corners_H_FT'), None); ca=_safe_float(first_value('corners_away','Corners_A_FT'), None)
    if market in {'corners_over_85','corners_over_95'}:
        if ch is None or ca is None: return None
        return int((ch+ca) > (8.5 if market=='corners_over_85' else 9.5))
    return None

def _prediction_lookup(preds: pd.DataFrame, key: Any, market: str) -> dict[str, Any]:
    if preds.empty: return {}
    sub=pd.DataFrame()
    if 'match_identity_key' in preds.columns: sub=preds[preds['match_identity_key'].astype(str)==str(key)]
    if sub.empty and 'match_id' in preds.columns: sub=preds[preds['match_id'].astype(str)==str(key)]
    if not sub.empty and 'market' in sub.columns:
        msub=sub[sub['market'].astype(str).str.lower().map(normalize_market)==normalize_market(market)]
        if not msub.empty: sub=msub
    return sub.iloc[0].to_dict() if not sub.empty else {}

def build_real_settled_results(root: Path | None=None) -> dict[str, Any]:
    root=Path(root) if root else project_root(); preds=_read_frame(root/'data/ml/predictions/future_predictions.parquet')
    raw=_read_frame(root/'data/raw/flashscore_matches.parquet'); raw = _read_frame(root/'data/raw/flashscore_matches.csv') if raw.empty else raw
    rows=[]
    if not raw.empty:
        status=raw.get('status', raw.get('match_status', pd.Series(dtype=str))).astype(str).str.upper()
        finished=raw[status.isin(['FINISHED','FT','AET','PEN','CLOSED'])] if len(status) else raw
        for _,r in finished.iterrows():
            if str(r.get('is_demo_data','false')).lower() in {'true','1','yes'}: continue
            key=r.get('match_identity_key') or r.get('flashscore_match_id') or r.get('match_id')
            if not key: continue
            markets=set(MARKETS)
            if not preds.empty and 'match_identity_key' in preds.columns:
                pm=preds[preds['match_identity_key'].astype(str)==str(key)]
                if not pm.empty and 'market' in pm.columns: markets=set(pm['market'].dropna().astype(str).map(normalize_market).tolist()) or markets
            for market in sorted(markets):
                actual=actual_result_for_market(r, market)
                if actual is None: continue
                p=_prediction_lookup(preds, key, market); prob=_clip_prob(p.get('calibration_adjusted_probability') or p.get('calibrated_ensemble_probability') or p.get('ensemble_probability'), 0.5)
                odds=_safe_float(p.get('odds') or r.get('odds_home') or r.get('odds_over_25'), None)
                roi=None if odds is None else (round(float(odds)-1.0,6) if int(prob>=0.5)==int(actual) else -1.0)
                rows.append({'match_identity_key':key,'match_date':r.get('match_date'),'league':r.get('league'),'home_team':r.get('home_team'),'away_team':r.get('away_team'),'market':market,'odds':odds,'predicted_probability':prob,'calibrated_probability':_clip_prob(p.get('calibrated_ensemble_probability') or prob, prob),'predicted_label':int(prob>=0.5),'actual_result':int(actual),'is_settled':True,'settlement_source':'flashscore_internal','settlement_source_type':'real','settlement_confidence':_safe_float(r.get('final_data_quality_score') or r.get('data_quality_score'),0.85),'settled_at':_now(),'realized_roi':roi,'data_quality_score':_safe_float(r.get('final_data_quality_score') or r.get('data_quality_score'),None),'provider_warnings':r.get('provider_warnings')})
    cols=['match_identity_key','match_date','league','home_team','away_team','market','odds','predicted_probability','calibrated_probability','predicted_label','actual_result','is_settled','settlement_source','settlement_source_type','settlement_confidence','settled_at','realized_roi','data_quality_score','provider_warnings']
    df=pd.DataFrame(rows); df = pd.DataFrame(columns=cols) if df.empty else df[cols]
    _write_frame(df, root/'data/results/real_settled_results.parquet', root/'data/results/real_settled_results.csv')
    summary={'ok':True,'mode':MODE,'settlement_source_type':'real','real_settled_results':int(len(df)),'markets':sorted(df['market'].dropna().unique().tolist()) if not df.empty else [],'generated_at':_now(),'output_paths':{'parquet':'data/results/real_settled_results.parquet','csv':'data/results/real_settled_results.csv'}}
    _write_json(root/'data/results/real_settled_results_summary.json', summary); return summary

def build_simulated_settled_results(root: Path | None=None) -> dict[str, Any]:
    root=Path(root) if root else project_root(); preds=_read_frame(root/'data/ml/predictions/future_predictions.parquet')
    specs={'paper':[root/'data/paper_trading/paper_signals.csv',root/'data/paper_trading/paper_results.csv'],'backtest':[root/'data/backtest/results/detailed_results.parquet',root/'04_backtest/results/detailed/detailed_results.parquet'],'demo':[root/'data/demo/demo_settled_results.csv']}
    counts={}; cols=['match_identity_key','match_date','league','home_team','away_team','market','odds','predicted_probability','calibrated_probability','predicted_label','actual_result','is_settled','settlement_source','settlement_source_type','settlement_confidence','settled_at','realized_roi','data_quality_score','provider_warnings']
    for st,paths in specs.items():
        frames=[_read_frame(p) for p in paths]; base=pd.concat([f for f in frames if not f.empty], ignore_index=True, sort=False) if any(not f.empty for f in frames) else pd.DataFrame(); rows=[]
        if not base.empty:
            if st=='paper': base=base[base.get('status', pd.Series(dtype=str)).astype(str).str.upper().isin(['WIN','LOSS','SETTLED'])]
            for idx,row in base.iterrows():
                key=row.get('match_identity_key') or row.get('match_key') or row.get('match_id') or row.get('signal_id') or f'{st}_{idx}'
                market=normalize_market(row.get('market') or row.get('strategy'), row.get('selection'), row.get('line') or row.get('point')); p=_prediction_lookup(preds,key,market)
                actual=_bool_from_status(row); actual=bool(idx%2==0) if actual is None else actual
                prob=_clip_prob(p.get('ensemble_probability') or row.get('probability') or row.get('ml_probability') or row.get('confidence'), 0.5)
                odds=_safe_float(row.get('odds') or row.get('odd') or p.get('odds'), None); stake=_safe_float(row.get('stake') or row.get('suggested_stake_amount'),1.0) or 1.0; profit=_safe_float(row.get('profit') or row.get('pnl'), None)
                if profit is None and odds is not None: profit=stake*(odds-1) if actual else -stake
                rows.append({'match_identity_key':key,'match_date':row.get('match_date') or row.get('date'),'league':row.get('league') or p.get('league'),'home_team':row.get('home_team') or p.get('home_team'),'away_team':row.get('away_team') or p.get('away_team'),'market':market,'odds':odds,'predicted_probability':prob,'calibrated_probability':_clip_prob(p.get('calibrated_ensemble_probability') or prob, prob),'predicted_label':int(prob>=0.5),'actual_result':int(bool(actual)),'is_settled':True,'settlement_source':st,'settlement_source_type':st,'settlement_confidence':0.65 if st=='backtest' else 0.5,'settled_at':row.get('settled_at') or _now(),'realized_roi':None if profit is None or not stake else round(float(profit)/float(stake),6),'data_quality_score':_safe_float(row.get('data_quality_score') or p.get('data_quality_score'),None),'provider_warnings':f'{st}_settlement_not_real_calibration_evidence'})
        df=pd.DataFrame(rows); df=pd.DataFrame(columns=cols) if df.empty else df[cols]
        _write_frame(df, root/f'data/results/{st}_settled_results.parquet', root/f'data/results/{st}_settled_results.csv'); counts[st]=int(len(df))
    _write_json(root/'data/results/settled_results_summary.json', {'ok':True,'mode':MODE,'generated_at':_now(),'source_type_breakdown':counts,'real_is_separate':True}); return {'ok':True,'mode':MODE,'source_type_breakdown':counts,'generated_at':_now()}

def build_all_settled_results(root: Path | None=None) -> dict[str, Any]:
    root=Path(root) if root else project_root(); real=build_real_settled_results(root); sim=build_simulated_settled_results(root); return {'ok':True,'mode':MODE,'real':real,'simulated':sim,'generated_at':_now()}

def load_real_settled_results(root: Path | None=None) -> pd.DataFrame:
    root=Path(root) if root else project_root(); p=root/'data/results/real_settled_results.parquet'
    if not p.exists(): build_real_settled_results(root)
    return _read_frame(p)

def settled_summary(root: Path | None=None) -> dict[str, Any]:
    root=Path(root) if root else project_root(); build_all_settled_results(root); breakdown={}; markets=[]
    for st in ['real','paper','backtest','demo']:
        df=_read_frame(root/f'data/results/{st}_settled_results.parquet'); breakdown[st]=int(len(df))
        if st=='real' and not df.empty: markets=sorted(df.get('market',pd.Series(dtype=str)).dropna().astype(str).unique().tolist())
    return {'ok':True,'mode':MODE,'source_type_breakdown':breakdown,'real_markets':markets,'generated_at':_now(),'real_calibration_eligible':breakdown.get('real',0)>0}
