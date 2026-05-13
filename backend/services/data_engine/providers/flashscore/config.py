from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class FlashScoreConfig:
    enabled: bool
    use_demo: bool
    headless: bool
    test_mode: bool
    max_leagues: int | None
    start_date: str
    end_date: str
    sleep_seconds: float
    timeout_seconds: int
    batch_size: int
    data_engine_mode: str
    primary_provider: str
    real_provider_enabled: bool


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "y", "on"}


def _int_or_none(raw: str) -> int | None:
    raw = str(raw).strip()
    return None if raw in {"", "0", "none", "None", "null"} else int(raw)


def get_flashscore_config() -> FlashScoreConfig:
    mode = os.getenv("DATA_ENGINE_MODE", "internal").strip().lower()
    use_demo = _bool("FLASHSCORE_USE_DEMO", False) or mode == "demo"
    raw_max = os.getenv("FLASHSCORE_MAX_LEAGUES", "5")
    return FlashScoreConfig(
        enabled=_bool("FLASHSCORE_ENABLED", True),
        use_demo=use_demo,
        headless=_bool("FLASHSCORE_HEADLESS", True),
        test_mode=_bool("FLASHSCORE_TEST_MODE", True),
        max_leagues=_int_or_none(raw_max),
        start_date=os.getenv("FLASHSCORE_START_DATE", "2023-01-01"),
        end_date=os.getenv("FLASHSCORE_END_DATE", "yesterday"),
        sleep_seconds=float(os.getenv("FLASHSCORE_SLEEP_SECONDS", "0.5")),
        timeout_seconds=int(os.getenv("FLASHSCORE_TIMEOUT_SECONDS", "30")),
        batch_size=int(os.getenv("FLASHSCORE_BATCH_SIZE", "20")),
        data_engine_mode=mode,
        primary_provider=os.getenv("DATA_ENGINE_PRIMARY_PROVIDER", "flashscore"),
        real_provider_enabled=(mode == "internal" and not use_demo and _bool("FLASHSCORE_ENABLED", True)),
    )


def provider_root() -> Path:
    return Path(__file__).resolve().parent


def project_root() -> Path:
    return Path(__file__).resolve().parents[5]
