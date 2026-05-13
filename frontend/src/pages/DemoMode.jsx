import { useEffect, useState } from 'react';
import { api } from '../api/client.js';

export default function DemoMode() {
  const [data, setData] = useState(null);
  const [offline, setOffline] = useState(false);
  useEffect(() => { api.platformDemoMode().then(r => setData(r.data)).catch(() => { setOffline(true); setData(null); }); }, []);
  return <div className="page erp-page">
    <section className="erp-hero demo-hero"><div><span className="brand-pill">Public Demo Ready</span><h1>Modo Demo</h1><p>Camada para apresentar o MatchFlow sem depender de API paga, mantendo segurança em paper trading e dados demonstrativos.</p></div><div className="hero-score-card clean"><span>Safe Mode</span><strong>{data?.safe_mode || '—'}</strong><small>{data?.demo_user || ''}</small></div></section>
    {offline && <div className="alert alert-error">API indisponível. Verifique VITE_API_BASE e se o backend está rodando em /health.</div>}
    <section className="section-block"><div className="section-title-row"><h2>Módulos da demo</h2><span>Para recrutadores/clientes</span></div><div className="tag-cloud">{(data?.demo_modules || []).map(x => <span key={x}>{x}</span>)}</div></section>
  </div>;
}
