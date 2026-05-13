from __future__ import annotations
import json, math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe
ROOT=Path(__file__).resolve().parents[1]

def _read_parquet(path: Path) -> pd.DataFrame:
    return safe_read_dataframe(path)

def _team_key(name: str)->str:
    return ''.join(ch.lower() if ch.isalnum() else '_' for ch in str(name or '').strip()).strip('_')

def _history(root:Path)->pd.DataFrame:
    for p in [root/'data/features/team_dataset_advanced.parquet', root/'data/features/team_dataset.parquet', root/'data/processed/base_data_engine.parquet']:
        df=_read_parquet(p)
        if not df.empty: return df.copy()
    return pd.DataFrame()

def _col(df, names, default=None):
    for n in names:
        if n in df.columns: return n
    return default

def _rates(team:str, league:str, hist:pd.DataFrame) -> dict:
    if hist.empty:
        return {'sample_size':0,'goals_for_avg_last_5':1.25,'goals_against_avg_last_5':1.15,'total_goals_avg_last_5':2.4,'over_25_rate_last_5':0.5,'over_25_rate_last_10':0.5,'btts_rate_last_5':0.5,'btts_rate_last_10':0.5,'clean_sheet_rate_last_10':0.25,'recent_form_score':0.5,'warnings':['history_unavailable_demo_proxy']}
    hcol=_col(hist,['home_team','Home','home']); acol=_col(hist,['away_team','Away','away']); lcol=_col(hist,['league','League']); datecol=_col(hist,['date','Date','match_date'])
    gh=_col(hist,['Goals_H_FT','goals_home_ft','home_goals','goals_h_ft']); ga=_col(hist,['Goals_A_FT','goals_away_ft','away_goals','goals_a_ft']); total=_col(hist,['TotalGoals_FT','total_goals_ft','total_goals'])
    if not hcol or not acol:
        return {'sample_size':0,'goals_for_avg_last_5':1.25,'goals_against_avg_last_5':1.15,'total_goals_avg_last_5':2.4,'over_25_rate_last_5':0.5,'over_25_rate_last_10':0.5,'btts_rate_last_5':0.5,'btts_rate_last_10':0.5,'clean_sheet_rate_last_10':0.25,'recent_form_score':0.5,'warnings':['history_schema_insufficient']}
    d=hist.copy()
    if datecol: d[datecol]=pd.to_datetime(d[datecol], errors='coerce'); d=d.sort_values(datecol)
    mask=(d[hcol].astype(str).str.lower()==team.lower()) | (d[acol].astype(str).str.lower()==team.lower())
    if lcol and league: mask &= d[lcol].astype(str).str.lower().eq(str(league).lower()) | mask
    g=d[mask].tail(10).copy()
    if g.empty:
        return {'sample_size':0,'goals_for_avg_last_5':1.25,'goals_against_avg_last_5':1.15,'total_goals_avg_last_5':2.4,'over_25_rate_last_5':0.5,'over_25_rate_last_10':0.5,'btts_rate_last_5':0.5,'btts_rate_last_10':0.5,'clean_sheet_rate_last_10':0.25,'recent_form_score':0.5,'warnings':['team_history_low_sample']}
    gf=[]; gc=[]; totals=[]; btts=[]; cs=[]
    for _,r in g.iterrows():
        is_home=str(r.get(hcol)).lower()==team.lower()
        hg=float(r.get(gh,0) or 0) if gh else 0; ag=float(r.get(ga,0) or 0) if ga else 0
        t=float(r.get(total, hg+ag) or hg+ag) if total else hg+ag
        gf.append(hg if is_home else ag); gc.append(ag if is_home else hg); totals.append(t); btts.append(1 if hg>0 and ag>0 else 0); cs.append(1 if (ag==0 if is_home else hg==0) else 0)
    last5=slice(max(0,len(gf)-5),None)
    return {'sample_size':len(g),'goals_for_avg_last_5':sum(gf[last5])/max(1,len(gf[last5])),'goals_against_avg_last_5':sum(gc[last5])/max(1,len(gc[last5])),'total_goals_avg_last_5':sum(totals[last5])/max(1,len(totals[last5])),'over_25_rate_last_5':sum(1 for x in totals[last5] if x>2.5)/max(1,len(totals[last5])),'over_25_rate_last_10':sum(1 for x in totals if x>2.5)/max(1,len(totals)),'btts_rate_last_5':sum(btts[last5])/max(1,len(btts[last5])),'btts_rate_last_10':sum(btts)/max(1,len(btts)),'clean_sheet_rate_last_10':sum(cs)/max(1,len(cs)),'recent_form_score':min(1,max(0,(sum(gf[-3:])-sum(gc[-3:])+6)/12)),'warnings':[]}

