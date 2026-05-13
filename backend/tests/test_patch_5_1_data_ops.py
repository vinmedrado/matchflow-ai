from __future__ import annotations

import importlib
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

engine_discovery = importlib.import_module("07_data_ops.engine_discovery")
future_discovery = importlib.import_module("07_data_ops.future_games_discovery")
future_loader = importlib.import_module("07_data_ops.future_games_loader")
data_ops_state = importlib.import_module("07_data_ops.data_ops_state")


def test_engine_discovery_uses_internal_provider():
    report = engine_discovery.discover_engine(config={}, write_report=False)
    assert report["engine_status"] == "ENGINE_READY"
    assert report["uses_external_repo"] is False
    assert report["is_using_external_repo"] is False
    assert "backend/services/data_engine/providers/flashscore" in report["engine_path"]


def test_engine_discovery_ignores_legacy_candidate_config(tmp_path):
    standalone = tmp_path / "standalone-engine"
    (standalone / "output").mkdir(parents=True)
    (standalone / "output" / "games.json").write_text("[]", encoding="utf-8")
    report = engine_discovery.discover_engine(
        config={"football_data_engine_candidates": [str(standalone)], "engine_output_candidates": ["output"]},
        write_report=False,
    )
    assert report["engine_status"] == "ENGINE_READY"
    assert report["uses_external_repo"] is False
    assert str(standalone) not in report["engine_path"]


def test_future_games_scripts_without_data(tmp_path, monkeypatch):
    future = tmp_path / "jogos_futuros"
    future.mkdir()
    (future / "scraper.py").write_text("print('script')", encoding="utf-8")
    monkeypatch.setenv("FUTURE_GAMES_PATH", str(future))
    report = future_discovery.discover_future_games({"future_games_candidates": [], "accepted_file_formats": [".json"]})
    assert report["future_games_status"] == "FUTURE_GAMES_NO_DATA_FILES"
    assert report["scripts_count"] == 1
    assert report["future_games_files_count"] == 0


def test_future_games_with_valid_data(tmp_path, monkeypatch):
    future = tmp_path / "jogos_futuros"
    future.mkdir()
    (future / "2026-05-01.jsonl").write_text('{"match_id":"1","date":"2026-05-01","league":"A","home_team":"H","away_team":"A","odds":1.8}\n', encoding="utf-8")
    monkeypatch.setenv("FUTURE_GAMES_PATH", str(future))
    report = future_discovery.discover_future_games({"future_games_candidates": [], "accepted_file_formats": [".jsonl"]})
    assert report["future_games_status"] == "FUTURE_GAMES_READY"
    snapshot_report = future_loader.load_future_games_snapshot({"future_games_candidates": [], "accepted_file_formats": [".jsonl"]})
    assert snapshot_report["rows"] >= 1


def test_state_update_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    saved = data_ops_state.save_state({"engine_status": "ENGINE_READY"}, path=path)
    loaded = data_ops_state.load_state(path=path)
    assert saved["engine_status"] == "ENGINE_READY"
    assert loaded["engine_status"] == "ENGINE_READY"


def test_data_ops_status_endpoint():
    client = TestClient(app)
    token = client.post("/api/auth/login", json={"email": "admin@matchflow.local", "password": "admin123"}).json()["access_token"]
    response = client.get("/api/data-ops/status", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "engine_status" in response.json()["data"]


def test_data_ops_discovery_endpoint():
    client = TestClient(app)
    token = client.post("/api/auth/login", json={"email": "admin@matchflow.local", "password": "admin123"}).json()["access_token"]
    response = client.get("/api/data-ops/discovery", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["ok"] is True
