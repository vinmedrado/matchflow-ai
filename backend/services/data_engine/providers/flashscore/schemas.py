from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

@dataclass
class FlashScoreLeague:
    league_slug: str
    league_name: str
    country: str = ""
    season: str = "2023+"
    enabled: bool = True
    provider: str = "flashscore"
    priority: int = 1
    canonical_league_id: str | None = None
    url: str | None = None

@dataclass
class FlashScoreMatch:
    flashscore_match_id: str
    provider: str
    source: str
    is_demo_data: bool
    league: str
    season: str
    match_date: str
    kickoff_time: str
    home_team: str
    away_team: str
    status: str = "SCHEDULED"
    goals_home_ft: int | None = None
    goals_away_ft: int | None = None
    goals_home_ht: int | None = None
    goals_away_ht: int | None = None
    corners_home: int | None = None
    corners_away: int | None = None
    shots_home: int | None = None
    shots_away: int | None = None
    shots_on_target_home: int | None = None
    shots_on_target_away: int | None = None
    xg_home: float | None = None
    xg_away: float | None = None
    odds_home: float | None = None
    odds_draw: float | None = None
    odds_away: float | None = None
    odds_over_25: float | None = None
    odds_under_25: float | None = None
    odds_btts_yes: float | None = None
    odds_btts_no: float | None = None
    provider_warnings: str = ""
    data_quality_score: float | None = None
    fetched_at: str = ""

    @property
    def match_id(self) -> str:
        return self.flashscore_match_id

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["match_id"] = self.flashscore_match_id
        if not data.get("fetched_at"):
            data["fetched_at"] = datetime.now(timezone.utc).isoformat()
        return data
