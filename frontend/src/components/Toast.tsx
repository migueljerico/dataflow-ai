import React, { useEffect } from 'react';

export type ToastKind = 'error' | 'success' | 'info';

export interface ToastItem {
  id: string;
  kind: ToastKind;
  message: string;
}

interface Props {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
}

export const ToastContainer: React.FC<Props> = ({ toasts, onDismiss }) => {
  if (!toasts.length) return null;
  return (
    <div
      role="region"
      aria-live="polite"
      aria-label="Notificaciones"
      style={{
        position: 'fixed',
        bottom: 16,
        right: 16,
        zIndex: 10000,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        maxWidth: 420,
      }}
    >
      {toasts.map((t) => (
        <Toast key={t.id} item={t} onDismiss={onDismiss} />
      ))}
    </div>
  );
};

const Toast: React.FC<{ item: ToastItem; onDismiss: (id: string) => void }> = ({ item, onDismiss }) => {
  useEffect(() => {
    const id = window.setTimeout(() => onDismiss(item.id), 6000);
    return () => window.clearTimeout(id);
  }, [item.id, onDismiss]);

  const bg =
    item.kind === 'error'
      ? 'rgba(244,63,94,0.95)'
      : item.kind === 'success'
        ? 'rgba(16,185,129,0.95)'
        : 'rgba(14,165,233,0.95)';

  return (
    <div
      role={item.kind === 'error' ? 'alert' : 'status'}
      style={{
        background: bg,
        color: '#fff',
        padding: '12px 14px',
        borderRadius: 10,
        fontSize: '0.875rem',
        lineHeight: 1.4,
        boxShadow: 'var(--shadow-lg)',
        display: 'flex',
        justifyContent: 'space-between',
        gap: 12,
        alignItems: 'flex-start',
      }}
    >
      <span style={{ flex: 1 }}>{item.message}</span>
      <button
        onClick={() => onDismiss(item.id)}
        aria-label="Cerrar notificación"
        style={{
          background: 'rgba(255,255,255,0.2)',
          border: 'none',
          color: '#fff',
          borderRadius: 6,
          padding: '2px 8px',
          cursor: 'pointer',
          fontSize: '0.75rem',
        }}
      >
        ×
      </button>
    </div>
  );
};
