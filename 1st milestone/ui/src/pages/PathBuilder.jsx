import { useState, useRef, useEffect, useCallback } from 'react';
import { useApp } from '../context/AppContext';
import './PathBuilder.css';

// Node type configuration matches schema
const NODE_TYPES = {
  intersection: { label: 'Intersection', color: '#6b7280', icon: '◆' },
  runway_end: { label: 'Runway End', color: '#ef4444', icon: '▮' },
  runway_entry: { label: 'Runway Entry', color: '#f97316', icon: '▶' },
  runway_exit: { label: 'Runway Exit', color: '#eab308', icon: '◀' },
  hold_point: { label: 'Hold Point', color: '#f87171', icon: '⬢' },
  gate: { label: 'Gate', color: '#34d399', icon: '◼' },
  apron_center: { label: 'Apron Center', color: '#60a5fa', icon: '●' },
};

const EDGE_TYPES = {
  runway: { label: 'Runway', color: '#4b5563', width: 8 },
  taxiway: { label: 'Taxiway', color: '#fbbf24', width: 4 },
  apron_link: { label: 'Apron Link', color: '#60a5fa', width: 3 },
  rapid_exit: { label: 'Rapid Exit', color: '#8b5cf6', width: 4 },
};

const FLOW_OPTIONS = ['both', 'arrival', 'departure'];

// Icons
const ArrowLeftIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="19" y1="12" x2="5" y2="12"></line>
    <polyline points="12 19 5 12 12 5"></polyline>
  </svg>
);

const SaveIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
    <polyline points="17 21 17 13 7 13 7 21"></polyline>
    <polyline points="7 3 7 8 15 8"></polyline>
  </svg>
);

const DownloadIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
    <polyline points="7 10 12 15 17 10"></polyline>
    <line x1="12" y1="15" x2="12" y2="3"></line>
  </svg>
);

const MousePointerIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M3 3l7.07 16.97 2.51-7.39 7.39-2.51L3 3z"></path>
  </svg>
);

const CircleIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="10"></circle>
  </svg>
);

const LineIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="5" y1="19" x2="19" y2="5"></line>
  </svg>
);

const TrashIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="3 6 5 6 21 6"></polyline>
    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
  </svg>
);

const GridIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="3" y="3" width="7" height="7"></rect>
    <rect x="14" y="3" width="7" height="7"></rect>
    <rect x="14" y="14" width="7" height="7"></rect>
    <rect x="3" y="14" width="7" height="7"></rect>
  </svg>
);

const ZoomInIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="11" cy="11" r="8"></circle>
    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
    <line x1="11" y1="8" x2="11" y2="14"></line>
    <line x1="8" y1="11" x2="14" y2="11"></line>
  </svg>
);

const ZoomOutIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="11" cy="11" r="8"></circle>
    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
    <line x1="8" y1="11" x2="14" y2="11"></line>
  </svg>
);

const SunIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="5"></circle>
    <line x1="12" y1="1" x2="12" y2="3"></line>
    <line x1="12" y1="21" x2="12" y2="23"></line>
    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
    <line x1="1" y1="12" x2="3" y2="12"></line>
    <line x1="21" y1="12" x2="23" y2="12"></line>
    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
  </svg>
);

const MoonIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
  </svg>
);

