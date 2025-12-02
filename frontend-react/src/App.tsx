import { useState, useEffect } from 'react';
import { AdminPanel } from './components/AdminPanel';
import { AskPanel } from './components/AskPanel';
import { IngestPanel } from './components/IngestPanel';
import { SourcesPanel } from './components/SourcesPanel';
import { AssetsPanel } from './components/AssetsPanel';
import { HistoryPanel } from './components/HistoryPanel';
import { LoginForm } from './components/LoginForm';
import Header from './components/Header';
import Footer from './components/Footer';
import HelpWidget from './components/HelpWidget';

type View = 'ask' | 'sources' | 'ingest' | 'admin' | 'assets' | 'history';

function App() {
  const [view, setView] = useState<View>('ask');
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [currentWorkspace, setCurrentWorkspace] = useState<string>('');

  useEffect(() => {
    // Check auth status
    fetch('/auth/me')
      .then(res => res.json())
      .then(data => {
        setAuthenticated(data.authenticated === true);
      })
      .catch(() => {
        setAuthenticated(false);
      });
  }, []);

  const renderView = () => {
    switch (view) {
      case 'sources':
        return <SourcesPanel workspaceId={currentWorkspace} />;
      case 'ingest':
        return <IngestPanel workspaceId={currentWorkspace} />;
      case 'admin':
        return <AdminPanel />;
      case 'assets':
        return <AssetsPanel workspaceId={currentWorkspace} />;
      case 'history':
        return <HistoryPanel workspaceId={currentWorkspace} />;
      case 'ask':
      default:
        return <AskPanel workspaceId={currentWorkspace} />;
    }
  };

  // Show login form if not authenticated (and not in LOCAL_MODE)
  if (authenticated === false) {
    return (
      <div className="app-shell">
        <main style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
          <LoginForm onSuccess={() => setAuthenticated(true)} />
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="app-shell">
      <Header 
        active={view} 
        onNavigate={setView}
        currentWorkspace={currentWorkspace}
        onWorkspaceChange={setCurrentWorkspace}
      />
      <main>{renderView()}</main>
      <Footer />
      <HelpWidget position="bottom-right" />
    </div>
  );
}

export default App;

