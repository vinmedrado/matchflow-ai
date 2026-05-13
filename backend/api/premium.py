from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

from backend.services.decision_engine_service import decision_candidates, decision_summary
from backend.services.paper_trading_service import paper_trading_summary
from backend.services.monitoring_service import monitoring_status
from backend.services.test_lab_service import calibration_summary, ensemble_summary
from backend.services.ai_brain import build_ai_brain_snapshot

router = APIRouter(prefix="/api/premium", tags=["premium-ai-platform"])
MODE = "PAPER_TRADING_SIMULATION_ONLY"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _safe(fn, fallback: Any, source: str, meta: dict[str, Any] | None = None) -> Any:
    try:
        value = fn()
        if value is None:
            if meta is not None:
                meta[source] = {"available": False, "state": "unavailable_data", "message": "Service returned no payload."}
            return fallback
        if meta is not None:
            meta[source] = {"available": True, "state": "real_data"}
        return value
    except Exception as exc:
        if meta is not None:
            meta[source] = {"available": False, "state": "unavailable_data", "message": str(exc)}
        return fallback


def _num(value: Any, default: float | None = None) -> float | None:
    try:
        if value in (None, "", "nan", "None"):
            return default
        return float(value)
    except Exception:
        return default


def _state(available: bool, *, partial: bool = False, simulated: bool = False) -> str:
    if simulated:
        return "simulated_data"
    if available and partial:
        return "partial_data"
    if available:
        return "real_data"
    return "no_data"


def _read_json(relative: str) -> tuple[dict[str, Any], dict[str, Any]]:
    path = _project_root() / relative
    if not path.exists():
        return {}, {"available": False, "state": "no_data", "path": str(path), "message": "Arquivo não encontrado."}
    try:
        return json.loads(path.read_text(encoding="utf-8")), {"available": True, "state": "real_data", "path": str(path)}
    except Exception as exc:
        return {}, {"available": False, "state": "unavailable_data", "path": str(path), "message": str(exc)}


def _normalize_candidates(limit: int = 160) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    meta: dict[str, Any] = {}
    data = _safe(lambda: decision_candidates(limit=limit), [], "decision_candidates", meta)
    if isinstance(data, dict):
        data = data.get("candidates") or data.get("data") or []
    if not isinstance(data, list):
        return [], {"available": False, "state": "unavailable_data", "message": "Decision engine returned an unsupported payload.", "sources": meta}

    out: list[dict[str, Any]] = []
    partial_rows = 0
    for raw in data[:limit]:
        if not isinstance(raw, dict):
            continue
        p = _num(raw.get("ml_probability") or raw.get("probability") or raw.get("confidence"), None)
        odds = _num(raw.get("odds"), None)
        implied = (1 / odds) if odds and odds > 1 else None
        ev_raw = raw.get("true_ev") if raw.get("true_ev") is not None else raw.get("ev")
        ev = _num(ev_raw, None)
        if ev is None and p is not None and implied is not None:
            ev = p - implied
        score = _num(raw.get("decision_score") or raw.get("score"), None)
        risk = _num(raw.get("risk_score"), None)
        kelly = _num(raw.get("kelly_stake_pct") or raw.get("stake_pct"), None)
        if any(v is None for v in [p, odds, ev, score]):
            partial_rows += 1
        out.append({
            "id": raw.get("id") or raw.get("event_id") or f"signal-{len(out)+1}",
            "date": raw.get("date") or raw.get("match_date"),
            "league": raw.get("league") or raw.get("competition"),
            "home_team": raw.get("home_team") or raw.get("home"),
            "away_team": raw.get("away_team") or raw.get("away"),
            "market": raw.get("market") or raw.get("market_name"),
            "selection": raw.get("selection") or raw.get("bet") or raw.get("signal"),
            "odds": odds,
            "ml_probability": p,
            "implied_probability": implied,
            "true_ev": ev,
            "decision_score": score,
            "risk_score": risk,
            "kelly_stake_pct": kelly,
            "confidence_band": raw.get("confidence_band"),
            "steam_detected": bool(raw.get("steam_detected") or raw.get("steam")),
            "data_state": _state(True, partial=any(v is None for v in [p, odds, ev, score])),
        })
    available = len(out) > 0
    return out, {
        "available": available,
        "state": _state(available, partial=partial_rows > 0),
        "total": len(out),
        "partial_rows": partial_rows,
        "sources": meta,
    }


