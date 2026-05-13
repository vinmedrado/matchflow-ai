from __future__ import annotations
import os
from pathlib import Path
import pandas as pd

from backend.services.data_engine.normalization.text_normalizer import normalize_text, canonical_slug
from backend.services.data_engine.normalization.entity_mapper import EntityMapper
from backend.services.data_engine.normalization.deduplication_engine import deduplicate_matches
from backend.services.data_engine.enrichment.enrichment_engine import enrich_record
from backend.services.data_engine.enrichment.data_quality_engine import score_dataframe
from backend.services.data_engine.consolidation import canonicalize_matches, filter_ml_eligible


def test_text_normalization_examples():
    assert normalize_text('São Paulo FC') == 'sao paulo'
    assert normalize_text('Manchester Utd') == 'manchester united'
    assert normalize_text('Atlético-MG') == 'atletico mineiro'
    assert normalize_text('PSG') == 'paris saint germain'


def test_rapidfuzz_matching_known_aliases(tmp_path):
    mapper = EntityMapper(tmp_path)
    result = mapper.map_entity('Manchester United FC', 'team', 'football_data_org')
    assert result['canonical_id'] == 'manchester_united'
    assert result['needs_review'] is False


def test_known_alias_exact_match(tmp_path):
    mapper = EntityMapper(tmp_path)
    first = mapper.map_entity('Man Utd', 'team', 'flashscore')
    second = mapper.map_entity('Manchester United', 'team', 'odds_api')
    assert first['canonical_id'] == second['canonical_id'] == 'manchester_united'


def test_manchester_united_not_confused_with_city(tmp_path):
    mapper = EntityMapper(tmp_path)
    united = mapper.map_entity('Manchester United', 'team', 'flashscore')
    city = mapper.map_entity('Manchester City', 'team', 'flashscore')
    assert united['canonical_id'] != city['canonical_id']


def test_inter_milan_not_confused_with_inter_miami(tmp_path):
    mapper = EntityMapper(tmp_path)
    milan = mapper.map_entity('Inter Milan', 'team', 'flashscore')
    miami = mapper.map_entity('Inter Miami', 'team', 'odds_api')
    assert milan['canonical_id'] == 'internazionale'
    assert miami['canonical_id'] == 'inter_miami'


def test_sao_paulo_and_atletico_mg_map_correctly(tmp_path):
    mapper = EntityMapper(tmp_path)
    assert mapper.map_entity('São Paulo FC', 'team', 'flashscore')['canonical_id'] == 'sao_paulo'
    assert mapper.map_entity('Atlético-MG', 'team', 'football_data_org')['canonical_id'] == 'atletico_mineiro'


def test_epl_maps_to_premier_league(tmp_path):
    mapper = EntityMapper(tmp_path)
    assert mapper.map_entity('EPL', 'league', 'football_data_org')['canonical_id'] == 'premier_league'


def test_deduplicate_same_match_between_providers(tmp_path):
    df = pd.DataFrame([
        {'match_identity_key':'premier|manu|manc|2026-05-10|2025','source':'flashscore','match_id':'fs1','match_date':'2026-05-10','kickoff_time':'18:00'},
        {'match_identity_key':'premier|manu|manc|2026-05-10|2025','source':'football_data_org','match_id':'fd1','match_date':'2026-05-10','kickoff_time':'19:00'},
    ])
    out, report = deduplicate_matches(df, tmp_path)
    assert len(out) == 1
    assert report['duplicates_removed'] == 1


def test_date_conflict_generates_warning(tmp_path):
    df = pd.DataFrame([
        {'match_identity_key':'x','source':'flashscore','match_id':'fs1','match_date':'2026-05-10','kickoff_time':'18:00'},
        {'match_identity_key':'x','source':'football_data_org','match_id':'fd1','match_date':'2026-05-12','kickoff_time':'18:00'},
    ])
    _, report = deduplicate_matches(df, tmp_path)
    assert report['conflicts'] >= 1


