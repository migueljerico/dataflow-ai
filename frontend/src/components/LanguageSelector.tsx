import React, { useState, useRef, useEffect } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { LANGUAGES, type Language } from '../i18n';
import FlagIcon from './FlagIcon';

export const LanguageSelector: React.FC = () => {
  const { language, setLanguage } = useLanguage();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const currentOption = LANGUAGES.find((l) => l.code === language) || LANGUAGES[0];

  // Cerrar al hacer clic fuera o al pulsar Esc
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  const handleSelect = (code: Language) => {
    setLanguage(code);
    setIsOpen(false);
  };

  return (
    <div
      ref={containerRef}
      style={{ position: 'relative', display: 'inline-block' }}
    >
      <button
        type="button"
        className="btn btn-outline"
        onClick={() => setIsOpen(!isOpen)}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label="Select language"
        title={`Idioma: ${currentOption.nativeName} (${currentOption.code.toUpperCase()})`}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '5px 10px',
          fontSize: '0.8rem',
          fontWeight: 600,
          backgroundColor: 'var(--bg-input)',
          borderColor: 'var(--border-color)',
          color: 'var(--text-main)',
          borderRadius: '6px',
          cursor: 'pointer',
          transition: 'all 0.15s ease',
        }}
      >
        <FlagIcon code={currentOption.code} size={15} />
        <span>{currentOption.code.toUpperCase()}</span>
        <span style={{ fontSize: '0.65rem', opacity: 0.7, marginLeft: '2px' }}>▼</span>
      </button>

      {isOpen && (
        <div
          role="listbox"
          aria-label="Languages"
          style={{
            position: 'absolute',
            right: 0,
            top: '100%',
            marginTop: '4px',
            backgroundColor: 'var(--bg-card, #1e293b)',
            border: '1px solid var(--border-color, #334155)',
            borderRadius: '8px',
            boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.4)',
            zIndex: 1000,
            minWidth: '180px',
            maxHeight: '320px',
            overflowY: 'auto',
            padding: '4px',
          }}
        >
          {LANGUAGES.map((option) => {
            const isSelected = option.code === language;
            return (
              <div
                key={option.code}
                role="option"
                aria-selected={isSelected}
                tabIndex={0}
                onClick={() => handleSelect(option.code)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleSelect(option.code);
                  }
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '7px 10px',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.82rem',
                  backgroundColor: isSelected ? 'var(--primary, #0ea5e9)' : 'transparent',
                  color: isSelected ? '#ffffff' : 'var(--text-main, #f8fafc)',
                  transition: 'background-color 0.15s ease',
                  fontWeight: isSelected ? 600 : 400,
                }}
              >
                <FlagIcon code={option.code} size={15} />
                <span style={{ flex: 1, whiteSpace: 'nowrap' }}>{option.nativeName}</span>
                <span
                  style={{
                    fontSize: '0.75rem',
                    opacity: isSelected ? 0.9 : 0.6,
                    fontFamily: 'monospace',
                  }}
                >
                  {option.code.toUpperCase()}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default LanguageSelector;
