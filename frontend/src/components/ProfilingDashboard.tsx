import React from 'react';
import { ShieldCheck, Table, AlertTriangle, Sparkles } from 'lucide-react';
import { ProfilingReport, QualityReport, DatasetMetadata } from '../types';

interface Props {
  metadata: DatasetMetadata;
  profiling: ProfilingReport;
  quality: QualityReport;
  onGeneratePlan: (provider: string) => void;
  loadingPlan: boolean;
}

export const ProfilingDashboard: React.FC<Props> = ({
  metadata,
  profiling,
  quality,
  onGeneratePlan,
  loadingPlan,
}) => {
  const score = quality.quality_score;

  const getScoreColor = (val: number) => {
    if (val >= 85) return 'var(--accent-emerald)';
    if (val >= 65) return 'var(--accent-amber)';
    return 'var(--accent-rose)';
  };

  return (
    <div>
      {/* Banner de Quality Score Global */}
      <div className="score-banner">
        <div style={{ textAlign: 'center' }}>
          <div
            className="score-badge-circle"
            style={{ borderColor: getScoreColor(score.overall_score) }}
          >
            <span className="score-num" style={{ color: getScoreColor(score.overall_score) }}>
              {score.overall_score}
            </span>
            <span className="score-label">Score / 100</span>
          </div>
        </div>

        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: '8px' }}>
            Diagnóstico de Calidad de Datos — {metadata.filename}
          </h2>
          <p style={{ color: 'var(--text-muted)', marginBottom: '16px', fontSize: '0.9rem' }}>
            {score.explanation}
          </p>

          <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
            <span className="badge badge-blue">Filas: {profiling.row_count.toLocaleString()}</span>
            <span className="badge badge-blue">Columnas: {profiling.column_count}</span>
            <span className="badge badge-amber">Duplicados: {profiling.duplicates_count} ({profiling.duplicates_percentage}%)</span>
            <span className="badge badge-rose">Problemas detectados: {quality.issues_count}</span>
          </div>
        </div>
      </div>

      {/* Tarjetas de las 5 Dimensiones con Lenguaje Empresarial Claro */}
      <div className="dimensions-grid">
        <div className="dim-card">
          <div className="dim-header">
            <span>Datos Completos (30%)</span>
            <ShieldCheck size={16} className="text-primary" />
          </div>
          <div className="dim-score">{score.completeness.score}%</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            {score.completeness.issues_count} columnas con nulos
          </div>
        </div>

        <div className="dim-card">
          <div className="dim-header">
            <span>Formatos Válidos (25%)</span>
            <ShieldCheck size={16} className="text-primary" />
          </div>
          <div className="dim-score">{score.validity.score}%</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            {score.validity.issues_count} correcciones de tipo/fecha
          </div>
        </div>

        <div className="dim-card">
          <div className="dim-header">
            <span>Formato Homogéneo (20%)</span>
            <ShieldCheck size={16} className="text-primary" />
          </div>
          <div className="dim-score">{score.consistency.score}%</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            {score.consistency.issues_count} variantes de texto
          </div>
        </div>

        <div className="dim-card">
          <div className="dim-header">
            <span>Registros Únicos (15%)</span>
            <ShieldCheck size={16} className="text-primary" />
          </div>
          <div className="dim-score">{score.uniqueness.score}%</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            {score.uniqueness.issues_count} filas duplicadas
          </div>
        </div>

        <div className="dim-card">
          <div className="dim-header">
            <span>Reglas de Negocio (10%)</span>
            <ShieldCheck size={16} className="text-primary" />
          </div>
          <div className="dim-score">{score.integrity.score}%</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            {score.integrity.issues_count} desvíos de rango/lógica
          </div>
        </div>
      </div>

      {/* Tabla de Profiling de Columnas */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <Table size={20} className="text-primary" /> Catálogo y Perfilado Estructural de Columnas
          </h3>
          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              className="btn btn-outline"
              disabled={loadingPlan}
              onClick={() => onGeneratePlan('rules')}
            >
              Motor de Reglas Determinista
            </button>
            <button
              className="btn btn-primary"
              disabled={loadingPlan}
              onClick={() => onGeneratePlan('mock')}
            >
              <Sparkles size={16} /> Generar Plan con Copiloto IA
            </button>
          </div>
        </div>

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Columna</th>
                <th>Tipo Inferido</th>
                <th>Sugerencia Semántica</th>
                <th>Nulos (%)</th>
                <th>Únicos</th>
                <th>Muestra de Valores</th>
                <th>Advertencias</th>
              </tr>
            </thead>
            <tbody>
              {profiling.columns.map((col) => (
                <tr key={col.column_name}>
                  <td style={{ fontWeight: 600 }}>{col.column_name}</td>
                  <td>
                    <span className="badge badge-blue">{col.inferred_type}</span>
                  </td>
                  <td>
                    <span className="badge badge-emerald">{col.semantic_hint}</span>
                  </td>
                  <td>
                    {col.null_count > 0 ? (
                      <span className="text-rose" style={{ fontWeight: 600 }}>
                        {col.null_count} ({col.null_percentage}%)
                      </span>
                    ) : (
                      <span className="text-emerald">0 (0%)</span>
                    )}
                  </td>
                  <td>{col.unique_count.toLocaleString()}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                    {col.sample_values.join(', ')}
                  </td>
                  <td>
                    {col.warnings.length > 0 ? (
                      col.warnings.map((w, idx) => (
                        <div key={idx} style={{ color: 'var(--accent-amber)', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <AlertTriangle size={12} /> {w}
                        </div>
                      ))
                    ) : (
                      <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>Sin incidencias</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
