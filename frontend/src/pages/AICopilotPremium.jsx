import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client.js';
import { DataStateBadge, MiniBarChart, PremiumHeader, PremiumState, SignalCard, StatTile, unwrap } from '../components/PremiumViz.jsx';

const questions = [
  'Faça um resumo operacional agora', 'Quais riscos aumentaram?', 'Quais ligas estão problemáticas?',
  'Explique o drawdown da banca', 'Quais mercados parecem mais consistentes?'
];

export default function AICopilotPremium() {
  const [data, setData] = useState(null);
  const [brain, setBrain] = useState(null);
  const [memory, setMemory] = useState(null);
  const [active, setActive] = useState(questions[0]);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState(null);
  const [answer,setAnswer]=useState(null);
  const [asking,setAsking]=useState(false);
  const load = () => {
    setLoading(true); setError(null);
    Promise.all([api.premiumCopilot(), api.intelligenceBrain(), api.intelligenceMemory()])
      .then(([premium, brainPayload, memoryPayload])=>{ setData(unwrap(premium)); setBrain(brainPayload); setMemory(memoryPayload); })
      .catch(setError).finally(()=>setLoading(false));
  };
  useEffect(load,[]);
  const top = data?.top_signals || [];
  const insights = brain?.insights || data?.insights || [];
  const alerts = brain?.alerts || [];
  const askCopilot = async (q = active) => {
    setActive(q); setAsking(true); setAnswer(null);
    try { const r = await api.intelligenceAsk(q); setAnswer(r?.answer || r?.summary || JSON.stringify(r)); setBrain(r?.snapshot || brain); }
    catch(e){
      try { const r = await api.ask(`${q}\n\nContexto AI Brain:\n${insights.map(i=>i.message).join('\n')}`); setAnswer(r?.summary || r?.answer || r?.message || JSON.stringify(r)); }
      catch(err){ setAnswer(`Não foi possível consultar o Copilot agora: ${err.message}`); }
    }
    finally{ setAsking(false); }
  };
  const leagueRows = useMemo(()=> brain?.analytics?.league_performance || [], [brain]);
  return <div className="premium-page">
    <PremiumHeader eyebrow="AI Brain + operational memory" title="MatchFlow AI Copilot" subtitle="Copiloto operacional com memória JSONL, contexto multi-turn, alertas inteligentes e análise real de sinais, banca, mercados e ligas." />
    <PremiumState loading={loading} error={error} onRetry={load}/>
    {!loading && !error && <>
      <div className="premium-grid four">
        <StatTile label="AI Brain" value={brain?.brain_version || '—'} sub="engine operacional" state={brain?.data_state}/>
        <StatTile label="Memória" value={memory?.profile?.events ?? 0} sub={`perfil ${memory?.profile?.risk_profile || 'balanced'}`} state={memory?.profile?.state}/>
        <StatTile label="Alertas" value={alerts.length} sub="priorizados por severidade" tone="orange" state={brain?.data_state}/>
        <StatTile label="Sinais" value={brain?.summary?.signals ?? top.length} sub="decision engine" tone="green" state={data?.source_meta?.decision_candidates?.state}/>
      </div>
      <div className="premium-grid two-one">
        <section className="ai-chat-panel">
          <div className="chat-orb">AI</div>
          <h2>Copiloto AI-native <DataStateBadge state={brain?.data_state || 'no_data'} /></h2>
          <p className="muted-text">Responde usando AI Brain, memória operacional e contexto real. Ausência de dados aparece explicitamente.</p>
          <div className="prompt-cloud">{questions.map(q=><button className={active===q?'active':''} onClick={()=>askCopilot(q)} key={q}>{q}</button>)}</div>
          <div className="ai-answer"><span>Resposta operacional</span><p>{asking ? 'Raciocinando com AI Brain + memória operacional...' : (answer || insights.map(i=>i.message).join(' '))}</p></div>
          <div className="copilot-memory"><b>Memória longa</b><small>{memory?.profile?.available ? `Perguntas recentes: ${(memory.profile.recent_questions || []).slice(-2).join(' | ')}` : 'Memória ainda vazia. Ela começa a registrar perguntas e preferências conforme o Copilot é usado.'}</small></div>
        </section>
        <aside className="premium-stack">
          <section className="premium-panel compact"><div className="panel-title"><h2>Alertas inteligentes</h2><span>severity engine</span></div><div className="timeline-list">{alerts.slice(0,5).map((a,i)=><div key={a.id || i}><b>{a.title}</b><small>{a.reason} {a.recommendation}</small><DataStateBadge state={a.state}/></div>)}</div></section>
          <section className="premium-panel compact"><div className="panel-title"><h2>Ligas por EV</h2><span>AI analytics</span></div><MiniBarChart data={leagueRows} valueKey="avg_ev_pct" labelKey="name" compact /></section>
        </aside>
      </div>
      <section className="premium-panel"><div className="panel-title"><h2>Sinais explicáveis priorizados</h2><span>AI ranking</span></div><div className="signal-grid">{top.length ? top.map(s=><SignalCard key={s.id} signal={s}/>) : <PremiumState empty message="Nenhum sinal real retornado pelo decision engine."/>}</div></section>
    </>}
  </div>;
}
