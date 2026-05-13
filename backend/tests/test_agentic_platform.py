
def test_agentic_cockpit_contract(client, auth_headers):
    r = client.get('/api/agents/cockpit', headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert 'agents' in data and len(data['agents']) >= 5
    assert 'decision' in data and 'confidence_score' in data['decision']
    assert 'auto_research' in data
    assert 'self_optimization' in data
    assert 'observability' in data


def test_agentic_decision_contract(client, auth_headers):
    r = client.get('/api/agents/decision', headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data['ok'] is True
    assert data['decision']['action']
    assert isinstance(data['consensus'], list)


def test_agentic_optimization_is_auditable(client, auth_headers):
    r = client.get('/api/agents/optimization', headers=auth_headers)
    assert r.status_code == 200
    opt = r.json()['self_optimization']
    assert opt['mode'] == 'advisory_auditable'
    assert all('requires_review' in item for item in opt['proposals'])
