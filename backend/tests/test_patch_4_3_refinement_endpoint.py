
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


def test_refinement_summary_endpoint_works(auth_headers):
    client = TestClient(app)
    response = client.get("/api/backtest/refinement-summary", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert "refined_candidates_top_10" in data
    assert "rejected_count" in data
    assert "markets" in data
    assert "favorable_odds_ranges" in data
    assert "high_risk_strategies" in data
