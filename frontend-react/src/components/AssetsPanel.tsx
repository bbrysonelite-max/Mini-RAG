import { useState, useEffect } from 'react';

interface Asset {
  id: string;
  workspace_id: string;
  type: string;
  title: string;
  content: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

interface AssetsPanelProps {
  workspaceId?: string;
}

const ASSET_TYPES = [
  'prompt',
  'workflow',
  'page',
  'sequence',
  'decision',
  'expert_instructions',
  'customer_avatar',
  'document',
];

export const AssetsPanel = ({ workspaceId }: AssetsPanelProps) => {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>('');
  const [searchText, setSearchText] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showAssetModal, setShowAssetModal] = useState<Asset | null>(null);
  const [newAsset, setNewAsset] = useState({ type: 'document', title: '', content: '', tags: '' });

  useEffect(() => {
    if (workspaceId) {
      loadAssets();
    }
  }, [workspaceId, filterType, searchText]);

  const loadAssets = async () => {
    if (!workspaceId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams();
      if (filterType) params.append('type', filterType);
      if (searchText) params.append('search', searchText);
      
      const res = await fetch(`/api/v1/workspaces/${workspaceId}/assets?${params}`);
      if (res.ok) {
        const data = await res.json();
        setAssets(data.assets || []);
      } else {
        setError('Failed to load assets');
      }
    } catch (err) {
      setError('Failed to load assets');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAsset = async () => {
    if (!workspaceId || !newAsset.title.trim() || !newAsset.content.trim()) return;
    
    try {
      const res = await fetch(`/api/v1/workspaces/${workspaceId}/assets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: newAsset.type,
          title: newAsset.title.trim(),
          content: newAsset.content.trim(),
          tags: newAsset.tags.split(',').map(t => t.trim()).filter(Boolean)
        })
      });
      
      if (res.ok) {
        await loadAssets();
        setShowAddModal(false);
        setNewAsset({ type: 'document', title: '', content: '', tags: '' });
      } else {
        const error = await res.json().catch(() => ({ detail: 'Failed to create asset' }));
        alert(error.detail || 'Failed to create asset');
      }
    } catch (err) {
      console.error('Failed to create asset:', err);
      alert('Failed to create asset');
    }
  };

  const handleDeleteAsset = async (assetId: string) => {
    if (!confirm('Are you sure you want to delete this asset?')) return;
    
    try {
      const res = await fetch(`/api/v1/assets/${assetId}`, {
        method: 'DELETE'
      });
      
      if (res.ok) {
        await loadAssets();
      } else {
        alert('Failed to delete asset');
      }
    } catch (err) {
      console.error('Failed to delete asset:', err);
      alert('Failed to delete asset');
    }
  };

  const handleCopyAsset = async (asset: Asset) => {
    try {
      await navigator.clipboard.writeText(asset.content);
      alert('Copied to clipboard!');
    } catch (err) {
      console.error('Failed to copy:', err);
      alert('Failed to copy');
    }
  };

  const handleExportAsset = async (asset: Asset, format: string) => {
    try {
      const res = await fetch(`/api/v1/assets/${asset.id}/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ format })
      });
      
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${asset.title}.${format}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      } else {
        alert('Export not yet available for PDF. Use TXT or MD format.');
      }
    } catch (err) {
      console.error('Failed to export:', err);
      alert('Failed to export');
    }
  };

  const handleInsertIntoAsk = (asset: Asset) => {
    // This would need to communicate with AskPanel - for now, copy to clipboard with a note
    navigator.clipboard.writeText(asset.content);
    alert('Asset content copied to clipboard. Paste it into the Ask input.');
  };

  if (!workspaceId) {
    return <section><p>Please select a workspace to view assets.</p></section>;
  }

  return (
    <section>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2>My Assets</h2>
        <button
          type="button"
          onClick={() => setShowAddModal(true)}
          className="button-primary"
        >
          Add Asset
        </button>
      </div>

      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        <div>
          <label htmlFor="filter-type" className="small">Filter by Type:</label>
          <select
            id="filter-type"
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            style={{ padding: '0.5rem', marginLeft: '0.5rem' }}
          >
            <option value="">All Types</option>
            {ASSET_TYPES.map(type => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>
        </div>
        <div style={{ flex: 1, minWidth: '200px' }}>
          <label htmlFor="search-text" className="small">Search:</label>
          <input
            id="search-text"
            type="text"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="Search by title or content..."
            style={{ padding: '0.5rem', width: '100%', marginLeft: '0.5rem' }}
          />
        </div>
      </div>

      {error && <p className="error">{error}</p>}
      
      {loading ? (
        <p>Loading assets...</p>
      ) : assets.length === 0 ? (
        <div className="empty-state">
          <p>No assets found. Create your first asset using the "Add Asset" button.</p>
        </div>
      ) : (
        <div className="asset-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1rem' }}>
          {assets.map(asset => (
            <div key={asset.id} className="asset-card" style={{ border: '1px solid #ccc', padding: '1rem', borderRadius: '4px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
                <h3 style={{ margin: 0 }}>{asset.title}</h3>
                <span className="pill-badge">{asset.type}</span>
              </div>
              <p className="small" style={{ color: '#666', marginBottom: '0.5rem' }}>
                {asset.content.substring(0, 150)}...
              </p>
              {asset.tags.length > 0 && (
                <div style={{ marginBottom: '0.5rem' }}>
                  {asset.tags.map(tag => (
                    <span key={tag} className="pill-badge small" style={{ marginRight: '0.25rem' }}>{tag}</span>
                  ))}
                </div>
              )}
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  onClick={() => setShowAssetModal(asset)}
                  className="button-outline small"
                >
                  Open
                </button>
                <button
                  type="button"
                  onClick={() => handleCopyAsset(asset)}
                  className="button-outline small"
                >
                  Copy
                </button>
                <button
                  type="button"
                  onClick={() => handleInsertIntoAsk(asset)}
                  className="button-outline small"
                >
                  Insert into Ask
                </button>
                <div style={{ position: 'relative', display: 'inline-block' }}>
                  <button
                    type="button"
                    className="button-outline small"
                    onClick={(e) => {
                      const menu = e.currentTarget.nextElementSibling as HTMLElement;
                      menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
                    }}
                  >
                    Export ▼
                  </button>
                  <div style={{ position: 'absolute', top: '100%', left: 0, background: 'white', border: '1px solid #ccc', borderRadius: '4px', padding: '0.5rem', display: 'none', zIndex: 10 }}>
                    <button type="button" onClick={() => handleExportAsset(asset, 'txt')} className="button-outline small" style={{ display: 'block', width: '100%', marginBottom: '0.25rem' }}>TXT</button>
                    <button type="button" onClick={() => handleExportAsset(asset, 'md')} className="button-outline small" style={{ display: 'block', width: '100%', marginBottom: '0.25rem' }}>MD</button>
                    <button type="button" onClick={() => handleExportAsset(asset, 'pdf')} className="button-outline small" style={{ display: 'block', width: '100%' }}>PDF</button>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => handleDeleteAsset(asset.id)}
                  className="button-outline small"
                  style={{ color: 'red' }}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showAddModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: 'white', padding: '2rem', borderRadius: '8px', maxWidth: '600px', width: '90%', maxHeight: '90vh', overflow: 'auto' }}>
            <h3>Add Asset</h3>
            <label style={{ display: 'block', marginTop: '1rem' }}>
              Type:
              <select
                value={newAsset.type}
                onChange={(e) => setNewAsset({ ...newAsset, type: e.target.value })}
                style={{ width: '100%', padding: '0.5rem', marginTop: '0.25rem' }}
              >
                {ASSET_TYPES.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </label>
            <label style={{ display: 'block', marginTop: '1rem' }}>
              Title:
              <input
                type="text"
                value={newAsset.title}
                onChange={(e) => setNewAsset({ ...newAsset, title: e.target.value })}
                style={{ width: '100%', padding: '0.5rem', marginTop: '0.25rem' }}
                placeholder="Asset title"
              />
            </label>
            <label style={{ display: 'block', marginTop: '1rem' }}>
              Content:
              <textarea
                value={newAsset.content}
                onChange={(e) => setNewAsset({ ...newAsset, content: e.target.value })}
                style={{ width: '100%', padding: '0.5rem', marginTop: '0.25rem', minHeight: '200px' }}
                placeholder="Paste or type asset content here"
              />
            </label>
            <label style={{ display: 'block', marginTop: '1rem' }}>
              Tags (comma-separated):
              <input
                type="text"
                value={newAsset.tags}
                onChange={(e) => setNewAsset({ ...newAsset, tags: e.target.value })}
                style={{ width: '100%', padding: '0.5rem', marginTop: '0.25rem' }}
                placeholder="tag1, tag2, tag3"
              />
            </label>
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
              <button type="button" onClick={handleCreateAsset} className="button-primary">Create</button>
              <button type="button" onClick={() => setShowAddModal(false)} className="button-outline">Cancel</button>
            </div>
          </div>
        </div>
      )}

      {showAssetModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: 'white', padding: '2rem', borderRadius: '8px', maxWidth: '800px', width: '90%', maxHeight: '90vh', overflow: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '1rem' }}>
              <div>
                <h3 style={{ margin: 0 }}>{showAssetModal.title}</h3>
                <span className="pill-badge">{showAssetModal.type}</span>
              </div>
              <button type="button" onClick={() => setShowAssetModal(null)} className="button-outline">Close</button>
            </div>
            <pre style={{ whiteSpace: 'pre-wrap', background: '#f5f5f5', padding: '1rem', borderRadius: '4px', overflow: 'auto' }}>
              {showAssetModal.content}
            </pre>
            {showAssetModal.tags.length > 0 && (
              <div style={{ marginTop: '1rem' }}>
                <strong>Tags:</strong> {showAssetModal.tags.join(', ')}
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
};


