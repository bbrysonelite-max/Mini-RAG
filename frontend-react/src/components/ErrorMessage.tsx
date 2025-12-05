interface ErrorMessageProps {
  title?: string;
  message: string;
  details?: string;
  onRetry?: () => void;
  type?: 'error' | 'warning' | 'info';
}

export const ErrorMessage = ({ 
  title = 'Error', 
  message, 
  details, 
  onRetry,
  type = 'error' 
}: ErrorMessageProps) => {
  const colorMap = {
    error: '#ff4444',
    warning: '#ff9800',
    info: '#2196f3'
  };
  
  const iconMap = {
    error: '❌',
    warning: '⚠️',
    info: 'ℹ️'
  };
  
  return (
    <div
      className={`error-message error-${type}`}
      style={{
        border: `1px solid ${colorMap[type]}`,
        borderRadius: '8px',
        padding: '1rem',
        marginTop: '1rem',
        background: `${colorMap[type]}10`
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span style={{ fontSize: '1.5rem' }}>{iconMap[type]}</span>
        <div style={{ flex: 1 }}>
          <h4 style={{ margin: 0, color: colorMap[type] }}>{title}</h4>
          <p style={{ margin: '0.5rem 0', color: '#ddd' }}>{message}</p>
          {details && (
            <details style={{ marginTop: '0.5rem' }}>
              <summary style={{ cursor: 'pointer', color: '#888', fontSize: '0.85rem' }}>
                Show details
              </summary>
              <pre style={{ 
                marginTop: '0.5rem', 
                padding: '0.5rem', 
                background: '#1a1a1a',
                borderRadius: '4px',
                fontSize: '0.8rem',
                overflow: 'auto'
              }}>
                {details}
              </pre>
            </details>
          )}
        </div>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="button-outline"
          style={{ marginTop: '1rem' }}
        >
          Try Again
        </button>
      )}
    </div>
  );
};


