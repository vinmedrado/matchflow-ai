from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAPER_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PAPER_ROOT) not in sys.path:
    sys.path.insert(0, str(PAPER_ROOT))

from backend.core.logging_config import configure_logging, get_logger
from paper_engine import PaperTradingEngine
from paper_journal import PaperJournal
from signal_selector import PaperSignalSelector

configure_logging()
logger = get_logger("matchflow.paper.runner")


def load_config(project_root: Path = PROJECT_ROOT) -> Dict[str, Any]:
    config_path = project_root / "config" / "paper_trading_config.json"
    if not config_path.exists():
        logger.warning("Config paper ausente, usando defaults seguros: %s", config_path)
        return {"initial_bankroll": 100.0, "stake_mode": "fixed", "fixed_stake": 1.0, "allowed_recommendations": ["KEEP"], "max_signals_per_day": 10, "min_consistency_score": 60, "min_sample_size": 100, "allow_watch_strategies": False, "paper_only": True, "resolution_delay_days": 1}
    return json.loads(config_path.read_text(encoding="utf-8"))


def _current_date_from_dataset(project_root: Path) -> pd.Timestamp:
    path = project_root / "data" / "features" / "team_dataset_advanced.parquet"
    if not path.exists():
        logger.warning("Dataset avançado ausente; usando data UTC atual para ciclo paper.")
        return pd.Timestamp.utcnow().normalize()
    try:
        df = safe_read_dataframe(path, columns=["date"])
        current = pd.to_datetime(df["date"], errors="coerce").max()
        return current.normalize() if pd.notna(current) else pd.Timestamp.utcnow().normalize()
    except Exception as exc:
        logger.warning("Falha ao inferir data do dataset avançado: %s", exc)
        return pd.Timestamp.utcnow().normalize()


def run_paper_trading() -> Dict[str, Any]:
    config = load_config()
    if not bool(config.get("paper_only", True)):
        raise RuntimeError("Paper trading config must remain paper_only=true in Patch 4.4.1")

    logger.info("Iniciando paper trading temporal incremental local/simulado")
    engine = PaperTradingEngine(PROJECT_ROOT, config)
    state = engine.load_state()
    current_date = pd.to_datetime(config.get("current_date"), errors="coerce") if config.get("current_date") else _current_date_from_dataset(PROJECT_ROOT)
    if pd.isna(current_date):
        current_date = pd.Timestamp.utcnow().normalize()
    last_processed_date = pd.to_datetime(state.get("last_processed_date"), errors="coerce") if state.get("last_processed_date") else None

    selector = PaperSignalSelector(PROJECT_ROOT, config)
    new_signals = selector.select_signals(current_date=current_date, last_processed_date=last_processed_date, existing_signal_ids=engine.existing_signal_ids())
    saved_signals, results, equity, summary = engine.run(new_signals, current_date=current_date)
    PaperJournal(PROJECT_ROOT).write(saved_signals, summary, selector.ignored_reasons)
    logger.info("Paper trading concluído: total=%s pending=%s settled=%s bankroll=%.2f", summary.get("total_signals", 0), summary.get("pending_signals", 0), summary.get("settled_signals", 0), summary.get("current_bankroll", 0.0))
    return summary


def main() -> None:
    summary = run_paper_trading()
    logger.info("Resumo paper: %s", summary)


if __name__ == "__main__":
    main()
