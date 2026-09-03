import React, { useCallback, useState } from 'react';
import { Activity, AlertTriangle, FlaskConical, Loader2, ShieldCheck } from 'lucide-react';
import { DriftSimulationResult, DriftStatus, TransformationStep } from '../types';
import { api } from '../services/api';
import { useLanguage } from '../context/LanguageContext';

interface Props {
  datasetId?: string | null;
  steps: TransformationStep[];
}

const statusBadge: Record<DriftStatus, string> = {
  stable: 'badge badge-emerald',
  moderate: 'badge badge-amber',
  critical: 'badge badge-rose',
};

function formatPct(value: number | undefined | null): string {
  if (value === undefined || value === null || Number.isNaN(value)) return '—';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

/**
 * Simulación interactiva de transformaciones hipotéticas (v1.16.0).
 * Calcula en tiempo real el impacto de los pasos actualmente aprobados sobre los
 * percentiles de drift ANTES de la aprobación formal. Es puramente hipotética:
 * no modifica el dataset ni crea ejecuciones (gobernanza estricta).
 */
export const DriftSimulator: React.FC<Props> = ({ datasetId, steps }) => {
  const { t } = useLanguage();
  const sim = t.driftSim;
  const [result, setResult] = useState<DriftSimulationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const simulableSteps = steps.filter((s) => s.status !== 'rejected');

  const runSimulation = useCallback(async () => {
    if (!datasetId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.simulateDrift(datasetId, simulableSteps);
      setResult(res);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [datasetId, simulableSteps]);

  if (!datasetId) return null;

  const drift = result?.drift_report;

  return (
    <div
      data-testid="drift-simulator"
      style={{
        backgroundColor: 'var(--bg-input)',
        border: '1px solid var(--border-color)',
        borderRadius: '10px',
        padding: '16px 20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
        <div>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FlaskConical size={18} className="text-primary" />
            {sim?.title || 'Simulador de Drift (Hipotético)'}
          </h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: '4px 0 0 0' }}>
            {sim?.subtitle ||
              'Anticipa el impacto de los pasos aprobados sobre los percentiles antes de la aprobación formal. No modifica el dataset.'}
          </p>
        </div>
        <button
          type="button"
          className="btn btn-outline"
          onClick={runSimulation}
          disabled={loading || simulableSteps.length === 0}
          data-testid="simulate-drift-btn"
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          {loading ? <Loader2 size={16} className="spin" /> : <Activity size={16} />}
          {loading
            ? sim?.simulating || 'Simulando…'
            : `${sim?.simulateBtn || 'Simular'} (${simulableSteps.length})`}
        </button>
      </div>

      {error && (
        <div className="badge badge-rose" style={{ padding: '8px 12px', display: 'flex', gap: '6px', alignItems: 'center' }}>
          <AlertTriangle size={14} /> {error}
        </div>
      )}

      {result && drift && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center', fontSize: '0.78rem' }}>
            <span className={statusBadge[drift.overall_drift_status]} data-testid="sim-overall-status">
              {sim?.overall || 'Estado global'}: {drift.overall_drift_status.toUpperCase()}
            </span>
            <span className="badge badge-slate" style={{ backgroundColor: 'var(--bg-main)' }}>
              {sim?.appliedSteps || 'Pasos aplicados'}: {result.applied_steps}/{result.hypothetical_steps}
            </span>
            <span className="badge badge-slate" style={{ backgroundColor: 'var(--bg-main)' }}>
              {sim?.elapsed || 'Tiempo'}: {result.elapsed_ms.toFixed(0)} ms
            </span>
            <span className="badge badge-slate" style={{ backgroundColor: 'var(--bg-main)' }}>
              {sim?.rows || 'Filas'}: {result.rows_before} → {result.rows_after}
            </span>
          </div>

          {result.step_outcomes.some((o) => !o.applied) && (
            <div style={{ fontSize: '0.75rem', color: 'var(--accent-amber, #f59e0b)' }}>
              {result.step_outcomes
                .filter((o) => !o.applied)
                .map((o) => (
                  <div key={o.step_id} data-testid={`sim-step-error-${o.step_id}`}>
                    ⚠ {o.step_id} ({o.operation}): {o.error}
                  </div>
                ))}
            </div>
          )}

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem' }} data-testid="sim-columns-table">
              <thead>
                <tr style={{ textAlign: 'left', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '6px 8px' }}>{sim?.colName || 'Columna'}</th>
                  <th style={{ padding: '6px 8px' }}>{sim?.colStatus || 'Estado'}</th>
                  <th style={{ padding: '6px 8px' }}>P50 {sim?.before || 'antes'} → {sim?.after || 'después'}</th>
                  <th style={{ padding: '6px 8px' }}>P05 Δ</th>
                  <th style={{ padding: '6px 8px' }}>P95 Δ</th>
                  <th style={{ padding: '6px 8px' }}>{sim?.maxShift || 'Δ máx'}</th>
                </tr>
              </thead>
              <tbody>
                {drift.columns.map((col) => (
                  <tr key={col.column_name} style={{ borderTop: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '6px 8px', fontFamily: 'var(--font-mono)' }}>{col.column_name}</td>
                    <td style={{ padding: '6px 8px' }}>
                      <span className={statusBadge[col.drift_status]}>{col.drift_status}</span>
                    </td>
                    <td style={{ padding: '6px 8px' }}>
                      {col.raw_percentiles ? col.raw_percentiles.p50.toLocaleString() : '—'} →{' '}
                      <strong>{col.clean_percentiles.p50.toLocaleString()}</strong>
                    </td>
                    <td style={{ padding: '6px 8px' }}>{formatPct(col.shift?.p05_shift_pct)}</td>
                    <td style={{ padding: '6px 8px' }}>{formatPct(col.shift?.p95_shift_pct)}</td>
                    <td style={{ padding: '6px 8px' }}>{formatPct(col.shift?.max_shift_pct)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div
            style={{
              display: 'flex',
              gap: '6px',
              alignItems: 'flex-start',
              fontSize: '0.72rem',
              color: 'var(--text-muted)',
              fontStyle: 'italic',
            }}
            data-testid="sim-governance-note"
          >
            <ShieldCheck size={14} style={{ flexShrink: 0, marginTop: '1px' }} />
            <span>{result.governance_note}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default DriftSimulator;
