import { useEffect, useState } from 'react';
import { api } from '../api/client.js';
import { DataStateBadge, PremiumHeader, PremiumState, StatTile } from '../components/PremiumViz.jsx';

function Pill({ children }) { return <span className="decision-tags"><span>{children}</span></span>; }
function List({ items = [], render }) { return <div className="planning-list">{items.length ? items.map(render) : <PremiumState empty message="Sem itens cognitivos nesta rodada." />}</div>; }
function Gauge({ label, value }) { const pct = Math.round((Number(value)||0)*100); return <div className="simulation-card"><b>{label}</b><strong>{pct}%</strong><div className="objective-progress"><i style={{width:`${pct}%`}} /></div></div>; }

function WorldModel({ world }) {
  const hypotheses = world?.world_hypotheses || [];
  return <section className="premium-panel os-decision">
    <div className="panel-title"><h2>World Model <DataStateBadge state={world?.data_state}/></h2><span>{world?.trace}</span></div>
    <div className="os-decision-main"><strong>{world?.regime || 'n/d'}</strong><span>{world?.state_quality}</span></div>
    <div className="decision-tags"><span>postura: {world?.regime_map?.recommended_posture}</span><span>risk/reward: {world?.regime_map?.risk_reward_balance}</span><span>volatilidade: {world?.systemic_state?.volatility_index}</span></div>
    <div className="workflow-grid">{hypotheses.map(h => <article className="workflow-card" key={h.id}><b>{h.id}</b><small>confidence {h.confidence}</small><p>{h.claim}</p></article>)}</div>
  </section>;
}

function Debate({ debate }) {
  return <section className="premium-panel"><div className="panel-title"><h2>Collaborative Agent Society</h2><span>{debate?.consensus}</span></div>
    <div className="premium-grid two">
      <div><h3>Argumentos a favor</h3><List items={debate?.supporting_arguments || []} render={(a,i)=><div key={i}><b>{a.agent}</b><small>{a.argument}</small></div>} /></div>
      <div><h3>Contrapontos</h3><List items={debate?.counter_arguments || []} render={(a,i)=><div key={i}><b>{a.agent}</b><small>{a.argument}</small></div>} /></div>
    </div>
  </section>;
}

function Knowledge({ knowledge }) {
  return <section className="premium-panel"><div className="panel-title"><h2>Knowledge Evolution</h2><span>{knowledge?.strategic_memory_state}</span></div>
    <div className="workflow-grid">{(knowledge?.patterns || []).map(p => <article className="workflow-card" key={p.id}><b>{p.source}</b><small>confidence {p.confidence}</small><p>{p.claim}</p></article>)}</div>
  </section>;
}

export default function CognitiveWorkspace() {
  const [data,setData]=useState(null); const [loading,setLoading]=useState(true); const [error,setError]=useState(null);
  const [question,setQuestion]=useState('Qual é a decisão cognitiva agora?'); const [answer,setAnswer]=useState(null); const [asking,setAsking]=useState(false);
  const load=()=>{setLoading(true);setError(null);api.cognitiveWorkspace().then(setData).catch(setError).finally(()=>setLoading(false));};
  useEffect(load,[]);
  const ask=async()=>{setAsking(true);setAnswer(null);try{setAnswer(await api.cognitiveAsk(question));}catch(e){setAnswer({answer:e.message});}finally{setAsking(false);}};
  const d=data?.cognitive_decision || {}; const u=data?.uncertainty || {}; const m=data?.meta_reasoning || {}; const obs=data?.observability || {};
  return <div className="premium-page autonomous-page">
    <PremiumHeader eyebrow="Cognitive Autonomous AI Intelligence Operating System" title="MatchFlow Cognitive Workspace" subtitle="World model, meta-reasoning, incerteza probabilística, autocrítica, aprendizado e decisão cognitiva auditável." actions={<button className="premium-button" onClick={load}>Atualizar Cognição</button>} />
    <PremiumState loading={loading} error={error} onRetry={load}/>
    {!loading && !error && data && <>
      <div className="premium-grid four">
        <StatTile label="Regime" value={data.world_model?.regime || 'n/d'} sub={data.world_model?.state_quality} state={data.data_state}/>
        <StatTile label="Incerteza" value={`${Math.round((u.uncertainty_score||0)*100)}%`} sub={u.ambiguity_level} tone="orange" state={data.data_state}/>
        <StatTile label="Reasoning" value={`${Math.round((m.reasoning_quality_score||0)*100)}%`} sub={m.verdict} tone="blue" state={data.data_state}/>
        <StatTile label="Decisão" value={d.action || 'n/d'} sub={`conf ${d.confidence_score}`} tone="green" state={data.data_state}/>
      </div>
      <WorldModel world={data.world_model}/>
      <div className="premium-grid two">
        <section className="premium-panel"><div className="panel-title"><h2>Cognitive Decision Engine</h2><span>{d.auditability}</span></div><div className="os-decision-main"><strong>{d.action}</strong><span>confidence {d.confidence_score}</span></div><p>{d.reasoning}</p><div className="decision-tags"><span>uncertainty: {d.uncertainty_level}</span><span>consensus: {d.agent_consensus}</span><span>review: {d.requires_human_review?'sim':'não'}</span></div></section>
        <section className="premium-panel"><div className="panel-title"><h2>Uncertainty Engine</h2><span>{u.explanation}</span></div><div className="simulation-grid"><Gauge label="Robustez" value={u.robustness_score}/><Gauge label="Incerteza" value={u.uncertainty_score}/></div><List items={u.probabilistic_scenarios || []} render={(s)=><div key={s.name}><b>{s.name}</b><small>prob {s.probability} • estado {s.expected_state}</small></div>} /></section>
      </div>
      <div className="premium-grid two"><section className="premium-panel"><div className="panel-title"><h2>Meta-Reasoning & Self-Critique</h2><span>quality {m.reasoning_quality_score}</span></div><List items={[...(m.issues||[]),...(m.contradictions||[])]} render={(x,i)=><div key={i}><b>{x.type}</b><small>{x.message}</small></div>} /><h3>Autocrítica</h3><List items={data.self_critique?.critiques || []} render={(x,i)=><div key={i}><b>critique {i+1}</b><small>{x}</small></div>} /></section><Knowledge knowledge={data.knowledge_evolution}/></div>
      <Debate debate={data.collaborative_agent_society}/>
      <div className="premium-grid two-one"><section className="premium-panel"><div className="panel-title"><h2>Multi-Timeframe Intelligence</h2><span>ciclos e deterioração temporal</span></div><pre className="diagnostic-pre">{JSON.stringify(data.multi_timeframe_intelligence, null, 2)}</pre></section><section className="premium-panel"><div className="panel-title"><h2>Cognitive Copilot</h2><span>memory-aware reasoning</span></div><div className="autonomous-ask"><input value={question} onChange={e=>setQuestion(e.target.value)} /><button onClick={ask} disabled={asking}>{asking?'Analisando...':'Perguntar'}</button></div>{answer && <div className="ai-answer"><b>{answer.mode || 'resposta'}</b><p>{answer.answer}</p></div>}</section></div>
      <section className="premium-panel"><div className="panel-title"><h2>Enterprise Cognitive Observability</h2><span>world • reasoning • uncertainty • decision tracing</span></div><pre className="diagnostic-pre">{JSON.stringify(obs, null, 2)}</pre></section>
    </>}
  </div>;
}
