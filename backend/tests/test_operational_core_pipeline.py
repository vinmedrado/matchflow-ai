from __future__ import annotations
import importlib.util
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

def _load(path, name):
    spec=importlib.util.spec_from_file_location(name, ROOT/path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def test_future_core_pipeline_outputs_and_no_fixed_probability():
    _load('07_data_ops/future_matches_pipeline.py','future_matches').build_future_matches_snapshot(ROOT)
    _load('03_features/future_feature_builder.py','future_features').build_future_features(ROOT)
    _load('06_ml/future_predictor.py','future_predictor').generate_future_predictions(ROOT)
    pred=pd.read_parquet(ROOT/'data/ml/predictions/future_predictions.parquet')
    assert {'random_forest_probability','lightgbm_probability','xgboost_probability','ensemble_probability','model_agreement_score','confidence_score'} <= set(pred.columns)
    assert not (pred['ensemble_probability'].round(2) == 0.61).all()
    assert pred['ensemble_probability'].between(0,1).all()

def test_test_lab_and_decision_candidates_are_connected_and_clean():
    rows=_load('08_test_lab/decision_research_engine.py','tl').build_simulated_candidates(ROOT)
    assert rows and all(r['mode']=='PAPER_TRADING_SIMULATION_ONLY' for r in rows)
    summary=_load('09_decision_engine/decision_engine.py','de').run_decision_engine(ROOT)
    assert summary['app_mode']=='PAPER_TRADING_SIMULATION_ONLY'
    assert 'Nenhuma ação real' in summary['manual_confirmation_message']
    csv_path = ROOT/'data/decision_engine/decision_candidates.csv'
    csv=csv_path.read_text(encoding='utf-8').upper()
    assert 'VALUE BET' not in csv
    csv_df = pd.read_csv(csv_path)
    assert {'suggested_allocation_pct','suggested_allocation_amount','suggested_stake_pct','suggested_stake_amount'} <= set(csv_df.columns)
    assert csv_df['suggested_stake_pct'].equals(csv_df['suggested_allocation_pct'])
    assert csv_df['suggested_stake_amount'].equals(csv_df['suggested_allocation_amount'])
    parquet=pd.read_parquet(ROOT/'data/decision_engine/decision_candidates.parquet')
    assert 'suggested_stake_amount' in parquet.columns
