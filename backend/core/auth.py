from __future__ import annotations

from backend.core.saas_auth import ROLE_PERMISSIONS, SaaSAuthManager, TokenRecord, user_can

# Backward-compatible import name used by historical tests and backend.main.
LocalDevAuthManager = SaaSAuthManager
