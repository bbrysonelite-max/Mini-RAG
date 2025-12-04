import { CSSProperties } from 'react';

interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
  style?: CSSProperties;
}

export const EmptyState = ({ 
  icon = '📦', 
  title, 
  description, 
  action, 
  secondaryAction,
  style 
}: EmptyStateProps) => {
  return (
    <div
      className="empty-state"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '3rem 2rem',
        textAlign: 'center',
        border: '1px dashed rgba(255, 255, 255, 0.15)',
        borderRadius: 'var(--radius-xl)',
        background: 'rgba(255, 255, 255, 0.02)',
        ...style
      }}
    >
      <div
        className="empty-state-icon"
        style={{
          fontSize: '4rem',
          marginBottom: '1rem',
          opacity: 0.6
        }}
      >
        {icon}
      </div>
      
      <h3
        style={{
          margin: '0 0 0.5rem 0',
          fontSize: '1.25rem',
          fontWeight: 600,
          color: 'var(--text-primary)'
        }}
      >
        {title}
      </h3>
      
      {description && (
        <p
          style={{
            margin: '0 0 1.5rem 0',
            fontSize: '0.9rem',
            color: 'var(--text-secondary)',
            maxWidth: '480px',
            lineHeight: 1.6
          }}
        >
          {description}
        </p>
      )}
      
      {action && (
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', justifyContent: 'center' }}>
          <button
            onClick={action.onClick}
            className="button-primary"
            style={{
              background: 'linear-gradient(135deg, var(--accent), #ff915c)',
              color: '#0b0b0d',
              padding: '0.75rem 1.5rem',
              borderRadius: 'var(--radius-pill)',
              border: 'none',
              fontWeight: 600,
              cursor: 'pointer',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              fontSize: '0.85rem'
            }}
          >
            {action.label}
          </button>
          
          {secondaryAction && (
            <button
              onClick={secondaryAction.onClick}
              className="button-outline"
              style={{
                padding: '0.75rem 1.5rem',
                borderRadius: 'var(--radius-pill)',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                background: 'transparent',
                color: 'var(--text-secondary)',
                fontWeight: 600,
                cursor: 'pointer',
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                fontSize: '0.85rem'
              }}
            >
              {secondaryAction.label}
            </button>
          )}
        </div>
      )}
    </div>
  );
};

// Pre-built empty states
export const EmptySourcesState = ({ onIngest }: { onIngest: () => void }) => (
  <EmptyState
    icon="📚"
    title="No Sources Yet"
    description="Start by uploading documents, adding YouTube videos, or pasting text content to build your knowledge base."
    action={{
      label: "Add Documents",
      onClick: onIngest
    }}
  />
);

export const EmptyAssetsState = ({ onAsk }: { onAsk: () => void }) => (
  <EmptyState
    icon="✨"
    title="No Assets Saved"
    description="Assets are reusable templates, workflows, and content you create. Try asking your Second Brain to build something, then save it as an asset."
    action={{
      label: "Ask to Create",
      onClick: onAsk
    }}
  />
);

export const EmptyHistoryState = () => (
  <EmptyState
    icon="🕐"
    title="No History Yet"
    description="Your command history will appear here as you use the Second Brain commands to generate workflows, prompts, and other assets."
  />
);

export const EmptySearchState = ({ query }: { query: string }) => (
  <EmptyState
    icon="🔍"
    title="No Results Found"
    description={`No matches found for "${query}". Try using different keywords or checking your spelling.`}
  />
);

export const EmptyWorkspaceState = ({ onCreate }: { onCreate: () => void }) => (
  <EmptyState
    icon="🏢"
    title="No Workspaces"
    description="Workspaces help you organize different projects and knowledge bases. Create your first workspace to get started."
    action={{
      label: "Create Workspace",
      onClick: onCreate
    }}
  />
);

