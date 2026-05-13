from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.data_engine.providers.flashscore.validate_provider import validate_flashscore_provider


if __name__ == "__main__":
    report = validate_flashscore_provider()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    # Offline not_validated is a warning, not a CI failure. Live probe failures return non-zero.
    if report.get("live_probe_attempted") and not report.get("success"):
        raise SystemExit(2)
    raise SystemExit(0)
