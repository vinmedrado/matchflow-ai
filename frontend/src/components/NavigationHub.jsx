import { useEffect, useMemo, useState } from 'react';
import { useI18n } from '../i18n.js';
import { useApp } from '../store/AppContext.jsx';

const STORAGE_KEY = 'matchflow_ai_sidebar_collapsed';

const MODULES = [
  {
    id: 'overview',
    label: 'Visão Geral',
    shortLabel: 'Geral',
    description: 'Resumo executivo, competições e indicadores do ERP.',
    accent: 'blue',
    items: [
      { page: 'Mission Control', icon: '🧠', key: 'missionControl', hint: 'Fluxo guiado do produto' },
      { page: 'Onboarding Roadmap', icon: '🧭', key: 'onboardingRoadmap', hint: 'Jornada passo a passo' },
      { page: 'Product Cockpit', icon: '🚀', key: 'productCockpit', hint: 'Visão SaaS vendável' },
      { page: 'Home', icon: '🏠', key: 'home', hint: 'Central do produto' },
      { page: 'Dashboard', icon: '📊', key: 'dashboard', hint: 'KPIs e visão executiva' },
      { page: 'Competitions', icon: '🏆', key: 'competitions', hint: 'Ligas, tabela e jogos' },
    ],
  },
  {
    id: 'intelligence',
    label: 'Inteligência',
    shortLabel: 'IA',
    description: 'Backtest, ML, decisão e gestão de banca em um fluxo único.',
    accent: 'purple',
    items: [
      { page: 'Backtest Intelligence', icon: '📈', key: 'backtestIntel', hint: 'Backtest por liga/time/mercado' },
      { page: 'ML Intelligence', icon: '🤖', key: 'mlIntel', hint: 'Gates, drift e calibração' },
      { page: 'Risk Engine', icon: '💰', key: 'riskEngine', hint: 'Banca automática inteligente' },
      { page: 'Strategy Studio', icon: '🧪', key: 'strategyStudio', hint: 'Presets de banca e risco' },
      { page: 'Decision Room', icon: '🕹️', key: 'decisionRoom', hint: 'Checklist antes dos sinais' },
      { page: 'Decision Engine', icon: '🎯', key: 'decision', hint: 'EV, risco e decisão' },
    ],
  },
  {
    id: 'operation',
    label: 'Operação',
    shortLabel: 'Ops',
    description: 'Execução do data-engine, monitoramento, testes e automações.',
    accent: 'green',
    items: [
      { page: 'Data Center', icon: '🗄️', key: 'dataCenter', hint: 'Data Engine online', pulse: true, badge: 'LIVE' },
      { page: 'Operational Guide', icon: '🗺️', key: 'operationalGuide', hint: 'APIs, Data Engine e fluxo SaaS' },
      { page: 'API Catalog', icon: '🔌', key: 'apiCatalog', hint: 'Rotas explicadas por negócio' },
      { page: 'Data Operations', icon: '⚙️', key: 'operations', hint: 'Rodar data-engine', pulse: true },
      { page: 'Test Lab', icon: '🧭', key: 'testLab', hint: 'Jogos futuros e simulação' },
      { page: 'Monitoring', icon: '📡', key: 'monitoring', hint: 'Drift e alertas', pulse: true },
      { page: 'Jobs Center', icon: '🧩', key: 'jobsCenter', hint: 'Fila, histórico e scheduler' },
      { page: 'Automation', icon: '🔁', key: 'automation', hint: 'Scheduler e histórico' },
    ],
  },
  {
    id: 'governance',
    label: 'Governança',
    shortLabel: 'Gov',
    description: 'Qualidade, auditoria, times, sistema e assistente.',
    accent: 'orange',
    items: [
      { page: 'Data Quality', icon: '✅', key: 'quality', hint: 'Consistência da base' },
      { page: 'Team Analytics', icon: '👥', key: 'teams', hint: 'Perfil por equipe' },
      { page: 'System Status', icon: '🛡️', key: 'system', hint: 'Saúde do sistema', pulse: true, badge: 'OK' },
      { page: 'User Workspace', icon: '🏢', key: 'userWorkspace', hint: 'Organização, usuário e banca' },
      { page: 'Sales Readiness', icon: '💎', key: 'salesReadiness', hint: 'Roteiro de venda e demo' },
      { page: 'SaaS Maturity', icon: '📌', key: 'saasMaturity', hint: 'Diagnóstico de produto vendável' },
      { page: 'Demo Mode', icon: '🎬', key: 'demoMode', hint: 'Demo pública segura', badge: 'DEMO' },
      { page: 'Assistant', icon: '✨', key: 'assistant', hint: 'Copiloto analítico' },
    ],
  },
];

function findActiveModule(page) {
  return MODULES.find((module) => module.items.some((item) => item.page === page)) || MODULES[0];
}

function readStoredPreference() {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === 'true';
  } catch {
    return false;
  }
}

function getInitialCollapsed() {
  if (typeof window === 'undefined') return false;
  if (window.innerWidth <= 1180) return true;
  return readStoredPreference();
}

