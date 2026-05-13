import { useEffect, useState } from 'react';
import { apiRequest } from '../api/client';
import MetricCard from '../components/MetricCard';
import Loading from '../components/Loading';
import ErrorState from '../components/ErrorState';
import EmptyState from '../components/EmptyState';
import StatusBadge from '../components/StatusBadge';

export default function MLLab() {
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiRequest('/api/ml/summary')
      .then((payload) => setSummary(payload.data || payload))
      .catch((err) => setError(err.message || 'Falha ao carregar resumo ML.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading message="Carregando ML Lab..." />;
  if (error) return <ErrorState title="ML Lab indisponível" message={error} />;

  const markets = summary?.markets || [];
  const metrics = summary?.metrics || {};

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>ML Lab</h1>
          <p className="subtitle">Camada de pesquisa: probabilidades, validação temporal e comparação futura. Não gera sinais operacionais.</p>
        </div>
        <StatusBadge status={summary?.dataset_available ? 'online' : 'offline'} label={summary?.research_only ? 'Research only' : 'Indisponível'} />
      </div>

      <div className="metrics-grid">
        <MetricCard label="Linhas Dataset ML" value={summary?.dataset_rows ?? 0} />
        <MetricCard label="Mercados Treinados" value={markets.length} />
        <MetricCard label="Modelos Registrados" value={summary?.trained_models_count ?? 0} />
        <MetricCard label="Predições" value={summary?.predictions_count ?? 0} />
      </div>

      <div className="table-card">
        <h2>Métricas por Mercado</h2>
        {markets.length === 0 ? (
          <EmptyState title="Nenhum modelo treinado" message="Execute python run_ml_pipeline.py para criar dataset, treinar modelos e gerar probabilidades." />
        ) : (
          <table>
            <thead>
              <tr><th>Mercado</th><th>Modelo</th><th>ROC-AUC</th><th>Accuracy</th><th>Precision</th><th>Recall</th><th>Log Loss</th></tr>
            </thead>
            <tbody>
              {markets.flatMap((market) => {
                const marketMetrics = metrics[market] || {};
                return Object.entries(marketMetrics).map(([modelName, item]) => (
                  <tr key={`${market}-${modelName}`}>
                    <td>{market}</td>
                    <td>{modelName}</td>
                    <td>{item.roc_auc === null || item.roc_auc === undefined ? 'N/A' : Number(item.roc_auc).toFixed(3)}</td>
                    <td>{Number(item.accuracy || 0).toFixed(3)}</td>
                    <td>{Number(item.precision || 0).toFixed(3)}</td>
                    <td>{Number(item.recall || 0).toFixed(3)}</td>
                    <td>{item.log_loss === null || item.log_loss === undefined ? 'N/A' : Number(item.log_loss).toFixed(3)}</td>
                  </tr>
                ));
              })}
            </tbody>
          </table>
        )}
      </div>

      <div className="table-card">
        <h2>Política de Uso</h2>
        <p className="subtitle">Este módulo gera probabilidades para pesquisa offline. Ele não altera estratégias, não executa paper trading, não calcula stake e não produz recomendação operacional.</p>
      </div>
    </div>
  );
}
