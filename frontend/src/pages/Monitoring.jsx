import { useEffect, useState } from 'react';
import { api } from '../api/client.js';
import Loading from '../components/Loading.jsx';
import ErrorState from '../components/ErrorState.jsx';
import MetricCard from '../components/MetricCard.jsx';
import StatusBadge from '../components/StatusBadge.jsx';

export default function Monitoring() {
  const [status, setStatus] = useState(null);
  const [alerts, setAlerts] = useState(null);
  const [drift, setDrift] = useState(null);
  const [anomalies, setAnomalies] = useState(null);
  const [coverage, setCoverage] = useState(null);
  const [calibration, setCalibration] = useState(null);
  const [modelHealth, setModelHealth] = useState(null);
  const [jobs, setJobs] = useState(null);
  const [evidenceAlerts, setEvidenceAlerts] = useState(null);
  const [settledSummary, setSettledSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      const [s, a, d, n, c, cal, mh, j, ev, ss] = await Promise.all([
        api.monitoringStatus(),
        api.monitoringAlerts(),
        api.monitoringDrift(),
        api.monitoringAnomalies(),
        api.flashscoreCoverage(),
        api.calibrationReport(),
        api.modelHealth(),
        api.jobs(),
        api.evidenceAlerts(),
        api.settledResultsSummary(),
      ]);
      setStatus(s.data || s);
      setAlerts(a.data || a);
      setDrift(d.data || d);
      setAnomalies(n.data || n);
      setCoverage(c.data || c);
      setCalibration(cal.data || cal);
      setModelHealth(mh.data || mh);
      setJobs(j.data || j);
      setEvidenceAlerts(ev.data || ev);
      setSettledSummary(ss.data || ss);
    } catch (err) {
      setError(err.message || 'Falha ao carregar monitoramento.');
    } finally {
      setLoading(false);
    }
  }

  async function runMonitoring() {
    setLoading(true);
    try {
      await api.monitoringRun();
      await load();
    } catch (err) {
      setError(err.message || 'Falha ao executar monitoramento.');
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  if (loading) return <Loading label="Carregando monitoramento..." />;
  if (error) return <ErrorState title="Monitoring offline" message={error} />;

  const alertItems = alerts?.alerts || [];

  return (
    <div className="page-grid">
      <section className="hero-card">
        <div>
          <p className="eyebrow">PAPER TRADING / SIMULATION ONLY</p>
          <h1>Monitoring</h1>
          <p>Monitora saúde do sistema, drift, alertas e anomalias sem executar nenhuma ação real.</p>
        </div>
        <button className="primary-button" onClick={runMonitoring}>Atualizar Monitoramento</button>
      </section>

      <section className="metrics-grid">
        <MetricCard title="Status Geral" value={status?.overall_status || 'UNKNOWN'} />
        <MetricCard title="Risco" value={status?.risk_level || 'UNKNOWN'} />
        <MetricCard title="Alertas" value={alerts?.total_alerts ?? 0} />
        <MetricCard title="Drift" value={drift?.drift_level || (drift?.drift_detected ? 'medium' : 'low')} />
        <MetricCard title="Odds Coverage" value={`${coverage?.odds_coverage_pct ?? 0}%`} />
        <MetricCard title="Stats Coverage" value={`${coverage?.stats_coverage_pct ?? 0}%`} />
        <MetricCard title="Calibration" value={calibration?.is_real_calibration ? 'real' : 'fallback'} />
        <MetricCard title="Real Results" value={settledSummary?.source_type_breakdown?.real ?? 0} />
      </section>

      <section className="panel-card">
        <h2>Alertas Ativos</h2>
        {alertItems.length === 0 ? <p>Nenhum alerta ativo.</p> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Severidade</th><th>Categoria</th><th>Código</th><th>Mensagem</th><th>Próximo passo</th></tr></thead>
              <tbody>{alertItems.map((item, idx) => (
                <tr key={`${item.code}-${idx}`}>
                  <td><StatusBadge status={item.severity} /></td>
                  <td>{item.category}</td>
                  <td>{item.code}</td>
                  <td>{item.message}</td>
                  <td>{item.next_step}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel-card">
        <h2>Saúde do Sistema</h2>
        <div className="metrics-grid compact">
          <MetricCard title="Engine" value={status?.data_ops?.engine_status || 'UNKNOWN'} />
          <MetricCard title="Jogos Futuros" value={status?.data_ops?.future_games_status || 'UNKNOWN'} />
          <MetricCard title="Paper ROI" value={String(status?.paper_trading?.roi ?? 0)} />
          <MetricCard title="Anomalias" value={anomalies?.anomalies_detected ? 'Detectadas' : 'Não detectadas'} />
        </div>
      </section>



      <section className="panel-card">
        <h2>Evidence Quality</h2>
        <div className="metrics-grid compact">
          <MetricCard title="Real Calibration" value={calibration?.is_real_calibration ? 'YES' : 'NO'} />
          <MetricCard title="Real Sample" value={calibration?.real_sample_size ?? 0} />
          <MetricCard title="Fallback Excluded" value={calibration?.fallback_sample_size ?? 0} />
          <MetricCard title="Evidence Alerts" value={evidenceAlerts?.total_alerts ?? 0} />
        </div>
        <p className="muted">Calibração real usa somente resultados liquidados reais. Paper, backtest e demo aparecem como fallback/evidência auxiliar e não são misturados silenciosamente.</p>
      </section>

      <section className="panel-card">
        <h2>Model Reliability</h2>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Modelo</th><th>Status</th><th>Reliability</th><th>Calibration</th><th>Drift Risk</th><th>Recent ROI</th></tr></thead>
            <tbody>{Object.entries(modelHealth?.models || {}).map(([name, item]) => (
              <tr key={name}>
                <td>{name}</td>
                <td><StatusBadge status={item.operational_status} /></td>
                <td>{item.reliability_score ?? '—'}</td>
                <td>{item.calibration_quality_score ?? '—'}</td>
                <td>{item.drift_risk_score ?? '—'}</td>
                <td>{item.recent_roi ?? '—'}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </section>

      <section className="panel-card">
        <h2>Production Monitoring</h2>
        <div className="metrics-grid compact">
          <MetricCard title="Drift Score" value={String(drift?.drift_score ?? 0)} />
          <MetricCard title="FlashScore Matches" value={coverage?.total_matches ?? 0} />
          <MetricCard title="Jobs Registrados" value={jobs?.jobs?.length ?? 0} />
          <MetricCard title="Provider Health" value={coverage?.provider_warnings?.length ? 'warnings' : 'ok'} />
          <MetricCard title="Model Health" value={modelHealth?.global_status || 'unknown'} />
        </div>
        <p className="muted">Cobertura, calibração e drift são calculados a partir dos artefatos reais do pipeline. Dados ausentes aparecem como 0/null com warning, sem inventar métricas.</p>
      </section>
    </div>
  );
}