def test_secondary_source_does_not_overwrite_flashscore():
    primary = {'source':'flashscore','odds_home':1.9,'corners':10,'source_used':'flashscore'}
    out = enrich_record(primary, {'odds_home':2.1,'corners':3,'season':'2026'}, 'the_odds_api')
    assert out['odds_home'] == 1.9
    assert out['corners'] == 10


def test_odds_api_fills_empty_odd():
    out = enrich_record({'source':'flashscore','odds_home':None,'source_used':'flashscore'}, {'odds_home':2.05}, 'the_odds_api')
    assert out['odds_home'] == 2.05


def test_football_data_fills_empty_metadata():
    out = enrich_record({'source':'flashscore','season':None,'source_used':'flashscore'}, {'season':'2025'}, 'football_data_org')
    assert out['season'] == '2025'


def test_ml_filter_excludes_blocked_records():
    df = pd.DataFrame([{'match_id':'a','data_quality_band':'blocked'}, {'match_id':'b','data_quality_band':'high_quality'}])
    out = filter_ml_eligible(df)
    assert out['match_id'].tolist() == ['b']


def test_decision_engine_dedup_supports_match_identity(tmp_path):
    df = pd.DataFrame([
        {'league':'Premier League','home_team':'Man Utd','away_team':'Manchester City','match_date':'2026-05-10','season':'2025','source':'flashscore','match_id':'1'},
        {'league':'EPL','home_team':'Manchester United FC','away_team':'Man City','match_date':'2026-05-10','season':'2025','source':'football_data_org','match_id':'2'},
    ])
    out, report = canonicalize_matches(df, tmp_path)
    assert len(out) == 1
    assert report['duplicates_removed'] == 1


def test_low_quality_reduces_confidence_or_marks_review(tmp_path):
    df = pd.DataFrame([{'league':'Unknown League','home_team':'Team A','away_team':'Team B','match_date':'','source':'unknown'}])
    out, _ = canonicalize_matches(df, tmp_path)
    assert out.iloc[0]['data_quality_band'] in {'low_quality','review_required','blocked','medium_quality'}
    assert out.iloc[0]['data_quality_score'] <= 0.82


def test_unresolved_entities_report_created(tmp_path):
    mapper = EntityMapper(tmp_path)
    mapper.map_entity('ZZZ Very Unknown Club 123', 'team', 'unknown_provider')
    assert (tmp_path/'backend/services/data_engine/audit/unresolved_entities.json').exists()


def test_groq_not_called_when_rapidfuzz_high(tmp_path, monkeypatch):
    monkeypatch.setenv('ENTITY_RESOLUTION_USE_LLM', 'true')
    mapper = EntityMapper(tmp_path)
    res = mapper.map_entity('Manchester United', 'team', 'football_data_org')
    assert res['method'] in {'alias','normalized_exact','rapidfuzz_auto'}


def test_groq_optional_safe_for_low_score(tmp_path, monkeypatch):
    monkeypatch.setenv('ENTITY_RESOLUTION_USE_LLM', 'true')
    mapper = EntityMapper(tmp_path)
    res = mapper.map_entity('Completely Unknown FC XYZ', 'team', 'weird_provider')
    assert res['needs_review'] is True
    assert (tmp_path/'backend/services/data_engine/storage/entity_resolution_cache.json').exists()


def test_pipeline_canonicalization_columns(tmp_path):
    df = pd.DataFrame([{'league':'EPL','home_team':'Man Utd','away_team':'Manchester City','match_date':'2026-05-10','season':'2025','source':'flashscore','match_id':'fs1'}])
    out, report = canonicalize_matches(df, tmp_path)
    assert {'canonical_home_team_id','canonical_league_id','match_identity_key','data_quality_score'}.issubset(out.columns)
    assert report['total_output'] == 1
