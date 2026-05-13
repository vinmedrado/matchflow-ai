from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "app_config.json"


def _load_dotenv() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@lru_cache(maxsize=1)
def get_settings() -> Dict[str, Any]:
    _load_dotenv()
    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    else:
        data = {}

    data.setdefault("app", {})
    data["app"].setdefault("name", "MatchFlow Analytics")
    data["app"].setdefault("version", "1.5.2")
    data.setdefault("environment", os.getenv("APP_ENV", "local"))
    data.setdefault("demo_mode", os.getenv("DEMO_MODE", "false").lower() in {"1", "true", "yes"})
    data.setdefault("data", {})
    data["data"].setdefault("processed_dataset_path", "data/processed/base_data_engine.parquet")
    data["data"].setdefault("quality_report_path", "data/reports/data_engine_quality_report.json")
    data.setdefault("ollama", {})
    data["ollama"].setdefault("enabled", os.getenv("OLLAMA_ENABLED", "true").lower() == "true")
    data["ollama"].setdefault("base_url", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    data["ollama"].setdefault("model", os.getenv("OLLAMA_MODEL", "llama3.1"))
    data.setdefault("api", {})
    data["api"].setdefault("host", os.getenv("API_HOST", "127.0.0.1"))
    data["api"].setdefault("port", int(os.getenv("API_PORT", "8000")))
    cors_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000")
    data["api"].setdefault("cors_origins", [item.strip() for item in cors_raw.split(",") if item.strip()])
    data["api"].setdefault("cors_origin_regex", os.getenv("CORS_ORIGIN_REGEX", r"https?://(localhost|127\.0\.0\.1):51[0-9]{2}"))
    data.setdefault("auth", {})
    data["auth"].setdefault("enabled", os.getenv("AUTH_ENABLED", "true").lower() in {"1", "true", "yes"})
    data["auth"].setdefault("mode", os.getenv("AUTH_MODE", "saas"))
    data["auth"].setdefault("token_expiration_minutes", int(os.getenv("AUTH_TOKEN_EXPIRATION_MINUTES", "60")))
    data["auth"].setdefault("refresh_token_expiration_days", int(os.getenv("AUTH_REFRESH_TOKEN_EXPIRE_DAYS", "14")))
    data["auth"].setdefault("database_url", os.getenv("AUTH_DATABASE_URL", "data/auth/matchflow_auth.sqlite3"))
    data["auth"].setdefault("email_verification_enabled", os.getenv("EMAIL_VERIFICATION_ENABLED", "false").lower() in {"1", "true", "yes"})
    data["auth"].setdefault("secure_cookies", os.getenv("AUTH_SECURE_COOKIES", "false").lower() in {"1", "true", "yes"})
    data["auth"].setdefault("public_registration_enabled", os.getenv("AUTH_PUBLIC_REGISTRATION_ENABLED", "true").lower() in {"1", "true", "yes"})
    data["auth"].setdefault("test_user", {
        "email": "admin@matchflow.local",
        "password": "admin123",
        "name": "Admin MatchFlow",
    })
    data.setdefault("cache", {"enabled": True})
    return data


def resolve_project_path(relative_or_absolute: str) -> Path:
    path = Path(relative_or_absolute)
    return path if path.is_absolute() else PROJECT_ROOT / path
