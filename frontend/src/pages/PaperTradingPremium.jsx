import { useEffect, useState } from 'react';
import { api } from '../api/client.js';
import { DataStateBadge, PremiumHeader, PremiumState, Sparkline, StatTile, unwrap } from '../components/PremiumViz.jsx';

export default function PaperTradingPremium(){
  const [data,setData]=useState(null); const [loading,setLoading]=useState(true); const [error,setError]=useState(null);
  const load=()=>{setLoading(true);setError(null);api.premiumPaper().then(r=>setData(unwrap(r))).catch(setError).finally(()=>setLoading(false));};
  useEffect(load,[]);
  const risk=data?.risk||{}, st=data?.streaks, s=data?.summary||{};
  return <div className="premium-page">
    <PremiumHeader eyebrow="Risk simulator" title="Paper Trading Premium" subtitle="Simulador visual baseado em arquivos reais do paper trading. Equity, drawdown, streaks e exposição não recebem valores fake." />
    <PremiumState loading={loading} error={error} onRetry={load}/>
    {!loading && !error && <>
      <div className="premium-grid four"><StatTile label="Trades" value={s.total_trades ?? s.total_signals ?? null} sub="amostra" state={s.file_exists ? 'real_data' : 'no_data'}/><StatTile label="ROI" value={s.roi != null ? `${Number(s.roi).toFixed(1)}%` : null} sub="paper" tone="green"/><StatTile label="Max DD" value={risk.max_drawdown != null ? `${Number(risk.max_drawdown).toFixed(1)}%` : null} sub="drawdown" tone="orange" state={risk.data_state}/><StatTile label="Streak" value={st?.current ?? null} sub={st ? `best ${st.best_win} / worst ${st.worst_loss}` : 'sem histórico'} state={st ? 'real_data' : 'no_data'}/></div>
      <div className="premium-grid half"><section className="premium-panel"><div className="panel-title"><h2>Equity curve <DataStateBadge state={data?.equity_curve?.length ? 'real_data' : 'no_data'} /></h2><span>bankroll evolution</span></div><Sparkline data={data?.equity_curve}/></section><section className="premium-panel"><div className="panel-title"><h2>Drawdown <DataStateBadge state={data?.drawdown?.length ? 'real_data' : 'no_data'} /></h2><span>risk line</span></div><Sparkline data={data?.drawdown}/></section></div>
      <section className="premium-panel"><div className="panel-title"><h2>Timeline operacional</h2><span>daily replay</span></div><div className="timeline-list"><div><b>Validação de risco</b><small>Exposição {risk.exposure ?? 'indisponível'} e stake média {risk.avg_stake ?? 'indisponível'}.</small></div><div><b>Controle emocional</b><small>{st ? 'Streaks calculados com últimas entradas reais.' : 'Streak indisponível por falta de resultados liquidados.'}</small></div><div><b>Modo seguro</b><small>Sem execução automática; plataforma continua em ambiente paper.</small></div></div></section>
    </>}
  </div>
}
