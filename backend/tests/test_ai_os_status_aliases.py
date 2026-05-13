from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def _headers():
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@matchflow.local", "password": "admin123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_ai_os_status_aliases_are_available():
    headers = _headers()
    for route in [
        "/api/evolution/status",
        "/api/executive/status",
        "/api/cognitive/status",
        "/api/autonomous/status",
    ]:
        response = client.get(route, headers=headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["endpoint"] == route
        assert payload["canonical_endpoint"].endswith("/workspace")
