import { useApp } from '../store/AppContext.jsx';
import { useI18n } from '../i18n.js';
import LanguageSelector from './LanguageSelector.jsx';
import logo from '../assets/brand/matchflow-ai-logo.jpeg';

const PAGE_META = {
  'Home': { icon:'🏠', key:'home', desc:'premiumSubtitle' },
  'Dashboard': { icon:'📊', key:'dashboard', desc:'premiumSubtitle' },
  'Competitions': { icon:'🏆', key:'competitions', desc:'competitionsDesc' },
  'Data Operations': { icon:'⚙️', key:'operations', desc:'dataEngineDesc' },
  'Decision Engine': { icon:'🎯', key:'decision', desc:'Motor de score, EV, risco e decisão' },
  'Bankroll Projection': { icon:'💰', key:'bankroll', desc:'Gestão automática de stake e risco' },
  'Backtest Lab': { icon:'🧪', key:'backtest', desc:'Validação por liga, time e mercado' },
  'ML Lab': { icon:'🤖', key:'ml', desc:'Modelos alimentados pela camada de backtest' },
  'Test Lab': { icon:'🧭', key:'testLab', desc:'Simulação forward com jogos futuros' },
  'Monitoring': { icon:'📡', key:'monitoring', desc:'Drift, anomalias e alertas' },
  'Automation': { icon:'🔁', key:'automation', desc:'Scheduler, integrações e histórico' },
  'Data Quality': { icon:'✅', key:'quality', desc:'Auditoria e consistência da base' },
  'Team Analytics': { icon:'👥', key:'teams', desc:'Análise por equipe' },
  'System Status': { icon:'🛡️', key:'system', desc:'Status do servidor e módulos' },
  'Assistant': { icon:'✨', key:'assistant', desc:'Assistente analítico' },
};

export default function Topbar({ page }) {
  const { user, logout } = useApp();
  const { t } = useI18n();
  const meta = PAGE_META[page] || { icon:'•', key:page, desc:'' };
  const desc = meta.desc && t(meta.desc) !== meta.desc ? t(meta.desc) : meta.desc;

  return (
    <header className="premium-topbar">
      <div className="product-lockup">
        <img className="topbar-logo-mark" src={logo} alt="MatchFlow AI" />
        <div>
          <h1>Match<span>Flow AI</span></h1>
          <p>{t('appSubtitle')}</p>
        </div>
      </div>

      <div className="topbar-current-page">
        <span className="topbar-icon">{meta.icon}</span>
        <div>
          <div className="topbar-page">{t(meta.key) || page}</div>
          {desc && <div className="topbar-desc">{desc}</div>}
        </div>
      </div>

      <div className="topbar-right">
        <LanguageSelector compact />
        <span className="topbar-badge">{t('version')}</span>
        {user && <span className="topbar-badge">{String(user.role || 'user').toUpperCase()}</span>}
        {user?.is_demo && <span className="topbar-badge">DEMO</span>}
        {user?.tenant_id && <span className="topbar-badge">Tenant: {user.tenant?.slug || user.tenant_id}</span>}
        {user && <span className="topbar-user">{user.name || user.email}</span>}
        <button className="topbar-btn" onClick={logout}>{t('logout')}</button>
      </div>
    </header>
  );
}
