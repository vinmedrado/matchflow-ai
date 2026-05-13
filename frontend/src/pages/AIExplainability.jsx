import { useEffect, useState } from 'react';
import { api } from '../api/client.js';
import { DataStateBadge, MiniBarChart, PremiumHeader, PremiumState, Radar, SignalCard, unwrap } from '../components/PremiumViz.jsx';

export default function AIExplainability(){
  const [data,setData]=useState(null); const [loading,setLoading]=useState(true); const [error,setError]=useState(null);
  const load=()=>{setLoading(true);setError(null);api.premiumExplainability().then(r=>setData(unwrap(r))).catch(setError).finally(()=>setLoading(false));};
  useEffect(load,[]);
  return <div className="premium-page">
    <PremiumHeader eyebrow="Model transparency" title="Explicabilidade Visual" subtitle="Breakdown baseado em métricas reais disponíveis. Quando faltam SHAP, confidence, drift ou CLV, a interface mostra ausência em vez de inventar números." />
    <PremiumState loading={loading} error={error} onRetry={load}/>
    {!loading && !error && <>
      <div className="premium-grid two-one"><SignalCard signal={data?.selected_signal}/><section className="premium-panel"><div className="panel-title"><h2>Radar de decisão <DataStateBadge state={data?.radar?.length ? 'real_data' : 'no_data'} /></h2><span>AI profile</span></div><Radar data={data?.radar}/></section></div>
      <div className="premium-grid half"><section className="premium-panel"><div className="panel-title"><h2>Feature importance simplificado</h2><span>impacto real disponível</span></div><MiniBarChart data={data?.feature_importance||[]} labelKey="name" /></section><section className="premium-panel"><div className="panel-title"><h2>Confidence breakdown</h2><span>score decomposition</span></div><div className="breakdown-list">{(data?.confidence_breakdown||[]).length ? data.confidence_breakdown.map(f=><div key={f.name}><span>{f.name}</span><b>{Number(f.value).toFixed(1)}</b><em className={f.impact}>{f.impact}</em></div>) : <PremiumState empty message={data?.message}/>}</div></section></div>
    </>}
  </div>
}
