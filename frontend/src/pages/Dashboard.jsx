import React, { useEffect, useState } from 'react';
import { 
  Database, 
  Activity, 
  AlertTriangle, 
  ShieldCheck, 
  Radio, 
  Zap, 
  TrendingUp, 
  ArrowUpRight 
} from 'lucide-react';
import { api } from '../api/client';
import StatCard from '../components/StatCard';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, AreaChart, Area } from 'recharts';

export default function Dashboard({ onNavigate }) {
  const [summary, setSummary] = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [runningDemo, setRunningDemo] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [sumData, anomData, repData] = await Promise.allSettled([
        api.getDashboardSummary(),
        api.listAnomalies({ limit: 10 }),
        api.getSecurityReport(),
      ]);

      if (sumData.status === 'fulfilled') setSummary(sumData.value);
      if (anomData.status === 'fulfilled') setAnomalies(anomData.value);
      if (repData.status === 'fulfilled') setReport(repData.value);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleQuickRun = async () => {
    setRunningDemo(true);
    try {
      // 1. Process dataset 1 if available
      const datasets = await api.listDatasets();
      if (datasets.length > 0) {
        const dsId = datasets[0].id;
        await api.processDataset(dsId, 'fixed', 24);
        const train = await api.trainModel(dsId, 'baseline');
        await api.runInference(train.graph_window_id || dsId, 'baseline', 0.5);
      }
      await fetchData();
    } catch (err) {
      alert(`Pipeline execution: ${err.message}`);
    } finally {
      setRunningDemo(false);
    }
  };

  const chartData = anomalies.slice(0, 10).map((a) => ({
    user: a.cloud_user_id,
    score: Number((a.anomaly_score * 100).toFixed(1)),
    isAnomaly: a.is_anomaly,
  }));

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-[#0e172a] to-[#0a1222] border border-slate-800 shadow-lg">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            Security Intelligence Console
            <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800 font-mono">
              Live Monitoring
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time graph anomaly scoring, multi-user behavioral analysis, and threat telemetry.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchData}
            className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300 transition-all border border-slate-700 flex items-center gap-1.5"
          >
            <span>Refresh</span>
          </button>
          <button
            onClick={handleQuickRun}
            disabled={runningDemo}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-xs font-semibold text-white transition-all shadow-md shadow-cyan-500/20 flex items-center gap-2 disabled:opacity-50"
          >
            <Zap className="w-3.5 h-3.5" />
            <span>{runningDemo ? 'Running Pipeline...' : 'Run Fast Inference'}</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Events"
          value={summary?.total_events ?? '0'}
          subtitle={`${summary?.total_datasets ?? 0} Ingested Datasets`}
          icon={Activity}
          color="cyan"
        />
        <StatCard
          title="Detected Anomalies"
          value={summary?.total_anomalies ?? '0'}
          subtitle={report?.avg_anomaly_score ? `Avg Score: ${(report.avg_anomaly_score * 100).toFixed(1)}%` : 'No score yet'}
          icon={AlertTriangle}
          color="rose"
        />
        <StatCard
          title="Active Incidents"
          value={summary?.open_incidents ?? '0'}
          subtitle={`${summary?.critical_incidents ?? 0} Critical Priority`}
          icon={ShieldCheck}
          color="amber"
        />
        <StatCard
          title="Unacknowledged Alerts"
          value={summary?.unacknowledged_alerts ?? '0'}
          subtitle="Real-time Alert Queue"
          icon={Radio}
          color="indigo"
        />
      </div>

      {/* Analytics Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Anomaly Distribution Chart */}
        <div className="lg:col-span-2 p-6 rounded-2xl bg-[#0c101b] border border-slate-800 shadow-md">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">User Anomaly Score Distribution</h2>
              <p className="text-xs text-slate-400">Scores evaluated by the Baseline/Enhanced Temporal GNN</p>
            </div>
            <button
              onClick={() => onNavigate('anomalies')}
              className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-medium"
            >
              <span>View All</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="h-64 w-full">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <XAxis dataKey="user" stroke="#64748b" fontSize={11} />
                  <YAxis stroke="#64748b" fontSize={11} domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '12px', fontSize: '12px' }}
                    labelStyle={{ color: '#94a3b8', fontWeight: 'bold' }}
                    formatter={(val) => [`${val}%`, 'Anomaly Score']}
                  />
                  <Bar
                    dataKey="score"
                    fill="#38bdf8"
                    radius={[6, 6, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-slate-500 text-xs">
                <p>No anomaly scores generated yet.</p>
                <p className="text-slate-600 mt-1">Upload a dataset and run inference to populate telemetry.</p>
              </div>
            )}
          </div>
        </div>

        {/* Top Suspicious Activity Feed */}
        <div className="p-6 rounded-2xl bg-[#0c101b] border border-slate-800 shadow-md flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">High Risk Users</h2>
            <button
              onClick={() => onNavigate('risk')}
              className="text-xs text-cyan-400 hover:text-cyan-300 font-medium"
            >
              Risk Matrix
            </button>
          </div>

          <div className="space-y-3 flex-1 overflow-y-auto max-h-64 pr-1">
            {anomalies.length > 0 ? (
              anomalies.slice(0, 5).map((a) => (
                <div
                  key={a.id}
                  className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 flex items-center justify-between hover:border-slate-700 transition-all"
                >
                  <div className="flex items-center gap-2.5">
                    <div className={`w-2 h-2 rounded-full ${a.is_anomaly ? 'bg-rose-500 animate-pulse' : 'bg-emerald-400'}`} />
                    <div>
                      <p className="text-xs font-mono font-bold text-white uppercase">{a.cloud_user_id}</p>
                      <p className="text-[10px] text-slate-400">
                        {a.is_anomaly ? 'Anomaly Flagged' : 'Normal Activity'}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={`text-xs font-bold font-mono px-2 py-0.5 rounded ${
                      a.is_anomaly
                        ? 'bg-rose-950/80 text-rose-300 border border-rose-800/60'
                        : 'bg-slate-800 text-slate-300'
                    }`}>
                      {(a.anomaly_score * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-500">
                No users evaluated yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
