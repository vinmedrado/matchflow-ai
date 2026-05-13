import { useEffect, useState } from 'react';
import { api } from '../api/client.js';

export default function SalesReadiness() {
  const [data, setData] = useState(null);
  useEffect(() => { api.platformSalesReadiness().then(r => setData(r.data)).catch(() => setData(null)); }, []);
  return <div className="page erp-page">
    <section className="erp-hero sales-hero">
      <div><span className="brand-pill">SaaS Readiness</span><h1>Pronto para Portfólio e Venda</h1><p>{data?.positioning || 'Posicionamento comercial do MatchFlow.'}</p></div>
      <div className="sales-score-stack"><div><span>Portfolio</span><strong>{data?.portfolio_score ?? 0}</strong></div><div><span>Venda</span><strong>{data?.sale_score ?? 0}</strong></div></div>
    </section>
    <section className="section-block split-2">
      <div className="panel-card"><h3>Roteiro de demo</h3><ol className="demo-steps">{(data?.demo_script || []).map((s,i)=><li key={s}><span>{i+1}</span>{s}</li>)}</ol></div>
      <div className="panel-card"><h3>Falta para venda real</h3><ul className="missing-list">{(data?.missing_for_real_sale || []).map(item => <li key={item}>{item}</li>)}</ul></div>
    </section>
  </div>;
}
