import { useApp } from '../context/AppContext';
import './Home.css';

// Icons as SVG components
const PlusIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="12" y1="5" x2="12" y2="19"></line>
    <line x1="5" y1="12" x2="19" y2="12"></line>
  </svg>
);

const FolderIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
  </svg>
);

const EditIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
  </svg>
);

const CopyIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
  </svg>
);

const TrashIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="3 6 5 6 21 6"></polyline>
    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
  </svg>
);

const PlayIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polygon points="5 3 19 12 5 21 5 3"></polygon>
  </svg>
);

const PlaneIcon = () => (
  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"></path>
  </svg>
);

function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { 
    month: 'short', 
    day: 'numeric', 
    year: 'numeric' 
  });
}

function LayoutCard({ layout, onEdit, onDuplicate, onDelete, onSimulate }) {
  return (
    <div className="layout-card glass-card animate-slideUp">
      <div className="layout-card-header">
        <div className="layout-icon">
          <FolderIcon />
        </div>
        <div className="layout-info">
          <h3 className="layout-name">{layout.name}</h3>
          <p className="layout-date">{formatDate(layout.createdAt)}</p>
        </div>
      </div>
      
      <div className="layout-stats">
        <div className="stat">
          <span className="stat-value">{layout.nodes?.length || 0}</span>
          <span className="stat-label">Nodes</span>
        </div>
        <div className="stat">
          <span className="stat-value">{layout.edges?.length || 0}</span>
          <span className="stat-label">Edges</span>
        </div>
        <div className="stat">
          <span className="stat-value">{layout.nodes?.filter(n => n.type === 'gate').length || 0}</span>
          <span className="stat-label">Gates</span>
        </div>
      </div>
      
      <div className="layout-actions">
        <button className="btn btn-secondary" onClick={() => onEdit(layout.id)} title="Edit Layout">
          <EditIcon /> Edit
        </button>
        <button className="btn btn-primary" onClick={() => onSimulate(layout.id)} title="Run Simulation">
          <PlayIcon /> Simulate
        </button>
      </div>
      
      <div className="layout-secondary-actions">
        <button className="btn btn-ghost btn-icon" onClick={() => onDuplicate(layout.id)} title="Duplicate">
          <CopyIcon />
        </button>
        <button className="btn btn-ghost btn-icon" onClick={() => onDelete(layout.id)} title="Delete">
          <TrashIcon />
        </button>
      </div>
    </div>
  );
}

export default function Home() {
  const { layouts, navigateTo, addLayout, duplicateLayout, deleteLayout } = useApp();

  const handleCreateNew = () => {
    const newLayout = addLayout({
      name: 'New Airport Layout',
      nodes: [],
      edges: []
    });
    navigateTo('pathBuilder', newLayout.id);
  };

  const handleEdit = (id) => {
    navigateTo('pathBuilder', id);
  };

  const handleSimulate = (id) => {
    navigateTo('simulation', id);
  };

  const handleDuplicate = (id) => {
    duplicateLayout(id);
  };

  const handleDelete = (id) => {
    if (confirm('Are you sure you want to delete this layout?')) {
      deleteLayout(id);
    }
  };

  return (
    <div className="home">
      <div className="home-header">
        <div className="logo">
          <div className="logo-icon">
            <PlaneIcon />
          </div>
          <div className="logo-text">
            <h1>Airport Ground Operations</h1>
            <p>Simulator</p>
          </div>
        </div>
      </div>

      <div className="home-content">
        <div className="section-header">
          <div>
            <h2>Your Layouts</h2>
            <p className="text-muted">Create and manage airport layouts for simulation</p>
          </div>
          <button className="btn btn-primary btn-lg" onClick={handleCreateNew}>
            <PlusIcon /> Create New Layout
          </button>
        </div>

        {layouts.length === 0 ? (
          <div className="empty-state glass-card">
            <div className="empty-icon">
              <FolderIcon />
            </div>
            <h3>No Layouts Yet</h3>
            <p>Create your first airport layout to get started with simulations.</p>
            <button className="btn btn-primary btn-lg" onClick={handleCreateNew}>
              <PlusIcon /> Create Your First Layout
            </button>
          </div>
        ) : (
          <div className="layouts-grid">
            {layouts.map((layout) => (
              <LayoutCard
                key={layout.id}
                layout={layout}
                onEdit={handleEdit}
                onDuplicate={handleDuplicate}
                onDelete={handleDelete}
                onSimulate={handleSimulate}
              />
            ))}
          </div>
        )}
      </div>

      <footer className="home-footer">
        <p>Airport Ground Operations Simulator v1.0 • Research-grade simulation engine</p>
      </footer>
    </div>
  );
}
