import { CSSProperties } from 'react';

interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large';
  message?: string;
  progress?: number;
  style?: CSSProperties;
}

export const LoadingSpinner = ({ size = 'medium', message, progress, style }: LoadingSpinnerProps) => {
  const sizeMap = {
    small: 20,
    medium: 40,
    large: 60
  };
  
  const spinnerSize = sizeMap[size];
  
  return (
    <div
      className="loading-spinner-container"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
        ...style
      }}
    >
      <svg
        className="loading-spinner"
        width={spinnerSize}
        height={spinnerSize}
        viewBox="0 0 50 50"
        style={{
          animation: 'spin 1s linear infinite'
        }}
      >
        <circle
          className="path"
          cx="25"
          cy="25"
          r="20"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
          style={{
            strokeDasharray: '1, 200',
            strokeDashoffset: '0',
            animation: 'dash 1.5s ease-in-out infinite'
          }}
        />
      </svg>
      
      {message && (
        <p className="loading-message" style={{ marginTop: '1rem', fontSize: '0.9rem', color: '#888' }}>
          {message}
        </p>
      )}
      
      {progress !== undefined && (
        <div style={{ width: '200px', marginTop: '1rem' }}>
          <div
            style={{
              width: '100%',
              height: '6px',
              background: '#333',
              borderRadius: '3px',
              overflow: 'hidden'
            }}
          >
            <div
              style={{
                width: `${progress}%`,
                height: '100%',
                background: '#ff6b35',
                borderRadius: '3px',
                transition: 'width 0.3s ease'
              }}
            />
          </div>
          <p style={{ textAlign: 'center', marginTop: '0.5rem', fontSize: '0.85rem', color: '#666' }}>
            {progress}%
          </p>
        </div>
      )}
      
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        
        @keyframes dash {
          0% {
            stroke-dasharray: 1, 200;
            stroke-dashoffset: 0;
          }
          50% {
            stroke-dasharray: 89, 200;
            stroke-dashoffset: -35px;
          }
          100% {
            stroke-dasharray: 89, 200;
            stroke-dashoffset: -124px;
          }
        }
      `}</style>
    </div>
  );
};

