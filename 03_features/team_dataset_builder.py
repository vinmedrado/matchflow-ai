from __future__ import annotations

import hashlib
import json
import logging
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

from backend.core.logging_config import configure_logging, get_logger

LOGGER = get_logger("matchflow.team_dataset_builder")

REQUIRED_COLUMNS = [
    "date",
    "league",
    "season",
    "home_team",
    "away_team",
    "home_team_key",
    "away_team_key",
]

COLUMN_CANDIDATES: Dict[str, List[str]] = {
    "goals_home_ft": ["goals_home_ft", "Goals_H_FT", "goals_h_ft", "home_goals", "goals_home"],
    "goals_away_ft": ["goals_away_ft", "Goals_A_FT", "goals_a_ft", "away_goals", "goals_away"],
    "total_goals_ft": ["total_goals_ft", "TotalGoals_FT", "totalgoals_ft"],
    "goals_home_ht": ["goals_home_ht", "Goals_H_HT", "goals_h_ht"],
    "goals_away_ht": ["goals_away_ht", "Goals_A_HT", "goals_a_ht"],
    "total_goals_ht": ["total_goals_ht", "TotalGoals_HT", "totalgoals_ht"],
    "shots_home": ["shots_home", "Shots_H", "shots_h"],
    "shots_away": ["shots_away", "Shots_A", "shots_a"],
    "shots_on_target_home": ["shots_on_target_home", "ShotsOnTarget_H", "shots_on_target_h"],
    "shots_on_target_away": ["shots_on_target_away", "ShotsOnTarget_A", "shots_on_target_a"],
    "corners_home": ["corners_home", "Corners_H_FT", "corners_h_ft"],
    "corners_away": ["corners_away", "Corners_A_FT", "corners_a_ft"],
}

ROLLING_WINDOWS = [3, 5, 10]


@dataclass
class TeamDatasetBuildResult:
    input_path: Path
    output_path: Path
    report_path: Path
    matches_loaded: int
    rows_created: int
    unique_teams: int
    unique_leagues: int
    features_created: List[str] = field(default_factory=list)
    ignored_features: List[str] = field(default_factory=list)
    leakage_ok: bool = False
    execution_time_seconds: float = 0.0


def resolve_path(path: str | Path, project_root: Optional[Path] = None) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    root = project_root or Path.cwd()
    return (root / p).resolve()


