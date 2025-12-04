import { useState, useEffect, useRef } from 'react';
import { AdminPanel } from './components/AdminPanel';
import { AskPanel } from './components/AskPanel';
import { IngestPanel } from './components/IngestPanel';
import { SourcesPanel } from './components/SourcesPanel';
import { AssetsPanel } from './components/AssetsPanel';
import { HistoryPanel } from './components/HistoryPanel';
import { SettingsPanel } from './components/SettingsPanel';
import { LoginForm } from './components/LoginForm';
import { ToastContainer } from './components/ToastContainer';
import { KeyboardShortcutsModal } from './components/KeyboardShortcuts';
import Header from './components/Header';
import Footer from './components/Footer';
import HelpWidget from './components/HelpWidget';
import { useToast } from './hooks/useToast';
import { useKeyboardShortcuts, APP_SHORTCUTS, KeyboardShortcut } from './hooks/useKeyboardShortcuts';

type View = 'ask' | 'sources' | 'ingest' | 'admin' | 'assets' | 'history' | 'settings';

function App() {
  const [view, setView] = useState<View>('ask');
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [currentWorkspace, setCurrentWorkspace] = useState<string>('');
  const [showShortcuts, setShowShortcuts] = useState(false);
  const { toasts, removeToast } = useToast();
  const askInputRef = useRef<HTMLTextAreaElement | null>(null);

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

  // Define keyboard shortcuts
  const shortcuts: KeyboardShortcut[] = [
    { ...APP_SHORTCUTS.FOCUS_SEARCH, action: () => {
      const askInput = document.querySelector('textarea') as HTMLTextAreaElement;
      askInput?.focus();
      setView('ask');
    }},
    { ...APP_SHORTCUTS.GO_TO_INGEST, action: () => setView('ingest') },
    { ...APP_SHORTCUTS.GO_TO_SOURCES, action: () => setView('sources') },
    { ...APP_SHORTCUTS.GO_TO_ASSETS, action: () => setView('assets') },
    { ...APP_SHORTCUTS.GO_TO_ADMIN, action: () => setView('admin') },
    { ...APP_SHORTCUTS.ESCAPE, action: () => setShowShortcuts(false) },
    { ...APP_SHORTCUTS.HELP, action: () => setShowShortcuts(true) },
  ];

  // Enable keyboard shortcuts
  useKeyboardShortcuts(shortcuts, authenticated !== false);

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
      case 'settings':
        return <SettingsPanel />;
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
      <a href="#main-content" className="skip-to-main">
        Skip to main content
      </a>
      <Header 
        active={view} 
        onNavigate={setView}
        currentWorkspace={currentWorkspace}
        onWorkspaceChange={setCurrentWorkspace}
      />
      <main id="main-content" role="main" aria-label="Main content">
        {renderView()}
      </main>
      <Footer />
      <HelpWidget position="bottom-right" />
      <ToastContainer toasts={toasts} onClose={removeToast} position="top-right" />
      <KeyboardShortcutsModal 
        isOpen={showShortcuts} 
        onClose={() => setShowShortcuts(false)}
        shortcuts={shortcuts}
      />
    </div>
  );
}

export default App;

