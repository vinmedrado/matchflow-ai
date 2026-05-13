import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client.js';
import { DataStateBadge, PremiumHeader, PremiumState, StatTile } from '../components/PremiumViz.jsx';

const sevRank = { critical: 4, high: 3, medium: 2, info: 1 };

function ObjectiveCard({ objective }) {
  return <article className="objective-card">
    <div className="objective-head"><div><b>{objective.title}</b><small>{objective.intent}</small></div><span className={`severity severity-${objective.severity}`}>{objective.severity}</span></div>
    <div className="objective-progress"><i style={{width: `${objective.progress_pct ?? 18}%`}} /></div>
    <div className="objective-meta"><span>status: {objective.status}</span><span>prioridade: {objective.priority}</span><span>métrica: {objective.target_metric}</span></div>
    <p>{objective.reasoning}</p>
    <small>Guardrail: {objective.guardrail}</small>
  </article>;
}

function WorkflowCard({ workflow }) {
  return <article className="workflow-card">
    <div className="workflow-title"><b>{workflow.name}</b><span className={`severity severity-${workflow.severity}`}>{workflow.severity}</span></div>
    <small>{workflow.status} • objetivo {workflow.objective_id}</small>
    <div className="workflow-steps">{(workflow.steps || []).slice(0,4).map(step => <span key={step.id}>{step.title}</span>)}</div>
    <em>{workflow.audit?.mutation_policy}</em>
  </article>;
}

function MemoryGraph({ graph }) {
  const nodes = graph?.nodes || [];
  const edges = graph?.edges || [];
  if (!nodes.length) return <PremiumState empty message="Memory graph ainda sem entidades suficientes." />;
  return <div className="memory-graph">
    <div className="graph-core">AI<br/>OS</div>
    {nodes.slice(0,18).map((n, i) => <div key={n.id} className={`graph-node graph-${n.type}`} style={{'--i': i}}><b>{n.label}</b><small>{n.type}</small></div>)}
    <div className="graph-caption">{nodes.length} nós • {edges.length} relações • {graph?.summary?.repeated_entities || 0} clusters</div>
  </div>;
}

function PlanningList({ tasks = [] }) {
  if (!tasks.length) return <PremiumState empty message="Nenhuma tarefa planejada nesta rodada." />;
  return <div className="planning-list">{tasks.slice(0,12).map(t => <div key={t.id}><b>{t.id} — {t.title}</b><small>{t.owner} • prioridade {t.priority} • revisão: {t.requires_human_review ? 'sim' : 'não'}</small></div>)}</div>;
}

function SimulationPanel({ simulations }) {
  const scenarios = simulations?.scenarios || [];
  return <div className="simulation-grid">{scenarios.map(s => <div key={s.name} className="simulation-card"><b>{s.name}</b><strong>{s.projected_ev_pct ?? '—'}%</strong><small>EV projetado</small><span>risk {s.risk_score ?? 'n/d'}</span><em>{s.recommendation || s.message}</em></div>)}</div>;
}

