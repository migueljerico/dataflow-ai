import React, { useState, useEffect } from 'react';
import { CheckCircle2, XCircle, Play, ShieldAlert, Sliders, Sparkles, AlertTriangle } from 'lucide-react';
import { TransformationPlan, TransformationStep } from '../types';
import { useLanguage } from '../context/LanguageContext';

interface Props {
  plan: TransformationPlan;
  onExecutePlan: (approvedSteps: TransformationStep[]) => void;
  executing: boolean;
}

export const PlanReview: React.FC<Props> = ({ plan, onExecutePlan, executing }) => {
  const { t } = useLanguage();
  const [steps, setSteps] = useState<TransformationStep[]>(plan.steps);
  useEffect(() => { setSteps(plan.steps); }, [plan.steps]);

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

  const approvedCount = steps.filter((s) => s.status !== 'rejected').length;

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2 className="card-title">
            <Sliders size={20} className="text-primary" /> {t.plan.title}
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '4px' }}>
            {t.plan.source}: <strong style={{ color: 'var(--primary)' }}>{plan.source}</strong> | {t.plan.summary}: {plan.summary}
          </p>
        </div>
        <button
          className="btn btn-success"
          disabled={executing || approvedCount === 0}
          onClick={() => onExecutePlan(steps)}
        >
          <Play size={16} /> {executing ? t.plan.executingBtn : `${t.plan.executeBtn} (${approvedCount})`}
        </button>
      </div>


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
                <span style={{ wordBreak: 'break-word' }}>{t.plan.parameters}: <code style={{ color: 'var(--primary)' }}>{JSON.stringify(step.parameters)}</code></span>
              </div>

              {/* Advertencia interactiva de Protección de Datos (posible descarte de texto libre no recuperable) */}
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

