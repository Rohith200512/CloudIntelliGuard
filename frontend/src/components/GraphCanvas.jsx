import React, { useEffect, useRef, useState } from 'react';

const NODE_COLORS = {
  user: '#06b6d4',       // Cyan
  ip: '#f59e0b',         // Amber
  action: '#10b981',     // Emerald
  service: '#3b82f6',    // Blue
  resource: '#a855f7',   // Purple
  default: '#94a3b8',
};

export default function GraphCanvas({ 
  graphData, 
  onSelectNode, 
  selectedNodeId, 
  filterTypes = [], 
  filterRisk = 'ALL',
  highlightPathIds = []
}) {
  const canvasRef = useRef(null);
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 });
  const isDraggingRef = useRef(false);
  const dragStartRef = useRef({ x: 0, y: 0 });

  useEffect(() => {
    if (!graphData || !graphData.nodes) {
      setNodes([]);
      setEdges([]);
      return;
    }

    const rawNodes = graphData.nodes || [];
    const rawEdges = graphData.edges || graphData.links || [];

    const width = 800;
    const height = 520;
    const centerX = width / 2;
    const centerY = height / 2;

    const typeRadius = {
      user: 65,
      ip: 130,
      action: 200,
      service: 270,
      resource: 340,
    };

    const typeCounts = {};
    rawNodes.forEach(n => {
      const type = n.node_type || n.type || 'user';
      typeCounts[type] = (typeCounts[type] || 0) + 1;
    });

    const typeIndices = {};
    const processedNodes = rawNodes.map((n) => {
      const id = n.id;
      const type = n.node_type || n.type || (id.startsWith('user::') ? 'user' : id.startsWith('ip::') ? 'ip' : id.startsWith('action::') ? 'action' : id.startsWith('service::') ? 'service' : id.startsWith('resource::') ? 'resource' : 'user');
      const totalInType = typeCounts[type] || 1;
      const indexInType = typeIndices[type] || 0;
      typeIndices[type] = indexInType + 1;

      const baseR = typeRadius[type] || 200;
      const angle = (indexInType / totalInType) * 2 * Math.PI - Math.PI / 2;
      const x = centerX + baseR * Math.cos(angle) + (Math.sin(indexInType * 3) * 15);
      const y = centerY + baseR * Math.sin(angle) + (Math.cos(indexInType * 3) * 15);

      const isHighRisk = n.is_anomaly || n.risk_level === 'HIGH' || n.risk_level === 'CRITICAL' || (id.includes('level6') || id.includes('AdminAccess'));

      return {
        ...n,
        id,
        type,
        x,
        y,
        isHighRisk,
        radius: type === 'user' ? 14 : type === 'service' ? 12 : type === 'ip' ? 10 : 8,
      };
    });

    setNodes(processedNodes);
    setEdges(rawEdges);
    setTransform({ x: 0, y: 0, scale: 0.95 });
  }, [graphData]);

  // Canvas drawing loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    ctx.save();
    ctx.translate(transform.x + width / 2, transform.y + height / 2);
    ctx.scale(transform.scale, transform.scale);
    ctx.translate(-width / 2, -height / 2);

    // Apply entity type & risk filtering
    const visibleNodes = nodes.filter(n => {
      if (filterTypes.length > 0 && !filterTypes.includes(n.type)) return false;
      if (filterRisk === 'HIGH_CRITICAL' && !n.isHighRisk) return false;
      return true;
    });

    const visibleNodeIds = new Set(visibleNodes.map(n => n.id));
    const nodeMap = new Map(visibleNodes.map(n => [n.id, n]));

    // Draw Edges
    edges.forEach(edge => {
      const srcId = typeof edge.source === 'object' ? edge.source.id : edge.source;
      const dstId = typeof edge.target === 'object' ? edge.target.id : edge.target;

      if (!visibleNodeIds.has(srcId) || !visibleNodeIds.has(dstId)) return;

      const source = nodeMap.get(srcId);
      const target = nodeMap.get(dstId);

      if (source && target) {
        const isPath = highlightPathIds.includes(srcId) && highlightPathIds.includes(dstId);

        ctx.beginPath();
        ctx.moveTo(source.x, source.y);
        ctx.lineTo(target.x, target.y);
        ctx.strokeStyle = isPath ? 'rgba(239, 68, 68, 0.85)' : 'rgba(100, 116, 139, 0.22)';
        ctx.lineWidth = isPath ? 2.5 : 1.0;
        ctx.stroke();

        // Directional indicator
        const midX = (source.x + target.x) / 2;
        const midY = (source.y + target.y) / 2;
        ctx.beginPath();
        ctx.arc(midX, midY, isPath ? 3.5 : 1.8, 0, 2 * Math.PI);
        ctx.fillStyle = isPath ? '#ef4444' : 'rgba(56, 189, 248, 0.4)';
        ctx.fill();
      }
    });

    // Draw Nodes
    visibleNodes.forEach(node => {
      const isSelected = selectedNodeId === node.id;
      const isHovered = hoveredNode?.id === node.id;
      const isPath = highlightPathIds.includes(node.id);
      const color = NODE_COLORS[node.type] || NODE_COLORS.default;

      // Glow effect for Threat / Selected / Hovered
      if (node.isHighRisk || isSelected || isHovered || isPath) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius + (node.isHighRisk ? 7 : 5), 0, 2 * Math.PI);
        ctx.fillStyle = node.isHighRisk ? 'rgba(239, 68, 68, 0.35)' : isPath ? 'rgba(245, 158, 11, 0.35)' : `${color}33`;
        ctx.fill();
      }

      // Main node body
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.radius, 0, 2 * Math.PI);
      ctx.fillStyle = node.isHighRisk ? '#ef4444' : color;
      ctx.fill();

      ctx.strokeStyle = isSelected ? '#ffffff' : node.isHighRisk ? '#fca5a5' : '#0f172a';
      ctx.lineWidth = isSelected ? 2.5 : 1.5;
      ctx.stroke();

      // Node Label
      ctx.font = '10px -apple-system, BlinkMacSystemFont, monospace';
      ctx.fillStyle = isSelected ? '#ffffff' : '#cbd5e1';
      ctx.textAlign = 'center';
      const label = String(node.id || '').replace(/^.*?:{1,2}/, '');
      const truncated = label.length > 14 ? label.substring(0, 12) + '..' : label;
      ctx.fillText(truncated, node.x, node.y + node.radius + 12);
    });

    ctx.restore();
  }, [nodes, edges, transform, hoveredNode, selectedNodeId, filterTypes, filterRisk, highlightPathIds]);

  const handleMouseDown = (e) => {
    isDraggingRef.current = true;
    dragStartRef.current = { x: e.clientX - transform.x, y: e.clientY - transform.y };
  };

  const handleMouseMove = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    if (isDraggingRef.current) {
      setTransform(t => ({
        ...t,
        x: e.clientX - dragStartRef.current.x,
        y: e.clientY - dragStartRef.current.y,
      }));
      return;
    }

    const width = canvas.width;
    const height = canvas.height;
    const canvasX = (mouseX - (transform.x + width / 2)) / transform.scale + width / 2;
    const canvasY = (mouseY - (transform.y + height / 2)) / transform.scale + height / 2;

    const hit = nodes.find(n => {
      const dx = n.x - canvasX;
      const dy = n.y - canvasY;
      return Math.sqrt(dx * dx + dy * dy) <= n.radius + 5;
    });

    setHoveredNode(hit || null);
    canvas.style.cursor = hit ? 'pointer' : 'grab';
  };

  const handleMouseUp = () => {
    isDraggingRef.current = false;
  };

  const handleClick = () => {
    if (hoveredNode && onSelectNode) {
      onSelectNode(hoveredNode);
    }
  };

  const handleWheel = (e) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    setTransform(t => ({
      ...t,
      scale: Math.max(0.3, Math.min(3.5, t.scale * zoomFactor)),
    }));
  };

  const resetView = () => {
    setTransform({ x: 0, y: 0, scale: 0.95 });
  };

  return (
    <div className="relative w-full h-[520px] bg-[#070b12] rounded-2xl border border-slate-800 overflow-hidden flex flex-col items-center justify-center">
      {nodes.length === 0 ? (
        <div className="text-center text-slate-500">
          <p className="text-sm">No graph nodes available for this temporal window.</p>
          <p className="text-xs mt-1 text-slate-600">Select a dataset and process graph windows to visualize.</p>
        </div>
      ) : (
        <>
          <canvas
            ref={canvasRef}
            width={850}
            height={520}
            className="w-full h-full"
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onClick={handleClick}
            onWheel={handleWheel}
          />

          {/* Controls Overlay */}
          <div className="absolute top-4 right-4 flex items-center gap-2 bg-slate-900/90 border border-slate-800 p-1.5 rounded-xl backdrop-blur-md text-xs text-slate-300">
            <button
              onClick={() => setTransform(t => ({ ...t, scale: Math.min(3.5, t.scale * 1.2) }))}
              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 font-bold"
            >
              +
            </button>
            <button
              onClick={() => setTransform(t => ({ ...t, scale: Math.max(0.3, t.scale * 0.8) }))}
              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 font-bold"
            >
              -
            </button>
            <button
              onClick={resetView}
              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 font-medium"
            >
              Reset View
            </button>
          </div>

          {/* Legend */}
          <div className="absolute bottom-4 left-4 flex flex-wrap items-center gap-3 bg-slate-900/95 border border-slate-800 px-3.5 py-2 rounded-xl backdrop-blur-md text-[11px] text-slate-300 shadow-lg">
            {Object.entries(NODE_COLORS).filter(([k]) => k !== 'default').map(([type, color]) => (
              <div key={type} className="flex items-center gap-1.5 uppercase font-mono text-[10px]">
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
                <span>{type}</span>
              </div>
            ))}
            <div className="flex items-center gap-1.5 font-mono text-[10px] text-red-400 border-l border-slate-700 pl-2">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-ping" />
              <span>THREAT NODE</span>
            </div>
          </div>

          {/* Hover Tooltip */}
          {hoveredNode && (
            <div className="absolute top-4 left-4 bg-slate-900/95 border border-slate-700 p-3 rounded-xl text-xs text-slate-200 shadow-2xl pointer-events-none max-w-xs">
              <p className="font-semibold uppercase tracking-wider text-cyan-400 text-[10px]">{hoveredNode.type}</p>
              <p className="font-mono text-sm font-bold text-white mt-0.5 break-all">{hoveredNode.id}</p>
              {hoveredNode.isHighRisk && (
                <span className="inline-block mt-1 px-1.5 py-0.5 rounded bg-red-950/80 border border-red-800 text-red-400 text-[10px] font-bold">
                  HIGH RISK / SUSPICIOUS ENTITY
                </span>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
