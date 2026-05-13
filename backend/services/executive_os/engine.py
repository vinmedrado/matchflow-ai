from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from backend.services.cognitive import build_cognitive_workspace
from backend.services.cognitive_hierarchy.engine import CognitiveHierarchyEngine
from backend.services.long_horizon_strategy.strategic_roadmap_engine import StrategicRoadmapEngine
from backend.services.goal_evolution.goal_lifecycle_manager import GoalLifecycleManager
from backend.services.reflection.decision_review_engine import DecisionReviewEngine
from backend.services.experimentation.experiment_runner import ExperimentRunner
from backend.services.governance.policy_engine import PolicyEngine
from backend.services.cognitive_digital_twin.system_self_model import SystemSelfModel
from backend.services.executive_cognition.executive_controller import ExecutiveController


def build_executive_workspace() -> dict[str, Any]:
    cognitive = build_cognitive_workspace()
    hierarchy = CognitiveHierarchyEngine().evaluate(cognitive)
    roadmap = StrategicRoadmapEngine().build(cognitive, hierarchy)
    goal_evolution = GoalLifecycleManager().evolve(cognitive, hierarchy, roadmap)
    reflections = DecisionReviewEngine().run(cognitive, goal_evolution)
    experiments = ExperimentRunner().run(cognitive, roadmap)
    proposed = [{"action": (cognitive.get("cognitive_decision") or {}).get("action", "UNKNOWN")}]
    proposed += [{"action": (m.get("mutation", "").upper() + "_" + m.get("goal_id", "").upper())} for m in goal_evolution.get("mutations", [])]
    governance = PolicyEngine().evaluate(proposed, cognitive)
    twin = SystemSelfModel().build(cognitive, governance, experiments)
    executive = ExecutiveController().decide(cognitive, hierarchy, roadmap, goal_evolution, governance, twin)
    observability = _observability(cognitive, executive, governance, experiments, twin)
    return {"ok": True, "generated_at": datetime.now(timezone.utc).isoformat(), "system_version": "1.0.0-executive-cognitive-autonomous-os", "data_state": cognitive.get("data_state"), "executive_summary": _summary(executive, cognitive, governance, twin), "executive_cognition": executive, "cognitive_hierarchy": hierarchy, "long_horizon_strategy": roadmap, "goal_evolution": goal_evolution, "reflection_cycles": reflections, "experimentation": experiments, "governance": governance, "cognitive_digital_twin": twin, "decision_board": _decision_board(executive, governance, goal_evolution, experiments, reflections, roadmap), "executive_observability": observability, "source_cognitive_decision": cognitive.get("cognitive_decision")}


def _summary(executive: dict[str, Any], cognitive: dict[str, Any], governance: dict[str, Any], twin: dict[str, Any]) -> dict[str, Any]:
    world = cognitive.get("world_model") or {}
    return {"headline": executive.get("executive_action"), "regime": world.get("regime"), "control_mode": executive.get("control_mode"), "safe_mode": governance.get("safe_mode"), "cognitive_health_score": twin.get("cognitive_health_score"), "summary": executive.get("reasoning"), "next_best_action": "revisar bloqueios e reduzir autonomia" if governance.get("safe_mode") else "manter autonomia com guardrails"}


def _decision_board(executive: dict[str, Any], governance: dict[str, Any], goal_evolution: dict[str, Any], experiments: dict[str, Any], reflections: dict[str, Any], roadmap: dict[str, Any]) -> dict[str, Any]:
    return {"active_risks": governance.get("blocks") or [], "active_goals": goal_evolution.get("mutations") or [], "active_experiments": experiments.get("experiments") or [], "active_reflections": reflections.get("reflections") or [], "governance_blocks": governance.get("blocks") or [], "strategic_recommendations": [{"horizon": r.get("horizon"), "objective": r.get("objective"), "posture": r.get("posture")} for r in roadmap.get("roadmap", [])], "final_executive_decision": executive}


def _observability(cognitive: dict[str, Any], executive: dict[str, Any], governance: dict[str, Any], experiments: dict[str, Any], twin: dict[str, Any]) -> dict[str, Any]:
    uncertainty = (cognitive.get("uncertainty") or {}).get("uncertainty_score")
    reasoning = (cognitive.get("meta_reasoning") or {}).get("reasoning_quality_score")
    exp = experiments.get("summary") or {}
    return {"decision_quality_score": executive.get("decision_quality_score"), "reasoning_robustness_score": reasoning, "uncertainty_score": uncertainty, "governance_block_count": governance.get("governance_block_count"), "strategy_health_score": 0.72 if not governance.get("safe_mode") else 0.48, "cognitive_health_score": twin.get("cognitive_health_score"), "experiment_success_rate": exp.get("experiment_success_rate"), "goal_alignment_score": 0.88, "traces": ["executive_trace", "goal_evolution_trace", "reflection_trace", "experiment_trace", "governance_trace", "digital_twin_telemetry", "cognitive_hierarchy_diagnostics"], "performance_guards": {"bounded_cycle": True, "recursive_loops": False, "safe_batching": True, "internal_rate_limit": "single deterministic executive cycle per request"}}
