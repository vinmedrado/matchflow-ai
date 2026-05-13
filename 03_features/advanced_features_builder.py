import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

from backend.core.logging_config import configure_logging, get_logger

LOGGER = get_logger("matchflow.advanced_features_builder")

INPUT_PATH = "data/features/team_dataset.parquet"
OUTPUT_PATH = "data/features/team_dataset_advanced.parquet"
REPORT_PATH = "data/reports/advanced_features_quality.json"

REQUIRED_COLUMNS = [
    "date",
    "league",
    "season",
    "team_key",
    "team_name",
    "opponent_key",
    "opponent_name",
    "side",
]

NUMERIC_BASE_COLUMNS = [
    "goals_for_ft",
    "goals_against_ft",
    "total_goals_ft",
    "shots_for",
    "shots_against",
    "shots_on_target_for",
    "shots_on_target_against",
    "corners_for",
    "corners_against",
    "shots_conversion_rate",
    "shots_on_target_rate",
]

ADVANCED_ROLLING_MAP: Dict[str, Dict[str, Any]] = {
    "points_last_5": {"base": "points", "group": ["team_key"], "window": 5, "op": "sum"},
    "goals_std_last_5": {"base": "goals_for_ft", "group": ["team_key"], "window": 5, "op": "std"},
    "shots_std_last_5": {"base": "shots_for", "group": ["team_key"], "window": 5, "op": "std"},
    "corners_std_last_5": {"base": "corners_for", "group": ["team_key"], "window": 5, "op": "std"},
    "pressure_avg_last_5": {"base": "pressure_raw", "group": ["team_key"], "window": 5, "op": "mean"},
    "home_goals_context_last_5": {"base": "goals_for_ft", "group": ["team_key", "side"], "window": 5, "op": "mean"},
    "away_goals_context_last_5": {"base": "goals_for_ft", "group": ["team_key", "side"], "window": 5, "op": "mean"},
    "home_shots_context_last_5": {"base": "shots_for", "group": ["team_key", "side"], "window": 5, "op": "mean"},
    "away_shots_context_last_5": {"base": "shots_for", "group": ["team_key", "side"], "window": 5, "op": "mean"},
    "home_corners_context_last_5": {"base": "corners_for", "group": ["team_key", "side"], "window": 5, "op": "mean"},
    "away_corners_context_last_5": {"base": "corners_for", "group": ["team_key", "side"], "window": 5, "op": "mean"},
}



