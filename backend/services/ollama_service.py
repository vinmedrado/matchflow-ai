from __future__ import annotations

import logging
from typing import Any, Dict, List

import requests

from backend.core.config import get_settings
from backend.core.logging_config import get_logger

logger = get_logger("matchflow.ollama_service")


class OllamaService:
    """Local assistant service with strict response contract.

    Contract required by PATCH 1.5.3:
    {
      "ok": true,
      "mode": "ollama|fallback",
      "model": "...",
      "answer": {
        "summary": "",
        "insights": [],
        "technical_notes": []
      }
    }
    """

    def __init__(self) -> None:
        settings = get_settings()
        ollama = settings.get("ollama", {})
        self.enabled = bool(ollama.get("enabled", True))
        self.base_url = str(ollama.get("base_url", "http://localhost:11434")).rstrip("/")
        self.model = str(ollama.get("model", "llama3.1"))

    def ping(self) -> bool:
        if not self.enabled:
            return False
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            ok = response.ok
            logger.info("Ollama ping status=%s base_url=%s", ok, self.base_url)
            return ok
        except requests.RequestException:
            logger.info("Ollama indisponível em %s", self.base_url)
            return False

    def ask(self, question: str, context: Dict[str, Any]) -> Dict[str, Any]:
        if not self.ping():
            logger.warning("Ollama fallback acionado: serviço indisponível")
            return self._fallback(question, context)

        prompt = self._build_prompt(question, context)
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=60,
            )
            response.raise_for_status()
            content = str(response.json().get("response", "")).strip()
            logger.info("Resposta recebida do Ollama: model=%s chars=%s", self.model, len(content))
            return self._response(
                mode="ollama",
                summary=content or "Ollama respondeu sem conteúdo textual.",
                insights=[],
                technical_notes=["Resposta gerada via Ollama local."],
            )
        except Exception as exc:
            logger.exception("Falha ao consultar Ollama: %s", exc)
            return self._fallback(question, context)

    def _build_prompt(self, question: str, context: Dict[str, Any]) -> str:
        limited_context = str(context)[:5000]
        return (
            "Você é o assistente técnico local do MatchFlow Analytics. "
            "Responda de forma objetiva, em português, sem recomendações financeiras, stake ou banca.\n\n"
            "IMPORTANTE: organize a resposta com as seções Summary, Insights e Technical Notes.\n\n"
            f"CONTEXTO LIMITADO DO SISTEMA:\n{limited_context}\n\n"
            f"PERGUNTA:\n{question}\n"
        )

    def _fallback(self, question: str, context: Dict[str, Any]) -> Dict[str, Any]:
        dataset = context.get("dataset", {}) or {}
        quality = context.get("quality", {}) or {}

        insights = [
            f"Dataset disponível: {dataset.get('available', False)}",
            f"Total de registros: {dataset.get('total_records', dataset.get('total_rows', 0))}",
            f"Relatório de qualidade disponível: {quality.get('available', False)}",
        ]

        technical_notes = [
            "Ollama local não está ativo, não respondeu ou não está acessível no endereço configurado.",
            "Fallback técnico executado com base nas métricas locais disponíveis.",
            "Este assistente não faz automação operacional, stake, banca ou recomendação financeira.",
            f"Pergunta recebida: {question}",
        ]

        return self._response(
            mode="fallback",
            summary="IA local via Ollama indisponível. Usei o fallback técnico com os dados básicos disponíveis do sistema.",
            insights=insights,
            technical_notes=technical_notes,
        )

    def _response(self, mode: str, summary: str, insights: List[str], technical_notes: List[str]) -> Dict[str, Any]:
        return {
            "ok": True,
            "mode": mode,
            "model": self.model,
            "answer": {
                "summary": summary,
                "insights": insights,
                "technical_notes": technical_notes,
            },
        }
