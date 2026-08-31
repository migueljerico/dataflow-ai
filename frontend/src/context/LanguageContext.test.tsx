import React from 'react';
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { LanguageProvider, useLanguage } from './LanguageContext';
import { LanguageSelector } from '../components/LanguageSelector';

const TestConsumer = () => {
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

  it('renders default Spanish language and opens listbox with 13 languages', () => {
    render(
      <LanguageProvider>
        <TestConsumer />
      </LanguageProvider>
    );

    expect(screen.getByTestId('current-lang').textContent).toBe('es');
    expect(screen.getByTestId('step1').textContent).toBe('Subir Datos');

    const button = screen.getByRole('button', { name: /select language/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveTextContent('ES');

    // Abrir desplegable
    fireEvent.click(button);
    const listbox = screen.getByRole('listbox');
    expect(listbox).toBeInTheDocument();

    const options = screen.getAllByRole('option');
    expect(options).toHaveLength(13);
  });

  it('switches to English and persists in localStorage', () => {
    render(
      <LanguageProvider>
        <TestConsumer />
      </LanguageProvider>
    );

    const button = screen.getByRole('button', { name: /select language/i });
    fireEvent.click(button);

    const enOption = screen.getAllByRole('option').find((opt) => opt.textContent?.includes('English'));
    expect(enOption).toBeDefined();

    act(() => {
      fireEvent.click(enOption!);
    });

    expect(screen.getByTestId('current-lang').textContent).toBe('en');
    expect(screen.getByTestId('step1').textContent).toBe('Upload Data');
    expect(localStorage.getItem('dataflow_app_language')).toBe('en');
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('persists selected language across renders', () => {
    localStorage.setItem('dataflow_app_language', 'en');

    render(
      <LanguageProvider>
        <TestConsumer />
      </LanguageProvider>
    );

    expect(screen.getByTestId('current-lang').textContent).toBe('en');
    expect(screen.getByTestId('step1').textContent).toBe('Upload Data');
  });

  it('closes dropdown on Escape key and on clicking outside', () => {
    render(
      <LanguageProvider>
        <div>
          <button data-testid="outside-btn">Outside</button>
          <LanguageSelector />
        </div>
      </LanguageProvider>
    );

    const button = screen.getByRole('button', { name: /select language/i });
    fireEvent.click(button);
    expect(screen.getByRole('listbox')).toBeInTheDocument();

    // Escape
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();

    // Click outside
    fireEvent.click(button);
    expect(screen.getByRole('listbox')).toBeInTheDocument();
    fireEvent.mouseDown(screen.getByTestId('outside-btn'));
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('selects option via keyboard navigation (Enter and Space)', () => {
    render(
      <LanguageProvider>
        <TestConsumer />
      </LanguageProvider>
    );

    const button = screen.getByRole('button', { name: /select language/i });
    fireEvent.click(button);

    const options = screen.getAllByRole('option');
    const enOption = options.find((opt) => opt.textContent?.includes('English'));
    expect(enOption).toBeDefined();

    fireEvent.keyDown(enOption!, { key: 'Enter' });
    expect(screen.getByTestId('current-lang').textContent).toBe('en');

    // Reopen and select French with Space
    fireEvent.click(button);
    const frOption = screen.getAllByRole('option').find((opt) => opt.textContent?.includes('Français'));
    expect(frOption).toBeDefined();
    fireEvent.keyDown(frOption!, { key: ' ' });
    expect(screen.getByTestId('current-lang').textContent).toBe('fr');
  });
});
