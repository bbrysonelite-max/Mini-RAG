import { useState } from 'react';
import { AdminPanel } from './components/AdminPanel';
import { AskPanel } from './components/AskPanel';
import { IngestPanel } from './components/IngestPanel';
import { SourcesPanel } from './components/SourcesPanel';
import Header from './components/Header';

type View = 'ask' | 'sources' | 'ingest' | 'admin';

function App() {
  const [view, setView] = useState<View>('ask');

  const renderView = () => {
    switch (view) {
      case 'sources':
        return <SourcesPanel />;
      case 'ingest':
        return <IngestPanel />;
      case 'admin':
        return <AdminPanel />;
      case 'ask':
      default:
        return <AskPanel />;
    }
  };

  return (
    <div className="app-shell">
      <Header active={view} onNavigate={setView} />
      <main>{renderView()}</main>
    </div>
  );
}

export default App;

