from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


def load_builder(project_root: Path):
    path = project_root / "03_features" / "team_dataset_builder.py"
    spec = importlib.util.spec_from_file_location("team_dataset_builder", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    import sys
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_base_dataset(path: Path) -> None:
    df = pd.DataFrame([
        {"event_id": "1", "date": "2024-01-01", "league": "A", "season": "2024", "home_team": "Alpha", "away_team": "Beta", "home_team_key": "alpha", "away_team_key": "beta", "Goals_H_FT": 2, "Goals_A_FT": 1, "Goals_H_HT": 1, "Goals_A_HT": 0, "Shots_H": 10, "Shots_A": 8, "ShotsOnTarget_H": 5, "ShotsOnTarget_A": 3, "Corners_H_FT": 6, "Corners_A_FT": 4},
        {"event_id": "2", "date": "2024-01-08", "league": "A", "season": "2024", "home_team": "Beta", "away_team": "Alpha", "home_team_key": "beta", "away_team_key": "alpha", "Goals_H_FT": 0, "Goals_A_FT": 3, "Goals_H_HT": 0, "Goals_A_HT": 1, "Shots_H": 7, "Shots_A": 12, "ShotsOnTarget_H": 2, "ShotsOnTarget_A": 6, "Corners_H_FT": 3, "Corners_A_FT": 8},
        {"event_id": "3", "date": "2024-01-15", "league": "A", "season": "2024", "home_team": "Alpha", "away_team": "Gamma", "home_team_key": "alpha", "away_team_key": "gamma", "Goals_H_FT": 1, "Goals_A_FT": 1, "Goals_H_HT": 0, "Goals_A_HT": 1, "Shots_H": 9, "Shots_A": 9, "ShotsOnTarget_H": 4, "ShotsOnTarget_A": 4, "Corners_H_FT": 5, "Corners_A_FT": 5},
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def test_two_rows_per_match_and_no_first_history(tmp_path: Path):
    project = tmp_path
    input_path = project / "data/processed/base_data_engine.parquet"
    output_path = project / "data/features/team_dataset.parquet"
    report_path = project / "data/reports/team_dataset_quality_report.json"
    make_base_dataset(input_path)
    builder = load_builder(Path.cwd())
    result = builder.build_team_dataset(input_path, output_path, report_path, project_root=project)
    df = pd.read_parquet(output_path)
    assert result.rows_created == 6
    assert len(df) == 6
    first_rows = df.sort_values(["team_key", "date"]).groupby("team_key").head(1)
    assert first_rows["goals_for_ft_avg_last_3"].isna().all()


def test_rolling_uses_only_previous_matches(tmp_path: Path):
    project = tmp_path
    input_path = project / "data/processed/base_data_engine.parquet"
    output_path = project / "data/features/team_dataset.parquet"
    report_path = project / "data/reports/team_dataset_quality_report.json"
    make_base_dataset(input_path)
    builder = load_builder(Path.cwd())
    builder.build_team_dataset(input_path, output_path, report_path, project_root=project)
    df = pd.read_parquet(output_path).sort_values(["team_key", "date"])
    alpha = df[df["team_key"] == "alpha"].sort_values("date")
    assert pd.isna(alpha.iloc[0]["goals_for_ft_avg_last_3"])
    assert alpha.iloc[1]["goals_for_ft_avg_last_3"] == 2
    assert alpha.iloc[2]["goals_for_ft_avg_last_3"] == 2.5


def test_shots_and_corners_columns_exist(tmp_path: Path):
    project = tmp_path
    input_path = project / "data/processed/base_data_engine.parquet"
    output_path = project / "data/features/team_dataset.parquet"
    report_path = project / "data/reports/team_dataset_quality_report.json"
    make_base_dataset(input_path)
    builder = load_builder(Path.cwd())
    builder.build_team_dataset(input_path, output_path, report_path, project_root=project)
    df = pd.read_parquet(output_path)
    for col in ["shots_for", "shots_against", "corners_for", "corners_against", "shots_avg_last_3", "corners_avg_last_5"]:
        assert col in df.columns
