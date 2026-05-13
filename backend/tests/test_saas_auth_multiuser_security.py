from __future__ import annotations


def _login(client, email="admin@matchflow.local", password="admin123"):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def test_auth_status_reports_saas_tenant_email_verification_disabled(client):
    r = client.get("/api/auth/status")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["auth"]["mode"] == "saas"
    assert body["auth"]["tenant_isolation"] is True
    assert body["auth"]["email_verification_enabled"] is False
    assert "ADMIN" in body["auth"]["roles"]


def test_register_login_refresh_logout_profile_flow(client):
    email = "new.user.flow@matchflow.local"
    reg = client.post("/api/auth/register", json={"email": email, "password": "StrongPass123", "name": "New User"})
    assert reg.status_code in {200, 409}
    login = _login(client, email, "StrongPass123")
    assert login["user"]["tenant_id"]
    assert login["refresh_token"]
    assert login["user"]["verification_pending_optional"] is True
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    profile = client.get("/api/auth/profile", headers=headers)
    assert profile.status_code == 200
    refreshed = client.post("/api/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != login["refresh_token"]
    logout = client.post("/api/auth/logout", headers=headers, json={"logout_all": True})
    assert logout.status_code == 200
    blocked = client.get("/api/system/status", headers=headers)
    assert blocked.status_code == 401


def test_forgot_reset_password_dev_flow(client):
    email = "reset.user@matchflow.local"
    client.post("/api/auth/register", json={"email": email, "password": "OldPass123", "name": "Reset User"})
    forgot = client.post("/api/auth/forgot-password", json={"email": email})
    assert forgot.status_code == 200
    token = forgot.json().get("dev_reset_token")
    assert token
    reset = client.post("/api/auth/reset-password", json={"token": token, "new_password": "NewPass123"})
    assert reset.status_code == 200
    assert client.post("/api/auth/login", json={"email": email, "password": "OldPass123"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": email, "password": "NewPass123"}).status_code == 200


def test_roles_and_permissions_are_enforced(client):
    viewer = _login(client, "viewer@matchflow.local", "viewer123")
    assert viewer["user"]["role"] == "viewer"
    r = client.post("/api/test-lab/run", headers={"Authorization": f"Bearer {viewer['access_token']}"})
    assert r.status_code == 403
    analyst = _login(client, "analyst@matchflow.local", "analyst123")
    r2 = client.post("/api/test-lab/run", headers={"Authorization": f"Bearer {analyst['access_token']}"})
    assert r2.status_code == 200


def test_tenant_context_is_attached_to_user_payload(client):
    demo = _login(client, "demo@matchflow.local", "demo123")
    assert demo["user"]["tenant_id"] == "tenant_demo"
    assert demo["user"]["tenant"]["is_demo"] is True
    assert demo["user"]["role_key"] == "DEMO"
