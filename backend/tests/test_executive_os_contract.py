from backend.services.executive_os.engine import build_executive_workspace


def test_executive_workspace_contract():
    data = build_executive_workspace()
    assert data["ok"] is True
    assert data["executive_cognition"]["executive_action"]
    assert data["cognitive_hierarchy"]["decision_layer"] in {"reactive", "tactical", "strategic", "executive", "meta"}
    assert len(data["long_horizon_strategy"]["roadmap"]) == 5
    assert "governance_block_count" in data["executive_observability"]
    assert "cognitive_health_score" in data["cognitive_digital_twin"]


def test_executive_api_workspace(client, auth_headers):
    r = client.get("/api/executive/workspace", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["decision_board"]["final_executive_decision"]["executive_action"]
    assert isinstance(data["reflection_cycles"]["reflections"], list)
    assert isinstance(data["experimentation"]["experiments"], list)


def test_executive_governance_safe_contract(client, auth_headers):
    r = client.get("/api/executive/governance", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "safe_mode" in data["governance"]
    assert "limitations" in data["digital_twin"]


def test_executive_ask_contract(client, auth_headers):
    r = client.post("/api/executive/ask", headers=auth_headers, json={"question": "explique governance e safe mode"})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["mode"] == "executive_structured_reasoning"
    assert "Governance" in data["answer"]
