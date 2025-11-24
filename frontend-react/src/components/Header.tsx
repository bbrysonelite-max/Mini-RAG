import { useState, useEffect, type FC, useMemo } from 'react';

type View = 'ask' | 'sources' | 'ingest' | 'admin';

interface Workspace {
  id: string;
  name: string;
}

interface HeaderProps {
  active: View;
  onNavigate: (view: View) => void;
}

const Header: FC<HeaderProps> = ({ active, onNavigate }) => {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [currentWorkspace, setCurrentWorkspace] = useState<string>('default');
  const [userName] = useState('Operator');

  useEffect(() => {
    // Load workspaces from API
    fetch('/api/v1/admin/workspaces')
      .then(res => res.ok ? res.json() : Promise.reject())
      .then(data => {
        const ws = data.workspaces || [];
        setWorkspaces(ws);
        // Set first workspace as default
        if (ws.length > 0) {
          setCurrentWorkspace(ws[0].id);
        }
      })
      .catch(() => {
        // Fallback if admin endpoint fails (non-admin user)
        setWorkspaces([{ id: 'default', name: 'Default Workspace' }]);
      });
  }, []);

  const activeWorkspace = useMemo(
    () => workspaces.find((ws) => ws.id === currentWorkspace)?.name ?? 'Default Workspace',
    [currentWorkspace, workspaces]
  );

  const links: { key: View; label: string }[] = [
    { key: 'ask', label: 'Ask' },
    { key: 'sources', label: 'Sources' },
    { key: 'ingest', label: 'Ingest' },
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
        <div className="workspace-selector">
          <label htmlFor="workspace-select" className="small">Workspace</label>
          <select
            id="workspace-select"
            value={currentWorkspace}
            onChange={(e) => setCurrentWorkspace(e.target.value)}
            aria-label="Select workspace"
          >
            {workspaces.map(ws => (
              <option key={ws.id} value={ws.id}>{ws.name}</option>
            ))}
          </select>
        </div>

        <nav className="primary-nav" aria-label="Primary navigation">
          {links.map((link) => (
            <button
              key={link.key}
              className={link.key === active ? 'active' : ''}
              onClick={() => onNavigate(link.key)}
              type="button"
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
    </header>
  );
};

export default Header;

