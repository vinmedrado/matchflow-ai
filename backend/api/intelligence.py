from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from backend.services.ai_brain import OperationalMemoryStore, answer_with_brain, build_ai_brain_snapshot

router = APIRouter(prefix="/api/intelligence", tags=["ai-brain"])


class BrainAskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=2000)


@router.get("/brain")
def ai_brain() -> dict[str, Any]:
    return build_ai_brain_snapshot()


@router.get("/memory")
def operational_memory(limit: int = 50) -> dict[str, Any]:
    store = OperationalMemoryStore()
    return {"ok": True, "profile": store.profile(), "events": store.list_events(limit=limit)}


@router.post("/ask")
def ask_brain(payload: BrainAskRequest) -> dict[str, Any]:
    return answer_with_brain(payload.question)


@router.get("/alerts")
def intelligent_alerts() -> dict[str, Any]:
    snapshot = build_ai_brain_snapshot()
    return {"ok": True, "generated_at": snapshot["generated_at"], "data_state": snapshot["data_state"], "alerts": snapshot["alerts"], "recommendations": snapshot["recommendations"]}


@router.get("/diagnostics")
def diagnostics() -> dict[str, Any]:
    snapshot = build_ai_brain_snapshot()
    meta = snapshot.get("source_meta", {})
    return {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "health": {
            "ai_brain": "ok",
            "decision_candidates": meta.get("decision_candidates", {}).get("state", "unknown"),
            "paper_trading": meta.get("paper_trading", {}).get("paper_summary", meta.get("paper_trading", {})).get("state", "unknown") if isinstance(meta.get("paper_trading"), dict) else "unknown",
            "model_trends": meta.get("model_trends", {}).get("state", "unknown"),
            "memory": snapshot.get("memory", {}).get("state", "unknown"),
        },
        "summary": snapshot.get("summary"),
        "source_meta": meta,
    }


@router.websocket("/ws/intelligence")
async def intelligence_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json({"type": "ai_brain_snapshot", "payload": build_ai_brain_snapshot()})
            await asyncio.sleep(8)
    except WebSocketDisconnect:
        return
