import React, { useState, useEffect } from 'react';
import { Database, Sparkles, ShieldCheck, Key } from 'lucide-react';
import { ApiKeyModal } from './ApiKeyModal';

export const Header: React.FC = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [hasApiKey, setHasApiKey] = useState(false);

  useEffect(() => {
    const key = localStorage.getItem('dataflow_gemini_api_key');
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
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
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
              backgroundColor: hasApiKey ? '#ecfdf5' : '#f8fafc',
              borderColor: hasApiKey ? '#a7f3d0' : '#cbd5e1',
              color: hasApiKey ? '#065f46' : '#334155',
              borderRadius: '6px',
              cursor: 'pointer'
            }}
            title="Configura tu API Key de Google Gemini para usar la IA Copilot"
          >
            <Key size={14} style={{ color: hasApiKey ? '#059669' : 'var(--primary-color)' }} />
            {hasApiKey ? (
              <span>Gemini IA: <strong style={{ color: '#059669' }}>Activa</strong></span>
            ) : (
              <span>Configurar API Key</span>
            )}
          </button>

          <span className="badge badge-emerald" title="Cumplimiento estricto de privacidad: procesamiento efímero y minimización de datos">
            <ShieldCheck size={13} /> Gobierno RGPD / Privacidad
          </span>
          <span className="badge badge-primary">
            <Sparkles size={12} /> Copiloto ETL Activo
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
