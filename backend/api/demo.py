from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/status")
def demo_status() -> dict:
    return {
        "ok": True,
        "data": {
            "enabled": True,
            "mode": "DEMO_SAFE_PAPER_TRADING_ONLY",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "disclaimer": "Dados fictícios marcados como demo. Nenhuma aposta real é executada.",
            "demo_user": {"email": "admin@matchflow.local", "password": "admin123"},
            "recommended_flow": [
                "Dashboard", "Data Operations", "AI Copilot Premium", "Evolution Cockpit", "Executive Cockpit"
            ],
        },
    }
