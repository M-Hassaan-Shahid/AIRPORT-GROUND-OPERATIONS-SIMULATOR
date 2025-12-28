import { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import './Graphs.css';

// Icons
const ArrowLeftIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="19" y1="12" x2="5" y2="12"></line>
    <polyline points="12 19 5 12 12 5"></polyline>
  </svg>
);

const DownloadIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
    <polyline points="7 10 12 15 17 10"></polyline>
    <line x1="12" y1="15" x2="12" y2="3"></line>
  </svg>
);

const ImageIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
    <circle cx="8.5" cy="8.5" r="1.5"></circle>
    <polyline points="21 15 16 10 5 21"></polyline>
  </svg>
);

const FileIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
    <polyline points="14 2 14 8 20 8"></polyline>
    <line x1="16" y1="13" x2="8" y2="13"></line>
    <line x1="16" y1="17" x2="8" y2="17"></line>
    <polyline points="10 9 9 9 8 9"></polyline>
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

// Generate mock time-series data
function generateMockData() {
  const timePoints = 60;
  const data = {
    aircraftOnGround: [],
    queueLengths: [],
    runwayThroughput: [],
    taxiTimes: [],
    waitTimes: []
  };
  
  for (let i = 0; i < timePoints; i++) {
    const t = i * 60; // seconds
    data.aircraftOnGround.push({
      x: t,
      y: Math.floor(5 + Math.sin(i / 10) * 3 + Math.random() * 5)
    });
    data.queueLengths.push({
      x: t,
      y: Math.floor(Math.max(0, 2 + Math.sin(i / 8) * 2 + Math.random() * 2))
    });
    data.runwayThroughput.push({
      x: t,
      y: Math.floor(Math.random() * 4)
    });
  }
  
  // Histograms
  for (let i = 0; i < 20; i++) {
    data.taxiTimes.push(Math.floor(120 + Math.random() * 240));
    data.waitTimes.push(Math.floor(10 + Math.random() * 60));
  }
  
  return data;
}

// Simple chart components (no external library needed)
function LineChart({ data, title, color = '#3b82f6', yLabel = '', xLabel = 'Time (s)' }) {
  if (!data || data.length === 0) return null;
  
  const maxY = Math.max(...data.map(d => d.y));
  const maxX = Math.max(...data.map(d => d.x));
  const minY = 0;
  
  const width = 400;
  const height = 200;
  const padding = { top: 20, right: 20, bottom: 40, left: 50 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  
  const scaleX = (x) => padding.left + (x / maxX) * chartWidth;
  const scaleY = (y) => height - padding.bottom - ((y - minY) / (maxY - minY || 1)) * chartHeight;
  
  const pathData = data.map((d, i) => 
    `${i === 0 ? 'M' : 'L'} ${scaleX(d.x)} ${scaleY(d.y)}`
  ).join(' ');
  
  const areaData = pathData + ` L ${scaleX(maxX)} ${height - padding.bottom} L ${padding.left} ${height - padding.bottom} Z`;
  
  return (
    <div className="chart-container">
      <h4 className="chart-title">{title}</h4>
      <svg viewBox={`0 0 ${width} ${height}`} className="chart-svg">
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map(ratio => (
          <g key={ratio}>
            <line
              x1={padding.left}
              y1={padding.top + ratio * chartHeight}
              x2={width - padding.right}
              y2={padding.top + ratio * chartHeight}
              stroke="var(--border-color)"
              strokeDasharray="4,4"
            />
            <text
              x={padding.left - 8}
              y={padding.top + ratio * chartHeight + 4}
              textAnchor="end"
              fill="var(--text-muted)"
              fontSize="10"
            >
              {Math.round(maxY * (1 - ratio))}
            </text>
          </g>
        ))}
        
        {/* Area under curve */}
        <path
          d={areaData}
          fill={`url(#gradient-${color.slice(1)})`}
          opacity="0.3"
        />
        
        {/* Gradient definition */}
        <defs>
          <linearGradient id={`gradient-${color.slice(1)}`} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.5" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>
        
        {/* Line */}
        <path
          d={pathData}
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinejoin="round"
        />
        
        {/* Data points */}
        {data.filter((_, i) => i % 5 === 0).map((d, i) => (
          <circle
            key={i}
            cx={scaleX(d.x)}
            cy={scaleY(d.y)}
            r="3"
            fill={color}
          />
        ))}
        
        {/* Axes labels */}
        <text
          x={width / 2}
          y={height - 5}
          textAnchor="middle"
          fill="var(--text-secondary)"
          fontSize="11"
        >
          {xLabel}
        </text>
        <text
          x={15}
          y={height / 2}
          textAnchor="middle"
          fill="var(--text-secondary)"
          fontSize="11"
          transform={`rotate(-90, 15, ${height / 2})`}
        >
          {yLabel}
        </text>
      </svg>
    </div>
  );
}

