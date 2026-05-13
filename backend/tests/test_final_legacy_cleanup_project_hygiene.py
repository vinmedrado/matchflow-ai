from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

def _admin_headers_for_protected_data_engine(client):
    res = client.post("/api/auth/login", json={"email": "admin@matchflow.local", "password": "admin123"})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


ROOT = Path(__file__).resolve().parents[2]
BANNED_TERMS = [
    "football" + "-data" + "-engine",
    "FOOTBALL" + "_DATA" + "_ENGINE" + "_PATH",
    "../" + "football" + "-data" + "-engine",
    "external" + " data" + " engine",
    "legacy" + " bridge",
]
SCAN_DIRS = ["01_scripts", "07_data_ops", "backend", "config", "docs", "data", "README.md"]


def _iter_files():
    for rel in SCAN_DIRS:
        path = ROOT / rel
        if path.is_file():
            yield path
            continue
        if not path.exists():
            continue
        for item in path.rglob("*"):
            if item.is_file() and item.suffix.lower() in {".py", ".json", ".md", ".txt", ".env", ".example"}:
                if "__pycache__" not in item.parts and ".pytest_cache" not in item.parts:
                    yield item


def test_project_has_no_obsolete_external_engine_references():
    offenders: list[str] = []
    for path in _iter_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        if path.name == "test_final_legacy_cleanup_project_hygiene.py":
            continue
        for term in BANNED_TERMS:
            if term.lower() in text.lower():
                offenders.append(f"{path.relative_to(ROOT)}::{term}")
    assert offenders == []


def test_data_engine_statuses_are_internal_only():
    client = TestClient(app)
    for path in [
        "/api/data-engine/status",
        "/api/data-engine/providers/status",
        "/api/data-engine/providers/flashscore/status",
    ]:
        response = client.get(path, headers=_admin_headers_for_protected_data_engine(client))
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert "uses_external_repo': True" not in str(payload)
        assert "is_using_external_repo': True" not in str(payload)
