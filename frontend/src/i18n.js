import { useApp } from './store/AppContext.jsx';

export const LANGUAGES = [
  { code: 'pt', label: 'Português' },
  { code: 'en', label: 'English' },
  { code: 'es', label: 'Español' },
];

const DICT = {
  pt: {
    aiCopilotPremium: 'AI Copilot', agenticIntelligence: 'Agentic Intelligence', autonomousWorkspace: 'Autonomous OS', cognitiveWorkspace: 'Cognitive OS', executiveCockpit: 'Executive Cockpit', evolutionCockpit: 'Evolution Cockpit', liveCenter: 'Live Center', aiExplainability: 'Explicabilidade IA', paperTradingPremium: 'Paper Premium', premiumAnalytics: 'Analytics Premium',
    
    missionControl: 'Mission Control', onboardingRoadmap: 'Roadmap', decisionRoom: 'Sala de Decisión', strategyStudio: 'Strategy Studio', saasMaturity: 'Madurez SaaS', onboardingRoadmap: 'Roadmap', decisionRoom: 'Decision Room', strategyStudio: 'Strategy Studio', saasMaturity: 'SaaS Maturity', onboardingRoadmap: 'Roadmap', decisionRoom: 'Sala de Decisão', strategyStudio: 'Strategy Studio', saasMaturity: 'Maturidade SaaS', apiCatalog: 'Catálogo de APIs', userWorkspace: 'Workspace', salesReadiness: 'Venda/Demo', operationalGuide: 'Guia Operacional', productCockpit: 'Cockpit do Produto', dataCenter: 'Central de Dados', backtestIntel: 'Backtest Intelligence', mlIntel: 'ML Intelligence', riskEngine: 'Risk Engine', jobsCenter: 'Jobs Center', demoMode: 'Modo Demo',
    home: 'Início', dashboard: 'Dashboard', operations: 'Operações de Dados', competitions: 'Competições', decision: 'Motor de Decisão', bankroll: 'Gestão de Banca', backtest: 'Laboratório de Backtest', ml: 'Laboratório de ML', testLab: 'Test Lab', monitoring: 'Monitoramento', automation: 'Automação', quality: 'Qualidade de Dados', teams: 'Análise por Times', system: 'Status do Sistema', assistant: 'Assistente', logout: 'Sair', version: 'v7.0',
    appSubtitle: 'ERP analítico esportivo', loginAccess: 'Acesso local', email: 'E-mail', password: 'Senha', enter: 'Entrar', entering: 'Entrando...', defaultCredentials: 'Credenciais padrão', noAutoBet: 'Sistema de análise. Não executa apostas automaticamente.', manualRequired: 'Confirmação manual obrigatória.',
    premiumTitle: 'Central MatchFlow', premiumSubtitle: 'Um ERP esportivo para dados, backtest, ML, decisão e banca em um único fluxo operacional.',
    runEngine: 'Rodar Data Engine', update7: 'Atualizar 7 dias', update30: 'Últimos 30 dias', fullHistory: 'Histórico completo', dataEngineTitle: 'Central do Data Engine', dataEngineDesc: 'Entenda exatamente de onde vêm os jogos, quando o FlashScore Engine roda e como os dados entram no MatchFlow.',
    competitionsTitle: 'Competições', competitionsDesc: 'Selecione uma liga para ver tabela, times, últimos jogos e base disponível.', standings: 'Tabela', recentMatches: 'Últimos jogos', upcomingMatches: 'Próximos jogos', selectLeague: 'Selecionar campeonato',
    backtestHealth: 'Auditoria do Backtest', bankrollPolicy: 'Política de Banca', recommendedMethod: 'Método recomendado', multiUser: 'Multiusuário', role: 'Perfil', language: 'Idioma',
    empty: 'Nenhum dado disponível ainda.', loading: 'Carregando...', refresh: 'Atualizar', status: 'Status', nextStep: 'Próximo passo',
  },
  en: {
    aiCopilotPremium: 'AI Copilot', agenticIntelligence: 'Agentic Intelligence', autonomousWorkspace: 'Autonomous OS', cognitiveWorkspace: 'Cognitive OS', executiveCockpit: 'Executive Cockpit', evolutionCockpit: 'Evolution Cockpit', liveCenter: 'Live Center', aiExplainability: 'AI Explainability', paperTradingPremium: 'Paper Premium', premiumAnalytics: 'Premium Analytics',
    
    missionControl: 'Mission Control', apiCatalog: 'API Catalog', userWorkspace: 'Workspace', salesReadiness: 'Sales/Demo', operationalGuide: 'Operational Guide', productCockpit: 'Product Cockpit', dataCenter: 'Data Center', backtestIntel: 'Backtest Intelligence', mlIntel: 'ML Intelligence', riskEngine: 'Risk Engine', jobsCenter: 'Jobs Center', demoMode: 'Demo Mode',
    home: 'Home', dashboard: 'Dashboard', operations: 'Data Operations', competitions: 'Competitions', decision: 'Decision Engine', bankroll: 'Bankroll Management', backtest: 'Backtest Lab', ml: 'ML Lab', testLab: 'Test Lab', monitoring: 'Monitoring', automation: 'Automation', quality: 'Data Quality', teams: 'Team Analytics', system: 'System Status', assistant: 'Assistant', logout: 'Logout', version: 'v7.0',
    appSubtitle: 'Sports analytics ERP', loginAccess: 'Local access', email: 'E-mail', password: 'Password', enter: 'Sign in', entering: 'Signing in...', defaultCredentials: 'Default credentials', noAutoBet: 'Analytics system. It does not place bets automatically.', manualRequired: 'Manual confirmation required.',
    premiumTitle: 'MatchFlow Hub', premiumSubtitle: 'A sports ERP for data, backtesting, ML, decisioning and bankroll operations in one workflow.',
    runEngine: 'Run Data Engine', update7: 'Update 7 days', update30: 'Last 30 days', fullHistory: 'Full history', dataEngineTitle: 'Data Engine Hub', dataEngineDesc: 'Understand exactly where matches come from, when the FlashScore Engine runs and how data enters MatchFlow.',
    competitionsTitle: 'Competitions', competitionsDesc: 'Select a league to view standings, teams, recent matches and available data.', standings: 'Standings', recentMatches: 'Recent matches', upcomingMatches: 'Upcoming matches', selectLeague: 'Select competition',
    backtestHealth: 'Backtest Audit', bankrollPolicy: 'Bankroll Policy', recommendedMethod: 'Recommended method', multiUser: 'Multi-user', role: 'Role', language: 'Language',
    empty: 'No data available yet.', loading: 'Loading...', refresh: 'Refresh', status: 'Status', nextStep: 'Next step',
  },
  es: {
    aiCopilotPremium: 'AI Copilot', agenticIntelligence: 'Agentic Intelligence', autonomousWorkspace: 'Autonomous OS', cognitiveWorkspace: 'Cognitive OS', executiveCockpit: 'Executive Cockpit', evolutionCockpit: 'Evolution Cockpit', liveCenter: 'Live Center', aiExplainability: 'Explicabilidad IA', paperTradingPremium: 'Paper Premium', premiumAnalytics: 'Analytics Premium',
    
    missionControl: 'Mission Control', apiCatalog: 'Catálogo de APIs', userWorkspace: 'Workspace', salesReadiness: 'Venta/Demo', operationalGuide: 'Guía Operativa', productCockpit: 'Cockpit del Producto', dataCenter: 'Central de Datos', backtestIntel: 'Backtest Intelligence', mlIntel: 'ML Intelligence', riskEngine: 'Risk Engine', jobsCenter: 'Jobs Center', demoMode: 'Modo Demo',
    home: 'Inicio', dashboard: 'Dashboard', operations: 'Operaciones de Datos', competitions: 'Competiciones', decision: 'Motor de Decisión', bankroll: 'Gestión de Banca', backtest: 'Laboratorio de Backtest', ml: 'Laboratorio de ML', testLab: 'Test Lab', monitoring: 'Monitoreo', automation: 'Automatización', quality: 'Calidad de Datos', teams: 'Análisis por Equipos', system: 'Estado del Sistema', assistant: 'Asistente', logout: 'Salir', version: 'v7.0',
    appSubtitle: 'ERP analítico deportivo', loginAccess: 'Acceso local', email: 'E-mail', password: 'Contraseña', enter: 'Entrar', entering: 'Entrando...', defaultCredentials: 'Credenciales predeterminadas', noAutoBet: 'Sistema de análisis. No ejecuta apuestas automáticamente.', manualRequired: 'Confirmación manual obligatoria.',
    premiumTitle: 'Central MatchFlow', premiumSubtitle: 'Un ERP deportivo para datos, backtest, ML, decisión y banca en un solo flujo operativo.',
    runEngine: 'Ejecutar Data Engine', update7: 'Actualizar 7 días', update30: 'Últimos 30 días', fullHistory: 'Histórico completo', dataEngineTitle: 'Central del Data Engine', dataEngineDesc: 'Comprende exactamente de dónde vienen los partidos, cuándo corre FlashScore Engine y cómo los datos entran en MatchFlow.',
    competitionsTitle: 'Competiciones', competitionsDesc: 'Selecciona una liga para ver tabla, equipos, últimos partidos y base disponible.', standings: 'Tabla', recentMatches: 'Últimos partidos', upcomingMatches: 'Próximos partidos', selectLeague: 'Seleccionar campeonato',
    backtestHealth: 'Auditoría del Backtest', bankrollPolicy: 'Política de Banca', recommendedMethod: 'Método recomendado', multiUser: 'Multiusuario', role: 'Perfil', language: 'Idioma',
    empty: 'Aún no hay datos disponibles.', loading: 'Cargando...', refresh: 'Actualizar', status: 'Estado', nextStep: 'Siguiente paso',
  },
};

export function translate(language, key) {
  return DICT[language]?.[key] || DICT.pt[key] || key;
}

export function useI18n() {
  const { language, setLanguage } = useApp();
  return { language, setLanguage, t: (key) => translate(language, key) };
}