function BarChart({ data, title, color = '#8b5cf6', xLabel = 'Value', yLabel = 'Frequency' }) {
  if (!data || data.length === 0) return null;
  
  // Create histogram bins
  const min = Math.min(...data);
  const max = Math.max(...data);
  const binCount = 10;
  const binWidth = (max - min) / binCount || 1;
  const bins = Array(binCount).fill(0);
  
  data.forEach(value => {
    const binIndex = Math.min(Math.floor((value - min) / binWidth), binCount - 1);
    bins[binIndex]++;
  });
  
  const maxBin = Math.max(...bins);
  
  const width = 400;
  const height = 200;
  const padding = { top: 20, right: 20, bottom: 40, left: 50 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  const barWidth = chartWidth / binCount - 4;
  
  return (
    <div className="chart-container">
      <h4 className="chart-title">{title}</h4>
      <svg viewBox={`0 0 ${width} ${height}`} className="chart-svg">
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map(ratio => (
          <line
            key={ratio}
            x1={padding.left}
            y1={padding.top + ratio * chartHeight}
            x2={width - padding.right}
            y2={padding.top + ratio * chartHeight}
            stroke="var(--border-color)"
            strokeDasharray="4,4"
          />
        ))}
        
        {/* Bars */}
        {bins.map((count, i) => {
          const barHeight = (count / maxBin) * chartHeight;
          const x = padding.left + (i * (chartWidth / binCount)) + 2;
          const y = height - padding.bottom - barHeight;
          
          return (
            <g key={i}>
              <rect
                x={x}
                y={y}
                width={barWidth}
                height={barHeight}
                fill={color}
                rx="2"
                opacity="0.8"
              />
              <rect
                x={x}
                y={y}
                width={barWidth}
                height={Math.min(4, barHeight)}
                fill="white"
                rx="2"
                opacity="0.3"
              />
            </g>
          );
        })}
        
        {/* Axes labels */}
        <text
          x={width / 2}
          y={height - 5}
          textAnchor="middle"
          fill="var(--text-secondary)"
          fontSize="11"
        >
          {xLabel}
        </text>
      </svg>
    </div>
  );
}

function StatCard({ label, value, unit, trend }) {
  return (
    <div className="stat-card glass-card">
      <span className="stat-label">{label}</span>
      <div className="stat-value-row">
        <span className="stat-value">{value}</span>
        {unit && <span className="stat-unit">{unit}</span>}
      </div>
      {trend && (
        <span className={`stat-trend ${trend > 0 ? 'up' : 'down'}`}>
          {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}%
        </span>
      )}
    </div>
  );
}