EXPECTED_ADVANCED_FEATURES = [
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
    "home_goals_context_last_5",
    "away_goals_context_last_5",
    "home_shots_context_last_5",
    "away_shots_context_last_5",
    "home_corners_context_last_5",
    "away_corners_context_last_5",
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

@dataclass
class AdvancedFeaturesBuildResult:
    input_path: Path
    output_path: Path
    report_path: Path
    rows_loaded: int
    rows_created: int
    total_features_created: int
    leakage_ok: bool
    features_created: List[str] = field(default_factory=list)
    ignored_features: List[str] = field(default_factory=list)
    execution_time_seconds: float = 0.0


def resolve_path(path: str | Path, project_root: Optional[Path] = None) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    root = project_root or Path.cwd()
    return (root / candidate).resolve()


def ensure_directories(project_root: Path) -> None:
    (project_root / "data/features").mkdir(parents=True, exist_ok=True)
    (project_root / "data/reports").mkdir(parents=True, exist_ok=True)


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    numerator = pd.to_numeric(numerator, errors="coerce")
    denominator = pd.to_numeric(denominator, errors="coerce")
    result = numerator / denominator.replace({0: np.nan})
    return result.replace([np.inf, -np.inf], np.nan)


def ensure_numeric(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    for column in columns:
        if column not in df.columns:
            LOGGER.warning("Coluna ausente no team dataset; preenchendo com NaN: %s", column)
            df[column] = np.nan
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


def validate_input(df: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Team dataset sem colunas obrigatórias: {missing}")
    if df.empty:
        raise ValueError("Team dataset está vazio.")


def prepare_base(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    validate_input(df)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    invalid_dates = int(df["date"].isna().sum())
    if invalid_dates:
        LOGGER.warning("Datas inválidas encontradas no team dataset: %s", invalid_dates)

    df = ensure_numeric(df, NUMERIC_BASE_COLUMNS)

    if "points" not in df.columns:
        if "result_ft" in df.columns:
            result_map = {"W": 3, "D": 1, "L": 0}
            df["points"] = df["result_ft"].map(result_map).astype("float")
        else:
            LOGGER.warning("Coluna result_ft ausente; points será NaN.")
            df["points"] = np.nan
    else:
        df["points"] = pd.to_numeric(df["points"], errors="coerce")

    if "win" not in df.columns:
        df["win"] = (df.get("result_ft") == "W").astype(float) if "result_ft" in df.columns else np.nan
    if "loss" not in df.columns:
        df["loss"] = (df.get("result_ft") == "L").astype(float) if "result_ft" in df.columns else np.nan
    if "draw" not in df.columns:
        df["draw"] = (df.get("result_ft") == "D").astype(float) if "result_ft" in df.columns else np.nan

    df["pressure_raw"] = pd.to_numeric(df["shots_for"], errors="coerce") + pd.to_numeric(df["corners_for"], errors="coerce")

    sort_cols = ["team_key", "date"]
    if "match_key" in df.columns:
        sort_cols.append("match_key")
    else:
        sort_cols.append("opponent_key")
    df = df.sort_values(sort_cols).reset_index(drop=True)
    return df


def rolling_past(
    df: pd.DataFrame,
    group_cols: List[str],
    value_col: str,
    window: int,
    op: str = "mean",
    min_periods: int = 1,
) -> pd.Series:
    if value_col not in df.columns:
        return pd.Series(np.nan, index=df.index)

    def transform_group(series: pd.Series) -> pd.Series:
        shifted = pd.to_numeric(series, errors="coerce").shift(1)
        rolling = shifted.rolling(window=window, min_periods=min_periods)
        if op == "mean":
            return rolling.mean()
        if op == "sum":
            return rolling.sum()
        if op == "std":
            return rolling.std(ddof=0)
        raise ValueError(f"Operação rolling não suportada: {op}")

    return df.groupby(group_cols, group_keys=False)[value_col].transform(transform_group)


def previous_streak(df: pd.DataFrame, result_value: str, *, unbeaten: bool = False) -> pd.Series:
    if "result_ft" not in df.columns:
        return pd.Series(np.nan, index=df.index)

    output = pd.Series(0, index=df.index, dtype="float")
    for _, idx in df.groupby("team_key", sort=False).groups.items():
        indexes = list(idx)
        results = df.loc[indexes, "result_ft"].astype(str).tolist()
        current_streak = 0
        values: List[int] = []
        for result in results:
            values.append(current_streak)
            if unbeaten:
                current_streak = current_streak + 1 if result in {"W", "D"} else 0
            else:
                current_streak = current_streak + 1 if result == result_value else 0
        output.loc[indexes] = values
    return output


def rolling_trend(df: pd.DataFrame, value_col: str, short_window: int = 3, long_window: int = 6) -> pd.Series:
    short = rolling_past(df, ["team_key"], value_col, short_window, "mean")
    long = rolling_past(df, ["team_key"], value_col, long_window, "mean")
    return short - long


def league_past_average(df: pd.DataFrame, value_col: str) -> pd.Series:
    if value_col not in df.columns:
        return pd.Series(np.nan, index=df.index)

    working = df[["league", "date", value_col]].copy()
    working[value_col] = pd.to_numeric(working[value_col], errors="coerce")
    daily = (
        working.dropna(subset=["date"])
        .groupby(["league", "date"], as_index=False)[value_col]
        .mean()
        .sort_values(["league", "date"])
    )
    daily[f"league_{value_col}_avg_past"] = (
        daily.groupby("league")[value_col]
        .transform(lambda s: s.shift(1).expanding(min_periods=1).mean())
    )
    merged = working[["league", "date"]].merge(
        daily[["league", "date", f"league_{value_col}_avg_past"]],
        on=["league", "date"],
        how="left",
    )
    return merged[f"league_{value_col}_avg_past"]


def add_form_features(df: pd.DataFrame, features: List[str]) -> pd.DataFrame:
    LOGGER.info("Criando features de forma.")
    df["win_streak"] = previous_streak(df, "W")
    df["loss_streak"] = previous_streak(df, "L")
    df["unbeaten_streak"] = previous_streak(df, "W", unbeaten=True)
    df["points_last_5"] = rolling_past(df, ["team_key"], "points", 5, "sum")
    df["points_trend"] = rolling_trend(df, "points", 3, 6)
    features.extend(["win_streak", "loss_streak", "unbeaten_streak", "points_last_5", "points_trend"])
    return df


def add_consistency_features(df: pd.DataFrame, features: List[str]) -> pd.DataFrame:
    LOGGER.info("Criando features de consistência.")
    df["goals_std_last_5"] = rolling_past(df, ["team_key"], "goals_for_ft", 5, "std")
    df["shots_std_last_5"] = rolling_past(df, ["team_key"], "shots_for", 5, "std")
    df["corners_std_last_5"] = rolling_past(df, ["team_key"], "corners_for", 5, "std")
    features.extend(["goals_std_last_5", "shots_std_last_5", "corners_std_last_5"])
    return df


def add_relative_strength_features(df: pd.DataFrame, features: List[str]) -> pd.DataFrame:
    LOGGER.info("Criando features de força relativa contra média histórica da liga.")
    for value_col, output_col in [
        ("goals_for_ft", "goals_vs_league_avg"),
        ("shots_for", "shots_vs_league_avg"),
        ("corners_for", "corners_vs_league_avg"),
    ]:
        team_past = rolling_past(df, ["team_key"], value_col, 5, "mean")
        league_avg = league_past_average(df, value_col)
        df[output_col] = safe_divide(team_past, league_avg)
        features.append(output_col)
    return df


def add_efficiency_features(df: pd.DataFrame, features: List[str]) -> pd.DataFrame:
    LOGGER.info("Criando features avançadas de eficiência.")
    goals_past = rolling_past(df, ["team_key"], "goals_for_ft", 5, "mean")
    shots_past = rolling_past(df, ["team_key"], "shots_for", 5, "mean")
    sot_past = rolling_past(df, ["team_key"], "shots_on_target_for", 5, "mean")
    df["goals_per_shot"] = safe_divide(goals_past, shots_past)
    df["goals_per_shot_on_target"] = safe_divide(goals_past, sot_past)
    df["shots_on_target_ratio"] = safe_divide(sot_past, shots_past)
    features.extend(["goals_per_shot", "goals_per_shot_on_target", "shots_on_target_ratio"])
    return df


def add_pressure_features(df: pd.DataFrame, features: List[str]) -> pd.DataFrame:
    LOGGER.info("Criando features de pressão.")
    df["pressure_index"] = df.groupby("team_key", group_keys=False)["pressure_raw"].transform(lambda s: s.shift(1))
    df["pressure_avg_last_5"] = rolling_past(df, ["team_key"], "pressure_raw", 5, "mean")
    features.extend(["pressure_index", "pressure_avg_last_5"])
    return df


def add_home_away_context(df: pd.DataFrame, features: List[str]) -> pd.DataFrame:
    LOGGER.info("Criando contexto home/away histórico.")
    side_features = {
        "home_goals_context_last_5": ("home", "goals_for_ft"),
        "away_goals_context_last_5": ("away", "goals_for_ft"),
        "home_shots_context_last_5": ("home", "shots_for"),
        "away_shots_context_last_5": ("away", "shots_for"),
        "home_corners_context_last_5": ("home", "corners_for"),
        "away_corners_context_last_5": ("away", "corners_for"),
    }
    for output_col, (side_value, base_col) in side_features.items():
        rolled = rolling_past(df, ["team_key", "side"], base_col, 5, "mean")
        df[output_col] = np.where(df["side"].astype(str).str.lower() == side_value, rolled, np.nan)
        features.append(output_col)
    return df


def add_opponent_context_features(df: pd.DataFrame, features: List[str]) -> pd.DataFrame:
    LOGGER.info("Criando contexto vs adversário.")
    league_goals_avg = league_past_average(df, "goals_for_ft")
    team_attack = rolling_past(df, ["team_key"], "goals_for_ft", 5, "mean")
    df["team_attack_strength"] = safe_divide(team_attack, league_goals_avg)

    if "match_key" in df.columns:
        opponent_defense = df[["match_key", "team_key"]].copy()
        opponent_defense["opponent_defense_weakness"] = rolling_past(df, ["team_key"], "goals_against_ft", 5, "mean")
        opponent_defense = opponent_defense.rename(columns={"team_key": "opponent_key"})
        df = df.merge(
            opponent_defense[["match_key", "opponent_key", "opponent_defense_weakness"]],
            on=["match_key", "opponent_key"],
            how="left",
        )
    else:
        LOGGER.warning("match_key ausente; opponent_defense_weakness será NaN.")
        df["opponent_defense_weakness"] = np.nan

    df["attack_vs_defense_ratio"] = safe_divide(df["team_attack_strength"], df["opponent_defense_weakness"])
    features.extend(["attack_vs_defense_ratio", "team_attack_strength", "opponent_defense_weakness"])
    return df


def add_market_features(df: pd.DataFrame, features: List[str]) -> pd.DataFrame:
    LOGGER.info("Criando features específicas por mercado: gols, corners e shots.")
    df["goal_trend"] = rolling_trend(df, "goals_for_ft", 3, 6)

    goals_past = rolling_past(df, ["team_key"], "goals_for_ft", 5, "mean")
    shots_past = rolling_past(df, ["team_key"], "shots_for", 5, "mean")
    sot_past = rolling_past(df, ["team_key"], "shots_on_target_for", 5, "mean")
    df["expected_goals_proxy"] = (
        goals_past.fillna(0) * 0.50
        + safe_divide(sot_past, shots_past).fillna(0) * 0.30
        + safe_divide(shots_past, league_past_average(df, "shots_for")).fillna(0) * 0.20
    ).replace({0: np.nan})

    df["corners_trend"] = rolling_trend(df, "corners_for", 3, 6)
    corners_avg = rolling_past(df, ["team_key"], "corners_for", 5, "mean")
    shots_avg = rolling_past(df, ["team_key"], "shots_for", 5, "mean")
    conversion_avg = rolling_past(df, ["team_key"], "shots_conversion_rate", 5, "mean")

    league_corners_avg = league_past_average(df, "corners_for")
    league_shots_avg = league_past_average(df, "shots_for")

    df["high_corner_flag"] = (corners_avg > league_corners_avg).astype("float")
    df.loc[corners_avg.isna() | league_corners_avg.isna(), "high_corner_flag"] = np.nan

    df["high_shots_flag"] = (shots_avg > league_shots_avg).astype("float")
    df.loc[shots_avg.isna() | league_shots_avg.isna(), "high_shots_flag"] = np.nan

    df["low_conversion_flag"] = (conversion_avg < 0.08).astype("float")
    df.loc[conversion_avg.isna(), "low_conversion_flag"] = np.nan

    features.extend([
        "goal_trend",
        "expected_goals_proxy",
        "corners_trend",
        "high_corner_flag",
        "high_shots_flag",
        "low_conversion_flag",
    ])
    return df


def recalculate_feature(df: pd.DataFrame, spec: Dict[str, Any]) -> pd.Series:
    return rolling_past(
        df,
        list(spec["group"]),
        str(spec["base"]),
        int(spec["window"]),
        str(spec.get("op", "mean")),
    )


def compare_series(left: pd.Series, right: pd.Series, tolerance: float = 1e-9) -> bool:
    left_num = pd.to_numeric(left, errors="coerce")
    right_num = pd.to_numeric(right, errors="coerce")
    both_nan = left_num.isna() & right_num.isna()
    close = (left_num - right_num).abs() <= tolerance
    return bool((both_nan | close).all())


def validate_anti_leakage(df: pd.DataFrame, features_created: List[str]) -> Tuple[bool, List[Dict[str, Any]]]:
    LOGGER.info("Validando anti-leakage das features avançadas.")
    failures: List[Dict[str, Any]] = []

    for feature_name, spec in ADVANCED_ROLLING_MAP.items():
        if feature_name not in df.columns:
            continue
        expected = recalculate_feature(df, spec)
        actual = df[feature_name]

        if feature_name.startswith("home_"):
            expected = expected.where(df["side"].astype(str).str.lower() == "home")
        if feature_name.startswith("away_"):
            expected = expected.where(df["side"].astype(str).str.lower() == "away")

        if not compare_series(actual, expected):
            failures.append(
                {
                    "feature": feature_name,
                    "base": spec["base"],
                    "group": spec["group"],
                    "window": spec["window"],
                    "reason": "generated values differ from shift(1)+rolling recalculation",
                }
            )

    if "pressure_index" in df.columns:
        expected_pressure = df.groupby("team_key", group_keys=False)["pressure_raw"].transform(lambda s: s.shift(1))
        if not compare_series(df["pressure_index"], expected_pressure):
            failures.append(
                {
                    "feature": "pressure_index",
                    "base": "pressure_raw",
                    "group": ["team_key"],
                    "window": 1,
                    "reason": "pressure_index must equal previous match pressure_raw",
                }
            )

    derived_expectations: Dict[str, pd.Series] = {}
    goals_past = rolling_past(df, ["team_key"], "goals_for_ft", 5, "mean")
    shots_past = rolling_past(df, ["team_key"], "shots_for", 5, "mean")
    sot_past = rolling_past(df, ["team_key"], "shots_on_target_for", 5, "mean")
    corners_past = rolling_past(df, ["team_key"], "corners_for", 5, "mean")
    conversion_past = rolling_past(df, ["team_key"], "shots_conversion_rate", 5, "mean")

    league_goals = league_past_average(df, "goals_for_ft")
    league_shots = league_past_average(df, "shots_for")
    league_corners = league_past_average(df, "corners_for")

    derived_expectations["goals_per_shot"] = safe_divide(goals_past, shots_past)
    derived_expectations["goals_per_shot_on_target"] = safe_divide(goals_past, sot_past)
    derived_expectations["shots_on_target_ratio"] = safe_divide(sot_past, shots_past)
    derived_expectations["goals_vs_league_avg"] = safe_divide(goals_past, league_goals)
    derived_expectations["shots_vs_league_avg"] = safe_divide(shots_past, league_shots)
    derived_expectations["corners_vs_league_avg"] = safe_divide(corners_past, league_corners)
    derived_expectations["team_attack_strength"] = safe_divide(goals_past, league_goals)
    derived_expectations["goal_trend"] = rolling_trend(df, "goals_for_ft", 3, 6)
    derived_expectations["corners_trend"] = rolling_trend(df, "corners_for", 3, 6)
    derived_expectations["points_trend"] = rolling_trend(df, "points", 3, 6)

    expected_goals_proxy = (
        goals_past.fillna(0) * 0.50
        + safe_divide(sot_past, shots_past).fillna(0) * 0.30
        + safe_divide(shots_past, league_shots).fillna(0) * 0.20
    ).replace({0: np.nan})
    derived_expectations["expected_goals_proxy"] = expected_goals_proxy

    high_corner_flag = (corners_past > league_corners).astype("float")
    high_corner_flag.loc[corners_past.isna() | league_corners.isna()] = np.nan
    derived_expectations["high_corner_flag"] = high_corner_flag

    high_shots_flag = (shots_past > league_shots).astype("float")
    high_shots_flag.loc[shots_past.isna() | league_shots.isna()] = np.nan
    derived_expectations["high_shots_flag"] = high_shots_flag

    low_conversion_flag = (conversion_past < 0.08).astype("float")
    low_conversion_flag.loc[conversion_past.isna()] = np.nan
    derived_expectations["low_conversion_flag"] = low_conversion_flag

    for feature_name, expected in derived_expectations.items():
        if feature_name in df.columns and not compare_series(df[feature_name], expected):
            failures.append(
                {
                    "feature": feature_name,
                    "reason": "derived feature differs from past-only recalculation",
                }
            )

    if {"attack_vs_defense_ratio", "team_attack_strength", "opponent_defense_weakness"}.issubset(df.columns):
        expected_ratio = safe_divide(df["team_attack_strength"], df["opponent_defense_weakness"])
        if not compare_series(df["attack_vs_defense_ratio"], expected_ratio):
            failures.append(
                {
                    "feature": "attack_vs_defense_ratio",
                    "reason": "ratio differs from team_attack_strength / opponent_defense_weakness",
                }
            )

    historical_columns = [
        col for col in features_created
        if col.endswith("_last_5") or col in {"pressure_index", "points_last_5"}
    ]
    first_rows = df.groupby("team_key", group_keys=False).head(1)
    for column in historical_columns:
        if column in first_rows.columns and first_rows[column].notna().any():
            failures.append(
                {
                    "feature": column,
                    "reason": "first match per team contains historical value",
                }
            )

    if failures:
        LOGGER.error("Validação anti-leakage falhou em %s features.", len(failures))
    else:
        LOGGER.info("Validação anti-leakage OK para features avançadas.")

    return len(failures) == 0, failures


def feature_distribution(df: pd.DataFrame, features: List[str]) -> Dict[str, Dict[str, Any]]:
    distribution: Dict[str, Dict[str, Any]] = {}
    for feature in features:
        if feature not in df.columns:
            continue
        series = pd.to_numeric(df[feature], errors="coerce")
        distribution[feature] = {
            "missing_pct": round(float(series.isna().mean() * 100), 4),
            "non_null_count": int(series.notna().sum()),
            "mean": None if series.dropna().empty else round(float(series.mean()), 6),
            "std": None if series.dropna().empty else round(float(series.std(ddof=0)), 6),
            "min": None if series.dropna().empty else round(float(series.min()), 6),
            "max": None if series.dropna().empty else round(float(series.max()), 6),
        }
    return distribution



def validate_output_dataset(df: pd.DataFrame, expected_features: Optional[List[str]] = None) -> None:
    """Validate final advanced dataset before persisting.

    This is a hard gate for Patch 3.0.1: the output must be non-empty and must
    contain every expected advanced feature. The function does not change data;
    it only prevents silently shipping an incomplete parquet file.
    """
    expected = expected_features or EXPECTED_ADVANCED_FEATURES
    if df.empty:
        raise ValueError("Advanced feature dataset is empty; refusing to save output.")

    missing_columns = [column for column in expected if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Advanced feature dataset missing expected columns: {missing_columns}")

    if "date" not in df.columns or "team_key" not in df.columns:
        raise ValueError("Advanced feature dataset must contain date and team_key columns.")

    LOGGER.info(
        "Validação final do dataset avançado OK: linhas=%s colunas=%s features_esperadas=%s",
        len(df),
        len(df.columns),
        len(expected),
    )


def build_report(
    df: pd.DataFrame,
    features_created: List[str],
    ignored_features: List[str],
    leakage_ok: bool,
    leakage_failures: List[Dict[str, Any]],
    execution_time_seconds: float,
) -> Dict[str, Any]:
    feature_missing = {
        feature: round(float(df[feature].isna().mean() * 100), 4)
        for feature in features_created
        if feature in df.columns
    }
    valid_feature_values = [100.0 - missing for missing in feature_missing.values()]
    return {
        "ok": bool(leakage_ok),
        "leakage_validation": {
            "status": "OK" if leakage_ok else "FAIL",
            "failures": leakage_failures,
            "rule": "All temporal features must use prior rows only through shift(1), rolling or prior-date league aggregates.",
        },
        "rows": int(len(df)),
        "teams": int(df["team_key"].nunique()) if "team_key" in df.columns else 0,
        "leagues": int(df["league"].nunique()) if "league" in df.columns else 0,
        "features_created": features_created,
        "features_created_count": len(features_created),
        "features_ignored": ignored_features,
        "feature_validity_pct_avg": round(float(np.mean(valid_feature_values)), 4) if valid_feature_values else 0.0,
        "missing_by_feature_pct": feature_missing,
        "distribution_by_feature": feature_distribution(df, features_created),
        "execution_time_seconds": execution_time_seconds,
    }


def build_advanced_features(project_root: Optional[Path] = None) -> AdvancedFeaturesBuildResult:
    configure_logging()
    started = time.perf_counter()
    root = project_root or Path.cwd()
    input_path = resolve_path(INPUT_PATH, root)
    output_path = resolve_path(OUTPUT_PATH, root)
    report_path = resolve_path(REPORT_PATH, root)

    ensure_directories(root)

    LOGGER.info("=" * 72)
    LOGGER.info("MATCHFLOW PATCH 3.0 - ADVANCED FEATURES PIPELINE START")
    LOGGER.info("Entrada: %s", input_path)
    LOGGER.info("Saída: %s", output_path)

    if not input_path.exists():
        LOGGER.error("Team dataset não encontrado: %s", input_path)
        raise FileNotFoundError(
            f"Team dataset not found: {input_path}. Execute primeiro: python run_team_dataset_pipeline.py"
        )

    try:
        df = safe_read_dataframe(input_path)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Falha ao ler team dataset: %s", exc)
        raise

    rows_loaded = int(len(df))
    LOGGER.info("Team dataset carregado com %s linhas e %s colunas.", len(df), len(df.columns))

    df = prepare_base(df)
    features_created: List[str] = []
    ignored_features: List[str] = []

    df = add_form_features(df, features_created)
    df = add_consistency_features(df, features_created)
    df = add_relative_strength_features(df, features_created)
    df = add_efficiency_features(df, features_created)
    df = add_pressure_features(df, features_created)
    df = add_home_away_context(df, features_created)
    df = add_opponent_context_features(df, features_created)
    df = add_market_features(df, features_created)

    leakage_ok, leakage_failures = validate_anti_leakage(df, features_created)
    execution_time = round(time.perf_counter() - started, 4)

    report = build_report(
        df=df,
        features_created=features_created,
        ignored_features=ignored_features,
        leakage_ok=leakage_ok,
        leakage_failures=leakage_failures,
        execution_time_seconds=execution_time,
    )

    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    LOGGER.info("Relatório de qualidade salvo em: %s", report_path)

    if not leakage_ok:
        raise RuntimeError(f"Anti-leakage validation failed. See report: {report_path}")

    validate_output_dataset(df, EXPECTED_ADVANCED_FEATURES)

    try:
        safe_write_dataframe(df, output_path, index=False)
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Falha ao salvar dataset avançado: %s", exc)
        raise

    LOGGER.info("Dataset avançado salvo em: %s", output_path)
    LOGGER.info("Linhas finais: %s", len(df))
    LOGGER.info("Features avançadas criadas: %s", len(features_created))
    LOGGER.info("Validade média das features: %s%%", report["feature_validity_pct_avg"])
    LOGGER.info("MATCHFLOW PATCH 3.0 - ADVANCED FEATURES PIPELINE END")
    LOGGER.info("=" * 72)

    return AdvancedFeaturesBuildResult(
        input_path=input_path,
        output_path=output_path,
        report_path=report_path,
        rows_loaded=rows_loaded,
        rows_created=int(len(df)),
        total_features_created=len(features_created),
        leakage_ok=leakage_ok,
        features_created=features_created,
        ignored_features=ignored_features,
        execution_time_seconds=execution_time,
    )


if __name__ == "__main__":
    build_advanced_features()
