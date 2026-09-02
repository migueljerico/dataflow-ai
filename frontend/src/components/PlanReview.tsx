import React, { useState, useEffect, useMemo } from 'react';
import {
  CheckCircle2,
  XCircle,
  Play,
  ShieldAlert,
  Sliders,
  AlertTriangle,
  Columns,
  Eye,
  EyeOff,
  Table,
  ArrowRight,
  Zap,
  Coins,
  Clock,
  Bot,
} from 'lucide-react';
import { DatasetMetadata, ProfilingReport, TransformationPlan, TransformationStep } from '../types';
import { useLanguage } from '../context/LanguageContext';

interface Props {
  plan: TransformationPlan;
  onExecutePlan: (approvedSteps: TransformationStep[]) => void;
  executing: boolean;
  metadata?: DatasetMetadata | null;
  profiling?: ProfilingReport | null;
}

export const PlanReview: React.FC<Props> = ({
  plan,
  onExecutePlan,
  executing,
  metadata,
  profiling,
}) => {
  const { t } = useLanguage();
  const [steps, setSteps] = useState<TransformationStep[]>(plan.steps);
  const [showGlobalSchema, setShowGlobalSchema] = useState<boolean>(false);
  const [previewStepId, setPreviewStepId] = useState<string | null>(null);

  useEffect(() => {
    setSteps(plan.steps);
  }, [plan.steps]);

  const toggleStepStatus = (stepId: string, newStatus: 'approved' | 'rejected') => {
    setSteps((prev) =>
      prev.map((s) => (s.step_id === stepId ? { ...s, status: newStatus } : s))
    );
  };

  const handleParameterChange = (stepId: string, paramKey: string, value: unknown) => {
    setSteps((prev) =>
      prev.map((s) =>
        s.step_id === stepId ? { ...s, parameters: { ...s.parameters, [paramKey]: value } } : s
      )
    );
  };

  const approvedSteps = useMemo(() => steps.filter((s) => s.status !== 'rejected'), [steps]);
  const approvedCount = approvedSteps.length;

  const allColumns = useMemo(() => {
    if (metadata?.columns && metadata.columns.length > 0) {
      return metadata.columns;
    }
    if (profiling?.columns && profiling.columns.length > 0) {
      return profiling.columns.map((c) => c.column_name);
    }
    const cols = new Set<string>();
    plan.steps.forEach((s) => {
      if (s.column) cols.add(s.column);
      if (Array.isArray(s.parameters?.columns)) {
        (s.parameters.columns as string[]).forEach((c) => cols.add(c));
      }
    });
    return Array.from(cols);
  }, [metadata, profiling, plan.steps]);

  const hasNewClusterCol = useMemo(
    () => approvedSteps.some((s) => s.operation === 'cluster_kmeans'),
    [approvedSteps]
  );

  return (
    <div className="card">
      <div className="card-header" style={{ flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 className="card-title">
            <Sliders size={20} className="text-primary" /> {t.plan.title}
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '4px' }}>
            {t.plan.source}: <strong style={{ color: 'var(--primary)' }}>{plan.source}</strong> | {t.plan.summary}: {plan.summary}
          </p>
        </div>

        {plan.ai_metrics && (
          <div
            data-testid="ai-metrics-banner"
            style={{
              width: '100%',
              display: 'flex',
              gap: '14px',
              alignItems: 'center',
              flexWrap: 'wrap',
              backgroundColor: 'rgba(59, 130, 246, 0.08)',
              border: '1px solid rgba(59, 130, 246, 0.25)',
              borderRadius: '8px',
              padding: '8px 14px',
              marginTop: '4px',
              fontSize: '0.8rem',
              color: 'var(--text-color)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: 'var(--primary)' }}>
              <Bot size={15} />
              <span>{plan.ai_metrics.model || 'Gemini 2.5 Flash'}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)' }}>
              <Clock size={14} className="text-primary" />
              <span>
                {t.plan?.aiLatency || 'Latencia'}:{' '}
                <strong style={{ color: 'var(--text-color)' }}>
                  {plan.ai_metrics.latency_ms >= 1000
                    ? `${(plan.ai_metrics.latency_ms / 1000).toFixed(2)} s`
                    : `${plan.ai_metrics.latency_ms.toFixed(0)} ms`}
                </strong>
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)' }}>
              <Zap size={14} style={{ color: 'var(--accent-amber, #f59e0b)' }} />
              <span>
                {t.plan?.aiTokens || 'Tokens'}:{' '}
                <strong style={{ color: 'var(--text-color)' }}>
                  {plan.ai_metrics.total_tokens.toLocaleString()}
                </strong>{' '}
                <span style={{ fontSize: '0.72rem', opacity: 0.85 }}>
                  ({plan.ai_metrics.prompt_tokens} in / {plan.ai_metrics.completion_tokens} out)
                </span>
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)' }}>
              <Coins size={14} style={{ color: 'var(--accent-emerald, #10b981)' }} />
              <span>
                {t.plan?.aiCost || 'Coste Estimado'}:{' '}
                <strong style={{ color: 'var(--accent-emerald, #10b981)' }}>
                  ${plan.ai_metrics.estimated_cost_usd.toFixed(6)} USD
                </strong>
              </span>
            </div>
            {plan.ai_metrics.cached && (
              <span
                data-testid="ai-cached-badge"
                className="badge badge-emerald"
                style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.725rem' }}
                title="Respuesta recuperada instantáneamente desde la caché de inferencia semántica (ahorro del 100% en tokens)"
              >
                <Zap size={12} /> {t.plan?.aiCachedBadge || 'Caché de Inferencia (100% Ahorro)'}
              </span>
            )}
          </div>
        )}

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          {allColumns.length > 0 && (
            <button
              type="button"
              className={`btn ${showGlobalSchema ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => setShowGlobalSchema((prev) => !prev)}
              aria-expanded={showGlobalSchema}
              aria-controls="global-schema-preview"
              data-testid="preview-global-schema-btn"
              title={t.plan.previewSchemaBtn || 'Previsualizar Esquema'}
            >
              <Columns size={16} />
              {showGlobalSchema
                ? (t.plan.hideSchemaBtn || 'Ocultar Esquema')
                : `${t.plan.previewSchemaBtn || 'Previsualizar Esquema'} (${allColumns.length})`}
            </button>
          )}

          <button
            className="btn btn-success"
            disabled={executing || approvedCount === 0}
            onClick={() => onExecutePlan(steps)}
            data-testid="execute-plan-btn"
          >
            <Play size={16} /> {executing ? t.plan.executingBtn : `${t.plan.executeBtn} (${approvedCount})`}
          </button>
        </div>
      </div>

      {/* Panel Global de Previsualización de Esquema de Columnas (Antes vs. Proyección ETL) */}
      {showGlobalSchema && (
        <div
          id="global-schema-preview"
          data-testid="global-schema-panel"
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
                <Table size={18} className="text-primary" />
                {t.plan.projectedSchemaTitle || 'Esquema Proyectado de Columnas (Antes vs. Después)'}
              </h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: '4px 0 0 0' }}>
                {t.plan.projectedSchemaDesc || 'Previsualiza cómo cada transformación aprobada modificará el esquema, tipos de datos y nombres antes de ejecutar.'}
              </p>
            </div>
            <div style={{ display: 'flex', gap: '8px', fontSize: '0.75rem', alignItems: 'center' }}>
              <span className="badge badge-emerald">{allColumns.length} columnas base</span>
              {hasNewClusterCol && (
                <span className="badge badge-purple" style={{ backgroundColor: 'rgba(168, 85, 247, 0.18)', color: '#a855f7' }}>
                  +1 columna proyectada (cluster)
                </span>
              )}
            </div>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.825rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '8px 10px' }}>{t.plan.colOriginal || 'Columna Original'}</th>
                  <th style={{ padding: '8px 10px' }}>{t.profiling?.colType || 'Tipo Inferido'}</th>
                  <th style={{ padding: '8px 10px' }}>{t.plan.colSamples || 'Muestras'}</th>
                  <th style={{ padding: '8px 10px' }}>{t.plan.colQuality || 'Calidad Inicial'}</th>
                  <th style={{ padding: '8px 10px' }}>{t.plan.colAppliedOps || 'Operaciones Aprobadas'}</th>
                  <th style={{ padding: '8px 10px' }}>{t.plan.colProjectedState || 'Estado Proyectado'}</th>
                </tr>
              </thead>
              <tbody>
                {allColumns.map((colName) => {
                  const profile = profiling?.columns?.find((c) => c.column_name === colName);
                  const colApprovedSteps = approvedSteps.filter(
                    (s) =>
                      s.column === colName ||
                      (s.operation === 'cluster_kmeans' &&
                        ((s.parameters?.columns as string[]) || []).includes(colName))
                  );
                  const isDropped = colApprovedSteps.some((s) => s.operation === 'drop_column');
                  const renameStep = colApprovedSteps.find((s) => s.operation === 'rename_column');
                  const newName = renameStep?.parameters?.new_name as string | undefined;

                  return (
                    <tr
                      key={colName}
                      style={{
                        borderBottom: '1px solid var(--border-color)',
                        opacity: isDropped ? 0.6 : 1,
                        backgroundColor: isDropped ? 'rgba(244, 63, 94, 0.05)' : 'transparent',
                      }}
                    >
                      <td style={{ padding: '8px 10px', fontWeight: 600 }}>
                        <span style={{ textDecoration: isDropped ? 'line-through' : 'none' }}>{colName}</span>
                      </td>
                      <td style={{ padding: '8px 10px' }}>
                        <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                          <span className="badge badge-blue">{profile?.inferred_type || 'desconocido'}</span>
                          {profile?.semantic_hint && profile.semantic_hint !== 'unknown' && (
                            <span className="badge badge-amber">{profile.semantic_hint}</span>
                          )}
                        </div>
                      </td>
                      <td
                        style={{
                          padding: '8px 10px',
                          color: 'var(--text-muted)',
                          maxWidth: '180px',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {profile?.sample_values && profile.sample_values.length > 0
                          ? profile.sample_values.slice(0, 3).map((v) => String(v ?? '')).join(', ')
                          : '—'}
                      </td>
                      <td style={{ padding: '8px 10px', color: 'var(--text-muted)' }}>
                        {profile ? (
                          <span>
                            {profile.null_count} nulos ({profile.null_percentage.toFixed(0)}%) · {profile.unique_count} unq
                          </span>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td style={{ padding: '8px 10px' }}>
                        {colApprovedSteps.length > 0 ? (
                          <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                            {colApprovedSteps.map((s) => (
                              <span key={s.step_id} className="badge badge-emerald" title={s.reason}>
                                {s.operation}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span style={{ color: 'var(--text-muted)' }}>—</span>
                        )}
                      </td>
                      <td style={{ padding: '8px 10px' }}>
                        {isDropped ? (
                          <span className="badge badge-rose">{t.plan.stateDropped || 'Eliminada'}</span>
                        ) : newName ? (
                          <span className="badge badge-amber" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                            <span>{t.plan.stateRenamed || 'Renombrada'}</span>
                            <ArrowRight size={12} />
                            <strong>{newName}</strong>
                          </span>
                        ) : colApprovedSteps.length > 0 ? (
                          <span className="badge badge-blue">
                            {t.plan.stateModified || 'Modificada'} ({colApprovedSteps.length})
                          </span>
                        ) : (
                          <span className="badge badge-emerald">{t.plan.stateUnchanged || 'Sin cambios'}</span>
                        )}
                      </td>
                    </tr>
                  );
                })}

                {hasNewClusterCol && (
                  <tr
                    style={{
                      borderBottom: '1px solid var(--border-color)',
                      backgroundColor: 'rgba(168, 85, 247, 0.08)',
                    }}
                  >
                    <td style={{ padding: '8px 10px', fontWeight: 600, color: '#a855f7' }}>
                      cluster <span style={{ fontSize: '0.75rem' }}>(nueva)</span>
                    </td>
                    <td style={{ padding: '8px 10px' }}>
                      <span className="badge badge-blue">numeric (int)</span>
                    </td>
                    <td style={{ padding: '8px 10px', color: 'var(--text-muted)' }}>0, 1, 2...</td>
                    <td style={{ padding: '8px 10px', color: 'var(--text-muted)' }}>0 nulos · segmentación K-Means</td>
                    <td style={{ padding: '8px 10px' }}>
                      <span className="badge badge-emerald">cluster_kmeans</span>
                    </td>
                    <td style={{ padding: '8px 10px' }}>
                      <span
                        className="badge badge-purple"
                        style={{ backgroundColor: 'rgba(168, 85, 247, 0.2)', color: '#a855f7' }}
                      >
                        {t.plan.stateNew || 'Nueva Columna'}
                      </span>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {plan.warnings && plan.warnings.length > 0 && (
        <div
          style={{
            backgroundColor: 'rgba(245, 158, 11, 0.08)',
            border: '1px solid rgba(245, 158, 11, 0.35)',
            borderRadius: '10px',
            padding: '12px 16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
          }}
        >
          {plan.warnings.map((warning, index) => (
            <p
              key={index}
              style={{ fontSize: '0.85rem', color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              <ShieldAlert size={15} style={{ color: '#f59e0b', flexShrink: 0 }} /> {warning}
            </p>
          ))}
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {steps.map((step) => {
          const isApproved = step.status !== 'rejected';
          const isPreviewingThisStep = previewStepId === step.step_id;
          const stepColProfile = step.column
            ? profiling?.columns?.find((c) => c.column_name === step.column)
            : null;

          return (
            <div
              key={step.step_id}
              style={{
                backgroundColor: 'var(--bg-input)',
                border: `1px solid ${isApproved ? 'var(--border-color)' : 'rgba(244, 63, 94, 0.3)'}`,
                borderRadius: '10px',
                padding: '16px 20px',
                opacity: isApproved ? 1 : 0.6,
                transition: 'all 0.2s ease',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px', flexWrap: 'wrap', gap: '10px' }}>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
                  <span className="badge badge-blue">{step.step_id}</span>
                  <span className="badge badge-emerald">{step.operation}</span>
                  {step.column && <span className="badge badge-amber">Columna: {step.column}</span>}
                  <span
                    className={`badge ${
                      step.risk === 'high' ? 'badge-rose' : step.risk === 'medium' ? 'badge-amber' : 'badge-emerald'
                    }`}
                  >
                    Riesgo {step.risk}
                  </span>

                  {/* Botón de Previsualización de Esquema de la Columna Afectada */}
                  {step.column && (
                    <button
                      type="button"
                      className="btn btn-outline"
                      style={{
                        padding: '3px 8px',
                        fontSize: '0.725rem',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        height: 'auto',
                        borderRadius: '6px',
                        borderColor: isPreviewingThisStep ? 'var(--primary)' : 'var(--border-color)',
                        color: isPreviewingThisStep ? 'var(--primary)' : 'var(--text-main)',
                      }}
                      onClick={() => setPreviewStepId(isPreviewingThisStep ? null : step.step_id)}
                      aria-expanded={isPreviewingThisStep}
                      data-testid={`preview-col-btn-${step.step_id}`}
                      title={
                        isPreviewingThisStep
                          ? (t.plan.hideColPreview || 'Ocultar esquema')
                          : (t.plan.viewColPreview || 'Ver esquema de columna')
                      }
                    >
                      {isPreviewingThisStep ? <EyeOff size={12} /> : <Eye size={12} />}
                      <span>
                        {isPreviewingThisStep
                          ? (t.plan.hideColPreview || 'Ocultar esquema')
                          : (t.plan.viewColPreview || 'Ver esquema de columna')}
                      </span>
                    </button>
                  )}
                </div>

                <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
                  <button
                    className={`btn ${isApproved ? 'btn-primary' : 'btn-outline'}`}
                    style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                    onClick={() => toggleStepStatus(step.step_id, 'approved')}
                  >
                    <CheckCircle2 size={14} /> {t.plan.approveBtn}
                  </button>
                  <button
                    className={`btn ${!isApproved ? 'btn-outline' : 'btn-outline'}`}
                    style={{
                      padding: '6px 12px',
                      fontSize: '0.8rem',
                      color: !isApproved ? 'var(--accent-rose)' : undefined,
                      borderColor: !isApproved ? 'var(--accent-rose)' : undefined,
                    }}
                    onClick={() => toggleStepStatus(step.step_id, 'rejected')}
                  >
                    <XCircle size={14} /> {t.plan.rejectBtn}
                  </button>
                </div>
              </div>

              <p style={{ fontSize: '0.875rem', color: 'var(--text-main)', margin: '8px 0', lineHeight: 1.5 }}>
                <strong>{t.plan.reason}:</strong> {step.reason}
              </p>

              <div style={{ display: 'flex', gap: '12px', fontSize: '0.8rem', color: 'var(--text-muted)', flexWrap: 'wrap', marginTop: '8px' }}>
                <span>{t.plan.confidence}: {(step.confidence * 100).toFixed(0)}%</span>
                <span>{t.plan.estimatedRows}: {step.affected_rows_estimate}</span>
                <span style={{ wordBreak: 'break-word' }}>
                  {t.plan.parameters}: <code style={{ color: 'var(--primary)' }}>{JSON.stringify(step.parameters)}</code>
                </span>
              </div>

              {/* Visor Contextual del Esquema de la Columna Afectada */}
              {isPreviewingThisStep && step.column && (
                <div
                  data-testid={`col-schema-details-${step.step_id}`}
                  style={{
                    marginTop: '12px',
                    padding: '12px 14px',
                    backgroundColor: 'var(--bg-main)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px',
                    fontSize: '0.8rem',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: 'var(--primary)' }}>
                      <Columns size={14} />
                      <span>{t.plan.schemaDetails || 'Detalles del Esquema'}: {step.column}</span>
                    </div>
                    {stepColProfile && (
                      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                        <span className="badge badge-blue">{stepColProfile.inferred_type}</span>
                        {stepColProfile.semantic_hint && stepColProfile.semantic_hint !== 'unknown' && (
                          <span className="badge badge-amber">{stepColProfile.semantic_hint}</span>
                        )}
                      </div>
                    )}
                  </div>

                  {stepColProfile ? (
                    <>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '8px', color: 'var(--text-muted)' }}>
                        <div>
                          <strong>Nulos:</strong> {stepColProfile.null_count} ({stepColProfile.null_percentage.toFixed(1)}%)
                        </div>
                        <div>
                          <strong>Únicos:</strong> {stepColProfile.unique_count}
                        </div>
                        {stepColProfile.min_value !== undefined && (
                          <div>
                            <strong>Mín:</strong> {stepColProfile.min_value}
                          </div>
                        )}
                        {stepColProfile.max_value !== undefined && (
                          <div>
                            <strong>Máx:</strong> {stepColProfile.max_value}
                          </div>
                        )}
                      </div>

                      {stepColProfile.sample_values && stepColProfile.sample_values.length > 0 && (
                        <div>
                          <span style={{ color: 'var(--text-muted)', display: 'block', marginBottom: '4px', fontSize: '0.75rem' }}>
                            {t.plan.colSamples || 'Valores de muestra (antes de transformación):'}
                          </span>
                          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                            {stepColProfile.sample_values.slice(0, 5).map((val, idx) => (
                              <code
                                key={idx}
                                style={{
                                  backgroundColor: 'var(--bg-input)',
                                  padding: '2px 6px',
                                  borderRadius: '4px',
                                  fontSize: '0.75rem',
                                  border: '1px solid var(--border-color)',
                                  color: 'var(--text-main)',
                                }}
                              >
                                {String(val ?? 'null')}
                              </code>
                            ))}
                          </div>
                        </div>
                      )}

                      {stepColProfile.warnings && stepColProfile.warnings.length > 0 && (
                        <div style={{ color: '#f59e0b', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <ShieldAlert size={12} /> {stepColProfile.warnings.join(' · ')}
                        </div>
                      )}
                    </>
                  ) : (
                    <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.775rem' }}>
                      Información detallada de perfilado no disponible para esta columna.
                    </p>
                  )}
                </div>
              )}

              {/* Advertencia interactiva de Protección de Datos */}
              {step.data_loss_warning && (
                <div
                  style={{
                    marginTop: '12px',
                    padding: '12px 14px',
                    borderRadius: '8px',
                    backgroundColor: 'rgba(244, 63, 94, 0.1)',
                    border: '1px solid rgba(244, 63, 94, 0.35)',
                    color: 'var(--text-main)',
                    fontSize: '0.85rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-rose)', fontWeight: 600 }}>
                    <AlertTriangle size={16} />
                    <span>Aviso de Protección de Datos: Posible Descarte Irreversible de Texto</span>
                  </div>
                  <p style={{ margin: 0, fontSize: '0.825rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>
                    {step.data_loss_warning}
                  </p>
                  <div style={{ marginTop: '4px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem' }}>
                    <input
                      type="checkbox"
                      id={`ack-${step.step_id}`}
                      checked={step.parameters?.confirmed_data_loss === true}
                      onChange={(e) => {
                        handleParameterChange(step.step_id, 'confirmed_data_loss', e.target.checked);
                      }}
                      style={{ cursor: 'pointer', accentColor: 'var(--accent-rose)' }}
                    />
                    <label htmlFor={`ack-${step.step_id}`} style={{ cursor: 'pointer', color: 'var(--text-main)' }}>
                      He revisado esta columna y confirmo la transformación aunque descarte texto libre no parseable.
                    </label>
                  </div>
                </div>
              )}

              {/* Panel de Feature Selection para K-Means */}
              {step.operation === 'cluster_kmeans' && (
                <div
                  style={{
                    marginTop: '14px',
                    padding: '14px 16px',
                    backgroundColor: 'var(--bg-main)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                  }}
                >
                  <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--primary)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Sliders size={15} /> {t.clusteringConfig?.title || 'Configuración de Segmentación K-Means'}
                  </h4>

                  {/* Selector de Columnas */}
                  <div style={{ marginBottom: '10px' }}>
                    <label style={{ fontSize: '0.775rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                      {t.clusteringConfig?.selectNumericCols || 'Variables numéricas a incluir:'}
                    </label>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                      {Array.from(
                        new Set([
                          ...((step.parameters.columns as string[]) || []),
                          ...steps.map((s) => s.column).filter((c): c is string => Boolean(c)),
                        ])
                      ).map((colName) => {
                        const activeCols = (step.parameters.columns as string[]) || [];
                        const isSelected = activeCols.includes(colName);
                        return (
                          <label
                            key={colName}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '6px',
                              padding: '4px 10px',
                              borderRadius: '6px',
                              backgroundColor: isSelected ? 'rgba(59, 130, 246, 0.15)' : 'var(--bg-input)',
                              border: `1px solid ${isSelected ? 'var(--primary)' : 'var(--border-color)'}`,
                              cursor: 'pointer',
                              fontSize: '0.775rem',
                              fontWeight: isSelected ? 600 : 400,
                            }}
                          >
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={(e) => {
                                const newCols = e.target.checked
                                  ? [...activeCols, colName]
                                  : activeCols.filter((c) => c !== colName);
                                setSteps((prev) =>
                                  prev.map((s) =>
                                    s.step_id === step.step_id
                                      ? { ...s, parameters: { ...s.parameters, columns: newCols } }
                                      : s
                                  )
                                );
                              }}
                            />
                            {colName}
                          </label>
                        );
                      })}
                    </div>
                  </div>

                  {/* Número de Clusters K y Opciones */}
                  <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <label style={{ fontSize: '0.775rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                        {t.clusteringConfig?.kClusters || 'Clusters (K):'}
                      </label>
                      <input
                        type="number"
                        min={2}
                        max={10}
                        value={(step.parameters.n_clusters as number) || 3}
                        onChange={(e) => {
                          const kVal = Math.max(2, Math.min(10, parseInt(e.target.value, 10) || 3));
                          setSteps((prev) =>
                            prev.map((s) =>
                              s.step_id === step.step_id
                                ? { ...s, parameters: { ...s.parameters, n_clusters: kVal } }
                                : s
                            )
                          );
                        }}
                        style={{
                          width: '60px',
                          padding: '4px 8px',
                          borderRadius: '4px',
                          border: '1px solid var(--border-color)',
                          backgroundColor: 'var(--bg-input)',
                          color: 'var(--text-main)',
                          fontSize: '0.8rem',
                        }}
                      />
                    </div>

                    <label style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.775rem', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={Boolean(step.parameters.scale_features ?? true)}
                        onChange={(e) => {
                          const scale = e.target.checked;
                          setSteps((prev) =>
                            prev.map((s) =>
                              s.step_id === step.step_id
                                ? { ...s, parameters: { ...s.parameters, scale_features: scale } }
                                : s
                            )
                          );
                        }}
                      />
                      {t.clusteringConfig?.scaleFeatures || 'Escalado Z-Score estándar'}
                    </label>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
