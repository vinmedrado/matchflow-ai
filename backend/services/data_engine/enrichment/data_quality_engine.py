from __future__ import annotations
from pathlib import Path
import json
import pandas as pd


def score_record(record: dict) -> dict:
    required = ['canonical_league_id','canonical_home_team_id','canonical_away_team_id','match_identity_key','match_date']
    completeness_fields = ['league','home_team','away_team','match_date','odds_home','odds_draw','odds_away','odds_over_25']
    entity_score = sum(1 for f in required[:3] if record.get(f)) / 3
    identity_score = 1.0 if record.get('match_identity_key') else 0.0
    completeness = sum(1 for f in completeness_fields if record.get(f) not in (None,'') and str(record.get(f)).lower()!='nan') / len(completeness_fields)
    conflict_count = len([x for x in str(record.get('conflict_flags') or '').split('|') if x])
    duplicate_risk = 0.0 if record.get('match_identity_key') else 0.7
    provider_agreement = 0.9 if len(str(record.get('linked_sources') or '').split('|')) > 1 else 0.7
    enrichment_quality = 0.85 if record.get('enrichment_metadata') else 0.72
    final = max(0.0, min(1.0, entity_score*.22 + identity_score*.18 + completeness*.24 + provider_agreement*.14 + enrichment_quality*.12 + (1-duplicate_risk)*.10 - conflict_count*.08))
    band = 'high_quality' if final >= .82 else 'medium_quality' if final >= .62 else 'low_quality' if final >= .42 else 'blocked'
    if conflict_count: band = 'review_required' if final >= .42 else 'blocked'
    return {'entity_mapping_score': round(entity_score,3),'match_identity_score': round(identity_score,3),'completeness_score': round(completeness,3),'provider_agreement_score': round(provider_agreement,3),'duplicate_risk_score': round(duplicate_risk,3),'conflict_count': conflict_count,'low_sample_flag': bool(record.get('low_sample_flag', False)),'enrichment_quality_score': round(enrichment_quality,3),'final_data_quality_score': round(final,3),'data_quality_score': round(final,3),'data_quality_band': band}

def score_dataframe(df: pd.DataFrame, root: Path | None = None) -> pd.DataFrame:
    if df.empty: return df
    scored=[]
    for rec in df.to_dict('records'):
        rec.update(score_record(rec)); scored.append(rec)
    out = pd.DataFrame(scored)
    if root:
        report = {'total_records': int(len(out)), 'quality_bands': out.get('data_quality_band', pd.Series(dtype=str)).value_counts().to_dict(), 'blocked_records': int((out.get('data_quality_band')=='blocked').sum()) if 'data_quality_band' in out else 0}
        p=Path(root)/'data/reports/data_engine_quality_report.json'; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    return out
