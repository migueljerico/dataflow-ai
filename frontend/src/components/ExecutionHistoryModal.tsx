import React, { useState, useEffect, useCallback } from 'react';
import {
  History,
  X,
  ArrowRight,
  TrendingUp,
  Download,
  Database,
  FileCode,
  CheckCircle2,
  RefreshCw,
  GitCompare,
  ShieldCheck,
  Calendar,
} from 'lucide-react';
import { api } from '../services/api';
import { ExecutionSummaryItem, QualityComparisonReport } from '../types';
import { useLanguage } from '../context/LanguageContext';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  currentRunId?: string;
  datasetId?: string;
}

export const ExecutionHistoryModal: React.FC<Props> = ({
  isOpen,
  onClose,
  currentRunId,
  datasetId,
}) => {
  const { t } = useLanguage();
  const [runs, setRuns] = useState<ExecutionSummaryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Selección para comparación
  const [selectedRunA, setSelectedRunA] = useState<string | null>(null);
  const [selectedRunB, setSelectedRunB] = useState<string | null>(null);
  const [comparison, setComparison] = useState<QualityComparisonReport | null>(null);
  const [comparing, setComparing] = useState<boolean>(false);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getRunsHistory(datasetId);
      setRuns(data);
      if (data.length >= 2) {
        setSelectedRunA(data[1].run_id);
        setSelectedRunB(data[0].run_id);
      } else if (data.length === 1) {
        setSelectedRunA(data[0].run_id);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al cargar el historial de ejecuciones');
    } finally {
      setLoading(false);
    }
  }, [datasetId]);

  useEffect(() => {
    if (isOpen) {
      fetchHistory();
    } else {
      setComparison(null);
    }
  }, [isOpen, fetchHistory]);

  // Manejo de la tecla Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const handleCompare = async () => {
    if (!selectedRunA || !selectedRunB) return;
    setComparing(true);
    try {
      const comp = await api.compareRuns(selectedRunA, selectedRunB);
      setComparison(comp);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al comparar versiones');
    } finally {
      setComparing(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="modal-backdrop"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        padding: '16px',
        backdropFilter: 'blur(4px)',
      }}
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="history-modal-title"
        className="card"
        style={{
          width: '100%',
          maxWidth: '920px',
          maxHeight: '90vh',
          overflowY: 'auto',
          margin: 0,
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
          border: '1px solid var(--border-color)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header del Modal */}
        <div className="card-header" style={{ marginBottom: '16px', paddingBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <History size={24} className="text-primary" />
            <div>
              <h3 id="history-modal-title" style={{ fontSize: '1.25rem', fontWeight: 800 }}>
                {t.historyModal?.title || 'Historial de Ejecuciones & Control de Versiones'}
              </h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {t.historyModal?.subtitle || 'Auditoría cronológica de transformaciones y comparador de calidad.'}
              </p>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <button
              className="btn btn-outline"
              onClick={fetchHistory}
              disabled={loading}
              title="Refrescar historial"
              style={{ padding: '6px 12px' }}
            >
              <RefreshCw size={14} className={loading ? 'spin' : ''} />
            </button>
            <button
              className="btn btn-outline"
              onClick={onClose}
              aria-label="Cerrar modal"
              style={{ padding: '6px 10px' }}
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {error && (
          <div
            style={{
              padding: '12px',
              backgroundColor: 'rgba(239, 68, 68, 0.12)',
              border: '1px solid var(--accent-rose)',
              borderRadius: '8px',
              color: 'var(--accent-rose)',
              marginBottom: '16px',
              fontSize: '0.85rem',
            }}
          >
            {error}
          </div>
        )}

        {/* Tabla de Ejecuciones Registradas */}
        {runs.length === 0 && !loading ? (
          <div
            style={{
              textAlign: 'center',
              padding: '36px',
              color: 'var(--text-muted)',
              backgroundColor: 'var(--bg-input)',
              borderRadius: '8px',
            }}
          >
            {t.historyModal?.noHistory || 'No hay ejecuciones registradas en esta sesión.'}
          </div>
        ) : (
          <div>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '12px',
                flexWrap: 'wrap',
                gap: '8px',
              }}
            >
              <span className="badge badge-blue">
                {runs.length} {t.historyModal?.runsCount || 'Ejecuciones Registradas'}
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {t.historyModal?.selectRunsToCompare || 'Selecciona 2 ejecuciones para comparar calidad:'}
              </span>
            </div>

            <div className="table-wrapper" style={{ maxHeight: '260px', overflowY: 'auto', marginBottom: '20px' }}>
              <table style={{ width: '100%', fontSize: '0.8rem' }}>
                <thead>
                  <tr>
                    <th style={{ width: '40px' }}>A</th>
                    <th style={{ width: '40px' }}>B</th>
                    <th>Run ID</th>
                    <th>{t.historyModal?.date || 'Fecha'}</th>
                    <th>Filas (Crudo → Limpio)</th>
                    <th>Quality Score</th>
                    <th>Pasos</th>
                    <th>Descargas</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((r) => {
                    const isCurrent = r.run_id === currentRunId;
                    const isA = selectedRunA === r.run_id;
                    const isB = selectedRunB === r.run_id;
                    return (
                      <tr
                        key={r.run_id}
                        style={{
                          backgroundColor: isCurrent ? 'rgba(59, 130, 246, 0.08)' : undefined,
                        }}
                      >
                        <td style={{ textAlign: 'center' }}>
                          <input
                            type="radio"
                            name="compare_run_a"
                            checked={isA}
                            onChange={() => setSelectedRunA(r.run_id)}
                            aria-label={`Seleccionar ${r.run_id} como versión A`}
                          />
                        </td>
                        <td style={{ textAlign: 'center' }}>
                          <input
                            type="radio"
                            name="compare_run_b"
                            checked={isB}
                            onChange={() => setSelectedRunB(r.run_id)}
                            aria-label={`Seleccionar ${r.run_id} como versión B`}
                          />
                        </td>
                        <td>
                          <code style={{ color: 'var(--primary)', fontWeight: 600 }}>
                            {r.run_id.slice(0, 8)}…
                          </code>
                          {isCurrent && (
                            <span
                              className="badge badge-emerald"
                              style={{ marginLeft: '6px', fontSize: '0.65rem' }}
                            >
                              Actual
                            </span>
                          )}
                        </td>
                        <td style={{ whiteSpace: 'nowrap', color: 'var(--text-muted)' }}>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <Calendar size={12} />
                            {new Date(r.finished_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </td>
                        <td>
                          <span>{r.rows_before}</span>
                          <ArrowRight size={12} style={{ display: 'inline', margin: '0 4px' }} />
                          <span className="text-emerald" style={{ fontWeight: 600 }}>
                            {r.rows_after}
                          </span>
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span>{r.score_before}</span>
                            <ArrowRight size={12} />
                            <span className="text-emerald" style={{ fontWeight: 700 }}>
                              {r.score_after}
                            </span>
                            {r.score_delta > 0 && (
                              <span className="badge badge-emerald" style={{ fontSize: '0.65rem' }}>
                                +{r.score_delta}
                              </span>
                            )}
                          </div>
                        </td>
                        <td style={{ textAlign: 'center' }}>{r.applied_steps_count}</td>
                        <td>
                          <div style={{ display: 'flex', gap: '6px' }}>
                            <a
                              href={r.download_url}
                              download
                              title={t.historyModal?.downloadCsv || 'CSV'}
                              className="btn btn-outline"
                              style={{ padding: '3px 6px', fontSize: '0.7rem' }}
                            >
                              <Download size={12} /> CSV
                            </a>
                            {r.parquet_url && (
                              <a
                                href={r.parquet_url}
                                download
                                title={t.historyModal?.downloadParquet || 'Parquet'}
                                className="btn btn-outline"
                                style={{ padding: '3px 6px', fontSize: '0.7rem' }}
                              >
                                <Database size={12} /> Pqt
                              </a>
                            )}
                            {r.script_url && (
                              <a
                                href={r.script_url}
                                download
                                title={t.historyModal?.downloadScript || 'Script'}
                                className="btn btn-outline"
                                style={{ padding: '3px 6px', fontSize: '0.7rem' }}
                              >
                                <FileCode size={12} /> Py
                              </a>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Botón de Disparo de Comparación */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '20px' }}>
              <button
                className="btn btn-primary"
                onClick={handleCompare}
                disabled={comparing || !selectedRunA || !selectedRunB}
                style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
              >
                <GitCompare size={16} />
                {comparing ? 'Comparando...' : (t.historyModal?.compareVersions || 'Comparar 2 Versiones')}
              </button>
            </div>

            {/* Panel de Comparación de Calidad Diferencial */}
            {comparison && (
              <div
                style={{
                  backgroundColor: 'var(--bg-input)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '10px',
                  padding: '16px',
                  marginTop: '12px',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '12px',
                    marginBottom: '16px',
                    borderBottom: '1px solid var(--border-color)',
                    paddingBottom: '12px',
                  }}
                >
                  <div>
                    <h4 style={{ fontSize: '1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <TrendingUp size={18} className="text-emerald" /> Comparativa de Calidad Dimensional
                    </h4>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                      {comparison.explanation}
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Score Global</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: 800 }}>
                        <span>{comparison.overall_score_before}</span>
                        <ArrowRight size={14} style={{ display: 'inline', margin: '0 4px' }} />
                        <span className="text-emerald">{comparison.overall_score_after}</span>
                      </div>
                    </div>
                    <span
                      className={`badge ${comparison.delta_score >= 0 ? 'badge-emerald' : 'badge-rose'}`}
                      style={{ fontSize: '0.85rem', padding: '6px 10px' }}
                    >
                      {comparison.delta_score >= 0 ? `+${comparison.delta_score}` : comparison.delta_score} pts
                    </span>
                  </div>
                </div>

                {/* Desglose de las 5 Dimensiones */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '10px' }}>
                  {comparison.dimensions.map((dim) => {
                    const isPositive = dim.delta >= 0;
                    return (
                      <div
                        key={dim.dimension}
                        style={{
                          backgroundColor: 'var(--bg-main)',
                          padding: '12px',
                          borderRadius: '8px',
                          border: '1px solid var(--border-color)',
                        }}
                      >
                        <div style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'capitalize', color: 'var(--text-muted)' }}>
                          {dim.dimension}
                        </div>
                        <div style={{ fontSize: '1.1rem', fontWeight: 700, margin: '4px 0', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span>{dim.score_before}%</span>
                          <ArrowRight size={12} className="text-primary" />
                          <span className="text-emerald">{dim.score_after}%</span>
                        </div>
                        <div style={{ fontSize: '0.7rem', color: isPositive ? 'var(--accent-emerald)' : 'var(--accent-rose)' }}>
                          {isPositive ? `+${dim.delta}` : dim.delta} pts ({dim.issues_after} issues)
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Footer del Modal */}
        <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'flex-end' }}>
          <button className="btn btn-outline" onClick={onClose}>
            {t.historyModal?.close || 'Cerrar'}
          </button>
        </div>
      </div>
    </div>
  );
};
