from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
from .field_priority_rules import get_rule


def can_enrich(field: str, current: Any, incoming_source: str, current_source: str | None = None, low_quality: bool = False) -> tuple[bool, str]:
    rule = get_rule(field); policy = rule.get('overwrite_policy')
    primary = rule.get('primary_source')
    if current not in (None, '') and str(current).lower() != 'nan':
        if current_source == primary and incoming_source != primary:
            return False, 'secondary_source_cannot_overwrite_primary'
        if policy == 'fill_if_empty':
            return False, 'field_already_filled'
        if policy == 'fill_if_low_quality' and not low_quality:
            return False, 'field_not_low_quality'
        if policy == 'never_overwrite_primary':
            return False, 'never_overwrite_primary'
    if incoming_source == primary or incoming_source in rule.get('fallback_sources', []):
        return True, 'allowed_by_field_priority_rule'
    return False, 'source_not_allowed_for_field'

def enrich_record(primary: dict, secondary: dict, source: str, root: Path | None = None) -> dict:
    result = dict(primary)
    metadata = result.get('enrichment_metadata') or []
    if isinstance(metadata, str):
        try: metadata = json.loads(metadata)
        except Exception: metadata = []
    current_source = result.get('source_used') or result.get('source') or 'flashscore'
    for field, value in secondary.items():
        if value in (None, '') or str(value).lower() == 'nan':
            continue
        allowed, reason = can_enrich(field, result.get(field), source, current_source, low_quality=result.get('data_quality_band') in {'low_quality','review_required'})
        if allowed:
            old = result.get(field)
            result[field] = value
            metadata.append({'field': field, 'source_used': source, 'original_source': current_source, 'enrichment_source': source, 'confidence': 0.82, 'reason': reason, 'timestamp': datetime.now(timezone.utc).isoformat(), 'old_empty': old in (None,'')})
    result['enrichment_metadata'] = metadata
    return result
