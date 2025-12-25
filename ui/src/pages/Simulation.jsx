import { useState, useEffect, useRef } from 'react';
import { useApp } from '../context/AppContext';
import './Simulation.css';

// Icons
const ArrowLeftIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="19" y1="12" x2="5" y2="12"></line>
    <polyline points="12 19 5 12 12 5"></polyline>
  </svg>
);

const PlayIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
    <polygon points="5 3 19 12 5 21 5 3"></polygon>
  </svg>
);

const PauseIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
    <rect x="6" y="4" width="4" height="16"></rect>
    <rect x="14" y="4" width="4" height="16"></rect>
  </svg>
);

const StopIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
    <rect x="4" y="4" width="16" height="16" rx="2"></rect>
  </svg>
);

const RefreshIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="23 4 23 10 17 10"></polyline>
    <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
  </svg>
);

const ChartIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="18" y1="20" x2="18" y2="10"></line>
    <line x1="12" y1="20" x2="12" y2="4"></line>
    <line x1="6" y1="20" x2="6" y2="14"></line>
  </svg>
);

const ChevronDownIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="6 9 12 15 18 9"></polyline>
  </svg>
);

const ChevronUpIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="18 15 12 9 6 15"></polyline>
  </svg>
);

// Node/Edge type configurations
const NODE_TYPES = {
  intersection: { color: '#6b7280' },
  runway_end: { color: '#ef4444' },
  runway_entry: { color: '#f97316' },
  runway_exit: { color: '#eab308' },
  hold_point: { color: '#f87171' },
  gate: { color: '#34d399' },
  apron_center: { color: '#60a5fa' },
};

const EDGE_TYPES = {
  runway: { color: '#4b5563', width: 8 },
  taxiway: { color: '#fbbf24', width: 4 },
  apron_link: { color: '#60a5fa', width: 3 },
};

// Parameter categories
const PARAM_CATEGORIES = [
  {
    id: 'traffic',
    label: 'Traffic',
    icon: '✈️',
    params: [
      { key: 'departure_spawn_rate', label: 'Departure Spawn Rate', type: 'slider', min: 0, max: 2, step: 0.1, unit: '/min' },
      { key: 'arrival_spawn_rate', label: 'Arrival Spawn Rate', type: 'slider', min: 0, max: 2, step: 0.1, unit: '/min' },
      { key: 'traffic_mode', label: 'Traffic Mode', type: 'select', options: ['mixed', 'departures_only', 'arrivals_only'] },
    ]
  },
  {
    id: 'environment',
    label: 'Environment',
    icon: '🌤️',
    params: [
      { key: 'weather_condition', label: 'Weather', type: 'select', options: ['good', 'mild', 'bad'] },
      { key: 'wind_speed', label: 'Wind Speed', type: 'slider', min: 0, max: 25, step: 1, unit: 'm/s' },
      { key: 'wind_direction', label: 'Wind Direction', type: 'slider', min: 0, max: 360, step: 5, unit: '°' },
    ]
  },
  {
    id: 'movement',
    label: 'Movement',
    icon: '🚀',
    params: [
      { key: 'speed_base_small', label: 'Small Aircraft Speed', type: 'slider', min: 1, max: 15, step: 0.5, unit: 'm/s' },
      { key: 'speed_base_medium', label: 'Medium Aircraft Speed', type: 'slider', min: 1, max: 15, step: 0.5, unit: 'm/s' },
      { key: 'speed_base_large', label: 'Large Aircraft Speed', type: 'slider', min: 1, max: 15, step: 0.5, unit: 'm/s' },
    ]
  },
  {
    id: 'separation',
    label: 'Separation',
    icon: '↔️',
    params: [
      { key: 'separation_runway', label: 'Runway Separation', type: 'slider', min: 50, max: 200, step: 10, unit: 'm' },
      { key: 'separation_taxiway', label: 'Taxiway Separation', type: 'slider', min: 20, max: 100, step: 5, unit: 'm' },
      { key: 'separation_apron', label: 'Apron Separation', type: 'slider', min: 10, max: 60, step: 5, unit: 'm' },
    ]
  },
  {
    id: 'priority',
    label: 'Priority',
    icon: '📋',
    params: [
      { key: 'runway_priority_mode', label: 'Runway Priority', type: 'select', options: ['fifo', 'depart_first', 'arrive_first', 'weighted'] },
      { key: 'intersection_priority_mode', label: 'Intersection Priority', type: 'select', options: ['fifo', 'random', 'weighted'] },
    ]
  },
  {
    id: 'simulation',
    label: 'Simulation',
    icon: '⚙️',
    params: [
      { key: 'total_duration', label: 'Duration', type: 'slider', min: 600, max: 7200, step: 300, unit: 's' },
      { key: 'time_step_size', label: 'Time Step', type: 'slider', min: 0.5, max: 5, step: 0.5, unit: 's' },
      { key: 'random_seed', label: 'Random Seed', type: 'number', min: 0, max: 9999 },
    ]
  },
];

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function ParamSlider({ param, value, onChange }) {
  // Calculate fill percentage for the track
  const fillPercent = ((value - param.min) / (param.max - param.min)) * 100;
  
  return (
    <div className="param-control">
      <div className="param-header">
        <label className="param-label">{param.label}</label>
        <span className="param-value">{value}{param.unit || ''}</span>
      </div>
      <div className="slider-container">
        <span className="slider-limit slider-limit-min">{param.min}</span>
        <div className="slider-track-wrapper">
          <input
            type="range"
            className="slider"
            min={param.min}
            max={param.max}
            step={param.step}
            value={value}
            onChange={(e) => onChange(Number(e.target.value))}
            style={{ '--fill-percent': `${fillPercent}%` }}
          />
        </div>
        <span className="slider-limit slider-limit-max">{param.max}</span>
      </div>
    </div>
  );
}

