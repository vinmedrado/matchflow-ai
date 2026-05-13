import { useEffect, useState } from 'react';
import { api } from '../api/client.js';
import { DataStateBadge, PremiumHeader, PremiumState, StatTile } from '../components/PremiumViz.jsx';

function ListBlock({ title, subtitle, items = [], render }) {
  return <section className="premium-panel">
    <div className="panel-title"><h2>{title}</h2><span>{subtitle}</span></div>
    <div className="planning-list">{items.length ? items.map(render) : <PremiumState empty message="Sem registros nesta rodada executiva." />}</div>
  </section>;
}

function Gauge({ label, value }) {
  const pct = Math.round((Number(value) || 0) * 100);
  return <div className="simulation-card"><b>{label}</b><strong>{pct}%</strong><div className="objective-progress"><i style={{width:`${pct}%`}} /></div></div>;
}

function ExecutiveBoard({ data }) {
  const board = data?.decision_board || {};
  const summary = data?.executive_summary || {};
  return <section className="premium-panel os-decision">
    <div className="panel-title"><h2>Executive Decision Board <DataStateBadge state={data?.data_state}/></h2><span>{data?.system_version}</span></div>
    <div className="os-decision-main"><strong>{summary.headline || 'n/d'}</strong><span>{summary.control_mode}</span></div>
    <p>{summary.summary}</p>
    <div className="decision-tags"><span>regime: {summary.regime}</span><span>safe mode: {summary.safe_mode ? 'ativo' : 'off'}</span><span>next: {summary.next_best_action}</span></div>
    <div className="workflow-grid">
      {(board.strategic_recommendations || []).map((r) => <article className="workflow-card" key={r.horizon}><b>{r.horizon}</b><small>{r.posture}</small><p>{r.objective}</p></article>)}
    </div>
  </section>;
}

function Hierarchy({ hierarchy }) {
  return <section className="premium-panel"><div className="panel-title"><h2>Cognitive Hierarchy</h2><span>{hierarchy?.decision_layer}</span></div>
    <p>{hierarchy?.decision_layer_explanation}</p>
    <div className="workflow-grid">{(hierarchy?.layers || []).map(l => <article className="workflow-card" key={l.id}><b>{l.name}</b><small>{l.state} • {l.active ? 'active' : 'standby'}</small><p>{l.purpose}</p></article>)}</div>
  </section>;
}

function Roadmap({ roadmap }) {
  return <section className="premium-panel"><div className="panel-title"><h2>Long-Horizon Strategy</h2><span>{roadmap?.posture}</span></div>
    <div className="workflow-grid">{(roadmap?.roadmap || []).map(r => <article className="workflow-card" key={r.horizon}><b>{r.horizon}</b><small>{r.risk} • {r.posture}</small><p>{r.objective}</p><ul>{(r.actions || []).slice(0,3).map(a => <li key={a}>{a}</li>)}</ul></article>)}</div>
  </section>;
}