export default function NavigationHub({ page, setPage }) {
  const { t } = useI18n();
  const { user, logout } = useApp();
  const activeModule = findActiveModule(page);
  const [moduleId, setModuleId] = useState(activeModule.id);
  const [collapsed, setCollapsed] = useState(getInitialCollapsed);
  const [mobileOpen, setMobileOpen] = useState(false);

  const selectedModule = useMemo(() => MODULES.find((module) => module.id === moduleId) || activeModule, [moduleId, activeModule]);

  useEffect(() => {
    setModuleId(activeModule.id);
  }, [activeModule.id]);

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, String(collapsed));
    } catch {
      // Preference persistence is a UX enhancement; navigation still works without localStorage.
    }
  }, [collapsed]);

  useEffect(() => {
    const onResize = () => {
      if (window.innerWidth <= 1180) setCollapsed(true);
      if (window.innerWidth > 760) setMobileOpen(false);
    };
    onResize();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  useEffect(() => {
    if (!mobileOpen) return;
    const onKey = (event) => {
      if (event.key === 'Escape') setMobileOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [mobileOpen]);

  function openPage(nextPage) {
    setPage(nextPage);
    setMobileOpen(false);
  }

  function selectModule(module) {
    setModuleId(module.id);
    if (collapsed) return;
    const firstPage = module.items[0]?.page;
    if (firstPage) openPage(firstPage);
  }

  return (
    <>
      <button
        type="button"
        className="mobile-sidebar-trigger"
        onClick={() => setMobileOpen(true)}
        aria-label="Abrir navegação"
      >
        ☰ <span>Menu</span>
      </button>

      <div
        className={`sidebar-drawer-backdrop${mobileOpen ? ' open' : ''}`}
        onClick={() => setMobileOpen(false)}
        aria-hidden="true"
      />

      <aside
        className={`navigation-hub premium-sidebar ${collapsed ? 'collapsed' : 'expanded'} ${mobileOpen ? 'mobile-open' : ''}`}
        aria-label="Navegação principal MatchFlow"
      >
        <div className="premium-sidebar-brand">
          <div className="premium-sidebar-logo" aria-hidden="true">MF</div>
          <div className="premium-sidebar-brand-copy">
            <strong>Match<span>Flow</span> AI</strong>
            <small>{t('appSubtitle')}</small>
          </div>
          <button
            type="button"
            className="sidebar-collapse-btn"
            onClick={() => setCollapsed((value) => !value)}
            aria-label={collapsed ? 'Expandir sidebar' : 'Recolher sidebar'}
            aria-expanded={!collapsed}
            title={collapsed ? 'Expandir' : 'Recolher'}
          >
            {collapsed ? '›' : '‹'}
          </button>
        </div>

        <div className="premium-sidebar-mode" title="PAPER TRADING SIMULATION ONLY">
          <span className="status-pulse-dot" />
          <div>
            <b>PAPER TRADING</b>
            <small>{user?.tenant?.is_demo ? 'DEMO TENANT' : 'SIMULATION ONLY'}</small>
          </div>
        </div>

        <div className="premium-sidebar-modules" role="tablist" aria-label="Módulos do MatchFlow AI">
          {MODULES.map((module) => (
            <button
              type="button"
              key={module.id}
              className={`sidebar-module-pill sidebar-module-${module.accent}${selectedModule.id === module.id ? ' active' : ''}`}
              onClick={() => selectModule(module)}
              title={`${module.label} · ${module.description}`}
              aria-pressed={selectedModule.id === module.id}
            >
              <span>{module.shortLabel}</span>
              <small>{module.items.length}</small>
            </button>
          ))}
        </div>

        <nav className="premium-sidebar-nav" aria-label={`Rotas de ${selectedModule.label}`}>
          <div className="premium-sidebar-section">
            <span className="sidebar-section-kicker">Módulo ativo</span>
            <strong>{selectedModule.label}</strong>
            <small>{selectedModule.description}</small>
          </div>

          {selectedModule.items.map((item) => {
            const isActive = page === item.page;
            const label = t(item.key) || item.page;
            return (
              <button
                type="button"
                key={item.page}
                className={`premium-sidebar-item${isActive ? ' active' : ''}${item.pulse ? ' monitored' : ''}`}
                onClick={() => openPage(item.page)}
                title={`${label} · ${item.hint}`}
                aria-current={isActive ? 'page' : undefined}
              >
                <span className="premium-sidebar-icon" aria-hidden="true">{item.icon}</span>
                <span className="premium-sidebar-label">
                  <b>{label}</b>
                  <small>{item.hint}</small>
                </span>
                {item.badge ? <span className="premium-sidebar-badge">{item.badge}</span> : null}
                {item.pulse ? <span className="sidebar-mini-pulse" aria-label="status ativo" /> : null}
              </button>
            );
          })}
        </nav>

        <div className="premium-sidebar-user" title={user?.email || 'Usuário'}>
          <span className="premium-sidebar-avatar">{(user?.name || 'MF').slice(0,2).toUpperCase()}</span>
          <div>
            <b>{user?.name || 'Usuário'}</b>
            <small>{user?.role_key || user?.role || 'USER'} · {user?.tenant?.name || 'Workspace seguro'}</small>
          </div>
          <button type="button" className="sidebar-logout-btn" onClick={logout} title="Sair">⏻</button>
        </div>
      </aside>
    </>
  );
}
