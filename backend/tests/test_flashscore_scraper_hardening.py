from backend.services.data_engine.providers.flashscore.parser import (
    extract_match_id,
    parse_score,
    parse_text_rows,
    parse_odds_from_markets,
    parse_stats_from_pairs,
)
from backend.services.data_engine.providers.flashscore.client import FlashScoreClient


def test_parser_extracts_match_id_score_and_teams():
    assert extract_match_id('https://www.flashscore.com/match/abc123XY/#/match-summary') == 'abc123XY'
    assert parse_score('2-1 (1-0)') == {
        'goals_home_ft': 2,
        'goals_away_ft': 1,
        'goals_home_ht': 1,
        'goals_away_ht': 0,
    }
    rows = parse_text_rows('Tomorrow\n18:00\nManchester United\nManchester City\n', {'league_name': 'Premier League', 'league_slug': 'premier-league'}, max_rows=5)
    assert rows and rows[0]['home_team'] == 'Manchester United'
    assert rows[0]['away_team'] == 'Manchester City'
    assert rows[0]['is_demo_data'] is False


def test_odds_and_stats_missing_are_null_safe():
    odds = parse_odds_from_markets({})
    stats = parse_stats_from_pairs({})
    assert odds['odds_home'] is None
    assert odds['odds_over_25'] is None
    assert stats['shots_home'] is None
    parsed_odds = parse_odds_from_markets({'1x2': ['1.91', '3.40', '4.20'], 'Over/Under 2.5': ['1.80', '2.00']})
    assert parsed_odds['odds_home'] == 1.91
    assert parsed_odds['odds_over_25'] == 1.80


def test_demo_only_when_client_configured():
    league = {'league_name': 'Premier League', 'league_slug': 'premier-league'}
    demo = FlashScoreClient(use_demo=True).fetch_league_matches(league, test_mode=True)
    assert demo and demo[0]['is_demo_data'] is True
    assert demo[0]['source'] == 'demo'


def test_network_structured_payload_parser():
    client = FlashScoreClient(use_demo=False)
    payload = '{"events":[{"id":"abc123XY","home":"Arsenal","away":"Chelsea","score":"2-1 (1-0)","markets":{"1x2":["1.9","3.5","4.2"]},"stats":{"Corners":["5","4"]}}]}'
    rows = client._parse_network_payload(payload, {'league_name': 'Premier League', 'league_slug': 'premier-league'}, max_rows=5)
    assert rows[0]['flashscore_match_id'] == 'abc123XY'
    assert rows[0]['goals_home_ft'] == 2
    assert rows[0]['odds_home'] == 1.9
    assert rows[0]['corners_home'] == 5