export default function ExecutiveCockpit() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [question, setQuestion] = useState('Qual é a decisão executiva agora?');
  const [answer, setAnswer] = useState(null);
  const [asking, setAsking] = useState(false);
  const load = () => { setLoading(true); setError(null); api.executiveWorkspace().then(setData).catch(setError).finally(() => setLoading(false)); };
  useEffect(load, []);
  const ask = async () => { setAsking(true); setAnswer(null); try { setAnswer(await api.executiveAsk(question)); } catch(e) { setAnswer({answer:e.message}); } finally { setAsking(false); } };
  const obs = data?.executive_observability || {};
  const gov = data?.governance || {};
  const twin = data?.cognitive_digital_twin || {};
  return <div className="premium-page autonomous-page">
    <PremiumHeader eyebrow="Executive Cognitive Autonomous AI Operating System" title="MatchFlow Executive Cockpit" subtitle="Camada executiva com hierarquia cognitiva, governança, reflexão, experimentos, digital twin e roadmap estratégico auditável." actions={<button className="premium-button" onClick={load}>Atualizar Executive OS</button>} />
    <PremiumState loading={loading} error={error} onRetry={load}/>
    {!loading && !error && data && <>
      <div className="premium-grid four">
        <StatTile label="Decision Quality" value={`${Math.round((obs.decision_quality_score || 0) * 100)}%`} sub={data.executive_cognition?.control_mode} state={data.data_state}/>
        <StatTile label="Cognitive Health" value={`${Math.round((obs.cognitive_health_score || 0) * 100)}%`} sub={twin.forecast} tone="green" state={data.data_state}/>
        <StatTile label="Governance Blocks" value={obs.governance_block_count ?? 0} sub={gov.safe_mode ? 'safe mode ativo' : 'guardrails ok'} tone="orange" state={data.data_state}/>
        <StatTile label="Goal Alignment" value={`${Math.round((obs.goal_alignment_score || 0) * 100)}%`} sub="executive alignment" tone="blue" state={data.data_state}/>
      </div>
      <ExecutiveBoard data={data}/>
      <div className="premium-grid two">
        <Hierarchy hierarchy={data.cognitive_hierarchy}/>
        <section className="premium-panel"><div className="panel-title"><h2>Executive Observability</h2><span>bounded cycle • safe batching</span></div><div className="simulation-grid"><Gauge label="Reasoning" value={obs.reasoning_robustness_score}/><Gauge label="Strategy" value={obs.strategy_health_score}/></div><pre className="diagnostic-pre">{JSON.stringify(obs.performance_guards, null, 2)}</pre></section>
      </div>
      <Roadmap roadmap={data.long_horizon_strategy}/>
      <div className="premium-grid two">
        <ListBlock title="Goal Evolution Timeline" subtitle={data.goal_evolution?.lifecycle_policy} items={data.goal_evolution?.mutations || []} render={(g)=><div key={g.goal_id}><b>{g.goal_id}</b><small>{g.mutation} • priority {g.new_priority}</small><p>{g.reason}</p></div>} />
        <ListBlock title="Governance Center" subtitle={`safe mode: ${gov.safe_mode ? 'ativo' : 'off'}`} items={[...(gov.blocks || []), ...(gov.approvals_required || []), ...(gov.allowed_actions || [])]} render={(x,i)=><div key={i}><b>{x.action}</b><small>{x.policy}</small><p>{x.reason}</p></div>} />
      </div>
      <div className="premium-grid two">
        <ListBlock title="Reflection Center" subtitle={`${data.reflection_cycles?.summary?.total || 0} ciclos`} items={data.reflection_cycles?.reflections || []} render={(r)=><div key={r.cycle}><b>{r.cycle}</b><small>{r.evidence_level}</small><p>{r.learning}</p></div>} />
        <ListBlock title="Experimentation Center" subtitle={data.experimentation?.guardrail} items={data.experimentation?.experiments || []} render={(e)=><div key={e.id}><b>{e.id}</b><small>{e.status} • risk {e.risk}</small><p>{e.hypothesis}</p></div>} />
      </div>
      <div className="premium-grid two-one">
        <section className="premium-panel"><div className="panel-title"><h2>Cognitive Digital Twin</h2><span>{twin.forecast}</span></div><div className="simulation-grid"><Gauge label="Health" value={twin.cognitive_health_score}/></div><ListBlock title="Limitações detectadas" subtitle="self-model" items={twin.limitations || []} render={(x,i)=><div key={i}><b>limitação {i+1}</b><small>{x}</small></div>} /></section>
        <section className="premium-panel"><div className="panel-title"><h2>Executive Copilot</h2><span>governance-aware reasoning</span></div><div className="autonomous-ask"><input value={question} onChange={e=>setQuestion(e.target.value)} /><button onClick={ask} disabled={asking}>{asking?'Analisando...':'Perguntar'}</button></div>{answer && <div className="ai-answer"><b>{answer.mode || 'resposta'}</b><p>{answer.answer}</p></div>}</section>
      </div>
    </>}
  </div>;
}