def detect_column(df: pd.DataFrame, candidates: Iterable[str]) -> Optional[str]:
    exact = {c: c for c in df.columns}
    lower = {str(c).lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate in exact:
            return exact[candidate]
        lowered = candidate.lower()
        if lowered in lower:
            return lower[lowered]
    return None


def ensure_metric_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    df = df.copy()
    missing: List[str] = []
    for standard_name, candidates in COLUMN_CANDIDATES.items():
        found = detect_column(df, candidates)
        if found is None:
            df[standard_name] = np.nan
            missing.append(standard_name)
        elif found != standard_name:
            df[standard_name] = df[found]
    for col in COLUMN_CANDIDATES:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if df["total_goals_ft"].isna().all():
        df["total_goals_ft"] = df["goals_home_ft"] + df["goals_away_ft"]
    if df["total_goals_ht"].isna().all():
        df["total_goals_ht"] = df["goals_home_ht"] + df["goals_away_ht"]
    return df, missing


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = denominator.replace({0: np.nan})
    result = numerator / denominator
    return result.replace([np.inf, -np.inf], np.nan)


def points_from_result(result: str) -> int:
    if result == "W":
        return 3
    if result == "D":
        return 1
    return 0


def build_match_identity(row: pd.Series) -> str:
    existing = row.get("match_key")
    if pd.notna(existing) and str(existing).strip():
        return str(existing)
    parts = [
        str(row.get("date", "")),
        str(row.get("league", "")),
        str(row.get("season", "")),
        str(row.get("home_team_key", "")),
        str(row.get("away_team_key", "")),
    ]
    return "|".join(parts)


def load_base_dataset(input_path: Path) -> pd.DataFrame:
    csv_fallback = input_path.with_suffix(".csv")
    if not input_path.exists() and not csv_fallback.exists():
        raise FileNotFoundError(f"Base dataset not found: {input_path}")
    df = safe_read_dataframe(input_path)
    if df.empty:
        raise ValueError(f"Base dataset is empty: {input_path}")
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    invalid_dates = int(df["date"].isna().sum())
    if invalid_dates:
        LOGGER.warning("Dropping rows with invalid dates: %s", invalid_dates)
        df = df.dropna(subset=["date"])
    if df.empty:
        raise ValueError("No valid rows after date validation")
    return df


def expand_matches_to_team_rows(matches: pd.DataFrame) -> pd.DataFrame:
    records: List[Dict[str, Any]] = []
    for _, row in matches.iterrows():
        match_id = build_match_identity(row)
        base = {
            "event_id": row.get("event_id", np.nan),
            "match_key": match_id,
            "date": row["date"],
            "league": row["league"],
            "season": row["season"],
            "source_file": row.get("source_file", np.nan),
            "source_layer": row.get("source_layer", np.nan),
        }
        home_goals_ft = row.get("goals_home_ft", np.nan)
        away_goals_ft = row.get("goals_away_ft", np.nan)
        home_goals_ht = row.get("goals_home_ht", np.nan)
        away_goals_ht = row.get("goals_away_ht", np.nan)

        def result(gf: Any, ga: Any) -> Optional[str]:
            if pd.isna(gf) or pd.isna(ga):
                return None
            if gf > ga:
                return "W"
            if gf < ga:
                return "L"
            return "D"

        records.append({
            **base,
            "team_key": row["home_team_key"],
            "team_name": row["home_team"],
            "opponent_key": row["away_team_key"],
            "opponent_name": row["away_team"],
            "side": "home",
            "goals_for_ft": home_goals_ft,
            "goals_against_ft": away_goals_ft,
            "total_goals_ft": row.get("total_goals_ft", np.nan),
            "goals_for_ht": home_goals_ht,
            "goals_against_ht": away_goals_ht,
            "total_goals_ht": row.get("total_goals_ht", np.nan),
            "shots_for": row.get("shots_home", np.nan),
            "shots_against": row.get("shots_away", np.nan),
            "shots_on_target_for": row.get("shots_on_target_home", np.nan),
            "shots_on_target_against": row.get("shots_on_target_away", np.nan),
            "corners_for": row.get("corners_home", np.nan),
            "corners_against": row.get("corners_away", np.nan),
            "result_ft": result(home_goals_ft, away_goals_ft),
            "result_ht": result(home_goals_ht, away_goals_ht),
        })
        records.append({
            **base,
            "team_key": row["away_team_key"],
            "team_name": row["away_team"],
            "opponent_key": row["home_team_key"],
            "opponent_name": row["home_team"],
            "side": "away",
            "goals_for_ft": away_goals_ft,
            "goals_against_ft": home_goals_ft,
            "total_goals_ft": row.get("total_goals_ft", np.nan),
            "goals_for_ht": away_goals_ht,
            "goals_against_ht": home_goals_ht,
            "total_goals_ht": row.get("total_goals_ht", np.nan),
            "shots_for": row.get("shots_away", np.nan),
            "shots_against": row.get("shots_home", np.nan),
            "shots_on_target_for": row.get("shots_on_target_away", np.nan),
            "shots_on_target_against": row.get("shots_on_target_home", np.nan),
            "corners_for": row.get("corners_away", np.nan),
            "corners_against": row.get("corners_home", np.nan),
            "result_ft": result(away_goals_ft, home_goals_ft),
            "result_ht": result(away_goals_ht, home_goals_ht),
        })
    team_df = pd.DataFrame.from_records(records)
    team_df["points"] = team_df["result_ft"].map(points_from_result).astype("Int64")
    team_df["is_win"] = (team_df["result_ft"] == "W").astype(int)
    team_df["is_draw"] = (team_df["result_ft"] == "D").astype(int)
    team_df["is_loss"] = (team_df["result_ft"] == "L").astype(int)
    team_df["shots_conversion_rate"] = safe_divide(team_df["goals_for_ft"], team_df["shots_for"])
    team_df["shots_on_target_rate"] = safe_divide(team_df["shots_on_target_for"], team_df["shots_for"])
    return team_df


def _rolling_mean_previous(group: pd.DataFrame, source_col: str, window: int) -> pd.Series:
    ordered = group.sort_values(["date", "match_key", "side"])
    values = pd.to_numeric(ordered[source_col], errors="coerce").shift(1).rolling(window=window, min_periods=1).mean()
    return values.reindex(group.index)


def _rolling_mean_previous_transform(df: pd.DataFrame, group_cols: str | List[str], source_col: str, window: int) -> pd.Series:
    """Vectorized, pandas-future-safe shift(1)+rolling mean within sorted groups.

    This replaces DataFrameGroupBy.apply usages that trigger pandas deprecation
    warnings while preserving the same anti-leakage semantics. Callers must pass
    a dataframe already sorted in the intended temporal order.
    """
    return (
        pd.to_numeric(df[source_col], errors="coerce")
        .groupby([df[c] for c in ([group_cols] if isinstance(group_cols, str) else group_cols)], sort=False)
        .transform(lambda s: s.shift(1).rolling(window=window, min_periods=1).mean())
    )


def add_rolling_features(team_df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Create temporal team features with strict anti-leakage shift(1) semantics."""
    df = team_df.sort_values(["team_key", "date", "match_key", "side"]).reset_index(drop=True)
    created: List[str] = []

    rolling_map = {
        "goals_for_ft": "goals_for_ft_avg_last_{w}",
        "goals_against_ft": "goals_against_ft_avg_last_{w}",
        "total_goals_ft": "total_goals_ft_avg_last_{w}",
        "points": "points_avg_last_{w}",
        "is_win": "win_rate_last_{w}",
        "is_draw": "draw_rate_last_{w}",
        "is_loss": "loss_rate_last_{w}",
        "shots_for": "shots_avg_last_{w}",
        "shots_against": "shots_allowed_avg_last_{w}",
        "shots_on_target_for": "shots_on_target_avg_last_{w}",
        "shots_on_target_against": "shots_on_target_allowed_avg_last_{w}",
        "corners_for": "corners_avg_last_{w}",
        "corners_against": "corners_allowed_avg_last_{w}",
    }

    for source_col, name_template in rolling_map.items():
        for window in ROLLING_WINDOWS:
            feature_name = name_template.format(w=window)
            df[feature_name] = _rolling_mean_previous_transform(df, "team_key", source_col, window)
            created.append(feature_name)

    efficiency_features = {
        "shots_conversion_rate": "shots_conversion_rate_avg_last_5",
        "shots_on_target_rate": "shots_on_target_rate_avg_last_5",
    }
    for source_col, feature_name in efficiency_features.items():
        df[feature_name] = _rolling_mean_previous_transform(df, "team_key", source_col, 5)
        created.append(feature_name)

    # Home/away context MUST be grouped by team_key + side. This prevents mixing
    # a team's home history with its away history and still applies shift(1).
    side_features = {
        "goals_for_ft": {"home": "home_goals_avg_last_5", "away": "away_goals_avg_last_5"},
        "shots_for": {"home": "home_shots_avg_last_5", "away": "away_shots_avg_last_5"},
        "corners_for": {"home": "home_corners_avg_last_5", "away": "away_corners_avg_last_5"},
    }
    for source_col, side_names in side_features.items():
        for side, feature_name in side_names.items():
            df[feature_name] = np.nan
            mask = df["side"] == side
            if mask.any():
                df.loc[mask, feature_name] = _rolling_mean_previous_transform(df.loc[mask], ["team_key", "side"], source_col, 5)
            created.append(feature_name)

    return df.sort_values(["date", "team_key", "side", "match_key"]).reset_index(drop=True), created


def _rolling_feature_spec(feature: str) -> Optional[Dict[str, Any]]:
    """Map each created rolling feature back to its source column and window."""
    specs: List[Tuple[str, str, int, str]] = []
    base_map = {
        "goals_for_ft": "goals_for_ft_avg_last_{w}",
        "goals_against_ft": "goals_against_ft_avg_last_{w}",
        "total_goals_ft": "total_goals_ft_avg_last_{w}",
        "points": "points_avg_last_{w}",
        "is_win": "win_rate_last_{w}",
        "is_draw": "draw_rate_last_{w}",
        "is_loss": "loss_rate_last_{w}",
        "shots_for": "shots_avg_last_{w}",
        "shots_against": "shots_allowed_avg_last_{w}",
        "shots_on_target_for": "shots_on_target_avg_last_{w}",
        "shots_on_target_against": "shots_on_target_allowed_avg_last_{w}",
        "corners_for": "corners_avg_last_{w}",
        "corners_against": "corners_allowed_avg_last_{w}",
    }
    for source_col, template in base_map.items():
        for window in ROLLING_WINDOWS:
            specs.append((template.format(w=window), source_col, window, "team"))
    specs.extend([
        ("shots_conversion_rate_avg_last_5", "shots_conversion_rate", 5, "team"),
        ("shots_on_target_rate_avg_last_5", "shots_on_target_rate", 5, "team"),
        ("home_goals_avg_last_5", "goals_for_ft", 5, "side:home"),
        ("away_goals_avg_last_5", "goals_for_ft", 5, "side:away"),
        ("home_shots_avg_last_5", "shots_for", 5, "side:home"),
        ("away_shots_avg_last_5", "shots_for", 5, "side:away"),
        ("home_corners_avg_last_5", "corners_for", 5, "side:home"),
        ("away_corners_avg_last_5", "corners_for", 5, "side:away"),
    ])
    for name, source_col, window, scope in specs:
        if feature == name:
            return {"feature": name, "source_col": source_col, "window": window, "scope": scope}
    return None


def _series_equal_with_nan(left: pd.Series, right: pd.Series, tolerance: float = 1e-10) -> bool:
    left_values = pd.to_numeric(left, errors="coerce").reset_index(drop=True)
    right_values = pd.to_numeric(right, errors="coerce").reset_index(drop=True)
    left_nan = left_values.isna()
    right_nan = right_values.isna()
    if not left_nan.equals(right_nan):
        return False
    comparable = ~(left_nan | right_nan)
    if not comparable.any():
        return True
    return bool(np.allclose(left_values[comparable], right_values[comparable], atol=tolerance, rtol=0))


def _recalculate_team_feature(df: pd.DataFrame, source_col: str, window: int) -> pd.Series:
    ordered = df.sort_values(["team_key", "date", "match_key", "side"]).reset_index()
    values = _rolling_mean_previous_transform(ordered, "team_key", source_col, window)
    recalculated = pd.Series(index=df.index, dtype="float64")
    recalculated.loc[ordered["index"].to_numpy()] = values.to_numpy()
    return recalculated


def _recalculate_side_feature(df: pd.DataFrame, source_col: str, window: int, side: str) -> pd.Series:
    recalculated = pd.Series(np.nan, index=df.index, dtype="float64")
    mask = df["side"] == side
    if not mask.any():
        return recalculated
    subset = df.loc[mask].sort_values(["team_key", "side", "date", "match_key"]).reset_index()
    values = _rolling_mean_previous_transform(subset, ["team_key", "side"], source_col, window)
    recalculated.loc[subset["index"].to_numpy()] = values.to_numpy()
    return recalculated


def validate_anti_leakage(df: pd.DataFrame, rolling_features: List[str]) -> Dict[str, Any]:
    """Validate every generated rolling feature by recalculating shift(1)+rolling."""
    validation: Dict[str, Any] = {
        "leakage_ok": True,
        "checks": [],
        "failures": [],
        "features_checked": [],
    }
    sorted_df = df.sort_values(["team_key", "date", "match_key", "side"]).reset_index(drop=True)

    first_rows = sorted_df.groupby("team_key", as_index=False).head(1)
    team_scope_features = [
        f for f in rolling_features
        if (_rolling_feature_spec(f) or {}).get("scope") == "team" and f in first_rows.columns
    ]
    first_feature_non_null = int(first_rows[team_scope_features].notna().sum().sum()) if team_scope_features else 0
    first_ok = first_feature_non_null == 0
    validation["checks"].append({
        "name": "first_match_has_no_team_history",
        "ok": first_ok,
        "non_null_rolling_values_on_first_rows": first_feature_non_null,
    })
    if not first_ok:
        validation["leakage_ok"] = False
        validation["failures"].append("First match for at least one team contains team-scope rolling feature values")

    for side in ["home", "away"]:
        side_features = [
            f for f in rolling_features
            if (_rolling_feature_spec(f) or {}).get("scope") == f"side:{side}" and f in sorted_df.columns
        ]
        if not side_features:
            continue
        first_side_rows = sorted_df[sorted_df["side"] == side].groupby(["team_key", "side"], as_index=False).head(1)
        non_null = int(first_side_rows[side_features].notna().sum().sum()) if not first_side_rows.empty else 0
        ok = non_null == 0
        validation["checks"].append({
            "name": f"first_{side}_match_has_no_side_history",
            "ok": ok,
            "non_null_rolling_values_on_first_side_rows": non_null,
        })
        if not ok:
            validation["leakage_ok"] = False
            validation["failures"].append(f"First {side} match for at least one team contains side-scope rolling feature values")

    for feature in rolling_features:
        if feature not in sorted_df.columns:
            continue
        spec = _rolling_feature_spec(feature)
        if spec is None:
            validation["checks"].append({"name": f"unknown_feature_spec_{feature}", "ok": False})
            validation["leakage_ok"] = False
            validation["failures"].append(f"No anti-leakage spec registered for feature: {feature}")
            continue

        source_col = spec["source_col"]
        if source_col not in sorted_df.columns:
            validation["checks"].append({"name": f"missing_source_{feature}", "ok": False, "source_col": source_col})
            validation["leakage_ok"] = False
            validation["failures"].append(f"Missing source column {source_col} for feature {feature}")
            continue

        if spec["scope"] == "team":
            expected = _recalculate_team_feature(sorted_df, source_col, int(spec["window"]))
        elif str(spec["scope"]).startswith("side:"):
            side = str(spec["scope"]).split(":", 1)[1]
            expected = _recalculate_side_feature(sorted_df, source_col, int(spec["window"]), side)
        else:
            validation["checks"].append({"name": f"invalid_scope_{feature}", "ok": False, "scope": spec["scope"]})
            validation["leakage_ok"] = False
            validation["failures"].append(f"Invalid scope for feature {feature}: {spec['scope']}")
            continue

        ok = _series_equal_with_nan(expected, sorted_df[feature])
        validation["features_checked"].append(feature)
        validation["checks"].append({
            "name": f"rolling_shift_validation_{feature}",
            "ok": ok,
            "source_col": source_col,
            "window": int(spec["window"]),
            "scope": spec["scope"],
        })
        if not ok:
            validation["leakage_ok"] = False
            validation["failures"].append(f"Rolling feature does not match shifted historical calculation: {feature}")

    return validation

def create_quality_report(
    team_df: pd.DataFrame,
    features_created: List[str],
    ignored_features: List[str],
    leakage_validation: Dict[str, Any],
) -> Dict[str, Any]:
    feature_cols = [c for c in features_created if c in team_df.columns]
    total_cells = len(team_df) * max(len(feature_cols), 1)
    valid_feature_cells = int(team_df[feature_cols].notna().sum().sum()) if feature_cols else 0
    missing_pct_by_column = {
        col: round(float(team_df[col].isna().mean() * 100), 4)
        for col in team_df.columns
    }
    return {
        "ok": bool(leakage_validation.get("leakage_ok")),
        "leakage_validation": leakage_validation,
        "rows": int(len(team_df)),
        "unique_teams": int(team_df["team_key"].nunique()) if "team_key" in team_df else 0,
        "unique_leagues": int(team_df["league"].nunique()) if "league" in team_df else 0,
        "features_created_count": len(features_created),
        "features_created": features_created,
        "features_ignored": ignored_features,
        "valid_feature_values_pct": round((valid_feature_cells / total_cells) * 100, 4) if total_cells else 0,
        "data_available_pct_by_column": {
            col: round(100 - pct, 4) for col, pct in missing_pct_by_column.items()
        },
        "missing_pct_by_column": missing_pct_by_column,
    }


def build_team_dataset(
    input_path: str | Path = "data/processed/base_data_engine.parquet",
    output_path: str | Path = "data/features/team_dataset.parquet",
    report_path: str | Path = "data/reports/team_dataset_quality_report.json",
    project_root: Optional[str | Path] = None,
) -> TeamDatasetBuildResult:
    configure_logging()
    started = time.perf_counter()
    root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
    input_file = resolve_path(input_path, root)
    output_file = resolve_path(output_path, root)
    report_file = resolve_path(report_path, root)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.parent.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Starting team dataset pipeline")
    LOGGER.info("Input dataset: %s", input_file)
    matches = load_base_dataset(input_file)
    LOGGER.info("Matches loaded: %s", len(matches))

    matches, missing_metrics = ensure_metric_columns(matches)
    LOGGER.info("Missing source metric columns filled with NaN: %s", missing_metrics)

    team_df = expand_matches_to_team_rows(matches)
    LOGGER.info("Expanded team rows: %s", len(team_df))

    team_df, features_created = add_rolling_features(team_df)
    LOGGER.info("Features created: %s", len(features_created))

    leakage_validation = validate_anti_leakage(team_df, features_created)
    if not leakage_validation.get("leakage_ok"):
        LOGGER.error("Anti-leakage validation failed: %s", leakage_validation.get("failures"))
        raise ValueError(f"Anti-leakage validation failed: {leakage_validation.get('failures')}")

    report = create_quality_report(team_df, features_created, missing_metrics, leakage_validation)
    safe_write_dataframe(team_df, output_file, index=False)
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    elapsed = time.perf_counter() - started
    missing_pct = float(team_df.isna().mean().mean() * 100) if not team_df.empty else 0.0
    LOGGER.info("Team dataset saved: %s", output_file)
    LOGGER.info("Quality report saved: %s", report_file)
    LOGGER.info("Unique teams: %s", team_df["team_key"].nunique())
    LOGGER.info("Average missing pct: %.2f%%", missing_pct)
    LOGGER.info("Execution time: %.3fs", elapsed)

    return TeamDatasetBuildResult(
        input_path=input_file,
        output_path=output_file,
        report_path=report_file,
        matches_loaded=int(len(matches)),
        rows_created=int(len(team_df)),
        unique_teams=int(team_df["team_key"].nunique()),
        unique_leagues=int(team_df["league"].nunique()),
        features_created=features_created,
        ignored_features=missing_metrics,
        leakage_ok=True,
        execution_time_seconds=round(elapsed, 4),
    )


if __name__ == "__main__":
    result = build_team_dataset()
    LOGGER.info("Team dataset build result: %s", json.dumps(result.__dict__, ensure_ascii=False, default=str))
