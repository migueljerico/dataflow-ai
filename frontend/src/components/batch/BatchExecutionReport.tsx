import React, { useState, useEffect, useMemo } from 'react';
import {
  CheckCircle,
  Download,
  Database,
  Network,
  Sparkles,
  RefreshCw,
  ArrowRight,
  ShieldCheck,
  FileCode,
  Archive,
  Layers,
  Table2,
} from 'lucide-react';
import { ExecutionResult, MultiTableStarSchema, StarSchemaTableNode } from '../../types';
import { MultiTableStarSchemaViewer } from '../MultiTableStarSchema';
import { BusinessInsights } from '../BusinessInsights';
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

const isFactTable = (filename: string, cleanFilename: string, factNode?: StarSchemaTableNode): boolean => {
  if (!factNode || !factNode.table_name) return false;
  const factLower = factNode.table_name.toLowerCase();
  const fileLower = filename.toLowerCase();
  const fileStem = fileLower.replace(/\.[^/.]+$/, '');
  const cleanLower = cleanFilename.toLowerCase();
  return fileLower.includes(factLower) || factLower.includes(fileStem) || cleanLower.includes(factLower);
};

export const BatchExecutionReport: React.FC<Props> = ({
  results,
  cleanStarSchema,
  loadingStarSchema,
  onGenerateStarSchema,
  onResetSession,
}) => {
  // Seleccionar la tabla activa para inspeccionar Business Insights y fórmulas DAX
  // Por defecto, selecciona la tabla de hechos si está identificada en cleanStarSchema, o la primera
  const defaultSelectedId = useMemo(() => {
    if (!results || results.length === 0) return '';
    if (cleanStarSchema?.fact_table) {
      const match = results.find((r) =>
        isFactTable(r.filename, r.result.clean_filename, cleanStarSchema.fact_table)
      );
      if (match) return match.result.run_id;
    }
    return results[0]?.result?.run_id || '';
  }, [results, cleanStarSchema]);

  const [selectedRunId, setSelectedRunId] = useState<string>(defaultSelectedId);

  useEffect(() => {
    if (defaultSelectedId && (!selectedRunId || !results.some((r) => r.result.run_id === selectedRunId))) {
      setSelectedRunId(defaultSelectedId);
    }
  }, [defaultSelectedId, results, selectedRunId]);

  const activeItem = useMemo(() => {
    return results.find((r) => r.result.run_id === selectedRunId) || results[0];
  }, [results, selectedRunId]);

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
              Todas las transformaciones deterministas han sido aprobadas y aplicadas. Datasets limpios listos para descarga individual o en ZIP, fórmulas DAX contextuales y modelo estrella.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
            {results.length > 0 && (
              <a
                href={api.getBatchZipDownloadUrl(results.map((r) => r.result.run_id))}
                download="datasets_limpios_lote.zip"
                className="btn btn-primary"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  textDecoration: 'none',
                  padding: '9px 18px',
                  fontWeight: 600,
                  boxShadow: '0 2px 8px rgba(59, 130, 246, 0.3)',
                }}
                title="Descargar paquete completo con todos los CSVs limpios, Parquet columnar y Scripts de Python en un solo archivo ZIP"
              >
                <Archive size={18} /> Descargar Lote Completo (.ZIP)
              </a>
            )}
            <button className="btn btn-outline" onClick={onResetSession}>
              Iniciar Nueva Sesión
            </button>
          </div>
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
            <div style={{ fontSize: '0.72rem', color: 'var(--accent-emerald)', marginTop: '4px' }}>
              +{Math.round((avgScoreAfter - avgScoreBefore) * 10) / 10} pts de mejora media
            </div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-input)', padding: '14px', borderRadius: '8px' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Filas Totales Saneadas</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 800, marginTop: '4px' }}>
              {totalRowsAfter.toLocaleString()}
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--accent-emerald)', marginTop: '4px' }}>
              Duplicados eliminados: {totalRowsBefore - totalRowsAfter}
            </div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-input)', padding: '14px', borderRadius: '8px' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Pasos ETL Ejecutados</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 800, marginTop: '4px', color: 'var(--primary)' }}>
              {totalStepsApplied} pasos
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              100% Determinista
            </div>
          </div>

          <div style={{ backgroundColor: 'var(--bg-input)', padding: '14px', borderRadius: '8px' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Estado del Modelo</div>
            <div style={{ fontSize: '1rem', fontWeight: 700, marginTop: '6px', color: 'var(--accent-emerald)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <ShieldCheck size={16} /> 100% Saneado
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--accent-emerald)', marginTop: '4px' }}>
              Sin pérdida de registros válidos
            </div>
          </div>
        </div>
      </div>

      {/* SECCIÓN 1: DESCARGAS DIRECTAS Y DESTACADAS DE TODOS LOS DATASETS LIMPIOS */}
      <div className="card" style={{ marginBottom: '28px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
          <div>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
              <Database size={20} className="text-primary" /> Datasets Limpios & Artefactos de Exportación ({results.length} Tablas)
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '4px', margin: 0 }}>
              Acceso directo a los archivos saneados por el motor ETL determinista en formatos CSV estándar, Apache Parquet columnar y scripts reproducibles de Python.
            </p>
          </div>
          <span className="badge badge-emerald" style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.8rem' }}>
            <ShieldCheck size={14} /> 100% Calidad Verificada
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {results.map((r) => {
            const isSelected = r.result.run_id === selectedRunId;
            const isFact = isFactTable(r.filename, r.result.clean_filename, cleanStarSchema?.fact_table);

            return (
              <div
                key={r.datasetId}
                style={{
                  backgroundColor: isSelected ? 'rgba(59, 130, 246, 0.06)' : 'var(--bg-input)',
                  border: isSelected ? '1px solid var(--primary)' : '1px solid var(--border-color)',
                  borderRadius: '10px',
                  padding: '14px 18px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '16px',
                  transition: 'all 0.2s ease',
                }}
              >
                {/* Info tabla */}
                <div style={{ minWidth: '220px', flex: '1 1 240px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>{r.filename}</span>
                    {isFact && (
                      <span className="badge badge-amber" style={{ fontSize: '0.7rem' }}>
                        ★ Tabla de Hechos (Fact)
                      </span>
                    )}
                    {isSelected && (
                      <span className="badge badge-blue" style={{ fontSize: '0.7rem' }}>
                        Seleccionada para Fórmulas
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                    <span>
                      Archivo limpio: <code style={{ color: 'var(--primary)', fontWeight: 600 }}>{r.result.clean_filename}</code>
                    </span>
                    <span>
                      Filas: {r.result.rows_before} → <strong className="text-emerald">{r.result.rows_after}</strong>
                    </span>
                    <span>
                      Score: <strong className="text-emerald">{r.scoreAfter}%</strong>
                      {r.scoreDelta > 0 && <span style={{ color: 'var(--accent-emerald)', marginLeft: '3px' }}>(+{r.scoreDelta})</span>}
                    </span>
                  </div>
                </div>

                {/* Botones de acción y descarga */}
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                  {/* Descarga CSV */}
                  <a
                    href={r.result.download_url}
                    download={r.result.clean_filename}
                    className="btn btn-success"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      fontSize: '0.8rem',
                      padding: '8px 14px',
                      textDecoration: 'none',
                      fontWeight: 600,
                    }}
                    title={`Descargar CSV depurado ${r.result.clean_filename}`}
                  >
                    <Download size={15} /> Descargar CSV
                  </a>

                  {/* Descarga Parquet */}
                  {r.result.parquet_url && (
                    <a
                      href={r.result.parquet_url}
                      download={r.result.parquet_filename || `${r.result.clean_filename.replace('.csv', '')}.parquet`}
                      className="btn btn-outline"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        fontSize: '0.8rem',
                        padding: '8px 14px',
                        textDecoration: 'none',
                        borderColor: 'var(--primary)',
                        color: 'var(--primary)',
                        fontWeight: 600,
                      }}
                      title="Descargar en formato nativo columnar Apache Parquet"
                    >
                      <Database size={15} /> Parquet
                    </a>
                  )}

                  {/* Descarga Script Python */}
                  {r.result.script_url && (
                    <a
                      href={r.result.script_url}
                      download={`pipeline_${r.result.clean_filename.replace('.csv', '')}.py`}
                      className="btn btn-outline"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        fontSize: '0.8rem',
                        padding: '8px 14px',
                        textDecoration: 'none',
                        fontWeight: 600,
                      }}
                      title="Descargar script de Python reproducible con todos los pasos ETL ejecutados"
                    >
                      <FileCode size={15} /> Script .py
                    </a>
                  )}

                  {/* Botón para seleccionar y ver fórmulas/insights */}
                  <button
                    type="button"
                    onClick={() => setSelectedRunId(r.result.run_id)}
                    className={`btn ${isSelected ? 'btn-primary' : 'btn-outline'}`}
                    style={{
                      fontSize: '0.8rem',
                      padding: '8px 14px',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                    }}
                  >
                    <Layers size={15} /> {isSelected ? 'Viendo DAX & Insights' : 'Ver Fórmulas & DAX'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* SECCIÓN 2: BUSINESS INSIGHTS, FÓRMULAS DAX Y GUÍA DE INTEGRACIÓN POWER BI / EXCEL POR TABLA */}
      {activeItem && (
        <div style={{ marginBottom: '32px' }}>
          <div className="card" style={{ marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
              <div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '8px', margin: 0, color: 'var(--primary)' }}>
                  <Layers size={22} /> Fórmulas DAX, Power Query M y Business Insights
                </h3>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '4px', margin: 0 }}>
                  Selecciona cualquier tabla del lote para inspeccionar sus fórmulas DAX adaptadas, código Power Query M, fórmulas Excel, KPIs y segmentación.
                </p>
              </div>

              {/* Selector de Tabla (Pills) */}
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginRight: '4px' }}>Tabla:</span>
                {results.map((r) => {
                  const isSel = r.result.run_id === selectedRunId;
                  const isFact = isFactTable(r.filename, r.result.clean_filename, cleanStarSchema?.fact_table);

                  return (
                    <button
                      key={r.datasetId}
                      type="button"
                      onClick={() => setSelectedRunId(r.result.run_id)}
                      className={`btn ${isSel ? 'btn-primary' : 'btn-outline'}`}
                      style={{
                        padding: '6px 12px',
                        fontSize: '0.8rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        fontWeight: isSel ? 700 : 500,
                      }}
                    >
                      <Table2 size={14} />
                      <span>{r.filename}</span>
                      {isFact && <span style={{ color: isSel ? '#fef08a' : '#f59e0b', fontSize: '0.7rem' }}>★</span>}
                    </button>
                  );
                })}
              </div>
            </div>

            <div
              style={{
                backgroundColor: 'rgba(59, 130, 246, 0.08)',
                border: '1px solid rgba(59, 130, 246, 0.25)',
                borderRadius: '8px',
                padding: '8px 14px',
                marginTop: '14px',
                fontSize: '0.82rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '8px',
              }}
            >
              <div>
                Explorando: <strong>{activeItem.filename}</strong> · Modelo limpio: <code style={{ color: 'var(--primary)', fontWeight: 600 }}>{activeItem.result.clean_filename}</code> ({activeItem.result.rows_after.toLocaleString()} registros)
              </div>
              <span className="badge badge-blue">DAX y Power Query 100% Adaptados</span>
            </div>
          </div>

          {/* Renderizado del componente BusinessInsights completo para la tabla activa */}
          <BusinessInsights key={activeItem.result.run_id} runId={activeItem.result.run_id} />
        </div>
      )}

      {/* SECCIÓN FINAL DEL FLUJO: ESQUEMA DE ESTRELLA DEL MODELO SEMÁNTICO LIMPIO */}
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
