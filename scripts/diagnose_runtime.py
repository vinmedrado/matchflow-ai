#!/usr/bin/env python3
"""Diagnóstico rápido de runtime do MatchFlow."""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from matchflow_imports import import_from_dir


def check_pkg(name: str, required: bool = True) -> dict:
    try:
        importlib.import_module(name)
        return {"name": name, "ok": True, "required": required}
    except Exception as exc:
        return {"name": name, "ok": False, "required": required, "error": str(exc)}


def main() -> int:
    checks = []
    checks.extend([
        check_pkg("pandas"),
        check_pkg("numpy"),
        check_pkg("sklearn"),
        check_pkg("joblib"),
        check_pkg("fastapi", required=False),
        check_pkg("apscheduler", required=False),
        check_pkg("scipy", required=False),
    ])

    print("\nMatchFlow Runtime Doctor")
    print("=" * 32)
    for item in checks:
        marker = "OK" if item["ok"] else ("MISSING" if item["required"] else "OPTIONAL")
        print(f"[{marker:<8}] {item['name']}")

    try:
        scheduler = import_from_dir("matchflow_automation", ROOT / "11_automation", "scheduler")
        status = scheduler.scheduler_status(ROOT)
        print(f"[OK      ] scheduler importado | tipo={status.get('scheduler_type')} | mode={status.get('mode')}")
    except Exception as exc:
        print(f"[FAILED  ] scheduler import: {exc}")
        return 1

    for var in ["APP_MODE", "FOOTBALL_DATA_API_KEY", "ODDS_API_KEY", "TELEGRAM_BOT_TOKEN", "GROQ_API_KEY"]:
        value = os.getenv(var, "")
        configured = bool(value and not value.startswith("seu_") and "aqui" not in value)
        print(f"[{'OK' if configured else 'WARN':<8}] {var}={'configurado' if configured else 'não configurado'}")

    missing_required = [i["name"] for i in checks if i["required"] and not i["ok"]]
    if missing_required:
        print("\nInstale dependências críticas:")
        print("pip install -r requirements.txt")
        return 1

    print("\nDiagnóstico concluído.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
