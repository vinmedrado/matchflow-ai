import { useEffect, useState } from 'react';
import { api } from '../api/client.js';

export default function UserWorkspace() {
  const [data, setData] = useState(null);
  useEffect(() => { api.platformUserWorkspace().then(r => setData(r.data)).catch(() => setData(null)); }, []);
  return <div className="page erp-page">
    <section className="erp-hero workspace-hero">
      <div><span className="brand-pill">Multiusuário</span><h1>Workspace & Cliente</h1><p>Hoje o MatchFlow roda como sistema autoral. Esta área mostra como ele vira ERP multiusuário: organização, perfil, preferências, banca e histórico por cliente.</p></div>
      <div className="hero-score-card clean"><span>Status</span><strong>Ready</strong><small>{data?.status || 'planejado'}</small></div>
    </section>
    <section className="section-block"><div className="section-title-row"><h2>Modelo alvo</h2><span>Base para SaaS vendável</span></div><div className="entity-grid">
      {(data?.target_model || []).map(entity => <div className="entity-card" key={entity.entity}><b>{entity.entity}</b><div>{entity.fields.map(f => <span key={f}>{f}</span>)}</div></div>)}
    </div></section>
    <section className="section-block split-2"><div className="panel-card"><h3>Perfis</h3><div className="tag-cloud">{(data?.roles || []).map(r => <span key={r}>{r}</span>)}</div></div><div className="panel-card"><h3>Valor comercial</h3><p className="muted-text">{data?.commercial_value}</p></div></section>
  </div>;
}
