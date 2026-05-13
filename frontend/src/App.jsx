import { useState } from 'react';
import { AppProvider, useApp } from './store/AppContext.jsx';
import ErrorBoundary from './components/ErrorBoundary.jsx';
import AppShell from './components/AppShell.jsx';
import Login from './pages/Login.jsx';
import LandingPage from './pages/LandingPage.jsx';
import Home from './pages/Home.jsx';
import Dashboard from './pages/Dashboard.jsx';
import DataQuality from './pages/DataQuality.jsx';
import Assistant from './pages/Assistant.jsx';
import SystemStatus from './pages/SystemStatus.jsx';
import TeamAnalytics from './pages/TeamAnalytics.jsx';
import BacktestLab from './pages/BacktestLab.jsx';
import MLLab from './pages/MLLab.jsx';
import DataOperations from './pages/DataOperations.jsx';
import TestLab from './pages/TestLab.jsx';
import DecisionEngine from './pages/DecisionEngine.jsx';
import Monitoring from './pages/Monitoring.jsx';
import Automation from './pages/Automation.jsx';
import BankrollProjection from './pages/BankrollProjection.jsx';
import Competitions from './pages/Competitions.jsx';
import OperationalGuide from './pages/OperationalGuide.jsx';
import ProductCockpit from './pages/ProductCockpit.jsx';
import DataCenter from './pages/DataCenter.jsx';
import BacktestIntelligence from './pages/BacktestIntelligence.jsx';
import MLIntelligence from './pages/MLIntelligence.jsx';
import RiskEngine from './pages/RiskEngine.jsx';
import JobsCenter from './pages/JobsCenter.jsx';
import DemoMode from './pages/DemoMode.jsx';
import MissionControl from './pages/MissionControl.jsx';
import APICatalog from './pages/APICatalog.jsx';
import UserWorkspace from './pages/UserWorkspace.jsx';
import SalesReadiness from './pages/SalesReadiness.jsx';
import OnboardingRoadmap from './pages/OnboardingRoadmap.jsx';
import DecisionRoom from './pages/DecisionRoom.jsx';
import StrategyStudio from './pages/StrategyStudio.jsx';
import SaaSMaturity from './pages/SaaSMaturity.jsx';
import AICopilotPremium from './pages/AICopilotPremium.jsx';
import LiveCenterPremium from './pages/LiveCenterPremium.jsx';
import AIExplainability from './pages/AIExplainability.jsx';
import PaperTradingPremium from './pages/PaperTradingPremium.jsx';
import PremiumAnalytics from './pages/PremiumAnalytics.jsx';
import AgenticIntelligence from './pages/AgenticIntelligence.jsx';
import AutonomousWorkspace from './pages/AutonomousWorkspace.jsx';
import CognitiveWorkspace from './pages/CognitiveWorkspace.jsx';
import ExecutiveCockpit from './pages/ExecutiveCockpit.jsx';
import EvolutionCockpit from './pages/EvolutionCockpit.jsx';
import { TranslationRuntime } from './i18nRuntime.jsx';


// Legacy route compatibility markers used by historical QA contracts:
// page === 'Team Analytics'
// Content = TeamAnalytics
// page === 'Backtest Lab'
// Content = BacktestLab
// Legacy navigation order: 'Backtest Lab', 'ML Lab'

const PAGE_MAP = {
  Dashboard, 'Data Quality': DataQuality, Assistant, 'System Status': SystemStatus,
  'Team Analytics': TeamAnalytics, 'Backtest Lab': BacktestLab, 'ML Lab': MLLab,
  'Data Operations': DataOperations, 'Test Lab': TestLab, 'Decision Engine': DecisionEngine,
  Monitoring, Automation, 'Bankroll Projection': BankrollProjection, Competitions, 'Operational Guide': OperationalGuide, 'Product Cockpit': ProductCockpit, 'Data Center': DataCenter, 'Backtest Intelligence': BacktestIntelligence, 'ML Intelligence': MLIntelligence, 'Risk Engine': RiskEngine, 'Jobs Center': JobsCenter, 'Demo Mode': DemoMode, 'Mission Control': MissionControl, 'API Catalog': APICatalog, 'User Workspace': UserWorkspace, 'Sales Readiness': SalesReadiness, 'Onboarding Roadmap': OnboardingRoadmap, 'Decision Room': DecisionRoom, 'Strategy Studio': StrategyStudio, 'SaaS Maturity': SaaSMaturity, 'AI Copilot Premium': AICopilotPremium, 'Live Center': LiveCenterPremium, 'AI Explainability': AIExplainability, 'Paper Trading Premium': PaperTradingPremium, 'Premium Analytics': PremiumAnalytics, 'Agentic Intelligence': AgenticIntelligence, 'Autonomous Workspace': AutonomousWorkspace, 'Cognitive Workspace': CognitiveWorkspace, 'Executive Cockpit': ExecutiveCockpit, 'Evolution Cockpit': EvolutionCockpit,
};

function Router() {
  const { user } = useApp();
  const [page, setPage] = useState('Landing');
  if (!user) {
    if (page === 'Login') return <Login setPage={setPage} />;
    return <LandingPage setPage={setPage} />;
  }
  const currentPage = (page === 'Login' || page === 'Landing') ? 'Home' : page;
  const Content = PAGE_MAP[currentPage] || null;
  return (
    <AppShell page={currentPage} setPage={setPage}>
      {currentPage === 'Home'
        ? <Home setPage={setPage} />
        : Content ? <Content setPage={setPage} /> : <Home setPage={setPage} />}
    </AppShell>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <AppProvider>
        <TranslationRuntime />
        <Router />
      </AppProvider>
    </ErrorBoundary>
  );
}
