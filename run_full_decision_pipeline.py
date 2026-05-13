from __future__ import annotations
import importlib.util, json, sys, traceback
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def _run(label, path, func):
    print(f'[MatchFlow] START {label}')
    
    if str(path).startswith('backend/services/data_engine/providers/flashscore/'):
        from backend.services.data_engine.providers.flashscore import run_flashscore_sync
        result = run_flashscore_sync(max_leagues=3, test_mode=True)
    else:
        spec=importlib.util.spec_from_file_location(label, ROOT/path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        result=getattr(mod, func)(ROOT)
    print(f'[MatchFlow] OK {label}: {json.dumps(result, ensure_ascii=False)[:500]}')
    return result

def main():
    summary={'ok': True, 'mode':'PAPER_TRADING_SIMULATION_ONLY', 'started_at': datetime.now(timezone.utc).isoformat(), 'steps': []}
    steps=[
        ('flashscore_internal_sync','backend/services/data_engine/providers/flashscore/incremental_sync.py','run_flashscore_sync'),
        ('future_matches_snapshot','07_data_ops/future_matches_pipeline.py','build_future_matches_snapshot'),
        ('future_feature_builder','03_features/future_feature_builder.py','build_future_features'),
        ('future_predictor','06_ml/future_predictor.py','generate_future_predictions'),
        ('settled_predictions_sync','backend/services/ml_reliability_service.py','sync_settled_predictions'),
        ('calibration_refresh','backend/services/ml_calibration_service.py','build_calibration_report'),
        ('drift_monitoring','backend/services/drift_monitoring_service.py','build_drift_report'),
        ('model_health','backend/services/model_health_service.py','build_model_health_report'),
        ('monitoring_alerts','backend/services/monitoring_alert_service.py','build_monitoring_alerts'),
        ('test_lab_candidates','08_test_lab/decision_research_engine.py','build_simulated_candidates'),
        ('decision_engine','09_decision_engine/decision_engine.py','run_decision_engine'),
    ]
    for label,path,func in steps:
        try:
            result=_run(label,path,func); summary['steps'].append({'step':label,'ok': True, 'result': result if isinstance(result, dict) else {'rows': len(result)}})
        except Exception as exc:
            traceback.print_exc(); summary['ok']=False; summary['steps'].append({'step':label,'ok':False,'error':str(exc)})
            if label in {'future_matches_snapshot','future_feature_builder'}: break
    out=ROOT/'data/reports/full_decision_pipeline_summary.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    return 0 if summary['ok'] else 1
if __name__=='__main__': raise SystemExit(main())
