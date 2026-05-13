import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client.js';
import { useApp } from '../store/AppContext.jsx';

const PAGE_BY_STEP = {
  connect_engine: 'Data Center', sync_matches: 'Data Center', validate_segments: 'Backtest Intelligence',
  train_models: 'ML Intelligence', operate_bankroll: 'Strategy Studio', package_saas: 'SaaS Maturity',
};

const COPY = {
  pt: {
    pill: 'ERP Guiado',
    title: 'Onboarding operacional do MatchFlow',
    subtitle: 'Do primeiro dado até a banca inteligente, sem depender de terminal.',
    start: 'Começar operação',
    maturity: 'Ver maturidade SaaS',
    readiness: 'Prontidão',
    journey: 'jornada guiada',
    section: 'Jornada do usuário',
    action: 'Ação',
    metric: 'Métrica',
    principle: 'O usuário final entende decisões e resultados; a engenharia fica invisível por trás dos jobs.',
    statuses: { done: 'concluído', blocked: 'bloqueado', ready: 'pronto', needs_data: 'precisa de dados', gated: 'com gate', waiting_signals: 'aguardando sinais', in_progress: 'em andamento' },
    steps: {
      connect_engine: { title: 'Conectar motor de dados', business_goal: 'Transformar o provider interno FlashScore em uma operação interna do MatchFlow.', user_action: 'Abrir Central de Dados e validar se o engine foi detectado.', success_metric: 'Engine detectado e pelo menos uma base de jogos disponível.' },
      sync_matches: { title: 'Atualizar jogos e odds', business_goal: 'Garantir que o usuário não precise rodar scripts manualmente.', user_action: 'Clicar em Atualizar Dados ou usar job agendado.', success_metric: 'Jogos, ligas e times visíveis no produto.' },
      validate_segments: { title: 'Validar liga, time e mercado', business_goal: 'Evitar decisões com ROI bonito, mas sem amostra confiável.', user_action: 'Escolher campeonato e mercado para auditar.', success_metric: 'Segmentos aprovados para alimentar ML.' },
      train_models: { title: 'Treinar ML com gates', business_goal: 'Usar ML apenas onde o backtest provou estabilidade.', user_action: 'Rodar treino/avaliação no ML Intelligence.', success_metric: 'Modelo ativo com calibração e explicabilidade.' },
      operate_bankroll: { title: 'Operar banca inteligente', business_goal: 'Automatizar stake sem assumir aposta real automática.', user_action: 'Definir banca, perfil de risco e mercados permitidos.', success_metric: 'Sinais com stake recomendada e justificativa.' },
      package_saas: { title: 'Empacotar como SaaS vendável', business_goal: 'Cliente acessa online, sem pasta, terminal ou conhecimento técnico.', user_action: 'Preparar demo, usuários, planos e deploy separado.', success_metric: 'Demo pública com dados consistentes e fluxo por clique.' },
    },
  },
  en: {
    pill: 'Guided ERP',
    title: 'MatchFlow operational onboarding',
    subtitle: 'From the first data point to intelligent bankroll operation, without depending on the terminal.',
    start: 'Start operation',
    maturity: 'View SaaS maturity',
    readiness: 'Readiness',
    journey: 'guided journey',
    section: 'User journey',
    action: 'Action',
    metric: 'Metric',
    principle: 'The final user understands decisions and outcomes; engineering stays invisible behind the jobs.',
    statuses: { done: 'done', blocked: 'blocked', ready: 'ready', needs_data: 'needs data', gated: 'gated', waiting_signals: 'waiting signals', in_progress: 'in progress' },
    steps: {
      connect_engine: { title: 'Connect data engine', business_goal: 'Turn the internal FlashScore provider into a MatchFlow internal operation.', user_action: 'Open Data Center and confirm the engine was detected.', success_metric: 'Engine detected and at least one match dataset available.' },
      sync_matches: { title: 'Update matches and odds', business_goal: 'Make sure the user does not need to run scripts manually.', user_action: 'Click Update Data or use a scheduled job.', success_metric: 'Matches, leagues and teams visible in the product.' },
      validate_segments: { title: 'Validate league, team and market', business_goal: 'Avoid decisions with attractive ROI but unreliable sample size.', user_action: 'Choose a competition and market to audit.', success_metric: 'Approved segments ready to feed ML.' },
      train_models: { title: 'Train ML with gates', business_goal: 'Use ML only where the backtest proved stability.', user_action: 'Run training/evaluation in ML Intelligence.', success_metric: 'Active model with calibration and explainability.' },
      operate_bankroll: { title: 'Operate intelligent bankroll', business_goal: 'Automate stake sizing without assuming real automatic betting.', user_action: 'Define bankroll, risk profile and allowed markets.', success_metric: 'Signals with recommended stake and justification.' },
      package_saas: { title: 'Package as sellable SaaS', business_goal: 'Client accesses online without folders, terminal or technical knowledge.', user_action: 'Prepare demo, users, plans and separated deployment.', success_metric: 'Public demo with consistent data and click-based flow.' },
    },
  },
  es: {
    pill: 'ERP Guiado',
    title: 'Onboarding operacional de MatchFlow',
    subtitle: 'Desde el primer dato hasta la banca inteligente, sin depender del terminal.',
    start: 'Comenzar operación',
    maturity: 'Ver madurez SaaS',
    readiness: 'Preparación',
    journey: 'jornada guiada',
    section: 'Jornada del usuario',
    action: 'Acción',
    metric: 'Métrica',
    principle: 'El usuario final entiende decisiones y resultados; la ingeniería queda invisible detrás de los jobs.',
    statuses: { done: 'concluido', blocked: 'bloqueado', ready: 'listo', needs_data: 'necesita datos', gated: 'con gate', waiting_signals: 'esperando señales', in_progress: 'en progreso' },
    steps: {
      connect_engine: { title: 'Conectar motor de datos', business_goal: 'Transformar el provider interno FlashScore en una operación interna de MatchFlow.', user_action: 'Abrir Central de Datos y validar si el engine fue detectado.', success_metric: 'Engine detectado y al menos una base de partidos disponible.' },
      sync_matches: { title: 'Actualizar partidos y odds', business_goal: 'Garantizar que el usuario no necesite ejecutar scripts manualmente.', user_action: 'Hacer clic en Actualizar Datos o usar un job programado.', success_metric: 'Partidos, ligas y equipos visibles en el producto.' },
      validate_segments: { title: 'Validar liga, equipo y mercado', business_goal: 'Evitar decisiones con ROI bonito, pero sin muestra confiable.', user_action: 'Elegir campeonato y mercado para auditar.', success_metric: 'Segmentos aprobados para alimentar ML.' },
      train_models: { title: 'Entrenar ML con gates', business_goal: 'Usar ML solo donde el backtest demostró estabilidad.', user_action: 'Ejecutar entrenamiento/evaluación en ML Intelligence.', success_metric: 'Modelo activo con calibración y explicabilidad.' },
      operate_bankroll: { title: 'Operar banca inteligente', business_goal: 'Automatizar stake sin asumir apuesta real automática.', user_action: 'Definir banca, perfil de riesgo y mercados permitidos.', success_metric: 'Señales con stake recomendado y justificación.' },
      package_saas: { title: 'Empaquetar como SaaS vendible', business_goal: 'El cliente accede online, sin carpeta, terminal o conocimiento técnico.', user_action: 'Preparar demo, usuarios, planes y deploy separado.', success_metric: 'Demo pública con datos consistentes y flujo por clic.' },
    },
  },
};

