import React, { useCallback, useEffect, useState } from 'react';
import { Bell, CalendarClock, Download, FileText, Loader2, Play, Trash2, Webhook } from 'lucide-react';
import { ReportFormat, ReportSchedule, WebhookTrigger } from '../types';
import { api } from '../services/api';
import { useLanguage } from '../context/LanguageContext';

interface Props {
  runId: string;
}

/**
 * Exportación programada de reportes ejecutivos (v1.16.0).
 * El usuario decide formato, intervalo y webhook; el backend regenera el reporte
 * de forma desatendida y notifica según el trigger configurado (drift crítico o siempre).
 */
export const ScheduledReportsPanel: React.FC<Props> = ({ runId }) => {
  const { t, language } = useLanguage();
  const tr = t.scheduledReports;
  const [schedules, setSchedules] = useState<ReportSchedule[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [format, setFormat] = useState<ReportFormat>('pdf');
  const [intervalMinutes, setIntervalMinutes] = useState<number>(60);
  const [webhookUrl, setWebhookUrl] = useState<string>('');
  const [trigger, setTrigger] = useState<WebhookTrigger>('critical_drift');

  const reportLang = language === 'en' ? 'en' : 'es';

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.listReportSchedules();
      setSchedules(res.schedules.filter((s) => s.run_id === runId));
      setError(null);
    } catch {
      // Sin schedules disponibles (p. ej. backend reiniciado): estado vacío, no es un error fatal
      setSchedules([]);
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleCreate = async () => {
    setCreating(true);
    setError(null);
    try {
      await api.createReportSchedule({
        run_id: runId,
        report_format: format,
        interval_minutes: intervalMinutes,
        webhook_url: webhookUrl.trim() || null,
        trigger,
        lang: reportLang,
      });
      setWebhookUrl('');
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setCreating(false);
    }
  };

  const handleRunNow = async (scheduleId: string) => {
    setRunningId(scheduleId);
    setError(null);
    try {
      await api.runReportScheduleNow(scheduleId);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRunningId(null);
    }
  };

  const handleDelete = async (scheduleId: string) => {
    setError(null);
    try {
      await api.deleteReportSchedule(scheduleId);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div
      data-testid="scheduled-reports-panel"
      style={{
        backgroundColor: 'var(--bg-input)',
        border: '1px solid var(--border-color)',
        borderRadius: '10px',
        padding: '16px 20px',
        marginBottom: '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
        <div>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CalendarClock size={18} className="text-primary" />
            {tr?.title || 'Reportes Ejecutivos & Exportación Programada'}
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: '4px 0 0 0' }}>
            {tr?.subtitle ||
              'Descarga el reporte ejecutivo en PDF/HTML o programa su regeneración desatendida con notificación webhook por drift crítico.'}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <a
            href={api.getExecutiveReportPdfUrl(runId, reportLang)}
            className="btn btn-primary"
            data-testid="export-pdf-btn"
            style={{ textDecoration: 'none', padding: '8px 14px', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem' }}
          >
            <FileText size={15} /> {tr?.exportPdf || 'PDF Ejecutivo'}
          </a>
          <a
            href={api.getExecutiveReportHtmlUrl(runId, reportLang)}
            className="btn btn-outline"
            data-testid="export-html-btn"
            style={{ textDecoration: 'none', padding: '8px 14px', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem' }}
          >
            <Download size={15} /> {tr?.exportHtml || 'HTML Ejecutivo'}
          </a>
        </div>
      </div>

      {/* Alta de programación */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
          gap: '10px',
          alignItems: 'end',
        }}
      >
        <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {tr?.format || 'Formato'}
          <select
            value={format}
            onChange={(e) => setFormat(e.target.value as ReportFormat)}
            data-testid="schedule-format"
            className="input-dark"
            style={{ padding: '8px', borderRadius: '6px', backgroundColor: 'var(--bg-main)', color: 'var(--text-color)', border: '1px solid var(--border-color)' }}
          >
            <option value="pdf">PDF</option>
            <option value="html">HTML</option>
          </select>
        </label>
        <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {tr?.interval || 'Intervalo (min)'}
          <input
            type="number"
            min={5}
            max={1440}
            value={intervalMinutes}
            onChange={(e) => setIntervalMinutes(Number(e.target.value))}
            data-testid="schedule-interval"
            style={{ padding: '8px', borderRadius: '6px', backgroundColor: 'var(--bg-main)', color: 'var(--text-color)', border: '1px solid var(--border-color)' }}
          />
        </label>
        <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {tr?.trigger || 'Notificar webhook'}
          <select
            value={trigger}
            onChange={(e) => setTrigger(e.target.value as WebhookTrigger)}
            data-testid="schedule-trigger"
            style={{ padding: '8px', borderRadius: '6px', backgroundColor: 'var(--bg-main)', color: 'var(--text-color)', border: '1px solid var(--border-color)' }}
          >
            <option value="critical_drift">{tr?.triggerCritical || 'Solo con drift crítico'}</option>
            <option value="always">{tr?.triggerAlways || 'En cada regeneración'}</option>
          </select>
        </label>
        <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '4px', gridColumn: 'span 2' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Webhook size={12} /> {tr?.webhookUrl || 'Webhook URL (opcional, validada anti-SSRF)'}
          </span>
          <input
            type="url"
            value={webhookUrl}
            onChange={(e) => setWebhookUrl(e.target.value)}
            placeholder="https://hooks.ejemplo.com/dataflow"
            data-testid="schedule-webhook"
            style={{ padding: '8px', borderRadius: '6px', backgroundColor: 'var(--bg-main)', color: 'var(--text-color)', border: '1px solid var(--border-color)' }}
          />
        </label>
        <button
          type="button"
          className="btn btn-success"
          onClick={handleCreate}
          disabled={creating || intervalMinutes < 5 || intervalMinutes > 1440}
          data-testid="create-schedule-btn"
          style={{ padding: '9px 14px', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem' }}
        >
          {creating ? <Loader2 size={15} className="spin" /> : <Bell size={15} />}
          {tr?.createBtn || 'Programar exportación'}
        </button>
      </div>

      {error && (
        <div className="badge badge-rose" data-testid="schedule-error" style={{ padding: '8px 12px', whiteSpace: 'normal' }}>
          {error}
        </div>
      )}

      {/* Listado de programaciones */}
      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          <Loader2 size={14} className="spin" /> {tr?.loading || 'Cargando programaciones…'}
        </div>
      ) : schedules.length === 0 ? (
        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }} data-testid="no-schedules">
          {tr?.noSchedules || 'Sin exportaciones programadas para esta ejecución.'}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {schedules.map((s) => (
            <div
              key={s.schedule_id}
              data-testid={`schedule-row-${s.schedule_id}`}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                gap: '10px',
                flexWrap: 'wrap',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                padding: '10px 12px',
                fontSize: '0.78rem',
              }}
            >
              <div style={{ display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' }}>
                <span className="badge badge-emerald">{s.report_format.toUpperCase()}</span>
                <span style={{ fontFamily: 'var(--font-mono)' }}>{s.schedule_id}</span>
                <span style={{ color: 'var(--text-muted)' }}>
                  {tr?.every || 'cada'} {s.interval_minutes} min · {s.trigger === 'critical_drift'
                    ? tr?.triggerCritical || 'Solo con drift crítico'
                    : tr?.triggerAlways || 'En cada regeneración'}
                </span>
                {s.last_status && (
                  <span className={s.last_status === 'ok' ? 'badge badge-emerald' : 'badge badge-amber'}>
                    {s.last_status}
                    {s.last_drift_status ? ` · drift: ${s.last_drift_status}` : ''}
                  </span>
                )}
                <span style={{ color: 'var(--text-muted)' }}>
                  {tr?.executions || 'Ejecuciones'}: {s.executions_count} · {tr?.deliveries || 'Webhooks'}: {s.deliveries_count}
                </span>
              </div>
              <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => handleRunNow(s.schedule_id)}
                  disabled={runningId === s.schedule_id}
                  data-testid={`run-now-${s.schedule_id}`}
                  style={{ padding: '5px 10px', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                >
                  {runningId === s.schedule_id ? <Loader2 size={12} className="spin" /> : <Play size={12} />}
                  {tr?.runNow || 'Ejecutar ahora'}
                </button>
                {s.last_report_key && (
                  <a
                    href={api.getScheduledLastReportUrl(s.schedule_id)}
                    className="btn btn-outline"
                    data-testid={`last-report-${s.schedule_id}`}
                    style={{ padding: '5px 10px', fontSize: '0.72rem', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '4px' }}
                  >
                    <Download size={12} /> {tr?.lastReport || 'Último reporte'}
                  </a>
                )}
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => handleDelete(s.schedule_id)}
                  data-testid={`delete-${s.schedule_id}`}
                  style={{ padding: '5px 10px', fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '4px', borderColor: 'var(--accent-rose, #f43f5e)', color: 'var(--accent-rose, #f43f5e)' }}
                >
                  <Trash2 size={12} /> {tr?.delete || 'Eliminar'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ScheduledReportsPanel;
