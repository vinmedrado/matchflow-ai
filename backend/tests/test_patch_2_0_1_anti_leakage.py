from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


def load_builder(project_root: Path):
    path = project_root / "03_features" / "team_dataset_builder.py"
    spec = importlib.util.spec_from_file_location("team_dataset_builder_patch_201", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_side_dataset(path: Path) -> None:
    rows = [
        {"event_id": "1", "date": "2024-01-01", "league": "A", "season": "2024", "home_team": "Alpha", "away_team": "Beta", "home_team_key": "alpha", "away_team_key": "beta", "Goals_H_FT": 2, "Goals_A_FT": 1, "Shots_H": 10, "Shots_A": 8, "ShotsOnTarget_H": 5, "ShotsOnTarget_A": 3, "Corners_H_FT": 6, "Corners_A_FT": 4},
        {"event_id": "2", "date": "2024-01-08", "league": "A", "season": "2024", "home_team": "Gamma", "away_team": "Alpha", "home_team_key": "gamma", "away_team_key": "alpha", "Goals_H_FT": 0, "Goals_A_FT": 3, "Shots_H": 7, "Shots_A": 12, "ShotsOnTarget_H": 2, "ShotsOnTarget_A": 6, "Corners_H_FT": 3, "Corners_A_FT": 8},
        {"event_id": "3", "date": "2024-01-15", "league": "A", "season": "2024", "home_team": "Alpha", "away_team": "Delta", "home_team_key": "alpha", "away_team_key": "delta", "Goals_H_FT": 1, "Goals_A_FT": 1, "Shots_H": 9, "Shots_A": 9, "ShotsOnTarget_H": 4, "ShotsOnTarget_A": 4, "Corners_H_FT": 5, "Corners_A_FT": 5},
        {"event_id": "4", "date": "2024-01-22", "league": "A", "season": "2024", "home_team": "Zeta", "away_team": "Alpha", "home_team_key": "zeta", "away_team_key": "alpha", "Goals_H_FT": 2, "Goals_A_FT": 2, "Shots_H": 11, "Shots_A": 6, "ShotsOnTarget_H": 5, "ShotsOnTarget_A": 2, "Corners_H_FT": 7, "Corners_A_FT": 2},
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)


def test_home_away_rolling_uses_only_previous_matches_same_side(tmp_path: Path):
    project = tmp_path
    input_path = project / "data/processed/base_data_engine.parquet"
    output_path = project / "data/features/team_dataset.parquet"
    report_path = project / "data/reports/team_dataset_quality_report.json"
    make_side_dataset(input_path)

    builder = load_builder(Path.cwd())
    builder.build_team_dataset(input_path, output_path, report_path, project_root=project)
    df = pd.read_parquet(output_path)
    alpha = df[df["team_key"] == "alpha"].sort_values("date")

    alpha_home = alpha[alpha["side"] == "home"].sort_values("date")
    assert pd.isna(alpha_home.iloc[0]["home_goals_avg_last_5"])
    assert alpha_home.iloc[1]["home_goals_avg_last_5"] == 2

    alpha_away = alpha[alpha["side"] == "away"].sort_values("date")
    assert pd.isna(alpha_away.iloc[0]["away_goals_avg_last_5"])
    assert alpha_away.iloc[1]["away_goals_avg_last_5"] == 3


def test_anti_leakage_validates_shots_corners_efficiency_and_side_features(tmp_path: Path):
    project = tmp_path
    input_path = project / "data/processed/base_data_engine.parquet"
    output_path = project / "data/features/team_dataset.parquet"
    report_path = project / "data/reports/team_dataset_quality_report.json"
    make_side_dataset(input_path)

    builder = load_builder(Path.cwd())
    builder.build_team_dataset(input_path, output_path, report_path, project_root=project)
    df = pd.read_parquet(output_path)
    features = [
        "shots_avg_last_3",
        "shots_allowed_avg_last_5",
        "shots_on_target_avg_last_10",
        "corners_avg_last_5",
        "corners_allowed_avg_last_10",
        "shots_conversion_rate_avg_last_5",
        "shots_on_target_rate_avg_last_5",
        "home_goals_avg_last_5",
        "away_corners_avg_last_5",
    ]
    validation = builder.validate_anti_leakage(df, features)
    assert validation["leakage_ok"] is True
    for feature in features:
        assert feature in validation["features_checked"]


def test_anti_leakage_fails_when_feature_uses_current_row(tmp_path: Path):
    project = tmp_path
    input_path = project / "data/processed/base_data_engine.parquet"
    output_path = project / "data/features/team_dataset.parquet"
    report_path = project / "data/reports/team_dataset_quality_report.json"
    make_side_dataset(input_path)

    builder = load_builder(Path.cwd())
    builder.build_team_dataset(input_path, output_path, report_path, project_root=project)
    df = pd.read_parquet(output_path).sort_values(["team_key", "date", "match_key", "side"]).reset_index(drop=True)
    df["shots_avg_last_3"] = df.groupby("team_key")["shots_for"].transform(lambda s: s.rolling(3, min_periods=1).mean())
    validation = builder.validate_anti_leakage(df, ["shots_avg_last_3"])
    assert validation["leakage_ok"] is False
    assert validation["failures"]
