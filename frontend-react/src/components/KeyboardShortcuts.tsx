import { KeyboardShortcut } from '../hooks/useKeyboardShortcuts';

interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
  shortcuts: KeyboardShortcut[];
}

export const KeyboardShortcutsModal = ({ isOpen, onClose, shortcuts }: KeyboardShortcutsModalProps) => {
  if (!isOpen) return null;

  // Group shortcuts by category
  const groupedShortcuts = shortcuts.reduce((acc, shortcut) => {
    const category = shortcut.category || 'General';
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(shortcut);
    return acc;
  }, {} as Record<string, KeyboardShortcut[]>);

  const formatKey = (shortcut: KeyboardShortcut) => {
    const keys: string[] = [];
    if (shortcut.ctrl) keys.push('⌘');
    if (shortcut.alt) keys.push('⌥');
    if (shortcut.shift) keys.push('⇧');
    keys.push(shortcut.key.toUpperCase());
    return keys.join(' + ');
  };

  return (
    <div
      className="modal-overlay"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0, 0, 0, 0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 10000,
        backdropFilter: 'blur(4px)',
        animation: 'fadeIn 200ms ease'
      }}
      onClick={onClose}
    >
      <div
        className="modal-content"
        style={{
          background: 'var(--bg-panel-solid)',
          border: '1px solid var(--border-strong)',
          borderRadius: 'var(--radius-xl)',
          maxWidth: '600px',
          width: '90%',
          maxHeight: '80vh',
          overflow: 'auto',
          padding: '2rem',
          boxShadow: 'var(--shadow-ambient)',
          animation: 'slideIn 300ms ease'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h2 style={{ margin: 0, fontSize: '1.5rem' }}>⌨️ Keyboard Shortcuts</h2>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              fontSize: '1.5rem',
              cursor: 'pointer',
              padding: '0.25rem',
              lineHeight: 1
            }}
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {Object.entries(groupedShortcuts).map(([category, categoryShortcuts]) => (
          <div key={category} style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ 
              fontSize: '0.85rem', 
              textTransform: 'uppercase', 
              letterSpacing: '0.1em',
              color: 'var(--text-muted)',
              marginBottom: '0.75rem',
              fontWeight: 600
            }}>
              {category}
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {categoryShortcuts.map((shortcut, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '0.75rem',
                    background: 'rgba(255, 255, 255, 0.02)',
                    borderRadius: '8px',
                    border: '1px solid rgba(255, 255, 255, 0.06)'
                  }}
                >
                  <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                    {shortcut.description}
                  </span>
                  <kbd
                    style={{
                      padding: '0.25rem 0.75rem',
                      background: 'rgba(255, 255, 255, 0.1)',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '6px',
                      fontFamily: 'monospace',
                      fontSize: '0.85rem',
                      color: 'var(--accent)',
                      fontWeight: 600,
                      boxShadow: '0 2px 4px rgba(0, 0, 0, 0.2)'
                    }}
                  >
                    {formatKey(shortcut)}
                  </kbd>
                </div>
              ))}
            </div>
          </div>
        ))}

        <div style={{ 
          marginTop: '1.5rem',
          paddingTop: '1.5rem',
          borderTop: '1px solid var(--divider)',
          fontSize: '0.85rem',
          color: 'var(--text-muted)',
          textAlign: 'center'
        }}>
          Press <kbd style={{ 
            padding: '0.2rem 0.5rem',
            background: 'rgba(255, 255, 255, 0.1)',
            borderRadius: '4px',
            fontFamily: 'monospace'
          }}>?</kbd> anytime to view shortcuts
        </div>
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(-20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
};


