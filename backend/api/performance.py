"""performance.py — Endpoints de performance, Monte Carlo e CLV."""
from __future__ import annotations
import json
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from backend.core.logging_config import get_logger

logger = get_logger("matchflow.api.performance")
router = APIRouter(prefix="/api/performance", tags=["performance"])

def _root() -> Path:
    return Path(__file__).resolve().parents[2]

class MonteCarloInput(BaseModel):
    edge_per_bet: float = 0.03
    bets_per_week: float = 5.0
    kelly_fraction: float = 0.25
    initial_bankroll: float = 1000.0
    simulations: int = 5000
    weeks: int = 26

@router.post("/monte-carlo")
def monte_carlo(params: MonteCarloInput):
    import sys
    root = _root()
    sys.path.insert(0, str(root / "04_backtest/analysis"))
    try:
        from monte_carlo import monte_carlo_bankroll
        result = monte_carlo_bankroll(
            edge_per_bet=params.edge_per_bet,
            bets_per_week=params.bets_per_week,
            kelly_fraction=params.kelly_fraction,
            initial_bankroll=params.initial_bankroll,
            simulations=params.simulations,
            weeks=params.weeks,
        )
        # Remover sample_curves da resposta (muito grande)
        result.pop("sample_curves", None)
        return {"ok": True, "data": result}
    except Exception as e:
        logger.error("Monte Carlo falhou: %s", e)
        return {"ok": False, "error": str(e)}

@router.get("/attribution")
def attribution():
    try:
        path = _root() / "data/performance/performance_attribution.json"
        if path.exists():
            return {"ok": True, "data": json.loads(path.read_text())}
        # Gerar on-demand
        import sys
        sys.path.insert(0, str(_root() / "09_decision_engine"))
        from performance_attributor import generate_performance_report
        result = generate_performance_report(_root())
        return {"ok": True, "data": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.get("/clv")
def clv_metrics(days: int = 30):
    try:
        import sys
        sys.path.insert(0, str(_root() / "09_decision_engine"))
        from clv_tracker import get_clv_metrics
        return {"ok": True, "data": get_clv_metrics(_root(), days=days)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@router.post("/settle")
def settle_bets():
    try:
        import sys
        sys.path.insert(0, str(_root() / "07_data_ops"))
        from result_settler import settle_pending_bets
        result = settle_pending_bets(_root())
        return {"ok": True, "data": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}
