from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def _headers():
    r = client.post('/api/auth/login', json={'email':'admin@matchflow.local','password':'admin123'})
    assert r.status_code == 200
    return {'Authorization': f"Bearer {r.json()['access_token']}"}

def test_autonomous_workspace_contract():
    r = client.get('/api/autonomous/workspace', headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert 'goals' in data and 'planning' in data and 'workflows' in data
    assert 'memory_graph' in data and 'simulations' in data
    assert 'autonomous_decision' in data
    assert data['autonomous_decision']['auditability']

def test_goal_contract_has_states():
    r = client.get('/api/autonomous/goals', headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data['objectives'], list)
    assert data['objectives']
    for obj in data['objectives']:
        assert 'status' in obj
        assert 'state' in obj
        assert 'priority' in obj

def test_autonomous_ask_contract():
    r = client.post('/api/autonomous/ask', headers=_headers(), json={'question':'Explique o plano e os objetivos atuais'})
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['router']['pipeline'] in {'planning_aware_reasoning','risk_reasoning','market_strategy_reasoning','operational_context_reasoning'}
    assert data['answer']
