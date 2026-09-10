import React, { useState, useEffect } from 'react';
import { Share2, Filter, Layers, Zap, Info, ArrowRight, ShieldAlert } from 'lucide-react';
import { api } from '../api/client';
import GraphCanvas from '../components/GraphCanvas';

export default function DynamicGraph({ onNavigate, initialUserId }) {
  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState(null);
  const [graphWindows, setGraphWindows] = useState([]);
  const [selectedWindowId, setSelectedWindowId] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [loading, setLoading] = useState(false);

  // Filters
  const [selectedTypes, setSelectedTypes] = useState(['user', 'ip', 'action', 'service', 'resource']);
  const [riskFilter, setRiskFilter] = useState('ALL');

  useEffect(() => {
    loadDatasets();
  }, []);

  const loadDatasets = async () => {
    try {
      const list = await api.listDatasets();
      setDatasets(list);
      if (list.length > 0) {
        const firstId = list[0].id;
        setSelectedDatasetId(firstId);
        loadGraphWindows(firstId);
      }
    } catch (err) {
      console.error('Failed to load datasets:', err);
    }
  };

  const loadGraphWindows = async (dsId) => {
    try {
      const ds = await api.getDataset(dsId);
      const windows = ds.graph_windows || [];
      setGraphWindows(windows);
      if (windows.length > 0) {
        setSelectedWindowId(windows[0].id);
        fetchGraph(windows[0].id);
      } else {
        setGraphData(null);
      }
    } catch (err) {
      console.error('Failed to load windows:', err);
    }
  };

  const fetchGraph = async (windowId) => {
    try {
      setLoading(true);
      const res = await api.getGraphWindow(windowId, true);
      setGraphData(res.graph || null);
    } catch (err) {
      console.error('Failed to fetch graph data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTypeToggle = (type) => {
    if (selectedTypes.includes(type)) {
      setSelectedTypes(selectedTypes.filter(t => t !== type));
    } else {
      setSelectedTypes([...selectedTypes, type]);
    }
  };

  const handleLaunchAttackPath = (node) => {
    const rawId = String(node.id || '').replace(/^.*?:{1,2}/, '');
    onNavigate('attack_path', { userId: rawId });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-cyan-400 uppercase tracking-widest font-mono mb-1">
            <Share2 className="w-3.5 h-3.5" />
            Temporal Multi-Hop Graph
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Dynamic Graph</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Interactive topology connecting Users, IPs, API Actions, Cloud Services, and Resources.
          </p>
        </div>

        {/* Dataset & Window Selectors */}
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={selectedDatasetId || ''}
            onChange={(e) => {
              const id = Number(e.target.value);
              setSelectedDatasetId(id);
              loadGraphWindows(id);
            }}
            className="px-3 py-2 rounded-xl bg-slate-900 border border-slate-700/80 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
          >
            {datasets.map(d => (
              <option key={d.id} value={d.id}>Dataset #{d.id}: {d.filename}</option>
            ))}
          </select>

          {graphWindows.length > 0 && (
            <select
              value={selectedWindowId || ''}
              onChange={(e) => {
                const id = Number(e.target.value);
                setSelectedWindowId(id);
                fetchGraph(id);
              }}
              className="px-3 py-2 rounded-xl bg-slate-900 border border-slate-700/80 text-xs text-cyan-400 font-mono focus:outline-none focus:border-cyan-500"
            >
              {graphWindows.map(w => (
                <option key={w.id} value={w.id}>
                  Window #{w.id} ({w.event_count} events)
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-3.5 rounded-xl bg-[#090e1a] border border-slate-800/80 text-xs">
        {/* Entity Type Checkboxes */}
        <div className="flex items-center gap-3">
          <span className="text-slate-400 font-mono text-[11px] uppercase flex items-center gap-1">
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            Entities:
          </span>
          {[
            { id: 'user', label: 'User', color: 'text-cyan-400' },
            { id: 'ip', label: 'IP', color: 'text-amber-400' },
            { id: 'action', label: 'Action', color: 'text-emerald-400' },
            { id: 'service', label: 'Service', color: 'text-blue-400' },
            { id: 'resource', label: 'Resource', color: 'text-purple-400' },
          ].map(t => (
            <label key={t.id} className="flex items-center gap-1.5 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={selectedTypes.includes(t.id)}
                onChange={() => handleTypeToggle(t.id)}
                className="rounded border-slate-700 text-cyan-500 focus:ring-0 bg-slate-800"
              />
              <span className={`font-mono text-[11px] ${t.color}`}>{t.label}</span>
            </label>
          ))}
        </div>

        {/* Risk Level Filter */}
        <div className="flex items-center gap-2">
          <span className="text-slate-400 font-mono text-[11px] uppercase flex items-center gap-1">
            <Filter className="w-3 h-3 text-red-400" />
            Risk Filter:
          </span>
          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="px-2 py-1 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-200 font-mono"
          >
            <option value="ALL">All Entities</option>
            <option value="HIGH_CRITICAL">High Risk & Threats Only</option>
          </select>
        </div>
      </div>

      {/* Main Canvas and Inspector Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3">
          {loading ? (
            <div className="h-[520px] bg-[#070b12] rounded-2xl border border-slate-800 flex items-center justify-center text-cyan-400 font-mono text-sm">
              Rendering dynamic temporal graph...
            </div>
          ) : (
            <GraphCanvas
              graphData={graphData}
              onSelectNode={setSelectedNode}
              selectedNodeId={selectedNode?.id}
              filterTypes={selectedTypes}
              filterRisk={riskFilter}
            />
          )}
        </div>

        {/* Node Inspector Side Panel */}
        <div className="bg-[#090e1a] border border-slate-800/90 rounded-2xl p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider font-mono mb-3">
              <Info className="w-4 h-4 text-cyan-400" />
              Entity Inspector
            </div>

            {selectedNode ? (
              <div className="space-y-4">
                <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-800">
                  <span className="text-[10px] uppercase font-mono text-cyan-400 block font-semibold">
                    {selectedNode.type} Entity
                  </span>
                  <p className="font-mono text-xs font-bold text-white mt-1 break-all">
                    {selectedNode.id}
                  </p>
                </div>

                {selectedNode.isHighRisk && (
                  <div className="p-3 rounded-xl bg-red-950/40 border border-red-800/60 text-xs text-red-300 flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-red-400 shrink-0" />
                    <span>Flagged as suspicious / anomalous by GNN engine.</span>
                  </div>
                )}

                <div className="space-y-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-slate-800 text-slate-400">
                    <span>Node Type</span>
                    <span className="font-mono text-slate-200 capitalize">{selectedNode.type}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-800 text-slate-400">
                    <span>Activity Weight</span>
                    <span className="font-mono text-slate-200">{selectedNode.weight || 1} events</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-12 text-center text-slate-500 text-xs">
                Click any node in the graph to inspect entity attributes, connections, and trace attack paths.
              </div>
            )}
          </div>

          {selectedNode && (
            <div className="mt-6 pt-4 border-t border-slate-800/80 space-y-2">
              <button
                onClick={() => handleLaunchAttackPath(selectedNode)}
                className="w-full px-3 py-2.5 rounded-xl bg-gradient-to-r from-red-600 to-amber-600 hover:from-red-500 hover:to-amber-500 text-white font-medium text-xs shadow-lg shadow-red-950/40 flex items-center justify-center gap-2"
              >
                <span>Trace Attack Path</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => onNavigate('uba', { userId: String(selectedNode.id || '').replace(/^.*?:{1,2}/, '') })}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 text-xs"
              >
                View UBA Profile
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