export default function Graphs() {
  const { navigateTo, currentLayout, theme, toggleTheme } = useApp();
  const [data, setData] = useState(null);
  const [selectedChart, setSelectedChart] = useState('all');

  useEffect(() => {
    // Generate mock data on mount
    setData(generateMockData());
  }, []);

  const handleBack = () => {
    navigateTo('simulation', currentLayout?.id);
  };

  const handleExportPNG = () => {
    alert('Export to PNG functionality would be implemented here');
  };

  const handleExportCSV = () => {
    alert('Export to CSV functionality would be implemented here');
  };

  if (!data) {
    return (
      <div className="graphs loading">
        <div className="loader"></div>
        <p>Loading data...</p>
      </div>
    );
  }

  // Calculate summary statistics
  const avgAircraft = (data.aircraftOnGround.reduce((sum, d) => sum + d.y, 0) / data.aircraftOnGround.length).toFixed(1);
  const maxQueue = Math.max(...data.queueLengths.map(d => d.y));
  const totalThroughput = data.runwayThroughput.reduce((sum, d) => sum + d.y, 0);
  const avgTaxiTime = (data.taxiTimes.reduce((a, b) => a + b, 0) / data.taxiTimes.length).toFixed(0);

  return (
    <div className="graphs">
      {/* Header */}
      <header className="graphs-header">
        <div className="graphs-header-left">
          <button className="btn btn-ghost" onClick={handleBack}>
            <ArrowLeftIcon /> Back to Simulation
          </button>
          <h1 className="graphs-title">Results & Analysis</h1>
        </div>
        <div className="graphs-header-right">
          <button className="btn btn-secondary btn-icon" onClick={toggleTheme} title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`} style={{marginRight: '0.5rem'}}>
            {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
          </button>
          <button className="btn btn-secondary" onClick={handleExportPNG}>
            <ImageIcon /> Export PNG
          </button>
          <button className="btn btn-secondary" onClick={handleExportCSV}>
            <FileIcon /> Export CSV
          </button>
        </div>
      </header>

      <div className="graphs-content">
        {/* Sidebar */}
        <aside className="graphs-sidebar">
          <div className="sidebar-section">
            <h3>Summary Statistics</h3>
            <div className="stats-grid">
              <StatCard label="Avg. Aircraft" value={avgAircraft} />
              <StatCard label="Max Queue" value={maxQueue} />
              <StatCard label="Throughput" value={totalThroughput} unit="ops" />
              <StatCard label="Avg. Taxi Time" value={avgTaxiTime} unit="s" />
            </div>
          </div>

          <div className="sidebar-section">
            <h3>View</h3>
            <div className="view-options">
              {[
                { id: 'all', label: 'All Charts' },
                { id: 'timeseries', label: 'Time Series' },
                { id: 'histograms', label: 'Histograms' },
              ].map(option => (
                <button
                  key={option.id}
                  className={`view-option ${selectedChart === option.id ? 'active' : ''}`}
                  onClick={() => setSelectedChart(option.id)}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          <div className="sidebar-section">
            <h3>Layout Info</h3>
            <div className="info-list">
              <div className="info-item">
                <span className="info-label">Name</span>
                <span className="info-value">{currentLayout?.name || 'N/A'}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Duration</span>
                <span className="info-value">60 min</span>
              </div>
              <div className="info-item">
                <span className="info-label">Data Points</span>
                <span className="info-value">{data.aircraftOnGround.length}</span>
              </div>
            </div>
          </div>
        </aside>

        {/* Charts Grid */}
        <main className="charts-area">
          {(selectedChart === 'all' || selectedChart === 'timeseries') && (
            <section className="charts-section">
              <h2>Time Series</h2>
              <div className="charts-grid">
                <LineChart
                  data={data.aircraftOnGround}
                  title="Aircraft on Ground"
                  color="#3b82f6"
                  yLabel="Count"
                />
                <LineChart
                  data={data.queueLengths}
                  title="Queue Length at Hold Points"
                  color="#10b981"
                  yLabel="Aircraft"
                />
                <LineChart
                  data={data.runwayThroughput}
                  title="Runway Throughput"
                  color="#f59e0b"
                  yLabel="Operations"
                />
              </div>
            </section>
          )}

          {(selectedChart === 'all' || selectedChart === 'histograms') && (
            <section className="charts-section">
              <h2>Distributions</h2>
              <div className="charts-grid">
                <BarChart
                  data={data.taxiTimes}
                  title="Taxi Time Distribution"
                  color="#8b5cf6"
                  xLabel="Time (seconds)"
                />
                <BarChart
                  data={data.waitTimes}
                  title="Wait Time Distribution"
                  color="#ec4899"
                  xLabel="Time (seconds)"
                />
              </div>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}
