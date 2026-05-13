import { useEffect, useState } from 'react';
import { api } from '../api/client';

/* ── helpers ── */
const fmtDate = iso => iso ? new Date(iso).toLocaleString('pt-BR') : '—';
const fmtAge  = iso => {
  if (!iso) return null;
  const s = (Date.now() - new Date(iso)) / 1000;
  if (s < 60) return `${Math.round(s)}s atrás`;
  if (s < 3600) return `${Math.round(s/60)}min atrás`;
  return `${Math.round(s/3600)}h atrás`;
};

function StatusBadge({ status }) {
  const map = {
    READY:'badge-green', SUCCESS:'badge-green', ALREADY_LOADED:'badge-green',
    ENGINE_READY:'badge-green', STARTED:'badge-green',
    INCREMENTAL:'badge-blue', SKIPPED_RECENT:'badge-blue',
    CSV_NOT_FOUND:'badge-orange', ENGINE_NOT_FOUND:'badge-red',
    FAILED:'badge-red', ERROR:'badge-red', NOT_FOUND:'badge-red',
    SKIPPED:'badge-muted', '—':'badge-muted',
  };
  return <span className={`badge ${map[status] || 'badge-muted'}`}>{status || '—'}</span>;
}

function EngineCard({ engine, bridge, onRun, running }) {
  const engineOk  = engine?.engine_found;
  const csvOk     = engine?.csv_found;
  const bridgeOk  = bridge?.ready;
  const lastRun   = engine?.last_run;
  const age       = fmtAge(lastRun?.finished_at);

  return (
    <div className="card mb20">
      <div className="card-header">
        <div className="flex-gap">
          <span style={{ fontSize:22 }}>⚡</span>
          <div>
            <div className="card-title">FlashScore Data Engine</div>
            <div style={{ fontSize:11, color:'var(--muted)', marginTop:1 }}>
              Fonte primária · escanteios · chutes · XG · odds reais
            </div>
          </div>
        </div>
        <div className="flex-gap">
          {age && <span style={{ fontSize:11, color:'var(--muted)' }}>{age}</span>}
          <StatusBadge status={
            bridgeOk ? 'READY' : csvOk ? 'CSV_FOUND' :
            engineOk ? 'CSV_NOT_FOUND' : 'ENGINE_NOT_FOUND'
          } />
        </div>
      </div>

      {/* Steps */}
      <div style={{ display:'flex', gap:0, marginBottom:16 }}>
        {[
          { label:'Engine instalado', ok: engineOk },
          { label:'CSV gerado',       ok: csvOk },
          { label:'Dados carregados', ok: bridgeOk },
        ].map(({ label, ok }, i) => (
          <div key={label} style={{ display:'flex', alignItems:'center', flex:1 }}>
            <div style={{
              flex:1, display:'flex', flexDirection:'column', alignItems:'center',
              gap:4, padding:'8px 4px',
              background: ok ? 'var(--green-dim)' : 'var(--surface)',
              border:`1px solid ${ok ? 'rgba(34,197,94,.25)' : 'var(--border)'}`,
              borderRadius: i === 0 ? '8px 0 0 8px' : i === 2 ? '0 8px 8px 0' : '0',
              borderRight: i < 2 ? 'none' : undefined,
            }}>
              <span style={{ fontSize:16 }}>{ok ? '✅' : '⬜'}</span>
              <span style={{ fontSize:10, color: ok ? 'var(--green)' : 'var(--muted)',
                fontWeight:600, textAlign:'center' }}>{label}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Stats */}
      {bridgeOk && (
        <div style={{ display:'flex', gap:16, marginBottom:14, flexWrap:'wrap' }}>
          {[
            ['Jogos carregados', (bridge?.parquet_rows || 0).toLocaleString()],
            ['Arquivo', `${bridge?.parquet_size_kb || 0} KB`],
            ['CSV', bridge?.flashscore_csv_path?.split('/').pop() || '—'],
          ].map(([k,v]) => (
            <div key={k}>
              <div style={{ fontSize:10, color:'var(--muted)', fontWeight:700,
                textTransform:'uppercase' }}>{k}</div>
              <div style={{ fontSize:14, fontWeight:700, color:'var(--text)' }}>{v}</div>
            </div>
          ))}
        </div>
      )}

      {/* Last run info */}
      {lastRun?.status === 'SUCCESS' && (
        <div className="alert alert-ok" style={{ marginBottom:12 }}>
          ✓ Último run: {fmtDate(lastRun.finished_at)} · {lastRun.rows_loaded?.toLocaleString()} jogos
          · {lastRun.duration_s}s
        </div>
      )}
      {lastRun?.status === 'FAILED' && (
        <div className="alert alert-error" style={{ marginBottom:12 }}>
          ✗ Último run falhou. Verifique logs/data_engine.log
        </div>
      )}

      {/* Actions */}
      <div className="flex-gap" style={{ flexWrap:'wrap' }}>
        <button className="btn btn-primary btn-sm" onClick={() => onRun('incremental', 7)}
          disabled={running || !engineOk}>
          {running ? <><span className="loading-bar" style={{width:12,height:12}}/> Executando...</>
           : '▶ Atualizar (7 dias)'}
        </button>
        <button className="btn btn-secondary btn-sm" onClick={() => onRun('incremental', 30)}
          disabled={running || !engineOk}>
          📅 Últimos 30 dias
        </button>
        <button className="btn btn-secondary btn-sm" onClick={() => onRun('full', 365)}
          disabled={running || !engineOk}>
          📦 Histórico completo
        </button>
        {!engineOk && (
          <a href="#"
            target="_blank" rel="noreferrer" className="btn btn-ghost btn-sm">
            🔗 Clone o repositório
          </a>
        )}
      </div>

      {/* Setup guide se engine não encontrado */}
      {!engineOk && (
        <div style={{ marginTop:14, padding:'14px 16px', background:'var(--surface)',
          borderRadius:'var(--radius-sm)', border:'1px solid var(--border)' }}>
          <div style={{ fontSize:11, fontWeight:700, color:'var(--muted)',
            textTransform:'uppercase', marginBottom:10 }}>Como instalar</div>
          {[
            ['1', 'Clone o repositório',
             'git clone # ../Internal FlashScore Provider'],
            ['2', 'Instale as dependências',
             'python -m playwright install chromium  # opcional para scraping real'],
            ['3', 'Clique em "Atualizar (7 dias)" acima', null],
          ].map(([n, label, cmd]) => (
            <div key={n} style={{ display:'flex', gap:10, marginBottom:8,
              alignItems:'flex-start' }}>
              <span style={{ width:20, height:20, background:'var(--accent)', color:'#fff',
                borderRadius:'50%', display:'flex', alignItems:'center',
                justifyContent:'center', fontSize:10, fontWeight:800, flexShrink:0 }}>
                {n}
              </span>
              <div>
                <div style={{ fontSize:12, fontWeight:600, color:'var(--text)' }}>{label}</div>
                {cmd && <code style={{ fontSize:10.5, color:'var(--muted)',
                  background:'var(--card)', padding:'3px 8px',
                  borderRadius:4, display:'block', marginTop:3 }}>{cmd}</code>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function PipelineStageCard({ icon, title, status, rows, detail, sub }) {
  const ok   = ['OK','READY','SUCCESS','ALREADY_LOADED'].includes(status);
  const warn = ['SKIPPED','CSV_NOT_FOUND','SKIPPED_RECENT'].includes(status);
  return (
    <div className="card" style={{
      borderColor: ok ? 'rgba(34,197,94,.2)' : warn ? 'rgba(245,158,11,.2)' : 'var(--border)'
    }}>
      <div className="flex-between mb8">
        <div className="flex-gap">
          <span style={{ fontSize:18 }}>{icon}</span>
          <span style={{ fontWeight:600, fontSize:13 }}>{title}</span>
        </div>
        <StatusBadge status={status} />
      </div>
      {rows != null && (
        <div style={{ fontSize:22, fontWeight:800, color:'var(--accent)',
          letterSpacing:'-0.02em', marginBottom:4 }}>
          {typeof rows === 'number' ? rows.toLocaleString() : rows}
        </div>
      )}
      {detail && <div style={{ fontSize:11.5, color:'var(--muted)' }}>{detail}</div>}
      {sub   && <div style={{ fontSize:11, color:'var(--muted)', marginTop:3 }}>{sub}</div>}
    </div>
  );
}

const RICH_COLS = [
  ['⚽','Gols FT/HT'],['🚩','Escanteios'],['🥅','Chutes a gol'],
  ['📊','Odds 1X2'],['📉','Over/Under'],['🎯','BTTS'],
  ['🔲','Double Chance'],['🚩','Odds Corners 7.5–11.5'],['📈','XG estimado'],
];

export default function DataOperations() {
  const [engineData, setEngineData] = useState(null);
  const [bridgeData, setBridgeData] = useState(null);
  const [opsData,    setOpsData]    = useState(null);
  const [dataEngineOps, setDataEngineOps] = useState(null);
  const [mappingOps, setMappingOps] = useState(null);
  const [dedupOps, setDedupOps] = useState(null);
  const [qualityOps, setQualityOps] = useState(null);
  const [loading,    setLoading]    = useState(true);
  const [running,    setRunning]    = useState(false);
  const [runMsg,     setRunMsg]     = useState('');
  const [error,      setError]      = useState('');

  async function load() {
    setLoading(true); setError('');
    try {
      const [e, b, o, d, m, ded, q] = await Promise.allSettled([
        api.engineStatus(),
        api.bridgeStatus(),
        api.dataOpsStatus(),
        api.dataEngineStatus(),
        api.dataEngineMappingReport(),
        api.dataEngineDedupReport(),
        api.dataEngineQualityReport(),
      ]);
      if (e.status === 'fulfilled') setEngineData(e.value?.data || e.value);
      if (b.status === 'fulfilled') setBridgeData(b.value?.bridge_status || b.value);
      if (o.status === 'fulfilled') setOpsData(o.value?.data || o.value);
      if (d.status === 'fulfilled') setDataEngineOps(d.value?.data || d.value);
      if (m.status === 'fulfilled') setMappingOps(m.value?.data || m.value);
      if (ded.status === 'fulfilled') setDedupOps(ded.value?.data || ded.value);
      if (q.status === 'fulfilled') setQualityOps(q.value?.data || q.value);
    } catch(e) { setError(e.message); }
    finally { setLoading(false); }
  }

  async function runEngine(mode, days) {
    setRunning(true); setRunMsg(''); setError('');
    try {
      const r = await api.engineRun(mode, days);
      setRunMsg(r?.message || 'Engine iniciado. Aguarde...');
      // Poll a cada 5s por até 2min
      let polls = 0;
      const poll = setInterval(async () => {
        polls++;
        await load();
        if (polls >= 24) clearInterval(poll);
      }, 5000);
    } catch(e) { setError(e.message); }
    finally { setRunning(false); }
  }

  useEffect(() => { load(); }, []);

  const engineStatus = opsData?.state?.engine_status || '—';
  const futureRows   = opsData?.state?.future_games_rows || 0;
  const totalRows    = bridgeData?.parquet_rows || 0;
  const oddsStatus   = opsData?.odds_fetcher?.status || '—';

  return (
    <div>
      {/* Header actions */}
      <div className="flex-between mb20">
        <div style={{ fontSize:12, color:'var(--muted)' }}>
          Pipeline de dados · FlashScore engine · odds em tempo real
        </div>
        <div className="flex-gap">
          <button className="btn btn-secondary btn-sm" onClick={load} disabled={loading}>
            {loading ? <span className="loading-bar" style={{width:12,height:12}}/> : '↻'} Refresh
          </button>
          <button className="btn btn-primary btn-sm"
            onClick={() => runEngine('incremental', 7)} disabled={running}>
            ▶ Pipeline Completo
          </button>
        </div>
      </div>

      {error   && <div className="alert alert-error">⚠ {error}</div>}
      {dataEngineOps && (
        <div className="alert alert-info" style={{ marginBottom: 16 }}>
          <strong>Data Engine Ops:</strong> {dataEngineOps.status} · outputs prontos: {(dataEngineOps.outputs_ready || []).join(', ') || 'nenhum'} · próximo passo: {(dataEngineOps.next_steps || [])[0]}
        </div>
      )}

      {runMsg  && <div className="alert alert-info">ℹ {runMsg}</div>}

      <div className="grid grid-3 mb20">
        <PipelineStageCard icon="🧭" title="Entity Mapping" status={mappingOps?.review_required ? 'REVIEW' : 'READY'} rows={mappingOps?.total_mappings || 0} detail={`${mappingOps?.review_required || 0} pendentes de revisão`} sub="RapidFuzz + registry canônico" />
        <PipelineStageCard icon="🧬" title="Deduplicação" status="READY" rows={dedupOps?.duplicates_removed || 0} detail="duplicatas removidas" sub={`${dedupOps?.canonical_matches || 0} partidas canônicas`} />
        <PipelineStageCard icon="✅" title="Data Quality" status={(qualityOps?.blocked_records || 0) ? 'REVIEW' : 'READY'} rows={qualityOps?.total_records || 0} detail={`${qualityOps?.blocked_records || 0} bloqueados`} sub="ML usa apenas registros elegíveis" />
      </div>

      {/* KPIs */}
      <div className="kpi-grid mb20">
        <div className="kpi-card">
          <span className="kpi-icon">📦</span>
          <div className="kpi-label">Jogos na base</div>
          <div className="kpi-value text-accent">{totalRows.toLocaleString()}</div>
          <div className="kpi-sub">parquet processado</div>
        </div>
        <div className="kpi-card">
          <span className="kpi-icon">⚙</span>
          <div className="kpi-label">Engine Status</div>
          <div className="kpi-value" style={{ fontSize:15, paddingTop:6 }}>{engineStatus}</div>
        </div>
        <div className="kpi-card">
          <span className="kpi-icon">📅</span>
          <div className="kpi-label">Jogos Futuros</div>
          <div className="kpi-value text-blue">{futureRows.toLocaleString()}</div>
          <div className="kpi-sub">para simulação</div>
        </div>
        <div className="kpi-card">
          <span className="kpi-icon">📊</span>
          <div className="kpi-label">Odds API</div>
          <div className="kpi-value" style={{ fontSize:15, paddingTop:6 }}>{oddsStatus}</div>
        </div>
      </div>

      {/* Engine card principal */}
      <EngineCard
        engine={engineData}
        bridge={bridgeData}
        onRun={runEngine}
        running={running}
      />

      {/* Outras fontes */}
      <div className="section-header">Outros módulos de dados</div>
      <div className="grid-2 mb20">
        <PipelineStageCard icon="📊" title="The Odds API"
          status={oddsStatus} rows={opsData?.odds_fetcher?.rows}
          detail="Odds em tempo real — line shopping automático"
          sub="Fallback quando engine não tem odds de fechamento" />
        <PipelineStageCard icon="🌐" title="Football-Data.org API"
          status={bridgeData?.ready ? 'READY' : 'FALLBACK'}
          detail="Dados históricos via API gratuita"
          sub="Usado como fallback quando CSV do engine não existe" />
        <PipelineStageCard icon="📡" title="Odds Monitor"
          status={opsData?.odds_monitor?.status || '—'}
          detail="Detecção de sharp money e steam moves"
          sub="Atualiza a cada 30 minutos via scheduler" />
        <PipelineStageCard icon="🔄" title="Result Settler"
          status={opsData?.result_settler?.status || '—'}
          rows={opsData?.result_settler?.settled_now}
          detail="Liquidação automática de apostas pendentes"
          sub="Busca resultados finais e atualiza paper trading" />
      </div>

      {/* Colunas ricas */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">📋 Dados exclusivos do FlashScore Engine</span>
          <span className="badge badge-accent">{RICH_COLS.length} tipos</span>
        </div>
        <p style={{ fontSize:12, color:'var(--muted)', marginBottom:12 }}>
          Estas colunas só existem quando o engine está instalado e o CSV foi gerado.
          Sem elas os mercados de <strong>escanteios</strong> e <strong>chutes</strong> não têm dados.
        </p>
        <div className="flex-wrap">
          {RICH_COLS.map(([icon, label]) => (
            <span key={label}
              className={`badge ${bridgeData?.ready ? 'badge-green' : 'badge-muted'}`}>
              {icon} {label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
