import React, { useState, useEffect } from 'react';
import { 
  UserCheck, 
  Activity, 
  AlertTriangle, 
  TrendingUp, 
  ShieldAlert, 
  Clock, 
  Server, 
  Globe, 
  ArrowRight,
  Zap
} from 'lucide-react';
import { api } from '../api/client';

export default function UserBehaviorAnalytics({ onNavigate, initialUserId }) {
  const [users, setUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState(initialUserId || '');
  const [profile, setProfile] = useState(null);
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
        fetchProfile(target);
      }
    } catch (err) {
      console.error('Failed to load UBA users:', err);
    }
  };

  const fetchProfile = async (uid) => {
    if (!uid) return;
    try {
      setLoading(true);
      const res = await api.getUBAProfile(uid);
      setProfile(res);
    } catch (err) {
      console.error('Failed to fetch UBA profile:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectUser = (uid) => {
    setSelectedUser(uid);
    fetchProfile(uid);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-cyan-400 uppercase tracking-widest font-mono mb-1">
            <UserCheck className="w-3.5 h-3.5" />
            Behavioral Intelligence
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">User Behavior Analytics (UBA)</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Analyzes whether a cloud identity's current activity deviates from historical baseline behavior.
          </p>
        </div>

        {/* User Selection Dropdown */}
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-slate-400 uppercase">Select Identity:</span>
          <select
            value={selectedUser}
            onChange={(e) => handleSelectUser(e.target.value)}
            className="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-700/80 text-xs font-mono text-cyan-400 focus:outline-none focus:border-cyan-500 font-bold"
          >
            {users.map(u => (
              <option key={u.cloud_user_id} value={u.cloud_user_id}>
                {u.cloud_user_id} (Risk: {u.risk_score.toFixed(0)} - {u.status})
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="py-20 text-center text-cyan-400 font-mono text-sm">
          Computing behavioral baseline and deviation metrics...
        </div>
      ) : profile ? (
        <div className="space-y-6">
          {/* Top Overview Bar */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-2xl bg-[#090e1a] border border-slate-800">
              <span className="text-xs text-slate-400 font-mono uppercase block">Enforcement Status</span>
              <span className={`text-xl font-bold font-mono mt-1 block ${
                profile.current_status === 'BLOCKED' ? 'text-red-400' :
                profile.current_status === 'RESTRICTED' ? 'text-amber-400' :
                'text-emerald-400'
              }`}>
                {profile.current_status}
              </span>
            </div>

            <div className="p-4 rounded-2xl bg-[#090e1a] border border-slate-800">
              <span className="text-xs text-slate-400 font-mono uppercase block">Risk Score</span>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-2xl font-black text-white">{profile.current_risk_score.toFixed(1)}</span>
                <span className="text-xs font-mono text-slate-400">/ 100 ({profile.current_risk_level})</span>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-[#090e1a] border border-slate-800 md:col-span-2 flex items-center justify-between">
              <div>
                <span className="text-xs text-slate-400 font-mono uppercase block">Behavior Deviation Score</span>
                <div className="flex items-baseline gap-2 mt-1">
                  <span className={`text-3xl font-black ${
                    profile.deviation_score > 60 ? 'text-red-400' :
                    profile.deviation_score > 25 ? 'text-amber-400' : 'text-emerald-400'
                  }`}>
                    {profile.deviation_score.toFixed(1)}%
                  </span>
                  <span className="text-xs text-slate-400">DEVIATION FROM BASELINE</span>
                </div>
              </div>

              <button
                onClick={() => onNavigate('simulator', { userId: profile.cloud_user_id })}
                className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-600/80 text-xs font-medium text-slate-200 flex items-center gap-1.5"
              >
                <Zap className="w-3.5 h-3.5 text-cyan-400" />
                <span>Simulate Risk</span>
              </button>
            </div>
          </div>

          {/* Baseline vs Current Behavior Comparison */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Historical Baseline */}
            <div className="bg-[#090e1a] border border-slate-800/90 rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <Clock className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-semibold text-white">Normal Behavioral Baseline</h3>
              </div>

              <div className="space-y-3 text-xs">
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex justify-between">
                  <span className="text-slate-400">Average API Velocity</span>
                  <span className="font-mono text-slate-200 font-bold">{profile.baseline?.avg_daily_api_calls || 0} calls/day</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex justify-between">
                  <span className="text-slate-400">Baseline Failure Rate</span>
                  <span className="font-mono text-slate-200 font-bold">{profile.baseline?.failure_rate || 0}%</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex justify-between">
                  <span className="text-slate-400">Operating Hours</span>
                  <span className="font-mono text-slate-200">{profile.baseline?.active_hours || 'Standard Business Hours'}</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-slate-400 block mb-1">Known Baseline Services:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {profile.baseline?.common_services?.map(s => (
                      <span key={s} className="px-2 py-0.5 rounded bg-slate-800 font-mono text-[11px] text-cyan-300">
                        {s}
                      </span>
                    )) || <span className="text-slate-500">None</span>}
                  </div>
                </div>
              </div>
            </div>

            {/* Current Window Observed Behavior */}
            <div className="bg-[#090e1a] border border-slate-800/90 rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <Activity className="w-4 h-4 text-cyan-400" />
                <h3 className="text-sm font-semibold text-white">Current Observed Behavior</h3>
              </div>

              <div className="space-y-3 text-xs">
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex justify-between">
                  <span className="text-slate-400">Current API Velocity</span>
                  <span className={`font-mono font-bold ${
                    profile.current_behavior?.current_api_calls > (profile.baseline?.avg_daily_api_calls * 1.5)
                      ? 'text-red-400'
                      : 'text-slate-200'
                  }`}>
                    {profile.current_behavior?.current_api_calls || 0} calls/day
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex justify-between">
                  <span className="text-slate-400">Current Failure Rate</span>
                  <span className={`font-mono font-bold ${
                    profile.current_behavior?.current_failure_rate > 20 ? 'text-red-400' : 'text-slate-200'
                  }`}>
                    {profile.current_behavior?.current_failure_rate || 0}%
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex justify-between">
                  <span className="text-slate-400">High-Privilege Operations</span>
                  <span className={`font-mono font-bold ${
                    profile.current_behavior?.sensitive_resource_accesses > 0 ? 'text-amber-400' : 'text-slate-200'
                  }`}>
                    {profile.current_behavior?.sensitive_resource_accesses || 0} sensitive operations
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-slate-400 block mb-1">Active Services in Current Window:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {profile.current_behavior?.active_services?.map(s => (
                      <span key={s} className="px-2 py-0.5 rounded bg-blue-950/80 border border-blue-800 font-mono text-[11px] text-blue-300">
                        {s}
                      </span>
                    )) || <span className="text-slate-500">None</span>}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Suspicious Behavioral Indicators */}
          <div className="bg-[#090e1a] border border-slate-800/90 rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <h3 className="text-sm font-semibold text-white">Suspicious Behavioral Indicators</h3>
            </div>

            {profile.suspicious_indicators.length === 0 ? (
              <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-900/40 text-xs text-emerald-400 text-center">
                ✓ No anomalous behavioral indicators detected for this identity. Activity is conforming to baseline.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {profile.suspicious_indicators.map((ind, i) => (
                  <div key={i} className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 flex items-start gap-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold shrink-0 mt-0.5 ${
                      ind.severity === 'HIGH' ? 'bg-red-950 text-red-400 border border-red-800' : 'bg-amber-950 text-amber-400 border border-amber-800'
                    }`}>
                      {ind.severity}
                    </span>
                    <div>
                      <h4 className="text-xs font-semibold text-slate-200">{ind.name}</h4>
                      <p className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">{ind.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recent Event Stream for this user */}
          <div className="bg-[#090e1a] border border-slate-800/90 rounded-2xl p-6">
            <h3 className="text-sm font-semibold text-white mb-3">Observed Activity Stream ({profile.cloud_user_id})</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-[11px] font-mono uppercase bg-slate-900/80 text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="p-2.5">Timestamp (UTC)</th>
                    <th className="p-2.5">Action</th>
                    <th className="p-2.5">Service</th>
                    <th className="p-2.5">Source IP</th>
                    <th className="p-2.5">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                  {profile.recent_events.map((ev, i) => (
                    <tr key={i} className="hover:bg-slate-800/40">
                      <td className="p-2.5 text-slate-400">{ev.timestamp}</td>
                      <td className="p-2.5 text-cyan-300 font-semibold">{ev.action}</td>
                      <td className="p-2.5 text-slate-300">{ev.service}</td>
                      <td className="p-2.5 text-slate-400">{ev.source_ip}</td>
                      <td className="p-2.5">
                        <span className={`px-2 py-0.5 rounded text-[10px] ${
                          ev.status === 'success' ? 'bg-emerald-950 text-emerald-400' : 'bg-red-950 text-red-400'
                        }`}>
                          {ev.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