def build_future_features(project_root:Path|None=None)->dict:
    root=Path(project_root) if project_root else ROOT
    out=root/'data/features'; out.mkdir(parents=True,exist_ok=True)
    snap=root/'data/future_matches/future_matches_snapshot.parquet'
    if not snap.exists():
        import importlib.util
        spec=importlib.util.spec_from_file_location('future_matches_pipeline', root/'07_data_ops/future_matches_pipeline.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); m.build_future_matches_snapshot(root)
    matches=_read_parquet(snap); hist=_history(root)
    try:
        from backend.services.data_engine.consolidation import filter_ml_eligible
        matches = filter_ml_eligible(matches)
    except Exception:
        pass
    rows=[]
    league_col=_col(hist,['league','League']) if not hist.empty else None
    for _,r in matches.iterrows():
        h=str(r.get('canonical_home_team_name') or r.get('home_team','')); a=str(r.get('canonical_away_team_name') or r.get('away_team','')); league=str(r.get('canonical_league_name') or r.get('league',''))
        hr=_rates(h,league,hist); ar=_rates(a,league,hist)
        league_goal_avg=float(hist[_col(hist,['TotalGoals_FT','total_goals_ft','total_goals'],None)].mean()) if not hist.empty and _col(hist,['TotalGoals_FT','total_goals_ft','total_goals'],None) else 2.45
        league_over=0.5
        if not hist.empty and _col(hist,['TotalGoals_FT','total_goals_ft','total_goals'],None):
            tc=_col(hist,['TotalGoals_FT','total_goals_ft','total_goals']); league_over=float((hist[tc]>2.5).mean())
        attack=hr['goals_for_avg_last_5']; defense_weak=ar['goals_against_avg_last_5']; ratio=attack/max(0.1, defense_weak)
        comp=sum(v is not None for v in r.to_dict().values())/max(1,len(r.to_dict()))
        warnings=list(set(hr.get('warnings',[])+ar.get('warnings',[])))
        low_sample=hr['sample_size']<5 or ar['sample_size']<5
        rows.append({**r.to_dict(), 'team_attack_strength':round(attack,4),'opponent_defense_weakness':round(defense_weak,4),'attack_vs_defense_ratio':round(ratio,4),'expected_goals_proxy':round((attack+defense_weak+league_goal_avg/2)/2.5,4),'pressure_avg_last_5':round((attack+hr['recent_form_score']*2)/3,4),'goals_for_avg_last_5':hr['goals_for_avg_last_5'],'goals_against_avg_last_5':hr['goals_against_avg_last_5'],'total_goals_avg_last_5':hr['total_goals_avg_last_5'],'over_25_rate_last_5':hr['over_25_rate_last_5'],'over_25_rate_last_10':hr['over_25_rate_last_10'],'btts_rate_last_5':hr['btts_rate_last_5'],'btts_rate_last_10':hr['btts_rate_last_10'],'clean_sheet_rate_last_10':hr['clean_sheet_rate_last_10'],'league_goal_avg':round(league_goal_avg,4),'league_over_25_rate':round(league_over,4),'home_away_factor':1.04,'recent_form_score':hr['recent_form_score'],'feature_completeness_score':round(comp,3),'data_quality_score':min(float(r.get('data_quality_score') or 0.6), round(comp,3)),'low_sample_flag':low_sample,'feature_warnings':'|'.join(warnings)})
    df=pd.DataFrame(rows)
    parquet=out/'future_features.parquet'; csv=out/'future_features.csv'; summary=out/'future_features_summary.json'
    storage_meta = safe_write_dataframe(df, parquet, index=False, also_write_csv=True)
    payload={'ok':True,'generated_at':datetime.now(timezone.utc).isoformat(),'total_rows':len(df),'low_sample_rows':int(df.get('low_sample_flag',pd.Series()).fillna(False).sum()) if not df.empty else 0,'status':'ready' if len(df) else 'no_data','outputs':{'parquet':str(parquet.relative_to(root)),'csv':str(csv.relative_to(root)),'summary':str(summary.relative_to(root))}, 'storage': storage_meta}
    summary.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
    return payload
if __name__=='__main__':
    import sys
    sys.stdout.write(json.dumps(build_future_features(),indent=2,ensure_ascii=False))
