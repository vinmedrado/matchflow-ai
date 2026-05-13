from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from backend.core.storage import safe_read_dataframe, safe_write_dataframe
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/platform", tags=["platform"])


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _safe_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except Exception:
        return default


def _safe_parquet(path: Path) -> pd.DataFrame:
    try:
        return safe_read_dataframe(path) if path.exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def _safe_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path) if path.exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def _file_meta(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    stat = path.stat()
    return {
        "exists": True,
        "path": str(path.relative_to(_root())) if path.is_relative_to(_root()) else str(path),
        "size_mb": round(stat.st_size / 1024 / 1024, 2),
        "updated_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }


def _engine_candidates() -> list[Path]:
    """Deprecated compatibility helper. Main flow uses the internal FlashScore provider only."""
    return [_root() / "backend/services/data_engine/providers/flashscore"]


def _detect_engine() -> dict[str, Any]:
    provider = _root() / "backend/services/data_engine/providers/flashscore"
    return {
        "status": "internal_provider_ready" if provider.exists() else "internal_provider_missing",
        "selected_path": str(provider),
        "candidates": [{"path": str(provider), "exists": provider.exists(), "score": 4 if provider.exists() else 0, "markers_found": ["provider_internal"] if provider.exists() else []}],
        "uses_external_repo": False,
        "saas_target": "Data Engine internalizado em backend/services/data_engine/providers/flashscore e fora de dependências de repositório separado.",
    }


@router.get("/cockpit")
def cockpit() -> dict[str, Any]:
    root = _root()
    base = _safe_parquet(root / "data/processed/base_data_engine.parquet")
    features = _safe_parquet(root / "data/features/team_dataset_advanced.parquet")
    signals = _safe_csv(root / "data/decision_engine/decision_candidates.csv")
    summary = _safe_csv(root / "data/backtest/results/summary_results.csv")
    engine = _detect_engine()

    leagues = int(base["league"].nunique()) if not base.empty and "league" in base.columns else 0
    teams = int(pd.concat([base.get("home_team", pd.Series(dtype=str)), base.get("away_team", pd.Series(dtype=str))]).dropna().nunique()) if not base.empty else 0
    matches = int(len(base)) if not base.empty else 0
    trades = int(summary["total_trades"].sum()) if not summary.empty and "total_trades" in summary.columns else 0
    signals_count = int(len(signals)) if not signals.empty else 0

    readiness = 20
    readiness += 15 if matches > 0 else 0
    readiness += 10 if leagues >= 2 else 0
    readiness += 15 if not features.empty else 0
    readiness += 15 if trades >= 100 else 5 if trades > 0 else 0
    readiness += 10 if signals_count > 0 else 0
    readiness += 10 if engine["status"] != "not_configured" else 0
    readiness = min(readiness, 96)

    return {"ok": True, "data": {
        "readiness_score": readiness,
        "positioning": "ERP analítico esportivo com Data Engine, Backtest, ML, Decision Engine e Banca Inteligente.",
        "mode": "PAPER_TRADING_SIMULATION_ONLY",
        "kpis": {
            "matches": matches,
            "leagues": leagues,
            "teams": teams,
            "backtest_trades": trades,
            "active_signals": signals_count,
        },
        "engine": engine,
        "next_actions": [
            {"label": "Centralizar Data Engine", "area": "Central de Dados", "priority": "alta"},
            {"label": "Rodar backtest por liga/time/mercado", "area": "Backtest Intelligence", "priority": "alta"},
            {"label": "Alimentar ML apenas com mercados validados", "area": "ML Intelligence", "priority": "média"},
            {"label": "Ativar banca inteligente com proteção de drawdown", "area": "Risk Engine", "priority": "alta"},
        ],
    }}


@router.get("/data-center")
def data_center() -> dict[str, Any]:
    root = _root()
    engine = _detect_engine()
    assets = [
        {"name": "Base unificada", "kind": "processed", "meta": _file_meta(root / "data/processed/base_data_engine.parquet")},
        {"name": "Features por time", "kind": "features", "meta": _file_meta(root / "data/features/team_dataset_advanced.parquet")},
        {"name": "Candidatos de decisão", "kind": "signals", "meta": _file_meta(root / "data/decision_engine/decision_candidates.csv")},
        {"name": "Resumo de backtest", "kind": "backtest", "meta": _file_meta(root / "data/backtest/results/summary_results.csv")},
        {"name": "Registro de modelos", "kind": "ml", "meta": _file_meta(root / "data/ml/models/registry.json")},
    ]
    return {"ok": True, "data": {
        "engine": engine,
        "assets": assets,
        "flow": [
            {"step": "Coleta", "owner": "Data Engine", "output": "jogos, odds, estatísticas e feeds"},
            {"step": "Normalização", "owner": "MatchFlow", "output": "base unificada por liga/time/jogo"},
            {"step": "Validação", "owner": "Data Quality", "output": "cobertura, duplicidade e integridade"},
            {"step": "Features", "owner": "Feature Engine", "output": "médias móveis, forma, casa/fora e sinais"},
        ],
        "recommended_architecture": "Converter o internal FlashScore provider em serviço interno executado por worker/job, com logs e histórico no banco.",
    }}


@router.get("/backtest-intelligence")
def backtest_intelligence() -> dict[str, Any]:
    root = _root()
    summary = _safe_csv(root / "data/backtest/results/summary_results.csv")
    detailed = _safe_parquet(root / "data/backtest/results/detailed_results.parquet")
    total_trades = int(summary["total_trades"].sum()) if not summary.empty and "total_trades" in summary.columns else int(len(detailed)) if not detailed.empty else 0
    segments = []
    for col in ["league", "team_key", "market"]:
        if not detailed.empty and col in detailed.columns:
            grouped = detailed.groupby(col).size().sort_values(ascending=False).head(8)
            segments.append({"field": col, "items": [{"name": str(k), "trades": int(v)} for k, v in grouped.items()]})
    if not segments:
        segments = [
            {"field": "league", "items": [{"name": "Aguardando dados", "trades": 0}]},
            {"field": "team_key", "items": [{"name": "Aguardando backtest por time", "trades": 0}]},
            {"field": "market", "items": [{"name": "Aguardando mercado", "trades": 0}]},
        ]
    return {"ok": True, "data": {
        "total_trades": total_trades,
        "validation_level": "forte" if total_trades >= 1000 else "médio" if total_trades >= 100 else "inicial",
        "ml_gate": total_trades >= 100,
        "recommended_method": "Backtest segmentado por liga + time + mercado, depois threshold por equipe com janela recente.",
        "segments": segments,
        "quality_rules": [
            "Não misturar mercados diferentes no mesmo ROI.",
            "Exigir amostra mínima por liga antes de liberar ML.",
            "Separar casa/fora para times com comportamento assimétrico.",
            "Registrar odds usadas, probabilidade estimada e EV no momento da decisão.",
        ],
    }}


@router.get("/ml-intelligence")
def ml_intelligence() -> dict[str, Any]:
    root = _root()
    registry = _safe_json(root / "data/ml/models/registry.json", {})
    calibration = _safe_json(root / "data/ml/calibration_summary.json", {})
    return {"ok": True, "data": {
        "status": "active" if registry else "needs_training",
        "registry": registry,
        "calibration": calibration,
        "model_policy": "ML só deve entrar após backtest validar liga/time/mercado com amostra mínima.",
        "gates": [
            {"name": "Dados suficientes", "passed": bool(registry) or (root / "data/features/team_dataset_advanced.parquet").exists()},
            {"name": "Backtest segmentado", "passed": (root / "data/backtest/results/detailed_results.parquet").exists()},
            {"name": "Calibração monitorada", "passed": bool(calibration)},
            {"name": "Drift monitorado", "passed": (root / "data/monitoring/drift_report.json").exists()},
        ],
        "explainability": ["feature importance", "probabilidade calibrada", "confiança", "drift", "mercado recomendado"],
    }}


@router.get("/risk-engine")
def risk_engine(bankroll: float = Query(1000, gt=0), risk_profile: str = Query("balanced")) -> dict[str, Any]:
    profile = risk_profile if risk_profile in {"conservative", "balanced", "aggressive"} else "balanced"
    if bankroll < 300:
        method = "stake_fixa_protegida"
        pct = 0.005 if profile == "conservative" else 0.008 if profile == "balanced" else 0.01
    elif bankroll < 2000:
        method = "hibrido_flat_kelly"
        pct = 0.008 if profile == "conservative" else 0.012 if profile == "balanced" else 0.018
    else:
        method = "kelly_fracionado_com_drawdown_guard"
        pct = 0.01 if profile == "conservative" else 0.015 if profile == "balanced" else 0.025
    return {"ok": True, "data": {
        "bankroll": bankroll,
        "profile": profile,
        "recommended_method": method,
        "max_stake_pct": pct,
        "max_stake_value": round(bankroll * pct, 2),
        "automatic_rules": [
            "Reduzir stake após drawdown relevante.",
            "Bloquear stake se EV vier sem amostra mínima de backtest.",
            "Diminuir exposição quando houver drift ou queda de calibração.",
            "Permitir Kelly fracionado apenas com probabilidade calibrada.",
        ],
    }}


@router.get("/jobs-center")
def jobs_center() -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    jobs = [
        {"id": "data_engine_sync", "name": "Atualizar Dados", "schedule": "06:50 / 12:50 / 18:50", "status": "scheduled", "last_run": None},
        {"id": "full_pipeline", "name": "Pipeline Completo", "schedule": "07:00 / 13:00 / 19:00", "status": "scheduled", "last_run": None},
        {"id": "settlement", "name": "Liquidação", "schedule": "a cada hora", "status": "scheduled", "last_run": None},
        {"id": "odds_monitor", "name": "Monitor de Odds", "schedule": "a cada 30 min", "status": "scheduled", "last_run": None},
    ]
    return {"ok": True, "data": {"server_time": now, "jobs": jobs, "next_evolution": "Persistir histórico de jobs em banco com fila, progresso, retry e logs por execução."}}


@router.get("/demo-mode")
def demo_mode() -> dict[str, Any]:
    return {"ok": True, "data": {
        "enabled": os.getenv("DEMO_MODE", "true").lower() in {"1", "true", "yes"},
        "purpose": "Permitir apresentação premium mesmo sem APIs pagas, scraping live ou dados pessoais.",
        "demo_user": "admin@matchflow.local",
        "safe_mode": "PAPER_TRADING_SIMULATION_ONLY",
        "data_policy": "Todo dado demonstrativo deve ser fictício, agregado ou claramente marcado como demo.",
        "demo_modules": ["Central de Dados", "AI Copilot", "Live Center", "Executive Cockpit", "Evolution Cockpit", "Data Engine Ops"],
        "presentation_script": [
            "Abrir Dashboard para visão executiva.",
            "Mostrar Data Operations e /api/data-engine/status para provar operação de dados.",
            "Mostrar AI Copilot/Executive/Evolution como camadas de inteligência auditáveis.",
            "Encerrar reforçando modo seguro: nenhuma ação real é executada."
        ],
    }}


@router.get("/mission-control")
def mission_control() -> dict[str, Any]:
    cockpit_data = cockpit()["data"]
    data_data = data_center()["data"]
    backtest_data = backtest_intelligence()["data"]
    ml_data = ml_intelligence()["data"]
    jobs_data = jobs_center()["data"]
    stages = [
        {"id": "data", "name": "Atualizar dados", "status": "ready" if cockpit_data["engine"]["status"] != "not_configured" else "needs_setup", "owner": "Data Engine", "action": "Central de Dados", "why": "Garante jogos, odds e estatísticas recentes antes de qualquer análise."},
        {"id": "quality", "name": "Validar cobertura", "status": "ready" if cockpit_data["kpis"]["matches"] > 0 else "waiting_data", "owner": "Data Quality", "action": "Qualidade de Dados", "why": "Evita backtest usando base incompleta, duplicada ou inconsistente."},
        {"id": "backtest", "name": "Backtest por liga/time/mercado", "status": "ready" if backtest_data["total_trades"] > 0 else "needs_run", "owner": "Backtest Intelligence", "action": "Backtest Intelligence", "why": "Descobre onde há vantagem estatística antes do ML entrar."},
        {"id": "ml", "name": "Treinar/avaliar ML", "status": "ready" if ml_data["status"] == "active" else "gated", "owner": "ML Intelligence", "action": "ML Intelligence", "why": "Modelos só entram onde o backtest provou amostra e estabilidade."},
        {"id": "risk", "name": "Aplicar banca inteligente", "status": "ready", "owner": "Risk Engine", "action": "Risk Engine", "why": "Define stake automaticamente conforme banca, volatilidade, EV e drawdown."},
        {"id": "jobs", "name": "Operar online", "status": "scheduled", "owner": "Jobs Center", "action": "Jobs Center", "why": "Transforma scripts locais em rotina operacional com agenda, logs e histórico."},
    ]
    return {"ok": True, "data": {
        "headline": "Fluxo guiado para operar o MatchFlow como produto SaaS",
        "readiness_score": cockpit_data["readiness_score"],
        "stages": stages,
        "primary_cta": "Começar pela Central de Dados",
        "warning": "Modo seguro: paper trading/simulação. Nenhuma aposta real é executada automaticamente.",
        "job_summary": jobs_data["jobs"],
        "assets": data_data["assets"],
    }}


@router.get("/api-catalog")
def api_catalog() -> dict[str, Any]:
    groups = [
        {"group": "Autenticação", "purpose": "Login, sessão e usuário atual.", "endpoints": ["POST /api/auth/login", "GET /api/auth/me"]},
        {"group": "Central de Dados", "purpose": "Status do Data Engine, execução incremental e bridge.", "endpoints": ["GET /api/platform/data-center", "GET /api/data-ops/status", "POST /api/data-ops/engine-run", "GET /api/data-ops/bridge-status"]},
        {"group": "Competições", "purpose": "Ligas, times, tabela, últimos jogos e cobertura.", "endpoints": ["GET /api/competitions/overview", "GET /api/competitions/detail"]},
        {"group": "Backtest", "purpose": "Auditoria por liga, time, mercado, ROI e amostra.", "endpoints": ["GET /api/platform/backtest-intelligence", "GET /api/backtest/analysis-summary", "GET /api/product/backtest-health"]},
        {"group": "Machine Learning", "purpose": "Calibração, registry, gates e monitoramento de modelo.", "endpoints": ["GET /api/platform/ml-intelligence", "GET /api/ml/calibration-summary", "GET /api/ml/ensemble-summary"]},
        {"group": "Decisão e Banca", "purpose": "EV, candidatos, stake, Kelly fracionado e proteção.", "endpoints": ["GET /api/decision-engine/summary", "GET /api/decision-engine/candidates", "GET /api/platform/risk-engine", "GET /api/paper-trading/summary"]},
        {"group": "Operação", "purpose": "Scheduler, jobs, monitoramento, drift e automação.", "endpoints": ["GET /api/platform/jobs-center", "GET /api/monitoring/status", "GET /api/automation/status", "POST /api/automation/run"]},
    ]
    return {"ok": True, "data": {
        "base_url": "http://127.0.0.1:8000",
        "docs": "/docs",
        "groups": groups,
        "product_rule": "A interface deve explicar intenção de negócio; o Swagger fica para diagnóstico técnico.",
    }}


@router.get("/user-workspace")
def user_workspace() -> dict[str, Any]:
    return {"ok": True, "data": {
        "status": "single_owner_today_multi_tenant_ready",
        "current_mode": "Usuário local de desenvolvimento com sessão JWT.",
        "target_model": [
            {"entity": "organization", "fields": ["id", "name", "plan", "created_at"]},
            {"entity": "user", "fields": ["id", "organization_id", "email", "role", "language"]},
            {"entity": "workspace", "fields": ["preferred_leagues", "markets", "risk_profile", "demo_mode"]},
            {"entity": "bankroll_account", "fields": ["user_id", "initial_balance", "current_balance", "stake_policy"]},
        ],
        "roles": ["owner", "analyst", "viewer"],
        "commercial_value": "Cada cliente teria ligas, banca, preferências, histórico e idioma próprios.",
    }}


@router.get("/sales-readiness")
def sales_readiness() -> dict[str, Any]:
    return {"ok": True, "data": {
        "positioning": "MatchFlow é uma plataforma de inteligência esportiva que transforma dados brutos de futebol em backtests, modelos, decisões simuladas e gestão de risco.",
        "demo_script": [
            "Abrir Cockpit e explicar o fluxo do produto.",
            "Mostrar Central de Dados para provar que o Data Engine virou operação por clique.",
            "Entrar em Competições e mostrar liga/time/tabela.",
            "Mostrar Backtest Intelligence por liga/time/mercado.",
            "Mostrar ML Intelligence com gates e drift.",
            "Finalizar no Risk Engine com política automática de stake.",
        ],
        "missing_for_real_sale": [
            "Persistência em PostgreSQL com multiusuário real.",
            "Jobs persistidos com logs por execução.",
            "Data Engine totalmente empacotado como serviço interno.",
            "Dados demo consistentes para apresentação pública.",
            "Deploy com frontend, backend e worker separados.",
        ],
        "portfolio_score": 91,
        "sale_score": 68,
    }}



@router.get("/onboarding-roadmap")
def onboarding_roadmap() -> dict[str, Any]:
    cockpit_data = cockpit()["data"]
    engine = cockpit_data["engine"]
    matches = cockpit_data["kpis"].get("matches", 0)
    trades = cockpit_data["kpis"].get("backtest_trades", 0)
    signals = cockpit_data["kpis"].get("active_signals", 0)
    steps = [
        {
            "id": "connect_engine",
            "title": "Conectar motor de dados",
            "status": "done" if engine["status"] != "not_configured" else "blocked",
            "business_goal": "Transformar o internal FlashScore provider em uma operação interna do MatchFlow.",
            "user_action": "Abrir Central de Dados e validar se o engine foi detectado.",
            "system_action": "Localiza engine, arquivos gerados, base unificada e bridge.",
            "success_metric": "Engine detectado e pelo menos uma base de jogos disponível.",
        },
        {
            "id": "sync_matches",
            "title": "Atualizar jogos e odds",
            "status": "done" if matches > 0 else "ready",
            "business_goal": "Garantir que o usuário não precise rodar scripts manualmente.",
            "user_action": "Clicar em Atualizar Dados ou usar job agendado.",
            "system_action": "Executa coleta, normalização, validação e grava metadados.",
            "success_metric": "Jogos, ligas e times visíveis no produto.",
        },
        {
            "id": "validate_segments",
            "title": "Validar liga, time e mercado",
            "status": "done" if trades >= 100 else "needs_data",
            "business_goal": "Evitar decisões com ROI bonito, mas sem amostra confiável.",
            "user_action": "Escolher campeonato e mercado para auditar.",
            "system_action": "Calcula amostra, ROI, winrate, drawdown e consistência por segmento.",
            "success_metric": "Segmentos aprovados para alimentar ML.",
        },
        {
            "id": "train_models",
            "title": "Treinar ML com gates",
            "status": "ready" if trades >= 100 else "gated",
            "business_goal": "Usar ML apenas onde o backtest provou estabilidade.",
            "user_action": "Rodar treino/avaliação no ML Intelligence.",
            "system_action": "Treina, calibra, registra modelo e monitora drift.",
            "success_metric": "Modelo ativo com calibração e explicabilidade.",
        },
        {
            "id": "operate_bankroll",
            "title": "Operar banca inteligente",
            "status": "ready" if signals > 0 else "waiting_signals",
            "business_goal": "Automatizar stake sem assumir aposta real automática.",
            "user_action": "Definir banca, perfil de risco e mercados permitidos.",
            "system_action": "Escolhe stake fixa, híbrida ou Kelly fracionado conforme risco.",
            "success_metric": "Sinais com stake recomendada e justificativa.",
        },
        {
            "id": "package_saas",
            "title": "Empacotar como SaaS vendável",
            "status": "in_progress",
            "business_goal": "Cliente acessa online, sem pasta, terminal ou conhecimento técnico.",
            "user_action": "Preparar demo, usuários, planos e deploy separado.",
            "system_action": "Frontend, backend, worker, banco e logs em serviços próprios.",
            "success_metric": "Demo pública com dados consistentes e fluxo por clique.",
        },
    ]
    return {"ok": True, "data": {
        "title": "Onboarding operacional do MatchFlow",
        "subtitle": "Do primeiro dado até a banca inteligente, sem depender de terminal.",
        "readiness_score": cockpit_data["readiness_score"],
        "steps": steps,
        "principle": "O usuário final entende decisões e resultados; a engenharia fica invisível por trás dos jobs.",
    }}


@router.get("/decision-room")
def decision_room() -> dict[str, Any]:
    root = _root()
    signals = _safe_csv(root / "data/decision_engine/decision_candidates.csv")
    paper = _safe_json(root / "data/paper_trading/paper_summary.json", {})
    top = []
    if not signals.empty:
        for _, row in signals.head(8).iterrows():
            item = {str(k): (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
            top.append(item)
    return {"ok": True, "data": {
        "title": "Sala de Decisão",
        "mode": "paper_trading_only",
        "summary": {
            "signals_available": int(len(signals)) if not signals.empty else 0,
            "paper_trading": bool(paper),
            "risk_status": "safe_simulation",
        },
        "decision_checklist": [
            {"label": "Dados recentes", "passed": (root / "data/processed/base_data_engine.parquet").exists()},
            {"label": "Backtest segmentado", "passed": (root / "data/backtest/results/detailed_results.parquet").exists()},
            {"label": "Modelo/calibração", "passed": (root / "data/ml/models/registry.json").exists()},
            {"label": "Sinais gerados", "passed": not signals.empty},
            {"label": "Modo seguro", "passed": True},
        ],
        "top_candidates": top,
        "operator_note": "A tela deve responder: por que esse jogo, por que esse mercado, qual amostra, qual EV e qual stake segura.",
    }}


@router.get("/strategy-studio")
def strategy_studio(bankroll: float = Query(1000, gt=0), risk_profile: str = Query("balanced")) -> dict[str, Any]:
    risk = risk_engine(bankroll=bankroll, risk_profile=risk_profile)["data"]
    presets = [
        {"id": "capital_protection", "name": "Proteção de Capital", "best_for": "banca pequena ou fase de validação", "stake_method": "stake fixa baixa", "max_daily_exposure": "2%", "ml_required": False},
        {"id": "validated_edges", "name": "Edges Validados", "best_for": "ligas/mercados com backtest consistente", "stake_method": "híbrido", "max_daily_exposure": "4%", "ml_required": False},
        {"id": "calibrated_ml", "name": "ML Calibrado", "best_for": "segmentos com amostra, calibração e baixo drift", "stake_method": "Kelly fracionado", "max_daily_exposure": "6%", "ml_required": True},
    ]
    guardrails = [
        "Bloquear decisão sem amostra mínima por liga/time/mercado.",
        "Reduzir exposição quando drawdown ou drift subir.",
        "Separar performance de gols, BTTS e escanteios.",
        "Nunca misturar ROI de treino com ROI de operação futura.",
        "Manter confirmação manual para qualquer ação financeira real.",
    ]
    return {"ok": True, "data": {
        "bankroll": bankroll,
        "risk_profile": risk_profile,
        "recommended_policy": risk,
        "presets": presets,
        "guardrails": guardrails,
        "next_product_step": "Salvar presets por usuário/workspace e aplicar automaticamente no Decision Engine.",
    }}


@router.get("/saas-maturity")
def saas_maturity() -> dict[str, Any]:
    cockpit_data = cockpit()["data"]
    engine_status = cockpit_data["engine"]["status"]
    dimensions = [
        {"area": "Produto", "score": 82, "status": "forte", "done": ["cockpit", "navegação premium", "fluxo guiado"], "missing": ["dados demo perfeitos", "onboarding final"]},
        {"area": "Dados", "score": 70 if engine_status != "not_configured" else 48, "status": "em evolução", "done": ["engine detectável", "central de dados", "arquivos auditáveis"], "missing": ["engine embutido como worker", "PostgreSQL como fonte principal"]},
        {"area": "Backtest/ML", "score": 76, "status": "bom", "done": ["pipeline separado", "gates", "intelligence pages"], "missing": ["backtest por time/liga visual", "model registry persistido em banco"]},
        {"area": "SaaS", "score": 52, "status": "base criada", "done": ["auth local", "workspace blueprint", "rotas"], "missing": ["multi tenant real", "billing", "deploy", "fila persistente"]},
        {"area": "Venda/Demo", "score": 74, "status": "quase apresentável", "done": ["sales readiness", "demo mode", "readiness"], "missing": ["landing/demo pública", "screenshots", "storytelling final"]},
    ]
    score = round(sum(d["score"] for d in dimensions) / len(dimensions))
    return {"ok": True, "data": {
        "overall_score": score,
        "verdict": "Portfólio premium agora; SaaS vendável após banco, jobs persistentes, engine embutido e demo pública.",
        "dimensions": dimensions,
        "ceiling_next": "A próxima barreira não é tela: é persistência, automação online e dados demo confiáveis.",
    }}
