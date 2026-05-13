from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from backend.services.agents import IntelligenceCoordinator

router = APIRouter(prefix='/api/agents', tags=['multi-agent-intelligence'])

class AgentTaskRequest(BaseModel):
    task: str = Field(default='continuous_operational_review', max_length=500)

@router.get('/cockpit')
def agentic_cockpit() -> dict[str, Any]:
    return IntelligenceCoordinator().run()

@router.post('/coordinate')
def coordinate(payload: AgentTaskRequest) -> dict[str, Any]:
    return IntelligenceCoordinator().run(task=payload.task)

@router.get('/decision')
def agentic_decision() -> dict[str, Any]:
    cycle = IntelligenceCoordinator().run(task='decision_review')
    return {'ok': True, 'generated_at': cycle['generated_at'], 'data_state': cycle['data_state'], 'decision': cycle['decision'], 'consensus': cycle['consensus'], 'conflicts': cycle['conflicts']}

@router.get('/research')
def auto_research() -> dict[str, Any]:
    cycle = IntelligenceCoordinator().run(task='auto_research')
    return {'ok': True, 'generated_at': cycle['generated_at'], 'data_state': cycle['data_state'], 'auto_research': cycle['auto_research']}

@router.get('/optimization')
def self_optimization() -> dict[str, Any]:
    cycle = IntelligenceCoordinator().run(task='self_optimization')
    return {'ok': True, 'generated_at': cycle['generated_at'], 'data_state': cycle['data_state'], 'self_optimization': cycle['self_optimization']}

@router.get('/diagnostics')
def agent_diagnostics() -> dict[str, Any]:
    cycle = IntelligenceCoordinator().run(task='agent_diagnostics')
    return {'ok': True, 'generated_at': cycle['generated_at'], 'observability': cycle['observability'], 'source_meta': cycle['source_meta']}

@router.websocket('/stream')
async def agentic_stream(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            cycle = IntelligenceCoordinator().run(task='realtime_stream_tick')
            await ws.send_text(json.dumps({
                'ok': True,
                'type': 'agentic_cycle',
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'decision': cycle['decision'],
                'events': cycle['event_stream'][-8:],
                'observability': cycle['observability'],
            }, default=str))
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        return
