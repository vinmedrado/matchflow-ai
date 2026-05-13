"""
common.py — Configuração central do módulo de automação.
Suporta APP_MODE=PAPER_TRADING_SIMULATION_ONLY | LIVE_RESEARCH via variável de ambiente.
"""
from __future__ import annotations
import json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# APP_MODE controlado por .env — nunca hardcoded
_APP_MODE = os.getenv("APP_MODE", "PAPER_TRADING_SIMULATION_ONLY").upper()
MODE = "LIVE_RESEARCH" if _APP_MODE == "LIVE_RESEARCH" else "PAPER_TRADING_SIMULATION_ONLY"
IS_LIVE = MODE == "LIVE_RESEARCH"

# Em modo PAPER_TRADING_SIMULATION_ONLY, bloquear vocabulário operacional no output
FORBIDDEN_TERMS = ["BET", "APOSTAR", "STAKE", "REAL_TRADE", "REAL_ENTRY"] if not IS_LIVE else []


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any = None) -> Any:
    if default is None:
        default = {}
    try:
        if not path.exists() or path.stat().st_size == 0:
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def load_config(root: Path) -> dict[str, Any]:
    base = {
        "mode": MODE,
        "enabled": True,
        "interval_hours": 2,
        "run_ml_training": False,
        "jobs": ["odds_fetcher", "data_ops", "result_settler", "test_lab",
                 "decision_engine", "monitoring", "clv_tracker", "performance_report"],
        "export": {
            "allowed_confidence_bands": ["HIGH_CONFIDENCE_SIMULATION", "MEDIUM_CONFIDENCE_SIMULATION"],
            "output_path": "data/automation/exported_candidates.csv",
        },
        "alerts": {
            "webhook_enabled": False,
            "webhook_url": "",
            "telegram_enabled": bool(os.getenv("TELEGRAM_BOT_TOKEN", "")),
        },
        "safety": {
            "paper_only": not IS_LIVE,
            "forbidden_terms": FORBIDDEN_TERMS,
        },
    }
    cfg_path = root / "config/automation_config.json"
    if cfg_path.exists():
        try:
            from_file = json.loads(cfg_path.read_text(encoding="utf-8"))
            # Merge: valores do arquivo sobrescrevem default
            base.update(from_file)
        except Exception:
            pass
    return base


def automation_dir(root: Path) -> Path:
    path = root / "data/automation"
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    for term in FORBIDDEN_TERMS:
        text = text.replace(term, "SIMULATION").replace(term.lower(), "simulation")
    return text
