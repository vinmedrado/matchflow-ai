import { useEffect } from 'react';
import { useApp } from './store/AppContext.jsx';

const TEXT_MAP = {
  pt: {
    'AI-Native Football Intelligence Platform': 'Plataforma de Inteligência de Futebol AI-Native',
    'Quant football intelligence · AI-native operations': 'Inteligência quantitativa de futebol · operações com IA',
    'Advanced data engine, ensemble machine learning, calibration, drift monitoring and decision intelligence.': 'Motor avançado de dados, machine learning em ensemble, calibração, monitoramento de drift e inteligência de decisão.',
    'Launch Dashboard': 'Abrir Dashboard',
    'Live Demo': 'Demo ao Vivo',
    'View Architecture': 'Ver Arquitetura',
    'Public demo mode': 'Modo demo público',
    'Live feeling, clearly marked as simulation.': 'Sensação de operação ao vivo, claramente marcada como simulação.',
    'Animated activity helps presentations without pretending that demo events are real operations.': 'Atividades animadas ajudam apresentações sem fingir que eventos de demonstração são operações reais.',
    'Product preview': 'Prévia do produto',
    'MatchFlow AI Live Terminal': 'Terminal ao vivo MatchFlow AI',
    'Calibration Curve': 'Curva de calibração',
    'Reliability': 'Confiabilidade',
    'Data Engine': 'Motor de Dados',
    'Machine Learning': 'Machine Learning',
    'Decision Engine': 'Motor de Decisão',
    'Monitoring': 'Monitoramento',
    'Safety': 'Segurança',
    'Internal data core': 'Núcleo interno de dados',
    'Quality scored': 'Qualidade pontuada',
    'Model intelligence': 'Inteligência de modelo',
    'Paper signals': 'Sinais em simulação',
    'Ops ready': 'Operação pronta',
    'Live health': 'Saúde em tempo real',
    'Manual confirmation': 'Confirmação manual',
    'Safe mode': 'Modo seguro',
    'Data Engine Ops': 'Operações do Motor de Dados',
    'Drift Dashboard': 'Dashboard de Drift',
    'Decision Queue': 'Fila de Decisão',
    'Evidence Alerts': 'Alertas de Evidência',
    'Ready': 'Pronto',
    'Watching': 'Monitorando',
    'Paper only': 'Somente simulação',
    'Demo Safe': 'Demo segura',
    'VALUE SIGNAL': 'SINAL DE VALOR',
    'HEALTHY': 'SAUDÁVEL',
    'RELIABILITY': 'CONFIABILIDADE',
    'INTERNAL': 'INTERNO',
    'confidence · EV · bankroll': 'confiança · EV · banca',
    'jobs · alerts · coverage': 'jobs · alertas · cobertura',
    'brier · bins · drift': 'brier · bins · drift',
    'mapping · dedup · quality': 'mapeamento · dedup · qualidade',
    'DEMO PAPER MODE': 'MODO DEMO PAPER',
    'PAPER MODE': 'MODO PAPER',
    'AI Platform': 'Plataforma de IA',
    'Inteligência': 'Inteligência',
    'Operação': 'Operação',
    'Governança': 'Governança',
    'Auth SaaS': 'Auth SaaS',
    'Tenant': 'Tenant',
    'Roles': 'Perfis',
    'Paper mode': 'Modo paper',
    'Workspace / tenant': 'Workspace / tenant',
    'Token de reset': 'Token de reset',
    'Nova senha': 'Nova senha',
    'Manter sessão': 'Manter sessão',
    'Criar conta': 'Criar conta',
    'Gerar reset': 'Gerar reset',
    'Atualizar senha': 'Atualizar senha',
    'Registro': 'Registro',
    'Esqueci senha': 'Esqueci senha',
    'Credenciais demo': 'Credenciais demo',
    'Token dev/demo': 'Token dev/demo',
    'Email verification estruturado, mas desabilitado por padrão.': 'Verificação de e-mail estruturada, mas desabilitada por padrão.',
    'Acesse sua organização com sessão segura.': 'Acesse sua organização com sessão segura.',
    'Crie sua conta e tenant isolado.': 'Crie sua conta e tenant isolado.',
    'Receba um token de reset. Em demo, ele aparece abaixo.': 'Receba um token de reset. Em demo, ele aparece abaixo.',
    'Informe o token e a nova senha.': 'Informe o token e a nova senha.',
    'Home': 'Início',
    'Dashboard': 'Dashboard',
    'Competitions': 'Competições',
    'Data Operations': 'Operações de Dados',
    'Bankroll Projection': 'Projeção de Banca',
    'Backtest Lab': 'Laboratório de Backtest',
    'ML Lab': 'Laboratório de ML',
    'Test Lab': 'Laboratório de Testes',
    'Automation': 'Automação',
    'Data Quality': 'Qualidade de Dados',
    'Team Analytics': 'Análise por Times',
    'System Status': 'Status do Sistema',
    'Assistant': 'Assistente',
    'API Catalog': 'Catálogo de APIs',
    'User Workspace': 'Workspace do Usuário',
    'Sales Readiness': 'Pronto para Vendas',
    'Onboarding Roadmap': 'Roadmap de Onboarding',
    'Decision Room': 'Sala de Decisão',
    'Strategy Studio': 'Estúdio de Estratégia',
    'SaaS Maturity': 'Maturidade SaaS',
    'Live Center': 'Central Ao Vivo',
    'AI Explainability': 'Explicabilidade da IA',
    'Paper Trading Premium': 'Paper Trading Premium',
    'Premium Analytics': 'Analytics Premium',
    'Agentic Intelligence': 'Inteligência Agêntica',
    'Autonomous Workspace': 'Workspace Autônomo',
    'Cognitive Workspace': 'Workspace Cognitivo',
    'Executive Cockpit': 'Cockpit Executivo',
    'Evolution Cockpit': 'Cockpit de Evolução',
    'Run': 'Rodar',
    'Refresh': 'Atualizar',
    'Status': 'Status',
    'Summary': 'Resumo',
    'Coverage': 'Cobertura',
    'Quality': 'Qualidade',
    'Confidence': 'Confiança',
    'Risk': 'Risco',
    'Bankroll': 'Banca',
    'Market': 'Mercado',
    'League': 'Liga',
    'Team': 'Time',
    'Teams': 'Times',
    'Matches': 'Jogos',
    'Upcoming': 'Próximos',
    'Recent': 'Recentes',
    'Settings': 'Configurações',
    'Health': 'Saúde',
    'Alerts': 'Alertas',
    'History': 'Histórico',
    'Signals': 'Sinais',
    'Simulation': 'Simulação',
    'Live': 'Ao vivo',
    'Language': 'Idioma',
    'Logout': 'Sair',
    'Search': 'Buscar',
    'Open': 'Abrir',
    'Close': 'Fechar',
    'Cancel': 'Cancelar',
    'Save': 'Salvar',
    'Loading...': 'Carregando...',
    'No data available yet.': 'Nenhum dado disponível ainda.',
    'Next step': 'Próximo passo',
    'Recommended method': 'Método recomendado',
    'Default credentials': 'Credenciais padrão',
    'Analytics system. It does not place bets automatically.': 'Sistema de análise. Não executa apostas automaticamente.',
    'Manual confirmation required.': 'Confirmação manual obrigatória.'
  },
  es: {
    'AI-Native Football Intelligence Platform': 'Plataforma de Inteligencia de Fútbol AI-Native',
    'Quant football intelligence · AI-native operations': 'Inteligencia cuantitativa de fútbol · operaciones con IA',
    'Advanced data engine, ensemble machine learning, calibration, drift monitoring and decision intelligence.': 'Motor avanzado de datos, machine learning en ensemble, calibración, monitoreo de drift e inteligencia de decisión.',
    'Launch Dashboard': 'Abrir Dashboard',
    'Live Demo': 'Demo en Vivo',
    'View Architecture': 'Ver Arquitectura',
    'Public demo mode': 'Modo demo público',
    'Live feeling, clearly marked as simulation.': 'Sensación de operación en vivo, claramente marcada como simulación.',
    'Animated activity helps presentations without pretending that demo events are real operations.': 'La actividad animada ayuda en presentaciones sin fingir que los eventos demo son operaciones reales.',
    'Product preview': 'Vista previa del producto',
    'MatchFlow AI Live Terminal': 'Terminal en vivo MatchFlow AI',
    'Calibration Curve': 'Curva de calibración',
    'Reliability': 'Confiabilidad',
    'Data Engine': 'Motor de Datos',
    'Machine Learning': 'Machine Learning',
    'Decision Engine': 'Motor de Decisión',
    'Monitoring': 'Monitoreo',
    'Safety': 'Seguridad',
    'Internal data core': 'Núcleo interno de datos',
    'Quality scored': 'Calidad puntuada',
    'Model intelligence': 'Inteligencia del modelo',
    'Paper signals': 'Señales en simulación',
    'Ops ready': 'Operación lista',
    'Live health': 'Salud en tiempo real',
    'Manual confirmation': 'Confirmación manual',
    'Safe mode': 'Modo seguro',
    'Data Engine Ops': 'Operaciones del Motor de Datos',
    'Drift Dashboard': 'Dashboard de Drift',
    'Decision Queue': 'Cola de Decisión',
    'Evidence Alerts': 'Alertas de Evidencia',
    'Ready': 'Listo',
    'Watching': 'Monitoreando',
    'Paper only': 'Solo simulación',
    'Demo Safe': 'Demo segura',
    'VALUE SIGNAL': 'SEÑAL DE VALOR',
    'HEALTHY': 'SALUDABLE',
    'RELIABILITY': 'CONFIABILIDAD',
    'INTERNAL': 'INTERNO',
    'confidence · EV · bankroll': 'confianza · EV · banca',
    'jobs · alerts · coverage': 'jobs · alertas · cobertura',
    'brier · bins · drift': 'brier · bins · drift',
    'mapping · dedup · quality': 'mapeo · dedup · calidad',
    'DEMO PAPER MODE': 'MODO DEMO PAPER',
    'PAPER MODE': 'MODO PAPER',
    'AI Platform': 'Plataforma de IA',
    'Inteligência': 'Inteligencia',
    'Operação': 'Operación',
    'Governança': 'Gobernanza',
    'Auth SaaS': 'Auth SaaS',
    'Tenant': 'Tenant',
    'Roles': 'Roles',
    'Paper mode': 'Modo paper',
    'Workspace / tenant': 'Workspace / tenant',
    'Token de reset': 'Token de reset',
    'Nova senha': 'Nueva contraseña',
    'Manter sessão': 'Mantener sesión',
    'Criar conta': 'Crear cuenta',
    'Gerar reset': 'Generar reset',
    'Atualizar senha': 'Actualizar contraseña',
    'Registro': 'Registro',
    'Esqueci senha': 'Olvidé contraseña',
    'Credenciais demo': 'Credenciales demo',
    'Token dev/demo': 'Token dev/demo',
    'Email verification estruturado, mas desabilitado por padrão.': 'Verificación de email estructurada, pero deshabilitada por defecto.',
    'Acesse sua organização com sessão segura.': 'Accede a tu organización con sesión segura.',
    'Crie sua conta e tenant isolado.': 'Crea tu cuenta y tenant aislado.',
    'Receba um token de reset. Em demo, ele aparece abaixo.': 'Recibe un token de reset. En demo aparece abajo.',
    'Informe o token e a nova senha.': 'Informa el token y la nueva contraseña.',
    'Home': 'Inicio',
    'Dashboard': 'Dashboard',
    'Competitions': 'Competiciones',
    'Data Operations': 'Operaciones de Datos',
    'Bankroll Projection': 'Proyección de Banca',
    'Backtest Lab': 'Laboratorio de Backtest',
    'ML Lab': 'Laboratorio de ML',
    'Test Lab': 'Laboratorio de Pruebas',
    'Automation': 'Automatización',
    'Data Quality': 'Calidad de Datos',
    'Team Analytics': 'Análisis por Equipos',
    'System Status': 'Estado del Sistema',
    'Assistant': 'Asistente',
    'API Catalog': 'Catálogo de APIs',
    'User Workspace': 'Workspace del Usuario',
    'Sales Readiness': 'Listo para Ventas',
    'Onboarding Roadmap': 'Roadmap de Onboarding',
    'Decision Room': 'Sala de Decisión',
    'Strategy Studio': 'Estudio de Estrategia',
    'SaaS Maturity': 'Madurez SaaS',
    'Live Center': 'Central en Vivo',
    'AI Explainability': 'Explicabilidad de IA',
    'Paper Trading Premium': 'Paper Trading Premium',
    'Premium Analytics': 'Analytics Premium',
    'Agentic Intelligence': 'Inteligencia Agéntica',
    'Autonomous Workspace': 'Workspace Autónomo',
    'Cognitive Workspace': 'Workspace Cognitivo',
    'Executive Cockpit': 'Cockpit Ejecutivo',
    'Evolution Cockpit': 'Cockpit de Evolución',
    'Run': 'Ejecutar',
    'Refresh': 'Actualizar',
    'Status': 'Estado',
    'Summary': 'Resumen',
    'Coverage': 'Cobertura',
    'Quality': 'Calidad',
    'Confidence': 'Confianza',
    'Risk': 'Riesgo',
    'Bankroll': 'Banca',
    'Market': 'Mercado',
    'League': 'Liga',
    'Team': 'Equipo',
    'Teams': 'Equipos',
    'Matches': 'Partidos',
    'Upcoming': 'Próximos',
    'Recent': 'Recientes',
    'Settings': 'Configuraciones',
    'Health': 'Salud',
    'Alerts': 'Alertas',
    'History': 'Historial',
    'Signals': 'Señales',
    'Simulation': 'Simulación',
    'Live': 'En vivo',
    'Language': 'Idioma',
    'Logout': 'Salir',
    'Search': 'Buscar',
    'Open': 'Abrir',
    'Close': 'Cerrar',
    'Cancel': 'Cancelar',
    'Save': 'Guardar',
    'Loading...': 'Cargando...',
    'No data available yet.': 'Aún no hay datos disponibles.',
    'Next step': 'Siguiente paso',
    'Recommended method': 'Método recomendado',
    'Default credentials': 'Credenciales predeterminadas',
    'Analytics system. It does not place bets automatically.': 'Sistema de análisis. No ejecuta apuestas automáticamente.',
    'Manual confirmation required.': 'Confirmación manual obligatoria.'
  },
};