export default function OnboardingRoadmap({ setPage }) {
  const { language } = useApp();
  const copy = COPY[language] || COPY.pt;
  const [data, setData] = useState(null);

  useEffect(() => { api.platformOnboardingRoadmap().then(r => setData(r.data)).catch(() => setData(null)); }, []);

  const steps = useMemo(() => {
    const apiSteps = data?.steps?.length ? data.steps : Object.keys(copy.steps).map((id) => ({ id, status: 'ready' }));
    return apiSteps.map((step) => ({ ...step, ...(copy.steps[step.id] || {}) }));
  }, [data, copy]);

  return <div className="page erp-page">
    <section className="erp-hero onboarding-hero">
      <div>
        <span className="brand-pill">{copy.pill}</span>
        <h1>{copy.title}</h1>
        <p>{copy.subtitle}</p>
        <div className="hero-actions">
          <button className="btn btn-primary" type="button" onClick={() => setPage('Data Center')}>{copy.start}</button>
          <button className="btn btn-secondary" type="button" onClick={() => setPage('SaaS Maturity')}>{copy.maturity}</button>
        </div>
      </div>
      <div className="hero-score-card clean"><span>{copy.readiness}</span><strong>{data?.readiness_score ?? 0}%</strong><small>{copy.journey}</small></div>
    </section>
    <section className="section-block">
      <div className="section-title-row"><h2>{copy.section}</h2><span>{copy.principle}</span></div>
      <div className="roadmap-lane">
        {steps.map((step, idx) => <button key={step.id} type="button" className={`roadmap-step ${step.status}`} onClick={() => setPage(PAGE_BY_STEP[step.id] || 'Mission Control')}>
          <span className="roadmap-number">{idx + 1}</span>
          <div>
            <b>{step.title}</b>
            <em>{copy.statuses[step.status] || step.status}</em>
            <p>{step.business_goal}</p>
            <small><strong>{copy.action}:</strong> {step.user_action}</small>
            <small><strong>{copy.metric}:</strong> {step.success_metric}</small>
          </div>
        </button>)}
      </div>
    </section>
  </div>;
}
