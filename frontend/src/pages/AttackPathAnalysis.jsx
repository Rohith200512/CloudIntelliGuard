import React, { useState, useEffect } from 'react';
import { 
  GitMerge, 
  Search, 
  ArrowRight, 
  ShieldAlert, 
  Clock, 
  Server, 
  Database, 
  AlertCircle,
  ExternalLink,
  ChevronRight
} from 'lucide-react';
import { api } from '../api/client';

export default function AttackPathAnalysis({ onNavigate, initialUserId }) {
  const [attackPaths, setAttackPaths] = useState([]);
  const [selectedPath, setSelectedPath] = useState(null);
  const [filterUser, setFilterUser] = useState(initialUserId || '');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPaths();
  }, [filterUser]);

  const loadPaths = async () => {
    try {
      setLoading(true);
      const res = await api.listAttackPaths(filterUser || null);
      setAttackPaths(res);
      if (res.length > 0) {
        setSelectedPath(res[0]);
      } else {
        setSelectedPath(null);
      }
    } catch (err) {
      console.error('Failed to load attack paths:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-amber-400 uppercase tracking-widest font-mono mb-1">
            <GitMerge className="w-3.5 h-3.5" />
            Kill Chain & Traversal Intelligence
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Attack Path Analysis</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Traces multi-hop progression from authenticated identities and IP addresses through intermediate services to sensitive target resources.
          </p>
        </div>

        {/* Filter / Search by User */}
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Trace specific identity..."
              value={filterUser}
              onChange={(e) => setFilterUser(e.target.value)}
              className="pl-9 pr-3.5 py-2 rounded-xl bg-slate-900 border border-slate-700/80 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 w-52"
            />
          </div>
          {filterUser && (
            <button
              onClick={() => setFilterUser('')}
              className="px-2.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs text-slate-300"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <div className="py-20 text-center text-cyan-400 font-mono text-sm">
          Tracing graph attack paths across temporal windows...
        </div>
      ) : attackPaths.length === 0 ? (
        <div className="bg-[#090e1a] border border-slate-800/90 rounded-2xl p-12 text-center text-slate-500 text-xs">
          <GitMerge className="w-8 h-8 text-slate-600 mx-auto mb-3" />
          <p className="text-sm font-semibold text-slate-400">No attack paths matching criteria.</p>
          <p className="mt-1 text-slate-600">All observed entity interactions are within normal baseline thresholds.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Path List Selector */}
          <div className="space-y-3">
            <span className="text-xs font-mono uppercase text-slate-400 font-semibold block px-1">
              Detected Attack Chains ({attackPaths.length})
            </span>
            <div className="space-y-2.5 max-h-[600px] overflow-y-auto pr-1">
              {attackPaths.map((path) => {
                const isSelected = selectedPath?.path_id === path.path_id;
                return (
                  <button
                    key={path.path_id}
                    onClick={() => setSelectedPath(path)}
                    className={`w-full p-4 rounded-2xl border text-left transition-all ${
                      isSelected
                        ? 'bg-gradient-to-r from-red-950/70 to-slate-900 border-red-700/80 shadow-lg shadow-red-950/30'
                        : 'bg-[#090e1a] hover:bg-slate-900/80 border-slate-800'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono text-xs font-bold text-white truncate max-w-[170px]">
                        {path.cloud_user_id}
                      </span>
                      <span className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold ${
                        path.severity === 'CRITICAL' ? 'bg-red-950 text-red-300 border border-red-800' :
                        path.severity === 'HIGH' ? 'bg-amber-950 text-amber-300 border border-amber-800' :
                        'bg-slate-800 text-slate-300'
                      }`}>
                        {path.severity} ({path.path_risk_score.toFixed(0)})
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 truncate">
                      ➔ Target: {path.target_resource}
                    </p>
                    <span className="text-[10px] font-mono text-slate-500 mt-2 block">
                      {path.steps.length} Progression Steps
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Path Detail & Visual Progression Chain */}
          {selectedPath && (
            <div className="lg:col-span-2 bg-[#090e1a] border border-slate-800/90 rounded-2xl p-6 space-y-6">
              {/* Path Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-red-400 font-bold uppercase tracking-wider">Attack Chain</span>
                    <span className="text-xs text-slate-500 font-mono">#{selectedPath.path_id}</span>
                  </div>
                  <h3 className="text-lg font-bold text-white mt-0.5">Identity: {selectedPath.cloud_user_id}</h3>
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <span className="text-[10px] uppercase font-mono text-slate-400 block">Path Risk Score</span>
                    <span className="text-xl font-black text-red-400">{selectedPath.path_risk_score.toFixed(1)}/100</span>
                  </div>
                  <button
                    onClick={() => onNavigate('uba', { userId: selectedPath.cloud_user_id })}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs text-slate-200"
                  >
                    View UBA
                  </button>
                </div>
              </div>

              {/* Summary Description */}
              <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-slate-300 leading-relaxed">
                {selectedPath.summary}
              </div>

              {/* Step-by-Step Multi-Hop Timeline */}
              <div className="space-y-4">
                <h4 className="text-xs font-mono font-semibold uppercase text-slate-400 tracking-wider">
                  Sequential Entity Transitions ({selectedPath.steps.length} Steps)
                </h4>

                <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-800">
                  {selectedPath.steps.map((step) => {
                    return (
                      <div key={step.step_number} className="relative">
                        {/* Step Dot */}
                        <div className={`absolute -left-6 top-1.5 w-3 h-3 rounded-full border-2 ${
                          step.is_suspicious ? 'bg-red-500 border-red-900 shadow-md shadow-red-500/50' : 'bg-slate-700 border-slate-900'
                        }`} />

                        <div className={`p-4 rounded-xl border ${
                          step.is_suspicious ? 'bg-red-950/30 border-red-900/60' : 'bg-slate-900/50 border-slate-800'
                        }`}>
                          <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                            <div className="flex items-center gap-2">
                              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-cyan-400 font-bold">
                                STEP {step.step_number}
                              </span>
                              <span className="text-xs font-bold text-white">{step.action}</span>
                            </div>
                            <span className="text-[10px] font-mono text-slate-500">{step.timestamp}</span>
                          </div>

                          {/* Source -> Target Visual Breadcrumb */}
                          <div className="flex flex-wrap items-center gap-2 font-mono text-xs my-2">
                            <span className="px-2 py-0.5 rounded bg-slate-800/90 text-cyan-300 border border-slate-700">
                              {step.source_type}: {step.source_entity}
                            </span>
                            <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
                            <span className={`px-2 py-0.5 rounded border ${
                              step.is_suspicious 
                                ? 'bg-red-950 text-red-300 border-red-800' 
                                : 'bg-slate-800/90 text-slate-200 border-slate-700'
                            }`}>
                              {step.target_type}: {step.target_entity}
                            </span>
                          </div>

                          {step.details && (
                            <p className="text-[11px] text-slate-400 mt-2 font-sans">{step.details}</p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
