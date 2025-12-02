import { useEffect, useState } from 'react';
import type { Source } from '../types';
import { SkeletonSourceItem } from './Skeleton';
import { EmptySourcesState, EmptySearchState } from './EmptyState';
import { ErrorMessage } from './ErrorMessage';

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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2>Sources</h2>
        <span className="pill-badge">{sources.length} Total</span>
      </div>
      
      <input
        type="text"
        placeholder="🔍 Filter sources by name, type, or path..."
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
      />
      
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
          {[1, 2, 3].map((i) => <SkeletonSourceItem key={i} />)}
        </div>
      ) : error ? (
        <ErrorMessage
          title="Failed to Load Sources"
          message={error}
          onRetry={() => window.location.reload()}
          type="error"
        />
      ) : sources.length === 0 ? (
        <EmptySourcesState onIngest={() => {
          const ingestTab = document.querySelector('[data-nav="ingest"]') as HTMLElement;
          ingestTab?.click();
        }} />
      ) : filtered.length === 0 ? (
        <EmptySearchState query={filter} />
      ) : (
        <div className="card-list" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '1rem' }}>
            {filtered.map((src) => (
              <div 
                key={src.id} 
                className="source-card"
                style={{
                  padding: '1.25rem',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '16px',
                  background: 'rgba(255, 255, 255, 0.02)',
                  transition: 'all 150ms ease',
                  cursor: 'pointer'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(255, 107, 53, 0.3)';
                  e.currentTarget.style.background = 'rgba(255, 107, 53, 0.05)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)';
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)';
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.75rem' }}>
                  <div>
                    <strong style={{ fontSize: '1.05rem' }}>{src.display_name || 'Untitled source'}</strong>
                    <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem', flexWrap: 'wrap' }}>
                      <span className="pill-badge" style={{ fontSize: '0.75rem' }}>{src.type}</span>
                      <span className="pill-badge" style={{ fontSize: '0.75rem' }}>{src.chunk_count} chunks</span>
                      {src.language && <span className="pill-badge" style={{ fontSize: '0.75rem' }}>{src.language}</span>}
                    </div>
                  </div>
                </div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  {src.path && <div>📄 {src.path}</div>}
                  {src.url && (
                    <div>
                      🔗{' '}
                      <a href={src.url} target="_blank" rel="noreferrer" style={{ color: 'var(--accent)' }}>
                        {src.url.length > 60 ? src.url.substring(0, 57) + '...' : src.url}
                      </a>
                    </div>
                  )}
                  {src.first_seen && (
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                      Added: {new Date(src.first_seen).toLocaleDateString()}
                    </div>
                  )}
                </div>
              </div>
            ))}
        </div>
      )}
    </section>
  );
};

