from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _root() -> Path:
    return Path(__file__).resolve().parents[3]


class OperationalMemoryStore:
    """Small durable JSONL memory for operational Copilot context.

    This is intentionally dependency-free and file-backed so it works in local/dev,
    Docker and tests without introducing a database migration. It stores only
    operational events/questions/preferences inferred from explicit user inputs.
    """

    def __init__(self, path: Path | None = None, max_events: int = 500) -> None:
        self.path = path or (_root() / "data" / "ai_brain" / "operational_memory.jsonl")
        self.max_events = max_events
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "payload": payload,
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        self._compact_if_needed()
        return record

    def list_events(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()[-limit:]
        events: list[dict[str, Any]] = []
        for line in lines:
            try:
                item = json.loads(line)
                if isinstance(item, dict):
                    events.append(item)
            except Exception:
                continue
        return events

    def profile(self) -> dict[str, Any]:
        events = self.list_events(self.max_events)
        leagues: Counter[str] = Counter()
        markets: Counter[str] = Counter()
        questions: list[str] = []
        risk_profile = "balanced"
        for event in events:
            payload = event.get("payload") or {}
            if not isinstance(payload, dict):
                continue
            question = str(payload.get("question") or "")
            if question:
                questions.append(question[-240:])
                low = question.lower()
                if any(term in low for term in ["conservador", "risco baixo", "seguro"]):
                    risk_profile = "conservative"
                if any(term in low for term in ["agressivo", "risco alto", "alavancar"]):
                    risk_profile = "aggressive"
            for key, counter in [("league", leagues), ("market", markets)]:
                value = payload.get(key)
                if value:
                    counter[str(value)] += 1
        return {
            "available": bool(events),
            "state": "real_data" if events else "no_data",
            "events": len(events),
            "risk_profile": risk_profile,
            "favorite_leagues": [x for x, _ in leagues.most_common(5)],
            "favorite_markets": [x for x, _ in markets.most_common(5)],
            "recent_questions": questions[-8:],
        }

    def _compact_if_needed(self) -> None:
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
            if len(lines) > self.max_events:
                self.path.write_text("\n".join(lines[-self.max_events:]) + "\n", encoding="utf-8")
        except Exception:
            return
