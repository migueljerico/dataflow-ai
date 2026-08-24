import React from 'react';
import { Smartphone, X, Share2, PlusSquare, Check } from 'lucide-react';

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
  if (!isOpen) return null;

  return (
    <div
      className="modal-overlay"
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
          aria-label="Cerrar"
        >
          <X size={20} />
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
            <Smartphone size={22} />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-main)' }}>
              Instalar DataFlow AI en tu Móvil
            </h3>
            <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Aplicación Web Progresiva (PWA) de alto rendimiento
            </p>
          </div>
        </div>

        <p style={{ fontSize: '0.875rem', color: 'var(--text-main)', marginBottom: '16px', lineHeight: 1.5 }}>
          Instala DataFlow AI como una app nativa en tu pantalla de inicio para abrirla a pantalla completa, sin barras de navegación y con carga ultra rápida.
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
              Instrucciones para iPhone / iPad (Safari):
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Share2 size={18} style={{ color: 'var(--primary)', flexShrink: 0 }} />
              <span>1. Toca el botón <strong>Compartir</strong> en la barra de Safari.</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <PlusSquare size={18} style={{ color: 'var(--accent-emerald)', flexShrink: 0 }} />
              <span>2. Selecciona <strong>"Añadir a pantalla de inicio"</strong>.</span>
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
              <Check size={16} /> <strong>Acceso Instantáneo:</strong> Icono directo en tu escritorio móvil.
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--primary)' }}>
              <Check size={16} /> <strong>Experiencia Inmersiva:</strong> Interfaz limpia sin barras del navegador.
            </div>
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
          <button className="btn btn-outline" onClick={onClose}>
            Entendido
          </button>
          {!isIOS && isInstallable && onInstallPrompt && (
            <button
              className="btn btn-primary"
              onClick={() => {
                onInstallPrompt();
                onClose();
              }}
            >
              <Smartphone size={16} /> Instalar Ahora
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
