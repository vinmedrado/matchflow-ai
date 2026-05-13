from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app

def _admin_headers_for_protected_data_engine(client):
    res = client.post("/api/auth/login", json={"email": "admin@matchflow.local", "password": "admin123"})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}

from backend.services.data_engine.providers.flashscore import load_leagues, run_flashscore_sync
from backend.services.data_engine.providers.flashscore.config import get_flashscore_config


def test_internal_mode_defaults_without_external_path(monkeypatch):
    monkeypatch.delenv("DATA_ENGINE_MODE", raising=False)
    cfg = get_flashscore_config()
    assert cfg.data_engine_mode == "internal"


def test_flashscore_internal_loads_leagues():
    payload = load_leagues(max_leagues=2, test_mode=True)
    assert payload["ok"] is True
    assert payload["total"] >= 1
    assert payload["leagues"][0]["provider"] == "flashscore"


def test_flashscore_internal_sync_outputs_and_state():
    result = run_flashscore_sync(max_leagues=2, test_mode=True)
    assert result["ok"] is True
    root = Path(__file__).resolve().parents[2]
    assert (root / "data/raw/flashscore_matches.parquet").exists()
    assert (root / "data/data_engine/state/flashscore_state.json").exists()
    assert result["internal_mode"] is True


def test_data_engine_ops_endpoints_flashscore():
    client = TestClient(app)
    for path in ["/api/data-engine/status", "/api/data-engine/providers/status", "/api/data-engine/providers/flashscore/status"]:
        resp = client.get(path, headers=_admin_headers_for_protected_data_engine(client))
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
    sync = client.post("/api/data-engine/providers/flashscore/sync", headers=_admin_headers_for_protected_data_engine(client))
    assert sync.status_code == 200
    assert sync.json()["ok"] is True
