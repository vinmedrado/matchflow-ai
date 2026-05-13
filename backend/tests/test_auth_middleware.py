from __future__ import annotations

from backend.main import app


def test_private_route_without_token_returns_401(client):
    response = client.get('/api/system/status')
    assert response.status_code == 401
    body = response.json()
    assert body['ok'] is False
    assert body['error']['code'] == 'UNAUTHORIZED'


def test_login_success(client):
    response = client.post('/api/auth/login', json={'email': 'admin@matchflow.local', 'password': 'admin123'})
    assert response.status_code == 200
    body = response.json()
    assert body['ok'] is True
    assert 'access_token' in body
    assert 'expires_at' in body


def test_login_invalid(client):
    response = client.post('/api/auth/login', json={'email': 'admin@matchflow.local', 'password': 'wrong'})
    assert response.status_code == 401
    body = response.json()
    assert body['ok'] is False
    assert body['error']['code'] == 'UNAUTHORIZED'
    assert 'message' in body['error']


def test_me_with_token(client, auth_headers):
    response = client.get('/api/auth/me', headers=auth_headers)
    assert response.status_code == 200
    assert response.json()['user']['email'] == 'admin@matchflow.local'


def test_expired_token_blocked(client):
    token = app.state.auth_manager.create_expired_token_for_tests()
    response = client.get('/api/system/status', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 401