export default function AutonomousWorkspace() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [question, setQuestion] = useState('Quais objetivos estão prioritários agora?');
  const [answer, setAnswer] = useState(null);
  const [asking, setAsking] = useState(false);
  const load = () => { setLoading(true); setError(null); api.autonomousWorkspace().then(setData).catch(setError).finally(()=>setLoading(false)); };
  useEffect(load, []);
  const ask = async () => { setAsking(true); setAnswer(null); try { setAnswer(await api.autonomousAsk(question)); } catch(e) { setAnswer({ ok:false, answer:e.message }); } finally { setAsking(false); } };
  const activeGoals = data?.goals?.active_objectives || [];
  const objectives = (activeGoals.length ? activeGoals : data?.goals?.objectives || []).slice().sort((a,b)=>(sevRank[b.severity]||0)-(sevRank[a.severity]||0));
  const decision = data?.autonomous_decision || {};
  const workflows = data?.workflows?.workflows || [];
  const tasks = data?.planning?.plan?.tasks || [];
  const obs = data?.observability || {};
  const routes = data?.goal_routes || [];
  const topRoute = useMemo(() => routes.slice(0,4).map(r => `${r.objective_id}→${r.route_to}`).join(' • '), [routes]);

  return <div className="premium-page autonomous-page">
    <PremiumHeader eyebrow="Goal-Driven Autonomous AI Operating System" title="MatchFlow Autonomous Workspace" subtitle="Objetivos, planejamento, workflows, memory graph, simulações e decisão autônoma auditável em um cockpit AI-native." actions={<button className="premium-button" onClick={load}>Atualizar OS</button>} />
    <PremiumState loading={loading} error={error} onRetry={load}/>
    {!loading && !error && data && <>
      <div className="premium-grid four">
        <StatTile label="Objetivos ativos" value={activeGoals.length} sub={`${data.goals?.summary?.needs_action || 0} exigem ação`} state={data.data_state}/>
        <StatTile label="Plan tasks" value={data.planning?.plan?.tasks_total || 0} sub="dependency graph" tone="blue" state={data.data_state}/>
        <StatTile label="Workflows" value={data.workflows?.summary?.total || 0} sub={`${data.workflows?.summary?.ready || 0} prontos`} tone="orange" state={data.data_state}/>
        <StatTile label="Memory graph" value={data.memory_graph?.summary?.nodes || 0} sub={`${data.memory_graph?.summary?.edges || 0} relações`} tone="green" state={data.data_state}/>
      </div>

      <section className="premium-panel os-decision">
        <div className="panel-title"><h2>Autonomous Decision Engine <DataStateBadge state={decision.state}/></h2><span>{decision.auditability}</span></div>
        <div className="os-decision-main"><strong>{decision.action}</strong><span>confidence {decision.confidence_score}</span></div>
        <p>{decision.reasoning}</p>
        <div className="decision-tags"><span>regime sugerido: {decision.simulation_preferred_regime || 'n/d'}</span><span>agentic: {decision.agentic_action || 'n/d'}</span><span>human review: {decision.requires_human_review ? 'sim' : 'não'}</span></div>
      </section>

      <div className="premium-grid two">
        <section className="premium-panel"><div className="panel-title"><h2>Goal Engine</h2><span>{topRoute || 'rotas indisponíveis'}</span></div><div className="objective-grid">{objectives.slice(0,8).map(o => <ObjectiveCard objective={o} key={o.id}/>)}</div></section>
        <section className="premium-panel"><div className="panel-title"><h2>Planning Engine</h2><span>multi-step • adaptive • dependency graph</span></div><PlanningList tasks={tasks}/></section>
      </div>

      <div className="premium-grid two">
        <section className="premium-panel"><div className="panel-title"><h2>Autonomous Workflows</h2><span>diagnóstico executável + revisão humana</span></div><div className="workflow-grid">{workflows.slice(0,8).map(w => <WorkflowCard workflow={w} key={w.id}/>)}</div></section>
        <section className="premium-panel"><div className="panel-title"><h2>Simulation Engine</h2><span>{data.simulations?.audit}</span></div><SimulationPanel simulations={data.simulations}/></section>
      </div>

      <div className="premium-grid two-one">
        <section className="premium-panel"><div className="panel-title"><h2>Memory Graph</h2><span>ligas • mercados • riscos • decisões • agentes</span></div><MemoryGraph graph={data.memory_graph}/></section>
        <section className="premium-panel"><div className="panel-title"><h2>LLM Orchestration</h2><span>planning-aware reasoning</span></div><div className="autonomous-ask"><input value={question} onChange={e=>setQuestion(e.target.value)} /><button onClick={ask} disabled={asking}>{asking?'Roteando...':'Perguntar'}</button></div>{answer && <div className="ai-answer"><b>{answer.router?.pipeline || 'erro'}</b><p>{answer.answer}</p></div>}</section>
      </div>

      <section className="premium-panel"><div className="panel-title"><h2>Enterprise Observability</h2><span>goal tracing • workflow tracing • memory tracing • decision tracing</span></div><pre className="diagnostic-pre">{JSON.stringify(obs, null, 2)}</pre></section>
    </>}
  </div>;
}
