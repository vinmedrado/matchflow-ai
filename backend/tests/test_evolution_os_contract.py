from backend.services.evolution_os.engine import build_evolution_workspace


def test_evolution_workspace_contract():
    data = build_evolution_workspace()
    assert data["ok"] is True
    assert data["system_version"].startswith("1.1.0")
    assert "recursive_improvement_score" in data["evolution_observability"]
    assert data["performance_guards"]["self_modifies_code"] is False
    assert data["self_preservation"]["mode"]["mode"] in {"normal_mode", "safe_mode", "defensive_mode", "degraded_mode", "low_confidence_mode", "emergency_stabilization_mode"}
    assert isinstance(data["executive_agent_society"]["arguments"], list)


def test_evolution_api_workspace(client, auth_headers):
    r = client.get("/api/evolution/workspace", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "meta_learning" in data
    assert "cognitive_economy" in data
    assert "continual_strategic_evolution" in data


def test_evolution_self_preservation_contract(client, auth_headers):
    r = client.get("/api/evolution/self-preservation", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "self_preservation" in data
    assert "cognitive_economy" in data
    assert "overload_risk_score" in data["cognitive_economy"]["pressure"]


def test_evolution_ask_contract(client, auth_headers):
    r = client.post("/api/evolution/ask", headers=auth_headers, json={"question": "explique safe mode e autopreservação"})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["mode"] == "self_evolving_structured_reasoning"
    assert "Self-preservation" in data["answer"]
