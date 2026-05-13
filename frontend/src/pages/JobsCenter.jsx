import { useEffect, useState } from 'react';
import { api } from '../api/client.js';

export default function JobsCenter() {
  const [data, setData] = useState(null);
  useEffect(() => { api.platformJobsCenter().then(r => setData(r.data)).catch(() => setData(null)); }, []);
  return <div className="page erp-page">
    <section className="erp-hero jobs-hero"><div><span className="brand-pill">Operations Center</span><h1>Jobs Center</h1><p>Scheduler, jobs, histórico, fila e execução precisam ficar visíveis para o produto parecer enterprise e não script local.</p></div><div className="hero-score-card clean"><span>Servidor</span><strong>Online</strong><small>{data?.server_time || '—'}</small></div></section>
    <section className="section-block"><div className="section-title-row"><h2>Jobs agendados</h2><span>Operação automática</span></div><div className="job-grid">{(data?.jobs || []).map(j => <div className="job-card" key={j.id}><b>{j.name}</b><span>{j.status}</span><p>{j.schedule}</p><small>{j.id}</small></div>)}</div></section>
    <section className="insight-box"><b>Próxima evolução</b><p>{data?.next_evolution}</p></section>
  </div>;
}
