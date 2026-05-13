from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from backend.services.executive_os.engine import build_executive_workspace
from backend.services.recursive_improvement.performance_feedback_engine import PerformanceFeedbackEngine
from backend.services.meta_learning.learning_strategy_engine import LearningStrategyEngine
from backend.services.meta_learning.adaptation_analyzer import AdaptationAnalyzer
from backend.services.meta_learning.learning_efficiency_tracker import LearningEfficiencyTracker
from backend.services.meta_learning.intelligence_evolution_engine import IntelligenceEvolutionEngine
from backend.services.meta_learning.operational_learning_patterns import OperationalLearningPatterns
from backend.services.architectural_evolution.architecture_review_engine import ArchitectureReviewEngine
from backend.services.architectural_evolution.workflow_reconfiguration_engine import WorkflowReconfigurationEngine
from backend.services.architectural_evolution.routing_adaptation_engine import RoutingAdaptationEngine
from backend.services.architectural_evolution.orchestration_optimizer import OrchestrationOptimizer
from backend.services.architectural_evolution.modularity_evaluator import ModularityEvaluator
from backend.services.executive_agents.executive_risk_agent import ExecutiveRiskAgent
from backend.services.executive_agents.executive_strategy_agent import ExecutiveStrategyAgent
from backend.services.executive_agents.executive_performance_agent import ExecutivePerformanceAgent
from backend.services.executive_agents.executive_governance_agent import ExecutiveGovernanceAgent
from backend.services.executive_agents.executive_research_agent import ExecutiveResearchAgent
from backend.services.executive_agents.executive_coordination_agent import ExecutiveCoordinationAgent
from backend.services.cognitive_economy.reasoning_budget_engine import ReasoningBudgetEngine
from backend.services.cognitive_economy.attention_allocator import AttentionAllocator
from backend.services.cognitive_economy.cognitive_priority_router import CognitivePriorityRouter
from backend.services.cognitive_economy.resource_pressure_engine import ResourcePressureEngine
from backend.services.cognitive_economy.complexity_manager import ComplexityManager
from backend.services.self_preservation.cognitive_health_guard import CognitiveHealthGuard
from backend.services.self_preservation.overload_detector import OverloadDetector
from backend.services.self_preservation.defensive_mode_engine import DefensiveModeEngine
from backend.services.self_preservation.stability_protector import StabilityProtector
from backend.services.self_preservation.autonomous_safety_engine import AutonomousSafetyEngine
from backend.services.executive_memory.strategic_memory_consolidator import StrategicMemoryConsolidator
from backend.services.executive_memory.long_term_pattern_compressor import LongTermPatternCompressor
from backend.services.executive_memory.executive_knowledge_synthesizer import ExecutiveKnowledgeSynthesizer
from backend.services.executive_memory.operational_abstraction_engine import OperationalAbstractionEngine
from backend.services.continual_evolution.strategic_evolution_engine import StrategicEvolutionEngine
from backend.services.continual_evolution.philosophy_adaptation_engine import PhilosophyAdaptationEngine
from backend.services.continual_evolution.macro_behavior_engine import MacroBehaviorEngine
from backend.services.continual_evolution.long_term_objective_evolution import LongTermObjectiveEvolution


def build_evolution_workspace(request_type: str = "dashboard") -> dict[str, Any]:
    executive = build_executive_workspace()
    recursive = PerformanceFeedbackEngine().run(executive)
    meta_base = LearningStrategyEngine().analyze(executive, recursive)
    adaptation = AdaptationAnalyzer().analyze(meta_base)
    tracker = LearningEfficiencyTracker().track(meta_base, adaptation)
    intelligence_evolution = IntelligenceEvolutionEngine().evolve(tracker)
    learning_patterns = OperationalLearningPatterns().build()
    meta_learning = {**meta_base, "adaptation": adaptation, "tracker": tracker, "intelligence_evolution": intelligence_evolution, **learning_patterns}

    architecture = _architecture(executive, recursive)
    society = _executive_society(executive)
    economy = _cognitive_economy(executive, recursive, meta_base, request_type)
    preservation = _self_preservation(executive, economy)
    memory = _executive_memory(executive)
    continual = _continual_evolution(executive, meta_learning)
    observability = _observability(recursive, meta_learning, society, economy, preservation, continual)
    summary = _summary(executive, recursive, meta_learning, society, preservation, observability)
    return {
        "ok": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system_version": "1.1.0-self-evolving-executive-cognitive-ai-system",
        "data_state": executive.get("data_state"),
        "executive_base": executive,
        "evolution_summary": summary,
        "recursive_improvement": recursive,
        "meta_learning": meta_learning,
        "architectural_evolution": architecture,
        "executive_agent_society": society,
        "cognitive_economy": economy,
        "self_preservation": preservation,
        "executive_memory_consolidation": memory,
        "continual_strategic_evolution": continual,
        "evolution_observability": observability,
        "performance_guards": {
            "recursion_limit": 2,
            "execution_budget": economy.get("budget"),
            "adaptive_throttling": economy.get("complexity", {}).get("throttling"),
            "circuit_breaker": preservation.get("protector", {}).get("circuit_breaker_active"),
            "self_modifies_code": False,
        },
    }


