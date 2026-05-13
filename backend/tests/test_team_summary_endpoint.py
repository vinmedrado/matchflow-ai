from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.datasets import router
from backend.services import dataset_service


def test_team_summary_endpoint_with_dataset(tmp_path: Path, monkeypatch):
    data_path = tmp_path / "data/features/team_dataset.parquet"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([
        {"date": "2024-01-01", "league": "A", "team_key": "alpha", "goals_for_ft": 2},
        {"date": "2024-01-01", "league": "A", "team_key": "beta", "goals_for_ft": 1},
    ]).to_parquet(data_path, index=False)

    monkeypatch.setattr(dataset_service, "project_root", lambda: tmp_path)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/api/datasets/team-summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["file_exists"] is True
    assert payload["data"]["total_rows"] == 2
    assert payload["data"]["total_teams"] == 2


def test_team_summary_endpoint_missing_dataset(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(dataset_service, "project_root", lambda: tmp_path)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/api/datasets/team-summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["file_exists"] is False
    assert payload["data"]["total_rows"] == 0
