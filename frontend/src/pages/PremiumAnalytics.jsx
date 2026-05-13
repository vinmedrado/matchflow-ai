import { useEffect, useState } from 'react';
import { api } from '../api/client.js';
import { DataStateBadge, MiniBarChart, PremiumHeader, PremiumState, StatTile, unwrap } from '../components/PremiumViz.jsx';

export default function PremiumAnalytics(){
  const [data,setData]=useState(null); const [brain,setBrain]=useState(null); const [loading,setLoading]=useState(true); const [error,setError]=useState(null);
  const load=()=>{setLoading(true);setError(null);Promise.all([api.premiumAnalytics(), api.intelligenceBrain(), api.intelligenceDiagnostics()]).then(([a,b,d])=>{setData(unwrap(a));setBrain(b);setData(prev=>({...prev, diagnostics:d}));}).catch(setError).finally(()=>setLoading(false));};
  useEffect(load,[]);
  const leaguePerf = data?.league_performance || brain?.analytics?.league_performance || [];
  const marketPerf = data?.market_performance || brain?.analytics?.market_performance || [];
  const alerts = data?.intelligent_alerts || brain?.alerts || [];
  return <div className="premium-page">
    <PremiumHeader eyebrow="AI analytics engine" title="Analytics Premium" subtitle="Analytics interpretáveis com drift simples, degradação, risco por liga/mercado, alertas inteligentes e diagnósticos operacionais." />
    <PremiumState loading={loading} error={error} onRetry={load}/>
    {!loading && !error && <>
      <div className="premium-grid four"><StatTile label="Ligas" value={leaguePerf.length || data?.league_roi?.length || 0} sub="com sinal" state={data?.source_meta?.decision_candidates?.state}/><StatTile label="Mercados" value={marketPerf.length || data?.market_roi?.length || 0} sub="consistência"/><StatTile label="Alertas AI" value={alerts.length} sub="risk/degradation" tone="orange" state={brain?.data_state}/><StatTile label="Model trend" value={data?.model_trends?.length ? `${data.model_trends.length} séries` : null} sub="registry real" tone="green" state={data?.source_meta?.model_trends?.state}/></div>
      {data?.message && <PremiumState empty message={data.message}/>} 
      <div className="premium-grid half"><section className="premium-panel"><div className="panel-title"><h2>Performance por liga <DataStateBadge state={leaguePerf.length ? 'real_data' : 'no_data'} /></h2><span>EV + consistência</span></div><MiniBarChart data={leaguePerf.length ? leaguePerf : data?.league_roi||[]} valueKey={leaguePerf.length ? 'avg_ev_pct' : 'roi'} /></section><section className="premium-panel"><div className="panel-title"><h2>Performance por mercado</h2><span>market intelligence</span></div><MiniBarChart data={marketPerf.length ? marketPerf : data?.market_roi||[]} valueKey={marketPerf.length ? 'avg_ev_pct' : 'roi'} /></section></div>
      <div className="premium-grid half"><section className="premium-panel"><div className="panel-title"><h2>Alertas e recomendações</h2><span>AI reasoning</span></div><div className="timeline-list">{alerts.length ? alerts.slice(0,8).map((a,i)=><div key={a.id || i}><b>{a.title}</b><small>{a.reason} {a.impact} {a.recommendation}</small><DataStateBadge state={a.state}/></div>) : <PremiumState empty message="Nenhum alerta inteligente gerado com os dados atuais."/>}</div></section><section className="premium-panel"><div className="panel-title"><h2>Model accuracy trend</h2><span>rolling real</span></div><MiniBarChart data={data?.model_trends||[]} labelKey="label" /></section></div>
    </>}
  </div>
}
