from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from backend.main import app


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ADVANCED_PATH = PROJECT_ROOT / "data" / "features" / "team_dataset_advanced.parquet"

EXPECTED_ADVANCED_COLUMNS = [
    "win_streak",
    "loss_streak",
    "unbeaten_streak",
    "points_last_5",
    "points_trend",
    "goals_std_last_5",
    "shots_std_last_5",
    "corners_std_last_5",
    "goals_vs_league_avg",
    "shots_vs_league_avg",
    "corners_vs_league_avg",
    "goals_per_shot",
    "goals_per_shot_on_target",
    "shots_on_target_ratio",
    "pressure_index",
    "pressure_avg_last_5",
    "attack_vs_defense_ratio",
    "team_attack_strength",
    "opponent_defense_weakness",
    "goal_trend",
    "expected_goals_proxy",
    "corners_trend",
    "high_corner_flag",
    "high_shots_flag",
    "low_conversion_flag",
]


def test_advanced_parquet_exists_and_is_not_empty():
    assert ADVANCED_PATH.exists(), "team_dataset_advanced.parquet must exist in the full ZIP"
    assert ADVANCED_PATH.stat().st_size > 0

    df = pd.read_parquet(ADVANCED_PATH)
    assert not df.empty
    assert len(df) > 0


def test_advanced_parquet_contains_expected_features():
    df = pd.read_parquet(ADVANCED_PATH)
    missing = [column for column in EXPECTED_ADVANCED_COLUMNS if column not in df.columns]
    assert missing == []


def test_advanced_dataset_has_consistent_identity_columns():
    df = pd.read_parquet(ADVANCED_PATH)
    for column in ["date", "league", "season", "team_key", "opponent_key", "side"]:
        assert column in df.columns
    assert set(df["side"].dropna().unique()).issubset({"home", "away"})


def test_advanced_summary_endpoint_works_with_generated_parquet(auth_headers):
    client = TestClient(app)
    response = client.get("/api/datasets/advanced-summary", headers=auth_headers)
    assert response.status_code == 200

    payload = response.json()
    assert payload["ok"] is True
    data = payload["data"]
    assert data["file_exists"] is True
    assert data["total_rows"] > 0
    assert data["features_count"] > 0
