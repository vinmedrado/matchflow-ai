from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any
try:
    from rapidfuzz import fuzz, process
except Exception:  # pragma: no cover
    from difflib import SequenceMatcher
    class fuzz:
        @staticmethod
        def token_sort_ratio(a,b): return SequenceMatcher(None, a, b).ratio()*100
    class process:
        @staticmethod
        def extractOne(query, choices, scorer=None):
            best = max(choices, key=lambda c: scorer(query,c) if scorer else 0)
            return (best, scorer(query,best) if scorer else 0, None)
from .canonical_registry import CanonicalRegistry
from .text_normalizer import normalize_text

AUTO_MATCH_THRESHOLD = 92.0
REVIEW_THRESHOLD = 82.0

class EntityMapper:
    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root else Path(__file__).resolve().parents[4]
        self.registry = CanonicalRegistry(self.root)
        self.audit_dir = self.root / 'backend/services/data_engine/audit'
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = self.root / 'backend/services/data_engine/storage/entity_resolution_cache.json'
        self.cache = self._read_json(self.cache_path, {})

    def _read_json(self, path: Path, default: Any) -> Any:
        try: return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default
        except Exception: return default

    def _write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')

    def map_entity(self, raw_name: str, entity_type: str = 'team', provider: str = 'unknown', provider_id: str | None = None, context: dict | None = None) -> dict:
        normalized = normalize_text(raw_name, entity_type=entity_type)
        if provider_id:
            by_pid = self.registry.provider_id_lookup(provider, provider_id, entity_type)
            if by_pid:
                meta = self.registry.candidates(entity_type)[by_pid]
                return self._result(by_pid, meta['canonical_name'], provider, raw_name, normalized, 100, 'provider_id', False, 'Provider id already linked.')
        by_alias = self.registry.alias_lookup(raw_name, entity_type, provider)
        if by_alias:
            meta = self.registry.candidates(entity_type)[by_alias]
            return self._result(by_alias, meta['canonical_name'], provider, raw_name, normalized, 100, 'alias', False, 'Known provider alias.')
        data = self.registry.candidates(entity_type)
        normalized_to_id = {}
        for cid, meta in data.items():
            names = [meta.get('canonical_name', cid)] + meta.get('aliases', [])
            for name in names:
                normalized_to_id[normalize_text(name, entity_type=entity_type)] = cid
        if normalized in normalized_to_id:
            cid = normalized_to_id[normalized]; meta = data[cid]
            self.registry.ensure_entity(raw_name, entity_type, provider, provider_id, 1.0)
            return self._result(cid, meta['canonical_name'], provider, raw_name, normalized, 100, 'normalized_exact', False, 'Normalized name matched canonical registry.')
        choices = list(normalized_to_id.keys())
        score = 0.0; matched_norm = None
        if choices:
            matched = process.extractOne(normalized, choices, scorer=fuzz.token_sort_ratio)
            if matched:
                matched_norm, score = matched[0], float(matched[1])
        if matched_norm and score >= AUTO_MATCH_THRESHOLD:
            cid = normalized_to_id[matched_norm]; meta = data[cid]
            self.registry.ensure_entity(raw_name, entity_type, provider, provider_id, min(0.99, score/100))
            return self._result(cid, meta['canonical_name'], provider, raw_name, normalized, score, 'rapidfuzz_auto', False, 'RapidFuzz auto-match above threshold.')
        if matched_norm and score >= REVIEW_THRESHOLD:
            cid = normalized_to_id[matched_norm]; meta = data[cid]
            self._queue_review(entity_type, raw_name, normalized, provider, cid, score, context, 'score_between_82_and_92')
            return self._result(cid, meta['canonical_name'], provider, raw_name, normalized, score, 'rapidfuzz_review', True, 'RapidFuzz match requires review.')
        llm_suggestion = self._optional_llm_suggestion(raw_name, normalized, entity_type, provider, matched_norm, score, context)
        if llm_suggestion and llm_suggestion.get('canonical_id') in data and float(llm_suggestion.get('confidence', 0)) >= 0.92:
            cid = llm_suggestion['canonical_id']; meta = data[cid]
            self._queue_review(entity_type, raw_name, normalized, provider, cid, score, context, 'llm_suggestion_high_confidence')
            return self._result(cid, meta['canonical_name'], provider, raw_name, normalized, max(score, 82), 'llm_suggestion_review', True, 'LLM suggested match; queued for review.')
        cid = self.registry.ensure_entity(raw_name, entity_type, provider, provider_id, 0.55)
        meta = data.get(cid, {'canonical_name': raw_name})
        self._queue_unresolved(entity_type, raw_name, normalized, provider, score, context)
        return self._result(cid, meta.get('canonical_name', raw_name), provider, raw_name, normalized, score, 'created_low_confidence', True, 'No reliable match; created low-confidence entity and queued review.')

    def _optional_llm_suggestion(self, raw_name, normalized, entity_type, provider, matched_norm, score, context):
        if os.getenv('ENTITY_RESOLUTION_USE_LLM', 'false').lower() != 'true':
            return None
        try:
            threshold = float(os.getenv('ENTITY_RESOLUTION_LLM_THRESHOLD', '82'))
        except ValueError:
            threshold = 82.0
        if score >= threshold:
            return None
        if os.getenv('ENTITY_RESOLUTION_LLM_PROVIDER', 'groq').lower() != 'groq':
            return None
        cache_key = f'{entity_type}:{provider}:{normalized}'
        if os.getenv('ENTITY_RESOLUTION_LLM_CACHE', 'true').lower() in {'1','true','yes'} and cache_key in self.cache:
            return self.cache[cache_key]

        data = self.registry.candidates(entity_type)
        candidates = [{'canonical_id': cid, 'canonical_name': meta.get('canonical_name', cid), 'aliases': meta.get('aliases', [])[:5]} for cid, meta in list(data.items())[:30]]
        suggestion = {'canonical_id': None, 'confidence': 0.0, 'reason': 'groq_not_called'}
        api_key = os.getenv('GROQ_API_KEY', '').strip()
        if not api_key:
            suggestion['reason'] = 'GROQ_API_KEY_missing; queued for human review.'
        else:
            try:
                import urllib.request, urllib.error
                prompt = (
                    'You are an entity-resolution reviewer. Return compact JSON only with canonical_id, confidence 0-1, reason. '
                    f'Entity type: {entity_type}. Raw name: {raw_name}. Normalized: {normalized}. Provider: {provider}. '
                    f'Closest RapidFuzz score: {score}. Candidates: {json.dumps(candidates, ensure_ascii=False)}'
                )
                payload = json.dumps({
                    'model': os.getenv('ENTITY_RESOLUTION_GROQ_MODEL', 'llama-3.1-8b-instant'),
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0,
                    'max_tokens': 160,
                }).encode('utf-8')
                req = urllib.request.Request(
                    'https://api.groq.com/openai/v1/chat/completions',
                    data=payload,
                    headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                    method='POST',
                )
                with urllib.request.urlopen(req, timeout=8) as resp:  # nosec B310 - user-configured optional API call
                    body = json.loads(resp.read().decode('utf-8'))
                content = body.get('choices', [{}])[0].get('message', {}).get('content', '{}')
                parsed = json.loads(content[content.find('{'):content.rfind('}')+1])
                cid = parsed.get('canonical_id')
                confidence = float(parsed.get('confidence') or 0.0)
                suggestion = {'canonical_id': cid if cid in data else None, 'confidence': max(0.0, min(1.0, confidence)), 'reason': parsed.get('reason', 'groq_suggestion')}
            except Exception as exc:
                suggestion = {'canonical_id': None, 'confidence': 0.0, 'reason': f'groq_fallback_failed: {type(exc).__name__}'}
        self.cache[cache_key] = suggestion
        self._write_json(self.cache_path, self.cache)
        return suggestion

    def _result(self, cid, cname, provider, raw, normalized, score, method, needs_review, reason):
        return {'canonical_id': cid, 'canonical_name': cname, 'provider': provider, 'raw_name': raw, 'normalized_name': normalized, 'score': round(float(score), 3), 'method': method, 'confidence_band': 'high' if score >= 92 else 'medium' if score >= 82 else 'low', 'needs_review': bool(needs_review), 'reason': reason}

    def _append_json_list(self, path: Path, item: dict, dedupe_key: str):
        data = self._read_json(path, [])
        if not any(x.get(dedupe_key) == item.get(dedupe_key) for x in data):
            data.append(item)
        self._write_json(path, data)

    def _queue_review(self, entity_type, raw, normalized, provider, candidate_id, score, context, reason):
        self._append_json_list(self.audit_dir/'mapping_review_queue.json', {'entity_type':entity_type,'provider':provider,'raw_name':raw,'normalized_name':normalized,'candidate_id':candidate_id,'score':score,'context':context or {},'reason':reason}, 'raw_name')

    def _queue_unresolved(self, entity_type, raw, normalized, provider, score, context):
        self._append_json_list(self.audit_dir/'unresolved_entities.json', {'entity_type':entity_type,'provider':provider,'raw_name':raw,'normalized_name':normalized,'score':score,'context':context or {},'reason':'no_reliable_match'}, 'raw_name')
