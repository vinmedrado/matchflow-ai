from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter

logger = logging.getLogger("matchflow.backend.data_ops")
router = APIRouter(prefix="/api/data-ops", tags=["data-ops"])


def _load_data_ops_modules():
    common = importlib.import_module("07_data_ops.common")
    state = importlib.import_module("07_data_ops.data_ops_state")
    check = importlib.import_module("07_data_ops.check_data_sources")
    return common, state, check


def _build_status_payload() -> Dict[str, Any]:
    common, state_module, _ = _load_data_ops_modules()
    state = state_module.load_state()
    discovery = common.load_json(common.DISCOVERY_REPORT_PATH, {})
    messages = []
    if isinstance(discovery, dict):
        messages.extend(discovery.get("messages", []))
    engine_status = state.get("engine_status", "UNKNOWN")
    future_status = state.get("future_games_status", "UNKNOWN")
    if engine_status == "ENGINE_FOUND_OUTPUTS_EMPTY":
        actionable = "Execute POST /api/data-engine/providers/flashscore/sync ou python run_full_decision_pipeline.py para gerar outputs internos."
    elif engine_status == "ENGINE_MISSING":
        actionable = "O provider FlashScore interno é o fluxo principal."
    elif future_status in {"FUTURE_GAMES_NO_DATA_FILES", "FUTURE_GAMES_EMPTY", "FUTURE_GAMES_MISSING"}:
        actionable = "Verifique a pasta jogos_futuros e gere arquivos JSON/JSONL/CSV/Parquet se quiser alimentar previsões futuras."
    elif engine_status == "ENGINE_READY" and future_status == "FUTURE_GAMES_READY":
        actionable = "Fontes em condição operacional."
    else:
        actionable = "Execute o discovery Data Ops para identificar o estado real das fontes."
    return {
        "engine_status": engine_status,
        "engine_path": state.get("engine_path"),
        "engine_files_count": state.get("engine_files_count", 0),
        "future_games_status": future_status,
        "future_games_path": state.get("future_games_path"),
        "future_games_files_count": state.get("future_games_files_count", 0),
        "last_sync": state.get("last_engine_sync"),
        "last_discovery_at": state.get("last_discovery_at"),
        "messages": messages,
        "actionable_next_step": actionable,
    }


@router.get("/status")
def data_ops_status() -> Dict[str, Any]:
    try:
        payload = _build_status_payload()
        return {"ok": True, "data": payload}
    except Exception as exc:
        logger.exception("Falha ao obter status Data Ops: %s", exc)
        return {"ok": False, "error": {"code": "DATA_OPS_STATUS_ERROR", "message": "Falha ao obter status Data Ops."}}


@router.get("/discovery")
def data_ops_discovery() -> Dict[str, Any]:
    try:
        common, _, check = _load_data_ops_modules()
        report = check.run_check()
        persisted = common.load_json(common.DISCOVERY_REPORT_PATH, report)
        return {"ok": True, "data": persisted}
    except Exception as exc:
        logger.exception("Falha ao executar discovery Data Ops: %s", exc)
        return {"ok": False, "error": {"code": "DATA_OPS_DISCOVERY_ERROR", "message": "Falha ao executar discovery Data Ops."}}


@router.get("/bridge-status")
def bridge_status():
    """Status do FlashScore bridge."""
    from pathlib import Path
    import sys
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "07_data_ops"))
    try:
        from flashscore_bridge import get_bridge_status
        return {"ok": True, "bridge_status": get_bridge_status(root)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/run")
def run_pipeline():
    """Executa pipeline Data Ops completo."""
    import importlib.util
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    path = root / "07_data_ops/run_data_ops.py"
    spec = importlib.util.spec_from_file_location("run_data_ops", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {"ok": True, "result": mod.run_data_ops(root)}


@router.get("/engine-status")
def engine_status():
    """Status do provider FlashScore interno e legado opcional."""
    from pathlib import Path
    import sys
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "07_data_ops"))
    try:
        from data_engine_runner import get_engine_status
        return {"ok": True, "data": get_engine_status(root)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/engine-run")
def engine_run(mode: str = "incremental", days_back: int = 7):
    """Executa provider FlashScore interno em background."""
    from pathlib import Path
    import sys, threading
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "07_data_ops"))
    try:
        from data_engine_runner import run_engine
        # Rodar em thread para não bloquear a API
        def _bg():
            run_engine(saas_root=root, mode=mode, days_back=days_back, stream_logs=False)
        thread = threading.Thread(target=_bg, daemon=True)
        thread.start()
        return {"ok": True, "status": "STARTED", "mode": mode, "days_back": days_back,
                "message": "Provider FlashScore interno iniciado em background. Acompanhe /api/data-engine/providers/flashscore/status"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
