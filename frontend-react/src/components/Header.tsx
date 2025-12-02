import { useState, useEffect, type FC, useMemo } from 'react';

type View = 'ask' | 'sources' | 'ingest' | 'admin' | 'assets' | 'history';

interface Workspace {
  id: string;
  name: string;
  default_engine?: string;
}

interface HeaderProps {
  active: View;
  onNavigate: (view: View) => void;
  currentWorkspace?: string;
  onWorkspaceChange?: (workspaceId: string) => void;
}

const Header: FC<HeaderProps> = ({ active, onNavigate, currentWorkspace: propWorkspace, onWorkspaceChange }) => {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [currentWorkspace, setCurrentWorkspace] = useState<string>(propWorkspace || '');
  const [userName] = useState('Operator');
  const [showCreateWorkspace, setShowCreateWorkspace] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState('');

  const loadWorkspaces = async () => {
    try {
      const res = await fetch('/api/v1/workspaces');
      if (res.ok) {
        const data = await res.json();
        const ws = data.workspaces || [];
        setWorkspaces(ws);
        // Set first workspace as default if none selected
        if (ws.length > 0 && !currentWorkspace) {
          const firstId = ws[0].id;
          setCurrentWorkspace(firstId);
          onWorkspaceChange?.(firstId);
        }
      }
    } catch (err) {
      console.error('Failed to load workspaces:', err);
    }
  };

  useEffect(() => {
    loadWorkspaces();
  }, []);

  useEffect(() => {
    if (propWorkspace && propWorkspace !== currentWorkspace) {
      setCurrentWorkspace(propWorkspace);
    }
  }, [propWorkspace]);

  const handleWorkspaceChange = async (workspaceId: string) => {
    setCurrentWorkspace(workspaceId);
    onWorkspaceChange?.(workspaceId);
    
    // Call switch endpoint
    try {
      await fetch(`/api/v1/workspaces/${workspaceId}/switch`, {
        method: 'POST',
      });
    } catch (err) {
      console.error('Failed to switch workspace:', err);
    }
  };

  const handleCreateWorkspace = async () => {
    if (!newWorkspaceName.trim()) return;
    
    try {
      const res = await fetch('/api/v1/workspaces', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newWorkspaceName.trim(),
          default_engine: 'auto'
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        await loadWorkspaces();
        setCurrentWorkspace(data.workspace.id);
        onWorkspaceChange?.(data.workspace.id);
        setShowCreateWorkspace(false);
        setNewWorkspaceName('');
      } else {
        const error = await res.json().catch(() => ({ detail: 'Failed to create workspace' }));
        alert(error.detail || 'Failed to create workspace');
      }
    } catch (err) {
      console.error('Failed to create workspace:', err);
      alert('Failed to create workspace');
    }
  };

  const activeWorkspace = useMemo(
    () => workspaces.find((ws) => ws.id === currentWorkspace)?.name ?? 'Select Workspace',
    [currentWorkspace, workspaces]
  );

  const links: { key: View; label: string }[] = [
    { key: 'ask', label: 'Ask' },
    { key: 'sources', label: 'Sources' },
    { key: 'ingest', label: 'Ingest' },
    { key: 'assets', label: 'Assets' },
    { key: 'history', label: 'History' },
    { key: 'admin', label: 'Admin' }
  ];

  return (
    <header className="app-header">
      <div className="brand-group">
        <div className="brand-glyph">SB</div>
        <div className="brand-title">
          <span>Second Brain</span>
          <strong>{activeWorkspace}</strong>
        </div>
      </div>

      <div className="header-actions">
        <div className="workspace-selector" style={{ position: 'relative' }}>
          <label htmlFor="workspace-select" className="small">Workspace</label>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <select
              id="workspace-select"
              value={currentWorkspace}
              onChange={(e) => handleWorkspaceChange(e.target.value)}
              aria-label="Select workspace"
            >
              {workspaces.map(ws => (
                <option key={ws.id} value={ws.id}>{ws.name}</option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => setShowCreateWorkspace(true)}
              className="button-outline small"
              title="Create new workspace"
            >
              +
            </button>
          </div>
        </div>

        <nav className="primary-nav" aria-label="Primary navigation">
          {links.map((link) => (
            <button
              key={link.key}
              className={link.key === active ? 'active' : ''}
              onClick={() => onNavigate(link.key)}
              type="button"
              data-nav={link.key}
            >
              {link.label}
            </button>
          ))}
        </nav>

        <div className="user-chip" aria-label="Active user">
          <span className="status-dot" aria-hidden="true" />
          <span>{userName}</span>
        </div>
      </div>

      {showCreateWorkspace && (
        <div 
          style={{ 
            position: 'fixed', 
            top: 0, 
            left: 0, 
            right: 0, 
            bottom: 0, 
            background: 'rgba(0,0,0,0.5)', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            zIndex: 10000 
          }}
          onClick={() => setShowCreateWorkspace(false)}
        >
          <div 
            style={{ 
              padding: '2rem', 
              background: 'var(--bg-panel-solid)', 
              border: '1px solid var(--border-strong)', 
              borderRadius: '8px', 
              maxWidth: '400px', 
              width: '90%',
              zIndex: 10001
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginTop: 0 }}>Create New Workspace</h3>
            <label style={{ display: 'block', marginTop: '1rem' }}>
              Workspace Name:
              <input
                type="text"
                value={newWorkspaceName}
                onChange={(e) => setNewWorkspaceName(e.target.value)}
                placeholder="Enter workspace name"
                style={{ width: '100%', padding: '0.5rem', marginTop: '0.25rem' }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleCreateWorkspace();
                  if (e.key === 'Escape') setShowCreateWorkspace(false);
                }}
                autoFocus
              />
            </label>
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
              <button type="button" onClick={handleCreateWorkspace} className="button-primary">Create</button>
              <button type="button" onClick={() => setShowCreateWorkspace(false)} className="button-outline">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
};

export default Header;

