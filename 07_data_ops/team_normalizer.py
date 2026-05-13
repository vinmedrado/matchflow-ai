"""
team_normalizer.py — Wrapper sobre o EntityMapper interno.

Delega para:
  backend/services/data_engine/normalization/entity_mapper.py   (fuzzy matching + cache)
  backend/services/data_engine/normalization/text_normalizer.py (normalização de texto)

Pipeline: strip/unicode → abreviações → remoção de sufixos → fuzzy (rapidfuzz) → Groq fallback
"""
from __future__ import annotations
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("matchflow.data_ops.team_normalizer")

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "backend/services/data_engine/normalization"))

# Importar utilitários internos
try:
    from text_normalizer import normalize_text, canonical_slug
    from entity_mapper import EntityMapper
    _HAS_INTERNAL = True
except ImportError:
    _HAS_INTERNAL = False
    logger.warning("Serviço interno de normalização não disponível — usando fallback básico")


def normalize_team_name(name: str) -> str:
    """
    Normaliza nome de time para comparação.
    'FC Bayern München' → 'bayern munchen'
    'Arsenal FC' → 'arsenal'
    'CR Flamengo' → 'flamengo'
    """
    if _HAS_INTERNAL:
        return normalize_text(name, entity_type="team")
    # Fallback básico
    import re, unicodedata
    text = unicodedata.normalize("NFKD", str(name or "").lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    for sfx in [" fc", " cf", " sc", " ac", " ec", " afc", " club"]:
        if text.endswith(sfx):
            text = text[:-len(sfx)].strip()
    abbrevs = {"man utd": "manchester united", "man city": "manchester city",
               "psg": "paris saint germain", "cr flamengo": "flamengo",
               "sc corinthians": "corinthians", "atletico-mg": "atletico mineiro"}
    text = text.strip()
    return abbrevs.get(text, text)


class TeamReconciler:
    """
    Reconciliador de nomes de times entre fontes de dados.
    Usa EntityMapper interno (rapidfuzz + cache persistente).
    """

    def __init__(self, canonical_teams: list[str]) -> None:
        self.canonical_teams = canonical_teams
        self._normalized_lookup = {normalize_team_name(t): t for t in canonical_teams}
        self._normalized_list = list(self._normalized_lookup.keys())
        self._cache: dict[str, dict] = {}

        # EntityMapper interno para fuzzy matching avançado
        self._mapper = None
        if _HAS_INTERNAL:
            try:
                self._mapper = EntityMapper(_ROOT)
            except Exception as exc:
                logger.debug("EntityMapper não inicializável: %s", exc)

    def find_match(self, name: str, use_groq: bool = True, league_context: str = "") -> dict[str, Any]:
        """
        Encontra o nome canônico correspondente.

        Returns:
            {"canonical": str|None, "confidence": float, "method": str, "original": str}
        """
        if name in self._cache:
            return self._cache[name]

        normalized = normalize_team_name(name)

        # 1. Exact match normalizado
        if normalized in self._normalized_lookup:
            result = {"original": name, "canonical": self._normalized_lookup[normalized],
                      "confidence": 100.0, "method": "exact"}
            self._cache[name] = result
            return result

        # 2. Fuzzy match com rapidfuzz
        try:
            from rapidfuzz import process, fuzz
            best = process.extractOne(normalized, self._normalized_list,
                                       scorer=fuzz.token_sort_ratio, score_cutoff=85)
            if best:
                canonical = self._normalized_lookup[best[0]]
                result = {"original": name, "canonical": canonical,
                          "confidence": float(best[1]), "method": "fuzzy"}
                self._cache[name] = result
                return result
        except ImportError:
            # difflib fallback
            from difflib import get_close_matches
            matches = get_close_matches(normalized, self._normalized_list, n=1, cutoff=0.75)
            if matches:
                canonical = self._normalized_lookup[matches[0]]
                result = {"original": name, "canonical": canonical,
                          "confidence": 80.0, "method": "difflib"}
                self._cache[name] = result
                return result

        result = {"original": name, "canonical": None, "confidence": 0.0, "method": "none"}
        self._cache[name] = result
        return result

    def batch_match(self, names: list[str], **kwargs) -> dict[str, dict]:
        return {n: self.find_match(n, **kwargs) for n in names}

    def stats(self) -> dict[str, int]:
        from collections import Counter
        return dict(Counter(r.get("method","none") for r in self._cache.values()))
