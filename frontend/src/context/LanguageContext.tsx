import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Language, LANGUAGES, Translations, translations } from '../i18n';

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: Translations;
}

const STORAGE_LANG_KEY = 'dataflow_app_language';

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<Language>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_LANG_KEY) as Language | null;
      if (saved && LANGUAGES.some((l) => l.code === saved)) {
        return saved;
      }
    } catch {
      // Fallback si localStorage no está disponible
    }
    return 'es';
  });

  const updateDocumentAttributes = (targetLang: Language) => {
    const isRtl = targetLang === 'ar' || targetLang === 'ur';
    document.documentElement.dir = isRtl ? 'rtl' : 'ltr';
    document.documentElement.lang = targetLang;
  };

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    try {
      localStorage.setItem(STORAGE_LANG_KEY, lang);
    } catch {
      // Silencioso
    }
    updateDocumentAttributes(lang);
  };

  useEffect(() => {
    updateDocumentAttributes(language);
  }, [language]);

  const value = {
    language,
    setLanguage,
    t: (translations[language] || translations['es']) as Translations,
  };

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
};

export const useLanguage = (): LanguageContextType => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage debe usarse dentro de un LanguageProvider');
  }
  return context;
};
