from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pandas as pd

from backend.core.cache import file_cache
from backend.core.config import get_settings, resolve_project_path
from backend.core.logging_config import get_logger

logger = get_logger("matchflow.dataset_service")


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_local_path(relative_or_absolute: str | Path) -> Path:
    path = Path(relative_or_absolute)
    if path.is_absolute():
        return path
    return project_root() / path


def dataset_path() -> Path:
    settings = get_settings()
    return resolve_project_path(settings["data"]["processed_dataset_path"])


def team_dataset_path() -> Path:
    return resolve_local_path("data/features/team_dataset.parquet")


def _date_range(df: pd.DataFrame) -> Dict[str, Any] | None:
    if "date" not in df.columns:
        return None
    dates = pd.to_datetime(df["date"], errors="coerce")
    valid_dates = dates.dropna()
    if valid_dates.empty:
        return {"min": None, "max": None}
    return {"min": str(valid_dates.min().date()), "max": str(valid_dates.max().date())}


def _team_count_from_match_dataset(df: pd.DataFrame) -> int:
    teams: set[str] = set()
    if "home_team_key" in df.columns:
        teams.update(df["home_team_key"].dropna().astype(str).tolist())
    if "away_team_key" in df.columns:
        teams.update(df["away_team_key"].dropna().astype(str).tolist())
    return len(teams)


def get_dataset_summary() -> Dict[str, Any]:
    path = dataset_path()
    df, cache_meta = file_cache.get_parquet("base_dataset", path)
    if df is None:
        logger.warning("Dataset ausente ou inválido: %s", path)
        return {
            "available": False,
            "file_exists": path.exists(),
            "total_records": 0,
            "total_rows": 0,
            "total_leagues": 0,
            "total_teams": 0,
            "date_range": None,
            "columns": [],
            "path": str(path),
            "message": f"Dataset not found or invalid: {path}",
            "cache": cache_meta,
        }

    logger.info("Dataset carregado para resumo: linhas=%s colunas=%s path=%s", len(df), len(df.columns), path)
    summary = {
        "available": True,
        "file_exists": True,
        "total_records": int(len(df)),
        "total_rows": int(len(df)),
        "total_leagues": int(df["league"].nunique()) if "league" in df.columns else 0,
        "total_teams": _team_count_from_match_dataset(df),
        "date_range": _date_range(df),
        "columns": list(df.columns),
        "path": str(path),
        "cache": cache_meta,
    }
    return summary


def dataset_summary(path: str | Path = "data/processed/base_data_engine.parquet") -> Dict[str, Any]:
    dataset_file = resolve_local_path(path)
    df, cache_meta = file_cache.get_parquet(f"dataset_summary:{dataset_file}", dataset_file)
    if df is None:
        logger.warning("Dataset summary fallback: arquivo ausente ou inválido em %s", dataset_file)
        return {
            "available": False,
            "file_exists": dataset_file.exists(),
            "total_records": 0,
            "total_rows": 0,
            "total_leagues": 0,
            "total_teams": 0,
            "date_range": None,
            "columns": [],
            "message": f"Dataset not found or invalid: {dataset_file}",
            "cache": cache_meta,
        }
    logger.info("Resumo do dataset calculado: linhas=%s colunas=%s", len(df), len(df.columns))
    return {
        "available": True,
        "file_exists": True,
        "total_records": int(len(df)),
        "total_rows": int(len(df)),
        "total_leagues": int(df["league"].nunique()) if "league" in df.columns else 0,
        "total_teams": _team_count_from_match_dataset(df),
        "date_range": _date_range(df),
        "columns": list(df.columns),
        "cache": cache_meta,
    }


