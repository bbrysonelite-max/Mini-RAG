import { CSSProperties } from 'react';

interface SkeletonProps {
  variant?: 'text' | 'circular' | 'rectangular' | 'rounded';
  width?: string | number;
  height?: string | number;
  animation?: 'pulse' | 'wave' | 'none';
  style?: CSSProperties;
}

export const Skeleton = ({ 
  variant = 'text', 
  width, 
  height, 
  animation = 'pulse',
  style 
}: SkeletonProps) => {
  const variantStyles: Record<string, CSSProperties> = {
    text: {
      height: '1em',
      borderRadius: '4px',
    },
    circular: {
      borderRadius: '50%',
    },
    rectangular: {
      borderRadius: '0',
    },
    rounded: {
      borderRadius: '8px',
    }
  };

  const baseStyle: CSSProperties = {
    background: 'rgba(255, 255, 255, 0.1)',
    width: width || '100%',
    height: height || variantStyles[variant].height || '40px',
    borderRadius: variantStyles[variant].borderRadius,
    ...style,
  };

  const animationClass = animation !== 'none' ? `skeleton-${animation}` : '';

  return (
    <>
      <div
        className={`skeleton ${animationClass}`}
        style={baseStyle}
        aria-busy="true"
        aria-live="polite"
      />
      <style>{`
        @keyframes skeleton-pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.4;
          }
        }

        @keyframes skeleton-wave {
          0% {
            transform: translateX(-100%);
          }
          100% {
            transform: translateX(100%);
          }
        }

        .skeleton-pulse {
          animation: skeleton-pulse 1.5s ease-in-out infinite;
        }

        .skeleton-wave {
          position: relative;
          overflow: hidden;
        }

        .skeleton-wave::after {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: linear-gradient(
            90deg,
            transparent,
            rgba(255, 255, 255, 0.2),
            transparent
          );
          animation: skeleton-wave 1.5s linear infinite;
        }
      `}</style>
    </>
  );
};

// Pre-built skeleton layouts
export const SkeletonChunkCard = () => (
  <div style={{
    background: 'var(--bg-panel)',
    borderRadius: '20px',
    padding: '1.6rem',
    border: '1px solid rgba(255, 255, 255, 0.1)',
  }}>
    <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.8rem', alignItems: 'center' }}>
      <Skeleton width="80px" height="20px" />
      <Skeleton width="60px" height="24px" variant="rounded" />
    </div>
    <Skeleton width="100%" height="60px" style={{ marginBottom: '0.5rem' }} />
    <Skeleton width="85%" height="16px" />
    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.8rem' }}>
      <Skeleton width="100px" height="16px" />
      <Skeleton width="80px" height="24px" variant="rounded" />
    </div>
  </div>
);

export const SkeletonSourceItem = () => (
  <div style={{
    padding: '1rem',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '12px',
    background: 'rgba(255, 255, 255, 0.02)'
  }}>
    <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
      <Skeleton variant="circular" width="40px" height="40px" />
      <div style={{ flex: 1 }}>
        <Skeleton width="60%" height="18px" style={{ marginBottom: '0.5rem' }} />
        <Skeleton width="40%" height="14px" />
      </div>
      <Skeleton width="80px" height="32px" variant="rounded" />
    </div>
  </div>
);

export const SkeletonAssetCard = () => (
  <div style={{
    padding: '1.5rem',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '16px',
    background: 'var(--bg-panel)'
  }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
      <Skeleton width="70%" height="22px" />
      <Skeleton width="60px" height="24px" variant="rounded" />
    </div>
    <Skeleton width="100%" height="80px" style={{ marginBottom: '0.5rem' }} />
    <Skeleton width="90%" height="16px" />
    <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
      <Skeleton width="80px" height="28px" variant="rounded" />
      <Skeleton width="80px" height="28px" variant="rounded" />
    </div>
  </div>
);

export const SkeletonHistoryItem = () => (
  <div style={{
    padding: '1rem',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    borderRadius: '12px',
    borderLeft: '3px solid rgba(255, 107, 53, 0.3)'
  }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
      <Skeleton width="120px" height="16px" />
      <Skeleton width="100px" height="14px" />
    </div>
    <Skeleton width="100%" height="16px" style={{ marginBottom: '0.25rem' }} />
    <Skeleton width="80%" height="16px" />
  </div>
);



