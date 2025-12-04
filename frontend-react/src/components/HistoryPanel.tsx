import { useState, useEffect } from 'react';

interface HistoryEntry {
  id: string;
  workspace_id: string;
  command: string;
  input_snippet: string;
  output_snippet: string;
  full_input?: string;
  full_output?: string;
  created_at: string;
}

interface HistoryPanelProps {
  workspaceId?: string;
}

export const HistoryPanel = ({ workspaceId }: HistoryPanelProps) => {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedEntry, setSelectedEntry] = useState<HistoryEntry | null>(null);
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [saveTitle, setSaveTitle] = useState('');

  useEffect(() => {
    if (workspaceId) {
      loadHistory();
    }
  }, [workspaceId]);

  const loadHistory = async () => {
    if (!workspaceId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const res = await fetch(`/api/v1/workspaces/${workspaceId}/history?limit=100`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data.history || []);
      } else {
        setError('Failed to load history');
      }
    } catch (err) {
      setError('Failed to load history');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadFullEntry = async (entryId: string) => {
    try {
      const res = await fetch(`/api/v1/history/${entryId}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedEntry(data.history);
      }
    } catch (err) {
      console.error('Failed to load full entry:', err);
    }
  };

  const handleSaveAsAsset = async () => {
    if (!selectedEntry || !workspaceId || !saveTitle.trim()) return;
    
    try {
      const res = await fetch(`/api/v1/history/${selectedEntry.id}/save-asset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: saveTitle.trim(),
          tags: [selectedEntry.command, 'from_history']
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        setShowSaveModal(false);
        setSaveTitle('');
        alert('Asset saved successfully!');
      } else {
        const error = await res.json().catch(() => ({ detail: 'Failed to save asset' }));
        alert(error.detail || 'Failed to save asset');
      }
    } catch (err) {
      console.error('Failed to save asset:', err);
      alert('Failed to save asset');
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const formatCommandName = (command: string) => {
    return command.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  if (!workspaceId) {
    return <section><p>Please select a workspace to view history.</p></section>;
  }

  return (
    <section>
      <h2>History</h2>

      {error && <p className="error">{error}</p>}
      
      {loading ? (
        <p>Loading history...</p>
      ) : history.length === 0 ? (
        <div className="empty-state">
          <p>No history yet. Start using Ask commands to see your history here.</p>
        </div>
      ) : (
        <div className="history-list">
          {history.map(entry => (
            <div key={entry.id} className="history-item" style={{ border: '1px solid #ccc', padding: '1rem', borderRadius: '4px', marginBottom: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
                <div>
                  <strong>{formatCommandName(entry.command)}</strong>
                  <span className="small" style={{ marginLeft: '1rem', color: '#666' }}>
                    {formatDate(entry.created_at)}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => loadFullEntry(entry.id)}
                  className="button-outline small"
                >
                  Open
                </button>
              </div>
              <div style={{ marginBottom: '0.5rem' }}>
                <strong className="small">Input:</strong>
                <p className="small" style={{ marginTop: '0.25rem', color: '#666' }}>
                  {entry.input_snippet || entry.full_input || 'N/A'}
                </p>
              </div>
              <div>
                <strong className="small">Output:</strong>
                <p className="small" style={{ marginTop: '0.25rem', color: '#666' }}>
                  {entry.output_snippet || entry.full_output || 'N/A'}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedEntry && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: 'white', padding: '2rem', borderRadius: '8px', maxWidth: '800px', width: '90%', maxHeight: '90vh', overflow: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '1rem' }}>
              <div>
                <h3 style={{ margin: 0 }}>{formatCommandName(selectedEntry.command)}</h3>
                <span className="small" style={{ color: '#666' }}>
                  {formatDate(selectedEntry.created_at)}
                </span>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  type="button"
                  onClick={() => {
                    setSaveTitle(`${formatCommandName(selectedEntry.command)} - ${new Date(selectedEntry.created_at).toLocaleDateString()}`);
                    setShowSaveModal(true);
                  }}
                  className="button-primary small"
                >
                  Save as Asset
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedEntry(null);
                    setShowSaveModal(false);
                  }}
                  className="button-outline small"
                >
                  Close
                </button>
              </div>
            </div>
            
            <div style={{ marginBottom: '1rem' }}>
              <h4>Input:</h4>
              <pre style={{ whiteSpace: 'pre-wrap', background: '#f5f5f5', padding: '1rem', borderRadius: '4px', overflow: 'auto' }}>
                {selectedEntry.full_input || selectedEntry.input_snippet || 'N/A'}
              </pre>
            </div>
            
            <div>
              <h4>Output:</h4>
              <pre style={{ whiteSpace: 'pre-wrap', background: '#f5f5f5', padding: '1rem', borderRadius: '4px', overflow: 'auto' }}>
                {selectedEntry.full_output || selectedEntry.output_snippet || 'N/A'}
              </pre>
            </div>
          </div>
        </div>
      )}

      {showSaveModal && selectedEntry && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1001 }}>
          <div style={{ background: 'white', padding: '2rem', borderRadius: '8px', maxWidth: '500px', width: '90%' }}>
            <h3>Save as Asset</h3>
            <label style={{ display: 'block', marginTop: '1rem' }}>
              Title:
              <input
                type="text"
                value={saveTitle}
                onChange={(e) => setSaveTitle(e.target.value)}
                style={{ width: '100%', padding: '0.5rem', marginTop: '0.25rem' }}
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSaveAsAsset();
                  if (e.key === 'Escape') setShowSaveModal(false);
                }}
              />
            </label>
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
              <button type="button" onClick={handleSaveAsAsset} className="button-primary">Save</button>
              <button type="button" onClick={() => setShowSaveModal(false)} className="button-outline">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};



