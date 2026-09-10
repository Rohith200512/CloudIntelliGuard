import React, { useState, useEffect } from 'react';
import { 
  Zap, 
  ShieldCheck, 
  Lock, 
  UserX, 
  AlertTriangle, 
  RefreshCw, 
  CheckCircle, 
  Info,
  Clock,
  ArrowRight
} from 'lucide-react';
import { api } from '../api/client';

export default function AutomatedResponse({ onNavigate }) {
  const [enforcements, setEnforcements] = useState([]);
  const [policySummary, setPolicySummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [selectedUserForOverride, setSelectedUserForOverride] = useState(null);
  const [overrideAction, setOverrideAction] = useState('RESTORE');
  const [overrideReason, setOverrideReason] = useState('Analyst verified legitimate activity');

  useEffect(() => {
    loadEnforcements();
  }, []);

  const loadEnforcements = async () => {
    try {
      setLoading(true);
      const [list, sum] = await Promise.all([
        api.listEnforcements(),
        api.getPolicySummary(),
      ]);
      setEnforcements(list);
      setPolicySummary(sum);
    } catch (err) {
      console.error('Failed to load enforcements:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleExecuteOverride = async () => {
    if (!selectedUserForOverride) return;
    try {
      setActionLoading(true);
      await api.overrideEnforcement(
        selectedUserForOverride.cloud_user_id,
        overrideAction,
        overrideReason
      );
      setSelectedUserForOverride(null);
      await loadEnforcements();
    } catch (err) {
      alert(`Override failed: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400 uppercase tracking-widest font-mono mb-1">
            <Zap className="w-3.5 h-3.5" />
            Autonomous Mitigation Engine
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Automated Response</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Risk-driven autonomous mitigation policy. Automatically quarantines HIGH-risk and locks CRITICAL-risk cloud identities.
          </p>
        </div>

        <button
          onClick={loadEnforcements}
          className="px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-xs text-slate-300 flex items-center gap-2"
        >
          <RefreshCw className="w-3.5 h-3.5 text-cyan-400" />
          <span>Refresh State</span>
        </button>
      </div>

      {/* Autonomous Policy Matrix */}
      <div className="bg-[#090e1a] border border-slate-800/90 rounded-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white">Active Autonomous Response Policy Matrix</h3>
          <span className="text-[11px] font-mono text-emerald-400 font-bold">Policy Mode: Real-Time Auto-Enforce</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-900/40 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold font-mono text-emerald-400">LOW (0–24)</span>
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
            </div>
            <p className="text-xs font-bold text-white">Monitor Only</p>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Standard continuous behavioral tracking. No access restrictions applied.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-blue-950/20 border border-blue-900/40 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold font-mono text-blue-400">MEDIUM (25–49)</span>
              <AlertTriangle className="w-4 h-4 text-blue-400" />
            </div>
            <p className="text-xs font-bold text-white">Alert & Track</p>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Dispatches operational alerts to SOC console; escalates sampling frequency.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-900/40 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold font-mono text-amber-400">HIGH (50–74)</span>
              <Lock className="w-4 h-4 text-amber-400" />
            </div>
            <p className="text-xs font-bold text-amber-300">Auto-RESTRICT Identity</p>
            <p className="text-[11px] text-amber-300/80 leading-relaxed">
              Quarantines high-privilege IAM/KMS operations, records automated audit event.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-red-950/20 border border-red-900/40 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold font-mono text-red-400">CRITICAL (75+)</span>
              <UserX className="w-4 h-4 text-red-400" />
            </div>
            <p className="text-xs font-bold text-red-300">Auto-BLOCK & Revoke Session</p>
            <p className="text-[11px] text-red-300/80 leading-relaxed">
              Revokes active session tokens, blocks all API access, creates critical incident.
            </p>
          </div>
        </div>
      </div>

      {/* Live Enforcements Management Table */}
      <div className="bg-[#090e1a] border border-slate-800/90 rounded-2xl overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-white">Identity Enforcement Registry ({enforcements.length})</h3>
            <p className="text-xs text-slate-400">Live security state of monitored cloud identities.</p>
          </div>
          <button
            onClick={() => onNavigate('audit')}
            className="text-xs text-cyan-400 hover:text-cyan-300 font-mono flex items-center gap-1"
          >
            <span>View Audit Log</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        {loading ? (
          <div className="py-20 text-center text-cyan-400 font-mono text-sm">
            Loading active enforcements...
          </div>
        ) : enforcements.length === 0 ? (
          <div className="py-16 text-center text-slate-500 text-xs">
            No identities evaluated yet. Run inference on a dataset to trigger automated response evaluation.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="text-[11px] font-mono uppercase bg-slate-900/80 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="p-3.5">Enforcement Status</th>
                  <th className="p-3.5">Cloud Identity</th>
                  <th className="p-3.5">Risk Score</th>
                  <th className="p-3.5">Session State</th>
                  <th className="p-3.5">Enforcement Reason</th>
                  <th className="p-3.5">Last Evaluated</th>
                  <th className="p-3.5 text-right">Analyst Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                {enforcements.map((enf) => {
                  const isBlocked = enf.status === 'BLOCKED';
                  const isRestricted = enf.status === 'RESTRICTED';

                  return (
                    <tr key={enf.id} className="hover:bg-slate-800/40">
                      <td className="p-3.5">
                        <span className={`px-2.5 py-1 rounded font-bold text-[10px] ${
                          isBlocked ? 'bg-red-950 text-red-300 border border-red-800' :
                          isRestricted ? 'bg-amber-950 text-amber-300 border border-amber-800' :
                          'bg-emerald-950/60 text-emerald-300 border border-emerald-800/60'
                        }`}>
                          {enf.status}
                        </span>
                      </td>

                      <td className="p-3.5">
                        <span className="font-bold text-white text-xs">{enf.cloud_user_id}</span>
                      </td>

                      <td className="p-3.5">
                        <span className={`font-bold ${
                          enf.risk_score >= 75 ? 'text-red-400' :
                          enf.risk_score >= 50 ? 'text-amber-400' : 'text-slate-300'
                        }`}>
                          {enf.risk_score.toFixed(1)}/100
                        </span>
                      </td>

                      <td className="p-3.5">
                        {enf.session_revoked ? (
                          <span className="text-red-400 font-bold flex items-center gap-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-ping" />
                            REVOKED
                          </span>
                        ) : (
                          <span className="text-emerald-400">Active</span>
                        )}
                      </td>

                      <td className="p-3.5 font-sans text-slate-300 max-w-xs truncate">
                        {enf.blocking_reason || enf.restriction_reason || 'Standard observation baseline'}
                      </td>

                      <td className="p-3.5 text-slate-400">
                        {new Date(enf.last_evaluated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </td>

                      <td className="p-3.5 text-right">
                        <button
                          onClick={() => {
                            setSelectedUserForOverride(enf);
                            setOverrideAction(isBlocked || isRestricted ? 'RESTORE' : 'BLOCK');
                          }}
                          className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-cyan-300 font-sans text-[11px] font-medium"
                        >
                          Manual Action
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Manual Override Modal */}
      {selectedUserForOverride && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#090e1a] border border-slate-700 p-6 rounded-2xl max-w-md w-full space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-white">Manual Enforcement Override</h3>
            <p className="text-xs text-slate-400">
              Update security enforcement status for identity: <span className="text-cyan-400 font-mono font-bold">{selectedUserForOverride.cloud_user_id}</span>
            </p>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Target Action:</label>
                <select
                  value={overrideAction}
                  onChange={(e) => setOverrideAction(e.target.value)}
                  className="w-full p-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-200 font-mono"
                >
                  <option value="RESTORE">RESTORE (Unblock / Active)</option>
                  <option value="RESTRICT">RESTRICT (Quarantine Sensitive IAM)</option>
                  <option value="BLOCK">BLOCK (Revoke Credentials / Lock)</option>
                </select>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Analyst Justification / Reason:</label>
                <textarea
                  rows={2}
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  className="w-full p-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-200"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setSelectedUserForOverride(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-medium hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteOverride}
                disabled={actionLoading}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white text-xs font-semibold"
              >
                {actionLoading ? 'Applying...' : 'Confirm Override'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
