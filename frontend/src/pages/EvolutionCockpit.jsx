import { useEffect, useState } from 'react';
import { api } from '../api/client.js';
import { DataStateBadge, PremiumHeader, PremiumState, StatTile } from '../components/PremiumViz.jsx';

function Gauge({ label, value, hint }) {
  const pct = Math.round((Number(value) || 0) * 100);
  return <div className="simulation-card"><b>{label}</b><strong>{pct}%</strong><div className="objective-progress"><i style={{width:`${pct}%`}} /></div>{hint && <small>{hint}</small>}</div>;
}
function Panel({ title, subtitle, children }) { return <section className="premium-panel"><div className="panel-title"><h2>{title}</h2><span>{subtitle}</span></div>{children}</section>; }
function Items({ items = [], render, empty='Sem eventos nesta rodada evolutiva.' }) { return <div className="planning-list">{items.length ? items.map(render) : <PremiumState empty message={empty}/>}</div>; }

export default function EvolutionCockpit() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [question, setQuestion] = useState('Como está a autopreservação e a evolução cognitiva?');
  const [answer, setAnswer] = useState(null);
  const [asking, setAsking] = useState(false);
  const load = () => { setLoading(true); setError(null); api.evolutionWorkspace().then(setData).catch(setError).finally(()=>setLoading(false)); };
  useEffect(load, []);
  const ask = async () => { setAsking(true); setAnswer(null); try { setAnswer(await api.evolutionAsk(question)); } catch(e) { setAnswer({answer:e.message}); } finally { setAsking(false); } };
  const obs = data?.evolution_observability || {};
  const summary = data?.evolution_summary || {};
  const rec = data?.recursive_improvement || {};
  const meta = data?.meta_learning || {};
  const society = data?.executive_agent_society || {};
  const economy = data?.cognitive_economy || {};
  const preservation = data?.self_preservation || {};
  const arch = data?.architectural_evolution || {};
  const memory = data?.executive_memory_consolidation || {};
  const continual = data?.continual_strategic_evolution || {};

  return <div className="premium-page autonomous-page">
    <PremiumHeader eyebrow="Self-Evolving Executive Cognitive Autonomous AI System" title="MatchFlow Evolution Cockpit" subtitle="Centro executivo de evolução recursiva, meta-learning, economia cognitiva, autopreservação, sociedade de agentes e evolução estratégica contínua." actions={<button className="premium-button" onClick={load}>Atualizar Evolution OS</button>} />
    <PremiumState loading={loading} error={error} onRetry={load}/>
    {!loading && !error && data && <>
      <div className="premium-grid four">
        <StatTile label="Cognitive Efficiency" value={`${Math.round((obs.cognitive_efficiency_score || 0) * 100)}%`} sub={economy?.complexity?.complexity_mode} state={data.data_state}/>
        <StatTile label="Learning Efficiency" value={`${Math.round((obs.learning_efficiency_score || 0) * 100)}%`} sub={meta.learning_strategy} tone="green" state={data.data_state}/>
        <StatTile label="Overload Risk" value={`${Math.round((obs.overload_risk_score || 0) * 100)}%`} sub={economy?.pressure?.pressure_state} tone="orange" state={data.data_state}/>
        <StatTile label="Self Preservation" value={`${Math.round((obs.self_preservation_score || 0) * 100)}%`} sub={preservation?.mode?.mode} tone="blue" state={data.data_state}/>
      </div>

      <Panel title="Evolution Executive Summary" subtitle={<DataStateBadge state={data.data_state}/> }>
        <div className="os-decision-main"><strong>{summary.headline}</strong><span>{summary.evolution_state}</span></div>
        <p>Modo: <b>{summary.self_preservation_mode}</b> • Consenso: <b>{summary.consensus}</b> • Próxima ação: <b>{summary.next_best_action}</b></p>
        <div className="decision-tags"><span>{data.system_version}</span><span>self-modifies-code: {String(data.performance_guards?.self_modifies_code)}</span><span>recursion-limit: {data.performance_guards?.recursion_limit}</span></div>
      </Panel>

      <div className="premium-grid two">
        <Panel title="Recursive Intelligence Center" subtitle={rec.status}>
          <div className="simulation-grid"><Gauge label="Recursive Improvement" value={obs.recursive_improvement_score}/><Gauge label="Reasoning Cost" value={obs.reasoning_cost_score}/></div>
          <Items items={rec.cognition?.improvement_plan || []} render={(x,i)=><div key={i}><b>{x.area}</b><small>{x.action}</small><p>{x.reason}</p></div>} />
        </Panel>
        <Panel title="Meta-Learning Center" subtitle={meta.intelligence_evolution?.evolution_state}>
          <div className="simulation-grid"><Gauge label="Learning" value={obs.learning_efficiency_score}/><Gauge label="Adaptation" value={obs.adaptation_quality_score}/></div>
          <Items items={meta.detected_learning_patterns || []} render={(x,i)=><div key={i}><b>padrão {i+1}</b><small>{x}</small></div>} />
        </Panel>
      </div>

      <div className="premium-grid two">
        <Panel title="Cognitive Economy Panel" subtitle={economy?.attention?.attention_policy}>
          <div className="simulation-grid"><Gauge label="Attention Risk" value={economy?.attention?.allocation?.risk}/><Gauge label="Pressure" value={economy?.pressure?.overload_risk_score}/></div>
          <pre className="diagnostic-pre">{JSON.stringify({budget:economy.budget, priority:economy.priority, complexity:economy.complexity}, null, 2)}</pre>
        </Panel>
        <Panel title="Self-Preservation Monitor" subtitle={preservation?.safety?.autonomous_safety_status}>
          <div className="simulation-grid"><Gauge label="Guard" value={preservation?.guard?.self_preservation_score}/><Gauge label="Overload" value={preservation?.overload?.risk_score}/></div>
          <Items items={preservation?.protector?.stability_actions || []} render={(x,i)=><div key={i}><b>proteção {i+1}</b><small>{x}</small></div>} />
        </Panel>
      </div>

      <Panel title="Executive Agent Society" subtitle={`${society.consensus} • conflict_count=${society.conflict_count}`}>
        <div className="workflow-grid">{(society.arguments || []).map(a => <article className="workflow-card" key={a.agent}><b>{a.agent}</b><small>{a.vote} • {a.priority}</small><p>{a.position}</p></article>)}</div>
      </Panel>

      <div className="premium-grid two">
        <Panel title="Architectural Evolution Insights" subtitle="sem autoalteração de código">
          <Items items={[...(arch.architecture_review?.gaps || []), ...(arch.workflow_reconfiguration?.proposals || [])]} render={(x,i)=><div key={i}><b>insight {i+1}</b><small>{x}</small></div>} />
          <pre className="diagnostic-pre">{JSON.stringify({routing:arch.routing_adaptation, orchestration:arch.orchestration_optimizer, modularity:arch.modularity}, null, 2)}</pre>
        </Panel>
        <Panel title="Long-Term Intelligence Dashboard" subtitle={continual?.strategic?.strategic_evolution_status}>
          <Items items={continual?.objectives?.long_term_objectives || []} render={(x,i)=><div key={i}><b>objetivo {i+1}</b><small>{x}</small></div>} />
          <div className="decision-tags"><span>{continual?.strategic?.macro_behavior}</span><span>{continual?.philosophy?.risk_philosophy}</span></div>
        </Panel>
      </div>

      <div className="premium-grid two-one">
        <Panel title="Executive Memory Consolidation" subtitle={memory?.abstraction?.long_term_memory_quality ? `${Math.round(memory.abstraction.long_term_memory_quality*100)}% quality` : 'memory'}>
          <Items items={memory?.abstraction?.operational_abstractions || []} render={(x,i)=><div key={i}><b>abstração {i+1}</b><small>{x}</small></div>} />
        </Panel>
        <Panel title="Evolution Copilot" subtitle="recursive reasoning aware">
          <div className="autonomous-ask"><input value={question} onChange={e=>setQuestion(e.target.value)} /><button onClick={ask} disabled={asking}>{asking?'Analisando...':'Perguntar'}</button></div>
          {answer && <div className="ai-answer"><b>{answer.mode || 'resposta'}</b><p>{answer.answer}</p></div>}
        </Panel>
      </div>

      <Panel title="Evolution Observability" subtitle="telemetry">
        <div className="simulation-grid"><Gauge label="Consensus" value={obs.executive_consensus_score}/><Gauge label="Strategic Stability" value={obs.strategic_stability_score}/><Gauge label="Adaptation Quality" value={obs.adaptation_quality_score}/></div>
        <pre className="diagnostic-pre">{JSON.stringify({observability: obs, performance_guards: data.performance_guards}, null, 2)}</pre>
      </Panel>
    </>}
  </div>;
}
