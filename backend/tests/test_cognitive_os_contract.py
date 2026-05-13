from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def _headers():
    r = client.post('/api/auth/login', json={'email':'admin@matchflow.local','password':'admin123'})
    assert r.status_code == 200
    return {'Authorization': f"Bearer {r.json()['access_token']}"}


def test_cognitive_workspace_contract():
    r = client.get('/api/cognitive/workspace', headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert 'world_model' in data
    assert 'meta_reasoning' in data
    assert 'uncertainty' in data
    assert 'knowledge_evolution' in data
    assert 'collaborative_agent_society' in data
    assert 'cognitive_decision' in data
    assert isinstance(data['cognitive_decision']['confidence_score'], (int, float))


def test_cognitive_decision_contract():
    r = client.get('/api/cognitive/decision', headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['cognitive_decision']['action']
    assert 'observability' in data


def test_cognitive_ask_contract():
    r = client.post('/api/cognitive/ask', headers=_headers(), json={'question': 'Explique a incerteza e decisão'})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['mode'] == 'cognitive_structured_reasoning'
    assert data['answer']
