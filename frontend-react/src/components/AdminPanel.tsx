import { useEffect, useState } from 'react';
import type { WorkspaceSummary } from '../types';
import { UserManagement } from './UserManagement';

export const AdminPanel = () => {
  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'workspaces' | 'users'>('workspaces');

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const resp = await fetch('/api/v1/admin/workspaces', {
          headers: {
            'Content-Type': 'application/json'
          }
        });
        if (!resp.ok) throw new Error('Admin access required.');
        const data = await resp.json();
        setWorkspaces(data.workspaces ?? []);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (error) {
    return (
      <section>
        <h2>Admin</h2>
        <p className="error">{error}</p>
      </section>
    );
  }

  return (
    <section>
      <h2>Admin</h2>
      
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', borderBottom: '1px solid var(--border-strong)' }}>
        <button
          onClick={() => setActiveTab('workspaces')}
          className={activeTab === 'workspaces' ? 'button-primary' : 'button-outline'}
          style={{ borderBottom: 'none', borderRadius: '8px 8px 0 0' }}
        >
          Workspaces
        </button>
        <button
          onClick={() => setActiveTab('users')}
          className={activeTab === 'users' ? 'button-primary' : 'button-outline'}
          style={{ borderBottom: 'none', borderRadius: '8px 8px 0 0' }}
        >
          Users
        </button>
      </div>

      {activeTab === 'workspaces' && (
        <>
          {loading && <p className="small">Loading tenant data…</p>}
          {!loading && workspaces.length === 0 ? (
            <div className="empty-state">No workspace data available or insufficient permissions.</div>
          ) : (
            <table className="table">
          <thead>
            <tr>
              <th>Workspace</th>
              <th>Organization</th>
              <th>Plan</th>
              <th>Billing</th>
            </tr>
          </thead>
          <tbody>
            {workspaces.map((ws) => (
              <tr key={ws.id}>
                <td>{ws.name}</td>
                <td>{ws.organization_name}</td>
                <td>{ws.plan}</td>
                <td>{ws.billing_status}</td>
              </tr>
            ))}
          </tbody>
            </table>
          )}
        </>
      )}

      {activeTab === 'users' && <UserManagement />}
    </section>
  );
};

