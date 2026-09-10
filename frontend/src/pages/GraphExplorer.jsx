import React, { useEffect, useState } from 'react';
import { Share2, RefreshCw, Layers, ZoomIn, Info, Search, Filter } from 'lucide-react';
import { api } from '../api/client';
import GraphCanvas from '../components/GraphCanvas';

export default function GraphExplorer() {
  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState('1');
  const [windowData, setWindowData] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [userFilter, setUserFilter] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function init() {
      try {
        const dss = await api.listDatasets();
        setDatasets(dss);
        if (dss.length > 0) {
          setSelectedDatasetId(String(dss[0].id));
        }
      } catch (err) {
        console.error(err);
      }
    }
    init();
  }, []);

  const loadGraph = async () => {
    if (!selectedDatasetId) return;
    setLoading(true);
    setError(null);
    setSelectedNode(null);
    try {
      if (userFilter.trim()) {
        // Ego subgraph for user
        const ego = await api.getUserSubgraph(userFilter.trim().toLowerCase(), Number(selectedDatasetId));
        setWindowData(ego.graph);
      } else {
        // Window 1 full graph
        const gw = await api.getGraphWindow(Number(selectedDatasetId), true);
        setWindowData(gw.graph_json);
      }
    } catch (err) {
      setError(`Failed to load graph: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedDatasetId) {
      loadGraph();
    }
  }, [selectedDatasetId]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Share2 className="w-5 h-5 text-cyan-400" />
            Dynamic Temporal Graph Explorer
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Visual topological representation of User $\rightarrow$ Action $\rightarrow$ Service $\rightarrow$ Resource interactions.
          </p>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-300">
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            <label className="text-slate-400">Dataset:</label>
            <select
              value={selectedDatasetId}
              onChange={(e) => setSelectedDatasetId(e.target.value)}
              className="bg-transparent border-0 text-white font-mono focus:outline-none cursor-pointer"
            >
              {datasets.map((d) => (
                <option key={d.id} value={d.id} className="bg-slate-900">
                  #{d.id} - {d.filename}
                </option>
              ))}
            </select>
          </div>

          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={userFilter}
              onChange={(e) => setUserFilter(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && loadGraph()}
              placeholder="Filter user (e.g. u006)"
              className="bg-slate-900 border border-slate-800 rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <button
            onClick={loadGraph}
            disabled={loading}
            className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300 border border-slate-700 flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Load</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/60 border border-rose-800/60 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {/* Main Graph Canvas & Inspector Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3">
          <GraphCanvas
            graphData={windowData}
            onSelectNode={setSelectedNode}
            selectedNodeId={selectedNode?.id}
          />
        </div>

        {/* Node Inspector Sidebar */}
        <div className="p-5 rounded-2xl bg-[#0c101b] border border-slate-800 shadow-md flex flex-col">
          <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
            <Info className="w-4 h-4 text-cyan-400" />
            Node Inspector
          </h2>

          {selectedNode ? (
            <div className="space-y-4 text-xs">
              <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-800">
                <p className="text-[11px] text-slate-500 uppercase tracking-wide">Node ID</p>
                <p className="font-mono font-bold text-white text-sm break-all mt-0.5">{selectedNode.id}</p>
              </div>

              <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-800">
                <p className="text-[11px] text-slate-500 uppercase tracking-wide">Node Type</p>
                <span className="inline-block mt-1 px-2 py-0.5 rounded-full text-[11px] font-bold font-mono uppercase bg-cyan-950 text-cyan-300 border border-cyan-800">
                  {selectedNode.type}
                </span>
              </div>

              {selectedNode.type === 'user' && (
                <div className="pt-2">
                  <button
                    onClick={() => {
                      setUserFilter(selectedNode.id);
                      loadGraph();
                    }}
                    className="w-full py-2 px-3 rounded-xl bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-800/60 font-medium text-xs transition-all flex items-center justify-center gap-1.5"
                  >
                    <ZoomIn className="w-3.5 h-3.5" />
                    <span>Focus 2-Hop Ego Subgraph</span>
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center text-slate-500 text-xs">
              <p>Click any node in the graph to inspect its properties and topological connections.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
