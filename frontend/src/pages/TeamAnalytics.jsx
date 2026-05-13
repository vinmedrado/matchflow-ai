import { useEffect, useState } from 'react';
import MetricCard from '../components/MetricCard';
import Loading from '../components/Loading';
import ErrorState from '../components/ErrorState';
import StatusBadge from '../components/StatusBadge';
import { apiRequest } from '../api/client';

export default function TeamAnalytics() {
  const [teamSummary, setTeamSummary] = useState(null);
  const [advancedSummary, setAdvancedSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;

    async function loadSummaries() {
      try {
        setLoading(true);
        setError(null);

        const [teamResponse, advancedResponse] = await Promise.allSettled([
          apiRequest('/api/datasets/team-summary'),
          apiRequest('/api/datasets/advanced-summary'),
        ]);

        if (!mounted) return;

        if (teamResponse.status === 'fulfilled') {
          setTeamSummary(teamResponse.value?.data || teamResponse.value);
        } else {
          setTeamSummary(null);
        }

        if (advancedResponse.status === 'fulfilled') {
          setAdvancedSummary(advancedResponse.value?.data || advancedResponse.value);
        } else {
          setAdvancedSummary(null);
        }

        if (teamResponse.status === 'rejected' && advancedResponse.status === 'rejected') {
          throw new Error('Não foi possível carregar os datasets de Team Analytics.');
        }
      } catch (err) {
        if (!mounted) return;
        setError(err?.message || 'Não foi possível carregar Team Analytics.');
      } finally {
        if (mounted) setLoading(false);
      }
    }

    loadSummaries();
    return () => {
      mounted = false;
    };
  }, []);

  if (loading) return <Loading label="Carregando Team Analytics..." />;
  if (error) return <ErrorState title="Team Analytics indisponível" message={error} />;

  const teamDateRange = teamSummary?.date_range
    ? `${teamSummary.date_range.min || '-'} → ${teamSummary.date_range.max || '-'}`
    : '-';

  const advancedDateRange = advancedSummary?.date_range
    ? `${advancedSummary.date_range.min || '-'} → ${advancedSummary.date_range.max || '-'}`
    : '-';

  return (
    <div className="page team-analytics-page">
      <div className="page-header">
        <p className="eyebrow">PATCH 3.0</p>
        <h1>Team Analytics</h1>
        <p className="page-description">
          Dataset temporal por time com camada avançada de features multi-mercado, mantendo validação anti-leakage.
        </p>
      </div>

      <div className="panel">
        <div className="status-row">
          <h2>Dataset temporal por time</h2>
          <StatusBadge ok={!!teamSummary?.file_exists} label="Temporal" />
        </div>

        <div className="metrics">
          <MetricCard label="Linhas" value={teamSummary?.total_rows ?? 0} />
          <MetricCard label="Times" value={teamSummary?.total_teams ?? 0} />
          <MetricCard label="Ligas" value={teamSummary?.total_leagues ?? 0} />
          <MetricCard label="Features" value={teamSummary?.features_count ?? 0} />
          <MetricCard label="Datas" value={teamDateRange} />
        </div>

        {!teamSummary?.file_exists && (
          <div className="warning-panel">
            <h3>Dataset temporal ainda não encontrado</h3>
            <p>Execute o pipeline abaixo antes das features avançadas:</p>
            <pre>python run_team_dataset_pipeline.py</pre>
          </div>
        )}
      </div>

      <div className="panel">
        <div className="status-row">
          <h2>Dataset avançado multi-mercado</h2>
          <StatusBadge ok={!!advancedSummary?.file_exists} label="Avançado" />
        </div>

        <div className="metrics">
          <MetricCard label="Linhas avançadas" value={advancedSummary?.total_rows ?? 0} />
          <MetricCard label="Times" value={advancedSummary?.total_teams ?? 0} />
          <MetricCard label="Ligas" value={advancedSummary?.total_leagues ?? 0} />
          <MetricCard label="Features totais" value={advancedSummary?.features_count ?? 0} />
          <MetricCard label="Features avançadas" value={advancedSummary?.advanced_features_count ?? 0} />
          <MetricCard label="Datas" value={advancedDateRange} />
        </div>

        {!advancedSummary?.file_exists && (
          <div className="warning-panel">
            <h3>Dataset avançado ainda não encontrado</h3>
            <p>Execute o pipeline abaixo após gerar o dataset temporal:</p>
            <pre>python run_advanced_features_pipeline.py</pre>
          </div>
        )}
      </div>
    </div>
  );
}
