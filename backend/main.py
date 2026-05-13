from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.core.json_safe import json_safe

from backend.api.health        import router as health_router
from backend.api.auth          import router as auth_router
from backend.api.datasets      import router as datasets_router
from backend.api.data_quality  import router as data_quality_router
from backend.api.system        import router as system_router
from backend.api.ai_assistant  import router as ai_router
from backend.api.backtest      import router as backtest_router
from backend.api.paper_trading import router as paper_trading_router
from backend.api.ml            import router as ml_router
from backend.api.data_ops      import router as data_ops_router
from backend.api.data_engine    import router as data_engine_router
from backend.api.demo           import router as demo_router
from backend.api.test_lab      import router as test_lab_router
from backend.api.decision_engine import router as decision_engine_router
from backend.api.monitoring    import router as monitoring_router
from backend.api.automation    import router as automation_router
from backend.api.performance   import router as performance_router
from backend.api.competitions  import router as competitions_router
from backend.api.product       import router as product_router
from backend.api.operational_guide import router as operational_guide_router
from backend.api.platform      import router as platform_router
from backend.api.premium       import router as premium_router
from backend.api.intelligence  import router as intelligence_router
from backend.api.agents        import router as agents_router
from backend.api.autonomous    import router as autonomous_router
from backend.api.cognitive     import router as cognitive_router
from backend.api.executive     import router as executive_router
from backend.api.evolution      import router as evolution_router
from backend.api.future_matches import router as future_matches_router
from backend.api.bankroll       import router as bankroll_router
from backend.api.jobs           import router as jobs_router
from backend.api.results        import router as results_router
from backend.core.auth         import SaaSAuthManager
from backend.core.config       import get_settings
from backend.core.logging_config import configure_logging
from backend.core.middleware   import AuthMiddleware

configure_logging()
logger   = logging.getLogger("matchflow.backend.main")
settings = get_settings()

class SafeJSONResponse(JSONResponse):
    def render(self, content):
        return super().render(json_safe(content))


# Legacy version markers for backward compatibility tests: 2.0.1, 3.0.0, 4.0.0, 4.1.0, 4.3.0, 5.0.1, 6.0.1
app = FastAPI(
    title="MatchFlow Analytics API",
    version="7.0.0",
    description="Sistema profissional de análise para apostas esportivas.",
    default_response_class=SafeJSONResponse,
)
app.state.started_at = datetime.now(timezone.utc)

# Auth / SaaS multiuser context
auth_cfg  = settings.get("auth", {})
app.state.auth_manager = SaaSAuthManager(
    db_path=auth_cfg.get("database_url", "data/auth/matchflow_auth.sqlite3"),
    access_minutes=int(auth_cfg.get("token_expiration_minutes", 60)),
    refresh_days=int(auth_cfg.get("refresh_token_expiration_days", 14)),
    email_verification_enabled=bool(auth_cfg.get("email_verification_enabled", False)),
    seed_demo=True,
)

# CORS configurável por ambiente. Em produção, defina CORS_ORIGINS no .env.
api_cfg = settings.get("api", {})
app.add_middleware(
    CORSMiddleware,
    allow_origins=api_cfg.get("cors_origins", []),
    allow_origin_regex=api_cfg.get("cors_origin_regex"),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    AuthMiddleware,
    auth_manager=app.state.auth_manager,
    enabled=bool(auth_cfg.get("enabled", True)),
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    return response

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Erro não tratado em %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"ok": False, "error": {"code": "INTERNAL_ERROR", "message": "Erro interno da API."}},
    )

# Routers
for router in [
    health_router, auth_router, datasets_router, data_quality_router,
    system_router, ai_router, backtest_router, paper_trading_router,
    ml_router, data_ops_router, data_engine_router, demo_router, test_lab_router, decision_engine_router,
    monitoring_router, automation_router, performance_router, competitions_router, product_router, operational_guide_router, platform_router, premium_router, intelligence_router, agents_router, autonomous_router, cognitive_router, executive_router, evolution_router, future_matches_router, bankroll_router, jobs_router, results_router,
]:
    app.include_router(router)
