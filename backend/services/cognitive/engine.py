from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from backend.services.ai_brain import build_ai_brain_snapshot
from backend.services.agents import IntelligenceCoordinator
from backend.services.memory_graph import MemoryGraphEngine
from backend.services.simulation_engine import SimulationEngine
from backend.services.world_model.operational_world_model import OperationalWorldModel
from backend.services.meta_reasoning.reasoning_auditor import ReasoningAuditor
from backend.services.meta_reasoning.confidence_reviewer import ConfidenceReviewer
from backend.services.uncertainty_engine.probabilistic_reasoning import ProbabilisticReasoningEngine
from backend.services.knowledge_engine.historical_intelligence import HistoricalIntelligenceEngine


def build_cognitive_workspace() -> dict[str, Any]:
    snapshot=build_ai_brain_snapshot()
    agent_cycle=IntelligenceCoordinator().run('cognitive_operating_cycle')
    memory_graph=MemoryGraphEngine().build(snapshot, agent_cycle)
    simulations=SimulationEngine().run(snapshot)
    world=OperationalWorldModel().build(snapshot, memory_graph, simulations)
    base_decision=_cognitive_decision_seed(snapshot, world, agent_cycle)
    uncertainty=ProbabilisticReasoningEngine().evaluate(snapshot, world)
    audit=ReasoningAuditor().audit(base_decision, world, agent_cycle)
    confidence=ConfidenceReviewer().review(base_decision['confidence_score'], uncertainty, audit)
    knowledge=HistoricalIntelligenceEngine().evolve(snapshot, world, memory_graph)
    debate=_agent_debate(agent_cycle, world, uncertainty)
    final_decision=_final_decision(base_decision, confidence, uncertainty, audit, world, knowledge, debate)
    return {'ok':True,'generated_at':datetime.now(timezone.utc).isoformat(),'system_version':'1.0.0-cognitive-autonomous-os','data_state':snapshot.get('data_state'),'world_model':world,'meta_reasoning':audit,'self_critique':_self_critique(final_decision, audit, uncertainty),'uncertainty':uncertainty,'autonomous_learning':_learning(snapshot, knowledge, final_decision),'knowledge_evolution':knowledge,'multi_timeframe_intelligence':_timeframes(world, snapshot),'collaborative_agent_society':debate,'cognitive_decision':final_decision,'memory_graph':memory_graph,'simulations':simulations,'observability':_observability(world,audit,uncertainty,knowledge,debate)}


def _cognitive_decision_seed(snapshot: dict[str,Any], world: dict[str,Any], agent_cycle: dict[str,Any]) -> dict[str,Any]:
    regime=world.get('regime')
    if regime=='diagnostic': action='COGNITIVE_DATA_COLLECTION_MODE'; conf=.72; reason='World model indica contexto fraco; decisão cognitiva limita autonomia a diagnóstico.'
    elif regime=='defensive': action='COGNITIVE_DEFENSIVE_MODE'; conf=.78; reason='Risco sistêmico/regime defensivo detectado; preservar bankroll e reduzir exposição.'
    elif regime=='aggressive': action='SELECTIVE_EV_EXPANSION'; conf=.66; reason='EV positivo com risco controlado; expansão apenas seletiva e auditável.'
    else: action='BALANCED_COGNITIVE_MONITORING'; conf=.62; reason='Contexto monitorável sem evidência extrema; manter observação adaptativa.'
    consensus = agent_cycle.get('consensus') or {}
    conflict_count = len(agent_cycle.get('conflicts') or [])
    if isinstance(consensus, dict):
        conflict_count = max(conflict_count, int(consensus.get('conflict_count') or 0))
    elif isinstance(consensus, list):
        conflict_count = max(conflict_count, len([c for c in consensus if isinstance(c, dict) and c.get('status') == 'conflict']))
    if conflict_count > 0: conf-=.08
    return {'action':action,'confidence_score':round(conf,3),'reasoning':reason,'regime':regime}


