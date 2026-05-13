from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.core.config import resolve_project_path
from backend.core.logging_config import get_logger

logger = get_logger("matchflow.saas_auth")

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin": [
        "view_all", "admin_only", "view_dashboard", "view_reports", "view_monitoring",
        "run_jobs", "manage_jobs", "view_data_engine", "run_data_engine",
        "view_system_status", "manage_system", "view_ml", "view_decision_engine",
        "manage_tenant", "manage_tenants", "manage_settings", "view_admin",
        "run_test_lab", "run_data_ops", "run_simulation", "view_analytics",
    ],
    "user": [
        "view_dashboard", "view_reports", "view_monitoring", "view_ml",
        "view_decision_engine", "run_jobs", "view_data_engine", "run_simulation",
        "view_analytics",
    ],
    "analyst": [
        "view_dashboard", "view_reports", "view_monitoring", "view_ml",
        "view_decision_engine", "run_jobs", "view_data_engine", "run_test_lab",
        "run_simulation", "view_analytics",
    ],
    "viewer": [
        "view_dashboard", "view_reports", "view_monitoring", "view_ml",
        "view_decision_engine", "view_data_engine", "view_only",
    ],
    "demo": [
        "view_dashboard", "view_reports", "view_monitoring", "view_ml",
        "view_decision_engine", "view_data_engine", "run_jobs", "run_simulation",
        "view_analytics", "view_only",
    ],
}

@dataclass
class TokenRecord:
    token: str
    email: str
    name: str
    role: str
    permissions: list[str]
    expires_at: datetime
    user_id: str = ""
    tenant_id: str = ""
    token_id: str = ""
    token_type: str = "access"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def normalize_role(role: str | None) -> str:
    value = (role or "user").strip().lower()
    if value == "admin":
        return "admin"
    if value in {"analyst", "user", "viewer", "demo"}:
        return value
    return "user"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(12).replace('-', '_')}"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


