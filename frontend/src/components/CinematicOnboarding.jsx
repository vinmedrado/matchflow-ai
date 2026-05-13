import { useEffect, useMemo, useState } from 'react';
import logo from '../assets/brand/matchflow-ai-logo.jpeg';
import { useApp } from '../store/AppContext.jsx';

const ONBOARDING_COPY = {
  pt: {
    aria: 'Onboarding do MatchFlow AI',
    skip: 'Pular',
    tour: 'Tour Premium',
    back: 'Voltar',
    next: 'Próximo',
    launch: 'Abrir Workspace',
    spotlight: 'Tour contextual · Respeita redução de movimento',
    goTo: 'Ir para',
    steps: [
      { title: 'Bem-vindo ao MatchFlow AI', eyebrow: 'Tour de produto AI-native', text: 'Um cockpit cinematográfico para ingestão de dados, confiabilidade de modelos, monitoramento de drift e decisões seguras em PAPER_TRADING_SIMULATION_ONLY.', focus: 'Plataforma' },
      { title: 'Motor de Dados', eyebrow: 'Provider interno FlashScore', text: 'Captura de rede, fallback por DOM, mapeamento de entidades, deduplicação e qualidade de dados alimentam o núcleo operacional.', focus: 'Dados → Qualidade' },
      { title: 'Ensemble de ML', eyebrow: 'Calibração e confiabilidade', text: 'Predições com Random Forest, LightGBM e XGBoost são monitoradas com calibração, drift e saúde baseada em evidências.', focus: 'ML → Confiabilidade' },
      { title: 'Inteligência de Decisão', eyebrow: 'Ranking seguro de sinais', text: 'Candidatos de decisão exibem EV, confiança, flags de risco, simulação de banca e status de confirmação manual.', focus: 'Sinais → Revisão' },
      { title: 'Operação e Monitoramento', eyebrow: 'Sensação operacional ao vivo', text: 'Jobs, cobertura, saúde do provider, alertas e drift criam uma rotina operacional pronta para produção.', focus: 'Operação → Controle' },
    ],
  },
  en: {
    aria: 'MatchFlow AI onboarding',
    skip: 'Skip',
    tour: 'Premium Tour',
    back: 'Back',
    next: 'Next',
    launch: 'Launch Workspace',
    spotlight: 'Contextual walkthrough · Reduced-motion aware',
    goTo: 'Go to',
    steps: [
      { title: 'Welcome to MatchFlow AI', eyebrow: 'AI-native product tour', text: 'A cinematic cockpit for data ingestion, model reliability, drift monitoring and safe PAPER_TRADING_SIMULATION_ONLY decisions.', focus: 'Platform' },
      { title: 'Data Engine', eyebrow: 'FlashScore internal provider', text: 'Network capture, DOM fallback, entity mapping, deduplication and data quality feed the operational core.', focus: 'Data → Quality' },
      { title: 'ML Ensemble', eyebrow: 'Calibration and reliability', text: 'Random Forest, LightGBM and XGBoost predictions are monitored with calibration, drift and evidence-aware health.', focus: 'ML → Reliability' },
      { title: 'Decision Intelligence', eyebrow: 'Safe signal ranking', text: 'Decision candidates expose EV, confidence, risk flags, bankroll simulation and manual confirmation status.', focus: 'Signals → Review' },
      { title: 'Monitoring Ops', eyebrow: 'Live operational feeling', text: 'Jobs, coverage, provider health, alerts and drift create a production-ready operating rhythm.', focus: 'Ops → Control' },
    ],
  },
  es: {
    aria: 'Onboarding de MatchFlow AI',
    skip: 'Saltar',
    tour: 'Tour Premium',
    back: 'Volver',
    next: 'Siguiente',
    launch: 'Abrir Workspace',
    spotlight: 'Tour contextual · Compatible con reducción de movimiento',
    goTo: 'Ir a',
    steps: [
      { title: 'Bienvenido a MatchFlow AI', eyebrow: 'Tour de producto AI-native', text: 'Un cockpit cinematográfico para ingesta de datos, confiabilidad de modelos, monitoreo de drift y decisiones seguras en PAPER_TRADING_SIMULATION_ONLY.', focus: 'Plataforma' },
      { title: 'Motor de Datos', eyebrow: 'Provider interno FlashScore', text: 'Captura de red, fallback por DOM, mapeo de entidades, deduplicación y calidad de datos alimentan el núcleo operativo.', focus: 'Datos → Calidad' },
      { title: 'Ensemble de ML', eyebrow: 'Calibración y confiabilidad', text: 'Predicciones con Random Forest, LightGBM y XGBoost se monitorean con calibración, drift y salud basada en evidencias.', focus: 'ML → Confiabilidad' },
      { title: 'Inteligencia de Decisión', eyebrow: 'Ranking seguro de señales', text: 'Los candidatos de decisión muestran EV, confianza, flags de riesgo, simulación de banca y estado de confirmación manual.', focus: 'Señales → Revisión' },
      { title: 'Operación y Monitoreo', eyebrow: 'Sensación operacional en vivo', text: 'Jobs, cobertura, salud del provider, alertas y drift crean una rutina operativa lista para producción.', focus: 'Operación → Control' },
    ],
  },
};

export default function CinematicOnboarding({ open, onClose }) {
  const { language } = useApp();
  const copy = ONBOARDING_COPY[language] || ONBOARDING_COPY.pt;
  const steps = copy.steps;
  const [step, setStep] = useState(0);
  const current = steps[step] || steps[0];

  useEffect(() => {
    if (open) setStep(0);
  }, [open, language]);

  const goBack = () => setStep((s) => Math.max(0, s - 1));
  const goNext = () => setStep((s) => Math.min(steps.length - 1, s + 1));

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event) => {
      if (event.key === 'Escape') onClose?.();
      if (event.key === 'ArrowRight') goNext();
      if (event.key === 'ArrowLeft') goBack();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose, steps.length]);

  if (!open) return null;
  return (
    <div className="onboarding-backdrop" role="presentation">
      <section className="cinematic-onboarding" role="dialog" aria-modal="true" aria-label={copy.aria} onClick={(event) => event.stopPropagation()}>
        <div className="onboarding-field" aria-hidden="true"><i/><i/><i/><span/><span/></div>
        <button type="button" className="onboarding-close" onClick={onClose}>{copy.skip}</button>
        <div className="onboarding-brand"><img src={logo} alt="MatchFlow AI" /><span>{copy.tour}</span></div>
        <div className="onboarding-content">
          <span className="premium-eyebrow">{current.eyebrow}</span>
          <h2>{current.title}</h2>
          <p>{current.text}</p>
          <div className="walkthrough-spotlight"><b>{current.focus}</b><small>{copy.spotlight}</small></div>
        </div>
        <div className="onboarding-progress">
          {steps.map((item, index) => (
            <button key={`${language}-${item.title}`} type="button" className={index === step ? 'active' : ''} onClick={() => setStep(index)} aria-label={`${copy.goTo} ${item.title}`} />
          ))}
        </div>
        <div className="onboarding-actions">
          <button type="button" onClick={goBack} disabled={step === 0}>{copy.back}</button>
          {step < steps.length - 1
            ? <button type="button" className="primary" onClick={goNext}>{copy.next}</button>
            : <button type="button" className="primary" onClick={onClose}>{copy.launch}</button>}
        </div>
      </section>
    </div>
  );
}
