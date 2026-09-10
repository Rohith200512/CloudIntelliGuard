import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import Login from './pages/Login';

// 9 Purpose-Driven SOC Pages + Datasets
import Overview from './pages/Overview';
import DynamicGraph from './pages/DynamicGraph';
import UserBehaviorAnalytics from './pages/UserBehaviorAnalytics';
import ThreatDetection from './pages/ThreatDetection';
import AttackPathAnalysis from './pages/AttackPathAnalysis';
import WhatIfSimulator from './pages/WhatIfSimulator';
import AICopilot from './pages/AICopilot';
import AutomatedResponse from './pages/AutomatedResponse';
import AuditLog from './pages/AuditLog';
import Datasets from './pages/Datasets';

import { api } from './api/client';

function AppContent() {
  const { isAuthenticated, loading } = useAuth();
  const [activeTab, setActiveTab] = useState('overview');
  const [navParams, setNavParams] = useState({});
  const [alertsCount, setAlertsCount] = useState(0);

  useEffect(() => {
    if (isAuthenticated) {
      api.listAlerts(true)
        .then((alerts) => setAlertsCount(alerts.length))
        .catch(() => {});
    }
  }, [isAuthenticated, activeTab]);

  const handleNavigate = (tabId, params = {}) => {
    setActiveTab(tabId);
    setNavParams(params);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#07090e] flex items-center justify-center text-cyan-400 font-mono text-xs">
        Initializing CloudIntelliGuard Enterprise SOC Console...
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Login />;
  }

  const renderContent = () => {
    switch (activeTab) {
      case 'overview':
        return <Overview onNavigate={handleNavigate} />;
      case 'dynamic_graph':
        return <DynamicGraph onNavigate={handleNavigate} initialUserId={navParams.userId} />;
      case 'uba':
        return <UserBehaviorAnalytics onNavigate={handleNavigate} initialUserId={navParams.userId} />;
      case 'threats':
        return <ThreatDetection onNavigate={handleNavigate} />;
      case 'attack_path':
        return <AttackPathAnalysis onNavigate={handleNavigate} initialUserId={navParams.userId} />;
      case 'simulator':
        return <WhatIfSimulator onNavigate={handleNavigate} initialUserId={navParams.userId} />;
      case 'copilot':
        return <AICopilot onNavigate={handleNavigate} initialQuery={navParams.query} />;
      case 'response':
        return <AutomatedResponse onNavigate={handleNavigate} />;
      case 'audit':
        return <AuditLog onNavigate={handleNavigate} />;
      case 'datasets':
        return <Datasets onNavigate={handleNavigate} />;
      default:
        return <Overview onNavigate={handleNavigate} />;
    }
  };

  return (
    <div className="min-h-screen bg-[#07090e] text-slate-100 flex flex-col font-sans">
      <Navbar activeAlertsCount={alertsCount} onNavigate={handleNavigate} />
      <div className="flex flex-1">
        <Sidebar activeTab={activeTab} onSelectTab={(tab) => handleNavigate(tab)} />
        <main className="flex-1 p-6 md:p-8 overflow-y-auto max-w-7xl mx-auto w-full">
          {renderContent()}
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
