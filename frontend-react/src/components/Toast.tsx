import { useEffect, useState } from 'react';
import type { Toast as ToastType } from '../hooks/useToast';

interface ToastProps {
  toast: ToastType;
  onClose: (id: string) => void;
}

export const Toast = ({ toast, onClose }: ToastProps) => {
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    if (toast.duration && toast.duration > 0) {
      const timer = setTimeout(() => {
        handleClose();
      }, toast.duration);

      return () => clearTimeout(timer);
    }
  }, [toast.duration]);

  const handleClose = () => {
    setIsExiting(true);
    setTimeout(() => onClose(toast.id), 300); // Match animation duration
  };

  const iconMap = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: 'ℹ'
  };

  const colorMap = {
    success: '#10b981',
    error: '#ef4444',
    warning: '#f59e0b',
    info: '#3b82f6'
  };

  return (
    <div
      className={`toast toast-${toast.type} ${isExiting ? 'toast-exit' : 'toast-enter'}`}
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: '0.75rem',
        padding: '1rem 1.25rem',
        background: 'rgba(15, 16, 18, 0.95)',
        border: `1px solid ${colorMap[toast.type]}40`,
        borderRadius: '12px',
        boxShadow: `0 8px 32px rgba(0, 0, 0, 0.4), 0 0 0 1px ${colorMap[toast.type]}20`,
        backdropFilter: 'blur(12px)',
        minWidth: '320px',
        maxWidth: '420px',
        position: 'relative',
        overflow: 'hidden'
      }}
    >
      <div
        className="toast-icon"
        style={{
          width: '24px',
          height: '24px',
          borderRadius: '50%',
          background: `${colorMap[toast.type]}20`,
          color: colorMap[toast.type],
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '14px',
          fontWeight: 'bold',
          flexShrink: 0
        }}
      >
        {iconMap[toast.type]}
      </div>

      <div style={{ flex: 1 }}>
        {toast.title && (
          <div style={{ 
            fontWeight: 600, 
            marginBottom: '0.25rem',
            color: '#f9fafb',
            fontSize: '0.9rem'
          }}>
            {toast.title}
          </div>
        )}
        <div style={{ 
          color: 'rgba(249, 250, 251, 0.85)',
          fontSize: '0.85rem',
          lineHeight: 1.5
        }}>
          {toast.message}
        </div>
        {toast.action && (
          <button
            onClick={toast.action.onClick}
            style={{
              marginTop: '0.5rem',
              padding: '0.25rem 0.75rem',
              background: `${colorMap[toast.type]}20`,
              border: `1px solid ${colorMap[toast.type]}40`,
              borderRadius: '6px',
              color: colorMap[toast.type],
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            {toast.action.label}
          </button>
        )}
      </div>

      <button
        onClick={handleClose}
        aria-label="Close notification"
        style={{
          background: 'transparent',
          border: 'none',
          color: 'rgba(249, 250, 251, 0.5)',
          cursor: 'pointer',
          padding: '0.25rem',
          fontSize: '1.2rem',
          lineHeight: 1,
          flexShrink: 0,
          transition: 'color 150ms ease'
        }}
        onMouseEnter={(e) => e.currentTarget.style.color = '#f9fafb'}
        onMouseLeave={(e) => e.currentTarget.style.color = 'rgba(249, 250, 251, 0.5)'}
      >
        ×
      </button>

      {toast.duration && toast.duration > 0 && (
        <div
          className="toast-progress"
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            height: '3px',
            background: `${colorMap[toast.type]}40`,
            animation: `toastProgress ${toast.duration}ms linear`
          }}
        />
      )}

      <style>{`
        @keyframes toast-enter {
          from {
            opacity: 0;
            transform: translateX(100%);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }

        @keyframes toast-exit {
          from {
            opacity: 1;
            transform: translateX(0);
          }
          to {
            opacity: 0;
            transform: translateX(100%);
          }
        }

        @keyframes toastProgress {
          from {
            transform: scaleX(1);
            transform-origin: left;
          }
          to {
            transform: scaleX(0);
            transform-origin: left;
          }
        }

        .toast-enter {
          animation: toast-enter 300ms ease-out;
        }

        .toast-exit {
          animation: toast-exit 300ms ease-in;
        }
      `}</style>
    </div>
  );
};


