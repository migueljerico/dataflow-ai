import React, { useState, useEffect } from 'react';
import { Database, Sparkles, ShieldCheck, Key, Smartphone, Activity } from 'lucide-react';
import { ApiKeyModal } from './ApiKeyModal';
import { InstallPwaModal } from './InstallPwaModal';
import { CacheObservabilityModal } from './CacheObservabilityModal';
import { LanguageSelector } from './LanguageSelector';
import { useLanguage } from '../context/LanguageContext';
import { getApiKey } from '../utils/security';

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

export const Header: React.FC = () => {
  const { t } = useLanguage();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [hasApiKey, setHasApiKey] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [isPwaModalOpen, setIsPwaModalOpen] = useState(false);
  const [isStandalone, setIsStandalone] = useState(false);
  const [isIOS, setIsIOS] = useState(false);
  const [isCacheModalOpen, setIsCacheModalOpen] = useState(false);

  useEffect(() => {
    const key = getApiKey();
    setHasApiKey(!!key);

    // Detectar si ya está en modo standalone (instalada)
    const isRunningStandalone = window.matchMedia('(display-mode: standalone)').matches || (navigator as unknown as { standalone?: boolean }).standalone === true;
    setIsStandalone(isRunningStandalone);

    // Detectar iOS Safari
    const userAgent = window.navigator.userAgent.toLowerCase();
    const isIosDevice = /iphone|ipad|ipod/.test(userAgent);
    setIsIOS(isIosDevice);

    // Capturar evento de instalación en Android / Chrome / Edge
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    };
  }, []);

  const handleInstallClick = () => {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      deferredPrompt.userChoice.then((choiceResult) => {
        if ((choiceResult as { outcome: string }).outcome === 'accepted') {
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
            <Database size={22} aria-hidden="true" />
          </div>
          <div>
            <h1 className="brand-title">{t.brand.title}</h1>
            <p className="brand-tagline">{t.brand.tagline}</p>
          </div>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <LanguageSelector />

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
              title={t.header.installTitle}
            >
              <Smartphone size={14} aria-hidden="true" />
              <span>{t.header.installApp}</span>
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
            title={t.header.apiKeyTitle}
          >
            <Key size={14} aria-hidden="true" style={{ color: hasApiKey ? 'var(--accent-emerald)' : 'var(--primary)' }} />
            {hasApiKey ? (
              <span><strong style={{ color: 'var(--accent-emerald)' }}>{t.header.apiKeyActive}</strong></span>
            ) : (
              <span>{t.header.apiKey}</span>
            )}
          </button>

          <button
            onClick={() => setIsCacheModalOpen(true)}
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
            data-testid="header-cache-observability-btn"
            title={t.header?.cacheObservabilityTitle || 'Observabilidad de la caché distribuida (L1 Memoria + L2 Redis)'}
          >
            <Activity size={14} aria-hidden="true" style={{ color: 'var(--primary)' }} />
            <span>{t.header?.cacheObservability || 'Caché IA'}</span>
          </button>

          <span className="badge badge-emerald hide-on-mobile" title={t.header.gdprTitle}>
            <ShieldCheck size={13} /> {t.header.gdprPrivacy}
          </span>
          <span className="badge badge-primary hide-on-mobile">
            <Sparkles size={12} /> {t.header.etlCopilot}
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

      <CacheObservabilityModal
        isOpen={isCacheModalOpen}
        onClose={() => setIsCacheModalOpen(false)}
      />
    </>
  );
};
