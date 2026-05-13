from pathlib import Path

from backend.services.data_engine.providers.flashscore.client import FlashScoreClient
from backend.services.data_engine.providers.flashscore.network_capture import classify_response, build_capture_record, is_relevant_response
from backend.services.data_engine.providers.flashscore.parser import parse_odds_from_markets, parse_stats_from_pairs, parse_matches
from backend.services.data_engine.providers.flashscore.state_manager import update_after_sync

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "flashscore"
LEAGUE = {"league_name": "Premier League", "league_slug": "premier-league", "season": "2025"}


def _load(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_network_capture_classifies_relevant_responses():
    assert is_relevant_response("https://global.flashscore.ninja/event/abc/odds", "xhr", 200)
    assert classify_response("https://global.flashscore.ninja/event/abc/odds", body_sample="odds bookmakers") == "odds"
    rec = build_capture_record("https://global.flashscore.ninja/event/abc/statistics", 200, "application/json", "{}")
    assert rec.response_type == "stats"
    assert rec.sanitized()["url"].startswith("https://")


def test_parser_extracts_fixture_json_without_browser():
    rows = FlashScoreClient(use_demo=False)._parse_network_payload(_load("fixture_matches_sample.json"), LEAGUE, max_rows=10)
    assert rows[0]["flashscore_match_id"] == "abc123XY"
    assert rows[0]["home_team"] == "Arsenal"
    assert rows[0]["away_team"] == "Chelsea"
    assert rows[0]["goals_home_ft"] == 2
    assert rows[0]["status"] == "FINISHED"


def test_parser_extracts_odds_stats_and_events_json():
    odds = FlashScoreClient(use_demo=False)._parse_network_payload(_load("fixture_odds_sample.json"), LEAGUE, max_rows=10)[0]
    stats = FlashScoreClient(use_demo=False)._parse_network_payload(_load("fixture_stats_sample.json"), LEAGUE, max_rows=10)[0]
    events = FlashScoreClient(use_demo=False)._parse_network_payload(_load("fixture_events_sample.json"), LEAGUE, max_rows=10)[0]
    assert odds["odds_home"] == 1.90
    assert odds["odds_over_05"] == 1.08
    assert odds["odds_over_15"] == 1.30
    assert odds["odds_over_25"] == 1.80
    assert odds["odds_btts_yes"] == 1.75
    assert stats["corners_home"] == 5
    assert stats["shots_home"] == 14
    assert stats["shots_on_target_home"] == 6
    assert stats["xg_home"] == 1.82
    assert events["goal_minutes_home"] == [12, 88]
    assert events["goal_minutes_away"] == [54]


def test_missing_fields_are_null_and_warned():
    row = parse_matches([{"home_team": "Arsenal", "away_team": "Chelsea", "league": "Premier League", "match_date": "2026-05-10"}])[0]
    assert row["odds_home"] is None
    assert row["corners_home"] is None
    assert "optional_fields_missing" in row["provider_warnings"]
    assert row["flashscore_match_id"].startswith("fallback_")
    assert "fallback_provider_match_id_generated" in row["provider_warnings"]


def test_retry_state_records_failures(tmp_path, monkeypatch):
    import backend.services.data_engine.providers.flashscore.state_manager as sm
    monkeypatch.setattr(sm, "STATE_PATH", tmp_path / "flashscore_state.json")
    state = update_after_sync(
        processed_leagues=["premier-league"], processed_matches=["abc123XY"], failed_leagues=["serie-a"],
        failed_matches=["missing-detail"], test_mode=True, batch_size=1, start_date="2023-01-01", end_date="yesterday",
        mode="internal", provider_status="degraded", last_error="timeout", provider_health="degraded",
    )
    assert state["failed_leagues"] == ["serie-a"]
    assert state["failed_matches"] == ["missing-detail"]
    assert state["retry_count"] >= 1
    assert state["provider_health"] == "degraded"


def test_parser_helpers_keep_nulls_for_absent_odds_stats():
    assert parse_odds_from_markets({})["odds_home"] is None
    assert parse_stats_from_pairs({})["xg_home"] is None
