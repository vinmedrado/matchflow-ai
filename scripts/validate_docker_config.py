from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "Dockerfile.prod",
    "docker-compose.prod.yml",
    "frontend/Dockerfile.prod",
    ".env.example",
]


def read(path: str) -> str:
    p = ROOT / path
    return p.read_text(encoding="utf-8") if p.exists() else ""


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    for rel in REQUIRED:
        if not (ROOT / rel).exists():
            errors.append(f"missing:{rel}")
    compose = read("docker-compose.prod.yml")
    backend_df = read("Dockerfile.prod")
    frontend_df = read("frontend/Dockerfile.prod")
    env = read(".env.example")

    checks = {
        "compose_has_backend": "backend:" in compose,
        "compose_has_frontend": "frontend:" in compose,
        "compose_has_healthcheck": "healthcheck:" in compose,
        "compose_uses_prod_env": "APP_ENV: production" in compose or "ENVIRONMENT: production" in compose,
        "backend_not_reload": "--reload" not in backend_df and "uvicorn backend.main:app --reload" not in compose,
        "backend_uses_gunicorn_or_uvicorn": "gunicorn" in backend_df or "uvicorn" in backend_df,
        "frontend_builds_dist": "npm run build" in frontend_df,
        "env_has_demo_flags": all(k in env for k in ["ENABLE_DEMO_ACCOUNTS", "DEMO_ACCOUNTS_ALLOWED_ENV", "DISABLE_DEMO_ACCOUNTS_IN_PRODUCTION"]),
        "env_has_email_verification_flag": "EMAIL_VERIFICATION_ENABLED=false" in env,
        "no_real_secret_markers": not re.search(r"(sk-|ghp_|xoxb-|AIza|AKIA)[A-Za-z0-9_\-]{8,}", env + compose + backend_df + frontend_df),
    }
    for name, ok in checks.items():
        if not ok:
            errors.append(f"failed:{name}")
    if ".env" in compose:
        warnings.append("compose references .env; create it from .env.example before production deploy")
    report = {"ok": not errors, "checks": checks, "errors": errors, "warnings": warnings, "next_command": "docker compose -f docker-compose.prod.yml up --build"}
    out = ROOT / "data/reports/docker_config_validation_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not errors else 1

if __name__ == "__main__":
    raise SystemExit(main())
