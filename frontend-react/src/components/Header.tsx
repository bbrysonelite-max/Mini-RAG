import { useState, useEffect, type FC } from 'react';

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

  const links: { key: View; label: string }[] = [
    { key: 'ask', label: 'Ask' },
    { key: 'sources', label: 'Sources' },
    { key: 'ingest', label: 'Ingest' },
    { key: 'admin', label: 'Admin' }
  ];

  return (
    <header className="app-header">
      <div className="brand">Mini-RAG</div>
      <div className="workspace-selector">
        <label htmlFor="workspace-select" className="small">Workspace:</label>
        <select
          id="workspace-select"
          value={currentWorkspace}
          onChange={(e) => setCurrentWorkspace(e.target.value)}
        >
          {workspaces.map(ws => (
            <option key={ws.id} value={ws.id}>{ws.name}</option>
          ))}
        </select>
      </div>
      <nav className="primary-nav" aria-label="Primary">
        {links.map((link) => (
          <button
            key={link.key}
            className={link.key === active ? 'active' : ''}
            onClick={() => onNavigate(link.key)}
          >
            {link.label}
          </button>
        ))}
      </nav>
    </header>
  );
};

export default Header;

