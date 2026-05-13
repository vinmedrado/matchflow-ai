from __future__ import annotations

FIELD_PRIORITY_RULES = {
    'corners': {'primary_source': 'flashscore', 'fallback_sources': [], 'overwrite_policy': 'never_overwrite_primary', 'quality_policy': 'rich_match_stat'},
    'shots': {'primary_source': 'flashscore', 'fallback_sources': [], 'overwrite_policy': 'never_overwrite_primary', 'quality_policy': 'rich_match_stat'},
    'shots_on_target': {'primary_source': 'flashscore', 'fallback_sources': [], 'overwrite_policy': 'never_overwrite_primary', 'quality_policy': 'rich_match_stat'},
    'xg': {'primary_source': 'flashscore', 'fallback_sources': [], 'overwrite_policy': 'never_overwrite_primary', 'quality_policy': 'rich_match_stat'},
    'score': {'primary_source': 'flashscore', 'fallback_sources': ['football_data_org'], 'overwrite_policy': 'fill_if_empty', 'quality_policy': 'core_result'},
    'match_date': {'primary_source': 'flashscore', 'fallback_sources': ['football_data_org'], 'overwrite_policy': 'fill_if_empty', 'quality_policy': 'fixture_metadata'},
    'league': {'primary_source': 'flashscore', 'fallback_sources': ['football_data_org'], 'overwrite_policy': 'fill_if_empty', 'quality_policy': 'competition_metadata'},
    'odds_home': {'primary_source': 'flashscore', 'fallback_sources': ['the_odds_api'], 'overwrite_policy': 'fill_if_empty', 'quality_policy': 'market_odds'},
    'odds_draw': {'primary_source': 'flashscore', 'fallback_sources': ['the_odds_api'], 'overwrite_policy': 'fill_if_empty', 'quality_policy': 'market_odds'},
    'odds_away': {'primary_source': 'flashscore', 'fallback_sources': ['the_odds_api'], 'overwrite_policy': 'fill_if_empty', 'quality_policy': 'market_odds'},
    'odds_over_25': {'primary_source': 'flashscore', 'fallback_sources': ['the_odds_api'], 'overwrite_policy': 'fill_if_empty', 'quality_policy': 'market_odds'},
    'season': {'primary_source': 'flashscore', 'fallback_sources': ['football_data_org'], 'overwrite_policy': 'fill_if_empty', 'quality_policy': 'season_metadata'},
}

def get_rule(field: str) -> dict:
    return FIELD_PRIORITY_RULES.get(field, {'primary_source': 'flashscore', 'fallback_sources': ['football_data_org','the_odds_api'], 'overwrite_policy': 'fill_if_empty', 'quality_policy': 'generic'})
