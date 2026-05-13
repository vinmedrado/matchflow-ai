import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client.js';

const fallbackSteps = [
  ['data_engine', 'Data Engine', 'Coletar e normalizar jogos'],
  ['competitions', 'Campeonatos', 'Organizar ligas, times e próximos jogos'],
  ['backtest', 'Backtest', 'Validar estratégia por liga, time e mercado'],
  ['ml', 'Machine Learning', 'Treinar modelos depois do backtest'],
  ['decision_engine', 'Decision Engine', 'Gerar candidatos auditáveis'],
  ['bankroll', 'Banca', 'Definir stake e método de risco'],
];

function ReadinessDot({ ok }) {
  return <span className={`readiness-dot ${ok ? 'ok' : 'warn'}`}>{ok ? 'OK' : 'Pendente'}</span>;
}

function StepTimeline({ steps, active, onSelect }) {
  return (
    <div className="ops-timeline">
      {steps.map((step, index) => (
        <button
          key={step.id}
          type="button"
          className={`ops-step ${active?.id === step.id ? 'active' : ''}`}
          onClick={() => onSelect(step)}
        >
          <span className="ops-step-index">{String(index + 1).padStart(2, '0')}</span>
          <span className="ops-step-copy">
            <b>{step.name}</b>
            <small>{step.title}</small>
          </span>
        </button>
      ))}
    </div>
  );
}

function EndpointGroup({ group }) {
  return (
    <div className="endpoint-card">
      <div>
        <strong>{group.group}</strong>
        <p>{group.purpose}</p>
      </div>
      <div className="endpoint-list">
        {group.endpoints?.map((endpoint) => <code key={endpoint}>{endpoint}</code>)}
      </div>
    </div>
  );
}

function RoadmapCard({ item }) {
  return (
    <div className="roadmap-card">
      <span>{item.phase}</span>
      <strong>{item.title}</strong>
      <p>{item.goal}</p>
      <small>{item.done_when}</small>
    </div>
  );
}

function HealthPanel({ health }) {
  const items = [
    ['Script Data Engine', health?.data_engine_script],
    ['Scheduler', health?.scheduler_script],
    ['Dataset processado', health?.processed_dataset],
    ['Dataset por time', health?.team_dataset],
    ['Backtest', health?.backtest_results],
    ['Pasta ML', health?.ml_folder],
    ['Candidatos decisão', health?.decision_candidates],
  ];
  return (
    <div className="ops-health-grid">
      {items.map(([label, ok]) => (
        <div className="ops-health-item" key={label}>
          <span>{label}</span>
          <ReadinessDot ok={ok} />
        </div>
      ))}
    </div>
  );
}

export default function OperationalGuide() {
  const [blueprint, setBlueprint] = useState(null);
  const [activeStep, setActiveStep] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function load() {
    setLoading(true);
    setError('');
    try {
      const response = await api.operationalBlueprint();
      const data = response?.data || response;
      setBlueprint(data);
      setActiveStep(data?.pipeline_steps?.[0] || null);
    } catch (err) {
      setError(err.message || 'Falha ao carregar guia operacional.');
      const steps = fallbackSteps.map(([id, name, title]) => ({ id, name, title }));
      setBlueprint({ pipeline_steps: steps, api_groups: [], sellable_roadmap: [], health: {} });
      setActiveStep(steps[0]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const steps = useMemo(() => blueprint?.pipeline_steps || [], [blueprint]);
  const groups = blueprint?.api_groups || [];
  const roadmap = blueprint?.sellable_roadmap || [];

  return (
    <div className="page operational-guide-page">
      <section className="ops-hero">
        <div>
          <span className="brand-pill">Produto vendável · fluxo operacional</span>
          <h1>Guia Operacional MatchFlow</h1>
          <p>
            Aqui fica claro o que cada parte faz: Data Engine, APIs, campeonatos, backtest,
            Machine Learning, motor de decisão e banca. A meta é esconder a complexidade técnica
            e transformar tudo em operação por clique.
          </p>
          <div className="hero-actions">
            <button className="btn btn-primary" onClick={load}>{loading ? 'Atualizando...' : 'Atualizar diagnóstico'}</button>
            <a className="btn btn-secondary" href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">Abrir Swagger</a>
          </div>
          {error && <div className="alert alert-warn" style={{ marginTop: 14 }}>{error}</div>}
        </div>
        <div className="ops-position-card">
          <span>Estado atual</span>
          <strong>{blueprint?.current_state || 'local/autoral'}</strong>
          <small>{blueprint?.target_state || 'SaaS online com Data Engine interno'}</small>
        </div>
      </section>

      <section className="ops-board">
        <div className="section-title-row">
          <h2>Dado → Backtest → ML → Decisão → Banca</h2>
          <span>Fluxo que o usuário final precisa entender sem ler código</span>
        </div>
        <StepTimeline steps={steps} active={activeStep} onSelect={setActiveStep} />
        {activeStep && (
          <div className="ops-detail-card">
            <div>
              <span className="eyebrow">{activeStep.business_label || activeStep.name}</span>
              <h3>{activeStep.title}</h3>
              <p>{activeStep.description}</p>
            </div>
            <div className="ops-detail-grid">
              <div><span>Comando técnico</span><code>{activeStep.command || '—'}</code></div>
              <div><span>Endpoint principal</span><code>{activeStep.primary_endpoint || '—'}</code></div>
              <div><span>Status</span><code>{activeStep.status_endpoint || '—'}</code></div>
              <div><span>Saída esperada</span><code>{activeStep.output || '—'}</code></div>
              <div><span>Tela</span><b>{activeStep.ui_page || '—'}</b></div>
              <div><span>Meta vendável</span><b>{activeStep.sellable_goal || '—'}</b></div>
            </div>
          </div>
        )}
      </section>

      <section className="section-block">
        <div className="section-title-row"><h2>Status técnico do motor</h2><span>O que já existe dentro do projeto</span></div>
        <HealthPanel health={blueprint?.health || {}} />
      </section>

      <section className="section-block">
        <div className="section-title-row"><h2>Mapa de APIs</h2><span>Grupos de endpoints por responsabilidade</span></div>
        <div className="endpoint-grid">
          {groups.map((group) => <EndpointGroup key={group.group} group={group} />)}
        </div>
      </section>

      <section className="section-block">
        <div className="section-title-row"><h2>Rota para virar SaaS vendável</h2><span>Sem depender visualmente da pasta do Data Engine</span></div>
        <div className="roadmap-grid">
          {roadmap.map((item) => <RoadmapCard key={item.phase} item={item} />)}
        </div>
      </section>
    </div>
  );
}
