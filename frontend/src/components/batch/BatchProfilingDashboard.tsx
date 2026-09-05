import React from 'react';
import { ShieldCheck, Table, AlertTriangle, Sparkles, Database } from 'lucide-react';
import { ProfilingReport, QualityReport, DatasetMetadata } from '../../types';
import { useLanguage } from '../../context/LanguageContext';

export interface BatchItem {
  metadata: DatasetMetadata;
  profiling: ProfilingReport;
  quality: QualityReport;
}

interface Props {
  items: BatchItem[];
  onGeneratePlan: (provider: string) => void;
  loadingPlan: boolean;
}

export const BatchProfilingDashboard: React.FC<Props> = ({
  items,
  onGeneratePlan,
  loadingPlan,
}) => {
  const { t } = useLanguage();

  const totalRows = items.reduce((acc, it) => acc + it.profiling.row_count, 0);
  const totalCols = items.reduce((acc, it) => acc + it.profiling.column_count, 0);
  const totalIssues = items.reduce((acc, it) => acc + it.quality.issues_count, 0);
  const avgScore =
    items.length > 0
      ? Math.round(
          (items.reduce((acc, it) => acc + it.quality.quality_score.overall_score, 0) / items.length) * 10
        ) / 10
      : 0;

  const getScoreColor = (val: number) => {
    if (val >= 85) return 'var(--accent-emerald)';
    if (val >= 65) return 'var(--accent-amber)';
    return 'var(--accent-rose)';
  };

  return (
    <div>
      {/* Banner de Calidad Consolidada del Lote */}
      <div className="score-banner" style={{ marginBottom: '24px' }}>
        <div style={{ textAlign: 'center' }}>
          <div
            className="score-badge-circle"
            style={{ borderColor: getScoreColor(avgScore) }}
          >
            <span className="score-num" style={{ color: getScoreColor(avgScore) }}>
              {avgScore}
            </span>
            <span className="score-label">{t.profiling.qualityScore} (Media)</span>
          </div>
        </div>

        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: '8px' }}>
            Auditoría de Calidad — Lote de {items.length} Tablas Relacionadas
          </h2>
          <p style={{ color: 'var(--text-muted)', marginBottom: '16px', fontSize: '0.9rem' }}>
            Se han analizado en paralelo todas las tablas del modelo relacional. Se detectaron {totalIssues} anomalías
            distribuidas en el lote que serán saneadas en el siguiente paso.
          </p>

          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <span className="badge badge-blue">
              <Database size={14} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
              {items.length} Tablas
            </span>
            <span className="badge badge-blue">Filas Totales: {totalRows.toLocaleString()}</span>
            <span className="badge badge-blue">Columnas Totales: {totalCols}</span>
            <span className="badge badge-rose">Incidencias Totales: {totalIssues}</span>
          </div>
        </div>
      </div>

      {/* Tabla resumen de cada dataset del lote */}
      <div className="card" style={{ marginBottom: '24px', overflowX: 'auto' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Table size={18} className="text-primary" /> Desglose por Tabla
        </h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
              <th style={{ padding: '10px 14px' }}>Tabla / Archivo</th>
              <th style={{ padding: '10px 14px' }}>Filas</th>
              <th style={{ padding: '10px 14px' }}>Columnas</th>
              <th style={{ padding: '10px 14px' }}>Duplicados</th>
              <th style={{ padding: '10px 14px' }}>Incidencias</th>
              <th style={{ padding: '10px 14px' }}>Data Score</th>
            </tr>
          </thead>
          <tbody>
            {items.map(({ metadata, profiling, quality }) => (
              <tr key={metadata.dataset_id} style={{ borderBottom: '1px solid var(--border-color-light)' }}>
                <td style={{ padding: '12px 14px', fontWeight: 600 }}>{metadata.filename}</td>
                <td style={{ padding: '12px 14px' }}>{profiling.row_count.toLocaleString()}</td>
                <td style={{ padding: '12px 14px' }}>{profiling.column_count}</td>
                <td style={{ padding: '12px 14px' }}>
                  {profiling.duplicates_count > 0 ? (
                    <span style={{ color: 'var(--accent-amber)' }}>{profiling.duplicates_count}</span>
                  ) : (
                    <span style={{ color: 'var(--text-muted)' }}>0</span>
                  )}
                </td>
                <td style={{ padding: '12px 14px' }}>
                  {quality.issues_count > 0 ? (
                    <span style={{ color: 'var(--accent-rose)', fontWeight: 600 }}>{quality.issues_count}</span>
                  ) : (
                    <span style={{ color: 'var(--accent-emerald)' }}>0</span>
                  )}
                </td>
                <td style={{ padding: '12px 14px' }}>
                  <span
                    style={{
                      padding: '3px 10px',
                      borderRadius: '12px',
                      fontWeight: 700,
                      fontSize: '0.85rem',
                      backgroundColor: `${getScoreColor(quality.quality_score.overall_score)}18`,
                      color: getScoreColor(quality.quality_score.overall_score),
                    }}
                  >
                    {quality.quality_score.overall_score}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Acciones de generación del plan para todas las tablas */}
      <div className="card" style={{ textAlign: 'center', padding: '24px' }}>
        <h4 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '8px' }}>
          Siguiente Paso: Propuesta de Limpieza para Todas las Tablas
        </h4>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '20px' }}>
          El motor analizará las anomalías de cada tabla y propondrá un plan de correcciones ejecutables para sanear todo el conjunto a la vez.
        </p>
        <div style={{ display: 'flex', gap: '14px', justifyContent: 'center', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => onGeneratePlan('mock')}
            disabled={loadingPlan}
            style={{ padding: '10px 24px', fontSize: '0.95rem' }}
          >
            <Sparkles size={18} />
            <span>{loadingPlan ? 'Generando planes...' : 'Proponer Plan de Limpieza con IA (Todas las Tablas)'}</span>
          </button>
          <button
            type="button"
            className="btn btn-outline"
            onClick={() => onGeneratePlan('rules')}
            disabled={loadingPlan}
            style={{ padding: '10px 24px', fontSize: '0.95rem' }}
          >
            <ShieldCheck size={18} />
            <span>{loadingPlan ? 'Generando planes...' : 'Proponer Plan por Reglas Deterministas (Todas)'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
