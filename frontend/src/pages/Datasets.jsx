import React, { useEffect, useState } from 'react';
import { Database, Upload, Play, CheckCircle2, Clock, FileSpreadsheet, RefreshCw, AlertCircle } from 'lucide-react';
import { api } from '../api/client';

export default function Datasets({ onNavigate }) {
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [processingId, setProcessingId] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [datasetName, setDatasetName] = useState('');
  const [windowType, setWindowType] = useState('fixed');
  const [windowHours, setWindowHours] = useState(24);
  const [message, setMessage] = useState(null);

  const loadDatasets = async () => {
    try {
      setLoading(true);
      const data = await api.listDatasets();
      setDatasets(data);
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDatasets();
  }, []);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile) return;

    setUploading(true);
    setMessage(null);
    try {
      const res = await api.uploadDataset(selectedFile, datasetName);
      setMessage({ type: 'success', text: `Uploaded dataset '${res.filename}' successfully! ID: ${res.id}` });
      setSelectedFile(null);
      setDatasetName('');
      await loadDatasets();
    } catch (err) {
      setMessage({ type: 'error', text: `Upload failed: ${err.message}` });
    } finally {
      setUploading(false);
    }
  };

  const handleProcess = async (id) => {
    setProcessingId(id);
    setMessage(null);
    try {
      const res = await api.processDataset(id, windowType, Number(windowHours));
      setMessage({ type: 'success', text: res.message || 'Dataset processed and graph windows built!' });
      await loadDatasets();
    } catch (err) {
      setMessage({ type: 'error', text: `Processing failed: ${err.message}` });
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Database className="w-5 h-5 text-cyan-400" />
            Dataset Management & Pipeline
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Ingest raw CloudTrail events, clean and normalize timestamps, and construct temporal dynamic graph snapshots.
          </p>
        </div>

        <button
          onClick={loadDatasets}
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
          {message.type === 'error' ? <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" /> : <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />}
          <span>{message.text}</span>
        </div>
      )}

      {/* Upload Card */}
      <div className="p-6 rounded-2xl bg-[#0c101b] border border-slate-800 shadow-md">
        <h2 className="text-sm font-bold text-white uppercase tracking-wider mb-4 flex items-center gap-2">
          <Upload className="w-4 h-4 text-cyan-400" />
          Upload Cloud Activity Data
        </h2>

        <form onSubmit={handleUpload} className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          <div className="md:col-span-1">
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Select CSV / JSON File
            </label>
            <input
              type="file"
              accept=".csv,.json"
              onChange={(e) => setSelectedFile(e.target.files[0])}
              className="w-full text-xs text-slate-400 file:mr-3 file:py-2 file:px-3 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-cyan-950 file:text-cyan-300 hover:file:bg-cyan-900 border border-slate-800 rounded-xl p-1 bg-slate-900/60"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Dataset Name / Tag (Optional)
            </label>
            <input
              type="text"
              value={datasetName}
              onChange={(e) => setDatasetName(e.target.value)}
              placeholder="e.g. AWS Production Audit 2024"
              className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div>
            <button
              type="submit"
              disabled={uploading || !selectedFile}
              className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-xs font-semibold text-white transition-all shadow-md shadow-cyan-500/20 disabled:opacity-40 flex items-center justify-center gap-2"
            >
              <Upload className="w-4 h-4" />
              <span>{uploading ? 'Uploading...' : 'Upload Dataset'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Dataset List */}
      <div className="p-6 rounded-2xl bg-[#0c101b] border border-slate-800 shadow-md">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <FileSpreadsheet className="w-4 h-4 text-cyan-400" />
            Ingested Datasets & Temporal Windows
          </h2>

          {/* Window configuration options */}
          <div className="flex items-center gap-3 text-xs bg-slate-900 p-1.5 rounded-xl border border-slate-800">
            <label className="text-slate-400 font-medium pl-1">Window Strategy:</label>
            <select
              value={windowType}
              onChange={(e) => setWindowType(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg px-2 py-1 text-xs text-white focus:outline-none"
            >
              <option value="fixed">Fixed Duration (24h)</option>
              <option value="adaptive">Adaptive Heuristic</option>
            </select>
          </div>
        </div>

        {loading ? (
          <div className="py-12 text-center text-xs text-slate-500">Loading datasets...</div>
        ) : datasets.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-500">
            No datasets uploaded yet. Upload `sample_cloudtrail.csv` to begin.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-900/80 text-[11px] uppercase tracking-wider text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">ID</th>
                  <th className="py-3 px-4">Filename</th>
                  <th className="py-3 px-4">Events</th>
                  <th className="py-3 px-4">Uploaded At</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {datasets.map((ds) => (
                  <tr key={ds.id} className="hover:bg-slate-900/40 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-cyan-400">#{ds.id}</td>
                    <td className="py-3 px-4 font-medium text-white">{ds.filename}</td>
                    <td className="py-3 px-4 font-mono">{ds.raw_event_count ?? '100'} events</td>
                    <td className="py-3 px-4 text-slate-400">{new Date(ds.upload_time).toLocaleString()}</td>
                    <td className="py-3 px-4">
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold font-mono ${
                        ds.status === 'PROCESSED'
                          ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/60'
                          : 'bg-amber-950/80 text-amber-300 border border-amber-800/60'
                      }`}>
                        {ds.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleProcess(ds.id)}
                        disabled={processingId === ds.id}
                        className="px-3 py-1.5 rounded-xl bg-cyan-950/80 hover:bg-cyan-900 text-cyan-300 border border-cyan-800/60 text-xs font-medium transition-all flex items-center gap-1.5 ml-auto disabled:opacity-50"
                      >
                        <Play className="w-3 h-3" />
                        <span>{processingId === ds.id ? 'Processing...' : 'Build Graph Windows'}</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
