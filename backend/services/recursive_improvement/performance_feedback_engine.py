from __future__ import annotations
from typing import Any
from .cognition_optimizer import CognitionOptimizer
from .reasoning_optimizer import ReasoningOptimizer
from .workflow_optimizer import WorkflowOptimizer
from .strategy_optimizer import StrategyOptimizer

class PerformanceFeedbackEngine:
    def run(self, executive: dict[str, Any]) -> dict[str, Any]:
        cognition = CognitionOptimizer().evaluate(executive)
        reasoning = ReasoningOptimizer().optimize(executive)
        workflow = WorkflowOptimizer().evaluate(executive)
        strategy = StrategyOptimizer().evaluate(executive)
        return {"cognition": cognition, "reasoning": reasoning, "workflow": workflow, "strategy": strategy, "continuous_improvement_cycle": ["measure", "detect", "propose", "govern", "review"], "status": "review_required" if cognition["bottlenecks"] else "stable"}
