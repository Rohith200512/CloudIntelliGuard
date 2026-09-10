import React, { useState, useEffect } from 'react';
import { 
  Sliders, 
  Zap, 
  TrendingUp, 
  ShieldAlert, 
  ArrowRight, 
  RefreshCw, 
  HelpCircle,
  AlertTriangle
} from 'lucide-react';
import { api } from '../api/client';

export default function WhatIfSimulator({ onNavigate, initialUserId }) {
  const [users, setUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState(initialUserId || '');
  const [toggles, setToggles] = useState({
    unusual_login: false,
    new_ip_location: false,
    privilege_escalation: false,
    abnormal_api_activity: false,
    sensitive_resource_access: false,
    multiple_failed_logins: false,
    coordinated_behavior: false,
    temporal_anomaly: false,
  });

  const [simResult, setSimResult] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const list = await api.listUBAUsers();
      setUsers(list);
      if (list.length > 0) {
        const target = initialUserId && list.some(u => u.cloud_user_id === initialUserId)
          ? initialUserId
          : list[0].cloud_user_id;
        setSelectedUser(target);
        runSimulation(target, toggles);
      }
    } catch (err) {
      console.error('Failed to load users for simulator:', err);
    }
  };

  const handleToggle = (key) => {
    const updated = { ...toggles, [key]: !toggles[key] };
    setToggles(updated);
    runSimulation(selectedUser, updated);
  };

  const runSimulation = async (uid, toggleStates) => {
    if (!uid) return;
    try {
      setLoading(true);
      const res = await api.simulateRisk({
        cloud_user_id: uid,
        ...toggleStates,
      });
      setSimResult(res);
    } catch (err) {
      console.error('Simulation failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    const cleared = {
      unusual_login: false,
      new_ip_location: false,
      privilege_escalation: false,
      abnormal_api_activity: false,
      sensitive_resource_access: false,
      multiple_failed_logins: false,
      coordinated_behavior: false,
      temporal_anomaly: false,
    };
    setToggles(cleared);
    runSimulation(selectedUser, cleared);
  };

  const behaviorControls = [
    {
      key: 'privilege_escalation',
      title: 'Privilege Escalation',
      desc: 'Attempt to attach admin policy or assume higher-privilege IAM roles.',
      impact: '+30 pts (High Driver)',
    },
    {
      key: 'sensitive_resource_access',
      title: 'Sensitive Resource Mutation',
      desc: 'Read or mutate production KMS keys and Secrets Manager secrets.',
      impact: '+20 pts',
    },
    {
      key: 'abnormal_api_activity',
      title: 'Abnormal API Velocity (Burst)',
      desc: 'Request frequency surges to 4x baseline rate within a short window.',
      impact: '+25 pts',
    },
    {
      key: 'multiple_failed_logins',
      title: 'Multiple Failed Auth Attempts',
      desc: 'Simulate 12+ failed authentication or authorization rejections.',
      impact: '+15 pts',
    },
    {
      key: 'new_ip_location',
      title: 'Novel Source IP / Geo Shift',
      desc: 'Session initiated from an unrecognized geographic region or IP prefix.',
      impact: '+12 pts',
    },
    {
      key: 'unusual_login',
      title: 'Unusual Login Pattern',
      desc: 'Session creation bypassing standard SSO or MFA policies.',
      impact: '+10 pts',
    },
    {
      key: 'coordinated_behavior',
      title: 'Coordinated Attack Correlation',
      desc: 'Identity acts synchronously with other flagged suspicious identities.',
      impact: '+15 pts',
    },
    {
      key: 'temporal_anomaly',
      title: 'Off-Hours Activity',
      desc: 'Operations executed at 03:00 AM UTC (outside normal business hours).',
      impact: '+10 pts',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-cyan-400 uppercase tracking-widest font-mono mb-1">
            <Sliders className="w-3.5 h-3.5" />
            Risk Simulation Sandbox
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">What-If Risk Simulator</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Test hypothetical adversarial behaviors on identities to evaluate predicted risk shifts and automated response triggers.
          </p>
        </div>

        {/* Identity Selector & Reset */}
        <div className="flex items-center gap-3">
          <select
            value={selectedUser}
            onChange={(e) => {
              setSelectedUser(e.target.value);
              runSimulation(e.target.value, toggles);
            }}
            className="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-700/80 text-xs font-mono text-cyan-400 focus:outline-none focus:border-cyan-500 font-bold"
          >
            {users.map(u => (
              <option key={u.cloud_user_id} value={u.cloud_user_id}>
                Identity: {u.cloud_user_id}
              </option>
            ))}
          </select>

          <button
            onClick={handleReset}
            className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reset</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Behavior Toggles Panel */}
        <div className="lg:col-span-2 bg-[#090e1a] border border-slate-800/90 rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-white">Hypothetical Adversarial Behaviors</h3>
            <span className="text-[11px] font-mono text-slate-400">Toggle behaviors to evaluate risk</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {behaviorControls.map((ctrl) => {
              const isActive = toggles[ctrl.key];
              return (
                <div
                  key={ctrl.key}
                  onClick={() => handleToggle(ctrl.key)}
                  className={`p-4 rounded-xl border cursor-pointer transition-all flex items-start justify-between gap-3 ${
                    isActive
                      ? 'bg-gradient-to-r from-red-950/60 to-slate-900 border-red-700/80 shadow-md shadow-red-950/30'
                      : 'bg-slate-900/60 hover:bg-slate-800/60 border-slate-800'
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-bold ${isActive ? 'text-red-300' : 'text-slate-200'}`}>
                        {ctrl.title}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-tight">{ctrl.desc}</p>
                    <span className="text-[10px] font-mono text-cyan-400 block pt-1">{ctrl.impact}</span>
                  </div>

                  {/* Toggle Switch */}
                  <div className={`w-10 h-5 rounded-full p-0.5 transition-colors shrink-0 ${
                    isActive ? 'bg-red-500' : 'bg-slate-700'
                  }`}>
                    <div className={`w-4 h-4 rounded-full bg-white transition-transform ${
                      isActive ? 'translate-x-5' : 'translate-x-0'
                    }`} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Simulation Output Card */}
        <div className="bg-[#090e1a] border border-slate-800/90 rounded-2xl p-6 flex flex-col justify-between space-y-6">
          <div>
            <span className="text-xs font-mono uppercase text-slate-400 font-semibold block mb-4">
              Simulation Results & Risk Shift
            </span>

            {simResult ? (
              <div className="space-y-5">
                {/* Score Comparison Meters */}
                <div className="grid grid-cols-2 gap-3 p-4 rounded-xl bg-slate-900/90 border border-slate-800">
                  <div>
                    <span className="text-[10px] font-mono uppercase text-slate-400 block">Baseline Risk</span>
                    <span className="text-2xl font-black text-slate-300">{simResult.current_risk_score.toFixed(1)}</span>
                    <span className="text-[10px] font-mono text-slate-500 block">({simResult.current_risk_level})</span>
                  </div>

                  <div className="border-l border-slate-800 pl-3">
                    <span className="text-[10px] font-mono uppercase text-red-400 font-bold block">Simulated Risk</span>
                    <span className={`text-2xl font-black ${
                      simResult.simulated_risk_score >= 75 ? 'text-red-400' :
                      simResult.simulated_risk_score >= 50 ? 'text-amber-400' : 'text-white'
                    }`}>
                      {simResult.simulated_risk_score.toFixed(1)}
                    </span>
                    <span className="text-[10px] font-mono text-red-400 block">({simResult.simulated_risk_level})</span>
                  </div>
                </div>

                {/* Score Delta Indicator */}
                <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between text-xs">
                  <span className="text-slate-400">Risk Score Change:</span>
                  <span className={`font-mono font-black text-base ${simResult.delta > 0 ? 'text-red-400' : 'text-slate-300'}`}>
                    {simResult.delta > 0 ? `+${simResult.delta.toFixed(1)} pts` : '0.0 pts'}
                  </span>
                </div>

                {/* Automated Response Trigger Notice */}
                {simResult.simulated_risk_score >= 75 ? (
                  <div className="p-3.5 rounded-xl bg-red-950/60 border border-red-800 text-xs text-red-300 space-y-1">
                    <div className="font-bold flex items-center gap-1.5 text-red-400">
                      <ShieldAlert className="w-4 h-4" />
                      CRITICAL POLICY TRIGGERED
                    </div>
                    <p className="text-[11px] text-red-300/90 leading-relaxed">
                      Identity would be <strong>AUTOMATICALLY BLOCKED</strong>, active sessions revoked, and a critical incident created.
                    </p>
                  </div>
                ) : simResult.simulated_risk_score >= 50 ? (
                  <div className="p-3.5 rounded-xl bg-amber-950/60 border border-amber-800 text-xs text-amber-300 space-y-1">
                    <div className="font-bold flex items-center gap-1.5 text-amber-400">
                      <AlertTriangle className="w-4 h-4" />
                      HIGH POLICY TRIGGERED
                    </div>
                    <p className="text-[11px] text-amber-300/90 leading-relaxed">
                      Identity would be <strong>AUTOMATICALLY RESTRICTED</strong> and quarantined from sensitive IAM/KMS operations.
                    </p>
                  </div>
                ) : (
                  <div className="p-3.5 rounded-xl bg-emerald-950/30 border border-emerald-900/60 text-xs text-emerald-400">
                    ✓ Risk remains within standard observation parameters (Monitor Only).
                  </div>
                )}

                {/* Contributor Explanation */}
                <div className="p-3 rounded-xl bg-slate-900/40 border border-slate-800/80 text-[11px] text-slate-400 leading-relaxed">
                  <span className="text-slate-300 font-semibold block mb-0.5">Primary Risk Contributor:</span>
                  {simResult.top_contributor}
                </div>
              </div>
            ) : null}
          </div>

          <button
            onClick={() => onNavigate('response')}
            className="w-full px-3.5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-medium text-slate-200 flex items-center justify-center gap-2"
          >
            <span>Review Policy Rules</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
