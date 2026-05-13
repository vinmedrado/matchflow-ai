from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from .common import PROJECT_ROOT, load_config, resolve_path, supported_files, utc_now_iso
except ImportError:
    from common import PROJECT_ROOT, load_config, resolve_path, supported_files, utc_now_iso

logger = logging.getLogger("matchflow.data_ops.future_games_discovery")


def discover_future_games(config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    config = config or load_config()
    formats = set(config.get("accepted_file_formats", [".json", ".jsonl", ".csv", ".parquet"]))
    candidates: List[Path] = []
    override = os.getenv("FUTURE_GAMES_PATH")
    if override: candidates.append(resolve_path(override))
    for candidate in config.get("future_games_candidates", []):
        candidates.append(resolve_path(candidate, PROJECT_ROOT))
    checked: List[str] = []
    selected: Optional[Path] = None
    for candidate in candidates:
        checked.append(str(candidate))
        if candidate.exists() and candidate.is_dir():
            selected = candidate
            break
    if selected is None:
        logger.warning("Pasta de jogos futuros não encontrada. Caminhos checados: %s", checked)
        return {"checked_at": utc_now_iso(), "future_games_status": "FUTURE_GAMES_MISSING", "future_games_path": None, "checked_paths": checked, "future_games_files_count": 0, "scripts_count": 0, "data_files": [], "scripts": [], "messages": ["Pasta de jogos futuros não encontrada."], "actionable_next_step": "Crie ou restaure a pasta jogos_futuros no football-saas, ou configure FUTURE_GAMES_PATH."}
    data_files = supported_files(selected, formats)
    scripts = sorted([p for p in selected.rglob("*.py") if p.is_file()])
    if data_files:
        status = "FUTURE_GAMES_READY"; messages = [f"Pasta de jogos futuros encontrada com {len(data_files)} arquivos de dados e {len(scripts)} scripts."]; next_step = "Pode gerar o snapshot de jogos futuros."
    elif scripts:
        status = "FUTURE_GAMES_NO_DATA_FILES"; messages = ["Pasta jogos_futuros encontrada, mas contém apenas scripts e nenhum arquivo de dados suportado."]; next_step = "Execute os scripts de jogos_futuros para gerar JSON/JSONL/CSV/Parquet antes de alimentar paper/ML futuro."
    else:
        status = "FUTURE_GAMES_EMPTY"; messages = ["Pasta jogos_futuros encontrada, mas está vazia para dados suportados."]; next_step = "Gere arquivos de jogos futuros ou configure FUTURE_GAMES_PATH."
    logger.info("Future games status=%s path=%s data_files=%s scripts=%s", status, selected, len(data_files), len(scripts))
    return {"checked_at": utc_now_iso(), "future_games_status": status, "future_games_path": str(selected), "checked_paths": checked, "future_games_files_count": len(data_files), "scripts_count": len(scripts), "data_files": [str(p) for p in data_files], "scripts": [str(p) for p in scripts], "messages": messages, "actionable_next_step": next_step}
