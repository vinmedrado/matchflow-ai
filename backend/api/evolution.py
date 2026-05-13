from __future__ import annotations
from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.services.evolution_os.engine import build_evolution_workspace

router = APIRouter(prefix="/api/evolution", tags=["self-evolving-executive-cognitive-ai-system"])

class EvolutionAskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)

@router.get("/workspace")
def workspace() -> dict[str, Any]:
    return build_evolution_workspace()

@router.get("/recursive-improvement")
def recursive_improvement() -> dict[str, Any]:
    ws = build_evolution_workspace()
    return {"ok": True, "generated_at": ws["generated_at"], "recursive_improvement": ws["recursive_improvement"]}

@router.get("/meta-learning")
def meta_learning() -> dict[str, Any]:
    ws = build_evolution_workspace()
    return {"ok": True, "generated_at": ws["generated_at"], "meta_learning": ws["meta_learning"]}

@router.get("/self-preservation")
def self_preservation() -> dict[str, Any]:
    ws = build_evolution_workspace()
    return {"ok": True, "generated_at": ws["generated_at"], "self_preservation": ws["self_preservation"], "cognitive_economy": ws["cognitive_economy"]}

@router.get("/observability")
def observability() -> dict[str, Any]:
    ws = build_evolution_workspace()
    return {"ok": True, "generated_at": ws["generated_at"], "evolution_observability": ws["evolution_observability"], "performance_guards": ws["performance_guards"]}

@router.post("/ask")
def ask(payload: EvolutionAskRequest) -> dict[str, Any]:
    ws = build_evolution_workspace(request_type="ask")
    q = payload.question.lower()
    if "safe" in q or "preserva" in q or "modo" in q:
        p = ws["self_preservation"]
        answer = f"Self-preservation está em {p['mode']['mode']}. Ações críticas permitidas: {p['mode']['critical_actions_allowed']}. Proteções: {', '.join(p['protector']['stability_actions'])}."
    elif "aprend" in q or "meta" in q:
        m = ws["meta_learning"]
        answer = f"Meta-learning usa {m['learning_strategy']} com eficiência {m['learning_efficiency_score']}. Estado: {m['intelligence_evolution']['evolution_state']}."
    elif "arquitet" in q or "modifica" in q:
        a = ws["architectural_evolution"]
        answer = f"Architectural evolution não altera código automaticamente. Proposta atual: {a['workflow_reconfiguration']['proposals'][0]}. Modularity score: {a['modularity']['modularity_score']}."
    elif "agente" in q or "consenso" in q:
        s = ws["executive_agent_society"]
        answer = f"Executive agent society tem consenso {s['consensus']} e score {s['executive_consensus_score']}. Posição final: {s['final_position']}."
    else:
        sm = ws["evolution_summary"]
        answer = f"Evolution OS: {sm['headline']}. Estado={sm['evolution_state']}, modo={sm['self_preservation_mode']}, próxima ação={sm['next_best_action']}."
    return {"ok": True, "mode": "self_evolving_structured_reasoning", "answer": answer, "context": ws}


@router.get("/status")
def status() -> dict[str, Any]:
    ws = build_evolution_workspace()
    return {
        "ok": True,
        "endpoint": "/api/evolution/status",
        "canonical_endpoint": "/api/evolution/workspace",
        "generated_at": ws.get("generated_at"),
        "system_version": ws.get("system_version", "self-evolving-executive-ai-os"),
        "state": (ws.get("evolution_summary") or {}).get("evolution_state"),
        "summary": ws.get("evolution_summary"),
        "observability": ws.get("evolution_observability"),
    }
