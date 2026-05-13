from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from backend.main import app

MODE = "PAPER_TRADING_SIMULATION_ONLY"
FORBIDDEN = ["VALUE BET", "APOSTAR", "REAL_TRADE"]


def root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_module(rel: str, name: str):
    path = root() / rel
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def auth_headers():
    client = TestClient(app)
    response = client.post('/api/auth/login', json={'email':'admin@matchflow.local','password':'admin123'})
    assert response.status_code == 200
    token = response.json()['access_token']
    return {'Authorization': f'Bearer {token}'}


def test_score_between_zero_and_100_and_risks_reduce():
    module = load_module('09_decision_engine/decision_score.py', 'decision_score_test')
    clean = module.calculate_decision_score({'rule_status':'KEEP','ml_probability':0.75,'ensemble_probability':0.75,'consistency_score':80,'sample_size':150})
    risky = module.calculate_decision_score({'rule_status':'KEEP','ml_probability':0.75,'ensemble_probability':0.75,'consistency_score':80,'sample_size':150,'risk_flags':'HIGH_DRAWDOWN,UNSTABLE_ROI'})
    assert 0 <= clean['decision_score'] <= 100
    assert 0 <= risky['decision_score'] <= 100
    assert risky['decision_score'] < clean['decision_score']


def test_low_sample_never_high_confidence():
    module = load_module('09_decision_engine/decision_score.py', 'decision_score_low_sample')
    result = module.calculate_decision_score({'rule_status':'KEEP','ml_probability':0.99,'ensemble_probability':0.99,'consistency_score':100,'sample_size':5,'risk_flags':'LOW_SAMPLE_SIZE'})
    assert result['decision_score'] < 80
    assert result['confidence_band'] != 'HIGH_CONFIDENCE_SIMULATION'


def test_engine_outputs_are_generated_and_clean():
    module = load_module('09_decision_engine/decision_engine.py', 'decision_engine_test')
    summary = module.run_decision_engine(root())
    assert summary['mode'] == MODE
    out = root() / 'data/decision_engine/decision_candidates.csv'
    assert out.exists()
    text = out.read_text(encoding='utf-8').upper()
    for term in FORBIDDEN:
        assert term not in text
    df = pd.read_csv(out)
    assert 'decision_score' in df.columns
    assert 'confidence_band' in df.columns
    assert 'suggested_allocation_pct' in df.columns
    assert 'suggested_allocation_amount' in df.columns
    assert 'suggested_stake_pct' in df.columns
    assert 'suggested_stake_amount' in df.columns
    assert df['suggested_stake_pct'].equals(df['suggested_allocation_pct'])
    assert df['suggested_stake_amount'].equals(df['suggested_allocation_amount'])
    assert df['decision_score'].between(0, 100).all()


def test_decision_engine_endpoint_works():
    client = TestClient(app)
    headers = auth_headers()
    run = client.post('/api/decision-engine/run', headers=headers)
    assert run.status_code == 200
    assert run.json()['mode'] == MODE
    summary = client.get('/api/decision-engine/summary', headers=headers)
    assert summary.status_code == 200
    payload = summary.json()
    assert payload['mode'] == MODE
    assert 'total_candidates' in payload['data']
    candidates = client.get('/api/decision-engine/candidates', headers=headers)
    assert candidates.status_code == 200
    payload = candidates.json()
    assert payload['mode'] == MODE
    rows = payload['data']['candidates']
    if rows:
        first = rows[0]
        assert 'suggested_allocation_pct' in first
        assert 'suggested_allocation_amount' in first
        assert 'suggested_stake_pct' in first
        assert 'suggested_stake_amount' in first
        assert first['suggested_stake_pct'] == first['suggested_allocation_pct']
        assert first['suggested_stake_amount'] == first['suggested_allocation_amount']


def test_rejected_candidates_are_never_actionable_in_outputs():
    module = load_module('09_decision_engine/decision_engine.py', 'decision_engine_rejected_safety')
    df = pd.DataFrame([
        {
            'decision_status': 'REJECTED',
            'confidence_band': 'REJECTED',
            'signal_label': 'VALUE SIGNAL',
            'suggested_stake_pct': 0.02,
            'suggested_stake_amount': 20.0,
            'suggested_allocation_pct': 0.02,
            'suggested_allocation_amount': 20.0,
            'action_required': True,
            'why_selected': '',
        },
        {
            'decision_status': 'HIGH_CONFIDENCE_SIMULATION',
            'confidence_band': 'HIGH_CONFIDENCE_SIMULATION',
            'signal_label': 'VALUE SIGNAL',
            'suggested_stake_pct': 0.01,
            'suggested_stake_amount': 10.0,
            'suggested_allocation_pct': 0.01,
            'suggested_allocation_amount': 10.0,
            'action_required': False,
        },
    ])
    fixed = module._enforce_decision_output_safety(df)
    rejected = fixed[fixed['decision_status'] == 'REJECTED'].iloc[0]
    assert rejected['suggested_stake_pct'] == 0
    assert rejected['suggested_stake_amount'] == 0
    assert rejected['suggested_allocation_pct'] == 0
    assert rejected['suggested_allocation_amount'] == 0
    assert rejected['signal_label'] in {'NO SIGNAL', 'REJECTED'}
    assert bool(rejected['action_required']) is False
    assert 'Rejected by Decision Engine safety gate' in rejected['why_selected']
    approved = fixed[fixed['decision_status'] == 'HIGH_CONFIDENCE_SIMULATION'].iloc[0]
    assert approved['signal_label'] == 'VALUE SIGNAL'
    assert approved['suggested_stake_pct'] > 0


def test_api_candidate_sanitizer_blocks_rejected_value_signal():
    service = load_module('backend/services/decision_engine_service.py', 'decision_service_rejected_safety')
    row = {
        'decision_status': 'REJECTED',
        'confidence_band': 'REJECTED',
        'signal_label': 'VALUE SIGNAL',
        'suggested_allocation_pct': 0.03,
        'suggested_allocation_amount': 30.0,
        'action_required': True,
    }
    fixed = service._sanitize_candidate_row(row)
    assert fixed['suggested_stake_pct'] == 0
    assert fixed['suggested_stake_amount'] == 0
    assert fixed['suggested_allocation_pct'] == 0
    assert fixed['suggested_allocation_amount'] == 0
    assert fixed['signal_label'] == 'NO SIGNAL'
    assert fixed['action_required'] is False
