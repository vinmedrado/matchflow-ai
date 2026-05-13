from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from fastapi import Depends, HTTPException, Request

from backend.core.saas_auth import user_can, normalize_role

READONLY_PREFIXES = ("view_",)

def current_user(request: Request) -> dict[str, Any]:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Autenticação obrigatória."})
    if user.get("is_active") is False:
        raise HTTPException(status_code=403, detail={"code": "INACTIVE_USER", "message": "Usuário inativo."})
    return user

def require_permission(permission: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def _guard(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
        if user_can(user, permission):
            return user
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": f"Permissão exigida: {permission}."})
    return _guard

def require_any_permission(*permissions: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def _guard(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
        if any(user_can(user, permission) for permission in permissions):
            return user
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Permissão insuficiente."})
    return _guard

def require_job_run_permission(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    role = normalize_role(user.get("role"))
    if role == "viewer":
        raise HTTPException(status_code=403, detail={"code": "VIEWER_READ_ONLY", "message": "Viewer é somente leitura."})
    if user_can(user, "run_jobs"):
        return user
    raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Permissão run_jobs exigida."})

def tenant_scope(user: dict[str, Any]) -> dict[str, str | bool]:
    role = normalize_role(user.get("role"))
    return {
        "tenant_id": str(user.get("tenant_id") or "tenant_demo"),
        "user_id": str(user.get("user_id") or user.get("id") or "unknown_user"),
        "is_admin": role == "admin",
        "is_demo": bool(user.get("is_demo") or role == "demo"),
        "role": role,
    }

def ensure_tenant_access(resource_tenant_id: str | None, user: dict[str, Any]) -> None:
    scope = tenant_scope(user)
    if scope["is_admin"]:
        return
    if not resource_tenant_id or resource_tenant_id != scope["tenant_id"]:
        raise HTTPException(status_code=403, detail={"code": "TENANT_FORBIDDEN", "message": "Recurso pertence a outro tenant."})

def tenant_data_path(project_root: Path, user: dict[str, Any], area: str, *parts: str) -> Path:
    scope = tenant_scope(user)
    safe_area = area.strip("/\\").replace("..", "_") or "misc"
    p = project_root / "data" / "tenants" / str(scope["tenant_id"]) / safe_area
    for part in parts:
        p = p / str(part).strip("/\\").replace("..", "_")
    p.mkdir(parents=True, exist_ok=True) if not p.suffix else p.parent.mkdir(parents=True, exist_ok=True)
    return p
