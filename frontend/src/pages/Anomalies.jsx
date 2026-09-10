import React, { useEffect, useState } from 'react';
import { AlertTriangle, Play, RefreshCw, Sliders, ShieldAlert, Cpu, FileText, CheckCircle2 } from 'lucide-react';
import { api } from '../api/client';

export default function Anomalies() {
  const [anomalies, setAnomalies] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState('1');
  const [modelType, setModelType] = useState('baseline');
  const [threshold, setThreshold] = useState(0.5);
  const [thresholdType, setThresholdType] = useState('statistical');
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [selectedAnomaly, setSelectedAnomaly] = useState(null);
  const [message, setMessage] = useState(null);

  const loadAnomalies = async () => {
    try {
      setLoading(true);
      const [anomList, dss] = await Promise.all([
        api.listAnomalies({ limit: 100 }),
        api.listDatasets(),
      ]);
      setAnomalies(anomList);
      setDatasets(dss);
      if (dss.length > 0 && !selectedDatasetId) {
        setSelectedDatasetId(String(dss[0].id));
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnomalies();
  }, []);

  const handleTrain = async () => {
    setActionLoading(true);
    setMessage(null);
    try {
      const res = await api.trainModel(Number(selectedDatasetId), modelType);
      setMessage({ type: 'success', text: `Model training completed! ModelRun ID: ${res.id}, Status: ${res.status}` });
      await loadAnomalies();
    } catch (err) {
      setMessage({ type: 'error', text: `Training failed: ${err.message}` });
    } finally {
      setActionLoading(false);
    }
  };

  const handleInfer = async () => {
    setActionLoading(true);
    setMessage(null);
    try {
      const res = await api.runInference(Number(selectedDatasetId), modelType, Number(threshold), thresholdType);
      setMessage({ type: 'success', text: `Inference completed for ${res.length} user nodes!` });
      await loadAnomalies();
    } catch (err) {
      setMessage({ type: 'error', text: `Inference failed: ${err.message}` });
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-rose-400" />
            Anomaly Detection & GNN Inference Console
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Train baseline or enhanced temporal GNN models, calibrate anomaly thresholds, and inspect behavioral deviations.
          </p>
        </div>

        <button
          onClick={loadAnomalies}
          className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300 border border-slate-700 flex items-center gap-1.5"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh</span>
        </button>
      </div>

      {message && (
        <div className={`p-4 rounded-xl text-xs flex items-center gap-2.5 border ${
          message.type === 'error'
            ? 'bg-rose-950/60 border-rose-800/60 text-rose-300'
            : 'bg-emerald-950/60 border-emerald-800/60 text-emerald-300'
        }`}>
          {message.type === 'error' ? <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" /> : <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />}
          <span>{message.text}</span>
        </div>
      )}

      {/* Model Controls Bar */}
      <div className="p-6 rounded-2xl bg-[#0c101b] border border-slate-800 shadow-md">
        <h2 className="text-sm font-bold text-white uppercase tracking-wider mb-4 flex items-center gap-2">
          <Cpu className="w-4 h-4 text-cyan-400" />
          Model Pipeline Controls
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 items-end">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Select Dataset
            </label>
            <select
              value={selectedDatasetId}
              onChange={(e) => setSelectedDatasetId(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none"
            >
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  #{d.id} - {d.filename}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              GNN Architecture
            </label>
            <select
              value={modelType}
              onChange={(e) => setModelType(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none"
            >
              <option value="baseline">Baseline GCN + IsolationForest</option>
              <option value="enhanced">Enhanced Temporal GNN (Attn)</option>
            </select>
          </div>

          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Anomaly Threshold
              </label>
              <span className="text-xs font-mono text-cyan-400 font-bold">{threshold}</span>
            </div>
            <input
              type="range"
              min="0.1"
              max="0.9"
              step="0.05"
              value={threshold}
              onChange={(e) => setThreshold(parseFloat(e.target.value))}
              className="w-full accent-cyan-400 cursor-pointer"
            />
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleTrain}
              disabled={actionLoading}
              className="flex-1 py-2.5 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition-all flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              <Cpu className="w-3.5 h-3.5 text-cyan-400" />
              <span>Train Model</span>
            </button>

            <button
              onClick={handleInfer}
              disabled={actionLoading}
              className="flex-1 py-2.5 px-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-xs font-semibold text-white transition-all shadow-md shadow-cyan-500/20 flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5" />
              <span>Run Inference</span>
            </button>
          </div>
        </div>
      </div>

      {/* Anomalies Table */}
      <div className="p-6 rounded-2xl bg-[#0c101b] border border-slate-800 shadow-md">
        <h2 className="text-sm font-bold text-white uppercase tracking-wider mb-4 flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-rose-400" />
          Evaluated User Anomaly Records ({anomalies.length})
        </h2>

        {loading ? (
          <div className="py-12 text-center text-xs text-slate-500">Loading anomalies...</div>
        ) : anomalies.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-500">
            No inference evaluations found. Click 'Run Inference' above to evaluate user activity.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-900/80 text-[11px] uppercase tracking-wider text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Evaluation ID</th>
                  <th className="py-3 px-4">Cloud User ID</th>
                  <th className="py-3 px-4">Anomaly Score</th>
                  <th className="py-3 px-4">Classification</th>
                  <th className="py-3 px-4">Confidence</th>
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {anomalies.map((a) => (
                  <tr key={a.id} className="hover:bg-slate-900/40 transition-colors">
                    <td className="py-3 px-4 font-mono text-slate-500">#{a.id}</td>
                    <td className="py-3 px-4 font-mono font-bold text-white uppercase">{a.cloud_user_id}</td>
                    <td className="py-3 px-4 font-mono font-bold">
                      <span className={a.is_anomaly ? 'text-rose-400' : 'text-emerald-400'}>
                        {(a.anomaly_score * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold font-mono ${
                        a.is_anomaly
                          ? 'bg-rose-950/80 text-rose-300 border border-rose-800/60'
                          : 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60'
                      }`}>
                        {a.is_anomaly ? 'ANOMALY' : 'NORMAL'}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-400">
                      {a.confidence ? `${(a.confidence * 100).toFixed(0)}%` : 'High'}
                    </td>
                    <td className="py-3 px-4 text-slate-400">{new Date(a.created_at).toLocaleString()}</td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => setSelectedAnomaly(a)}
                        className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 text-[11px] font-medium"
                      >
                        Explain
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Explanation Modal */}
      {selectedAnomaly && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#0e1424] border border-slate-700 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <FileText className="w-4 h-4 text-cyan-400" />
                Explanation for User {selectedAnomaly.cloud_user_id.toUpperCase()}
              </h3>
              <button
                onClick={() => setSelectedAnomaly(null)}
                className="text-slate-400 hover:text-white text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs text-slate-300">
              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex justify-between">
                <span className="text-slate-400">Anomaly Score:</span>
                <span className="font-mono font-bold text-cyan-400">{(selectedAnomaly.anomaly_score * 100).toFixed(2)}%</span>
              </div>

              <div>
                <p className="font-semibold text-slate-300 mb-1">Observable Findings:</p>
                {selectedAnomaly.explanation?.findings ? (
                  <ul className="list-disc list-inside space-y-1 text-slate-400">
                    {selectedAnomaly.explanation.findings.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-slate-500 italic">No specific rule violations observed. Model flagged deviation via graph structural embedding distance.</p>
                )}
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setSelectedAnomaly(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200"
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
