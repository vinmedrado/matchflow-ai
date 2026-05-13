import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client.js';
import { DataStateBadge, PremiumHeader, PremiumState, StatTile } from '../components/PremiumViz.jsx';

const severityRank = { critical: 4, high: 3, medium: 2, info: 1 };

function AgentCard({ agent }) {
  const findings = agent?.findings || [];
  const top = findings.slice().sort((a,b)=>(severityRank[b.severity]||0)-(severityRank[a.severity]||0))[0];
  return <article className="agent-card">
    <div className="agent-card-head"><div><b>{agent.agent}</b><small>{agent.role}</small></div><DataStateBadge state={agent.state}/></div>
    <p>{agent.summary}</p>
    {top && <div className="agent-finding"><span className={`severity severity-${top.severity}`}>{top.severity}</span><b>{top.title}</b><small>{top.reasoning}</small></div>}
  </article>;
}

function Timeline({ events = [] }) {
  if (!events.length) return <PremiumState empty message="Nenhum evento agentic emitido nesta rodada." />;
  return <div className="agent-timeline">{events.map((e,i)=><div key={`${e.seq}-${i}`} className="agent-event"><span>{e.event_type}</span><b>{e.agent || e.action || e.topic}</b><small>{e.summary}</small></div>)}</div>;
}

export default function AgenticIntelligence() {
  const [data,setData]=useState(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState(null);
  const [task,setTask]=useState('continuous_operational_review');
  const [running,setRunning]=useState(false);
  const load=()=>{setLoading(true);setError(null);api.agentsCockpit().then(setData).catch(setError).finally(()=>setLoading(false));};
  useEffect(load,[]);
  const coordinate=async()=>{setRunning(true);setError(null);try{setData(await api.agentsCoordinate(task));}catch(e){setError(e);}finally{setRunning(false);}};
  const findings = data?.findings || [];
  const critical = findings.filter(f=>['critical','high'].includes(f.severity)).length;
  const consensus = data?.consensus || [];
  const decision = data?.decision || {};
  const proposals = data?.self_optimization?.proposals || [];
  const hypotheses = data?.auto_research?.hypotheses || [];
  const agents = data?.agents || [];
  const severitySpread = useMemo(()=>Object.entries(data?.observability?.severity_distribution || {}).map(([k,v])=>`${k}: ${v}`).join(' • '),[data]);

  return <div className="premium-page agentic-page">
    <PremiumHeader eyebrow="Autonomous Multi-Agent Intelligence" title="MatchFlow Agentic Cockpit" subtitle="Coordenação de agentes especializados, decisão auditável, auto-research e self-optimization sem mutação automática dos modelos." actions={<button className="premium-button" onClick={coordinate} disabled={running}>{running?'Coordenando...':'Rodar coordenação'}</button>} />
    <PremiumState loading={loading} error={error} onRetry={load}/>
    {!loading && !error && data && <>
      <div className="agent-command-bar"><input value={task} onChange={e=>setTask(e.target.value)} placeholder="task routing: ex. review BTTS drawdown"/><button onClick={coordinate} disabled={running}>Enviar tarefa</button><DataStateBadge state={data.data_state}/></div>
      <div className="premium-grid four">
        <StatTile label="Agentes" value={agents.length} sub="especialistas executados" state={data.data_state}/>
        <StatTile label="Findings" value={findings.length} sub={severitySpread || 'sem distribuição'} tone="green" state={data.data_state}/>
        <StatTile label="Riscos altos" value={critical} sub="high/critical" tone="orange" state={data.data_state}/>
        <StatTile label="Decisão" value={decision.action || '—'} sub={`confiança ${decision.confidence_score ?? '—'}`} tone="blue" state={decision.state}/>
      </div>
      <div className="premium-grid two-one">
        <section className="premium-panel decision-panel"><div className="panel-title"><h2>AI Decision Engine</h2><span>auditable reasoning</span></div><div className="decision-action">{decision.action}</div><p>{decision.reasoning}</p><small>{decision.recommendation_summary}</small><div className="decision-tags"><span>human review: {decision.requires_human_review ? 'sim' : 'não'}</span><span>{decision.auditability}</span></div></section>
        <section className="premium-panel compact"><div className="panel-title"><h2>Conflitos</h2><span>resolution engine</span></div>{(data.conflicts||[]).length ? data.conflicts.map((c,i)=><div className="compact-row" key={i}><b>{c.topic}</b><small>{c.reasoning} {c.resolution}</small></div>) : <PremiumState empty message="Nenhum conflito relevante entre agentes."/>}</section>
      </div>
      <section className="premium-panel"><div className="panel-title"><h2>Agentes especializados</h2><span>risk • strategy • market • bankroll • anomaly • performance • research • alert • execution</span></div><div className="agent-grid">{agents.map(a=><AgentCard agent={a} key={a.agent}/>)}</div></section>
      <div className="premium-grid two">
        <section className="premium-panel"><div className="panel-title"><h2>Consenso operacional</h2><span>aggregation pipeline</span></div><div className="timeline-list">{consensus.map((c,i)=><div key={i}><b>{c.topic} <span className={`severity severity-${c.severity}`}>{c.severity}</span></b><small>{c.reasoning}</small><small>Recomendação: {c.recommendation}</small></div>)}</div></section>
        <section className="premium-panel"><div className="panel-title"><h2>Realtime reasoning feed</h2><span>event intelligence</span></div><Timeline events={data.event_stream}/></section>
      </div>
      <div className="premium-grid two">
        <section className="premium-panel"><div className="panel-title"><h2>Auto Research Engine</h2><span>hypothesis discovery</span></div><div className="timeline-list">{hypotheses.map((h,i)=><div key={i}><b>{h.title}</b><small>{h.hypothesis}</small><small>{h.validation_plan}</small><DataStateBadge state={h.state}/></div>)}</div></section>
        <section className="premium-panel"><div className="panel-title"><h2>Self-Optimization</h2><span>advisory + versioned</span></div><div className="timeline-list">{proposals.map((p,i)=><div key={i}><b>{p.type}</b><small>{p.proposal}</small><small>Revisão humana: {p.requires_review ? 'obrigatória' : 'não obrigatória'}</small></div>)}</div></section>
      </div>
      <section className="premium-panel"><div className="panel-title"><h2>Enterprise Observability</h2><span>agent diagnostics + tracing</span></div><pre className="diagnostic-pre">{JSON.stringify(data.observability, null, 2)}</pre></section>
    </>}
  </div>;
}
