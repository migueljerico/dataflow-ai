import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ScheduledReportsPanel } from './ScheduledReportsPanel';
import { LanguageProvider } from '../context/LanguageContext';
import { api } from '../services/api';
import { ReportSchedule, ReportScheduleListResponse } from '../types';

const mockSchedule: ReportSchedule = {
  schedule_id: 'SCHED-abc123',
  run_id: 'RUN-001',
  dataset_id: 'DS-001',
  report_format: 'pdf',
  interval_minutes: 30,
  webhook_url: 'https://hooks.ejemplo.com/dataflow',
  trigger: 'critical_drift',
  lang: 'es',
  enabled: true,
  created_at: '2026-09-03T12:00:00Z',
  next_run_at: '2026-09-03T12:30:00Z',
  last_executed_at: '2026-09-03T12:05:00Z',
  last_status: 'ok',
  last_drift_status: 'stable',
  last_error: null,
  executions_count: 2,
  deliveries_count: 1,
  last_report_key: 'report_SCHED-abc123_20260903.pdf',
};

const otherRunSchedule: ReportSchedule = { ...mockSchedule, schedule_id: 'SCHED-other', run_id: 'RUN-999' };

function mockList(schedules: ReportSchedule[]) {
  return vi.spyOn(api, 'listReportSchedules').mockResolvedValue({
    schedules,
    total: schedules.length,
  } as ReportScheduleListResponse);
}

describe('ScheduledReportsPanel Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('lista solo las programaciones del run actual y expone exportaciones directas', async () => {
    mockList([mockSchedule, otherRunSchedule]);

    render(
      <LanguageProvider>
        <ScheduledReportsPanel runId="RUN-001" />
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('schedule-row-SCHED-abc123')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('schedule-row-SCHED-other')).not.toBeInTheDocument();

    const pdfBtn = screen.getByTestId('export-pdf-btn');
    expect(pdfBtn.getAttribute('href')).toContain('/api/v1/reports/RUN-001/pdf');
    const htmlBtn = screen.getByTestId('export-html-btn');
    expect(htmlBtn.getAttribute('href')).toContain('/api/v1/reports/RUN-001/html');

    // Estado y contadores de la programación
    const row = screen.getByTestId('schedule-row-SCHED-abc123');
    expect(row.textContent).toContain('PDF');
    expect(row.textContent).toContain('ok');
    // Último reporte disponible (hay last_report_key)
    expect(screen.getByTestId('last-report-SCHED-abc123').getAttribute('href')).toContain(
      '/api/v1/reports/schedules/SCHED-abc123/last-report'
    );
  });

  it('crea una programación con formato, intervalo, webhook y trigger', async () => {
    mockList([]);
    const createSpy = vi.spyOn(api, 'createReportSchedule').mockResolvedValue(mockSchedule);

    render(
      <LanguageProvider>
        <ScheduledReportsPanel runId="RUN-001" />
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('no-schedules')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId('schedule-format'), { target: { value: 'html' } });
    fireEvent.change(screen.getByTestId('schedule-interval'), { target: { value: '15' } });
    fireEvent.change(screen.getByTestId('schedule-trigger'), { target: { value: 'always' } });
    fireEvent.change(screen.getByTestId('schedule-webhook'), {
      target: { value: 'https://hooks.ejemplo.com/nuevo' },
    });
    fireEvent.click(screen.getByTestId('create-schedule-btn'));

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith({
        run_id: 'RUN-001',
        report_format: 'html',
        interval_minutes: 15,
        webhook_url: 'https://hooks.ejemplo.com/nuevo',
        trigger: 'always',
        lang: 'es',
      });
    });
  });

  it('ejecuta ahora y elimina una programación', async () => {
    mockList([mockSchedule]);
    const runNowSpy = vi.spyOn(api, 'runReportScheduleNow').mockResolvedValue({
      schedule_id: 'SCHED-abc123',
      executed_at: '2026-09-03T13:00:00Z',
      report_format: 'pdf',
      drift_status: 'critical',
      report_key: 'report_x.pdf',
      webhook: { delivered: true, reason: 'delivered', http_status: 200, error: null },
      error: null,
    });
    const deleteSpy = vi.spyOn(api, 'deleteReportSchedule').mockResolvedValue({ deleted: true });

    render(
      <LanguageProvider>
        <ScheduledReportsPanel runId="RUN-001" />
      </LanguageProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('schedule-row-SCHED-abc123')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('run-now-SCHED-abc123'));
    await waitFor(() => expect(runNowSpy).toHaveBeenCalledWith('SCHED-abc123'));

    fireEvent.click(screen.getByTestId('delete-SCHED-abc123'));
    await waitFor(() => expect(deleteSpy).toHaveBeenCalledWith('SCHED-abc123'));
  });

  it('muestra el error anti-SSRF del backend al crear con webhook inválido', async () => {
    mockList([]);
    vi.spyOn(api, 'createReportSchedule').mockRejectedValue(
      new Error('Acceso denegado por seguridad: el destino (192.168.1.1) es una dirección IP privada o restringida.')
    );

    render(
      <LanguageProvider>
        <ScheduledReportsPanel runId="RUN-001" />
      </LanguageProvider>
    );

    fireEvent.change(screen.getByTestId('schedule-webhook'), { target: { value: 'http://192.168.1.1/hook' } });
    fireEvent.click(screen.getByTestId('create-schedule-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('schedule-error').textContent).toContain('IP privada');
    });
  });
});
