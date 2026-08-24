import React, { useState, useEffect } from 'react';
import { Database, Sparkles, ShieldCheck, Key } from 'lucide-react';
import { ApiKeyModal } from './ApiKeyModal';
import { getApiKey } from '../utils/security';

export const Header: React.FC = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [hasApiKey, setHasApiKey] = useState(false);

  useEffect(() => {
    const key = getApiKey();
    setHasApiKey(!!key);
  }, []);

  return (
    <>
      <header className="navbar">
        <div className="brand">
          <div className="brand-icon">
            <Database size={22} />
          </div>
          <div>
            <h1 className="brand-title">DataFlow AI</h1>
            <p className="brand-tagline">From raw business data to clean, trusted and actionable insights</p>
          </div>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <button
            onClick={() => setIsModalOpen(true)}
            className="btn btn-outline"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              fontSize: '0.8rem',
              fontWeight: 500,
              backgroundColor: hasApiKey ? 'rgba(16, 185, 129, 0.12)' : 'var(--bg-input)',
              borderColor: hasApiKey ? 'rgba(16, 185, 129, 0.4)' : 'var(--border-color)',
              color: hasApiKey ? 'var(--accent-emerald)' : 'var(--text-main)',
              borderRadius: '6px',
              cursor: 'pointer'
            }}
            title="Configura tu API Key de Google Gemini para usar la IA Copilot"
          >
            <Key size={14} style={{ color: hasApiKey ? 'var(--accent-emerald)' : 'var(--primary)' }} />
            {hasApiKey ? (
              <span>Gemini: <strong style={{ color: 'var(--accent-emerald)' }}>Activo</strong></span>
            ) : (
              <span>API Key</span>
            )}
          </button>

          <span className="badge badge-emerald hide-on-mobile" title="Cumplimiento estricto de privacidad: procesamiento efímero y minimización de datos">
            <ShieldCheck size={13} /> Privacidad RGPD
          </span>
          <span className="badge badge-primary hide-on-mobile">
            <Sparkles size={12} /> Copiloto ETL
          </span>
        </div>
      </header>

      <ApiKeyModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onKeyChange={(k) => setHasApiKey(!!k)}
      />
    </>
  );
};
