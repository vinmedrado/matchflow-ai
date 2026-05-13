from __future__ import annotations


def _get(client, auth_headers, path: str):
    response = client.get(path, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "data" in body
    return body


def test_premium_copilot_contract(client, auth_headers):
    body = _get(client, auth_headers, "/api/premium/copilot")
    data = body["data"]
    assert "insights" in data
    assert "top_signals" in data
    assert "source_meta" in data
    assert body["data_state"] in {"real_data", "partial_data", "no_data", "unavailable_data"}
    for insight in data["insights"]:
        assert "state" in insight
        assert insight["state"] in {"real_data", "partial_data", "no_data", "unavailable_data", "simulated_data"}


def test_premium_live_center_contract(client, auth_headers):
    body = _get(client, auth_headers, "/api/premium/live-center")
    data = body["data"]
    for key in ["signals", "bankroll", "equity_curve", "alerts", "timeline", "source_meta"]:
        assert key in data
    assert isinstance(data["signals"], list)
    assert isinstance(data["alerts"], list)


def test_premium_explainability_contract(client, auth_headers):
    body = _get(client, auth_headers, "/api/premium/explainability")
    data = body["data"]
    for key in ["selected_signal", "feature_importance", "confidence_breakdown", "radar", "source_meta"]:
        assert key in data
    assert isinstance(data["feature_importance"], list)
    assert body["data_state"] in {"real_data", "partial_data", "no_data", "unavailable_data"}


def test_premium_paper_contract(client, auth_headers):
    body = _get(client, auth_headers, "/api/premium/paper-premium")
    data = body["data"]
    for key in ["summary", "equity_curve", "drawdown", "streaks", "risk", "source_meta"]:
        assert key in data
    assert isinstance(data["risk"], dict)
    assert "data_state" in data["risk"]


def test_premium_analytics_contract(client, auth_headers):
    body = _get(client, auth_headers, "/api/premium/analytics")
    data = body["data"]
    for key in ["league_roi", "market_roi", "hour_roi", "ev_distribution", "model_trends", "source_meta"]:
        assert key in data
        if key != "source_meta":
            assert isinstance(data[key], list)
