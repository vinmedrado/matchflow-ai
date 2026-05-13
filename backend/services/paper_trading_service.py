from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from backend.core.logging_config import get_logger

logger = get_logger("matchflow.paper_service")


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else project_root() / p


def paper_trading_summary(directory: str | Path = "data/paper_trading") -> Dict[str, Any]:
    output_dir = _resolve(directory)
    summary_path = output_dir / "paper_summary.json"
    signals_path = output_dir / "paper_signals.csv"
    state_path = output_dir / "paper_state.json"

    if not summary_path.exists():
        logger.warning("Resumo paper trading ausente: %s", summary_path)
        return {"file_exists": False, "paper_only": True, "total_signals": 0, "settled_signals": 0, "pending_signals": 0, "ROI": 0.0, "roi": 0.0, "current_bankroll": 100.0, "max_drawdown": 0.0, "latest_signals": [], "state_exists": state_path.exists(), "message": "Paper trading summary not found. Run python run_paper_trading_pipeline.py"}

    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("Falha ao ler paper_summary.json: %s", exc)
        return {"file_exists": True, "paper_only": True, "total_signals": 0, "settled_signals": 0, "pending_signals": 0, "ROI": 0.0, "roi": 0.0, "current_bankroll": 100.0, "max_drawdown": 0.0, "latest_signals": [], "state_exists": state_path.exists(), "message": f"Invalid paper summary: {exc}"}

    latest = []
    if signals_path.exists():
        try:
            signals = pd.read_csv(signals_path)
            latest = signals.tail(10).to_dict(orient="records") if not signals.empty else []
        except Exception as exc:
            logger.warning("Falha ao ler sinais paper para summary: %s", exc)

    logger.info("Resumo paper trading carregado: signals=%s bankroll=%s", summary.get("total_signals"), summary.get("current_bankroll"))
    return {
        "file_exists": True,
        "paper_only": bool(summary.get("paper_only", True)),
        "total_signals": int(summary.get("total_signals", 0)),
        "settled_signals": int(summary.get("settled_signals", 0)),
        "pending_signals": int(summary.get("pending_signals", 0)),
        "new_signals_today": int(summary.get("new_signals_today", 0)),
        "resolved_signals_today": int(summary.get("resolved_signals_today", 0)),
        "daily_pnl": float(summary.get("daily_pnl", 0.0) or 0.0),
        "active_exposure": float(summary.get("active_exposure", 0.0) or 0.0),
        "ROI": float(summary.get("ROI", summary.get("roi", 0.0)) or 0.0),
        "roi": float(summary.get("roi", summary.get("ROI", 0.0)) or 0.0),
        "current_bankroll": float(summary.get("current_bankroll", 100.0) or 100.0),
        "max_drawdown": float(summary.get("max_drawdown", 0.0) or 0.0),
        "latest_signals": latest,
        "state_exists": state_path.exists(),
        "paths": {"summary": str(summary_path), "signals": str(signals_path), "results": str(output_dir / "paper_results.csv"), "equity_curve": str(output_dir / "paper_equity_curve.csv"), "journal": str(output_dir / "paper_journal.md"), "state": str(state_path)},
    }
