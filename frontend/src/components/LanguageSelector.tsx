import React from 'react';
import { useLanguage } from '../context/LanguageContext';
import { Globe } from 'lucide-react';

const SpainFlag: React.FC = () => (
  <svg
    width="16"
    height="12"
    viewBox="0 0 640 480"
    aria-hidden="true"
    style={{
      borderRadius: '2px',
      display: 'inline-block',
      verticalAlign: 'middle',
      flexShrink: 0,
      boxShadow: '0 0 1px rgba(0,0,0,0.35)',
    }}
  >
    <path fill="#c60b1e" d="M0 0h640v480H0z" />
    <path fill="#ffc400" d="M0 120h640v240H0z" />
  </svg>
);

const UkFlag: React.FC = () => (
  <svg
    width="16"
    height="12"
    viewBox="0 0 60 30"
    aria-hidden="true"
    style={{
      borderRadius: '2px',
      display: 'inline-block',
      verticalAlign: 'middle',
      flexShrink: 0,
      boxShadow: '0 0 1px rgba(0,0,0,0.35)',
    }}
  >
    <path fill="#012169" d="M0 0h60v30H0z" />
    <path stroke="#ffffff" strokeWidth="6" d="M0 0l60 30M60 0L0 30" />
    <path stroke="#c8102e" strokeWidth="4" d="M0 0l60 30M60 0L0 30" />
    <path stroke="#ffffff" strokeWidth="10" d="M30 0v30M0 15h60" />
    <path stroke="#c8102e" strokeWidth="6" d="M30 0v30M0 15h60" />
  </svg>
);

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
          gap: '6px',
          transition: 'all 0.15s ease',
        }}
        title="Español (ES)"
        aria-pressed={language === 'es'}
      >
        <SpainFlag />
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
          gap: '6px',
          transition: 'all 0.15s ease',
        }}
        title="English (EN)"
        aria-pressed={language === 'en'}
      >
        <UkFlag />
        <span>EN</span>
      </button>
    </div>
  );
};

