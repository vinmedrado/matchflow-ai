"""
telegram_notifier.py — Notificações via Telegram Bot para candidatos HIGH_CONFIDENCE.
Envia alerta formatado com jogo, mercado, odds, EV, Kelly e explicação.
"""
from __future__ import annotations
import json, logging, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("matchflow.automation.telegram_notifier")

def _get_config() -> tuple[str, str, float]:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    min_score = float(os.getenv("TELEGRAM_MIN_SCORE", "70"))
    return token, chat_id, min_score

def _is_configured() -> bool:
    token, chat_id, _ = _get_config()
    return bool(token and chat_id and token != "seu_bot_token_aqui")

def send_message(text: str, parse_mode: str = "HTML") -> bool:
    """Envia mensagem de texto simples para o Telegram."""
    if not _is_configured():
        logger.info("[Telegram] Não configurado — mensagem registrada apenas em log.")
        return False
    try:
        import httpx
    except ImportError:
        logger.error("httpx não instalado. Execute: pip install httpx")
        return False

    token, chat_id, _ = _get_config()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(url, json=payload)
        if resp.status_code == 200:
            logger.info("[Telegram] Mensagem enviada com sucesso.")
            return True
        else:
            logger.warning("[Telegram] Falha HTTP %s: %s", resp.status_code, resp.text[:200])
            return False
    except Exception as exc:
        logger.error("[Telegram] Erro: %s", exc)
        return False

def format_candidate_message(candidate: dict) -> str:
    """Formata candidato HIGH_CONFIDENCE para mensagem Telegram."""
    home = candidate.get("home_team", "?")
    away = candidate.get("away_team", "?")
    league = candidate.get("league", "?")
    date = str(candidate.get("date", "?"))[:10]
    market = str(candidate.get("market", "?")).upper()
    odds = float(candidate.get("odds") or 0)
    ml_prob = float(candidate.get("ensemble_probability") or candidate.get("ml_probability") or 0)
    true_ev = float(candidate.get("true_ev") or 0)
    edge_pct = float(candidate.get("edge_pct") or candidate.get("edge_over_market") or 0)
    kelly_pct = float(candidate.get("kelly_stake_pct") or 0)
    score = float(candidate.get("decision_score") or 0)
    band = str(candidate.get("confidence_band") or "")
    steam = bool(candidate.get("steam_detected", False))
    movement = str(candidate.get("movement_type") or "")

    # Ícones por mercado
    market_icons = {"GOALS": "⚽", "CORNERS": "🚩", "BTTS": "🎯", "SHOTS": "🥅"}
    icon = market_icons.get(market, "📊")

    lines = [
        f"🔔 <b>SINAL MATCHFLOW</b>",
        f"",
        f"{icon} <b>{home} x {away}</b>",
        f"🏆 {league} | 📅 {date}",
        f"",
        f"📈 Mercado: <b>{market}</b> @ <b>{odds:.2f}</b>",
        f"🤖 Prob ML: <b>{ml_prob:.1%}</b>",
        f"💎 True EV: <b>{true_ev:+.2%}</b>  |  Edge: <b>{edge_pct:+.1%}</b>",
        f"💰 Kelly: <b>{kelly_pct:.1%}</b> da banca",
        f"🎲 Score: <b>{score:.0f}/100</b>  |  {band}",
    ]

    if steam:
        lines.append(f"")
        lines.append(f"🔥 <b>STEAM MOVE:</b> dinheiro profissional confirmado")
    elif movement in ("SHARP_MOVEMENT", "LATE_SHARP"):
        lines.append(f"")
        lines.append(f"📉 Movimento sharp nas odds detectado")

    # Explicação se disponível
    explanation = candidate.get("explanation_text") or candidate.get("why_selected")
    if explanation and len(str(explanation)) > 20:
        lines.append(f"")
        lines.append(f"💡 <i>{str(explanation)[:300]}</i>")

    lines.append(f"")
    lines.append(f"⚠️ <i>Confirmação manual obrigatória. Este sistema não aposta automaticamente.</i>")
    lines.append(f"<i>MatchFlow Analytics v7.0 | {datetime.now(timezone.utc).strftime('%H:%M UTC')}</i>")

    return "\n".join(lines)

