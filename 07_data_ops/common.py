from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

LOGGER_NAME = "matchflow.data_ops"
logger = logging.getLogger(LOGGER_NAME)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "data_ops_config.json"
OPS_DIR = PROJECT_ROOT / "data" / "ops"
STATE_PATH = OPS_DIR / "data_ops_state.json"
DISCOVERY_REPORT_PATH = OPS_DIR / "discovery_report.json"
SYNC_REPORT_PATH = OPS_DIR / "sync_report.json"
FUTURE_SNAPSHOT_PATH = OPS_DIR / "future_games_snapshot.parquet"
INCREMENTAL_REPORT_PATH = OPS_DIR / "incremental_run_report.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_ops_dirs() -> None:
    OPS_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Falha ao ler JSON %s: %s", path, exc)
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def load_config(config_path: Path | None = None) -> Dict[str, Any]:
    path = config_path or DEFAULT_CONFIG_PATH
    config = load_json(path, {})
    if not config:
        raise FileNotFoundError(f"Configuração Data Ops não encontrada ou inválida: {path}")
    return config


def resolve_path(candidate: str | Path, base: Path = PROJECT_ROOT) -> Path:
    p = Path(candidate).expanduser()
    if not p.is_absolute():
        p = (base / p).resolve()
    return p


def supported_files(root: Path, formats: Iterable[str]) -> List[Path]:
    suffixes = {fmt.lower() if fmt.startswith(".") else f".{fmt.lower()}" for fmt in formats}
    if not root.exists() or not root.is_dir():
        return []
    files: List[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in suffixes:
            try:
                if path.stat().st_size > 0:
                    files.append(path)
            except OSError:
                continue
    return sorted(files)


def file_checksum(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path: Path, root: Path) -> Dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path.resolve()),
        "relative_path": str(path.resolve().relative_to(root.resolve())) if root.exists() else str(path.name),
        "modified_time": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "size_bytes": stat.st_size,
        "checksum": file_checksum(path),
    }
