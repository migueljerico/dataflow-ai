import React, { useState, useEffect } from 'react';
import { Database, Sparkles, ShieldCheck, Key, Smartphone } from 'lucide-react';
import { ApiKeyModal } from './ApiKeyModal';
import { InstallPwaModal } from './InstallPwaModal';
import { getApiKey } from '../utils/security';

export const Header: React.FC = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [hasApiKey, setHasApiKey] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [isPwaModalOpen, setIsPwaModalOpen] = useState(false);
  const [isStandalone, setIsStandalone] = useState(false);
  const [isIOS, setIsIOS] = useState(false);

  useEffect(() => {
    const key = getApiKey();
    setHasApiKey(!!key);

    // Detectar si ya está en modo standalone (instalada)
    const isRunningStandalone = window.matchMedia('(display-mode: standalone)').matches || (navigator as any).standalone === true;
    setIsStandalone(isRunningStandalone);

    // Detectar iOS Safari
    const userAgent = window.navigator.userAgent.toLowerCase();
    const isIosDevice = /iphone|ipad|ipod/.test(userAgent);
    setIsIOS(isIosDevice);

    // Capturar evento de instalación en Android / Chrome / Edge
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    };
  }, []);

  const handleInstallClick = () => {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      deferredPrompt.userChoice.then((choiceResult: any) => {
        if (choiceResult.outcome === 'accepted') {
          setDeferredPrompt(null);
        }
      });
    } else {
      setIsPwaModalOpen(true);
    }
  };

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
          {!isStandalone && (
            <button
              onClick={handleInstallClick}
              className="btn btn-outline"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                fontSize: '0.8rem',
                fontWeight: 500,
                backgroundColor: 'rgba(14, 165, 233, 0.1)',
                borderColor: 'rgba(14, 165, 233, 0.35)',
                color: 'var(--primary)',
                borderRadius: '6px',
                cursor: 'pointer'
              }}
              title="Instala DataFlow AI en tu móvil o escritorio"
            >
              <Smartphone size={14} />
              <span>Instalar App</span>
            </button>
          )}

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

      <InstallPwaModal
        isOpen={isPwaModalOpen}
        onClose={() => setIsPwaModalOpen(false)}
        onInstallPrompt={deferredPrompt ? handleInstallClick : undefined}
        isInstallable={!!deferredPrompt}
        isIOS={isIOS}
      />
    </>
  );
};
