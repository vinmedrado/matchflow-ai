from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from backend.services.executive_os.engine import build_executive_workspace

router = APIRouter(prefix="/api/executive", tags=["executive-cognitive-ai-os"])


class ExecutiveAskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)


@router.get("/workspace")
def workspace() -> dict[str, Any]:
    return build_executive_workspace()


@router.get("/summary")
def summary() -> dict[str, Any]:
    os = build_executive_workspace()
    return {"ok": True, "generated_at": os["generated_at"], "executive_summary": os["executive_summary"], "executive_observability": os["executive_observability"]}


@router.get("/decision-board")
def decision_board() -> dict[str, Any]:
    os = build_executive_workspace()
    return {"ok": True, "generated_at": os["generated_at"], "decision_board": os["decision_board"], "executive_cognition": os["executive_cognition"]}


@router.get("/governance")
def governance() -> dict[str, Any]:
    os = build_executive_workspace()
    return {"ok": True, "generated_at": os["generated_at"], "governance": os["governance"], "digital_twin": os["cognitive_digital_twin"]}


@router.get("/experiments")
def experiments() -> dict[str, Any]:
    os = build_executive_workspace()
    return {"ok": True, "generated_at": os["generated_at"], "experimentation": os["experimentation"]}


@router.get("/reflections")
def reflections() -> dict[str, Any]:
    os = build_executive_workspace()
    return {"ok": True, "generated_at": os["generated_at"], "reflection_cycles": os["reflection_cycles"]}


@router.get("/observability")
def observability() -> dict[str, Any]:
    os = build_executive_workspace()
    return {"ok": True, "generated_at": os["generated_at"], "executive_observability": os["executive_observability"], "cognitive_hierarchy": os["cognitive_hierarchy"]}


@router.post("/ask")
def ask(payload: ExecutiveAskRequest) -> dict[str, Any]:
    os = build_executive_workspace()
    q = payload.question.lower()
    if "govern" in q or "bloque" in q or "safe" in q:
        gov = os["governance"]
        answer = f"Governance: safe_mode={gov['safe_mode']} com {gov['governance_block_count']} bloqueio(s). Motivo principal: {(gov.get('blocks') or gov.get('allowed_actions') or [{'reason':'sem ação crítica'}])[0].get('reason')}"
    elif "exper" in q or "hipótese" in q or "hipotese" in q:
        exp = os["experimentation"]
        answer = f"Experimentation engine tem {exp['summary']['total']} experimento(s), {exp['summary']['inconclusive']} inconclusivo(s). Nenhuma estratégia é promovida sem robustez e aprovação."
    elif "reflex" in q or "falh" in q or "erro" in q:
        refl = os["reflection_cycles"]
        answer = f"Reflection cycles ativos: {refl['summary']['total']}. Eles revisam decisões, drawdowns, degradações e alimentam memória/knowledge evolution."
    elif "fraco" in q or "instável" in q or "instavel" in q or "twin" in q:
        twin = os["cognitive_digital_twin"]
        answer = f"Digital Twin: health={twin['cognitive_health_score']}. Ponto fraco principal: {twin['answers']['onde_estou_fraco']}."
    elif "horizonte" in q or "estratég" in q or "estrateg" in q:
        roadmap = os["long_horizon_strategy"]
        answer = f"Long-horizon strategy está em postura {roadmap['posture']} com horizontes: {', '.join([r['horizon'] for r in roadmap['roadmap']])}."
    else:
        summary = os["executive_summary"]
        answer = f"Executive OS: {summary['headline']} em modo {summary['control_mode']}. Safe mode={summary['safe_mode']}. Próxima ação: {summary['next_best_action']}."
    return {"ok": True, "mode": "executive_structured_reasoning", "answer": answer, "context": os}


@router.websocket("/stream")
async def stream(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            os = build_executive_workspace()
            await ws.send_text(json.dumps({
                "ok": True,
                "type": "executive_os_tick",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "summary": os["executive_summary"],
                "decision_board": os["decision_board"],
                "observability": os["executive_observability"],
            }, default=str))
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        return


@router.get("/status")
def status() -> dict[str, Any]:
    os = build_executive_workspace()
    return {
        "ok": True,
        "endpoint": "/api/executive/status",
        "canonical_endpoint": "/api/executive/workspace",
        "generated_at": os.get("generated_at"),
        "system_version": os.get("system_version", "executive-cognitive-ai-os"),
        "summary": os.get("executive_summary"),
        "observability": os.get("executive_observability"),
    }
