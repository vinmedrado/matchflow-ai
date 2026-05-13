from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from backend.main import app

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_module(rel: str):
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    module_name = rel.replace('\\\\', '/').replace('/', '.').removesuffix('.py')
    return importlib.import_module(module_name)


def _auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post('/api/auth/login', json={'email': 'admin@matchflow.local', 'password': 'admin123'})
    assert response.status_code == 200
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def test_scheduler_status_is_simulation_only():
    scheduler = _load_module('11_automation/scheduler.py')
    status = scheduler.scheduler_status(PROJECT_ROOT)
    assert status['mode'] == 'PAPER_TRADING_SIMULATION_ONLY'
    assert status['interval_hours'] >= 1


def test_export_engine_exports_only_simulation_candidates(tmp_path: Path):
    decision_dir = tmp_path / 'data/decision_engine'
    decision_dir.mkdir(parents=True)
    pd.DataFrame([
        {'home_team': 'A', 'away_team': 'B', 'market': 'goals', 'decision_score': 82, 'confidence_band': 'HIGH_CONFIDENCE_SIMULATION', 'ml_probability': 0.7, 'risk_flags': '', 'why_selected': 'score alto'},
        {'home_team': 'C', 'away_team': 'D', 'market': 'corners', 'decision_score': 30, 'confidence_band': 'REJECTED', 'ml_probability': 0.4, 'risk_flags': 'LOW_SAMPLE_SIZE', 'why_selected': 'rejeitado'},
    ]).to_csv(decision_dir / 'decision_candidates.csv', index=False)
    (tmp_path / 'config').mkdir()
    (tmp_path / 'config/automation_config.json').write_text(json.dumps({'export': {'allowed_confidence_bands': ['HIGH_CONFIDENCE_SIMULATION', 'MEDIUM_CONFIDENCE_SIMULATION']}}), encoding='utf-8')

    export_engine = _load_module('11_automation/export_engine.py')
    result = export_engine.export_candidates(tmp_path)
    assert result['exported_count'] == 1
    out = pd.read_csv(tmp_path / 'data/automation/exported_candidates.csv')
    assert len(out) == 1
    assert 'stake' not in ''.join(out.columns).lower()


def test_alert_dispatcher_records_events(tmp_path: Path):
    monitoring = tmp_path / 'data/monitoring'
    monitoring.mkdir(parents=True)
    (monitoring / 'alerts.json').write_text(json.dumps({'alerts': [{'severity': 'WARNING', 'category': 'ML', 'code': 'DRIFT', 'message': 'drift detectado'}]}), encoding='utf-8')
    (tmp_path / 'config').mkdir()
    (tmp_path / 'config/automation_config.json').write_text('{}', encoding='utf-8')

    dispatcher = _load_module('11_automation/alert_dispatcher.py')
    result = dispatcher.dispatch_alerts(tmp_path)
    assert result['total_dispatched'] == 1
    assert (tmp_path / 'data/automation/alerts_dispatched.json').exists()


def test_report_generator_creates_daily_report(tmp_path: Path):
    (tmp_path / 'data/automation').mkdir(parents=True)
    csv_content = 'match,market,score,probability,risks,explanation,mode\nA vs B,goals,80,0.7,,simulado,PAPER_TRADING_SIMULATION_ONLY\n'
    (tmp_path / 'data/automation/exported_candidates.csv').write_text(csv_content, encoding='utf-8')
    generator = _load_module('11_automation/report_generator.py')
    result = generator.generate_daily_report(tmp_path)
    assert Path(result['path']).exists()
    content = Path(result['path']).read_text(encoding='utf-8')
    assert 'PAPER_TRADING_SIMULATION_ONLY' in content
    assert 'Nenhuma ação real' in content


def test_automation_endpoints_work():
    client = TestClient(app)
    headers = _auth_headers(client)
    status = client.get('/api/automation/status', headers=headers)
    assert status.status_code == 200
    assert status.json()['mode'] == 'PAPER_TRADING_SIMULATION_ONLY'

    history = client.get('/api/automation/history', headers=headers)
    assert history.status_code == 200

    report = client.get('/api/automation/report', headers=headers)
    assert report.status_code == 200


def test_no_forbidden_financial_terms_in_export_fields():
    source = (PROJECT_ROOT / '11_automation/export_engine.py').read_text(encoding='utf-8').upper()
    assert 'REAL_TRADE' not in source
    assert 'REAL_ENTRY' not in source
