import { AppProvider, useApp } from './context/AppContext';
import Home from './pages/Home';
import PathBuilder from './pages/PathBuilder';
import Simulation from './pages/Simulation';
import Graphs from './pages/Graphs';
import './App.css';

function AppContent() {
  const { currentScreen } = useApp();

  switch (currentScreen) {
    case 'pathBuilder':
      return <PathBuilder />;
    case 'simulation':
      return <Simulation />;
    case 'graphs':
      return <Graphs />;
    default:
      return <Home />;
  }
}

function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}

export default App;
