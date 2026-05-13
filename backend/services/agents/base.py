from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import mean, pstdev
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def num(value: Any, default: float | None = None) -> float | None:
    try:
        if value in (None, '', 'nan', 'None'):
            return default
        return float(value)
    except Exception:
        return default


def severity(score: float) -> str:
    if score >= 85:
        return 'critical'
    if score >= 65:
        return 'high'
    if score >= 35:
        return 'medium'
    return 'info'


def data_state(snapshot: dict[str, Any]) -> str:
    return str(snapshot.get('data_state') or 'unavailable_data')


def trend(values: list[float]) -> dict[str, Any]:
    clean = [float(v) for v in values if num(v, None) is not None]
    if len(clean) < 4:
        return {'available': False, 'state': 'partial_data', 'message': 'Amostra insuficiente para tendência robusta.'}
    split = max(1, len(clean) // 2)
    prev = clean[:split]
    recent = clean[split:]
    prev_avg = mean(prev) if prev else 0.0
    recent_avg = mean(recent) if recent else 0.0
    delta = recent_avg - prev_avg
    vol = pstdev(clean) if len(clean) > 1 else 0.0
    return {
        'available': True,
        'state': 'real_data',
        'previous_avg': round(prev_avg, 6),
        'recent_avg': round(recent_avg, 6),
        'delta': round(delta, 6),
        'volatility': round(vol, 6),
        'direction': 'up' if delta > 0 else 'down' if delta < 0 else 'flat',
    }


@dataclass
class AgentFinding:
    agent: str
    type: str
    severity: str
    confidence: float
    title: str
    reasoning: str
    evidence: dict[str, Any]
    recommendation: str
    state: str = 'real_data'

    def as_dict(self) -> dict[str, Any]:
        return {
            'agent': self.agent,
            'type': self.type,
            'severity': self.severity,
            'confidence': round(float(self.confidence), 3),
            'title': self.title,
            'reasoning': self.reasoning,
            'evidence': self.evidence,
            'recommendation': self.recommendation,
            'state': self.state,
            'created_at': now_iso(),
        }


class BaseAgent:
    name = 'base_agent'
    role = 'generic intelligence'

    def analyze(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        findings = [f.as_dict() for f in self.findings(snapshot)]
        return {
            'agent': self.name,
            'role': self.role,
            'state': data_state(snapshot) if findings else ('no_data' if data_state(snapshot) == 'no_data' else 'real_data'),
            'findings': findings,
            'summary': self.summarize(findings, snapshot),
            'generated_at': now_iso(),
        }

    def findings(self, snapshot: dict[str, Any]) -> list[AgentFinding]:
        return []

    def summarize(self, findings: list[dict[str, Any]], snapshot: dict[str, Any]) -> str:
        if not findings:
            return f'{self.name} não encontrou sinais críticos na janela atual.'
        high = [f for f in findings if f.get('severity') in {'high', 'critical'}]
        return f'{self.name} gerou {len(findings)} achado(s), sendo {len(high)} de alta prioridade.'
