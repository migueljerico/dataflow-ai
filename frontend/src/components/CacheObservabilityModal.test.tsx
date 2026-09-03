import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import React from 'react';
import { CacheObservabilityModal } from './CacheObservabilityModal';
import { api } from '../services/api';
import { LanguageProvider } from '../context/LanguageContext';
import { CacheStats } from '../types';

vi.mock('../services/api', () => ({
  api: {
    getCacheStats: vi.fn(),
  },
}));

const mockStats: CacheStats = {
  backend: 'redis',
  distributed: true,
  redis_available: true,
  redis_hits: 5,
  redis_errors: 0,
  hits: 15,
  l1_hits: 10,
  l2_hits: 5,
  misses: 5,
  total_requests: 20,
  hit_rate_pct: 75.0,
  l1_hit_rate_pct: 50.0,
  l2_hit_rate_pct: 25.0,
  cached_entries: 42,
  saved_tokens: 15000,
  saved_cost_usd: 0.035,
};

const renderWithProvider = (ui: React.ReactElement) => {
  return render(<LanguageProvider>{ui}</LanguageProvider>);
};

describe('CacheObservabilityModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getCacheStats).mockResolvedValue(mockStats);
  });

  it('renders nothing when isOpen is false', () => {
    const { container } = renderWithProvider(
      <CacheObservabilityModal isOpen={false} onClose={() => {}} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('fetches and renders cache statistics when opened', async () => {
    renderWithProvider(<CacheObservabilityModal isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByTestId('cache-observability-modal')).toBeInTheDocument();
    });

    expect(screen.getByTestId('kpi-hit-rate')).toHaveTextContent('75.0%');
    expect(screen.getByTestId('kpi-l1-hits')).toHaveTextContent('10');
    expect(screen.getByTestId('kpi-l2-hits')).toHaveTextContent('5');
    expect(screen.getByTestId('kpi-misses')).toHaveTextContent('5');
    expect(screen.getByTestId('kpi-saved-tokens')).toHaveTextContent(mockStats.saved_tokens.toLocaleString());
    expect(screen.getByTestId('kpi-saved-cost')).toHaveTextContent('$0.035000');

    // Estado del backend
    const badge = screen.getByTestId('cache-backend-badge');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent(/Redis L2/i);
  });

  it('triggers refresh when clicking the refresh button', async () => {
    renderWithProvider(<CacheObservabilityModal isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByTestId('cache-refresh-btn')).toBeInTheDocument();
    });

    const refreshBtn = screen.getByTestId('cache-refresh-btn');
    await waitFor(() => {
      fireEvent.click(refreshBtn);
    });

    expect(api.getCacheStats).toHaveBeenCalledTimes(2);
  });

  it('calls onClose when close button is clicked or Escape key pressed', async () => {
    const onClose = vi.fn();
    renderWithProvider(<CacheObservabilityModal isOpen={true} onClose={onClose} />);

    await waitFor(() => {
      expect(screen.getByTestId('cache-modal-close-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('cache-modal-close-btn'));
    expect(onClose).toHaveBeenCalledTimes(1);

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});