def _architecture(executive: dict[str, Any], recursive: dict[str, Any]) -> dict[str, Any]:
    return {
        "architecture_review": ArchitectureReviewEngine().review(executive),
        "workflow_reconfiguration": WorkflowReconfigurationEngine().propose(recursive),
        "routing_adaptation": RoutingAdaptationEngine().route(),
        "orchestration_optimizer": OrchestrationOptimizer().optimize(),
        "modularity": ModularityEvaluator().evaluate(),
    }


def _executive_society(executive: dict[str, Any]) -> dict[str, Any]:
    agents = [
        ExecutiveRiskAgent().argue(executive),
        ExecutiveStrategyAgent().argue(executive),
        ExecutivePerformanceAgent().argue(executive),
        ExecutiveGovernanceAgent().argue(executive),
        ExecutiveResearchAgent().argue(executive),
    ]
    return ExecutiveCoordinationAgent().coordinate(agents)


def _cognitive_economy(executive: dict[str, Any], recursive: dict[str, Any], meta: dict[str, Any], request_type: str) -> dict[str, Any]:
    budget = ReasoningBudgetEngine().budget(request_type)
    attention = AttentionAllocator().allocate(executive)
    priority = CognitivePriorityRouter().route()
    pressure = ResourcePressureEngine().pressure(recursive, meta)
    complexity = ComplexityManager().manage(pressure)
    return {"budget": budget, "attention": attention, "priority": priority, "pressure": pressure, "complexity": complexity}


def _self_preservation(executive: dict[str, Any], economy: dict[str, Any]) -> dict[str, Any]:
    pressure = economy.get("pressure") or {}
    guard = CognitiveHealthGuard().evaluate(pressure, executive)
    overload = OverloadDetector().detect(pressure)
    mode = DefensiveModeEngine().mode(guard, overload, executive)
    protector = StabilityProtector().protect(mode)
    safety = AutonomousSafetyEngine().evaluate(mode, protector)
    return {"guard": guard, "overload": overload, "mode": mode, "protector": protector, "safety": safety}


def _executive_memory(executive: dict[str, Any]) -> dict[str, Any]:
    consolidated = StrategicMemoryConsolidator().consolidate(executive)
    compressed = LongTermPatternCompressor().compress(consolidated)
    synthesized = ExecutiveKnowledgeSynthesizer().synthesize(compressed)
    abstraction = OperationalAbstractionEngine().abstract(synthesized)
    return {"consolidated": consolidated, "compressed": compressed, "synthesized": synthesized, "abstraction": abstraction}


def _continual_evolution(executive: dict[str, Any], meta_learning: dict[str, Any]) -> dict[str, Any]:
    strategic = StrategicEvolutionEngine().evolve(executive, meta_learning)
    philosophy = PhilosophyAdaptationEngine().adapt(strategic)
    macro = MacroBehaviorEngine().model(philosophy)
    objectives = LongTermObjectiveEvolution().evolve(macro)
    return {"strategic": strategic, "philosophy": philosophy, "macro_behavior": macro, "objectives": objectives}


def _observability(recursive: dict[str, Any], meta: dict[str, Any], society: dict[str, Any], economy: dict[str, Any], preservation: dict[str, Any], continual: dict[str, Any]) -> dict[str, Any]:
    return {
        "cognitive_efficiency_score": round(1 - float(economy.get("pressure", {}).get("overload_risk_score") or 0), 3),
        "reasoning_cost_score": (recursive.get("reasoning") or {}).get("reasoning_cost_score"),
        "adaptation_quality_score": (meta.get("adaptation") or {}).get("adaptation_quality_score"),
        "executive_consensus_score": society.get("executive_consensus_score"),
        "strategic_stability_score": (recursive.get("strategy") or {}).get("strategy_stability_score"),
        "learning_efficiency_score": meta.get("learning_efficiency_score"),
        "overload_risk_score": economy.get("pressure", {}).get("overload_risk_score"),
        "self_preservation_score": preservation.get("guard", {}).get("self_preservation_score"),
        "recursive_improvement_score": (recursive.get("cognition") or {}).get("recursive_improvement_score"),
        "traces": ["recursive_trace", "evolution_trace", "adaptation_trace", "cognitive_economy_telemetry", "executive_negotiation_trace", "learning_diagnostics", "self_preservation_telemetry", "strategic_evolution_metrics"],
        "macro_behavior": continual.get("strategic", {}).get("macro_behavior"),
    }


def _summary(executive: dict[str, Any], recursive: dict[str, Any], meta: dict[str, Any], society: dict[str, Any], preservation: dict[str, Any], obs: dict[str, Any]) -> dict[str, Any]:
    mode = preservation.get("mode", {}).get("mode")
    return {
        "headline": "Self-evolving executive cognition operating under governance and cognitive economy controls",
        "evolution_state": meta.get("intelligence_evolution", {}).get("evolution_state"),
        "self_preservation_mode": mode,
        "consensus": society.get("consensus"),
        "status": recursive.get("status"),
        "next_best_action": "reduce autonomy and stabilize" if mode != "normal_mode" else "continue controlled recursive improvement",
        "scorecard": obs,
    }
