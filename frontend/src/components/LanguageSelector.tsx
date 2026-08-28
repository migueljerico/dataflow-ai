import React from 'react';
import { useLanguage } from '../context/LanguageContext';
import { Globe } from 'lucide-react';

export const LanguageSelector: React.FC = () => {
  const { language, setLanguage } = useLanguage();

  return (
    <div
      role="group"
      aria-label="Selector de idioma / Language selector"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        backgroundColor: 'var(--bg-input)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        padding: '2px',
        gap: '2px',
      }}
    >
      <div style={{ padding: '0 4px', display: 'flex', alignItems: 'center', color: 'var(--text-muted)' }}>
        <Globe size={14} aria-hidden="true" />
      </div>
      <button
        type="button"
        onClick={() => setLanguage('es')}
        style={{
          border: 'none',
          backgroundColor: language === 'es' ? 'var(--primary)' : 'transparent',
          color: language === 'es' ? '#ffffff' : 'var(--text-muted)',
          padding: '4px 8px',
          borderRadius: '6px',
          fontSize: '0.75rem',
          fontWeight: 600,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          transition: 'all 0.15s ease',
        }}
        title="Español (ES)"
        aria-pressed={language === 'es'}
      >
        <span>🇪🇸</span>
        <span>ES</span>
      </button>
      <button
        type="button"
        onClick={() => setLanguage('en')}
        style={{
          border: 'none',
          backgroundColor: language === 'en' ? 'var(--primary)' : 'transparent',
          color: language === 'en' ? '#ffffff' : 'var(--text-muted)',
          padding: '4px 8px',
          borderRadius: '6px',
          fontSize: '0.75rem',
          fontWeight: 600,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          transition: 'all 0.15s ease',
        }}
        title="English (EN)"
        aria-pressed={language === 'en'}
      >
        <span>🇬🇧</span>
        <span>EN</span>
      </button>
    </div>
  );
};