function ParamSelect({ param, value, onChange }) {
  return (
    <div className="param-control">
      <label className="param-label">{param.label}</label>
      <select className="select" value={value} onChange={(e) => onChange(e.target.value)}>
        {param.options.map(opt => (
          <option key={opt} value={opt}>
            {opt.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
          </option>
        ))}
      </select>
    </div>
  );
}

function ParamNumber({ param, value, onChange }) {
  return (
    <div className="param-control">
      <label className="param-label">{param.label}</label>
      <input
        type="number"
        className="input"
        min={param.min}
        max={param.max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  );
}

function CategoryPanel({ category, params, updateParams, expanded, onToggle }) {
  return (
    <div className={`category-panel ${expanded ? 'expanded' : ''}`}>
      <button className="category-header" onClick={onToggle}>
        <span className="category-icon">{category.icon}</span>
        <span className="category-label">{category.label}</span>
        {expanded ? <ChevronUpIcon /> : <ChevronDownIcon />}
      </button>
      {expanded && (
        <div className="category-content">
          {category.params.map(param => {
            const ParamComponent = param.type === 'slider' ? ParamSlider 
              : param.type === 'select' ? ParamSelect 
              : ParamNumber;
            return (
              <ParamComponent
                key={param.key}
                param={param}
                value={params[param.key]}
                onChange={(value) => updateParams(param.key, value)}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

// Generate mock aircraft for demo
function generateMockAircraft(nodes, edges, count = 5) {
  const aircraft = [];
  const gates = nodes.filter(n => n.type === 'gate');
  const taxiways = edges.filter(e => e.type === 'taxiway');
  
  for (let i = 0; i < count; i++) {
    const randomEdge = taxiways[Math.floor(Math.random() * taxiways.length)] || edges[0];
    if (randomEdge) {
      const fromNode = nodes.find(n => n.id === randomEdge.from);
      const toNode = nodes.find(n => n.id === randomEdge.to);
      if (fromNode && toNode) {
        const t = Math.random();
        aircraft.push({
          id: `ac-${i}`,
          x: fromNode.x + (toNode.x - fromNode.x) * t,
          y: fromNode.y + (toNode.y - fromNode.y) * t,
          type: ['small', 'medium', 'large'][Math.floor(Math.random() * 3)],
          status: ['taxiing', 'waiting', 'moving'][Math.floor(Math.random() * 3)],
          rotation: Math.atan2(toNode.y - fromNode.y, toNode.x - fromNode.x) * 180 / Math.PI
        });
      }
    }
  }
  return aircraft;
}

export default function Simulation() {
  const { currentLayout, params, updateParams, navigateTo, simulationState, 
    startSimulation, pauseSimulation, resumeSimulation, stopSimulation, 
    resetSimulation, setSimulationSpeed } = useApp();
  
  const [expandedCategory, setExpandedCategory] = useState('traffic');
  const [aircraft, setAircraft] = useState([]);
  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  
  const nodes = currentLayout?.nodes || [];
  const edges = currentLayout?.edges || [];

  // Initialize mock aircraft
  useEffect(() => {
    if (simulationState.running) {
      setAircraft(generateMockAircraft(nodes, edges, 8));
    }
  }, [simulationState.running, nodes.length]);

  // Animation loop for aircraft movement
  useEffect(() => {
    if (simulationState.running && !simulationState.paused) {
      const animate = () => {
        setAircraft(prev => prev.map(ac => ({
          ...ac,
          x: ac.x + (Math.random() - 0.5) * 2 * simulationState.speed,
          y: ac.y + (Math.random() - 0.5) * 2 * simulationState.speed,
        })));
        animationRef.current = requestAnimationFrame(animate);
      };
      animationRef.current = requestAnimationFrame(animate);
    }
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [simulationState.running, simulationState.paused, simulationState.speed]);

  const handleBack = () => {
    stopSimulation();
    navigateTo('home');
  };

  const handleViewGraphs = () => {
    navigateTo('graphs');
  };

  const progress = (simulationState.currentTime / params.total_duration) * 100;

  return (
    <div className="simulation">
      {/* Header */}
      <header className="sim-header">
        <div className="sim-header-left">
          <button className="btn btn-ghost" onClick={handleBack}>
            <ArrowLeftIcon /> Back
          </button>
          <h1 className="sim-title">{currentLayout?.name || 'Simulation'}</h1>
          {simulationState.running && (
            <span className={`sim-status ${simulationState.paused ? 'paused' : 'running'}`}>
              {simulationState.paused ? 'Paused' : 'Running'}
            </span>
          )}
        </div>
        <div className="sim-header-right">
          <button className="btn btn-secondary" onClick={handleViewGraphs}>
            <ChartIcon /> View Graphs
          </button>
        </div>
      </header>

      <div className="sim-content">
        {/* Canvas */}
        <div className="sim-canvas-area">
          <div className="sim-canvas-container">
            <svg ref={canvasRef} className="sim-canvas" viewBox="0 0 800 600">
              {/* Background */}
              <rect width="800" height="600" fill="#0a0f1a" />
              
              {/* Edges */}
              {edges.map(edge => {
                const fromNode = nodes.find(n => n.id === edge.from);
                const toNode = nodes.find(n => n.id === edge.to);
                if (!fromNode || !toNode) return null;
                const edgeType = EDGE_TYPES[edge.type] || EDGE_TYPES.taxiway;
                return (
                  <line
                    key={edge.id}
                    x1={fromNode.x}
                    y1={fromNode.y}
                    x2={toNode.x}
                    y2={toNode.y}
                    stroke={edgeType.color}
                    strokeWidth={edgeType.width}
                    strokeLinecap="round"
                    opacity="0.8"
                  />
                );
              })}
              
              {/* Nodes */}
              {nodes.map(node => {
                const nodeType = NODE_TYPES[node.type] || NODE_TYPES.intersection;
                return (
                  <g key={node.id}>
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r="10"
                      fill={nodeType.color}
                      stroke="rgba(255,255,255,0.3)"
                      strokeWidth="2"
                    />
                    {node.label && (
                      <text
                        x={node.x}
                        y={node.y + 22}
                        textAnchor="middle"
                        fill="rgba(255,255,255,0.6)"
                        fontSize="9"
                      >
                        {node.label}
                      </text>
                    )}
                  </g>
                );
              })}
              
              {/* Aircraft */}
              {aircraft.map(ac => (
                <g key={ac.id} transform={`translate(${ac.x}, ${ac.y}) rotate(${ac.rotation})`}>
                  <path
                    d="M-8,-6 L8,0 L-8,6 L-4,0 Z"
                    fill={ac.type === 'large' ? '#ef4444' : ac.type === 'medium' ? '#3b82f6' : '#10b981'}
                    stroke="white"
                    strokeWidth="1"
                  />
                  <circle
                    r="12"
                    fill="none"
                    stroke={ac.status === 'waiting' ? '#f59e0b' : 'transparent'}
                    strokeWidth="2"
                    strokeDasharray="4,2"
                    className={ac.status === 'waiting' ? 'pulse-ring' : ''}
                  />
                </g>
              ))}
            </svg>

            {/* Empty state */}
            {nodes.length === 0 && (
              <div className="canvas-empty">
                <p>No layout loaded. Please go back and select a layout.</p>
              </div>
            )}
          </div>

          {/* Controls bar */}
          <div className="sim-controls">
            <div className="controls-left">
              {!simulationState.running ? (
                <button className="btn btn-primary btn-lg" onClick={startSimulation}>
                  <PlayIcon /> Start Simulation
                </button>
              ) : simulationState.paused ? (
                <button className="btn btn-primary" onClick={resumeSimulation}>
                  <PlayIcon /> Resume
                </button>
              ) : (
                <button className="btn btn-secondary" onClick={pauseSimulation}>
                  <PauseIcon /> Pause
                </button>
              )}
              <button 
                className="btn btn-secondary" 
                onClick={stopSimulation}
                disabled={!simulationState.running}
              >
                <StopIcon /> Stop
              </button>
              <button className="btn btn-ghost" onClick={resetSimulation}>
                <RefreshIcon /> Reset
              </button>
            </div>

            <div className="controls-center">
              <div className="progress-container">
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${progress}%` }} />
                </div>
                <div className="progress-labels">
                  <span>{formatTime(simulationState.currentTime)}</span>
                  <span>{formatTime(params.total_duration)}</span>
                </div>
              </div>
            </div>

            <div className="controls-right">
              <span className="speed-label">Speed:</span>
              <div className="speed-buttons">
                {[1, 2, 4, 8].map(speed => (
                  <button
                    key={speed}
                    className={`speed-btn ${simulationState.speed === speed ? 'active' : ''}`}
                    onClick={() => setSimulationSpeed(speed)}
                  >
                    {speed}x
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Legend */}
          <div className="sim-legend">
            <div className="legend-section">
              <span className="legend-title">Aircraft</span>
              <div className="legend-items">
                <div className="legend-item">
                  <span className="legend-dot" style={{ background: '#10b981' }}></span>
                  Small
                </div>
                <div className="legend-item">
                  <span className="legend-dot" style={{ background: '#3b82f6' }}></span>
                  Medium
                </div>
                <div className="legend-item">
                  <span className="legend-dot" style={{ background: '#ef4444' }}></span>
                  Large
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Parameters Panel */}
        <aside className="sim-params">
          <div className="params-header">
            <h3>Parameters</h3>
            <span className="badge badge-primary">
              {simulationState.running ? 'Read-only' : 'Editable'}
            </span>
          </div>
          <div className="params-content">
            {PARAM_CATEGORIES.map(category => (
              <CategoryPanel
                key={category.id}
                category={category}
                params={params}
                updateParams={updateParams}
                expanded={expandedCategory === category.id}
                onToggle={() => setExpandedCategory(expandedCategory === category.id ? null : category.id)}
              />
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}
