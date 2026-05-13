from fastapi.testclient import TestClient
from backend.main import app


def test_health_ready_and_status_public():
    client = TestClient(app)
    assert client.get('/health').status_code == 200
    assert client.get('/ready').status_code == 200
    assert client.get('/api/health/status').json()['ok'] is True


def test_data_engine_status_contract_public():
    client = TestClient(app)
    response = client.get('/api/data-engine/status')
    assert response.status_code in (200, 401)
    if response.status_code == 200:
        data = response.json()['data']
        assert 'status' in data
        assert 'outputs' in data
        assert 'warnings' in data
        assert 'next_steps' in data


def test_demo_status_public():
    client = TestClient(app)
    response = client.get('/api/demo/status')
    assert response.status_code == 200
    assert response.json()['data']['mode'] == 'DEMO_SAFE_PAPER_TRADING_ONLY'