class SaaSAuthManager:
    """Small production-oriented auth manager backed by SQLite/PostgreSQL-compatible schema concepts.

    This keeps the current project lightweight while replacing local/dev-only auth with persistent users,
    tenants, refresh rotation, revocation, reset/verification tokens, and role/tenant context.
    """

    def __init__(
        self,
        db_path: str | Path = "data/auth/matchflow_auth.sqlite3",
        access_minutes: int = 60,
        refresh_days: int = 14,
        email_verification_enabled: bool = False,
        seed_demo: bool = True,
    ) -> None:
        self.db_path = resolve_project_path(str(db_path)) if not isinstance(db_path, Path) else db_path
        self.access_minutes = int(access_minutes)
        self.refresh_days = int(refresh_days)
        self.email_verification_enabled = bool(email_verification_enabled)
        env = os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development")).strip().lower()
        enable_demo = os.getenv("ENABLE_DEMO_ACCOUNTS", "true").strip().lower() in {"1", "true", "yes", "on"}
        allowed_envs = {item.strip().lower() for item in os.getenv("DEMO_ACCOUNTS_ALLOWED_ENV", "development,demo,local").split(",") if item.strip()}
        disable_prod = os.getenv("DISABLE_DEMO_ACCOUNTS_IN_PRODUCTION", "true").strip().lower() in {"1", "true", "yes", "on"}
        if env == "production" and enable_demo and disable_prod:
            logger.warning("Demo accounts disabled in production by DISABLE_DEMO_ACCOUNTS_IN_PRODUCTION=true")
            enable_demo = False
        self.seed_demo = bool(seed_demo) and enable_demo and env in allowed_envs
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        if self.seed_demo:
            self.seed_defaults()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS tenants (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    slug TEXT NOT NULL UNIQUE,
                    plan TEXT NOT NULL DEFAULT 'demo',
                    is_demo INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    email TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    is_demo INTEGER NOT NULL DEFAULT 0,
                    email_verified INTEGER NOT NULL DEFAULT 0,
                    verification_pending_optional INTEGER NOT NULL DEFAULT 1,
                    created_by TEXT,
                    updated_by TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    deleted_at TEXT
                );
                CREATE TABLE IF NOT EXISTS refresh_tokens (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    token_hash TEXT NOT NULL UNIQUE,
                    expires_at TEXT NOT NULL,
                    revoked_at TEXT,
                    replaced_by TEXT,
                    created_at TEXT NOT NULL,
                    user_agent TEXT,
                    ip_address TEXT
                );
                CREATE TABLE IF NOT EXISTS access_tokens (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                    token_hash TEXT NOT NULL UNIQUE,
                    expires_at TEXT NOT NULL,
                    revoked_at TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS email_verification_tokens (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    token_hash TEXT NOT NULL UNIQUE,
                    expires_at TEXT NOT NULL,
                    used_at TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    token_hash TEXT NOT NULL UNIQUE,
                    expires_at TEXT NOT NULL,
                    used_at TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS auth_rate_limits (
                    key TEXT PRIMARY KEY,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    reset_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tenant_audit_events (
                    id TEXT PRIMARY KEY,
                    tenant_id TEXT,
                    user_id TEXT,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
                CREATE INDEX IF NOT EXISTS idx_access_tokens_user ON access_tokens(user_id, tenant_id);
                CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id, tenant_id);
                CREATE INDEX IF NOT EXISTS idx_audit_tenant ON tenant_audit_events(tenant_id, created_at);
                """
            )

    @staticmethod
    def hash_password(password: str, salt: str | None = None) -> str:
        salt = salt or secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 260_000)
        return f"pbkdf2_sha256$260000${salt}${base64.b64encode(digest).decode('ascii')}"

    @staticmethod
    def verify_password(password: str, stored: str) -> bool:
        try:
            algo, iterations, salt, digest = stored.split("$", 3)
            if algo != "pbkdf2_sha256":
                return False
            computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations))
            return hmac.compare_digest(base64.b64encode(computed).decode("ascii"), digest)
        except Exception:
            return False

    def seed_defaults(self) -> None:
        now = iso(utcnow())
        with self.connect() as conn:
            row = conn.execute("SELECT id FROM tenants WHERE slug=?", ("demo",)).fetchone()
            tenant_id = row["id"] if row else "tenant_demo"
            if not row:
                conn.execute(
                    "INSERT INTO tenants(id,name,slug,plan,is_demo,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                    (tenant_id, "MatchFlow Demo Tenant", "demo", "demo", 1, now, now),
                )
            defaults = [
                ("user_admin", "admin@matchflow.local", "admin123", "Admin MatchFlow", "admin", 0),
                ("user_analyst", "analyst@matchflow.local", "analyst123", "Analyst MatchFlow", "analyst", 0),
                ("user_viewer", "viewer@matchflow.local", "viewer123", "Viewer MatchFlow", "viewer", 0),
                ("user_demo", "demo@matchflow.local", "demo123", "Demo User", "demo", 1),
            ]
            for user_id, email, password, name, role, is_demo in defaults:
                existing = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
                if existing:
                    continue
                conn.execute(
                    """INSERT INTO users(id,tenant_id,email,name,password_hash,role,is_active,is_demo,email_verified,
                       verification_pending_optional,created_by,updated_by,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        user_id, tenant_id, email, name, self.hash_password(password), role, 1, is_demo,
                        1, 0 if not self.email_verification_enabled else 1, "system", "system", now, now,
                    ),
                )

    def _user_payload_from_row(self, user: sqlite3.Row, tenant: sqlite3.Row | None = None) -> dict[str, Any]:
        role = normalize_role(user["role"])
        permissions = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["user"])
        payload = {
            "id": user["id"],
            "user_id": user["id"],
            "tenant_id": user["tenant_id"],
            "email": user["email"],
            "name": user["name"],
            "role": role,
            "role_key": role.upper(),
            "permissions": permissions,
            "mode": "saas",
            "is_demo": bool(user["is_demo"]),
            "email_verified": bool(user["email_verified"]),
            "verification_pending_optional": bool(user["verification_pending_optional"]),
        }
        if tenant:
            payload["tenant"] = {"id": tenant["id"], "name": tenant["name"], "slug": tenant["slug"], "is_demo": bool(tenant["is_demo"])}
        return payload

    def _get_user_by_email(self, conn: sqlite3.Connection, email: str) -> sqlite3.Row | None:
        return conn.execute("SELECT * FROM users WHERE lower(email)=lower(?) AND deleted_at IS NULL", (email.strip(),)).fetchone()

    def _get_user_by_id(self, conn: sqlite3.Connection, user_id: str) -> sqlite3.Row | None:
        return conn.execute("SELECT * FROM users WHERE id=? AND deleted_at IS NULL", (user_id,)).fetchone()

    def _tenant(self, conn: sqlite3.Connection, tenant_id: str) -> sqlite3.Row | None:
        return conn.execute("SELECT * FROM tenants WHERE id=?", (tenant_id,)).fetchone()

    def _issue_access(self, conn: sqlite3.Connection, user: sqlite3.Row) -> tuple[str, datetime, str]:
        token = "mf_at_" + secrets.token_urlsafe(36)
        token_id = new_id("at")
        exp = utcnow() + timedelta(minutes=self.access_minutes)
        conn.execute(
            "INSERT INTO access_tokens(id,user_id,tenant_id,token_hash,expires_at,created_at) VALUES(?,?,?,?,?,?)",
            (token_id, user["id"], user["tenant_id"], hash_token(token), iso(exp), iso(utcnow())),
        )
        return token, exp, token_id

    def _issue_refresh(self, conn: sqlite3.Connection, user: sqlite3.Row, user_agent: str | None = None, ip: str | None = None) -> tuple[str, datetime, str]:
        token = "mf_rt_" + secrets.token_urlsafe(48)
        token_id = new_id("rt")
        exp = utcnow() + timedelta(days=self.refresh_days)
        conn.execute(
            "INSERT INTO refresh_tokens(id,user_id,tenant_id,token_hash,expires_at,created_at,user_agent,ip_address) VALUES(?,?,?,?,?,?,?,?)",
            (token_id, user["id"], user["tenant_id"], hash_token(token), iso(exp), iso(utcnow()), user_agent, ip),
        )
        return token, exp, token_id

    def login(self, email: str, password: str, user_agent: str | None = None, ip: str | None = None) -> Optional[TokenRecord]:
        with self.connect() as conn:
            user = self._get_user_by_email(conn, email)
            if not user or not user["is_active"] or not self.verify_password(password, user["password_hash"]):
                return None
            if self.email_verification_enabled and not user["email_verified"]:
                return None
            access, exp, token_id = self._issue_access(conn, user)
            # keep a refresh token available through last_login_result to avoid changing TokenRecord contract
            refresh, refresh_exp, refresh_id = self._issue_refresh(conn, user, user_agent=user_agent, ip=ip)
            self._last_refresh = {"refresh_token": refresh, "refresh_expires_at": iso(refresh_exp), "refresh_token_id": refresh_id}
            role = normalize_role(user["role"])
            return TokenRecord(access, user["email"], user["name"], role, ROLE_PERMISSIONS.get(role, []), exp, user["id"], user["tenant_id"], token_id)

    def last_refresh_payload(self) -> dict[str, Any]:
        return getattr(self, "_last_refresh", {})

    def validate_token(self, token: str) -> Optional[TokenRecord]:
        if not token:
            return None
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM access_tokens WHERE token_hash=? AND revoked_at IS NULL",
                (hash_token(token),),
            ).fetchone()
            if not row:
                return None
            exp = parse_dt(row["expires_at"])
            if exp <= utcnow():
                conn.execute("UPDATE access_tokens SET revoked_at=? WHERE id=?", (iso(utcnow()), row["id"]))
                return None
            user = self._get_user_by_id(conn, row["user_id"])
            if not user or not user["is_active"]:
                return None
            role = normalize_role(user["role"])
            return TokenRecord(token, user["email"], user["name"], role, ROLE_PERMISSIONS.get(role, []), exp, user["id"], user["tenant_id"], row["id"])

    def user_payload(self, record: TokenRecord) -> dict[str, Any]:
        with self.connect() as conn:
            user = self._get_user_by_id(conn, record.user_id)
            if not user:
                return {"email": record.email, "name": record.name, "role": record.role, "permissions": record.permissions, "mode": "saas"}
            return self._user_payload_from_row(user, self._tenant(conn, user["tenant_id"]))

    def create_expired_token_for_tests(self) -> str:
        with self.connect() as conn:
            user = self._get_user_by_email(conn, "admin@matchflow.local")
            if not user:
                raise RuntimeError("default admin user missing")
            token = "mf_expired_" + secrets.token_urlsafe(12)
            token_id = new_id("at")
            conn.execute(
                "INSERT INTO access_tokens(id,user_id,tenant_id,token_hash,expires_at,created_at) VALUES(?,?,?,?,?,?)",
                (token_id, user["id"], user["tenant_id"], hash_token(token), iso(utcnow() - timedelta(minutes=1)), iso(utcnow())),
            )
            return token

    def register(self, email: str, password: str, name: str, tenant_name: str | None = None, role: str = "user") -> dict[str, Any]:
        now = iso(utcnow())
        email = email.strip().lower()
        if len(password) < 8:
            raise ValueError("PASSWORD_TOO_SHORT")
        with self.connect() as conn:
            if self._get_user_by_email(conn, email):
                raise ValueError("EMAIL_ALREADY_REGISTERED")
            tenant_id = new_id("tenant")
            slug = email.split("@", 1)[0].replace(".", "-") + "-" + secrets.token_hex(3)
            conn.execute(
                "INSERT INTO tenants(id,name,slug,plan,is_demo,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                (tenant_id, tenant_name or f"Tenant {name}", slug, "starter", 0, now, now),
            )
            user_id = new_id("user")
            email_verified = 0 if self.email_verification_enabled else 1
            pending_optional = 0 if self.email_verification_enabled else 1
            conn.execute(
                """INSERT INTO users(id,tenant_id,email,name,password_hash,role,is_active,is_demo,email_verified,
                   verification_pending_optional,created_by,updated_by,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (user_id, tenant_id, email, name.strip() or email, self.hash_password(password), normalize_role(role), 1, 0, email_verified, pending_optional, "self", "self", now, now),
            )
            user = self._get_user_by_id(conn, user_id)
            verification = self.create_verification_token(email, conn=conn) if user and self.email_verification_enabled else None
            return {"user": self._user_payload_from_row(user, self._tenant(conn, tenant_id)), "verification": verification}

    def refresh(self, refresh_token: str, user_agent: str | None = None, ip: str | None = None) -> Optional[dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM refresh_tokens WHERE token_hash=? AND revoked_at IS NULL", (hash_token(refresh_token),)).fetchone()
            if not row or parse_dt(row["expires_at"]) <= utcnow():
                return None
            user = self._get_user_by_id(conn, row["user_id"])
            if not user or not user["is_active"]:
                return None
            access, exp, _ = self._issue_access(conn, user)
            new_refresh, refresh_exp, refresh_id = self._issue_refresh(conn, user, user_agent=user_agent, ip=ip)
            conn.execute("UPDATE refresh_tokens SET revoked_at=?, replaced_by=? WHERE id=?", (iso(utcnow()), refresh_id, row["id"]))
            return {
                "access_token": access,
                "refresh_token": new_refresh,
                "token_type": "bearer",
                "expires_at": iso(exp),
                "refresh_expires_at": iso(refresh_exp),
                "user": self._user_payload_from_row(user, self._tenant(conn, user["tenant_id"])),
            }

    def logout(self, access_token: str | None = None, refresh_token: str | None = None, user_id: str | None = None) -> None:
        now = iso(utcnow())
        with self.connect() as conn:
            if access_token:
                conn.execute("UPDATE access_tokens SET revoked_at=? WHERE token_hash=? AND revoked_at IS NULL", (now, hash_token(access_token)))
            if refresh_token:
                conn.execute("UPDATE refresh_tokens SET revoked_at=? WHERE token_hash=? AND revoked_at IS NULL", (now, hash_token(refresh_token)))
            elif user_id:
                conn.execute("UPDATE refresh_tokens SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL", (now, user_id))

    def create_verification_token(self, email: str, conn: sqlite3.Connection | None = None) -> Optional[str]:
        own = conn is None
        conn = conn or self.connect()
        try:
            user = self._get_user_by_email(conn, email)
            if not user:
                return None
            token = "mf_vt_" + secrets.token_urlsafe(32)
            conn.execute(
                "INSERT INTO email_verification_tokens(id,user_id,token_hash,expires_at,created_at) VALUES(?,?,?,?,?)",
                (new_id("vt"), user["id"], hash_token(token), iso(utcnow() + timedelta(hours=24)), iso(utcnow())),
            )
            return token
        finally:
            if own:
                conn.close()

    def verify_email(self, token: str) -> bool:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM email_verification_tokens WHERE token_hash=? AND used_at IS NULL", (hash_token(token),)).fetchone()
            if not row or parse_dt(row["expires_at"]) <= utcnow():
                return False
            now = iso(utcnow())
            conn.execute("UPDATE email_verification_tokens SET used_at=? WHERE id=?", (now, row["id"]))
            conn.execute("UPDATE users SET email_verified=1, verification_pending_optional=0, updated_at=? WHERE id=?", (now, row["user_id"]))
            return True

    def create_password_reset_token(self, email: str) -> Optional[str]:
        with self.connect() as conn:
            user = self._get_user_by_email(conn, email)
            if not user:
                return None
            token = "mf_pr_" + secrets.token_urlsafe(32)
            conn.execute(
                "INSERT INTO password_reset_tokens(id,user_id,token_hash,expires_at,created_at) VALUES(?,?,?,?,?)",
                (new_id("pr"), user["id"], hash_token(token), iso(utcnow() + timedelta(minutes=30)), iso(utcnow())),
            )
            return token

    def reset_password(self, token: str, new_password: str) -> bool:
        if len(new_password) < 8:
            raise ValueError("PASSWORD_TOO_SHORT")
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM password_reset_tokens WHERE token_hash=? AND used_at IS NULL", (hash_token(token),)).fetchone()
            if not row or parse_dt(row["expires_at"]) <= utcnow():
                return False
            now = iso(utcnow())
            conn.execute("UPDATE password_reset_tokens SET used_at=? WHERE id=?", (now, row["id"]))
            conn.execute("UPDATE users SET password_hash=?, updated_at=? WHERE id=?", (self.hash_password(new_password), now, row["user_id"]))
            conn.execute("UPDATE access_tokens SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL", (now, row["user_id"]))
            conn.execute("UPDATE refresh_tokens SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL", (now, row["user_id"]))
            return True

    def profile(self, user_id: str) -> Optional[dict[str, Any]]:
        with self.connect() as conn:
            user = self._get_user_by_id(conn, user_id)
            return self._user_payload_from_row(user, self._tenant(conn, user["tenant_id"])) if user else None

    def update_profile(self, user_id: str, name: str | None = None) -> Optional[dict[str, Any]]:
        with self.connect() as conn:
            user = self._get_user_by_id(conn, user_id)
            if not user:
                return None
            if name:
                conn.execute("UPDATE users SET name=?, updated_at=? WHERE id=?", (name.strip(), iso(utcnow()), user_id))
            user = self._get_user_by_id(conn, user_id)
            return self._user_payload_from_row(user, self._tenant(conn, user["tenant_id"]))

    def auth_status(self) -> dict[str, Any]:
        with self.connect() as conn:
            users = conn.execute("SELECT COUNT(*) c FROM users WHERE deleted_at IS NULL").fetchone()["c"]
            tenants = conn.execute("SELECT COUNT(*) c FROM tenants").fetchone()["c"]
        return {
            "mode": "saas",
            "database": str(self.db_path),
            "users": users,
            "tenants": tenants,
            "roles": ["ADMIN", "USER", "ANALYST", "VIEWER", "DEMO"],
            "email_verification_enabled": self.email_verification_enabled,
            "refresh_rotation": True,
            "tenant_isolation": True,
        }


def user_can(user: dict | None, permission: str) -> bool:
    if not user:
        return False
    role = normalize_role(user.get("role"))
    permissions = set(user.get("permissions") or ROLE_PERMISSIONS.get(role, []))
    return role == "admin" or "view_all" in permissions or permission in permissions
