from __future__ import annotations
from pathlib import Path
import json
import pandas as pd
from .normalization.entity_mapper import EntityMapper
from .normalization.match_identity_resolver import resolve_match_identity
from .normalization.deduplication_engine import deduplicate_matches
from .enrichment.data_quality_engine import score_dataframe


def canonicalize_matches(df: pd.DataFrame, root: Path | None = None, *, persist_reports: bool = True) -> tuple[pd.DataFrame, dict]:
    root = Path(root) if root else Path(__file__).resolve().parents[3]
    if df.empty:
        return df, {'total_input': 0, 'total_output': 0, 'duplicates_removed': 0, 'unresolved_entities': 0}
    mapper = EntityMapper(root)
    rows=[]; mapping_rows=[]
    for rec in df.to_dict('records'):
        provider = str(rec.get('source') or 'unknown')
        league = mapper.map_entity(str(rec.get('league') or ''), 'league', provider, context={'season': rec.get('season')})
        home = mapper.map_entity(str(rec.get('home_team') or rec.get('Home') or ''), 'team', provider, context={'league': rec.get('league')})
        away = mapper.map_entity(str(rec.get('away_team') or rec.get('Away') or ''), 'team', provider, context={'league': rec.get('league')})
        rec.update({
            'canonical_league_id': league['canonical_id'], 'canonical_league_name': league['canonical_name'],
            'canonical_home_team_id': home['canonical_id'], 'canonical_home_team_name': home['canonical_name'],
            'canonical_away_team_id': away['canonical_id'], 'canonical_away_team_name': away['canonical_name'],
            'mapping_confidence': round(min(league['score'], home['score'], away['score']) / 100.0, 3),
            'mapping_needs_review': bool(league['needs_review'] or home['needs_review'] or away['needs_review']),
        })
        identity = resolve_match_identity(rec); rec.update(identity)
        if rec['mapping_needs_review']:
            rec['conflict_flags'] = '|'.join([str(rec.get('conflict_flags') or ''), 'mapping_review_required']).strip('|')
        rec['provider_match_ids'] = json.dumps(identity.get('provider_match_ids', {}), ensure_ascii=False) if isinstance(identity.get('provider_match_ids'), dict) else identity.get('provider_match_ids')
        rec['linked_sources'] = '|'.join(identity.get('linked_sources', [])) if isinstance(identity.get('linked_sources'), list) else identity.get('linked_sources')
        rows.append(rec)
        mapping_rows.extend([league, home, away])
    out = pd.DataFrame(rows)
    out, dedup_report = deduplicate_matches(out, root)
    out = score_dataframe(out, root)
    if persist_reports:
        reports = root / 'data/reports'; reports.mkdir(parents=True, exist_ok=True)
        mapping_report = {'total_mappings': len(mapping_rows), 'review_required': sum(1 for x in mapping_rows if x.get('needs_review')), 'low_confidence': sum(1 for x in mapping_rows if x.get('confidence_band') == 'low'), 'samples': mapping_rows[:25]}
        (reports/'entity_mapping_report.json').write_text(json.dumps(mapping_report, indent=2, ensure_ascii=False), encoding='utf-8')
        # mirror audit files into data/reports for ops endpoints
        audit = root/'backend/services/data_engine/audit'
        conflicts = json.loads((audit/'conflicts_report.json').read_text(encoding='utf-8')) if (audit/'conflicts_report.json').exists() else []
        (reports/'provider_conflicts_report.json').write_text(json.dumps({'total_conflicts': len(conflicts), 'conflicts': conflicts[:100]}, indent=2, ensure_ascii=False), encoding='utf-8')
    return out, {'total_input': int(len(df)), 'total_output': int(len(out)), **dedup_report}


def filter_ml_eligible(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or 'data_quality_band' not in df.columns:
        return df
    return df[df['data_quality_band'].ne('blocked')].copy()
