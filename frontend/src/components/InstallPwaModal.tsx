import React, { useEffect, useRef } from 'react';
import { Smartphone, X, Share2, PlusSquare, Check } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onInstallPrompt?: () => void;
  isInstallable: boolean;
  isIOS: boolean;
}

export const InstallPwaModal: React.FC<Props> = ({
  isOpen,
  onClose,
  onInstallPrompt,
  isInstallable,
  isIOS,
}) => {
  const { t } = useLanguage();
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      ref={overlayRef}
      className="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="pwa-modal-title"
      onClick={(e) => { if (e.target === overlayRef.current) onClose(); }}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.7)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        padding: '16px',
      }}
    >
      <div
        className="card modal-card"
        style={{
          maxWidth: '480px',
          width: '100%',
          backgroundColor: 'var(--bg-card)',
          borderRadius: '12px',
          boxShadow: 'var(--shadow-lg)',
          border: '1px solid var(--border-color)',
          padding: '24px',
          position: 'relative',
        }}
      >
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '16px',
            right: '16px',
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            padding: '4px',
          }}
          aria-label={t.pwaModal.close}
        >
          <X size={20} aria-hidden="true" />
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
          <div
            style={{
              width: '42px',
              height: '42px',
              borderRadius: '10px',
              backgroundColor: 'rgba(14, 165, 233, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--primary)',
            }}
          >
            <Smartphone size={22} aria-hidden="true" />
          </div>
          <div>
            <h3 id="pwa-modal-title" style={{ margin: 0, fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-main)' }}>
              {t.pwaModal.title}
            </h3>
            <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              PWA
            </p>
          </div>
        </div>

        <p style={{ fontSize: '0.875rem', color: 'var(--text-main)', marginBottom: '16px', lineHeight: 1.5 }}>
          {t.pwaModal.desc}
        </p>

        {isIOS ? (
          <div
            style={{
              backgroundColor: 'var(--bg-input)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              padding: '16px',
              fontSize: '0.85rem',
              color: 'var(--text-main)',
              marginBottom: '20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
          >
            <div style={{ fontWeight: 600, color: 'var(--primary)' }}>
              iOS Safari:
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Share2 size={18} aria-hidden="true" style={{ color: 'var(--primary)', flexShrink: 0 }} />
              <span>{t.pwaModal.iosInstructions}</span>
            </div>
          </div>
        ) : (
          <div
            style={{
              backgroundColor: 'var(--bg-input)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              padding: '14px',
              fontSize: '0.8rem',
              color: 'var(--text-muted)',
              marginBottom: '20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent-emerald)' }}>
              <Check size={16} aria-hidden="true" /> <strong>Web App:</strong> Installable on Desktop & Mobile.
            </div>
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
          <button className="btn btn-outline" onClick={onClose}>
            {t.pwaModal.close}
          </button>
          {!isIOS && isInstallable && onInstallPrompt && (
            <button
              className="btn btn-primary"
              onClick={() => {
                onInstallPrompt();
                onClose();
              }}
            >
              <Smartphone size={16} /> {t.pwaModal.installNow}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

