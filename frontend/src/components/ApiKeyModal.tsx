import React, { useState, useEffect, useRef } from 'react';
import { Key, Shield, ExternalLink, Check, Trash2, X, AlertCircle } from 'lucide-react';
import { saveApiKey, getApiKey, removeApiKey } from '../utils/security';

interface ApiKeyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onKeyChange: (key: string | null) => void;
}

export const ApiKeyModal: React.FC<ApiKeyModalProps> = ({ isOpen, onClose, onKeyChange }) => {
  const [apiKey, setApiKey] = useState('');
  const [saved, setSaved] = useState(false);
  const overlayRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<number | null>(null);

  useEffect(() => {
    const storedKey = getApiKey() || '';
    setApiKey(storedKey);
  }, [isOpen]);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) window.clearTimeout(timeoutRef.current);
    };
  }, []);

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanKey = apiKey.trim();
    if (cleanKey) {
      saveApiKey(cleanKey);
      onKeyChange(cleanKey);
    } else {
      removeApiKey();
      onKeyChange(null);
    }
    setSaved(true);
    timeoutRef.current = window.setTimeout(() => {
      setSaved(false);
      onClose();
    }, 800);
  };

  const handleClear = () => {
    removeApiKey();
    setApiKey('');
    onKeyChange(null);
  };

  return (
    <div
      ref={overlayRef}
      className="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="apikey-modal-title"
      onClick={(e) => { if (e.target === overlayRef.current) onClose(); }}
      style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(15, 23, 42, 0.65)',
      backdropFilter: 'blur(4px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '16px'
    }}>
      <div className="card modal-card" style={{
        maxWidth: '520px',
        width: '100%',
        backgroundColor: 'var(--bg-card)',
        borderRadius: '12px',
        boxShadow: 'var(--shadow-lg)',
        border: '1px solid var(--border-color)',
        padding: '24px',
        position: 'relative'
      }}>
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
            padding: '4px'
          }}
          aria-label="Cerrar"
        >
          <X size={20} />
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '8px',
            backgroundColor: 'rgba(14, 165, 233, 0.12)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--primary)'
          }}>
            <Key size={20} aria-hidden="true" />
          </div>
          <div>
            <h3 id="apikey-modal-title" style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-main)' }}>
              Configurar Google Gemini API Key
            </h3>
            <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Modo BYOK (Bring Your Own Key) para el Copiloto IA
            </p>
          </div>
        </div>

        <form onSubmit={handleSave}>
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 500, marginBottom: '6px', color: 'var(--text-main)' }}>
              Tu Gemini API Key:
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="AIzaSy..."
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: '6px',
                border: '1px solid var(--border-color)',
                backgroundColor: 'var(--bg-input)',
                color: 'var(--text-main)',
                fontSize: '0.9rem',
                fontFamily: 'monospace',
                outline: 'none',
                boxSizing: 'border-box'
              }}
            />
          </div>

          <div style={{
            backgroundColor: 'var(--bg-input)',
            border: '1px solid var(--border-color)',
            borderRadius: '8px',
            padding: '12px',
            fontSize: '0.8rem',
            color: 'var(--text-muted)',
            marginBottom: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px'
          }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
              <Shield size={14} aria-hidden="true" style={{ color: 'var(--accent-emerald)', flexShrink: 0, marginTop: '2px' }} />
              <span><strong style={{ color: 'var(--text-main)' }}>Seguridad Local:</strong> La clave se almacena ofuscada (Base64, no cifrado) en tu navegador (<code>localStorage</code>) y nunca en el servidor.</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
              <AlertCircle size={14} aria-hidden="true" style={{ color: 'var(--primary)', flexShrink: 0, marginTop: '2px' }} />
              <span><strong style={{ color: 'var(--text-main)' }}>Backend US:</strong> El servidor en Google Cloud Run evita restricciones geográficas.</span>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <a
              href="https://aistudio.google.com/app/apikey"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                fontSize: '0.8rem',
                color: 'var(--primary)',
                textDecoration: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              Obtener clave gratis en Google AI Studio <ExternalLink size={12} aria-hidden="true" />
            </a>

            <div style={{ display: 'flex', gap: '8px' }}>
              {apiKey && (
                <button
                  type="button"
                  onClick={handleClear}
                  className="btn btn-outline"
                  style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.85rem' }}
                >
                  <Trash2 size={14} aria-hidden="true" /> Quitar
                </button>
              )}
              <button
                type="submit"
                className="btn btn-primary"
                style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem' }}
              >
                {saved ? <><Check size={14} aria-hidden="true" /> Guardada</> : 'Guardar Clave'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