export default function PathBuilder() {
  const { currentLayout, setCurrentLayout, updateLayout, addLayout, navigateTo, theme, toggleTheme } = useApp();
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  
  // State
  const [tool, setTool] = useState('select');
  const [selectedNodeType, setSelectedNodeType] = useState('intersection');
  const [selectedEdgeType, setSelectedEdgeType] = useState('taxiway');
  const [nodes, setNodes] = useState(currentLayout?.nodes || []);
  const [edges, setEdges] = useState(currentLayout?.edges || []);
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [edgeStart, setEdgeStart] = useState(null);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [showGrid, setShowGrid] = useState(true);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState(null);
  const [layoutName, setLayoutName] = useState(currentLayout?.name || 'Untitled Layout');

  const GRID_SIZE = 20;
  const NODE_RADIUS = 12;

  // Snap to grid
  const snapToGrid = (value) => Math.round(value / GRID_SIZE) * GRID_SIZE;

  // Get canvas coordinates from mouse event
  const getCanvasCoords = useCallback((e) => {
    const rect = containerRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left - pan.x) / zoom;
    const y = (e.clientY - rect.top - pan.y) / zoom;
    return { x: snapToGrid(x), y: snapToGrid(y) };
  }, [pan, zoom]);

  // Find node at position
  const findNodeAt = useCallback((x, y) => {
    return nodes.find(node => {
      const dx = node.x - x;
      const dy = node.y - y;
      return Math.sqrt(dx * dx + dy * dy) < NODE_RADIUS * 2;
    });
  }, [nodes]);

  // Handle canvas click
  const handleCanvasClick = (e) => {
    if (isDragging) return;
    
    const coords = getCanvasCoords(e);
    
    if (tool === 'node') {
      // Create new node
      const newNode = {
        id: `node-${Date.now()}`,
        type: selectedNodeType,
        x: coords.x,
        y: coords.y,
        label: NODE_TYPES[selectedNodeType].label
      };
      setNodes([...nodes, newNode]);
      setSelectedNode(newNode.id);
      setSelectedEdge(null);
    } else if (tool === 'edge') {
      const clickedNode = findNodeAt(coords.x, coords.y);
      if (clickedNode) {
        if (edgeStart) {
          if (edgeStart.id !== clickedNode.id) {
            // Create new edge
            const newEdge = {
              id: `edge-${Date.now()}`,
              from: edgeStart.id,
              to: clickedNode.id,
              type: selectedEdgeType,
              flow: 'both' // Default
            };
            setEdges([...edges, newEdge]);
            setSelectedEdge(newEdge.id);
          }
          setEdgeStart(null);
        } else {
          setEdgeStart(clickedNode);
        }
      }
    } else if (tool === 'select') {
      const clickedNode = findNodeAt(coords.x, coords.y);
      if (clickedNode) {
        setSelectedNode(clickedNode.id);
        setSelectedEdge(null);
      } else {
        // Check for edge selection
        const clickedEdge = edges.find(edge => {
          const fromNode = nodes.find(n => n.id === edge.from);
          const toNode = nodes.find(n => n.id === edge.to);
          if (!fromNode || !toNode) return false;
          
          // Simple distance to line calculation
          const dx = toNode.x - fromNode.x;
          const dy = toNode.y - fromNode.y;
          const t = Math.max(0, Math.min(1, ((coords.x - fromNode.x) * dx + (coords.y - fromNode.y) * dy) / (dx * dx + dy * dy)));
          const nearestX = fromNode.x + t * dx;
          const nearestY = fromNode.y + t * dy;
          const dist = Math.sqrt((coords.x - nearestX) ** 2 + (coords.y - nearestY) ** 2);
          return dist < 10;
        });
        
        if (clickedEdge) {
          setSelectedEdge(clickedEdge.id);
          setSelectedNode(null);
        } else {
          setSelectedNode(null);
          setSelectedEdge(null);
        }
      }
    }
  };

  // Handle mouse down for panning
  const handleMouseDown = (e) => {
    if (e.button === 1 || (e.button === 0 && e.shiftKey)) {
      setIsDragging(true);
      setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    } else if (tool === 'select' && e.button === 0) {
      const coords = getCanvasCoords(e);
      const clickedNode = findNodeAt(coords.x, coords.y);
      if (clickedNode) {
        setIsDragging(true);
        setDragStart({ nodeId: clickedNode.id, x: e.clientX, y: e.clientY, origX: clickedNode.x, origY: clickedNode.y });
      }
    }
  };

  // Handle mouse move
  const handleMouseMove = (e) => {
    if (!isDragging || !dragStart) return;
    
    if (dragStart.nodeId) {
      // Dragging a node
      const dx = (e.clientX - dragStart.x) / zoom;
      const dy = (e.clientY - dragStart.y) / zoom;
      setNodes(nodes.map(n => 
        n.id === dragStart.nodeId 
          ? { ...n, x: snapToGrid(dragStart.origX + dx), y: snapToGrid(dragStart.origY + dy) }
          : n
      ));
    } else {
      // Panning
      setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
    }
  };

  // Handle mouse up
  const handleMouseUp = () => {
    setIsDragging(false);
    setDragStart(null);
  };

  // Handle zoom
  const handleWheel = (e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom(z => Math.max(0.25, Math.min(3, z * delta)));
  };

  // Delete selected
  const handleDelete = () => {
    if (selectedNode) {
      setNodes(nodes.filter(n => n.id !== selectedNode));
      setEdges(edges.filter(e => e.from !== selectedNode && e.to !== selectedNode));
      setSelectedNode(null);
    }
    if (selectedEdge) {
      setEdges(edges.filter(e => e.id !== selectedEdge));
      setSelectedEdge(null);
    }
  };

  // Save layout
  const handleSave = () => {
    if (currentLayout?.id) {
      // Update existing layout
      updateLayout(currentLayout.id, { name: layoutName, nodes, edges });
    } else {
      // Create new layout
      const newLayout = addLayout({ name: layoutName, nodes, edges });
      setCurrentLayout(newLayout); // Switch to editing this new layout
    }
  };
  
  // Export to JSON compatible with backend schema
  const handleExportJSON = () => {
    // 1. Convert to backend format
    const backendData = {
      name: layoutName,
      version: "1.0",
      nodes: {},
      edges: {}
    };
    
    // Convert Nodes
    nodes.forEach(node => {
      backendData.nodes[node.id] = {
        type: node.type,
        x: node.x,
        y: node.y,
        name: node.label || "",
        apron: node.apron || null, // UI doesn't have this yet, maybe add property
        size_class: node.size_class || null
      };
    });
    
    // Convert Edges
    edges.forEach(edge => {
      // Calculate length
      const fromNode = nodes.find(n => n.id === edge.from);
      const toNode = nodes.find(n => n.id === edge.to);
      let length = 100; // Default
      if (fromNode && toNode) {
        length = Math.sqrt(Math.pow(toNode.x - fromNode.x, 2) + Math.pow(toNode.y - fromNode.y, 2));
      }
      
      backendData.edges[edge.id] = {
        type: edge.type,
        start: edge.from,
        end: edge.to,
        length: Math.round(length * 10) / 10, // Round to 1 decimal
        allowed_flow: edge.flow || "both",
        one_way: edge.type === 'rapid_exit', // simplified assumption
        speed_hint: null,
        capacity_hint: null,
        polyline: []
      };
    });
    
    // 2. Download file
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(backendData, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", `layout_${layoutName.replace(/\s+/g, '_').toLowerCase()}.json`);
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
  };

  // Go back
  const handleBack = () => {
    // Only save if it's an existing layout OR if we have created some content
    if (currentLayout?.id || nodes.length > 0) {
      handleSave();
    }
    navigateTo('home');
  };

  // Update selected node properties
  const updateSelectedNode = (updates) => {
    setNodes(nodes.map(n => n.id === selectedNode ? { ...n, ...updates } : n));
  };

  // Update selected edge properties
  const updateSelectedEdge = (updates) => {
    setEdges(edges.map(e => e.id === selectedEdge ? { ...e, ...updates } : e));
  };

  const selectedNodeData = nodes.find(n => n.id === selectedNode);
  const selectedEdgeData = edges.find(e => e.id === selectedEdge);

  return (
    <div className="path-builder">
      {/* Header */}
      <header className="pb-header">
        <div className="pb-header-left">
          <button className="btn btn-ghost" onClick={handleBack}>
            <ArrowLeftIcon /> Back
          </button>
          <input 
            type="text" 
            className="layout-name-input"
            value={layoutName}
            onChange={(e) => setLayoutName(e.target.value)}
          />
        </div>
        <div className="pb-header-right">
          <button className="btn btn-secondary btn-icon" onClick={toggleTheme} title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`} style={{marginRight: '0.5rem'}}>
            {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
          </button>
          <button className="btn btn-secondary" onClick={handleExportJSON} style={{marginRight: '0.5rem'}}>
            <DownloadIcon /> Export JSON
          </button>
          <button className="btn btn-primary" onClick={handleSave}>
            <SaveIcon /> Save Layout
          </button>
        </div>
      </header>

      <div className="pb-content">
        {/* Toolbar */}
        <aside className="pb-toolbar">
          <div className="toolbar-section">
            <span className="toolbar-label">Tools</span>
            <div className="tool-buttons">
              <button 
                className={`tool-btn ${tool === 'select' ? 'active' : ''}`}
                onClick={() => setTool('select')}
                title="Select (V)"
              >
                <MousePointerIcon />
              </button>
              <button 
                className={`tool-btn ${tool === 'node' ? 'active' : ''}`}
                onClick={() => setTool('node')}
                title="Add Node (N)"
              >
                <CircleIcon />
              </button>
              <button 
                className={`tool-btn ${tool === 'edge' ? 'active' : ''}`}
                onClick={() => setTool('edge')}
                title="Add Edge (E)"
              >
                <LineIcon />
              </button>
              <button 
                className="tool-btn"
                onClick={handleDelete}
                title="Delete (Del)"
                disabled={!selectedNode && !selectedEdge}
              >
                <TrashIcon />
              </button>
            </div>
          </div>

          {tool === 'node' && (
            <div className="toolbar-section">
              <span className="toolbar-label">Node Type</span>
              <div className="type-list">
                {Object.entries(NODE_TYPES).map(([key, value]) => (
                  <button
                    key={key}
                    className={`type-btn ${selectedNodeType === key ? 'active' : ''}`}
                    onClick={() => setSelectedNodeType(key)}
                    style={{ '--type-color': value.color }}
                  >
                    <span className="type-icon">{value.icon}</span>
                    <span className="type-label">{value.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {tool === 'edge' && (
            <div className="toolbar-section">
              <span className="toolbar-label">Edge Type</span>
              <div className="type-list">
                {Object.entries(EDGE_TYPES).map(([key, value]) => (
                  <button
                    key={key}
                    className={`type-btn ${selectedEdgeType === key ? 'active' : ''}`}
                    onClick={() => setSelectedEdgeType(key)}
                    style={{ '--type-color': value.color }}
                  >
                    <span className="type-line" style={{ background: value.color, height: value.width }}></span>
                    <span className="type-label">{value.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="toolbar-section">
            <span className="toolbar-label">View</span>
            <div className="tool-buttons">
              <button 
                className={`tool-btn ${showGrid ? 'active' : ''}`}
                onClick={() => setShowGrid(!showGrid)}
                title="Toggle Grid"
              >
                <GridIcon />
              </button>
              <button 
                className="tool-btn"
                onClick={() => setZoom(z => Math.min(3, z * 1.2))}
                title="Zoom In"
              >
                <ZoomInIcon />
              </button>
              <button 
                className="tool-btn"
                onClick={() => setZoom(z => Math.max(0.25, z * 0.8))}
                title="Zoom Out"
              >
                <ZoomOutIcon />
              </button>
            </div>
            <span className="zoom-level">{Math.round(zoom * 100)}%</span>
          </div>

          <div className="toolbar-section">
            <span className="toolbar-label">Stats</span>
            <div className="stats-grid">
              <div className="stat-item">
                <span className="stat-value">{nodes.length}</span>
                <span className="stat-label">Nodes</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">{edges.length}</span>
                <span className="stat-label">Edges</span>
              </div>
            </div>
          </div>
        </aside>

        {/* Canvas */}
        <div 
          ref={containerRef}
          className="pb-canvas-container"
          onClick={handleCanvasClick}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onWheel={handleWheel}
        >
          <svg 
            ref={canvasRef}
            className="pb-canvas"
            style={{ 
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              transformOrigin: '0 0'
            }}
          >
            {/* Grid */}
            {showGrid && (
              <defs>
                <pattern id="grid" width={GRID_SIZE} height={GRID_SIZE} patternUnits="userSpaceOnUse">
                  <path 
                    d={`M ${GRID_SIZE} 0 L 0 0 0 ${GRID_SIZE}`} 
                    fill="none" 
                    stroke="rgba(255,255,255,0.05)" 
                    strokeWidth="1"
                  />
                </pattern>
              </defs>
            )}
            {showGrid && <rect width="10000" height="10000" x="-5000" y="-5000" fill="url(#grid)" />}

            {/* Edges */}
            {edges.map(edge => {
              const fromNode = nodes.find(n => n.id === edge.from);
              const toNode = nodes.find(n => n.id === edge.to);
              if (!fromNode || !toNode) return null;
              
              const edgeType = EDGE_TYPES[edge.type] || EDGE_TYPES.taxiway;
              const isSelected = edge.id === selectedEdge;
              
              return (
                <g key={edge.id}>
                  <line
                    x1={fromNode.x}
                    y1={fromNode.y}
                    x2={toNode.x}
                    y2={toNode.y}
                    stroke={isSelected ? '#3b82f6' : edgeType.color}
                    strokeWidth={edgeType.width + (isSelected ? 2 : 0)}
                    strokeLinecap="round"
                    strokeDasharray={edge.type === 'rapid_exit' ? 'none' : 'none'}
                  />
                  {/* Flow direction indicator */}
                  {edge.flow !== 'both' && (
                    <polygon
                      points="-6,-4 6,0 -6,4"
                      fill={edgeType.color}
                      transform={`translate(${(fromNode.x + toNode.x) / 2}, ${(fromNode.y + toNode.y) / 2}) rotate(${Math.atan2(toNode.y - fromNode.y, toNode.x - fromNode.x) * 180 / Math.PI})`}
                    />
                  )}
                </g>
              );
            })}

            {/* Edge being drawn */}
            {edgeStart && (
              <line
                x1={edgeStart.x}
                y1={edgeStart.y}
                x2={edgeStart.x}
                y2={edgeStart.y}
                stroke="#3b82f6"
                strokeWidth="3"
                strokeDasharray="5,5"
                className="drawing-edge"
              />
            )}

            {/* Nodes */}
            {nodes.map(node => {
              const nodeType = NODE_TYPES[node.type] || NODE_TYPES.intersection;
              const isSelected = node.id === selectedNode;
              
              return (
                <g key={node.id} className="node-group">
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={NODE_RADIUS + (isSelected ? 4 : 0)}
                    fill={isSelected ? '#3b82f6' : nodeType.color}
                    stroke={isSelected ? '#fff' : 'rgba(255,255,255,0.3)'}
                    strokeWidth="2"
                    className="node-circle"
                  />
                  <text
                    x={node.x}
                    y={node.y + NODE_RADIUS + 16}
                    textAnchor="middle"
                    fill="rgba(255,255,255,0.7)"
                    fontSize="10"
                    className="node-label"
                  >
                    {node.label}
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Instructions overlay */}
          {tool === 'edge' && edgeStart && (
            <div className="canvas-overlay">
              Click another node to complete the edge, or click the same node to cancel
            </div>
          )}
        </div>

        {/* Properties Panel */}
        <aside className="pb-properties">
          <div className="panel-header">
            <h3 className="panel-title">Properties</h3>
          </div>
          
          {selectedNodeData ? (
            <div className="properties-content">
              <div className="property-group">
                <label className="label">Label</label>
                <input
                  type="text"
                  className="input"
                  value={selectedNodeData.label}
                  onChange={(e) => updateSelectedNode({ label: e.target.value })}
                />
              </div>
              <div className="property-group">
                <label className="label">Type</label>
                <select 
                  className="select"
                  value={selectedNodeData.type}
                  onChange={(e) => updateSelectedNode({ type: e.target.value })}
                >
                  {Object.entries(NODE_TYPES).map(([key, value]) => (
                    <option key={key} value={key}>{value.label}</option>
                  ))}
                </select>
              </div>
              <div className="property-row">
                <div className="property-group">
                  <label className="label">X Position</label>
                  <input
                    type="number"
                    className="input"
                    value={selectedNodeData.x}
                    onChange={(e) => updateSelectedNode({ x: Number(e.target.value) })}
                  />
                </div>
                <div className="property-group">
                  <label className="label">Y Position</label>
                  <input
                    type="number"
                    className="input"
                    value={selectedNodeData.y}
                    onChange={(e) => updateSelectedNode({ y: Number(e.target.value) })}
                  />
                </div>
              </div>
              
              {/* Extra properties based on type */}
              {(selectedNodeData.type === 'gate' || selectedNodeData.type === 'apron_center') && (
                <div className="property-group">
                  <label className="label">Apron Name</label>
                  <input
                    type="text"
                    className="input"
                    value={selectedNodeData.apron || ''}
                    onChange={(e) => updateSelectedNode({ apron: e.target.value })}
                    placeholder="e.g. Apron A"
                  />
                </div>
              )}
              
              {selectedNodeData.type === 'gate' && (
                <div className="property-group">
                  <label className="label">Max Size Class</label>
                  <select 
                    className="select"
                    value={selectedNodeData.size_class || 'medium'}
                    onChange={(e) => updateSelectedNode({ size_class: e.target.value })}
                  >
                    <option value="small">Small</option>
                    <option value="medium">Medium</option>
                    <option value="large">Large</option>
                  </select>
                </div>
              )}
              
              <button className="btn btn-danger w-full" onClick={handleDelete} style={{marginTop: '1rem'}}>
                <TrashIcon /> Delete Node
              </button>
            </div>
          ) : selectedEdgeData ? (
            <div className="properties-content">
              <div className="property-group">
                <label className="label">Type</label>
                <select 
                  className="select"
                  value={selectedEdgeData.type}
                  onChange={(e) => updateSelectedEdge({ type: e.target.value })}
                >
                  {Object.entries(EDGE_TYPES).map(([key, value]) => (
                    <option key={key} value={key}>{value.label}</option>
                  ))}
                </select>
              </div>
              <div className="property-group">
                <label className="label">Flow Direction</label>
                <select 
                  className="select"
                  value={selectedEdgeData.flow}
                  onChange={(e) => updateSelectedEdge({ flow: e.target.value })}
                >
                  {FLOW_OPTIONS.map(flow => (
                    <option key={flow} value={flow}>{flow.charAt(0).toUpperCase() + flow.slice(1)}</option>
                  ))}
                </select>
              </div>
              <button className="btn btn-danger w-full" onClick={handleDelete}>
                <TrashIcon /> Delete Edge
              </button>
            </div>
          ) : (
            <div className="no-selection">
              <p>Select a node or edge to view its properties</p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
