from __future__ import annotations


def test_ai_brain_snapshot_contract(client, auth_headers):
    response = client.get('/api/intelligence/brain', headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body['ok'] is True
    assert body['data_state'] in {'real_data', 'partial_data', 'no_data', 'unavailable_data'}
    for key in ['summary', 'insights', 'alerts', 'recommendations', 'analytics', 'memory', 'source_meta']:
        assert key in body
    assert isinstance(body['alerts'], list)
    assert isinstance(body['recommendations'], list)
    assert 'league_performance' in body['analytics']
    assert 'market_performance' in body['analytics']


def test_ai_brain_memory_contract(client, auth_headers):
    response = client.get('/api/intelligence/memory', headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body['ok'] is True
    assert 'profile' in body
    assert 'events' in body
    assert body['profile']['state'] in {'real_data', 'no_data'}


def test_ai_brain_ask_uses_operational_context(client, auth_headers):
    response = client.post('/api/intelligence/ask', headers=auth_headers, json={'question': 'Quais riscos aumentaram?'})
    assert response.status_code == 200
    body = response.json()
    assert body['ok'] is True
    assert body['mode'] == 'ai_brain_rules_with_operational_context'
    assert isinstance(body.get('answer'), str)
    assert 'snapshot' in body


def test_ai_brain_alerts_and_diagnostics(client, auth_headers):
    alerts = client.get('/api/intelligence/alerts', headers=auth_headers)
    diagnostics = client.get('/api/intelligence/diagnostics', headers=auth_headers)
    assert alerts.status_code == 200
    assert diagnostics.status_code == 200
    assert 'alerts' in alerts.json()
    assert 'health' in diagnostics.json()
