import { useState, useEffect } from 'react';

interface User {
  id: string;
  username?: string;
  email?: string;
  name: string;
  role: string;
  auth_method: string;
  created_at: string;
}

export const UserManagement = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newUser, setNewUser] = useState({ username: '', password: '', name: '', role: 'admin' });

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const resp = await fetch('/api/v1/admin/users', {
        headers: { 'Content-Type': 'application/json' }
      });
      if (!resp.ok) throw new Error('Failed to load users');
      const data = await resp.json();
      setUsers(data.users || []);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const resp = await fetch('/api/v1/admin/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newUser)
      });
      if (!resp.ok) {
        const errorData = await resp.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to create user');
      }
      setShowCreateForm(false);
      setNewUser({ username: '', password: '', name: '', role: 'admin' });
      loadUsers();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const handleDeleteUser = async (userId: string) => {
    if (!confirm('Are you sure you want to delete this user?')) return;
    try {
      const resp = await fetch(`/api/v1/admin/users/${userId}`, {
        method: 'DELETE'
      });
      if (!resp.ok) throw new Error('Failed to delete user');
      loadUsers();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <div className="user-management">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3>User Management</h3>
        <button onClick={() => setShowCreateForm(!showCreateForm)} className="button-primary">
          {showCreateForm ? 'Cancel' : 'Create User'}
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      {showCreateForm && (
        <form onSubmit={handleCreateUser} className="create-user-form" style={{ marginBottom: '1rem', padding: '1rem', background: 'var(--bg-panel)', borderRadius: '8px' }}>
          <h4>Create New User</h4>
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              value={newUser.username}
              onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
              required
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={newUser.password}
              onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
              required
              minLength={8}
            />
          </div>
          <div className="form-group">
            <label>Name</label>
            <input
              type="text"
              value={newUser.name}
              onChange={(e) => setNewUser({ ...newUser, name: e.target.value })}
              required
            />
          </div>
          <div className="form-group">
            <label>Role</label>
            <select
              value={newUser.role}
              onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
            >
              <option value="admin">Admin</option>
              <option value="editor">Editor</option>
              <option value="reader">Reader</option>
            </select>
          </div>
          <button type="submit" className="button-primary">Create User</button>
        </form>
      )}

      {loading && <p className="small">Loading users...</p>}
      
      {!loading && users.length === 0 && (
        <div className="empty-state">No users found.</div>
      )}

      {!loading && users.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th>Username</th>
              <th>Email</th>
              <th>Name</th>
              <th>Role</th>
              <th>Auth Method</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>{user.username || '—'}</td>
                <td>{user.email || '—'}</td>
                <td>{user.name}</td>
                <td><span className="pill-badge">{user.role}</span></td>
                <td>{user.auth_method}</td>
                <td>{new Date(user.created_at).toLocaleDateString()}</td>
                <td>
                  <button
                    onClick={() => handleDeleteUser(user.id)}
                    className="button-outline small"
                    disabled={user.role === 'admin' && users.filter(u => u.role === 'admin').length === 1}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};