def format_daily_summary(summary: dict) -> str:
    """Formata resumo diário do pipeline para o Telegram."""
    status = summary.get("status", "UNKNOWN")
    total = summary.get("total_candidates", 0)
    high = summary.get("high_confidence", 0)
    roi = summary.get("total_roi", 0)
    bankroll = summary.get("current_bankroll", 0)
    clv = summary.get("mean_clv_pct", 0)
    pending = summary.get("pending_signals", 0)

    status_icon = "✅" if status == "SUCCESS" else "⚠️"

    return "\n".join([
        f"{status_icon} <b>Relatório Diário MatchFlow</b>",
        f"📅 {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}",
        f"",
        f"📊 Pipeline: <b>{status}</b>",
        f"🎯 Candidatos hoje: <b>{total}</b>  |  High Confidence: <b>{high}</b>",
        f"",
        f"💰 Banca atual: <b>R$ {bankroll:.2f}</b>",
        f"📈 ROI acumulado: <b>{roi:+.2%}</b>",
        f"🎲 CLV médio: <b>{clv:+.1f}%</b>",
        f"⏳ Apostas pendentes: <b>{pending}</b>",
        f"",
        f"<i>MatchFlow Analytics v7.0</i>",
    ])

def notify_high_confidence_candidates(candidates: list[dict], root: Path | None = None) -> dict:
    """
    Envia notificação Telegram para cada candidato HIGH_CONFIDENCE.
    Principal ponto de integração com o decision_engine.
    """
    root = root or Path.cwd()
    _, _, min_score = _get_config()
    sent = 0
    skipped = 0
    errors = 0

    # Log para audit trail mesmo sem Telegram configurado
    log_path = root / "data/automation/telegram_log.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing_log = json.loads(log_path.read_text()) if log_path.exists() else []
    except Exception:
        existing_log = []

    for candidate in candidates:
        score = float(candidate.get("decision_score") or 0)
        band = str(candidate.get("confidence_band") or "")
        kelly = float(candidate.get("kelly_stake_pct") or 0)

        # Filtro: só HIGH_CONFIDENCE com score >= min_score e kelly > 0
        if "HIGH_CONFIDENCE" not in band or score < min_score or kelly <= 0:
            skipped += 1
            continue

        msg = format_candidate_message(candidate)
        success = send_message(msg)

        log_entry = {
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "match": f"{candidate.get('home_team')} x {candidate.get('away_team')}",
            "market": candidate.get("market"),
            "score": score,
            "kelly_pct": kelly,
            "telegram_sent": success,
        }
        existing_log.append(log_entry)

        if success:
            sent += 1
        else:
            errors += 1

    # Manter apenas últimas 500 entradas
    log_path.write_text(
        json.dumps(existing_log[-500:], indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    result = {
        "ok": True,
        "sent": sent,
        "skipped": skipped,
        "errors": errors,
        "configured": _is_configured(),
        "dispatched_at": datetime.now(timezone.utc).isoformat(),
    }
    logger.info("[Telegram] Dispatch: sent=%s skipped=%s errors=%s", sent, skipped, errors)
    return result

def send_pipeline_status(run_summary: dict) -> bool:
    """Envia status do pipeline (sucesso/falha) para o Telegram."""
    if not _is_configured():
        return False
    status = run_summary.get("status", "UNKNOWN")
    if status == "SUCCESS":
        return False  # Não spammar com sucesso — apenas falhas
    msg = "\n".join([
        f"⚠️ <b>MatchFlow — Pipeline com Problema</b>",
        f"Status: <b>{status}</b>",
        f"Horário: {datetime.now(timezone.utc).strftime('%d/%m %H:%M UTC')}",
        f"Verifique os logs do sistema.",
    ])
    return send_message(msg)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
    configured = _is_configured()
    print(f"Telegram configurado: {configured}")
    if configured:
        ok = send_message("🔔 <b>MatchFlow</b> — Teste de conexão OK!")
        print(f"Mensagem enviada: {ok}")
