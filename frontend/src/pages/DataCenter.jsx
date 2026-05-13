import { useEffect, useState } from 'react';
import { api } from '../api/client.js';

export default function DataCenter() {
  const [data, setData] = useState(null);
  const [running, setRunning] = useState(false);
  useEffect(() => { api.platformDataCenter().then(r => setData(r.data)).catch(() => setData(null)); }, []);
  async function runEngine(days = 7) {
    setRunning(true);
    try { await api.engineRun('incremental', days); } catch (_) {}
    finally { setRunning(false); }
  }
  return <div className="page erp-page">
    <section className="erp-hero data-hero">
      <div><span className="brand-pill">Data Engine Online</span><h1>Central de Dados</h1><p>O usuário não precisa saber onde fica a pasta do Data Engine. Aqui o MatchFlow mostra origem, status, arquivos, fluxo e execução operacional.</p></div>
      <div className="ops-position-card"><span>Status do Engine</span><strong>{data?.engine?.status || 'verificando'}</strong><small>{data?.engine?.selected_path || 'Nenhum engine detectado ainda'}</small></div>
    </section>
    <section className="quick-actions-panel">
      <button className="btn btn-primary" disabled={running} onClick={() => runEngine(7)}>{running ? 'Executando...' : 'Atualizar últimos 7 dias'}</button>
      <button className="btn btn-secondary" disabled={running} onClick={() => runEngine(30)}>Atualizar últimos 30 dias</button>
      <button className="btn btn-secondary" onClick={() => location.reload()}>Recarregar status</button>
    </section>
    <section className="section-block"><div className="section-title-row"><h2>Fluxo dos dados</h2><span>Dado bruto até base analítica</span></div><div className="pipeline-flow">
      {(data?.flow || []).map((s, i) => <div className="flow-node" key={s.step}><span>{String(i+1).padStart(2,'0')}</span><b>{s.step}</b><small>{s.owner}</small><p>{s.output}</p></div>)}
    </div></section>
    <section className="section-block"><div className="section-title-row"><h2>Ativos de dados</h2><span>Arquivos que alimentam o produto</span></div><div className="asset-grid">
      {(data?.assets || []).map(a => <div className={`asset-card ${a.meta?.exists ? 'ok' : 'warn'}`} key={a.name}><b>{a.name}</b><span>{a.kind}</span><p>{a.meta?.exists ? a.meta.path : 'Ainda não gerado'}</p><small>{a.meta?.size_mb ? `${a.meta.size_mb} MB` : '—'}</small></div>)}
    </div></section>
  </div>;
}
