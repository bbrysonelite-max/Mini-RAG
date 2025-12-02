import { useEffect, useState } from 'react';
import type { Source } from '../types';

interface SourcesPanelProps {
  workspaceId?: string;
}

export const SourcesPanel = ({ workspaceId }: SourcesPanelProps) => {
  const [sources, setSources] = useState<Source[]>([]);
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const resp = await fetch('/api/v1/sources');
        if (!resp.ok) throw new Error('Failed to load sources');
        const data = await resp.json();
        setSources(data.sources ?? []);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const filtered = sources.filter((s) => {
    if (!filter) return true;
    const needle = filter.toLowerCase();
    return (
      s.display_name?.toLowerCase().includes(needle) ||
      s.type?.toLowerCase().includes(needle) ||
      s.path?.toLowerCase().includes(needle) ||
      s.url?.toLowerCase().includes(needle)
    );
  });

  return (
    <section>
      <h2>Sources</h2>
      <input
        type="text"
        placeholder="Filter sources…"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
      />
      {loading && <p className="small">Loading sources…</p>}
      {error && <p className="small error">{error}</p>}
      {!loading && filtered.length === 0 ? (
        <div className="empty-state">No sources found.</div>
      ) : (
        <div className="card-list">
            {filtered.map((src) => (
              <div key={src.id} className="source-card">
                <div className="source-card__header">
                  <div>
                    <strong>{src.display_name || 'Untitled source'}</strong>
                    <div className="badge-row">
                      <span className="badge">{src.type}</span>
                      <span className="badge">{src.chunk_count} chunks</span>
                      {src.language && <span className="badge">{src.language}</span>}
                    </div>
                  </div>
                </div>
                <div className="source-card__meta">
                  {src.path && <div>Path: {src.path}</div>}
                  {src.url && (
                    <div>
                      URL:{' '}
                      <a href={src.url} target="_blank" rel="noreferrer">
                        {src.url}
                      </a>
                    </div>
                  )}
                  {src.first_seen && (
                    <div>Added: {new Date(src.first_seen).toLocaleString()}</div>
                  )}
                </div>
              </div>
            ))}
        </div>
      )}
    </section>
  );
};

