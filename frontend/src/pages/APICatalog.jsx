import { useEffect, useState } from 'react';
import { api } from '../api/client.js';

export default function APICatalog() {
  const [data, setData] = useState(null);
  useEffect(() => { api.platformApiCatalog().then(r => setData(r.data)).catch(() => setData(null)); }, []);
  return <div className="page erp-page">
    <section className="erp-hero api-hero">
      <div><span className="brand-pill">API Map</span><h1>Catálogo Operacional de APIs</h1><p>Tradução das rotas técnicas em responsabilidades de produto. O usuário entende o que cada bloco faz sem precisar abrir o Swagger.</p></div>
      <div className="ops-position-card"><span>Backend</span><strong>{data?.base_url || '8010'}</strong><small>Docs: {data?.docs || '/docs'}</small></div>
    </section>
    <section className="api-catalog-grid">
      {(data?.groups || []).map(group => <article className="api-group-card" key={group.group}>
        <div className="api-group-head"><h3>{group.group}</h3><span>{group.endpoints?.length || 0} rotas</span></div>
        <p>{group.purpose}</p>
        <div className="endpoint-list">{(group.endpoints || []).map(ep => <code key={ep}>{ep}</code>)}</div>
      </article>)}
    </section>
    <section className="insight-box"><b>Regra de produto</b><p>{data?.product_rule}</p></section>
  </div>;
}
