import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  Search, 
  Filter, 
  RefreshCw, 
  Clock, 
  ShieldCheck, 
  ShieldAlert, 
  Lock, 
  UserX,
  Eye
} from 'lucide-react';
import { api } from '../api/client';

export default function AuditLog() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState('');
  const [selectedLog, setSelectedLog] = useState(null);

  useEffect(() => {
    loadLogs();
  }, [actionFilter]);

  const loadLogs = async () => {
    try {
      setLoading(true);
      const res = await api.listAuditLogs(actionFilter || null, 150);
      setLogs(res);
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-cyan-400 uppercase tracking-widest font-mono mb-1">
            <FileText className="w-3.5 h-3.5" />
            Compliance & Enforcement Trail
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Audit / Response Log</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Immutable chronological audit record of all automated security responses, restrictions, blocks, and manual overrides.
          </p>
        </div>

        {/* Action Filter & Refresh */}
        <div className="flex items-center gap-3">
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-700/80 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
          >
            <option value="">All Action Types</option>
            <option value="AUTOMATED_BLOCK">Automated Block</option>
            <option value="AUTOMATED_RESTRICTION">Automated Restriction</option>
            <option value="MANUAL">Manual Overrides</option>
            <option value="incident">Incident Creation</option>
          </select>

          <button
            onClick={loadLogs}
            className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5 text-cyan-400" />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Main Audit Table */}
      <div className="bg-[#090e1a] border border-slate-800/90 rounded-2xl overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white">Audit Records ({logs.length})</h3>
          <span className="text-[11px] font-mono text-slate-400">SOC Compliance Log</span>
        </div>

        {loading ? (
          <div className="py-20 text-center text-cyan-400 font-mono text-sm">
            Retrieving immutable audit logs...
          </div>
        ) : logs.length === 0 ? (
          <div className="py-16 text-center text-slate-500 text-xs">
            No audit logs found matching the filter.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="text-[11px] font-mono uppercase bg-slate-900/80 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="p-3.5">Timestamp (UTC)</th>
                  <th className="p-3.5">Action Taken</th>
                  <th className="p-3.5">Target Entity / Resource</th>
                  <th className="p-3.5">Risk Score / Level</th>
                  <th className="p-3.5">Trigger Reason</th>
                  <th className="p-3.5">Status</th>
                  <th className="p-3.5 text-right">Payload</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                {logs.map((log) => {
                  const isBlock = log.action.includes('BLOCK');
                  const isRestrict = log.action.includes('RESTRICT');
                  const riskScore = log.detail?.risk_score;
                  const riskLevel = log.detail?.risk_level;

                  return (
                    <tr key={log.id} className="hover:bg-slate-800/40">
                      <td className="p-3.5 text-slate-400">
                        {new Date(log.timestamp).toISOString().replace('T', ' ').substring(0, 19)}
                      </td>

                      <td className="p-3.5">
                        <span className={`px-2 py-0.5 rounded font-bold text-[10px] ${
                          isBlock ? 'bg-red-950 text-red-300 border border-red-800' :
                          isRestrict ? 'bg-amber-950 text-amber-300 border border-amber-800' :
                          'bg-slate-800 text-slate-300'
                        }`}>
                          {log.action}
                        </span>
                      </td>

                      <td className="p-3.5 font-bold text-white">
                        {log.resource || 'System'}
                      </td>

                      <td className="p-3.5">
                        {riskScore !== undefined ? (
                          <span className={`font-bold ${
                            riskScore >= 75 ? 'text-red-400' :
                            riskScore >= 50 ? 'text-amber-400' : 'text-slate-300'
                          }`}>
                            {Number(riskScore).toFixed(1)} ({riskLevel || 'N/A'})
                          </span>
                        ) : (
                          <span className="text-slate-500">—</span>
                        )}
                      </td>

                      <td className="p-3.5 font-sans text-slate-300 max-w-xs truncate">
                        {log.detail?.reason || log.detail?.note || 'Triggered by security event'}
                      </td>

                      <td className="p-3.5">
                        <span className="px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-900/60 text-[10px] font-bold">
                          COMMITTED
                        </span>
                      </td>

                      <td className="p-3.5 text-right">
                        <button
                          onClick={() => setSelectedLog(log)}
                          className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] flex items-center gap-1 ml-auto"
                        >
                          <Eye className="w-3 h-3" />
                          <span>Inspect</span>
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

      {/* Payload Modal */}
      {selectedLog && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#090e1a] border border-slate-700 p-6 rounded-2xl max-w-lg w-full space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <FileText className="w-4 h-4 text-cyan-400" />
              Audit Log #{selectedLog.id}
            </h3>

            <div className="space-y-2 text-xs font-mono">
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Action:</span>
                <span className="text-white font-bold">{selectedLog.action}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Resource:</span>
                <span className="text-cyan-400">{selectedLog.resource}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Timestamp:</span>
                <span className="text-slate-300">{selectedLog.timestamp}</span>
              </div>
            </div>

            <div>
              <span className="text-xs font-mono text-slate-400 block mb-1">Payload JSON:</span>
              <pre className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-[11px] font-mono text-emerald-400 overflow-x-auto max-h-48">
                {JSON.stringify(selectedLog.detail, null, 2)}
              </pre>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedLog(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-medium hover:bg-slate-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
