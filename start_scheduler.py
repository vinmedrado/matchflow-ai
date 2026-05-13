#!/usr/bin/env python3
"""
start_scheduler.py — Entry point do MatchFlow Scheduler.
Execute: python start_scheduler.py
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from matchflow_imports import import_from_dir

# Criar diretório de logs
(ROOT / "logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(ROOT / "logs" / "scheduler.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger("matchflow.start_scheduler")


def check_dependencies() -> None:
    missing: list[str] = []
    optional_warn: list[tuple[str, str]] = []

    for pkg in ["pandas", "numpy", "sklearn", "joblib"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    for pkg, reason in [
        ("httpx", "APIs externas (football-data.org, Groq, Telegram)"),
        ("apscheduler", "Scheduler automático — necessário para agendamento"),
        ("scipy", "Testes de significância estatística"),
    ]:
        try:
            __import__(pkg)
        except ImportError:
            optional_warn.append((pkg, reason))

    if missing:
        logger.error("Dependências CRÍTICAS faltando: %s", missing)
        logger.error("Execute: pip install %s", " ".join(missing))
        sys.exit(1)

    for pkg, reason in optional_warn:
        logger.warning("Opcional não instalado: %s — %s", pkg, reason)

    for var, importance in [
        ("FOOTBALL_DATA_API_KEY", "dados históricos"),
        ("ODDS_API_KEY", "odds em tempo real"),
        ("TELEGRAM_BOT_TOKEN", "notificações (opcional)"),
        ("GROQ_API_KEY", "AI assistant (opcional)"),
    ]:
        val = os.getenv(var, "")
        if not val or "seu_token" in val or "seu_bot_token" in val:
            logger.warning("Não configurado: %s (%s)", var, importance)
        else:
            logger.info("✓ %s configurado", var)


def main() -> int:
    logger.info("=" * 55)
    logger.info("  MatchFlow Analytics v7.0 — Iniciando Scheduler")
    logger.info("=" * 55)

    check_dependencies()

    try:
        sched_mod = import_from_dir("matchflow_automation", ROOT / "11_automation", "scheduler")
        sched_mod.start_blocking_scheduler(ROOT)
        return 0
    except KeyboardInterrupt:
        logger.info("Scheduler parado pelo usuário.")
        return 0
    except Exception as exc:
        logger.exception("Falha ao iniciar scheduler: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
