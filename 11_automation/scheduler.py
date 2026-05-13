"""
scheduler.py — Scheduler automático com APScheduler.
Pipeline completo: 7h, 13h, 19h | Liquidação: a cada hora | CLV: a cada 2h.
"""
from __future__ import annotations
import logging, os
from pathlib import Path
from typing import Any

from .common import MODE, load_config, utc_now
from .run_automation import run_automation

logger = logging.getLogger("matchflow.automation.scheduler")


def should_run(last_run_ts: float | None, interval_hours: float) -> bool:
    import time
    if last_run_ts is None:
        return True
    return (time.time() - last_run_ts) >= interval_hours * 3600


def run_scheduler_once(root: Path | None = None) -> dict[str, Any]:
    root = root or Path.cwd()
    return run_automation(root)


def scheduler_status(root: Path | None = None) -> dict[str, Any]:
    root = root or Path.cwd()
    config = load_config(root)
    return {
        "mode": MODE,
        "enabled": bool(config.get("enabled", True)),
        "interval_hours": config.get("interval_hours", 2),
        "checked_at": utc_now(),
        "app_mode": MODE,
        "scheduler_type": "APScheduler" if _apscheduler_available() else "manual",
    }


def _apscheduler_available() -> bool:
    try:
        import apscheduler
        return True
    except ImportError:
        return False


def start_blocking_scheduler(root: Path | None = None) -> None:
    """
    Inicia o scheduler bloqueante com APScheduler.
    Pipeline completo: 7h, 13h, 19h (timezone configurável via .env)
    Liquidação de resultados: a cada hora
    Monitoramento de odds: a cada 30 minutos
    """
    root = root or Path.cwd()

    if not _apscheduler_available():
        logger.error("APScheduler não instalado. Execute: pip install apscheduler")
        logger.info("Usando fallback: executando pipeline uma vez e saindo.")
        run_automation(root)
        return

    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger

    tz = os.getenv("SCHEDULER_TIMEZONE", "America/Sao_Paulo")
    run_hours = os.getenv("SCHEDULER_RUN_HOURS", "7,13,19")

    scheduler = BlockingScheduler(timezone=tz)

    # Pipeline completo 3x por dia
    run_hours_list = [h.strip() for h in run_hours.split(",") if h.strip().isdigit()]
    for hour in run_hours_list:
        scheduler.add_job(
            func=lambda r=root: _run_full_pipeline(r),
            trigger=CronTrigger(hour=int(hour), minute=0, timezone=tz),
            id=f"full_pipeline_{hour}h",
            name=f"Pipeline Completo {hour}h",
            replace_existing=True,
            misfire_grace_time=300,
        )
        logger.info("Pipeline completo agendado: %sh00 (%s)", hour, tz)

    # Engine FlashScore: roda 1h antes do pipeline (6h, 12h, 18h)
    engine_hours = [str(int(h) - 1) for h in run_hours_list if int(h) > 0]
    for hour in engine_hours:
        scheduler.add_job(
            func=lambda r=root: _run_engine_job(r),
            trigger=CronTrigger(hour=int(hour), minute=50, timezone=tz),
            id=f"data_engine_{hour}h50",
            name=f"FlashScore Engine {hour}h50",
            replace_existing=True,
            misfire_grace_time=600,
        )
        logger.info("FlashScore Engine agendado: %sh50 (%s)", hour, tz)


    # Liquidação de resultados a cada hora
    scheduler.add_job(
        func=lambda r=root: _run_result_settler(r),
        trigger=CronTrigger(minute=15, timezone=tz),  # :15 de cada hora
        id="result_settler_hourly",
        name="Liquidação de Resultados",
        replace_existing=True,
        misfire_grace_time=120,
    )
    logger.info("Liquidação agendada: a cada hora (%s)", tz)

    # Monitor de odds a cada 30 minutos
    scheduler.add_job(
        func=lambda r=root: _run_odds_monitor(r),
        trigger=CronTrigger(minute="0,30", timezone=tz),
        id="odds_monitor_30min",
        name="Monitor de Odds",
        replace_existing=True,
        misfire_grace_time=60,
    )
    logger.info("Monitor de odds agendado: a cada 30 minutos (%s)", tz)

    logger.info("=" * 60)
    logger.info("MatchFlow Scheduler iniciado | Modo: %s | TZ: %s", MODE, tz)
    logger.info("=" * 60)

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler interrompido pelo usuário.")
        scheduler.shutdown()



def _run_engine_job(root: Path) -> None:
    try:
        import sys
        sys.path.insert(0, str(root / "07_data_ops"))
        from data_engine_runner import run_engine
        logger.info("[Scheduler] Iniciando FlashScore Engine (incremental)...")
        result = run_engine(saas_root=root, mode="incremental", days_back=7,
                            timeout_seconds=3600, stream_logs=False)
        logger.info("[Scheduler] Engine: status=%s rows=%s duration=%ss",
                    result.get("status"), result.get("rows_loaded"), result.get("duration_s"))
    except Exception as exc:
        logger.exception("[Scheduler] Engine falhou: %s", exc)


def _run_full_pipeline(root: Path) -> None:
    logger.info("[Scheduler] Iniciando pipeline completo...")
    try:
        result = run_automation(root)
        status = result.get("status", "UNKNOWN")
        logger.info("[Scheduler] Pipeline completo: status=%s", status)
        # Notificar falha via Telegram
        if status != "SUCCESS":
            try:
                from telegram_notifier import send_pipeline_status
                send_pipeline_status(result)
            except Exception:
                pass
    except Exception as exc:
        logger.exception("[Scheduler] Falha no pipeline: %s", exc)


def _run_result_settler(root: Path) -> None:
    try:
        import sys
        sys.path.insert(0, str(root / "07_data_ops"))
        from result_settler import settle_pending_bets
        result = settle_pending_bets(root)
        logger.info("[Scheduler] Liquidação: settled=%s", result.get("settled_now", 0))
    except Exception as exc:
        logger.warning("[Scheduler] Liquidação falhou: %s", exc)


def _run_odds_monitor(root: Path) -> None:
    try:
        import sys
        sys.path.insert(0, str(root / "07_data_ops"))
        from odds_monitor import build_odds_movement_report
        result = build_odds_movement_report(root)
        sharp = result.get("sharp_movements", 0)
        if sharp > 0:
            logger.info("[Scheduler] Odds monitor: %s movimentos sharp detectados", sharp)
    except Exception as exc:
        logger.debug("[Scheduler] Odds monitor falhou: %s", exc)
