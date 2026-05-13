from __future__ import annotations

from pathlib import Path

from backend.core.authz import tenant_data_path
from backend.core.saas_auth import ROLE_PERMISSIONS


def _login(client, email, password):
    res = client.post('/api/auth/login', json={'email': email, 'password': password})
    assert res.status_code == 200, res.text
    return {'Authorization': f"Bearer {res.json()['access_token']}"}, res.json()['user']


def test_admin_accesses_jobs_and_system(client):
    headers, _ = _login(client, 'admin@matchflow.local', 'admin123')
    assert client.get('/api/jobs', headers=headers).status_code == 200
    assert client.get('/api/system/status', headers=headers).status_code == 200


def test_user_cannot_access_system_global(client):
    headers, _ = _login(client, 'analyst@matchflow.local', 'analyst123')
    assert client.get('/api/system/status', headers=headers).status_code == 403


def test_viewer_cannot_run_jobs(client):
    headers, _ = _login(client, 'viewer@matchflow.local', 'viewer123')
    assert client.post('/api/jobs/run/future_predictions', headers=headers).status_code == 403


def test_demo_only_runs_demo_jobs(client):
    headers, _ = _login(client, 'demo@matchflow.local', 'demo123')
    assert client.post('/api/jobs/run/data_engine_sync', headers=headers).status_code == 403


def test_data_engine_detailed_requires_auth(client):
    assert client.get('/api/data-engine/status').status_code == 401
    assert client.get('/api/data-engine/providers/flashscore/status').status_code == 401
    public = client.get('/api/data-engine/public-status')
    assert public.status_code == 200
    assert public.json()['data']['details'] == 'redacted'
    assert 'outputs' not in public.json()['data']


def test_user_job_history_is_tenant_scoped(client):
    headers, user = _login(client, 'analyst@matchflow.local', 'analyst123')
    result = client.post('/api/jobs/run/coverage_report', headers=headers)
    assert result.status_code == 200, result.text
    job = result.json()
    assert job['tenant_id'] == user['tenant_id']
    history = client.get('/api/jobs/history', headers=headers).json()
    assert all(item.get('tenant_id') == user['tenant_id'] for item in history.get('last_runs', []))


def test_tenant_path_helper_generates_isolated_path(tmp_path):
    user = {'tenant_id': 'tenant_x', 'user_id': 'user_x', 'role': 'user'}
    path = tenant_data_path(tmp_path, user, 'reports', 'a.json')
    assert path == tmp_path / 'data' / 'tenants' / 'tenant_x' / 'reports' / 'a.json'
    assert path.parent.exists()


def test_demo_permissions_are_explicit():
    assert 'run_jobs' in ROLE_PERMISSIONS['demo']
    assert 'run_data_engine' not in ROLE_PERMISSIONS['demo']
    assert 'admin_only' in ROLE_PERMISSIONS['admin']