def _agent_debate(agent_cycle: dict[str,Any], world: dict[str,Any], uncertainty: dict[str,Any]) -> dict[str,Any]:
    findings=agent_cycle.get('findings') or []
    pro=[]; con=[]
    for f in findings[:10]:
        txt=f.get('title') or f.get('finding') or f.get('message') or f.get('agent')
        sev=f.get('severity') or f.get('priority')
        if str(sev).lower() in {'high','critical'} or 'risk' in str(f).lower(): con.append({'agent':f.get('agent','agent'),'argument':txt,'stance':'caution'})
        else: pro.append({'agent':f.get('agent','agent'),'argument':txt,'stance':'support'})
    if uncertainty.get('uncertainty_score',0)>.55: con.append({'agent':'meta_reasoning','argument':'Incerteza elevada reduz força da decisão.', 'stance':'caution'})
    consensus='partial_consensus' if pro and con else 'risk_consensus' if con else 'operational_consensus'
    return {'ok':True,'consensus':consensus,'supporting_arguments':pro[:5],'counter_arguments':con[:5],'conflicts':agent_cycle.get('conflicts') or [],'debate_policy':'bounded single-pass debate; no recursive loops'}


def _final_decision(seed, confidence, uncertainty, audit, world, knowledge, debate):
    action=seed['action']
    if audit.get('verdict')=='review_required' and action not in {'COGNITIVE_DATA_COLLECTION_MODE'}:
        action='HUMAN_REVIEW_BEFORE_' + action
    return {'action':action,'confidence_score':confidence['adjusted_confidence'],'raw_confidence':confidence['raw_confidence'],'reasoning':seed['reasoning'],'world_regime':world.get('regime'),'uncertainty_level':uncertainty.get('ambiguity_level'),'reasoning_quality_score':audit.get('reasoning_quality_score'),'tradeoffs':['bankroll_protection_vs_ev_capture','confidence_vs_sample_size','agent_consensus_vs_uncertainty'],'alternatives':[s.get('expected_state') for s in uncertainty.get('probabilistic_scenarios',[])],'requires_human_review': audit.get('verdict')=='review_required' or uncertainty.get('uncertainty_score',0)>.6,'knowledge_used':[p['id'] for p in knowledge.get('patterns',[])[:3]],'agent_consensus':debate.get('consensus'),'auditability':'decision is explainable, probabilistic and read-only by default'}


def _self_critique(decision,audit,uncertainty):
    critiques=[]
    if uncertainty.get('uncertainty_score',0)>.5: critiques.append('A decisão pode estar sensível à qualidade/amostra dos dados.')
    if audit.get('issues'): critiques.append('Meta-reasoning encontrou pontos que exigem revisão.')
    if decision.get('requires_human_review'): critiques.append('Não executar mudanças automáticas sem validação humana e versionamento.')
    return {'ok':True,'critiques':critiques or ['Nenhuma falha crítica detectada no ciclo cognitivo atual.'],'counterfactuals':['Se EV deteriorar, migrar para modo defensivo.','Se incerteza cair e robustez subir, permitir expansão seletiva.'],'bias_checks':['overconfidence_guard','weak_context_guard','agent_conflict_guard']}


def _learning(snapshot, knowledge, decision):
    return {'mode':'continuous_operational_learning','learned_items':knowledge.get('patterns',[])[:5],'adaptation_candidates':[{'id':'confidence_filter','proposal':'Ajustar filtros de confiança conforme robustez/inconsistência observada.','requires_review':True},{'id':'risk_posture','proposal':f"Postura sugerida baseada em {decision.get('world_regime')}",'requires_review':True}], 'mutation_policy':'no blind model updates; only proposals with audit trail'}


def _timeframes(world,snapshot):
    temp=world.get('temporal_state') or {}
    return {'short_term':temp.get('short_term'),'medium_term':temp.get('medium_term'),'long_term':temp.get('long_term'),'cycle_detection':'insufficient_history' if snapshot.get('data_state')!='real_data' else 'monitoring_cycles','structural_change_risk':'high' if world.get('regime') in {'defensive','diagnostic'} else 'moderate'}


def _observability(world,audit,uncertainty,knowledge,debate):
    return {'trace_mode':'cognitive_structured_reasoning','world_model_regime':world.get('regime'),'reasoning_quality_score':audit.get('reasoning_quality_score'),'uncertainty_score':uncertainty.get('uncertainty_score'),'knowledge_patterns':len(knowledge.get('patterns',[])),'debate_consensus':debate.get('consensus'),'latency_class':'local_deterministic_fast','loop_guard':'single cycle; debate/planning bounded','telemetry':['world_model_trace','uncertainty_trace','reasoning_audit_trace','decision_robustness_trace']}
