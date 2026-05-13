import { useEffect, useState } from 'react';
import { api } from '../api/client.js';

export default function MLIntelligence() {
  const [data, setData] = useState(null);
  useEffect(() => { api.platformMLIntelligence().then(r => setData(r.data)).catch(() => setData(null)); }, []);
  return <div className="page erp-page">
    <section className="erp-hero ml-hero"><div><span className="brand-pill">Model Governance</span><h1>ML Intelligence</h1><p>O ML entra depois da validação por backtest. A tela mostra gates, calibração, drift e política de uso dos modelos.</p></div><div className="hero-score-card clean"><span>Status</span><strong>{data?.status || '—'}</strong><small>{data?.model_policy || ''}</small></div></section>
    <section className="section-block"><div className="section-title-row"><h2>Gates de produção</h2><span>Checklist antes de confiar no modelo</span></div><div className="gate-grid">
      {(data?.gates || []).map(g => <div className={`gate-card ${g.passed ? 'ok' : 'warn'}`} key={g.name}><b>{g.name}</b><span>{g.passed ? 'Pronto' : 'Pendente'}</span></div>)}
    </div></section>
    <section className="section-block"><div className="section-title-row"><h2>Explicabilidade</h2><span>O que o usuário precisa entender</span></div><div className="tag-cloud">{(data?.explainability || []).map(x => <span key={x}>{x}</span>)}</div></section>
  </div>;
}
