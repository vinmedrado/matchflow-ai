export const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';

export function getToken() { return localStorage.getItem('matchflow_token'); }
export function getRefreshToken() { return localStorage.getItem('matchflow_refresh_token'); }
export function setToken(token) { if (token) localStorage.setItem('matchflow_token', token); }
export function setRefreshToken(token) { if (token) localStorage.setItem('matchflow_refresh_token', token); }
export function clearToken() { localStorage.removeItem('matchflow_token'); localStorage.removeItem('matchflow_refresh_token'); }

export async function apiRequest(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const msg = data?.error?.message || data?.detail?.message || data?.detail || 'Falha ao chamar API.';
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }
  return data;
}

export const api = {
  // Auth
  login: (email, password, rememberSession = false) => apiRequest('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password, remember_session: rememberSession }) }),
  register: (payload) => apiRequest('/api/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  refresh: (refreshToken) => apiRequest('/api/auth/refresh', { method: 'POST', body: JSON.stringify({ refresh_token: refreshToken }) }),
  logout: (refreshToken) => apiRequest('/api/auth/logout', { method: 'POST', body: JSON.stringify({ refresh_token: refreshToken }) }),
  forgotPassword: (email) => apiRequest('/api/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email }) }),
  resetPassword: (token, newPassword) => apiRequest('/api/auth/reset-password', { method: 'POST', body: JSON.stringify({ token, new_password: newPassword }) }),
  resendVerification: (email) => apiRequest('/api/auth/resend-verification', { method: 'POST', body: JSON.stringify({ email }) }),
  profile: () => apiRequest('/api/auth/profile'),
  updateProfile: (payload) => apiRequest('/api/auth/profile', { method: 'PATCH', body: JSON.stringify(payload) }),
  me: () => apiRequest('/api/auth/me'),

  // System
  status: () => apiRequest('/api/system/status'),
  summary: () => apiRequest('/api/datasets/summary'),
  quality: () => apiRequest('/api/data-quality/report'),
  ask: (question) => apiRequest('/api/ai/ask', { method: 'POST', body: JSON.stringify({ question }) }),
  aiStatus: () => apiRequest('/api/ai/status'),

  // Backtest
  backtestAnalysis: () => apiRequest('/api/backtest/analysis-summary'),

  // Data Ops
  dataOpsStatus: () => apiRequest('/api/data-ops/status'),
  dataOpsDiscovery: () => apiRequest('/api/data-ops/discovery'),
  dataEngineStatus: () => apiRequest('/api/data-engine/status'),
  demoStatus: () => apiRequest('/api/demo/status'),

  // Test Lab
  testLabStatus: () => apiRequest('/api/test-lab/status'),
  testLabRun: () => apiRequest('/api/test-lab/run', { method: 'POST' }),
  testLabReport: () => apiRequest('/api/test-lab/report'),
  testLabCandidates: () => apiRequest('/api/test-lab/candidates'),

  // ML
  mlCalibration: () => apiRequest('/api/ml/calibration-summary'),
  mlEnsemble: () => apiRequest('/api/ml/ensemble-summary'),


  futureMatchesSnapshot: () => apiRequest('/api/future-matches/snapshot'),
  futurePredictions: () => apiRequest('/api/ml/future-predictions'),
  dataEngineProviders: () => apiRequest('/api/data-engine/providers/status'),
  dataEngineUnresolved: () => apiRequest('/api/data-engine/entities/unresolved'),
  dataEngineConflicts: () => apiRequest('/api/data-engine/entities/conflicts'),
  dataEngineMappingReport: () => apiRequest('/api/data-engine/mapping/report'),
  dataEngineDedupReport: () => apiRequest('/api/data-engine/deduplication/report'),
  dataEngineQualityReport: () => apiRequest('/api/data-engine/quality/report'),
  flashscoreCoverage: () => apiRequest('/api/data-engine/flashscore/coverage'),
  jobs: () => apiRequest('/api/jobs'),
  jobsHistory: () => apiRequest('/api/jobs/history'),
  jobStatus: (jobId) => apiRequest(`/api/jobs/${encodeURIComponent(jobId)}`),
  runJob: (jobName) => apiRequest(`/api/jobs/run/${jobName}`, { method: 'POST' }),
  metrics: () => apiRequest('/metrics'),
  bankrollProfiles: () => apiRequest('/api/bankroll/profiles'),

  // Decision Engine
  decisionEngineSummary: () => apiRequest('/api/decision-engine/summary'),
  decisionEngineCandidates: () => apiRequest('/api/decision-engine/candidates'),
  decisionEngineRun: () => apiRequest('/api/decision-engine/run', { method: 'POST' }),

  // Monitoring
  monitoringStatus: () => apiRequest('/api/monitoring/status'),
  monitoringAlerts: () => apiRequest('/api/monitoring/alerts'),
  monitoringDrift: () => apiRequest('/api/monitoring/drift'),
  calibrationReport: () => apiRequest('/api/ml/calibration/report'),
  modelHealth: () => apiRequest('/api/ml/model-health'),
  evidenceAlerts: () => apiRequest('/api/monitoring/evidence-alerts'),
  realSettledResults: () => apiRequest('/api/results/settled/real'),
  settledResultsSummary: () => apiRequest('/api/results/settled/summary'),
  monitoringAnomalies: () => apiRequest('/api/monitoring/anomalies'),
  monitoringRun: () => apiRequest('/api/monitoring/run', { method: 'POST' }),

  // Automation
  automationStatus: () => apiRequest('/api/automation/status'),
  automationRun: () => apiRequest('/api/automation/run', { method: 'POST' }),
  automationHistory: () => apiRequest('/api/automation/history'),
  automationReport: () => apiRequest('/api/automation/report'),

  // Paper Trading (v7)
  paperTradingSummary: () => apiRequest('/api/paper-trading/summary'),
  paperTradingSignals: () => apiRequest('/api/paper-trading/signals'),

  // Performance & Analytics (v7)
  performanceMonteCarlo: (params) => apiRequest('/api/performance/monte-carlo', {
    method: 'POST', body: JSON.stringify(params),
  }),
  performanceAttribution: () => apiRequest('/api/performance/attribution'),
  performanceClv: (days = 30) => apiRequest(`/api/performance/clv?days=${days}`),
  performanceSettle: () => apiRequest('/api/performance/settle', { method: 'POST' }),

  // Engine Runner (v7)
  engineStatus: () => apiRequest('/api/data-ops/engine-status'),
  engineRun: (mode='incremental', days=7) => apiRequest(`/api/data-ops/engine-run?mode=${mode}&days_back=${days}`, { method: 'POST' }),
  bridgeStatus: () => apiRequest('/api/data-ops/bridge-status'),

  // Operational guide / SaaS blueprint
  operationalBlueprint: () => apiRequest('/api/operational-guide/blueprint'),
  operationalStep: (stepId) => apiRequest(`/api/operational-guide/step/${stepId}`),

  // Product ERP additions
  competitionsOverview: () => apiRequest('/api/competitions/overview'),
  competitionDetail: (league) => apiRequest(`/api/competitions/detail?league=${encodeURIComponent(league)}`),
  productAudit: () => apiRequest('/api/product/audit'),
  backtestHealth: () => apiRequest('/api/product/backtest-health'),
  bankrollPolicy: (bankroll = 1000, risk = 'balanced') => apiRequest(`/api/product/bankroll-policy?bankroll=${bankroll}&risk_profile=${risk}`),


  // Product platform / SaaS evolution
  platformCockpit: () => apiRequest('/api/platform/cockpit'),
  platformDataCenter: () => apiRequest('/api/platform/data-center'),
  platformBacktestIntelligence: () => apiRequest('/api/platform/backtest-intelligence'),
  platformMLIntelligence: () => apiRequest('/api/platform/ml-intelligence'),
  platformRiskEngine: (bankroll = 1000, risk = 'balanced') => apiRequest(`/api/platform/risk-engine?bankroll=${bankroll}&risk_profile=${risk}`),
  platformJobsCenter: () => apiRequest('/api/platform/jobs-center'),
  platformDemoMode: () => apiRequest('/api/platform/demo-mode'),

  platformMissionControl: () => apiRequest('/api/platform/mission-control'),
  platformApiCatalog: () => apiRequest('/api/platform/api-catalog'),
  platformUserWorkspace: () => apiRequest('/api/platform/user-workspace'),
  platformSalesReadiness: () => apiRequest('/api/platform/sales-readiness'),

  platformOnboardingRoadmap: () => apiRequest('/api/platform/onboarding-roadmap'),
  platformDecisionRoom: () => apiRequest('/api/platform/decision-room'),
  platformStrategyStudio: (bankroll = 1000, risk = 'balanced') => apiRequest(`/api/platform/strategy-studio?bankroll=${bankroll}&risk_profile=${risk}`),
  platformSaasMaturity: () => apiRequest('/api/platform/saas-maturity'),

  // Premium AI-first platform patch
  premiumCopilot: () => apiRequest('/api/premium/copilot'),
  premiumLiveCenter: () => apiRequest('/api/premium/live-center'),
  premiumExplainability: () => apiRequest('/api/premium/explainability'),
  premiumPaper: () => apiRequest('/api/premium/paper-premium'),
  premiumAnalytics: () => apiRequest('/api/premium/analytics'),

  // AI Brain / live intelligence
  intelligenceBrain: () => apiRequest('/api/intelligence/brain'),
  intelligenceAsk: (question) => apiRequest('/api/intelligence/ask', { method: 'POST', body: JSON.stringify({ question }) }),
  intelligenceAlerts: () => apiRequest('/api/intelligence/alerts'),
  intelligenceMemory: () => apiRequest('/api/intelligence/memory'),
  intelligenceDiagnostics: () => apiRequest('/api/intelligence/diagnostics'),

  // Agentic autonomous intelligence
  agentsCockpit: () => apiRequest('/api/agents/cockpit'),
  agentsCoordinate: (task = 'continuous_operational_review') => apiRequest('/api/agents/coordinate', { method: 'POST', body: JSON.stringify({ task }) }),
  agentsDecision: () => apiRequest('/api/agents/decision'),
  agentsResearch: () => apiRequest('/api/agents/research'),
  agentsOptimization: () => apiRequest('/api/agents/optimization'),
  agentsDiagnostics: () => apiRequest('/api/agents/diagnostics'),

  // Goal-driven Autonomous AI Operating System
  autonomousWorkspace: () => apiRequest('/api/autonomous/workspace'),
  autonomousGoals: () => apiRequest('/api/autonomous/goals'),
  autonomousPlanning: () => apiRequest('/api/autonomous/planning'),
  autonomousWorkflows: () => apiRequest('/api/autonomous/workflows'),
  autonomousMemoryGraph: () => apiRequest('/api/autonomous/memory-graph'),
  autonomousSimulations: () => apiRequest('/api/autonomous/simulations'),
  autonomousDecision: () => apiRequest('/api/autonomous/decision'),
  autonomousAsk: (question) => apiRequest('/api/autonomous/ask', { method: 'POST', body: JSON.stringify({ question }) }),

  // Cognitive Autonomous AI OS
  cognitiveWorkspace: () => apiRequest('/api/cognitive/workspace'),
  cognitiveWorldModel: () => apiRequest('/api/cognitive/world-model'),
  cognitiveMetaReasoning: () => apiRequest('/api/cognitive/meta-reasoning'),
  cognitiveUncertainty: () => apiRequest('/api/cognitive/uncertainty'),
  cognitiveKnowledge: () => apiRequest('/api/cognitive/knowledge'),
  cognitiveDecision: () => apiRequest('/api/cognitive/decision'),
  cognitiveAsk: (question) => apiRequest('/api/cognitive/ask', { method: 'POST', body: JSON.stringify({ question }) }),

  // Executive Cognitive Autonomous AI OS
  executiveWorkspace: () => apiRequest('/api/executive/workspace'),
  executiveSummary: () => apiRequest('/api/executive/summary'),
  executiveDecisionBoard: () => apiRequest('/api/executive/decision-board'),
  executiveGovernance: () => apiRequest('/api/executive/governance'),
  executiveExperiments: () => apiRequest('/api/executive/experiments'),
  executiveReflections: () => apiRequest('/api/executive/reflections'),
  executiveObservability: () => apiRequest('/api/executive/observability'),
  executiveAsk: (question) => apiRequest('/api/executive/ask', { method: 'POST', body: JSON.stringify({ question }) }),

  // Self-Evolving Executive Cognitive AI System
  evolutionWorkspace: () => apiRequest('/api/evolution/workspace'),
  evolutionRecursiveImprovement: () => apiRequest('/api/evolution/recursive-improvement'),
  evolutionMetaLearning: () => apiRequest('/api/evolution/meta-learning'),
  evolutionSelfPreservation: () => apiRequest('/api/evolution/self-preservation'),
  evolutionObservability: () => apiRequest('/api/evolution/observability'),
  evolutionAsk: (question) => apiRequest('/api/evolution/ask', { method: 'POST', body: JSON.stringify({ question }) }),

};
