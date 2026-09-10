import React, { useEffect, useState } from 'react';
import { Radio, AlertCircle, CheckCircle, ShieldCheck, Clock, RefreshCw, AlertTriangle } from 'lucide-react';
import { api } from '../api/client';

export default function Incidents() {
  const [incidents, setIncidents] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [updatingId, setUpdatingId] = useState(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const [incList, alertList] = await Promise.all([
        api.listIncidents(),
        api.listAlerts(false),
      ]);
      setIncidents(incList);
      setAlerts(alertList);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleAcknowledge = async (alertId) => {
    try {
      await api.acknowledgeAlert(alertId);
      await loadData();
    } catch (err) {
      alert(`Failed to acknowledge alert: ${err.message}`);
    }
  };

  const handleUpdateStatus = async (incidentId, newStatus) => {
    setUpdatingId(incidentId);
    try {
      await api.updateIncidentStatus(incidentId, newStatus, 'Status updated from security console.');
      await loadData();
    } catch (err) {
      alert(`Failed to update status: ${err.message}`);
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Radio className="w-5 h-5 text-indigo-400" />
            Incidents & Alert Response Sandbox
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Triage active threats, acknowledge high-priority alerts, and review simulation-only policy recommendations.
          </p>
        </div>

        <button
          onClick={loadData}
          className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300 border border-slate-700 flex items-center gap-1.5"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Alerts Queue */}
        <div className="p-6 rounded-2xl bg-[#0c101b] border border-slate-800 shadow-md">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider mb-4 flex items-center justify-between">
            <span className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400" />
              Real-time Alert Queue ({alerts.length})
            </span>
            <span className="text-[11px] text-slate-400 font-mono">
              {alerts.filter(a => !a.acknowledged).length} Unacknowledged
            </span>
          </h2>

          <div className="space-y-3 max-h-[450px] overflow-y-auto pr-1">
            {alerts.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-500">
                No alerts in queue.
              </div>
            ) : (
              alerts.map((al) => (
                <div
                  key={al.id}
                  className={`p-4 rounded-xl border transition-all ${
                    al.acknowledged
                      ? 'bg-slate-900/40 border-slate-800/60 opacity-60'
                      : 'bg-rose-950/20 border-rose-800/40 shadow-sm'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase ${
                          al.severity === 'CRITICAL' || al.severity === 'HIGH'
                            ? 'bg-rose-950 text-rose-300 border border-rose-800'
                            : 'bg-amber-950 text-amber-300 border border-amber-800'
                        }`}>
                          {al.severity}
                        </span>
                        <span className="font-mono text-xs font-bold text-white uppercase">User {al.cloud_user_id}</span>
                      </div>
                      <p className="text-xs text-slate-300">{al.message}</p>
                      <p className="text-[10px] text-slate-500 mt-1.5 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(al.created_at).toLocaleString()}
                      </p>
                    </div>

                    {!al.acknowledged && (
                      <button
                        onClick={() => handleAcknowledge(al.id)}
                        className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-cyan-300 border border-slate-700 font-medium whitespace-nowrap"
                      >
                        Acknowledge
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Security Incidents & Recommendations */}
        <div className="p-6 rounded-2xl bg-[#0c101b] border border-slate-800 shadow-md">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider mb-4 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            Security Incidents & Recommendations
          </h2>

          <div className="space-y-4 max-h-[450px] overflow-y-auto pr-1">
            {incidents.length === 0 ? (
              <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 text-center text-xs text-slate-400">
                <p className="font-semibold text-slate-300 mb-1">Simulated Threat Response</p>
                <p className="text-slate-500 leading-relaxed mb-3">
                  When anomalies are converted to incidents, rule-based recommendations are generated with strict <code className="text-cyan-400 font-mono">is_simulation_only=True</code> tags.
                </p>
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800/80 text-left font-mono text-[11px] text-slate-400 space-y-1">
                  <p className="text-cyan-400 font-bold">1. Revoke temporary IAM session tokens</p>
                  <p className="text-amber-400">2. Enforce MFA challenge on next API request</p>
                  <p className="text-emerald-400">3. Isolate EC2 security group (dry-run only)</p>
                </div>
              </div>
            ) : (
              incidents.map((inc) => (
                <div key={inc.id} className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold text-sm text-white">{inc.title}</h3>
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono uppercase bg-rose-950 text-rose-300 border border-rose-800">
                      {inc.severity}
                    </span>
                  </div>

                  <p className="text-xs text-slate-400">{inc.explanation}</p>

                  <div className="flex items-center justify-between pt-2 border-t border-slate-800 text-xs">
                    <span className="text-slate-400">Status: <strong className="text-white uppercase font-mono">{inc.status}</strong></span>
                    <div className="flex gap-1.5">
                      {['INVESTIGATING', 'RESOLVED'].map((st) => (
                        <button
                          key={st}
                          onClick={() => handleUpdateStatus(inc.id, st)}
                          disabled={updatingId === inc.id || inc.status === st}
                          className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[10px] font-medium text-slate-300 disabled:opacity-40"
                        >
                          Mark {st}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
