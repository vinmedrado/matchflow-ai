"""
alert_dispatcher.py — Despacho de alertas via Telegram e log interno.
Integra candidatos HIGH_CONFIDENCE com notificações em tempo real.
"""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Any

from .automation_state import mark_alert_dispatch
from .common import MODE, automation_dir, load_config, load_json, save_json, sanitize_text, utc_now

logger = logging.getLogger("matchflow.automation.alert_dispatcher")


def _load_monitoring_alerts(root: Path) -> list[dict]:
    data = load_json(root / "data/monitoring/alerts.json", {})
    alerts = data.get("alerts", []) if isinstance(data, dict) else []
    return [a for a in alerts if isinstance(a, dict)]


def _load_high_confidence_candidates(root: Path) -> list[dict]:
    """Carrega candidatos HIGH_CONFIDENCE do decision engine."""
    import pandas as pd
    path = root / "data/decision_engine/decision_candidates.csv"
    if not path.exists():
        return []
    try:
        df = pd.read_csv(path)
        if df.empty:
            return []
        if "confidence_band" in df.columns:
            df = df[df["confidence_band"].str.contains("HIGH_CONFIDENCE", na=False)]
        if "kelly_stake_pct" in df.columns:
            df = df[df["kelly_stake_pct"].fillna(0) > 0]
        return df.to_dict(orient="records")
    except Exception as exc:
        logger.warning("Falha ao carregar candidatos: %s", exc)
        return []


def dispatch_alerts(root: Path | None = None) -> dict[str, Any]:
    root = root or Path.cwd()
    config = load_config(root)
    alerts = _load_monitoring_alerts(root)
    candidates = _load_high_confidence_candidates(root)
    events = []

    # Despachar alertas de monitoramento
    for alert in alerts:
        events.append({
            "mode": MODE,
            "dispatched_at": utc_now(),
            "channel": "internal_log",
            "type": "monitoring_alert",
            "severity": sanitize_text(alert.get("severity", "INFO")),
            "category": sanitize_text(alert.get("category", "system")),
            "code": sanitize_text(alert.get("code", "ALERT")),
            "message": sanitize_text(alert.get("message", "")),
            "status": "RECORDED",
        })

    # Despachar candidatos HIGH_CONFIDENCE via Telegram
    telegram_result = {"sent": 0, "skipped": 0, "errors": 0, "configured": False}
    if candidates:
        try:
            from telegram_notifier import notify_high_confidence_candidates
            telegram_result = notify_high_confidence_candidates(candidates, root)
        except ImportError:
            try:
                import sys
                sys.path.insert(0, str(Path(__file__).resolve().parent))
                from telegram_notifier import notify_high_confidence_candidates
                telegram_result = notify_high_confidence_candidates(candidates, root)
            except Exception as exc:
                logger.warning("Telegram notifier não disponível: %s", exc)

        for c in candidates:
            events.append({
                "mode": MODE,
                "dispatched_at": utc_now(),
                "channel": "telegram" if telegram_result.get("configured") else "internal_log",
                "type": "high_confidence_candidate",
                "match": f"{c.get('home_team')} x {c.get('away_team')}",
                "market": c.get("market"),
                "score": c.get("decision_score"),
                "kelly_stake_pct": c.get("kelly_stake_pct"),
                "true_ev": c.get("true_ev"),
                "status": "DISPATCHED",
            })

    payload = {
        "mode": MODE,
        "total_dispatched": len(events),
        "monitoring_alerts": len(alerts),
        "high_confidence_candidates": len(candidates),
        "telegram": telegram_result,
        "events": events,
    }
    save_json(automation_dir(root) / "alerts_dispatched.json", payload)
    mark_alert_dispatch(root)

    logger.info(
        "Alertas despachados: monitoring=%s candidates=%s telegram_sent=%s",
        len(alerts), len(candidates), telegram_result.get("sent", 0)
    )
    return payload
