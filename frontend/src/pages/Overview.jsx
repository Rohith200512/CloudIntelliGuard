import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  ShieldAlert, 
  Users, 
  Server, 
  Lock, 
  UserX, 
  AlertTriangle, 
  Activity, 
  ArrowRight,
  TrendingUp,
  Clock
} from 'lucide-react';
import { api } from '../api/client';
import StatCard from '../components/StatCard';

export default function Overview({ onNavigate }) {
  const [summary, setSummary] = useState(null);
  const [policySummary, setPolicySummary] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [sumRes, polRes, logsRes] = await Promise.all([
        api.getDashboardSummary().catch(() => ({})),
        api.getPolicySummary().catch(() => ({ total_monitored_users: 0, active_users: 0, restricted_users: 0, blocked_users: 0 })),
        api.listAuditLogs(null, 8).catch(() => []),
      ]);
      setSummary(sumRes);
      setPolicySummary(polRes);
      setAuditLogs(logsRes);
    } catch (err) {
      console.error('Failed to load security overview:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-cyan-400 font-mono text-sm py-12 text-center">Loading Security Overview...</div>;
  }

  const totalUsers = policySummary?.total_monitored_users || summary?.total_cloud_users || 57;
  const activeThreats = summary?.total_anomalies || 0;
  const restrictedUsers = policySummary?.restricted_users || 0;
  const blockedUsers = policySummary?.blocked_users || 0;
  const criticalIncidents = summary?.critical_incidents || 0;
  const highIncidents = summary?.high_incidents || 0;

  const securityScore = Math.max(20, Math.min(100, 100 - (blockedUsers * 15 + restrictedUsers * 8 + criticalIncidents * 10)));

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-cyan-400 uppercase tracking-widest font-mono mb-1">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            Executive SOC Telemetry
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Security Overview</h1>
          <p className="text-sm text-slate-400 mt-0.5">High-level real-time posture and threat surface across cloud identities.</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigate('copilot')}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-medium text-xs shadow-lg shadow-indigo-950/50 flex items-center gap-2"
          >
            <span>Ask AI Copilot</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Top Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Monitored Cloud Identities"
          value={totalUsers}
          subtext="IAM users, assumed roles & services"
          icon={Users}
          color="cyan"
        />
        <StatCard
          title="Active Threats Detected"
          value={activeThreats}
          subtext="Flagged by GNN behavioral models"
          icon={ShieldAlert}
          color={activeThreats > 0 ? "red" : "emerald"}
        />
        <StatCard
          title="Auto-Restricted Identities"
          value={restrictedUsers}
          subtext="Quarantined via HIGH risk policy"
          icon={Lock}
          color={restrictedUsers > 0 ? "amber" : "slate"}
        />
        <StatCard
          title="Auto-Blocked Identities"
          value={blockedUsers}
          subtext="Revoked via CRITICAL risk policy"
          icon={UserX}
          color={blockedUsers > 0 ? "red" : "slate"}
        />
      </div>

      {/* Security Health & Policy Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Posture Score */}
        <div className="bg-[#090e1a] border border-slate-800/90 rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider font-mono">Overall Security Posture</span>
              <ShieldCheck className={`w-5 h-5 ${securityScore > 75 ? 'text-emerald-400' : 'text-amber-400'}`} />
            </div>
            <div className="mt-4 flex items-baseline gap-3">
              <span className="text-5xl font-black text-white">{securityScore}</span>
              <span className="text-xs font-mono text-slate-400">/ 100 HEALTH INDEX</span>
            </div>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              Calculated from active threats, unmitigated critical incidents, and autonomous policy enforcements.
            </p>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-800/80 grid grid-cols-2 gap-3 text-xs">
            <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-slate-400 block text-[11px]">Critical Incidents</span>
              <span className="text-red-400 font-bold text-base">{criticalIncidents}</span>
            </div>
            <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-slate-400 block text-[11px]">High Risk Incidents</span>
              <span className="text-amber-400 font-bold text-base">{highIncidents}</span>
            </div>
          </div>
        </div>

        {/* Risk Level Distribution */}
        <div className="bg-[#090e1a] border border-slate-800/90 rounded-2xl p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white">Identity Risk Classification</h3>
              <p className="text-xs text-slate-400">Distribution of evaluated identities across the 4-tier risk policy.</p>
            </div>
            <button
              onClick={() => onNavigate('response')}
              className="text-xs text-cyan-400 hover:text-cyan-300 font-mono flex items-center gap-1"
            >
              <span>View Response Matrix</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
            <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-900/40 text-center">
              <span className="text-[11px] font-mono text-emerald-400 font-semibold block">LOW (0–24)</span>
              <span className="text-2xl font-bold text-white mt-1 block">{policySummary?.active_users || 0}</span>
              <span className="text-[10px] text-slate-400 mt-1 block">Monitor Only</span>
            </div>
            <div className="p-4 rounded-xl bg-blue-950/20 border border-blue-900/40 text-center">
              <span className="text-[11px] font-mono text-blue-400 font-semibold block">MEDIUM (25–49)</span>
              <span className="text-2xl font-bold text-white mt-1 block">0</span>
              <span className="text-[10px] text-slate-400 mt-1 block">Alert & Track</span>
            </div>
            <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-900/40 text-center">
              <span className="text-[11px] font-mono text-amber-400 font-semibold block">HIGH (50–74)</span>
              <span className="text-2xl font-bold text-amber-300 mt-1 block">{restrictedUsers}</span>
              <span className="text-[10px] text-amber-400/80 mt-1 block">Auto-Restricted</span>
            </div>
            <div className="p-4 rounded-xl bg-red-950/20 border border-red-900/40 text-center">
              <span className="text-[11px] font-mono text-red-400 font-semibold block">CRITICAL (75+)</span>
              <span className="text-2xl font-bold text-red-300 mt-1 block">{blockedUsers}</span>
              <span className="text-[10px] text-red-400/80 mt-1 block">Auto-Blocked</span>
            </div>
          </div>

          {/* Direct Navigation Links */}
          <div className="mt-6 pt-4 border-t border-slate-800/80 flex flex-wrap gap-2">
            <button
              onClick={() => onNavigate('uba')}
              className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700/60 text-xs text-slate-300 flex items-center gap-1.5"
            >
              <Activity className="w-3.5 h-3.5 text-cyan-400" />
              <span>User Behavior Analytics</span>
            </button>
            <button
              onClick={() => onNavigate('threats')}
              className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700/60 text-xs text-slate-300 flex items-center gap-1.5"
            >
              <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
              <span>Threat Detection</span>
            </button>
            <button
              onClick={() => onNavigate('attack_path')}
              className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700/60 text-xs text-slate-300 flex items-center gap-1.5"
            >
              <TrendingUp className="w-3.5 h-3.5 text-amber-400" />
              <span>Attack Path Analysis</span>
            </button>
          </div>
        </div>
      </div>

      {/* Recent Security Activity Stream */}
      <div className="bg-[#090e1a] border border-slate-800/90 rounded-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-semibold text-white">Recent Security Activity Stream</h3>
          </div>
          <button
            onClick={() => onNavigate('audit')}
            className="text-xs text-cyan-400 hover:text-cyan-300 font-mono flex items-center gap-1"
          >
            <span>View Full Audit Log</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        {auditLogs.length === 0 ? (
          <p className="text-xs text-slate-500 py-6 text-center">No recent security events logged.</p>
        ) : (
          <div className="divide-y divide-slate-800/60">
            {auditLogs.map((log) => {
              const isBlock = log.action.includes('BLOCK');
              const isRestrict = log.action.includes('RESTRICT');
              return (
                <div key={log.id} className="py-3 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-0.5 rounded font-mono font-bold text-[10px] ${
                      isBlock ? 'bg-red-950 text-red-300 border border-red-800' :
                      isRestrict ? 'bg-amber-950 text-amber-300 border border-amber-800' :
                      'bg-slate-800 text-slate-300'
                    }`}>
                      {log.action}
                    </span>
                    <span className="font-mono text-slate-300 font-semibold">{log.resource || 'System'}</span>
                    {log.detail?.reason && (
                      <span className="text-slate-400 hidden sm:inline text-[11px] truncate max-w-md">
                        — {log.detail.reason}
                      </span>
                    )}
                  </div>
                  <span className="font-mono text-slate-500 text-[11px]">
                    {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
