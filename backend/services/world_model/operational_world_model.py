from __future__ import annotations
from datetime import datetime, timezone
from statistics import mean, pstdev
from typing import Any


def _num(v: Any, default: float = 0.0) -> float:
    try:
        if v in (None, '', 'nan', 'None'):
            return default
        return float(v)
    except Exception:
        return default


def _avg(items: list[float]) -> float:
    return round(mean(items), 6) if items else 0.0


def _regime(snapshot: dict[str, Any]) -> str:
    s = snapshot.get('summary') or {}
    alerts = snapshot.get('alerts') or []
    data_state = snapshot.get('data_state')
    avg_ev = _num(s.get('avg_ev_pct'))
    risk = _num(s.get('avg_risk_score'))
    critical = sum(1 for a in alerts if a.get('severity') in {'critical','high'})
    if data_state != 'real_data': return 'diagnostic'
    if critical >= 2 or risk >= 65 or avg_ev < -1: return 'defensive'
    if avg_ev > 2 and risk < 45: return 'aggressive'
    if risk >= 50: return 'conservative'
    return 'balanced'

class OperationalWorldModel:
    """Continuous, read-only world model of MatchFlow operations."""
    version = '1.0.0-cognitive-world-model'
    def build(self, snapshot: dict[str, Any], memory_graph: dict[str, Any] | None = None, simulations: dict[str, Any] | None = None) -> dict[str, Any]:
        s = snapshot.get('summary') or {}
        analytics = snapshot.get('analytics') or {}
        leagues = analytics.get('league_performance') or []
        markets = analytics.get('market_performance') or []
        alerts = snapshot.get('alerts') or []
        regime = _regime(snapshot)
        evs = [_num(x.get('avg_ev_pct')) for x in leagues[:20] if x.get('state') == 'real_data']
        volatility = round(pstdev(evs), 4) if len(evs) > 1 else 0.0
        entities = {
            'markets': len(markets), 'leagues': len(leagues), 'alerts': len(alerts),
            'models': len((analytics.get('model_trends') or [])),
            'memory_nodes': (memory_graph or {}).get('summary', {}).get('nodes', 0),
        }
        systemic = {
            'risk_pressure': _num(s.get('avg_risk_score')),
            'ev_quality': _num(s.get('avg_ev_pct')),
            'confidence_quality': _num(s.get('avg_confidence')),
            'volatility_index': volatility,
            'alert_pressure': min(100, len(alerts) * 12),
        }
        state_quality = 'weak_context' if snapshot.get('data_state') != 'real_data' else 'observable_context'
        if systemic['alert_pressure'] > 50 or systemic['risk_pressure'] > 60: state_quality = 'stressed_context'
        return {
            'ok': True, 'version': self.version, 'generated_at': datetime.now(timezone.utc).isoformat(),
            'data_state': snapshot.get('data_state'), 'state_quality': state_quality, 'regime': regime,
            'entities': entities, 'systemic_state': systemic,
            'temporal_state': self._temporal(snapshot),
            'regime_map': self._regime_map(regime, systemic),
            'world_hypotheses': self._hypotheses(regime, systemic, alerts),
            'trace': 'snapshot -> systemic_state -> regime_mapping -> hypotheses; read-only model',
        }
    def _temporal(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        trends = (snapshot.get('analytics') or {}).get('model_trends') or []
        degrading = [t for t in trends if str(t.get('direction')).lower() == 'down']
        return {'short_term': 'unstable' if degrading else 'neutral', 'medium_term': 'requires_more_history' if snapshot.get('data_state') != 'real_data' else 'monitorable', 'long_term': 'memory_building', 'degrading_models': len(degrading)}
    def _regime_map(self, regime: str, systemic: dict[str, Any]) -> dict[str, Any]:
        posture = {'aggressive':'increase_selective_exposure','balanced':'maintain_filters','conservative':'raise_confidence_filters','defensive':'protect_bankroll','diagnostic':'collect_data'}[regime]
        return {'current': regime, 'recommended_posture': posture, 'risk_reward_balance': 'risk_first' if regime in {'defensive','diagnostic','conservative'} else 'ev_first'}
    def _hypotheses(self, regime: str, systemic: dict[str, Any], alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out=[]
        if regime == 'defensive': out.append({'id':'h_defensive_pressure','confidence':0.78,'claim':'Risco sistêmico acima do normal exige redução de exposição.'})
        if systemic.get('ev_quality',0) < 0: out.append({'id':'h_ev_decay','confidence':0.7,'claim':'Qualidade média de EV está fraca no contexto atual.'})
        if alerts: out.append({'id':'h_alert_cluster','confidence':0.66,'claim':'Cluster de alertas sugere investigação antes de escalar entradas.'})
        return out or [{'id':'h_stable_monitoring','confidence':0.58,'claim':'Ambiente sem evidência forte de degradação; manter monitoramento.'}]
