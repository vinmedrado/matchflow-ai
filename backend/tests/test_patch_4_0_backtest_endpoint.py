from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


def _auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@matchflow.local", "password": "admin123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_backtest_summary_endpoint_works():
    client = TestClient(app)
    response = client.get("/api/backtest/summary", headers=_auth_headers(client))

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "data" in payload
    assert "file_exists" in payload["data"]
    assert "total_strategies" in payload["data"]
    assert "total_trades" in payload["data"]
