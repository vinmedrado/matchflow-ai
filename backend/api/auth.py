from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.core.config import get_settings
from backend.core.logging_config import get_logger

logger = get_logger("matchflow.api.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str
    remember_session: bool = False


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    name: str = Field(min_length=1)
    tenant_name: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None
    logout_all: bool = False


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: str


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None


def error_response(code: str, message: str, status_code: int = 400, extra: dict | None = None) -> JSONResponse:
    content = {"ok": False, "error": {"code": code, "message": message}}
    if extra:
        content.update(extra)
    return JSONResponse(status_code=status_code, content=content)


def unauthorized_response(message: str, status_code: int = 401) -> JSONResponse:
    logger.warning("Unauthorized response: %s", message)
    return error_response("UNAUTHORIZED", message, status_code)


def bearer_token(request: Request) -> str | None:
    header = request.headers.get("Authorization", "")
    return header.replace("Bearer ", "", 1).strip() if header.startswith("Bearer ") else None


@router.get("/status")
def auth_status(request: Request):
    return {"ok": True, "auth": request.app.state.auth_manager.auth_status()}


@router.post("/register")
def register(payload: RegisterRequest, request: Request):
    settings = get_settings().get("auth", {})
    if not bool(settings.get("public_registration_enabled", True)):
        return error_response("REGISTRATION_DISABLED", "Registro público desabilitado.", 403)
    try:
        result = request.app.state.auth_manager.register(
            email=str(payload.email),
            password=payload.password,
            name=payload.name,
            tenant_name=payload.tenant_name,
            role="user",
        )
    except ValueError as exc:
        code = str(exc)
        if code == "EMAIL_ALREADY_REGISTERED":
            return error_response(code, "E-mail já cadastrado.", 409)
        if code == "PASSWORD_TOO_SHORT":
            return error_response(code, "Senha deve ter pelo menos 8 caracteres.", 422)
        return error_response("REGISTRATION_FAILED", "Não foi possível criar a conta.", 400)
    verification_enabled = bool(settings.get("email_verification_enabled", False))
    response = {
        "ok": True,
        "user": result["user"],
        "email_verification_enabled": verification_enabled,
        "verification_pending_optional": not verification_enabled,
        "message": "Conta criada com sucesso.",
    }
    # In dev/demo, exposing this value makes the flow testable without a mail provider. In production enable an email sender.
    if result.get("verification") and not verification_enabled:
        response["dev_verification_token"] = result["verification"]
    return response


@router.post("/login")
def login(payload: LoginRequest, request: Request):
    record = request.app.state.auth_manager.login(
        payload.email,
        payload.password,
        user_agent=request.headers.get("User-Agent"),
        ip=request.client.host if request.client else None,
    )
    if not record:
        logger.warning("Login inválido para email=%s", payload.email)
        return unauthorized_response("Credenciais inválidas ou conta não verificada.")
    refresh_payload = request.app.state.auth_manager.last_refresh_payload()
    logger.info("Login SaaS realizado com sucesso para email=%s tenant=%s", record.email, record.tenant_id)
    return {
        "ok": True,
        "access_token": record.token,
        "refresh_token": refresh_payload.get("refresh_token"),
        "token_type": "bearer",
        "expires_at": record.expires_at.isoformat(),
        "refresh_expires_at": refresh_payload.get("refresh_expires_at"),
        "user": request.app.state.auth_manager.user_payload(record),
    }


@router.post("/refresh")
def refresh(payload: RefreshRequest, request: Request):
    result = request.app.state.auth_manager.refresh(
        payload.refresh_token,
        user_agent=request.headers.get("User-Agent"),
        ip=request.client.host if request.client else None,
    )
    if not result:
        return unauthorized_response("Refresh token inválido ou expirado.")
    return {"ok": True, **result}


@router.post("/logout")
def logout(request: Request, payload: LogoutRequest | None = None):
    user = getattr(request.state, "user", None)
    request.app.state.auth_manager.logout(
        access_token=bearer_token(request),
        refresh_token=None if ((payload.logout_all if payload else False)) else ((payload.refresh_token if payload else None)),
        user_id=user.get("user_id") if ((payload.logout_all if payload else False)) and user else None,
    )
    return {"ok": True, "message": "Sessão encerrada com segurança."}


@router.get("/me")
def me(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        logger.warning("/api/auth/me chamado sem usuário autenticado no request.state")
        return unauthorized_response("Usuário não autenticado.")
    logger.info("Usuário autenticado consultou /api/auth/me: %s", user.get("email"))
    return {"ok": True, "user": user}


@router.get("/profile")
def profile(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        return unauthorized_response("Usuário não autenticado.")
    profile_data = request.app.state.auth_manager.profile(user.get("user_id"))
    return {"ok": True, "profile": profile_data}


@router.patch("/profile")
def update_profile(payload: ProfileUpdateRequest, request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        return unauthorized_response("Usuário não autenticado.")
    profile_data = request.app.state.auth_manager.update_profile(user.get("user_id"), name=payload.name)
    return {"ok": True, "profile": profile_data}


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, request: Request):
    token = request.app.state.auth_manager.create_password_reset_token(str(payload.email))
    response = {
        "ok": True,
        "message": "Se o e-mail existir, um token de redefinição será enviado.",
        "email_delivery_enabled": False,
    }
    if token:
        # Dev/demo safe path until mail provider is configured.
        response["dev_reset_token"] = token
    return response


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, request: Request):
    try:
        ok = request.app.state.auth_manager.reset_password(payload.token, payload.new_password)
    except ValueError:
        return error_response("PASSWORD_TOO_SHORT", "Senha deve ter pelo menos 8 caracteres.", 422)
    if not ok:
        return error_response("INVALID_RESET_TOKEN", "Token de reset inválido ou expirado.", 400)
    return {"ok": True, "message": "Senha atualizada. Faça login novamente."}


@router.post("/verify-email")
def verify_email(payload: VerifyEmailRequest, request: Request):
    ok = request.app.state.auth_manager.verify_email(payload.token)
    if not ok:
        return error_response("INVALID_VERIFICATION_TOKEN", "Token de verificação inválido ou expirado.", 400)
    return {"ok": True, "message": "E-mail verificado."}


@router.post("/resend-verification")
def resend_verification(payload: ResendVerificationRequest, request: Request):
    token = request.app.state.auth_manager.create_verification_token(str(payload.email))
    response = {
        "ok": True,
        "email_verification_enabled": bool(get_settings().get("auth", {}).get("email_verification_enabled", False)),
        "message": "Se o e-mail existir, uma verificação será enviada.",
    }
    if token:
        response["dev_verification_token"] = token
    return response
