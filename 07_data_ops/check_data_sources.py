from __future__ import annotations

import logging
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from common import DISCOVERY_REPORT_PATH, load_config, write_json  # type: ignore
    from data_ops_state import update_state  # type: ignore
    from engine_discovery import discover_engine  # type: ignore
    from future_games_discovery import discover_future_games  # type: ignore
else:
    from .common import DISCOVERY_REPORT_PATH, load_config, write_json
    from .data_ops_state import update_state
    from .engine_discovery import discover_engine
    from .future_games_discovery import discover_future_games

from backend.core.logging_config import configure_logging

logger = logging.getLogger("matchflow.data_ops.check_data_sources")


def evaluate_status(engine_status: str, future_status: str) -> str:
    if engine_status == "ENGINE_READY" and future_status == "FUTURE_GAMES_READY":
        return "READY"
    if engine_status == "ENGINE_MISSING":
        return "ENGINE_MISSING"
    if engine_status == "ENGINE_FOUND_OUTPUTS_EMPTY":
        return "ENGINE_OUTPUTS_EMPTY"
    if engine_status == "ENGINE_READY" and future_status in {"FUTURE_GAMES_EMPTY", "FUTURE_GAMES_NO_DATA_FILES", "FUTURE_GAMES_MISSING"}:
        return "PARTIAL_READY"
    return "PARTIAL_READY"


def run_check() -> dict:
    config = load_config()
    engine = discover_engine(config=config, write_report=False)
    future = discover_future_games(config=config)
    final_status = evaluate_status(engine["engine_status"], future["future_games_status"])
    report = {
        "final_status": final_status,
        "engine": engine,
        "future_games": future,
        "messages": engine.get("messages", []) + future.get("messages", []),
        "actionable_next_step": engine.get("actionable_next_step") if final_status != "READY" else "Fontes prontas para sincronização e snapshot.",
    }
    write_json(DISCOVERY_REPORT_PATH, report)
    update_state(
        last_discovery_at=engine.get("checked_at"),
        engine_path=engine.get("engine_path"),
        engine_status=engine.get("engine_status"),
        engine_files_count=engine.get("engine_files_count", 0),
        future_games_path=future.get("future_games_path"),
        future_games_status=future.get("future_games_status"),
        future_games_files_count=future.get("future_games_files_count", 0),
    )
    return report


def print_report(report: dict) -> None:
    engine = report.get("engine", {})
    future = report.get("future_games", {})
    lines = [
        "=== MatchFlow Data Ops Check ===",
        f"Engine status: {engine.get('engine_status')}",
        f"Engine path: {engine.get('engine_path')}",
        f"Arquivos históricos: {engine.get('engine_files_count', 0)}",
        f"Jogos futuros status: {future.get('future_games_status')}",
        f"Jogos futuros path: {future.get('future_games_path')}",
        f"Arquivos futuros: {future.get('future_games_files_count', 0)}",
        f"Scripts jogos_futuros: {future.get('scripts_count', 0)}",
        f"Status final: {report.get('final_status')}",
        f"Próximo passo: {report.get('actionable_next_step')}",
    ]
    sys.stdout.write("\n".join(lines) + "\n")


def main() -> int:
    configure_logging()
    report = run_check()
    print_report(report)
    logger.info("Check Data Ops finalizado com status=%s", report.get("final_status"))
    return 0 if report.get("final_status") in {"READY", "PARTIAL_READY"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
