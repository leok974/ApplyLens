import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { HealthBadge } from './HealthBadge';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('HealthBadge', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders OK state with green badge', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        divergence_pct: 0.011,
        status: 'ok',
        es_count: 10050,
        bq_count: 10000,
        divergence: 0.011,
        slo_met: true,
        message: 'Divergence: 1.10% (within SLO)',
      }),
    });

    render(<HealthBadge />);

    await waitFor(() => {
      expect(screen.getByText('Warehouse OK')).toBeInTheDocument();
    });

    const badge = screen.getByText('Warehouse OK').closest('div');
    expect(badge).toHaveClass('bg-green-100');
  });

  it('renders Degraded state with yellow badge', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        divergence_pct: 0.035,
        status: 'degraded',
        es_count: 10350,
        bq_count: 10000,
        divergence: 0.035,
        slo_met: false,
        message: 'Divergence: 3.50% (exceeds SLO)',
      }),
    });

    render(<HealthBadge />);

    await waitFor(() => {
      expect(screen.getByText('Degraded')).toBeInTheDocument();
    });

    const badge = screen.getByText('Degraded').closest('div');
    expect(badge).toHaveClass('bg-yellow-100');
  });

  it('renders Paused state with grey badge when warehouse disabled', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 412,
      json: async () => ({
        detail: 'Warehouse disabled',
      }),
    });

    render(<HealthBadge />);

    await waitFor(() => {
      expect(screen.getByText('Paused')).toBeInTheDocument();
    });

    const badge = screen.getByText('Paused').closest('div');
    expect(badge).toHaveClass('bg-gray-100');
  });

  it('renders Paused state when network error occurs', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'));

    render(<HealthBadge />);

    await waitFor(() => {
      expect(screen.getByText('Paused')).toBeInTheDocument();
    });
  });

  it('shows divergence percentage in tooltip for OK state', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        divergence_pct: 0.011,
        status: 'ok',
        es_count: 10050,
        bq_count: 10000,
        divergence: 0.011,
        slo_met: true,
        message: 'Divergence: 1.10% (within SLO)',
      }),
    });

    render(<HealthBadge />);

    await waitFor(() => {
      const badge = screen.getByText('Warehouse OK').closest('div');
      expect(badge).toHaveAttribute('title');
      expect(badge?.getAttribute('title')).toContain('1.1%');
    });
  });

  it('shows divergence percentage in badge label', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        divergence_pct: 1.5,
        status: 'ok',
        es_count: 10150,
        bq_count: 10000,
        divergence: 0.015,
        slo_met: true,
        message: 'Divergence: 1.50% (within SLO)',
      }),
    });

    render(<HealthBadge />);

    await waitFor(() => {
      expect(screen.getByText(/1\.5%/)).toBeInTheDocument();
    });
  });

  it('transitions from OK to Degraded when divergence increases', async () => {
    // First fetch: OK
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        divergence_pct: 0.011,
        status: 'ok',
        slo_met: true,
      }),
    });

    const { rerender } = render(<HealthBadge />);

    await waitFor(() => {
      expect(screen.getByText('Warehouse OK')).toBeInTheDocument();
    });

    // Second fetch: Degraded
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        divergence_pct: 0.035,
        status: 'degraded',
        slo_met: false,
      }),
    });

    // Force re-render to trigger new fetch
    rerender(<HealthBadge />);

    await waitFor(() => {
      expect(screen.getByText('Degraded')).toBeInTheDocument();
    });
  });

  it('shows loading state initially', () => {
    mockFetch.mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(
            () =>
              resolve({
                ok: true,
                status: 200,
                json: async () => ({ divergence_pct: 0.011, status: 'ok' }),
              }),
            100
          )
        )
    );

    render(<HealthBadge />);

    expect(screen.getByText('Checking...')).toBeInTheDocument();
  });
});
