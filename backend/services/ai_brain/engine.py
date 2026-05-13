from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from statistics import mean, pstdev
from typing import Any

from .memory import OperationalMemoryStore


def _num(value: Any, default: float | None = None) -> float | None:
    try:
        if value in (None, "", "nan", "None"):
            return default
        return float(value)
    except Exception:
        return default


def _severity(score: float) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 35:
        return "medium"
    return "info"


def _trend(values: list[float]) -> dict[str, Any]:
    if len(values) < 4:
        return {"available": False, "state": "partial_data", "message": "Amostra insuficiente para tendência robusta."}
    half = max(1, len(values) // 2)
    previous = values[:half]
    recent = values[half:]
    prev_avg = mean(previous) if previous else 0.0
    recent_avg = mean(recent) if recent else 0.0
    delta = recent_avg - prev_avg
    volatility = pstdev(values) if len(values) > 1 else 0.0
    return {
        "available": True,
        "state": "real_data",
        "previous_avg": round(prev_avg, 6),
        "recent_avg": round(recent_avg, 6),
        "delta": round(delta, 6),
        "volatility": round(volatility, 6),
        "direction": "up" if delta > 0 else "down" if delta < 0 else "flat",
    }


def _current_streak(values: list[float]) -> int:
    if not values:
        return 0
    signs = [1 if v > 0 else -1 if v < 0 else 0 for v in values]
    last = next((s for s in reversed(signs) if s != 0), 0)
    if last == 0:
        return 0
    streak = 0
    for s in reversed(signs):
        if s == last:
            streak += last
        elif s == 0:
            continue
        else:
            break
    return streak


def _bucket_stats(candidates: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    buckets: defaultdict[str, list[float]] = defaultdict(list)
    for row in candidates:
        ev = _num(row.get("true_ev"), None)
        name = row.get(key)
        if ev is not None and name:
            buckets[str(name)].append(ev)
    out: list[dict[str, Any]] = []
    for name, vals in buckets.items():
        out.append({
            "name": name,
            "signals": len(vals),
            "avg_ev_pct": round(mean(vals) * 100, 2),
            "positive_rate_pct": round(sum(1 for v in vals if v > 0) / len(vals) * 100, 2),
            "streak": _current_streak(vals),
            "trend": _trend(vals),
            "state": "real_data",
        })
    return sorted(out, key=lambda item: (item["avg_ev_pct"], item["signals"]), reverse=True)[:20]


def _build_alerts(candidates: list[dict[str, Any]], paper: dict[str, Any], analytics: dict[str, Any]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    evs = [_num(c.get("true_ev"), None) for c in candidates]
    evs = [v for v in evs if v is not None]
    scores = [_num(c.get("decision_score"), None) for c in candidates]
    scores = [v for v in scores if v is not None]
    risks = [_num(c.get("risk_score"), None) for c in candidates]
    risks = [v for v in risks if v is not None]

    if not candidates:
        alerts.append({
            "id": "no-signals",
            "type": "NO_DATA",
            "severity": "info",
            "priority": 10,
            "state": "no_data",
            "title": "Decision engine sem sinais disponíveis",
            "reason": "Nenhum candidato real foi retornado para análise operacional.",
            "impact": "Live intelligence, ranking e explicabilidade ficam limitados.",
            "recommendation": "Rodar pipeline de features, ML predictions e decision engine antes de avaliar performance.",
        })
        return alerts

    if evs:
        tr = _trend(evs)
        if tr.get("available") and tr.get("delta", 0) < -0.01:
            priority = min(100, abs(float(tr["delta"])) * 2000)
            alerts.append({
                "id": "ev-degradation",
                "type": "DEGRADATION",
                "severity": _severity(priority),
                "priority": round(priority, 1),
                "state": "real_data",
                "title": "EV médio degradou no lote recente",
                "reason": f"EV recente {tr['recent_avg']:.4f} vs anterior {tr['previous_avg']:.4f}.",
                "impact": "Pode indicar piora da qualidade dos sinais ou mudança de mercado.",
                "recommendation": "Reduzir exposição e revisar mercados/ligas com EV negativo antes de operar.",
            })
        neg_rate = sum(1 for v in evs if v < 0) / len(evs)
        if neg_rate >= 0.45:
            priority = neg_rate * 100
            alerts.append({
                "id": "negative-ev-density",
                "type": "RISK",
                "severity": _severity(priority),
                "priority": round(priority, 1),
                "state": "real_data",
                "title": "Alta densidade de EV negativo",
                "reason": f"{neg_rate:.0%} dos sinais com EV calculado estão negativos.",
                "impact": "Entrada automática ou agressiva pode aumentar drawdown.",
                "recommendation": "Aplicar filtro de EV mínimo e priorizar apenas sinais com margem clara sobre a probabilidade implícita.",
            })

    if risks and mean(risks) >= 55:
        priority = min(100, mean(risks))
        alerts.append({
            "id": "risk-exposure",
            "type": "EXPOSURE",
            "severity": _severity(priority),
            "priority": round(priority, 1),
            "state": "real_data",
            "title": "Risco operacional médio elevado",
            "reason": f"Risk score médio do lote: {mean(risks):.1f}.",
            "impact": "Aumenta chance de sequência ruim se stake não for limitada.",
            "recommendation": "Usar staking conservador, limitar mercados correlacionados e aguardar confirmação de CLV quando disponível.",
        })

    equity = [_num(v, None) for v in (paper.get("equity_curve") or [])]
    equity = [v for v in equity if v is not None]
    if len(equity) >= 3:
        peak = max(equity)
        current = equity[-1]
        drawdown = 0 if peak == 0 else (current - peak) / peak * 100
        if drawdown <= -5:
            priority = min(100, abs(drawdown) * 8)
            alerts.append({
                "id": "bankroll-drawdown",
                "type": "BANKROLL",
                "severity": _severity(priority),
                "priority": round(priority, 1),
                "state": "real_data",
                "title": "Drawdown relevante detectado na banca",
                "reason": f"Banca atual está {drawdown:.2f}% abaixo do pico registrado.",
                "impact": "Pode exigir pausa operacional ou redução de stake.",
                "recommendation": "Ativar perfil conservador até a curva recuperar consistência.",
            })

    league_stats = analytics.get("league_performance") or []
    for item in league_stats[:10]:
        if item.get("signals", 0) >= 3 and item.get("avg_ev_pct", 0) < -1:
            priority = min(100, abs(item["avg_ev_pct"]) * 15 + item["signals"])
            alerts.append({
                "id": f"league-{item['name']}",
                "type": "LEAGUE",
                "severity": _severity(priority),
                "priority": round(priority, 1),
                "state": "real_data",
                "title": f"Liga inconsistente: {item['name']}",
                "reason": f"EV médio {item['avg_ev_pct']:.2f}% em {item['signals']} sinais.",
                "impact": "Essa liga pode estar degradando o resultado agregado.",
                "recommendation": "Rebaixar peso da liga ou exigir score/confiança maior temporariamente.",
            })
    return sorted(alerts, key=lambda x: x.get("priority", 0), reverse=True)[:30]


def build_ai_brain_snapshot() -> dict[str, Any]:
    # Import here to avoid hard dependency/cycles at app startup.
    from backend.api.premium import _analytics, _model_trends, _normalize_candidates, _paper_with_equity

    candidates, candidates_meta = _normalize_candidates(300)
    paper, paper_meta = _paper_with_equity()
    base_analytics = _analytics(candidates)
    trends, trend_meta = _model_trends()
    advanced_analytics = {
        **base_analytics,
        "league_performance": _bucket_stats(candidates, "league"),
        "market_performance": _bucket_stats(candidates, "market"),
        "model_trends": trends,
    }
    alerts = _build_alerts(candidates, paper, advanced_analytics)
    recommendations = []
    if alerts:
        for alert in alerts[:8]:
            recommendations.append({
                "source_alert": alert["id"],
                "severity": alert["severity"],
                "action": alert["recommendation"],
                "state": alert.get("state", "real_data"),
            })
    else:
        recommendations.append({
            "source_alert": "stable-operation",
            "severity": "info",
            "action": "Sem alertas críticos no lote atual. Manter monitoramento e evitar aumentar stake sem amostra suficiente.",
            "state": "real_data" if candidates else "no_data",
        })

    evs = [_num(c.get("true_ev"), None) for c in candidates]
    evs = [v for v in evs if v is not None]
    scores = [_num(c.get("decision_score"), None) for c in candidates]
    scores = [v for v in scores if v is not None]
    markets = Counter(c.get("market") for c in candidates if c.get("market"))
    leagues = Counter(c.get("league") for c in candidates if c.get("league"))
    memory = OperationalMemoryStore().profile()
    data_state = "real_data" if candidates else "no_data"
    if candidates and (not evs or not scores):
        data_state = "partial_data"

    return {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_state": data_state,
        "brain_version": "1.0.0-operational",
        "summary": {
            "signals": len(candidates),
            "ev_available": len(evs),
            "avg_ev_pct": round(mean(evs) * 100, 2) if evs else None,
            "avg_score": round(mean(scores), 2) if scores else None,
            "top_market": markets.most_common(1)[0][0] if markets else None,
            "top_league": leagues.most_common(1)[0][0] if leagues else None,
            "alerts": len(alerts),
            "memory_state": memory["state"],
        },
        "insights": _build_insights(candidates, advanced_analytics, alerts, memory),
        "alerts": alerts,
        "recommendations": recommendations,
        "analytics": advanced_analytics,
        "memory": memory,
        "source_meta": {
            "decision_candidates": candidates_meta,
            "paper_trading": paper_meta,
            "model_trends": trend_meta,
        },
    }


def _build_insights(candidates: list[dict[str, Any]], analytics: dict[str, Any], alerts: list[dict[str, Any]], memory: dict[str, Any]) -> list[dict[str, Any]]:
    insights: list[dict[str, Any]] = []
    if not candidates:
        insights.append({"type": "operational", "state": "no_data", "title": "Sem material operacional", "message": "O AI Brain está ativo, mas aguarda sinais reais do decision engine."})
        return insights
    league = (analytics.get("league_performance") or [{}])[0]
    market = (analytics.get("market_performance") or [{}])[0]
    if league.get("name"):
        insights.append({"type": "league", "state": "real_data", "title": "Liga com melhor leitura recente", "message": f"{league['name']} lidera a amostra com EV médio {league.get('avg_ev_pct')}% em {league.get('signals')} sinais."})
    if market.get("name"):
        insights.append({"type": "market", "state": "real_data", "title": "Mercado dominante", "message": f"{market['name']} aparece como mercado mais forte por EV médio na janela atual."})
    if alerts:
        insights.append({"type": "risk", "state": "real_data", "title": "Risco priorizado", "message": f"Alerta principal: {alerts[0]['title']} — {alerts[0]['impact']}"})
    if memory.get("available"):
        insights.append({"type": "memory", "state": "real_data", "title": "Memória operacional ativa", "message": f"Perfil inferido: {memory.get('risk_profile')}; {memory.get('events')} eventos recentes armazenados."})
    else:
        insights.append({"type": "memory", "state": "no_data", "title": "Memória ainda vazia", "message": "O Copilot passará a lembrar perguntas e preferências conforme for usado."})
    return insights


def answer_with_brain(question: str) -> dict[str, Any]:
    store = OperationalMemoryStore()
    store.append("question", {"question": question})
    snapshot = build_ai_brain_snapshot()
    q = question.lower()
    lines: list[str] = []
    summary = snapshot.get("summary") or {}
    if any(term in q for term in ["drawdown", "banca", "bankroll"]):
        bankroll_alerts = [a for a in snapshot["alerts"] if a.get("type") == "BANKROLL"]
        if bankroll_alerts:
            lines.append(bankroll_alerts[0]["reason"] + " " + bankroll_alerts[0]["recommendation"])
        else:
            lines.append("Não há drawdown crítico detectado com os dados disponíveis. Se a equity curve estiver ausente, o sistema não inventa curva de banca.")
    elif any(term in q for term in ["liga", "league"]):
        leagues = snapshot["analytics"].get("league_performance") or []
        lines.append("Principais ligas por EV médio: " + "; ".join([f"{x['name']} ({x['avg_ev_pct']}%, {x['signals']} sinais)" for x in leagues[:5]]) if leagues else "Não há dados suficientes por liga.")
    elif any(term in q for term in ["mercado", "market", "btts", "over", "under"]):
        markets = snapshot["analytics"].get("market_performance") or []
        lines.append("Mercados mais fortes/fracos na amostra: " + "; ".join([f"{x['name']} ({x['avg_ev_pct']}%)" for x in markets[:6]]) if markets else "Não há dados suficientes por mercado.")
    elif any(term in q for term in ["risco", "risk", "exposure"]):
        risk_alerts = [a for a in snapshot["alerts"] if a.get("type") in {"RISK", "EXPOSURE", "BANKROLL"}]
        lines.append(" | ".join([f"{a['title']}: {a['recommendation']}" for a in risk_alerts[:4]]) if risk_alerts else "Nenhum alerta de risco elevado foi detectado na janela atual.")
    else:
        lines.append(f"AI Brain ativo: {summary.get('signals', 0)} sinais, EV médio {summary.get('avg_ev_pct')}, {summary.get('alerts', 0)} alertas e estado {snapshot.get('data_state')}.")
        for insight in snapshot.get("insights", [])[:3]:
            lines.append(insight.get("message", ""))
    return {
        "ok": True,
        "mode": "ai_brain_rules_with_operational_context",
        "answer": "\n".join([x for x in lines if x]),
        "snapshot": snapshot,
    }
