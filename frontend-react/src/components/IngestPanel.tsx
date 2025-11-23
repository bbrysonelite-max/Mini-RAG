import { useState } from 'react';

export const IngestPanel = () => {
  const [urls, setUrls] = useState('');
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const ingest = async () => {
    if (!urls.trim()) {
      setStatus('Add at least one URL.');
      return;
    }
    setStatus(null);
    setLoading(true);
    const body = new FormData();
    body.append('urls', urls);
    try {
      const resp = await fetch('/api/v1/ingest/urls', {
        method: 'POST',
        body
      });
      if (!resp.ok) throw new Error(`Failed (${resp.status})`);
      const data = await resp.json();
      setStatus(`Queued ${data.results?.length ?? 0} URL(s).`);
    } catch (err) {
      setStatus((err as Error).message);
    } finally {
      setLoading=false;
    }
  };

  return (
    <section>
      <h2>Ingest</h2>
      <textarea
        value={urls}
        onChange={(e)=>setUrls(e.target.value)}
        placeholder="Paste YouTube or transcript URLs, one per line"
      />
      <button onClick={ingest} disabled={loading}>
        {loading ? 'Submitting…' : 'Ingest URLs'}
      </button>
      {status && <p className="small">{status}</p>}
      <div className="empty-state">File uploads coming soon to the React shell.</div>
    </section>
  );
};

