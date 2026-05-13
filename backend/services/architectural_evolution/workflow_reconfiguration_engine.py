from __future__ import annotations
from typing import Any
class WorkflowReconfigurationEngine:
    def propose(self, recursive: dict[str, Any]) -> dict[str, Any]:
        overload = (recursive.get("workflow") or {}).get("workflow_overload")
        return {"proposals": ["split low-priority reflections into async queue"] if overload else ["keep synchronous executive snapshot"], "requires_approval": True}