def team_dataset_summary(path: str | Path = "data/features/team_dataset.parquet") -> Dict[str, Any]:
    dataset_file = resolve_local_path(path)
    df, cache_meta = file_cache.get_parquet(f"team_dataset_summary:{dataset_file}", dataset_file)
    if df is None:
        logger.warning("Team dataset ausente ou inválido: %s", dataset_file)
        return {
            "available": False,
            "file_exists": dataset_file.exists(),
            "total_rows": 0,
            "total_teams": 0,
            "total_leagues": 0,
            "date_range": None,
            "features_count": 0,
            "message": f"Team dataset not found or invalid: {dataset_file}",
            "cache": cache_meta,
        }
    if dataset_file.exists() and dataset_file.stat().st_size == 0 and df.empty:
        logger.warning("Team dataset existe, mas está vazio: %s", dataset_file)
        return {
            "available": False,
            "file_exists": True,
            "total_rows": 0,
            "total_teams": 0,
            "total_leagues": 0,
            "date_range": None,
            "features_count": 0,
            "message": "Team dataset exists but is empty.",
            "cache": cache_meta,
        }
    technical_columns = {
        "event_id", "match_key", "date", "league", "season", "source_file", "source_layer",
        "team_key", "team_name", "opponent_key", "opponent_name", "side", "result_ft", "result_ht",
    }
    features_count = len([col for col in df.columns if col not in technical_columns])
    logger.info("Resumo team dataset calculado: linhas=%s features=%s", len(df), features_count)
    return {
        "available": True,
        "file_exists": True,
        "total_rows": int(len(df)),
        "total_teams": int(df["team_key"].nunique()) if "team_key" in df.columns else 0,
        "total_leagues": int(df["league"].nunique()) if "league" in df.columns else 0,
        "date_range": _date_range(df),
        "features_count": int(features_count),
        "columns": list(df.columns),
        "cache": cache_meta,
    }

def advanced_dataset_path() -> Path:
    return resolve_local_path("data/features/team_dataset_advanced.parquet")


def advanced_dataset_summary(path: str | Path = "data/features/team_dataset_advanced.parquet") -> Dict[str, Any]:
    dataset_file = resolve_local_path(path)
    df, cache_meta = file_cache.get_parquet(f"advanced_dataset_summary:{dataset_file}", dataset_file)
    if df is None:
        logger.warning("Advanced team dataset ausente ou inválido: %s", dataset_file)
        return {
            "available": False,
            "file_exists": dataset_file.exists(),
            "total_rows": 0,
            "total_teams": 0,
            "total_leagues": 0,
            "date_range": None,
            "features_count": 0,
            "advanced_features_count": 0,
            "message": f"Advanced team dataset not found or invalid: {dataset_file}",
            "cache": cache_meta,
        }

    technical_columns = {
        "event_id", "match_key", "date", "league", "season", "source_file", "source_layer",
        "team_key", "team_name", "opponent_key", "opponent_name", "side", "result_ft", "result_ht",
    }
    advanced_feature_prefixes = (
        "win_streak", "loss_streak", "unbeaten_streak", "points_last_5", "points_trend",
        "goals_std", "shots_std", "corners_std", "goals_vs_", "shots_vs_", "corners_vs_",
        "goals_per_", "shots_on_target_ratio", "pressure_", "home_", "away_",
        "attack_vs_", "team_attack", "opponent_defense", "goal_trend",
        "expected_goals_proxy", "corners_trend", "high_", "low_conversion",
    )
    features = [col for col in df.columns if col not in technical_columns]
    advanced_features = [
        col for col in df.columns
        if any(str(col).startswith(prefix) for prefix in advanced_feature_prefixes)
    ]
    logger.info(
        "Resumo advanced dataset calculado: linhas=%s features=%s advanced_features=%s",
        len(df),
        len(features),
        len(advanced_features),
    )
    return {
        "available": True,
        "file_exists": True,
        "total_rows": int(len(df)),
        "total_teams": int(df["team_key"].nunique()) if "team_key" in df.columns else 0,
        "total_leagues": int(df["league"].nunique()) if "league" in df.columns else 0,
        "date_range": _date_range(df),
        "features_count": int(len(features)),
        "advanced_features_count": int(len(advanced_features)),
        "columns": list(df.columns),
        "cache": cache_meta,
    }

