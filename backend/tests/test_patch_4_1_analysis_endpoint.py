
from __future__ import annotations


def test_backtest_analysis_summary_endpoint(client, auth_headers):
    response = client.get("/api/backtest/analysis-summary", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()

    assert payload["ok"] is True
    assert "data" in payload

    data = payload["data"]
    assert data["analysis_available"] is True
    assert data["file_exists"] is True
    assert isinstance(data["top_markets"], list)
    assert isinstance(data["top_strategies"], list)
    assert "overall_roi" in data
    assert "insights" in data
    assert "Melhor mercado" in data["insights"]
