"""automation_service.py v7.0 — expõe APP_MODE, Telegram status, scheduler, CLV alert."""
from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any
import pandas as pd

def normalized_app_mode() -> str:
    raw = os.getenv("APP_MODE", "PAPER_TRADING_SIMULATION_ONLY").upper()
    if raw == "LIVE_RESEARCH":
        return "LIVE_RESEARCH"
    return "PAPER_TRADING_SIMULATION_ONLY"

MODE = normalized_app_mode()

def project_root() -> Path:
    return Path(__file__).resolve().parents[2]

def _json(path: Path, default: Any = None) -> Any:
    if default is None: default = {}
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except Exception:
        return default

def _csv(path: Path, limit: int = 50) -> list[dict]:
    try:
        if not path.exists() or path.stat().st_size == 0: return []
        return pd.read_csv(path).head(limit).fillna("").to_dict(orient="records")
    except Exception:
        return []

def run_automation_service() -> dict[str, Any]:
    root = project_root()
    import sys
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from matchflow_imports import import_from_dir
    mod = import_from_dir("matchflow_automation", root / "11_automation", "run_automation")
    return mod.run_automation(root)

def automation_status() -> dict[str, Any]:
    root = project_root()
    state   = _json(root / "data/automation/automation_state.json", {})
    last    = _json(root / "data/automation/last_run_summary.json", {})
    dispatched = _json(root / "data/automation/alerts_dispatched.json", {"events": []})
    exports = _csv(root / "data/automation/exported_candidates.csv", limit=10)

    if not state:
        state = {"overall_status": "NOT_RUN", "message": "Pipeline ainda não executado."}

    # Telegram status
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    tg_configured = bool(tg_token and tg_token != "seu_bot_token_aqui")
    tg_log = _json(root / "data/automation/telegram_log.json", [])
    tg_sent = len(tg_log) if isinstance(tg_log, list) else 0

    # Groq/AI status
    groq_key = os.getenv("GROQ_API_KEY", "")
    groq_ok = bool(groq_key and groq_key != "seu_token_aqui")

    # Scheduler status
    try:
        import apscheduler
        scheduler_available = True
    except ImportError:
        scheduler_available = False

    # CLV health
    clv_metrics = {}
    try:
        import sys
        sys.path.insert(0, str(root / "09_decision_engine"))
        from clv_tracker import get_clv_metrics
        clv_metrics = get_clv_metrics(root)
    except Exception:
        pass

    # Performance attribution
    perf = _json(root / "data/performance/performance_attribution.json", {})
    edge_ok = perf.get("edge_health", {}).get("edge_deteriorating") == False
    recommendation = perf.get("edge_health", {}).get("recommendation", "AGUARDAR_DADOS")

    return {
        "mode": MODE,
        "app_mode": normalized_app_mode(),
        "paper_only": MODE != "LIVE_RESEARCH",
        "state": state,
        "last_run": last,
        "overall_status": state.get("overall_status", last.get("status", "NOT_RUN")),
        "last_run_at": last.get("started_at"),
        "exported_candidates_count": len(exports),
        "alerts_dispatched_count": len(dispatched.get("events", [])) if isinstance(dispatched, dict) else 0,
        "integrations": {
            "telegram_configured": tg_configured,
            "telegram_messages_sent": tg_sent,
            "groq_ai_configured": groq_ok,
            "apscheduler_available": scheduler_available,
            "football_data_api": bool(os.getenv("FOOTBALL_DATA_API_KEY", "") not in ("", "seu_token_aqui")),
            "odds_api": bool(os.getenv("ODDS_API_KEY", "") not in ("", "seu_token_aqui")),
        },
        "edge_health": {
            "clv_last_30d_pct": clv_metrics.get("mean_clv_last_30d_pct", 0),
            "beating_market": clv_metrics.get("is_beating_market", False),
            "edge_deteriorating": clv_metrics.get("edge_deteriorating", False),
            "recommendation": recommendation,
        },
        "scheduler_run_hours": os.getenv("SCHEDULER_RUN_HOURS", "7,13,19"),
        "scheduler_timezone": os.getenv("SCHEDULER_TIMEZONE", "America/Sao_Paulo"),
    }

def automation_history() -> dict[str, Any]:
    history = _json(project_root() / "data/automation/job_history.json", {"runs": []})
    history["mode"] = MODE
    return history

def automation_report() -> dict[str, Any]:
    root = project_root()
    path = root / "data/automation/daily_report.md"
    content = path.read_text(encoding="utf-8") if path.exists() else "Relatório ainda não gerado. Execute o pipeline completo."
    return {"mode": MODE, "exists": path.exists(), "content": content}
