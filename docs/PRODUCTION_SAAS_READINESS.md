# MatchFlow AI — Production SaaS Readiness

This release hardens backend permissions, tenant context, Data Engine access, demo account controls, Docker static validation and FlashScore validation reporting.

## Deploy command

```bash
cp .env.example .env
# edit .env with production values
python scripts/validate_docker_config.py
docker compose -f docker-compose.prod.yml up --build
```

## Email verification

Default is `EMAIL_VERIFICATION_ENABLED=false`. Users can use the app normally and `verification_pending_optional=true` is explicit in auth payloads. Enable it only after configuring an email sender.

## Demo accounts

Demo accounts are controlled by:

```env
ENABLE_DEMO_ACCOUNTS=true
DEMO_ACCOUNTS_ALLOWED_ENV=development,demo,local
DISABLE_DEMO_ACCOUNTS_IN_PRODUCTION=true
```

In production, demo seeding is disabled when `DISABLE_DEMO_ACCOUNTS_IN_PRODUCTION=true`.

## FlashScore validation

Offline readiness:

```bash
python scripts/validate_flashscore_provider.py
```

Live probe:

```bash
python -m playwright install chromium
MATCHFLOW_FLASH_SCORE_VALIDATE_LIVE=1 python scripts/validate_flashscore_provider.py
```

If the live probe is not executed, the report must remain `not_validated`/warning and must not pretend production scraping was validated.
