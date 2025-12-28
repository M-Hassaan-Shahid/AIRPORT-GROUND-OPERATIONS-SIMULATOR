import { createContext, useContext, useState, useEffect } from 'react';

const AppContext = createContext();

// Sample layouts for demo
const sampleLayouts = [
  {
    id: '1',
    name: 'Sample Airport - Basic',
    createdAt: new Date().toISOString(),
    nodes: [
      { id: 'rwy1-start', type: 'runway_end', x: 100, y: 300, label: 'RWY 09L' },
      { id: 'rwy1-end', type: 'runway_end', x: 700, y: 300, label: 'RWY 27R' },
      { id: 'hold1', type: 'hold_point', x: 350, y: 350, label: 'Hold A' },
      { id: 'int1', type: 'intersection', x: 350, y: 300, label: '' },
      { id: 'gate1', type: 'gate', x: 200, y: 500, label: 'Gate 1' },
      { id: 'gate2', type: 'gate', x: 350, y: 500, label: 'Gate 2' },
      { id: 'gate3', type: 'gate', x: 500, y: 500, label: 'Gate 3' },
      { id: 'apron1', type: 'apron_center', x: 350, y: 420, label: 'Apron A' },
    ],
    edges: [
      { id: 'e1', from: 'rwy1-start', to: 'int1', type: 'runway', flow: 'both' },
      { id: 'e2', from: 'int1', to: 'rwy1-end', type: 'runway', flow: 'both' },
      { id: 'e3', from: 'int1', to: 'hold1', type: 'taxiway', flow: 'both' },
      { id: 'e4', from: 'hold1', to: 'apron1', type: 'taxiway', flow: 'both' },
      { id: 'e5', from: 'apron1', to: 'gate1', type: 'apron_link', flow: 'both' },
      { id: 'e6', from: 'apron1', to: 'gate2', type: 'apron_link', flow: 'both' },
      { id: 'e7', from: 'apron1', to: 'gate3', type: 'apron_link', flow: 'both' },
    ]
  }
];

const defaultParams = {
  // Traffic
  departure_spawn_rate: 0.5,
  arrival_spawn_rate: 0.3,
  departure_class_mix: { small: 0.2, medium: 0.5, large: 0.3 },
  arrival_class_mix: { small: 0.3, medium: 0.4, large: 0.3 },
  traffic_mode: 'mixed',
  
  // Environment
  weather_condition: 'good',
  wind_speed: 0,
  wind_direction: 180,
  
  // Movement
  speed_base_small: 5,
  speed_base_medium: 6,
  speed_base_large: 4,
  speed_mult_runway: 1.0,
  speed_mult_taxiway: 0.8,
  speed_mult_apron: 0.5,
  
  // Separation
  separation_runway: 100,
  separation_taxiway: 50,
  separation_apron: 30,
  
  // Priority
  runway_priority_mode: 'fifo',
  intersection_priority_mode: 'fifo',
  hold_release_priority: 'fifo',
  
  // Capacity
  gate_capacity_apron_A: 10,
  gate_capacity_apron_B: 8,
  runway_capacity: 1,
  
  // Simulation
  time_step_size: 1.0,
  total_duration: 3600,
  random_seed: 42
};

export function AppProvider({ children }) {
  const [currentScreen, setCurrentScreen] = useState('home');
  const [layouts, setLayouts] = useState([]);
  const [currentLayout, setCurrentLayout] = useState(null);
  const [params, setParams] = useState(defaultParams);
  const [theme, setTheme] = useState('dark');
  const [simulationState, setSimulationState] = useState({
    running: false,
    paused: false,
    currentTime: 0,
    speed: 1,
    aircraft: []
  });
  const [results, setResults] = useState(null);

  // Load theme from localStorage and apply
  useEffect(() => {
    const savedTheme = localStorage.getItem('airport-theme') || 'dark';
    setTheme(savedTheme);
    document.documentElement.setAttribute('data-theme', savedTheme);
  }, []);

  // Toggle theme function
  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    localStorage.setItem('airport-theme', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
  };

  // Load layouts from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('airport-layouts');
    if (saved) {
      setLayouts(JSON.parse(saved));
    } else {
      setLayouts(sampleLayouts);
      localStorage.setItem('airport-layouts', JSON.stringify(sampleLayouts));
    }
  }, []);

  // Save layouts to localStorage
  const saveLayouts = (newLayouts) => {
    setLayouts(newLayouts);
    localStorage.setItem('airport-layouts', JSON.stringify(newLayouts));
  };

  const addLayout = (layout) => {
    const newLayout = {
      ...layout,
      id: Date.now().toString(),
      createdAt: new Date().toISOString()
    };
    saveLayouts([...layouts, newLayout]);
    return newLayout;
  };

  const updateLayout = (id, updates) => {
    saveLayouts(layouts.map(l => l.id === id ? { ...l, ...updates } : l));
  };

  const deleteLayout = (id) => {
    saveLayouts(layouts.filter(l => l.id !== id));
  };

  const duplicateLayout = (id) => {
    const layout = layouts.find(l => l.id === id);
    if (layout) {
      addLayout({ ...layout, name: `${layout.name} (Copy)` });
    }
  };

  const navigateTo = (screen, layoutId = null) => {
    if (layoutId) {
      const layout = layouts.find(l => l.id === layoutId);
      setCurrentLayout(layout);
    }
    setCurrentScreen(screen);
  };

  const updateParams = (key, value) => {
    setParams(prev => ({ ...prev, [key]: value }));
  };

  const resetParams = () => {
    setParams(defaultParams);
  };

  // Mock simulation functions
  const startSimulation = () => {
    setSimulationState(prev => ({ ...prev, running: true, paused: false }));
  };

  const pauseSimulation = () => {
    setSimulationState(prev => ({ ...prev, paused: true }));
  };

  const resumeSimulation = () => {
    setSimulationState(prev => ({ ...prev, paused: false }));
  };

  const stopSimulation = () => {
    setSimulationState({ running: false, paused: false, currentTime: 0, speed: 1, aircraft: [] });
  };

  const resetSimulation = () => {
    stopSimulation();
    setResults(null);
  };

  const setSimulationSpeed = (speed) => {
    setSimulationState(prev => ({ ...prev, speed }));
  };

  const value = {
    currentScreen,
    navigateTo,
    layouts,
    currentLayout,
    setCurrentLayout,
    addLayout,
    updateLayout,
    deleteLayout,
    duplicateLayout,
    params,
    updateParams,
    resetParams,
    simulationState,
    startSimulation,
    pauseSimulation,
    resumeSimulation,
    stopSimulation,
    resetSimulation,
    setSimulationSpeed,
    results,
    setResults,
    theme,
    toggleTheme
  };

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within AppProvider');
  }
  return context;
}
