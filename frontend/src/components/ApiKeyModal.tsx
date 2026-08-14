import React, { useState, useEffect } from 'react';
import { Key, Shield, ExternalLink, Check, Trash2, X, AlertCircle } from 'lucide-react';

interface ApiKeyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onKeyChange: (key: string | null) => void;
}

export const ApiKeyModal: React.FC<ApiKeyModalProps> = ({ isOpen, onClose, onKeyChange }) => {
  const [apiKey, setApiKey] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const storedKey = localStorage.getItem('dataflow_gemini_api_key') || '';
    setApiKey(storedKey);
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanKey = apiKey.trim();
    if (cleanKey) {
      localStorage.setItem('dataflow_gemini_api_key', cleanKey);
      onKeyChange(cleanKey);
    } else {
      localStorage.removeItem('dataflow_gemini_api_key');
      onKeyChange(null);
    }
    setSaved(true);
    setTimeout(() => {
      setSaved(false);
      onClose();
    }, 800);
  };

  const handleClear = () => {
    localStorage.removeItem('dataflow_gemini_api_key');
    setApiKey('');
    onKeyChange(null);
  };

  return (
    <div className="modal-overlay" style={{
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
      <div className="card" style={{
        maxWidth: '520px',
        width: '100%',
        backgroundColor: '#ffffff',
        borderRadius: '12px',
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
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
            backgroundColor: '#eff6ff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--primary-color)'
          }}>
            <Key size={20} />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 600, color: 'var(--text-main)' }}>
              Configurar Google Gemini API Key
            </h3>
            <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Modo BYOK (Bring Your Own Key) para la IA Copilot
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
                fontSize: '0.9rem',
                fontFamily: 'monospace',
                outline: 'none',
                boxSizing: 'border-box'
              }}
            />
          </div>

          <div style={{
            backgroundColor: '#f8fafc',
            border: '1px solid #e2e8f0',
            borderRadius: '8px',
            padding: '12px',
            fontSize: '0.8rem',
            color: '#475569',
            marginBottom: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px'
          }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
              <Shield size={14} style={{ color: '#059669', flexShrink: 0, marginTop: '2px' }} />
              <span><strong>Seguridad Total:</strong> La clave se almacena exclusivamente en tu navegador (<code>localStorage</code>) y nunca se guarda en bases de datos.</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
              <AlertCircle size={14} style={{ color: '#0284c7', flexShrink: 0, marginTop: '2px' }} />
              <span><strong>Proxy en US:</strong> El backend (desplegado en US Central) gestiona las peticiones evitando restricciones geográficas europeas.</span>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <a
              href="https://aistudio.google.com/app/apikey"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                fontSize: '0.8rem',
                color: 'var(--primary-color)',
                textDecoration: 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              Obtener clave gratis en Google AI Studio <ExternalLink size={12} />
            </a>

            <div style={{ display: 'flex', gap: '8px' }}>
              {apiKey && (
                <button
                  type="button"
                  onClick={handleClear}
                  className="btn btn-outline"
                  style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.85rem' }}
                >
                  <Trash2 size={14} /> Quitar
                </button>
              )}
              <button
                type="submit"
                className="btn btn-primary"
                style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem' }}
              >
                {saved ? <><Check size={14} /> Guardada</> : 'Guardar Clave'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
