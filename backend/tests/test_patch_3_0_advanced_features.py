from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


def load_advanced_builder():
    project_root = Path(__file__).resolve().parents[2]
    module_path = project_root / "03_features" / "advanced_features_builder.py"
    spec = importlib.util.spec_from_file_location("advanced_features_builder", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sample_team_dataset() -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2024-01-01", periods=8, freq="7D")
    results_alpha = ["W", "W", "D", "L", "W", "W", "L", "D"]
    results_beta = ["L", "L", "D", "W", "L", "L", "W", "D"]

    for i, date in enumerate(dates):
        rows.append({
            "match_key": f"m{i}",
            "date": str(date.date()),
            "league": "League A",
            "season": "2024",
            "team_key": "alpha",
            "team_name": "Alpha",
            "opponent_key": "beta",
            "opponent_name": "Beta",
            "side": "home" if i % 2 == 0 else "away",
            "result_ft": results_alpha[i],
            "goals_for_ft": 1 + (i % 4),
            "goals_against_ft": i % 3,
            "total_goals_ft": 1 + (i % 4) + (i % 3),
            "shots_for": 8 + i,
            "shots_against": 7 + i,
            "shots_on_target_for": 3 + (i % 4),
            "shots_on_target_against": 2 + (i % 3),
            "corners_for": 4 + (i % 5),
            "corners_against": 3 + (i % 4),
            "shots_conversion_rate": (1 + (i % 4)) / (8 + i),
            "shots_on_target_rate": (3 + (i % 4)) / (8 + i),
        })
        rows.append({
            "match_key": f"m{i}",
            "date": str(date.date()),
            "league": "League A",
            "season": "2024",
            "team_key": "beta",
            "team_name": "Beta",
            "opponent_key": "alpha",
            "opponent_name": "Alpha",
            "side": "away" if i % 2 == 0 else "home",
            "result_ft": results_beta[i],
            "goals_for_ft": i % 3,
            "goals_against_ft": 1 + (i % 4),
            "total_goals_ft": i % 3 + 1 + (i % 4),
            "shots_for": 7 + i,
            "shots_against": 8 + i,
            "shots_on_target_for": 2 + (i % 3),
            "shots_on_target_against": 3 + (i % 4),
            "corners_for": 3 + (i % 4),
            "corners_against": 4 + (i % 5),
            "shots_conversion_rate": (i % 3) / (7 + i),
            "shots_on_target_rate": (2 + (i % 3)) / (7 + i),
        })
    return pd.DataFrame(rows)


def test_advanced_features_are_created_without_leakage(tmp_path: Path):
    module = load_advanced_builder()
    input_path = tmp_path / "data/features/team_dataset.parquet"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    sample_team_dataset().to_parquet(input_path, index=False)

    result = module.build_advanced_features(project_root=tmp_path)

    assert result.leakage_ok is True
    assert result.output_path.exists()
    assert result.report_path.exists()

    df = pd.read_parquet(result.output_path)
    required = [
        "win_streak",
        "loss_streak",
        "unbeaten_streak",
        "points_last_5",
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
    for column in required:
        assert column in df.columns

    first_rows = df.groupby("team_key", group_keys=False).head(1)
    assert first_rows["pressure_index"].isna().all()
    assert first_rows["points_last_5"].isna().all()


def test_validate_anti_leakage_fails_when_current_value_is_used():
    module = load_advanced_builder()
    df = module.prepare_base(sample_team_dataset())
    features = []
    df = module.add_pressure_features(df, features)

    # Inject leakage: current raw pressure, not previous pressure.
    df["pressure_index"] = df["pressure_raw"]

    ok, failures = module.validate_anti_leakage(df, features)
    assert ok is False
    assert any(item["feature"] == "pressure_index" for item in failures)


def test_home_away_context_uses_same_side_only():
    module = load_advanced_builder()
    df = module.prepare_base(sample_team_dataset())
    features = []
    df = module.add_home_away_context(df, features)

    alpha_home = df[(df["team_key"] == "alpha") & (df["side"] == "home")].copy()
    alpha_home = alpha_home.sort_values("date")
    if len(alpha_home) >= 2:
        second_home_idx = alpha_home.index[1]
        first_home_goals = alpha_home.iloc[0]["goals_for_ft"]
        assert df.loc[second_home_idx, "home_goals_context_last_5"] == first_home_goals
