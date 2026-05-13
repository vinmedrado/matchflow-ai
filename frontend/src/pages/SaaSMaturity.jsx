import { useEffect, useState } from 'react';
import { api } from '../api/client.js';

export default function SaaSMaturity() {
  const [data, setData] = useState(null);
  useEffect(() => { api.platformSaasMaturity().then(r => setData(r.data)).catch(() => setData(null)); }, []);
  return <div className="page erp-page">
    <section className="erp-hero maturity-hero">
      <div>
        <span className="brand-pill">SaaS Maturity</span>
        <h1>Maturidade do produto</h1>
        <p>{data?.verdict || 'Diagnóstico de quanto o MatchFlow está pronto para portfólio, demo e venda.'}</p>
      </div>
      <div className="hero-score-card clean"><span>Score geral</span><strong>{data?.overall_score ?? 0}%</strong><small>próximo teto técnico</small></div>
    </section>
    <section className="section-block maturity-grid">
      {(data?.dimensions || []).map(dim => <div className="maturity-card" key={dim.area}>
        <div className="maturity-head"><h3>{dim.area}</h3><strong>{dim.score}%</strong></div>
        <span className="maturity-status">{dim.status}</span>
        <div className="maturity-columns"><div><b>Feito</b>{dim.done.map(x => <small key={x}>✓ {x}</small>)}</div><div><b>Falta</b>{dim.missing.map(x => <small key={x}>→ {x}</small>)}</div></div>
      </div>)}
    </section>
    <section className="section-block"><div className="insight-box"><h3>Próxima barreira</h3><p>{data?.ceiling_next}</p></div></section>
  </div>;
}
