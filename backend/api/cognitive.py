from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from backend.services.cognitive import build_cognitive_workspace

router = APIRouter(prefix='/api/cognitive', tags=['cognitive-autonomous-ai'])

class CognitiveAskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)

@router.get('/workspace')
def workspace() -> dict[str, Any]:
    return build_cognitive_workspace()

@router.get('/world-model')
def world_model() -> dict[str, Any]:
    return build_cognitive_workspace()['world_model']

@router.get('/meta-reasoning')
def meta_reasoning() -> dict[str, Any]:
    os = build_cognitive_workspace()
    return {'ok': True, 'meta_reasoning': os['meta_reasoning'], 'self_critique': os['self_critique'], 'cognitive_decision': os['cognitive_decision']}

@router.get('/uncertainty')
def uncertainty() -> dict[str, Any]:
    return build_cognitive_workspace()['uncertainty']

@router.get('/knowledge')
def knowledge() -> dict[str, Any]:
    return build_cognitive_workspace()['knowledge_evolution']

@router.get('/decision')
def decision() -> dict[str, Any]:
    os = build_cognitive_workspace()
    return {'ok': True, 'generated_at': os['generated_at'], 'data_state': os['data_state'], 'cognitive_decision': os['cognitive_decision'], 'observability': os['observability']}

@router.post('/ask')
def ask(payload: CognitiveAskRequest) -> dict[str, Any]:
    os = build_cognitive_workspace()
    q = payload.question.lower()
    if 'incerteza' in q or 'uncert' in q or 'confiança' in q:
        u = os['uncertainty']
        answer = f"Incerteza {u['ambiguity_level']} ({u['uncertainty_score']}). Robustez {u['robustness_score']}. A confiança é ajustada para evitar overconfidence."
    elif 'world' in q or 'regime' in q or 'mundo' in q:
        w = os['world_model']
        answer = f"World model está em regime {w['regime']} com qualidade {w['state_quality']}. Postura: {w['regime_map']['recommended_posture']}."
    elif 'crítica' in q or 'critica' in q or 'reasoning' in q:
        m = os['meta_reasoning']
        answer = f"Meta-reasoning: {m['verdict']} com score {m['reasoning_quality_score']}. Issues: {len(m['issues'])}; contradições: {len(m['contradictions'])}."
    elif 'decisão' in q or 'decisao' in q or 'ação' in q or 'acao' in q:
        d = os['cognitive_decision']
        answer = f"Decisão cognitiva: {d['action']} com confiança ajustada {d['confidence_score']}. Tradeoffs: {', '.join(d['tradeoffs'])}."
    else:
        d = os['cognitive_decision']; w = os['world_model']; u = os['uncertainty']
        answer = f"Cognitive OS: regime {w['regime']}, decisão {d['action']}, incerteza {u['ambiguity_level']} e consenso {d['agent_consensus']}."
    return {'ok': True, 'mode': 'cognitive_structured_reasoning', 'answer': answer, 'context': os}

@router.websocket('/stream')
async def stream(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            os = build_cognitive_workspace()
            await ws.send_text(json.dumps({
                'ok': True,
                'type': 'cognitive_os_tick',
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'world_model': os['world_model'],
                'uncertainty': os['uncertainty'],
                'decision': os['cognitive_decision'],
                'observability': os['observability'],
            }, default=str))
            await asyncio.sleep(8)
    except WebSocketDisconnect:
        return


@router.get("/status")
def status() -> dict[str, Any]:
    os = build_cognitive_workspace()
    return {
        "ok": True,
        "endpoint": "/api/cognitive/status",
        "canonical_endpoint": "/api/cognitive/workspace",
        "generated_at": os.get("generated_at"),
        "system_version": os.get("system_version", "cognitive-autonomous-ai-os"),
        "data_state": os.get("data_state"),
        "decision": os.get("cognitive_decision"),
        "observability": os.get("observability"),
    }
