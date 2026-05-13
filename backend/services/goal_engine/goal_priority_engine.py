from __future__ import annotations
from typing import Any

class GoalPriorityEngine:
    def reprioritize(self, objectives: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(objectives, key=lambda o: (o.get('priority') or 0, 1 if o.get('status') == 'needs_action' else 0), reverse=True)
