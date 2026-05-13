"""
ai_assistant.py — Endpoint do assistente AI.
Usa Groq (Llama 3.3 70B) com fallback para Ollama local.
"""
from __future__ import annotations
import logging
from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.core.logging_config import get_logger
from backend.services.dataset_service import get_dataset_summary
from backend.services.quality_service import get_quality_report

logger = get_logger("matchflow.api.ai_assistant")
router = APIRouter(prefix="/api/ai", tags=["ai-assistant"])


class AskRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=2000)


def _get_ai_service():
    """Retorna Groq se disponível, senão Ollama."""
    try:
        from backend.services.groq_service import GroqService, _is_available
        if _is_available():
            logger.info("Usando Groq API como assistente AI")
            return GroqService()
    except Exception:
        pass
    try:
        from backend.services.ollama_service import OllamaService
        svc = OllamaService()
        if svc.ping():
            logger.info("Usando Ollama local como assistente AI")
            return svc
    except Exception:
        pass
    # Fallback: usar Groq mesmo sem ping (ele tem fallback interno)
    try:
        from backend.services.groq_service import GroqService
        return GroqService()
    except Exception:
        from backend.services.ollama_service import OllamaService
        return OllamaService()


def _build_rich_context() -> dict:
    """Monta contexto rico para o assistente AI."""
    ctx: dict = {
        "dataset": get_dataset_summary(),
        "quality": get_quality_report(),
    }
    # Candidatos do decision engine
    try:
        from pathlib import Path
        import pandas as pd
        root = Path.cwd()
        de_path = root / "data/decision_engine/decision_candidates.csv"
        if de_path.exists():
            df = pd.read_csv(de_path).head(10)
            ctx["candidates"] = df.to_dict(orient="records")
    except Exception:
        pass
    # Performance
    try:
        import json
        from pathlib import Path
        root = Path.cwd()
        perf_path = root / "data/performance/performance_attribution.json"
        if perf_path.exists():
            ctx["performance"] = json.loads(perf_path.read_text())
    except Exception:
        pass
    # CLV metrics
    try:
        from pathlib import Path
        import sys
        root = Path.cwd()
        sys.path.insert(0, str(root / "09_decision_engine"))
        from clv_tracker import get_clv_metrics
        ctx["clv_metrics"] = get_clv_metrics(root)
    except Exception:
        pass
    return ctx


@router.post("/ask")
def ask(payload: AskRequest) -> dict:
    logger.info("Pergunta recebida: chars=%s", len(payload.question))
    context = _build_rich_context()
    service = _get_ai_service()
    result = service.ask(payload.question, context)
    logger.info("Assistant respondeu: mode=%s model=%s", result.get("mode"), result.get("model"))
    return result


@router.get("/status")
def ai_status() -> dict:
    """Retorna qual assistente AI está ativo."""
    groq_ok = False
    ollama_ok = False
    try:
        from backend.services.groq_service import _is_available
        groq_ok = _is_available()
    except Exception:
        pass
    try:
        from backend.services.ollama_service import OllamaService
        ollama_ok = OllamaService().ping()
    except Exception:
        pass
    active = "groq" if groq_ok else ("ollama" if ollama_ok else "fallback_rules")
    return {
        "active_service": active,
        "groq_available": groq_ok,
        "ollama_available": ollama_ok,
        "model": "llama-3.3-70b-versatile" if groq_ok else ("llama3.1" if ollama_ok else "rule_based"),
    }
