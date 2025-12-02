import { useState, useRef } from 'react';
import { LoadingSpinner } from './LoadingSpinner';
import { ErrorMessage } from './ErrorMessage';

interface IngestPanelProps {
  workspaceId?: string;
}

export const IngestPanel = ({ workspaceId }: IngestPanelProps) => {
  const [urls, setUrls] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [pastedText, setPastedText] = useState('');
  const [pastedTextTitle, setPastedTextTitle] = useState('');
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const ingestUrls = async () => {
    if (!urls.trim()) {
      setError('Add at least one URL.');
      return;
    }
    setStatus(null);
    setError(null);
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
      setError((err as Error).message);
    } finally {
      setLoading(false);
      setTimeout(() => setProgress(0), 2000);
    }
  };

  const ingestFiles = async () => {
    if (files.length === 0) {
      setError('Select files first.');
      return;
    }
    setStatus(null);
    setError(null);
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
      setError((err as Error).message);
    } finally {
      setLoading(false);
      setTimeout(() => setProgress(0), 2000);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const dropped = Array.from(e.dataTransfer.files);
    setFiles(dropped);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };

  const removeFile = (index: number) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    const iconMap: Record<string, string> = {
      'pdf': '📄',
      'docx': '📝',
      'doc': '📝',
      'txt': '📃',
      'md': '📋',
      'markdown': '📋',
      'vtt': '🎬',
      'srt': '🎬',
      'png': '🖼️',
      'jpg': '🖼️',
      'jpeg': '🖼️',
      'gif': '🖼️'
    };
    return iconMap[ext || ''] || '📎';
  };

  const ingestPastedText = async () => {
    if (!pastedText.trim() || !pastedTextTitle.trim()) {
      setError('Title and content are required.');
      return;
    }
    if (!workspaceId) {
      setError('Please select a workspace first.');
      return;
    }
    
    setStatus(null);
    setError(null);
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
      setError((err as Error).message);
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
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          style={{
            border: isDragging ? '2px dashed var(--accent)' : '2px dashed rgba(255, 255, 255, 0.2)',
            borderRadius: '16px',
            padding: '2.5rem',
            textAlign: 'center',
            cursor: 'pointer',
            marginBottom: '1rem',
            background: isDragging 
              ? 'rgba(255, 107, 53, 0.1)' 
              : 'rgba(255, 255, 255, 0.02)',
            transform: isDragging ? 'scale(1.02)' : 'scale(1)',
            transition: 'all 200ms ease',
            boxShadow: isDragging 
              ? '0 0 20px rgba(255, 107, 53, 0.3)' 
              : 'none'
          }}
        >
          <div style={{ fontSize: '3rem', marginBottom: '0.5rem', opacity: 0.7 }}>
            {isDragging ? '🎯' : '📤'}
          </div>
          <p style={{ margin: '0 0 0.5rem 0', fontSize: '1rem', fontWeight: 500 }}>
            {isDragging ? 'Drop files here' : 'Click or drag files here'}
          </p>
          <p className="small" style={{ color: 'var(--text-muted)', margin: 0 }}>
            PDF, Word, Markdown, Text, Images, VTT, SRT supported
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
            <p className="small" style={{ marginBottom: '0.75rem', fontWeight: 600 }}>
              Selected {files.length} file(s):
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {files.map((f, i) => (
                <div 
                  key={i} 
                  style={{ 
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                    padding: '0.75rem',
                    background: 'rgba(255, 255, 255, 0.04)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '12px'
                  }}
                >
                  <span style={{ fontSize: '1.5rem' }}>{getFileIcon(f.name)}</span>
                  <div style={{ flex: 1, overflow: 'hidden' }}>
                    <div style={{ 
                      fontSize: '0.9rem', 
                      color: 'var(--text-primary)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}>
                      {f.name}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {(f.size / 1024).toFixed(1)} KB
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(i);
                    }}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      padding: '0.25rem',
                      fontSize: '1.2rem',
                      lineHeight: 1,
                      transition: 'color 150ms ease'
                    }}
                    title="Remove file"
                    onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent-red)'}
                    onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
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

      {loading && (
        <LoadingSpinner 
          size="medium" 
          message="Processing your request..." 
          progress={progress}
        />
      )}
      
      {error && (
        <ErrorMessage
          title="Ingestion Error"
          message={error}
          onRetry={() => {
            setError(null);
            setStatus(null);
          }}
          type="error"
        />
      )}
      
      {status && !error && !loading && (
        <div style={{ 
          marginTop: '1rem', 
          padding: '1rem', 
          background: 'rgba(16, 185, 129, 0.1)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          borderRadius: '8px',
          color: '#10b981'
        }}>
          {status}
        </div>
      )}
    </section>
  );
};

