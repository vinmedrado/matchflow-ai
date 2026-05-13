from __future__ import annotations
from pathlib import Path
import json
import pandas as pd
from .match_identity_resolver import kickoff_conflict
from .conflict_resolver import append_conflict

SOURCE_PRIORITY = {'flashscore': 1, 'flashscore/local': 1, 'flashscore/internal': 1, 'football_data_org': 2, 'football-data.org': 2, 'the_odds_api': 3, 'odds_api': 3, 'demo/local': 9}


def _priority(source: str) -> int:
    return SOURCE_PRIORITY.get(str(source or '').lower(), 5)

def deduplicate_matches(df: pd.DataFrame, root: Path | None = None) -> tuple[pd.DataFrame, dict]:
    if df.empty or 'match_identity_key' not in df.columns:
        return df, {'duplicates_removed': 0, 'conflicts': 0, 'canonical_matches': int(len(df))}
    root = Path(root) if root else Path(__file__).resolve().parents[4]
    rows=[]; duplicates=0; conflicts=0
    for key, group in df.groupby('match_identity_key', dropna=False):
        if len(group) == 1:
            rows.append(group.iloc[0].to_dict()); continue
        records = sorted(group.to_dict('records'), key=lambda r: _priority(r.get('source')))
        base = records[0].copy(); linked=set(); provider_ids={}
        for rec in records:
            linked.add(str(rec.get('source') or 'unknown'))
            provider_ids[str(rec.get('source') or 'unknown')] = str(rec.get('match_id') or key)
            if rec is not records[0] and kickoff_conflict(base, rec):
                conflicts += 1
                append_conflict(root, {'type':'match_time_or_date_conflict','match_identity_key':key,'primary':base,'secondary':rec})
            for col, val in rec.items():
                if (base.get(col) is None or str(base.get(col)).strip()=='' or str(base.get(col)).lower()=='nan') and val not in (None, ''):
                    base[col]=val
        base['linked_sources']='|'.join(sorted(linked))
        base['provider_match_ids']=json.dumps(provider_ids, ensure_ascii=False)
        rows.append(base); duplicates += len(records)-1
    out = pd.DataFrame(rows)
    report = {'duplicates_removed': int(duplicates), 'conflicts': int(conflicts), 'canonical_matches': int(len(out))}
    report_path = root/'data/reports/deduplication_report.json'; report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    return out, report
