"""
groq_service.py — Assistente AI via Groq API (Llama 3.3 70B, GRÁTIS).
Substitui Ollama local com fallback para análise baseada em regras.
Especializado em análise de apostas esportivas com contexto do sistema.
"""
from __future__ import annotations
import json, logging, os
from typing import Any

logger = logging.getLogger("matchflow.groq_service")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL_DEFAULT = "llama-3.3-70b-versatile"

SPORTS_BETTING_SYSTEM_PROMPT = """Você é o assistente analítico do MatchFlow Analytics, 
um sistema de análise estatística de futebol. Você tem acesso ao contexto atual do sistema 
incluindo candidatos de apostas, métricas de performance e análises de mercado.

REGRAS:
1. Responda sempre em português brasileiro
2. Seja objetivo e técnico — foque em estatísticas e probabilidades
3. NÃO faça recomendações de apostas específicas — apenas análise técnica
4. Estruture a resposta com: Resumo (1-2 frases), Análise (3-5 pontos), Observações técnicas
5. Se perguntado sobre apostas específicas, descreva métricas mas não diga "aposte"
6. Cite números e percentuais quando disponíveis no contexto

Contexto do sistema:
- Sistema analisa mercados: goals over/under, corners, BTTS, shots
- Usa ML ensemble (Random Forest + HistGBM) com walk-forward validation
- Mede CLV (Closing Line Value) como métrica principal de edge
- Calcula True EV com remoção de margem da casa (vig)
- Implementa Kelly fracionado para gestão de banca"""

def _get_api_key() -> str:
    return os.getenv("GROQ_API_KEY", "")

def _get_model() -> str:
    return os.getenv("GROQ_MODEL", GROQ_MODEL_DEFAULT)

def _is_available() -> bool:
    key = _get_api_key()
    return bool(key and key != "seu_token_aqui")

def ask_groq(prompt: str, context_data: dict | None = None,
             system_extra: str = "", max_tokens: int = 1024) -> dict[str, Any]:
    """
    Envia pergunta para Groq API com contexto do sistema.

    Returns:
        dict com ok, mode, model, answer{summary, insights, technical_notes}
    """
    if not _is_available():
        logger.info("Groq API key não configurada — usando fallback")
        return _fallback(prompt, context_data)

    try:
        import httpx
    except ImportError:
        logger.error("httpx não instalado.")
        return _fallback(prompt, context_data)

    # Montar contexto serializado
    context_str = ""
    if context_data:
        try:
            trimmed = _trim_context(context_data)
            context_str = f"\n\nCONTEXTO ATUAL DO SISTEMA:\n{json.dumps(trimmed, indent=2, ensure_ascii=False, default=str)[:4000]}"
        except Exception:
            pass

    system_prompt = SPORTS_BETTING_SYSTEM_PROMPT
    if system_extra:
        system_prompt += f"\n\n{system_extra}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{prompt}{context_str}"},
    ]

    payload = {
        "model": _get_model(),
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "top_p": 0.9,
    }

    try:
        headers = {
            "Authorization": f"Bearer {_get_api_key()}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=30) as client:
            resp = client.post(GROQ_API_URL, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()

        logger.info("Groq respondeu: model=%s tokens=%s chars=%s",
                    _get_model(),
                    data.get("usage", {}).get("total_tokens", "?"),
                    len(content))

        return _parse_response(content, mode="groq")

    except Exception as exc:
        logger.warning("Groq falhou (%s) — usando fallback", exc)
        return _fallback(prompt, context_data)

def _trim_context(ctx: dict) -> dict:
    """Remove campos grandes para não exceder token limit."""
    trimmed = {}
    for k, v in ctx.items():
        if isinstance(v, list) and len(v) > 5:
            trimmed[k] = v[:5]
        elif isinstance(v, str) and len(v) > 500:
            trimmed[k] = v[:500] + "..."
        elif isinstance(v, dict):
            trimmed[k] = {kk: vv for kk, vv in list(v.items())[:10]}
        else:
            trimmed[k] = v
    return trimmed

def _parse_response(content: str, mode: str) -> dict[str, Any]:
    """Tenta extrair sumário/insights estruturados do texto livre."""
    lines = [l.strip() for l in content.split("\n") if l.strip()]
    summary = lines[0] if lines else content[:200]
    insights = [l.lstrip("-•* ") for l in lines[1:] if len(l) > 15][:6]

    return {
        "ok": True,
        "mode": mode,
        "model": _get_model(),
        "answer": {
            "summary": summary,
            "insights": insights,
            "technical_notes": [
                f"Resposta gerada via {mode.upper()} — modelo {_get_model()}",
                "Análise técnica apenas. Não constitui recomendação financeira.",
            ],
            "full_text": content,
        },
    }

def _fallback(prompt: str, context_data: dict | None) -> dict[str, Any]:
    """Fallback analítico baseado em regras quando Groq não disponível."""
    ctx = context_data or {}
    candidates = ctx.get("candidates", [])
    perf = ctx.get("performance", {})
    clv_metrics = ctx.get("clv_metrics", {})

    high_conf = sum(1 for c in candidates if "HIGH" in str(c.get("confidence_band", "")))
    mean_clv = clv_metrics.get("mean_clv_last_30d_pct", 0)
    total_roi = perf.get("total_roi_pct", 0)
    is_beating = clv_metrics.get("is_beating_market", False)

    summary = (
        f"Análise automática: {len(candidates)} candidatos identificados, "
        f"{high_conf} com alta confiança."
    )
    insights = [
        f"CLV médio últimos 30 dias: {mean_clv:.1f}% {'(positivo ✓)' if mean_clv > 0 else '(negativo ✗)'}",
        f"Batendo o mercado: {'SIM' if is_beating else 'NÃO — coletar mais dados'}",
        f"ROI acumulado no paper trading: {total_roi:.1f}%",
        f"Candidatos HIGH_CONFIDENCE hoje: {high_conf}",
    ]

    return {
        "ok": True,
        "mode": "fallback",
        "model": "rule_based",
        "answer": {
            "summary": summary,
            "insights": [i for i in insights if i],
            "technical_notes": [
                "Groq API não configurada ou indisponível.",
                "Configure GROQ_API_KEY no .env para análise com Llama 3.3 70B.",
                f"Pergunta recebida: {prompt[:200]}",
            ],
            "full_text": summary,
        },
    }

class GroqService:
    """Interface orientada a objetos compatível com OllamaService."""

    def ping(self) -> bool:
        return _is_available()

    def ask(self, question: str, context: dict) -> dict:
        return ask_groq(question, context)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
    configured = _is_available()
    logger.info("Groq disponível: %s", configured)
    if configured:
        result = ask_groq("Qual o status atual do sistema de análise?")
        logger.info("Resposta Groq: %s", json.dumps(result.get("answer"), indent=2, ensure_ascii=False))
