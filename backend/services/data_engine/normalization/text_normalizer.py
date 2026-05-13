from __future__ import annotations
import re
import unicodedata
from typing import Any

_ABBREVIATIONS = {
    # Brasil — casos comuns do FlashScore
    'cr flamengo': 'flamengo', 'clube de regatas do flamengo': 'flamengo',
    'sc corinthians': 'corinthians', 'sport club corinthians': 'corinthians',
    'se palmeiras': 'palmeiras', 'sociedade esportiva palmeiras': 'palmeiras',
    'sao paulo fc': 'sao paulo', 'spfc': 'sao paulo',
    'santos fc': 'santos', 'sport club santos': 'santos',
    'atletico mineiro': 'atletico mineiro', 'atletico-mg': 'atletico mineiro',
    'atletico paranaense': 'atletico paranaense', 'cap': 'atletico paranaense',
    'vasco da gama': 'vasco', 'cr vasco da gama': 'vasco',
    'gremio fbpa': 'gremio', 'gremio foot-ball porto alegrense': 'gremio',
    'internacional rs': 'internacional', 'sport club internacional': 'internacional',
    'bahia ec': 'bahia', 'esporte clube bahia': 'bahia',
    'fluminense fc': 'fluminense',
    # Europa — casos comuns
    'man utd': 'manchester united', 'man united': 'manchester united', 'manchester utd': 'manchester united',
    'man utd': 'manchester united', 'man united': 'manchester united', 'manchester utd': 'manchester united',
    'psg': 'paris saint germain', 'paris sg': 'paris saint germain',
    'atletico mg': 'atletico mineiro', 'atletico-mg': 'atletico mineiro', 'atl mineiro': 'atletico mineiro',
    'inter milan': 'internazionale', 'internazionale milano': 'internazionale',
    'bayern munich': 'bayern munchen', 'borussia dortmund': 'dortmund',
    'epl': 'premier league', 'english premier league': 'premier league',
    'brasileirao serie a': 'brasileiro serie a', 'campeonato brasileiro serie a': 'brasileiro serie a',
}
_SUFFIXES = {'fc','sc','cf','afc','ec','ac','club','football','futebol','de','the'}
_KEEP_DISTINCT = {'city','united','sociedad','madrid','miami','milan','mineiro','paris','saint','germain'}

def strip_accents(value: str) -> str:
    return ''.join(ch for ch in unicodedata.normalize('NFKD', value) if not unicodedata.combining(ch))

def normalize_text(value: Any, *, entity_type: str = 'team') -> str:
    text = strip_accents(str(value or '').strip().lower())
    text = text.replace('&', ' and ')
    text = re.sub(r"[\./,;:_\[\]\(\)]+", ' ', text)
    text = re.sub(r"[-]+", ' ', text)
    text = re.sub(r"\s+", ' ', text).strip()
    if text in _ABBREVIATIONS:
        text = _ABBREVIATIONS[text]
    tokens = text.split()
    if entity_type == 'team':
        filtered = []
        for token in tokens:
            if token in _SUFFIXES and token not in _KEEP_DISTINCT:
                continue
            filtered.append(token)
        text = ' '.join(filtered)
    text = _ABBREVIATIONS.get(text, text)
    return re.sub(r"\s+", ' ', text).strip()

def canonical_slug(value: Any, *, entity_type: str = 'team') -> str:
    normalized = normalize_text(value, entity_type=entity_type)
    return re.sub(r'[^a-z0-9]+', '_', normalized).strip('_') or 'unknown'
