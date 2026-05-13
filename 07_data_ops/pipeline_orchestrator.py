"""pipeline_orchestrator.py v7.0 — FlashScore bridge como fonte primária."""
from __future__ import annotations
import logging, sys
from pathlib import Path
from typing import Any, Dict

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from check_data_sources import run_check
    from common import INCREMENTAL_REPORT_PATH, load_config, utc_now_iso, write_json
    from data_ops_state import update_state
    from engine_sync import sync_engine_outputs
    from future_games_loader import load_future_games_snapshot
else:
    from .check_data_sources import run_check
    from .common import INCREMENTAL_REPORT_PATH, load_config, utc_now_iso, write_json
    from .data_ops_state import update_state
    from .engine_sync import sync_engine_outputs
    from .future_games_loader import load_future_games_snapshot

logger = logging.getLogger("matchflow.data_ops.pipeline_orchestrator")


def _run_flashscore_bridge(root: Path) -> dict:
    """Executa provider FlashScore interno como fonte primária."""
    try:
        from backend.services.data_engine.providers.flashscore import run_flashscore_sync
        result = run_flashscore_sync()
        return {"status": "OK" if result.get("ok", True) else "FAILED", "rows": result.get("total_records", 0), "internal_provider": True, "warnings": result.get("warnings", [])}
    except Exception as exc:
        logger.warning("Provider FlashScore interno falhou (não crítico): %s", exc)
        return {"status": "ERROR", "error": str(exc), "rows": 0, "internal_provider": True}

def _run_odds_fetcher(root: Path) -> dict:
    """Busca odds atuais via The Odds API."""
    try:
        sys.path.insert(0, str(root / "07_data_ops"))
        from odds_fetcher import fetch_all_odds
        df = fetch_all_odds(output_dir=root / "data/odds")
        return {"status": "OK", "rows": len(df)}
    except Exception as exc:
        logger.debug("Odds fetcher: %s", exc)
        return {"status": "SKIPPED", "reason": str(exc)}


def run_data_ops_pipeline(config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    root = Path.cwd()
    config = config or load_config()

    # ── Etapa 0: FlashScore bridge (FONTE PRIMÁRIA) ────────────────
    bridge_result = _run_flashscore_bridge(root)
    logger.info("FlashScore bridge: status=%s rows=%s",
                bridge_result.get("status"), bridge_result.get("rows", 0))

    # ── Etapa 0b: Odds em tempo real ───────────────────────────────
    odds_result = _run_odds_fetcher(root)

    # ── Etapa 1: Check e sync legado (compatibilidade) ─────────────
    check = run_check()
    engine_status = check.get("engine", {}).get("engine_status")
    sync = None

    if engine_status == "ENGINE_READY":
        sync = sync_engine_outputs(config)
    else:
        sync = {"status": "SKIPPED", "reason": engine_status}

    # ── Etapa 2: Jogos futuros ─────────────────────────────────────
    future_snapshot = load_future_games_snapshot(config)
    paper_update = {"attempted": False, "status": "SKIPPED"}
    ml_update = {"attempted": False, "status": "SKIPPED"}

    if future_snapshot.get("rows", 0) > 0:
        if config.get("update_paper_trading", True):
            paper_update = {"attempted": True, "status": "READY_FOR_MANUAL_PIPELINE"}
            update_state(last_paper_trading_update=utc_now_iso())
        if config.get("update_ml_predictions", True) and not config.get("auto_retrain_ml", False):
            ml_update = {"attempted": True, "status": "READY_FOR_PREDICTIONS_ONLY"}
            update_state(last_ml_prediction_update=utc_now_iso())

    # Determinar status final
    bridge_ok = bridge_result.get("status") in ("OK", "ALREADY_LOADED")
    final_status = "READY" if bridge_ok else check.get("final_status", "NOT_READY")

    report = {
        "ran_at": utc_now_iso(),
        "final_status": final_status,
        "flashscore_bridge": bridge_result,
        "odds_fetcher": odds_result,
        "check": check,
        "engine_sync": sync,
        "future_games_snapshot": future_snapshot,
        "paper_trading_update": paper_update,
        "ml_prediction_update": ml_update,
    }
    write_json(INCREMENTAL_REPORT_PATH, report)
    logger.info("Data Ops v7.0 finalizado: status=%s bridge=%s rows=%s",
                final_status, bridge_result.get("status"), bridge_result.get("rows", 0))
    return report
