import React from 'react';
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { LanguageProvider, useLanguage } from './LanguageContext';
import { LanguageSelector } from '../components/LanguageSelector';

const TestComponent = () => {
  const { language, t } = useLanguage();
  return (
    <div>
      <span data-testid="current-lang">{language}</span>
      <span data-testid="title">{t.brand.title}</span>
      <span data-testid="step1">{t.stepper.step1}</span>
      <LanguageSelector />
    </div>
  );
};

describe('LanguageContext and LanguageSelector', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders default Spanish language and switches to English', () => {
    render(
      <LanguageProvider>
        <TestComponent />
      </LanguageProvider>
    );

    expect(screen.getByTestId('current-lang').textContent).toBe('es');
    expect(screen.getByTestId('step1').textContent).toBe('Subir Datos');

    // Cambiar a inglés
    const enButton = screen.getByRole('button', { name: /EN/i });
    act(() => {
      enButton.click();
    });

    expect(screen.getByTestId('current-lang').textContent).toBe('en');
    expect(screen.getByTestId('step1').textContent).toBe('Upload Data');
    expect(localStorage.getItem('dataflow_app_language')).toBe('en');
  });

  it('persists selected language across renders', () => {
    localStorage.setItem('dataflow_app_language', 'en');

    render(
      <LanguageProvider>
        <TestComponent />
      </LanguageProvider>
    );

    expect(screen.getByTestId('current-lang').textContent).toBe('en');
    expect(screen.getByTestId('step1').textContent).toBe('Upload Data');
  });
});
