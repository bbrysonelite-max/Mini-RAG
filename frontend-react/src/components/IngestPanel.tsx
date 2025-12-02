import { useState, useRef } from 'react';

interface IngestPanelProps {
  workspaceId?: string;
}

export const IngestPanel = ({ workspaceId }: IngestPanelProps) => {
  const [urls, setUrls] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [pastedText, setPastedText] = useState('');
  const [pastedTextTitle, setPastedTextTitle] = useState('');
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const ingestUrls = async () => {
    if (!urls.trim()) {
      setStatus('Add at least one URL.');
      return;
    }
    setStatus(null);
    setLoading(true);
    setProgress(0);
    const body = new FormData();
    body.append('urls', urls);
    try {
      const resp = await fetch('/api/v1/ingest/urls', {
        method: 'POST',
        body
      });
      if (!resp.ok) throw new Error(`Failed (${resp.status})`);
      const data = await resp.json();
      setProgress(100);
      setStatus(`✅ Ingested ${data.total_written ?? 0} chunks from ${data.results?.length ?? 0} URL(s).`);
      setUrls('');
    } catch (err) {
      setStatus(`❌ ${(err as Error).message}`);
    } finally {
      setLoading(false);
      setTimeout(() => setProgress(0), 2000);
    }
  };

  const ingestFiles = async () => {
    if (files.length === 0) {
      setStatus('Select files first.');
      return;
    }
    setStatus(null);
    setLoading(true);
    setProgress(30);
    const body = new FormData();
    files.forEach(f => body.append('files', f));
    try {
      const resp = await fetch('/api/v1/ingest/files', {
        method: 'POST',
        body
      });
      if (!resp.ok) throw new Error(`Failed (${resp.status})`);
      const data = await resp.json();
      setProgress(100);
      setStatus(`✅ Uploaded ${files.length} file(s), ingested ${data.total_written ?? 0} chunks.`);
      setFiles([]);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (err) {
      setStatus(`❌ ${(err as Error).message}`);
    } finally {
      setLoading(false);
      setTimeout(() => setProgress(0), 2000);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const dropped = Array.from(e.dataTransfer.files);
    setFiles(dropped);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };

  const ingestPastedText = async () => {
    if (!pastedText.trim() || !pastedTextTitle.trim()) {
      setStatus('Title and content are required.');
      return;
    }
    if (!workspaceId) {
      setStatus('Please select a workspace first.');
      return;
    }
    
    setStatus(null);
    setLoading(true);
    setProgress(0);
    
    try {
      const res = await fetch(`/api/v1/workspaces/${workspaceId}/documents/paste`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: pastedTextTitle.trim(),
          content: pastedText.trim()
        })
      });
      
      if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: `Failed (${res.status})` }));
        throw new Error(error.detail || `Failed (${res.status})`);
      }
      
      const data = await res.json();
      setProgress(100);
      setStatus(`✅ Ingested pasted text as document "${pastedTextTitle}".`);
      setPastedText('');
      setPastedTextTitle('');
    } catch (err) {
      setStatus(`❌ ${(err as Error).message}`);
    } finally {
      setLoading(false);
      setTimeout(() => setProgress(0), 2000);
    }
  };

  return (
    <section>
      <h2>Add Documents</h2>
      
      {!workspaceId && (
        <p className="error">Please select a workspace to add documents.</p>
      )}
      
      <div style={{ marginBottom: '2rem' }}>
        <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>📄 Upload File</h3>
        <p className="small" style={{ marginBottom: '0.5rem', color: '#666' }}>
          Upload PDF, DOCX, or TXT files to ingest into this workspace.
        </p>
        <div
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          style={{
            border: '2px dashed #555',
            borderRadius: '8px',
            padding: '2rem',
            textAlign: 'center',
            cursor: 'pointer',
            marginBottom: '1rem',
            background: '#1a1a1a'
          }}
        >
          <p>Click or drag files here</p>
          <p className="small" style={{ color: '#888' }}>
            PDF, Word, Markdown, Text, VTT, SRT supported
          </p>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />
        {files.length > 0 && (
          <div style={{ marginBottom: '1rem' }}>
            <p className="small">Selected {files.length} file(s):</p>
            {files.map((f, i) => (
              <div key={i} className="small" style={{ padding: '0.25rem', color: '#aaa' }}>
                {f.name} ({(f.size / 1024).toFixed(1)} KB)
              </div>
            ))}
          </div>
        )}
        <button onClick={ingestFiles} disabled={loading || files.length === 0}>
          {loading ? 'Uploading…' : '📤 Upload & Ingest'}
        </button>
      </div>

      <div style={{ marginBottom: '2rem' }}>
        <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>📝 Paste Text</h3>
        <p className="small" style={{ marginBottom: '0.5rem', color: '#666' }}>
          Paste text content directly to ingest into this workspace.
        </p>
        <label style={{ display: 'block', marginBottom: '0.5rem' }}>
          Document Title:
          <input
            type="text"
            value={pastedTextTitle}
            onChange={(e) => setPastedTextTitle(e.target.value)}
            placeholder="Enter a title for this document"
            style={{ width: '100%', padding: '0.5rem', marginTop: '0.25rem' }}
            disabled={!workspaceId || loading}
          />
        </label>
        <label style={{ display: 'block', marginBottom: '0.5rem' }}>
          Content:
          <textarea
            value={pastedText}
            onChange={(e) => setPastedText(e.target.value)}
            placeholder="Paste your text content here..."
            style={{ width: '100%', padding: '0.5rem', marginTop: '0.25rem', minHeight: '200px' }}
            disabled={!workspaceId || loading}
          />
        </label>
        <button
          type="button"
          onClick={ingestPastedText}
          disabled={!workspaceId || loading || !pastedText.trim() || !pastedTextTitle.trim()}
          className="button-primary"
        >
          {loading ? 'Ingesting...' : 'Ingest Pasted Text'}
        </button>
      </div>
      
      <div>
        <h3 style={{ fontSize: '1rem', marginBottom: '0.5rem' }}>🔗 Ingest URLs</h3>
        <textarea
          value={urls}
          onChange={(e) => setUrls(e.target.value)}
          placeholder="Paste YouTube or transcript URLs, one per line"
          style={{ marginBottom: '1rem' }}
        />
        <button onClick={ingestUrls} disabled={loading}>
          {loading ? 'Submitting…' : 'Ingest URLs'}
        </button>
      </div>

      {progress > 0 && (
        <div style={{ marginTop: '1rem', background: '#333', borderRadius: '4px', overflow: 'hidden' }}>
          <div
            style={{
              width: `${progress}%`,
              height: '4px',
              background: '#ff6b35',
              transition: 'width 0.3s'
            }}
          />
        </div>
      )}
      
      {status && <p className="small" style={{ marginTop: '1rem' }}>{status}</p>}
    </section>
  );
};

