import { useEffect, useState } from 'react';
import { api } from '../api/client.js';

export default function BacktestIntelligence() {
  const [data, setData] = useState(null);
  useEffect(() => { api.platformBacktestIntelligence().then(r => setData(r.data)).catch(() => setData(null)); }, []);
  return <div className="page erp-page">
    <section className="erp-hero"><div><span className="brand-pill">Validation Layer</span><h1>Backtest Intelligence</h1><p>Backtest precisa responder se a estratégia funciona por liga, time e mercado — antes de alimentar Machine Learning ou banca.</p></div><div className="hero-score-card clean"><span>Amostra</span><strong>{data?.total_trades ?? 0}</strong><small>{data?.validation_level || 'inicial'}</small></div></section>
    <section className="section-block"><div className="section-title-row"><h2>Segmentos obrigatórios</h2><span>Liga + time + mercado</span></div><div className="segment-grid">
      {(data?.segments || []).map(seg => <div className="segment-card" key={seg.field}><h3>{seg.field}</h3>{seg.items.map(item => <div className="mini-row" key={item.name}><span>{item.name}</span><b>{item.trades}</b></div>)}</div>)}
    </div></section>
    <section className="section-block"><div className="section-title-row"><h2>Regras de qualidade</h2><span>Antes do ML</span></div><div className="rule-grid">
      {(data?.quality_rules || []).map((r, i) => <div className="rule-card" key={r}><span>{i+1}</span><p>{r}</p></div>)}
    </div></section>
  </div>;
}