const ATTRS = ['placeholder', 'aria-label', 'title', 'alt'];
const originals = new WeakMap();
const attrOriginals = new WeakMap();

function normalize(text) { return String(text || '').replace(/\s+/g, ' ').trim(); }

function translateText(text, language) {
  if (!text || language === 'en') return text;
  const map = TEXT_MAP[language] || TEXT_MAP.pt;
  const leading = text.match(/^\s*/)?.[0] || '';
  const trailing = text.match(/\s*$/)?.[0] || '';
  const core = normalize(text);
  if (!core) return text;
  if (map[core]) return `${leading}${map[core]}${trailing}`;
  let translated = core;
  const entries = Object.entries(map).sort((a, b) => b[0].length - a[0].length);
  for (const [from, to] of entries) {
    if (from.length < 4) continue;
    translated = translated.replaceAll(from, to);
  }
  return `${leading}${translated}${trailing}`;
}

function translateNode(root, language) {
  if (!root) return;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      const parent = node.parentElement;
      if (!parent) return NodeFilter.FILTER_REJECT;
      if (['SCRIPT', 'STYLE', 'TEXTAREA', 'CODE'].includes(parent.tagName)) return NodeFilter.FILTER_REJECT;
      if (!normalize(node.nodeValue)) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    },
  });
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  nodes.forEach((node) => {
    if (!originals.has(node)) originals.set(node, node.nodeValue);
    node.nodeValue = translateText(originals.get(node), language);
  });

  root.querySelectorAll?.('*')?.forEach((el) => {
    ATTRS.forEach((attr) => {
      if (!el.hasAttribute(attr)) return;
      let saved = attrOriginals.get(el);
      if (!saved) { saved = {}; attrOriginals.set(el, saved); }
      if (!saved[attr]) saved[attr] = el.getAttribute(attr);
      el.setAttribute(attr, translateText(saved[attr], language));
    });
  });
}

export function TranslationRuntime() {
  const { language } = useApp();
  useEffect(() => {
    const apply = () => translateNode(document.body, language);
    apply();
    const observer = new MutationObserver(() => requestAnimationFrame(apply));
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    return () => observer.disconnect();
  }, [language]);
  return null;
}
