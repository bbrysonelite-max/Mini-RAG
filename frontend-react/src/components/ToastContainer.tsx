import { Toast } from './Toast';
import type { Toast as ToastType } from '../hooks/useToast';

interface ToastContainerProps {
  toasts: ToastType[];
  onClose: (id: string) => void;
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center';
}

export const ToastContainer = ({ 
  toasts, 
  onClose, 
  position = 'top-right' 
}: ToastContainerProps) => {
  const positionStyles: Record<string, React.CSSProperties> = {
    'top-right': {
      top: '1.5rem',
      right: '1.5rem',
      alignItems: 'flex-end'
    },
    'top-left': {
      top: '1.5rem',
      left: '1.5rem',
      alignItems: 'flex-start'
    },
    'bottom-right': {
      bottom: '1.5rem',
      right: '1.5rem',
      alignItems: 'flex-end'
    },
    'bottom-left': {
      bottom: '1.5rem',
      left: '1.5rem',
      alignItems: 'flex-start'
    },
    'top-center': {
      top: '1.5rem',
      left: '50%',
      transform: 'translateX(-50%)',
      alignItems: 'center'
    },
    'bottom-center': {
      bottom: '1.5rem',
      left: '50%',
      transform: 'translateX(-50%)',
      alignItems: 'center'
    }
  };

  return (
    <div
      className="toast-container"
      style={{
        position: 'fixed',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem',
        pointerEvents: 'none',
        ...positionStyles[position]
      }}
      aria-live="polite"
      aria-atomic="true"
    >
      {toasts.map((toast) => (
        <div key={toast.id} style={{ pointerEvents: 'auto' }}>
          <Toast toast={toast} onClose={onClose} />
        </div>
      ))}
    </div>
  );
};

