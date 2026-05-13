"""paper_trading.py — API com equity curve, win_rate e CLV integrados."""
from __future__ import annotations
import json
from pathlib import Path
from fastapi import APIRouter
from backend.core.logging_config import get_logger
from backend.services.paper_trading_service import paper_trading_summary

logger = get_logger("matchflow.api.paper_trading")
router = APIRouter(prefix="/api/paper-trading", tags=["paper-trading"])

def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]

@router.get("/summary")
def get_paper_trading_summary():
    root = _project_root()
    data = paper_trading_summary()
    # Injetar equity curve
    try:
        import pandas as pd
        eq_path = root / "data/paper_trading/paper_equity_curve.csv"
        if eq_path.exists():
            eq = pd.read_csv(eq_path)
            col = next((c for c in ["bankroll_after", "equity_curve", "cumulative_profit"] if c in eq.columns), None)
            if col:
                data["equity_curve"] = eq[col].dropna().tolist()
    except Exception:
        pass
    # Injetar CLV metrics
    try:
        import sys
        sys.path.insert(0, str(root / "09_decision_engine"))
        from clv_tracker import get_clv_metrics
        data["clv"] = get_clv_metrics(root)
    except Exception:
        pass
    # Injetar performance attribution
    try:
        perf_path = root / "data/performance/performance_attribution.json"
        if perf_path.exists():
            perf = json.loads(perf_path.read_text())
            data["win_rate"] = perf.get("win_rate")
            data["total_trades"] = perf.get("total_trades")
            data["total_wins"] = perf.get("wins")
            data["total_losses"] = perf.get("losses")
            data["total_profit"] = perf.get("total_profit")
            data["roi"] = perf.get("total_roi")
    except Exception:
        pass
    logger.info("Paper trading summary carregado")
    return {"ok": True, "data": data}

@router.get("/signals")
def get_signals():
    root = _project_root()
    try:
        import pandas as pd
        path = root / "data/paper_trading/paper_signals.csv"
        if not path.exists():
            return {"ok": True, "signals": [], "total": 0}
        df = pd.read_csv(path).fillna("").tail(50)
        return {"ok": True, "signals": df.to_dict(orient="records"), "total": len(df)}
    except Exception as e:
        return {"ok": False, "error": str(e), "signals": []}
