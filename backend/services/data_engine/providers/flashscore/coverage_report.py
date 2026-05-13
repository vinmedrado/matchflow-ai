from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

TRACKED_FIELDS = [
    "odds_home", "odds_draw", "odds_away", "odds_over_05", "odds_under_05",
    "odds_over_15", "odds_under_15", "odds_over_25", "odds_under_25", "odds_btts_yes", "odds_btts_no",
    "corners_home", "corners_away", "shots_home", "shots_away", "shots_on_target_home", "shots_on_target_away",
    "xg_home", "xg_away", "goal_minutes_home", "goal_minutes_away",
]

def project_root() -> Path:
    return Path(__file__).resolve().parents[5]

def _pct(part: int, total: int) -> float:
    return round((part / total) * 100, 2) if total else 0.0

def _load_matches(root: Path) -> pd.DataFrame:
    parquet = root / "data/raw/flashscore_matches.parquet"
    csv = root / "data/raw/flashscore_matches.csv"
    if parquet.exists():
        try:
            return safe_read_dataframe(parquet)
        except Exception:
            pass
    if csv.exists():
        try:
            return pd.read_csv(csv)
        except Exception:
            pass
    return pd.DataFrame()

def build_flashscore_coverage_report(root: Path | None = None) -> dict[str, Any]:
    root = Path(root) if root else project_root()
    df = _load_matches(root)
    total = int(len(df))
    def has_any(cols: list[str]) -> int:
        existing = [c for c in cols if c in df.columns]
        if not existing or df.empty:
            return 0
        return int(df[existing].notna().any(axis=1).sum())
    missing = {}
    for field in TRACKED_FIELDS:
        missing[field] = int(df[field].isna().sum()) if field in df.columns else total
    warnings: list[str] = []
    if total == 0:
        warnings.append("coverage_unavailable_no_flashscore_output")
    odds_count = has_any([c for c in TRACKED_FIELDS if c.startswith("odds_")])
    stats_count = has_any(["corners_home", "shots_home", "shots_on_target_home", "xg_home"])
    xg_count = has_any(["xg_home", "xg_away"])
    corners_count = has_any(["corners_home", "corners_away"])
    shots_count = has_any(["shots_home", "shots_away", "shots_on_target_home", "shots_on_target_away"])
    events_count = has_any(["goal_minutes_home", "goal_minutes_away"])
    low_quality = []
    if not df.empty:
        score_col = "final_data_quality_score" if "final_data_quality_score" in df.columns else "data_quality_score" if "data_quality_score" in df.columns else None
        if score_col:
            subset = df[df[score_col].fillna(0) < 0.6].head(50)
            low_quality = subset[[c for c in ["match_id", "flashscore_match_id", "league", "home_team", "away_team", score_col, "provider_warnings"] if c in subset.columns]].to_dict(orient="records")
    report = {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": "flashscore",
        "total_matches": total,
        "matches_with_odds": odds_count,
        "matches_with_stats": stats_count,
        "matches_with_xg": xg_count,
        "matches_with_corners": corners_count,
        "matches_with_shots": shots_count,
        "matches_with_events": events_count,
        "odds_coverage_pct": _pct(odds_count, total),
        "stats_coverage_pct": _pct(stats_count, total),
        "xg_coverage_pct": _pct(xg_count, total),
        "corners_coverage_pct": _pct(corners_count, total),
        "field_missing_summary": missing,
        "provider_warnings": warnings,
        "low_quality_matches": low_quality,
    }
    out = root / "data/reports/flashscore_coverage_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return report
