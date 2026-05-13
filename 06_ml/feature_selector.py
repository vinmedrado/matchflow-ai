from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

try:
    from backend.core.logging_config import get_logger
except Exception:  # pragma: no cover
    import logging
    logging.basicConfig(level=logging.INFO)
    def get_logger(name: str):
        return logging.getLogger(name)

logger = get_logger("matchflow.ml.feature_selector")

EXCLUDED_COLUMNS = {
    "event_id", "match_key", "date", "league", "season", "source_file", "source_layer",
    "team_key", "team_name", "opponent_key", "opponent_name", "side",
    "home_team", "away_team", "home_team_key", "away_team_key",
    "target_match_date", "target_league", "target_opponent_key", "target_side",
    "ml_target_horizon_matches", "ml_research_only", "ml_leakage_guard",
    "result_ft", "result_ht",
    "goals_for_ft", "goals_against_ft", "total_goals_ft",
    "goals_for_ht", "goals_against_ht", "total_goals_ht",
    "shots_for", "shots_against", "shots_on_target_for", "shots_on_target_against",
    "corners_for", "corners_against", "points", "is_win", "is_draw", "is_loss",
}
LEAKAGE_PREFIXES = ("target_", "current_target_")
SAFE_PATTERNS = (
    "last_", "_avg_last_", "_std_last_", "_rate_avg_last_", "rolling_", "lag_",
    "_trend", "_streak", "_vs_league_avg", "pressure_avg", "team_attack_strength",
    "opponent_defense_weakness", "attack_vs_defense_ratio", "expected_goals_proxy",
    "high_corner_flag", "high_shots_flag", "low_conversion_flag", "consistency", "strength"
)

class FeatureSelector:
    def __init__(self, project_root: Path, config: Dict[str, Any]) -> None:
        self.project_root = project_root
        self.config = config
        self.correlation_threshold = float(config.get("correlation_threshold", 0.95))
        self.max_missing_pct = float(config.get("max_missing_pct", 0.60))
        self.output_path = self.project_root / "data/ml/datasets/selected_features.json"
        self.report_path = self.project_root / "data/ml/datasets/feature_selection_report.json"

    def select(self, df: pd.DataFrame, target_col: str) -> List[str]:
        logger.info("Selecionando features ML leakage-safe para target=%s", target_col)
        usable = df[df[target_col].notna()].copy()
        numeric_cols = [
            col for col in usable.columns
            if self._is_candidate_column(usable, col)
        ]
        valid_cols, rejected = self._filter_quality(usable, numeric_cols)
        selected, dropped_corr = self._drop_highly_correlated(usable[valid_cols]) if valid_cols else ([], [])
        self._save_selection(target_col, selected, rejected, dropped_corr)
        logger.info("Features selecionadas para %s: %s | rejeitadas=%s | corr_drop=%s", target_col, len(selected), len(rejected), len(dropped_corr))
        return selected

    def _is_candidate_column(self, df: pd.DataFrame, col: str) -> bool:
        if col in EXCLUDED_COLUMNS or col.startswith(LEAKAGE_PREFIXES):
            return False
        if not pd.api.types.is_numeric_dtype(df[col]):
            return False
        return any(pattern in col for pattern in SAFE_PATTERNS)

    def _filter_quality(self, df: pd.DataFrame, cols: List[str]) -> Tuple[List[str], Dict[str, str]]:
        valid: List[str] = []
        rejected: Dict[str, str] = {}
        min_non_null = max(4, int(len(df) * (1 - self.max_missing_pct)))
        for col in cols:
            series = pd.to_numeric(df[col], errors="coerce")
            if series.notna().sum() < min_non_null:
                rejected[col] = "too_many_missing"
                continue
            if series.nunique(dropna=True) <= 1:
                rejected[col] = "constant_or_single_value"
                continue
            valid.append(col)
        return valid, rejected

    def _drop_highly_correlated(self, frame: pd.DataFrame) -> Tuple[List[str], List[str]]:
        if frame.empty or frame.shape[1] <= 1:
            return list(frame.columns), []
        filled = frame.copy()
        for col in filled.columns:
            filled[col] = pd.to_numeric(filled[col], errors="coerce")
        filled = filled.fillna(filled.median(numeric_only=True))
        corr = filled.corr().abs()
        upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
        to_drop = [column for column in upper.columns if any(upper[column] > self.correlation_threshold)]
        selected = [col for col in frame.columns if col not in set(to_drop)]
        return selected, to_drop

    def _save_selection(self, target_col: str, selected: List[str], rejected: Dict[str, str], dropped_corr: List[str]) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        payload: Dict[str, Any] = {}
        if self.output_path.exists():
            try:
                payload = json.loads(self.output_path.read_text(encoding="utf-8"))
            except Exception:
                payload = {}
        payload[target_col] = selected
        self.output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        report: Dict[str, Any] = {}
        if self.report_path.exists():
            try:
                report = json.loads(self.report_path.read_text(encoding="utf-8"))
            except Exception:
                report = {}
        report[target_col] = {
            "selected_count": len(selected),
            "selected_features": selected,
            "rejected": rejected,
            "dropped_high_correlation": dropped_corr,
            "correlation_threshold": self.correlation_threshold,
            "max_missing_pct": self.max_missing_pct,
            "leakage_policy": "Only numeric historical/rolling/lagged features with SAFE_PATTERNS are eligible. Targets/current outcomes are excluded."
        }
        self.report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
