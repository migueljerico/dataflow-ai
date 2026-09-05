import React, { useState, useEffect } from 'react';
import { CheckCircle, Download, Database, Network, Sparkles, RefreshCw, ArrowRight, ShieldCheck } from 'lucide-react';
import { ExecutionResult, MultiTableStarSchema } from '../../types';
import { MultiTableStarSchemaViewer } from '../MultiTableStarSchema';
import { api } from '../../services/api';

export interface BatchExecutionItem {
  datasetId: string;
  filename: string;
  result: ExecutionResult;
  scoreBefore: number;
  scoreAfter: number;
  scoreDelta: number;
}

interface Props {
  results: BatchExecutionItem[];
  cleanStarSchema: MultiTableStarSchema | null;
  loadingStarSchema: boolean;
  onGenerateStarSchema: () => void;
  onResetSession: () => void;
}

export const BatchExecutionReport: React.FC<Props> = ({
  results,
  cleanStarSchema,
  loadingStarSchema,
  onGenerateStarSchema,
  onResetSession,
}) => {
  const [showStarSchema, setShowStarSchema] = useState<boolean>(true);

  const totalRowsBefore = results.reduce((acc, r) => acc + r.result.rows_before, 0);
  const totalRowsAfter = results.reduce((acc, r) => acc + r.result.rows_after, 0);
  const totalStepsApplied = results.reduce((acc, r) => acc + r.result.applied_steps_count, 0);
  const avgScoreBefore =
    results.length > 0
      ? Math.round((results.reduce((acc, r) => acc + r.scoreBefore, 0) / results.length) * 10) / 10
      : 0;
  const avgScoreAfter =
    results.length > 0
      ? Math.round((results.reduce((acc, r) => acc + r.scoreAfter, 0) / results.length) * 10) / 10
      : 0;

  return (
    <div>
      {/* Cabecera de éxito de ejecución en lote */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h2 className="card-title text-emerald" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <CheckCircle size={24} /> ¡Lote de {results.length} Tablas Limpiado con Éxito!
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '4px' }}>
              Todas las transformaciones deterministas han sido aprobadas y aplicadas sin pérdida de información.
            </p>
          </div>
          <button className="btn btn-outline" onClick={onResetSession}>
            Iniciar Nueva Sesión
          </button>
        </div>

        {/* Métricas consolidadas del lote */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '12px',
            marginTop: '20px',
          }}
        >
          <div style={{ backgroundColor: 'var(--bg-input)', padding: '14px', borderRadius: '8px' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Calidad Media (Antes → Después)</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 800, marginTop: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span>{avgScoreBefore}%</span>
              <ArrowRight size={14} className="text-primary" />
              <span className="text-emerald">{avgScoreAfter}%</span>
            </div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-input)', padding: '14px', borderRadius: '8px' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Filas Totales Procesadas</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 800, marginTop: '4px' }}>
              {totalRowsAfter.toLocaleString()}
            </div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-input)', padding: '14px', borderRadius: '8px' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Pasos ETL Ejecutados</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 800, marginTop: '4px', color: 'var(--primary)' }}>
              {totalStepsApplied} pasos
            </div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-input)', padding: '14px', borderRadius: '8px' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Estado del Modelo</div>
            <div style={{ fontSize: '1rem', fontWeight: 700, marginTop: '6px', color: 'var(--accent-emerald)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <ShieldCheck size={16} /> 100% Saneado
            </div>
          </div>
        </div>
      </div>

      {/* Tabla detallada de descargas de cada archivo limpio */}
      <div className="card" style={{ marginBottom: '32px', overflowX: 'auto' }}>
        <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Database size={18} className="text-primary" /> Archivos Limpios Listos para Descarga
        </h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
              <th style={{ padding: '10px 12px' }}>Tabla</th>
              <th style={{ padding: '10px 12px' }}>Filas (Antes → Después)</th>
              <th style={{ padding: '10px 12px' }}>Calidad</th>
              <th style={{ padding: '10px 12px' }}>Descarga CSV</th>
              <th style={{ padding: '10px 12px' }}>Descarga Parquet</th>
            </tr>
          </thead>
          <tbody>
            {results.map((r) => (
              <tr key={r.datasetId} style={{ borderBottom: '1px solid var(--border-color-light)' }}>
                <td style={{ padding: '12px', fontWeight: 600 }}>{r.filename}</td>
                <td style={{ padding: '12px' }}>
                  {r.result.rows_before} → <strong className="text-emerald">{r.result.rows_after}</strong>
                </td>
                <td style={{ padding: '12px' }}>
                  <span style={{ fontWeight: 700, color: 'var(--accent-emerald)' }}>
                    {r.scoreAfter}%
                  </span>
                  {r.scoreDelta > 0 && (
                    <span style={{ fontSize: '0.75rem', color: 'var(--accent-emerald)', marginLeft: '4px' }}>
                      (+{r.scoreDelta})
                    </span>
                  )}
                </td>
                <td style={{ padding: '12px' }}>
                  <a
                    href={r.result.download_url}
                    download
                    className="btn btn-outline"
                    style={{ fontSize: '0.75rem', padding: '4px 10px', textDecoration: 'none' }}
                  >
                    <Download size={13} /> {r.result.clean_filename}
                  </a>
                </td>
                <td style={{ padding: '12px' }}>
                  {r.result.parquet_url && (
                    <a
                      href={r.result.parquet_url}
                      download
                      className="btn btn-outline"
                      style={{ fontSize: '0.75rem', padding: '4px 10px', textDecoration: 'none', borderColor: 'var(--primary)', color: 'var(--primary)' }}
                    >
                      <Database size={13} /> Parquet
                    </a>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* SECCIÓN FINAL DEL FLUJO: ESQUEMA DE ESTRELLA DEL MODELO LIMPIO */}
      <div className="card" style={{ marginBottom: '24px', border: '1px solid var(--primary)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
          <div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
              <Network size={20} /> 7️⃣ Esquema de Estrella del Modelo Semántico Limpio
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '4px', margin: 0 }}>
              Modelo relacional generado a partir de las tablas limpiadas: tabla de hechos central, dimensiones satélite, cardinalidades `1:*` e integridad referencial auditada lista para Power BI.
            </p>
          </div>

          {!cleanStarSchema && (
            <button
              type="button"
              className="btn btn-primary"
              onClick={onGenerateStarSchema}
              disabled={loadingStarSchema}
              style={{ padding: '8px 20px', fontSize: '0.9rem' }}
            >
              <Sparkles size={16} />
              <span>{loadingStarSchema ? 'Calculando relaciones limpias...' : 'Generar Esquema de Estrella'}</span>
            </button>
          )}
        </div>

        {loadingStarSchema ? (
          <div style={{ textAlign: 'center', padding: '40px 20px' }}>
            <RefreshCw size={32} className="text-primary spin" style={{ margin: '0 auto 12px auto' }} />
            <div style={{ fontWeight: 600 }}>Analizando integridad referencial entre las tablas limpias...</div>
          </div>
        ) : cleanStarSchema ? (
          <MultiTableStarSchemaViewer schema={cleanStarSchema} />
        ) : (
          <div style={{ textAlign: 'center', padding: '30px', backgroundColor: 'var(--bg-input)', borderRadius: '8px' }}>
            <p style={{ color: 'var(--text-muted)', marginBottom: '12px' }}>
              Pulsa el botón superior para calcular y visualizar el Esquema de Estrella sobre el lote limpio.
            </p>
            <button type="button" className="btn btn-primary" onClick={onGenerateStarSchema}>
              Generar Esquema de Estrella Ahora
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
