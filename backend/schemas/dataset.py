from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel


class DatasetSummary(BaseModel):
    available: bool
    total_records: int
    total_leagues: int
    total_teams: int
    date_min: Optional[str]
    date_max: Optional[str]
    columns: List[str]
