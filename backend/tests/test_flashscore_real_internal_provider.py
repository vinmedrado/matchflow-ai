from pathlib import Path
from fastapi.testclient import TestClient
import pandas as pd

from backend.main import app

def _admin_headers_for_protected_data_engine(client):
    res = client.post("/api/auth/login", json={"email": "admin@matchflow.local", "password": "admin123"})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}

from backend.services.data_engine.providers.flashscore import run_flashscore_sync
from backend.services.data_engine.providers.flashscore.config import get_flashscore_config


def test_internal_real_mode_is_default_and_external_path_not_required(monkeypatch):
    monkeypatch.delenv("DATA_ENGINE_MODE", raising=False)
    monkeypatch.delenv("FLASHSCORE_USE_DEMO", raising=False)
    cfg = get_flashscore_config()
    assert cfg.data_engine_mode == "internal"
    assert cfg.use_demo is False
    assert cfg.real_provider_enabled is True


def test_demo_only_runs_when_explicitly_enabled(monkeypatch):
    monkeypatch.setenv("DATA_ENGINE_MODE", "internal")
    monkeypatch.setenv("FLASHSCORE_USE_DEMO", "true")
    result = run_flashscore_sync(max_leagues=1, test_mode=True)
    assert result["ok"] is True
    assert result["demo_enabled"] is True
    root = Path(__file__).resolve().parents[2]
    df = pd.read_parquet(root / "data/raw/flashscore_matches.parquet")
    assert "is_demo_data" in df.columns
    assert df["is_demo_data"].astype(str).str.lower().isin({"true", "1"}).any()
    assert df["source"].eq("demo").any()
    assert df["provider_warnings"].astype(str).str.contains("demo fallback", case=False).any()


def test_internal_real_mode_does_not_silently_demo_when_browser_unavailable(monkeypatch):
    monkeypatch.setenv("DATA_ENGINE_MODE", "internal")
    monkeypatch.setenv("FLASHSCORE_USE_DEMO", "false")
    result = run_flashscore_sync(max_leagues=1, test_mode=True)
    assert result["ok"] is True
    assert result["real_provider_enabled"] is True
    assert result["demo_enabled"] is False
    assert result["is_using_external_repo"] is False
    joined = " ".join(result.get("warnings", []))
    assert "demo fallback" not in joined.lower() or "disabled" in joined.lower()


def test_state_output_and_mapping_columns_exist(monkeypatch):
    monkeypatch.setenv("DATA_ENGINE_MODE", "demo")
    result = run_flashscore_sync(max_leagues=1, test_mode=True)
    root = Path(__file__).resolve().parents[2]
    assert (root / "data/data_engine/state/flashscore_state.json").exists()
    path = root / "data/raw/flashscore_matches.parquet"
    assert path.exists()
    df = pd.read_parquet(path)
    required = {"match_identity_key", "canonical_home_team_id", "canonical_away_team_id", "canonical_league_id", "data_quality_score"}
    assert required.issubset(df.columns)


def test_data_engine_flashscore_endpoints(monkeypatch):
    monkeypatch.setenv("DATA_ENGINE_MODE", "internal")
    monkeypatch.setenv("FLASHSCORE_USE_DEMO", "false")
    client = TestClient(app)
    for path in [
        "/api/data-engine/status",
        "/api/data-engine/providers/status",
        "/api/data-engine/providers/flashscore/status",
        "/api/data-engine/providers/flashscore/report",
    ]:
        resp = client.get(path, headers=_admin_headers_for_protected_data_engine(client))
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["ok"] is True
    sync = client.post("/api/data-engine/providers/flashscore/sync", headers=_admin_headers_for_protected_data_engine(client))
    assert sync.status_code == 200
    assert sync.json()["data"]["is_using_external_repo"] is False