def _series(values: list[Any], points: int = 18) -> list[dict[str, Any]]:
    clean = [_num(v, None) for v in values]
    clean = [v for v in clean if v is not None]
    if not clean:
        return []
    step = max(1, len(clean) // points)
    sampled = clean[::step][-points:]
    return [{"label": f"D{idx+1}", "value": round(float(v), 2)} for idx, v in enumerate(sampled)]


def _paper_with_equity() -> tuple[dict[str, Any], dict[str, Any]]:
    meta: dict[str, Any] = {}
    paper = _safe(paper_trading_summary, {}, "paper_summary", meta)
    if not isinstance(paper, dict):
        paper = {}
    equity_path = _project_root() / "data/paper_trading/paper_equity_curve.csv"
    equity: list[float] = []
    if equity_path.exists():
        try:
            import pandas as pd
            df = pd.read_csv(equity_path)
            col = next((c for c in ["bankroll_after", "equity_curve", "current_bankroll", "cumulative_profit"] if c in df.columns), None)
            if col:
                equity = [float(v) for v in df[col].dropna().tolist()]
                meta["equity_curve"] = {"available": bool(equity), "state": _state(bool(equity)), "path": str(equity_path), "column": col}
            else:
                meta["equity_curve"] = {"available": False, "state": "partial_data", "path": str(equity_path), "message": "CSV encontrado, mas sem coluna de equity conhecida."}
        except Exception as exc:
            meta["equity_curve"] = {"available": False, "state": "unavailable_data", "path": str(equity_path), "message": str(exc)}
    else:
        raw = paper.get("equity_curve")
        if isinstance(raw, list):
            equity = [v for v in raw if _num(v, None) is not None]
        meta["equity_curve"] = {"available": bool(equity), "state": _state(bool(equity)), "path": str(equity_path)}
    return {**paper, "equity_curve": equity}, meta


def _streaks_from_latest(paper: dict[str, Any]) -> dict[str, Any] | None:
    latest = paper.get("latest_signals") or []
    if not isinstance(latest, list) or not latest:
        return None
    signs: list[int] = []
    for row in latest:
        if not isinstance(row, dict):
            continue
        pnl = _num(row.get("pnl") or row.get("profit") or row.get("result_profit"), None)
        result = str(row.get("result") or row.get("status") or "").lower()
        if pnl is not None:
            signs.append(1 if pnl > 0 else -1 if pnl < 0 else 0)
        elif "win" in result or "green" in result:
            signs.append(1)
        elif "loss" in result or "red" in result:
            signs.append(-1)
    if not signs:
        return None
    current = 0
    last = signs[-1]
    for s in reversed(signs):
        if s == last and s != 0:
            current += s
        else:
            break
    best_win = worst_loss = run = 0
    prev = None
    for s in signs:
        if s == prev and s != 0:
            run += s
        else:
            run = s
            prev = s
        best_win = max(best_win, run)
        worst_loss = min(worst_loss, run)
    return {"current": current, "best_win": best_win, "worst_loss": abs(worst_loss), "sample": len(signs)}


def _analytics(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    by_league: defaultdict[str, list[float]] = defaultdict(list)
    by_market: defaultdict[str, list[float]] = defaultdict(list)
    by_hour: defaultdict[str, list[float]] = defaultdict(list)
    for c in candidates:
        ev = _num(c.get("true_ev"), None)
        if ev is None:
            continue
        if c.get("league"):
            by_league[str(c["league"])].append(ev)
        if c.get("market"):
            by_market[str(c["market"])].append(ev)
        date = str(c.get("date") or "")
        hour = date[11:13] if len(date) >= 13 and date[11:13].isdigit() else "N/D"
        by_hour[hour].append(ev)

    def pack(bucket: defaultdict[str, list[float]]) -> list[dict[str, Any]]:
        return sorted([
            {"name": k, "roi": round(sum(v) / len(v) * 100, 2), "signals": len(v), "data_state": "real_data"}
            for k, v in bucket.items() if v
        ], key=lambda x: x["roi"], reverse=True)[:12]
    return {"league_roi": pack(by_league), "market_roi": pack(by_market), "hour_roi": pack(by_hour)}


def _model_trends() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    registry, meta = _read_json("data/ml/models/registry.json")
    if not registry:
        return [], meta
    candidates = []
    raw_models = registry.get("models") or registry.get("history") or registry.get("items") or []
    if isinstance(raw_models, dict):
        raw_models = list(raw_models.values())
    if isinstance(raw_models, list):
        for idx, item in enumerate(raw_models):
            if not isinstance(item, dict):
                continue
            val = _num(item.get("auc") or item.get("accuracy") or item.get("score") or item.get("validation_score"), None)
            if val is not None:
                candidates.append({"label": item.get("name") or item.get("market") or f"M{idx+1}", "value": round(val * 100 if val <= 1 else val, 2), "data_state": "real_data"})
    return candidates[:12], {**meta, "available": bool(candidates), "state": _state(bool(candidates))}


@router.get("/copilot")
def copilot_context(limit: int = Query(default=80, ge=1, le=300)):
    candidates, candidates_meta = _normalize_candidates(limit)
    source_meta: dict[str, Any] = {"decision_candidates": candidates_meta}
    summary = _safe(decision_summary, {}, "decision_summary", source_meta)
    paper, paper_meta = _paper_with_equity()
    source_meta["paper_trading"] = paper_meta
    ml = _safe(ensemble_summary, {}, "ml_ensemble", source_meta)
    calibration = _safe(calibration_summary, {}, "ml_calibration", source_meta)
    monitoring = _safe(monitoring_status, {}, "monitoring", source_meta)
    valid_ev = [c for c in candidates if _num(c.get("true_ev"), None) is not None]
    high_ev = [c for c in valid_ev if (c.get("true_ev") or 0) > 0 and (_num(c.get("decision_score"), 0) or 0) >= 55]
    market_counter = Counter(c.get("market") for c in candidates if c.get("market"))
    top = sorted(valid_ev, key=lambda c: (_num(c.get("decision_score"), -999) or -999, _num(c.get("true_ev"), -999) or -999), reverse=True)[:5]
    brain = build_ai_brain_snapshot()
    insights: list[dict[str, Any]] = list(brain.get("insights", []))
    if candidates:
        insights.append({"type": "signals", "state": candidates_meta["state"], "message": f"{len(candidates)} sinais reais carregados do decision engine; {len(high_ev)} têm EV positivo e score operacional >= 55."})
    else:
        insights.append({"type": "signals", "state": "no_data", "message": "Nenhum sinal real disponível. Rode o decision engine para popular a central premium."})
    if market_counter:
        insights.append({"type": "market", "state": "real_data", "message": f"Mercado mais frequente no lote atual: {market_counter.most_common(1)[0][0]}."})
    if paper.get("file_exists"):
        insights.append({"type": "bankroll", "state": "real_data", "message": f"Paper trading encontrado com {paper.get('total_signals', 0)} sinais e banca atual registrada."})
    else:
        insights.append({"type": "bankroll", "state": "no_data", "message": "Resumo de paper trading ausente; métricas de banca não serão inventadas."})
    insights.append({"type": "mode", "state": "simulated_data", "message": "Modo seguro: paper trading/simulação, sem execução automática de apostas."})
    return {"ok": True, "mode": MODE, "generated_at": datetime.now(timezone.utc).isoformat(), "data_state": candidates_meta["state"], "data": {"summary": summary, "paper": paper, "ml": ml, "calibration": calibration, "monitoring": monitoring, "insights": insights, "brain": brain, "top_signals": top, "source_meta": source_meta}}


@router.get("/live-center")
def live_center():
    candidates, candidates_meta = _normalize_candidates(120)
    paper, paper_meta = _paper_with_equity()
    brain = build_ai_brain_snapshot()
    alerts = list(brain.get("alerts", []))
    for c in candidates[:16]:
        score = _num(c.get("decision_score"), None)
        risk = _num(c.get("risk_score"), None)
        ev = _num(c.get("true_ev"), None)
        if score is not None and score >= 70:
            alerts.append({"type": "AI_SIGNAL", "severity": "high", "state": "real_data", "title": "Sinal premium aprovado", "message": f"{c.get('home_team') or 'Time A'} x {c.get('away_team') or 'Time B'} | {c.get('market') or 'mercado'} | EV {ev*100:+.1f}%" if ev is not None else "Sinal aprovado, mas EV indisponível."})
        elif risk is not None and risk >= 58:
            alerts.append({"type": "RISK", "severity": "medium", "state": "real_data", "title": "Risco operacional elevado", "message": f"{c.get('league') or 'Liga não informada'} apresenta risk score elevado."})
    if not candidates:
        alerts.append({"type": "NO_DATA", "severity": "info", "state": "no_data", "title": "Sem sinais reais", "message": "Live Center aguardando dados do decision engine."})
    return {"ok": True, "mode": MODE, "data_state": candidates_meta["state"], "data": {"signals": candidates[:40], "bankroll": paper, "equity_curve": _series(paper.get("equity_curve") or []), "alerts": alerts[:10], "ai_brain": brain, "timeline": alerts[:8], "source_meta": {"decision_candidates": candidates_meta, "paper_trading": paper_meta}}}


@router.get("/explainability")
def explainability():
    candidates, candidates_meta = _normalize_candidates(80)
    valid = [c for c in candidates if _num(c.get("decision_score"), None) is not None]
    best = sorted(valid, key=lambda c: _num(c.get("decision_score"), -999) or -999, reverse=True)[0] if valid else None
    factors: list[dict[str, Any]] = []
    radar: list[dict[str, Any]] = []
    if best:
        values = [
            ("Probabilidade ML", _num(best.get("ml_probability"), None), "positive", True),
            ("Valor esperado", _num(best.get("true_ev"), None), "positive", True),
            ("Odds vs prob. implícita", ((_num(best.get("ml_probability"), None) or 0) - (_num(best.get("implied_probability"), None) or 0)) if _num(best.get("ml_probability"), None) is not None and _num(best.get("implied_probability"), None) is not None else None, "positive", True),
            ("Risco operacional", _num(best.get("risk_score"), None), "negative", False),
            ("Kelly recomendado", _num(best.get("kelly_stake_pct"), None), "neutral", True),
        ]
        for name, val, impact, percent_scale in values:
            if val is None:
                continue
            factors.append({"name": name, "value": round(val * 100 if percent_scale else val, 2), "impact": impact, "data_state": "real_data"})
        ev = _num(best.get("true_ev"), None)
        prob = _num(best.get("ml_probability"), None)
        score = _num(best.get("decision_score"), None)
        risk = _num(best.get("risk_score"), None)
        if ev is not None:
            radar.append({"axis": "EV", "value": max(0, min(100, ev * 700)), "data_state": "real_data"})
        if prob is not None:
            radar.append({"axis": "Confiança", "value": prob * 100, "data_state": "real_data"})
        if score is not None:
            radar.append({"axis": "Score", "value": score, "data_state": "real_data"})
        if risk is not None:
            radar.append({"axis": "Risco", "value": max(0, 100 - risk), "data_state": "real_data"})
    return {"ok": True, "mode": MODE, "data_state": _state(bool(best), partial=bool(best and len(factors) < 3)), "data": {"selected_signal": best, "feature_importance": factors, "confidence_breakdown": factors, "radar": radar, "source_meta": {"decision_candidates": candidates_meta}, "message": None if best else "Nenhum sinal real disponível para explicabilidade. SHAP/confidence/drift não são simulados."}}


@router.get("/paper-premium")
def paper_premium():
    paper, paper_meta = _paper_with_equity()
    values = [_num(v, None) for v in (paper.get("equity_curve") or [])]
    values = [float(v) for v in values if v is not None]
    dd: list[float] = []
    if values:
        peak = values[0]
        for v in values:
            peak = max(peak, v)
            dd.append(0 if peak == 0 else (v - peak) / peak * 100)
    risk = {
        "max_drawdown": round(min(dd), 2) if dd else _num(paper.get("max_drawdown"), None),
        "exposure": _num(paper.get("active_exposure"), None),
        "avg_stake": _num(paper.get("avg_stake") or paper.get("average_stake_pct"), None),
        "data_state": _state(bool(dd or paper.get("file_exists")), partial=not bool(dd)),
    }
    streaks = _streaks_from_latest(paper)
    return {"ok": True, "mode": MODE, "data_state": _state(bool(paper.get("file_exists")), partial=not bool(values)), "data": {"summary": paper, "equity_curve": _series(values), "drawdown": _series(dd), "streaks": streaks, "risk": risk, "source_meta": {"paper_trading": paper_meta}, "message": None if paper.get("file_exists") else "Paper trading summary ausente. Métricas visuais não foram preenchidas com dados simulados."}}


@router.get("/analytics")
def premium_analytics():
    candidates, candidates_meta = _normalize_candidates(220)
    data = _analytics(candidates)
    ev_items = []
    for c in candidates[:30]:
        ev = _num(c.get("true_ev"), None)
        if ev is not None:
            ev_items.append({"label": str(c.get("league") or c.get("market") or "Sinal")[:18], "value": round(ev * 100, 2), "data_state": "real_data"})
    trends, trend_meta = _model_trends()
    data["ev_distribution"] = ev_items
    data["model_trends"] = trends
    brain = build_ai_brain_snapshot()
    data["ai_brain"] = brain
    data["league_performance"] = brain.get("analytics", {}).get("league_performance", [])
    data["market_performance"] = brain.get("analytics", {}).get("market_performance", [])
    data["intelligent_alerts"] = brain.get("alerts", [])
    data["source_meta"] = {"decision_candidates": candidates_meta, "model_trends": trend_meta}
    data["message"] = None if candidates else "Analytics premium sem sinais reais disponíveis. Rankings/heatmaps vazios indicam ausência de dados, não performance zero."
    return {"ok": True, "mode": MODE, "data_state": candidates_meta["state"], "data": data}
