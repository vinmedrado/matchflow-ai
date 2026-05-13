import { useEffect, useRef, useState } from 'react';
import { api, getToken } from '../api/client.js';
import { DataStateBadge, PremiumHeader, PremiumState, SignalCard, Sparkline, StatTile, unwrap } from '../components/PremiumViz.jsx';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';
const WS_BASE = API_BASE.replace(/^http/, 'ws');

export default function LiveCenterPremium(){
  const [data,setData]=useState(null); const [brain,setBrain]=useState(null); const [loading,setLoading]=useState(true); const [error,setError]=useState(null); const [wsState,setWsState]=useState('disconnected');
  const wsRef = useRef(null);
  const load=()=>{setLoading(true);setError(null);Promise.all([api.premiumLiveCenter(), api.intelligenceBrain()]).then(([live,b])=>{setData(unwrap(live));setBrain(b)}).catch(setError).finally(()=>setLoading(false));};
  useEffect(load,[]);
  useEffect(()=>{
    const token = getToken();
    const ws = new WebSocket(`${WS_BASE}/api/intelligence/ws/intelligence${token ? `?token=${encodeURIComponent(token)}` : ''}`);
    wsRef.current = ws; setWsState('connecting');
    ws.onopen = () => setWsState('connected');
    ws.onclose = () => setWsState('disconnected');
    ws.onerror = () => setWsState('error');
    ws.onmessage = (event) => { try { const payload = JSON.parse(event.data); if (payload.type === 'ai_brain_snapshot') setBrain(payload.payload); } catch { /* ignore malformed frames */ } };
    return () => ws.close();
  },[]);
  const signals=data?.signals||[], alerts=brain?.alerts || data?.alerts||[];
  return <div className="premium-page">
    <PremiumHeader eyebrow="Live intelligence stream" title="Live Center" subtitle="Central operacional event-driven com WebSocket, AI Brain, alertas inteligentes e métricas reais de decision engine/paper trading." actions={<DataStateBadge state={wsState === 'connected' ? 'real_data' : wsState === 'connecting' ? 'partial_data' : 'unavailable_data'} />} />
    <PremiumState loading={loading} error={error} onRetry={load}/>
    {!loading && !error && <>
      <div className="premium-grid four"><StatTile label="Live signals" value={signals.length} sub="fila operacional" state={data?.source_meta?.decision_candidates?.state}/><StatTile label="AI alerts" value={alerts.length} sub="severity engine" tone="orange"/><StatTile label="Avg EV" value={brain?.summary?.avg_ev_pct != null ? `${brain.summary.avg_ev_pct}%` : null} sub="AI Brain" tone="green" state={brain?.data_state}/><StatTile label="WebSocket" value={wsState} sub="live intelligence" state={wsState === 'connected' ? 'real_data' : 'partial_data'}/></div>
      <div className="premium-grid two-one"><section className="premium-panel"><div className="panel-title"><h2>Bankroll momentum <DataStateBadge state={data?.equity_curve?.length ? 'real_data' : 'no_data'} /></h2><span>equity curve</span></div><Sparkline data={data?.equity_curve}/></section><section className="premium-panel"><div className="panel-title"><h2>AI alerts</h2><span>event feed</span></div><div className="timeline-list">{alerts.map((a,i)=><div key={a.id || i}><b>{a.title}</b><small>{a.reason || a.message}</small><DataStateBadge state={a.state}/></div>)}</div></section></div>
      <section className="premium-panel"><div className="panel-title"><h2>Live signal board</h2><span>{signals.length} candidatos</span></div><div className="signal-grid">{signals.length ? signals.slice(0,12).map(s=><SignalCard key={s.id} signal={s}/>) : <PremiumState empty message="Nenhum candidato real disponível."/>}</div></section>
    </>}
  </div>
}
