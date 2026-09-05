import React, { useState } from 'react';
import { Sparkles, CheckCircle2, ChevronDown, ChevronRight, AlertCircle, ShieldAlert } from 'lucide-react';
import { TransformationPlan, TransformationStep } from '../../types';

export interface BatchPlanItem {
  datasetId: string;
  filename: string;
  plan: TransformationPlan;
}

interface Props {
  batchPlans: BatchPlanItem[];
  onExecuteAllPlans: () => void;
  executing: boolean;
}

export const BatchPlanReview: React.FC<Props> = ({
  batchPlans,
  onExecuteAllPlans,
  executing,
}) => {
  const [expandedTables, setExpandedTables] = useState<Record<string, boolean>>(() => {
    // Expand all by default
    const initial: Record<string, boolean> = {};
    batchPlans.forEach((bp) => {
      initial[bp.datasetId] = true;
    });
    return initial;
  });

  const toggleTable = (datasetId: string) => {
    setExpandedTables((prev) => ({
      ...prev,
      [datasetId]: !prev[datasetId],
    }));
  };

  const totalSteps = batchPlans.reduce((acc, bp) => acc + bp.plan.steps.length, 0);

  const getRiskBadge = (risk: string) => {
    if (risk === 'high') return <span className="badge badge-rose">Alto</span>;
    if (risk === 'medium') return <span className="badge badge-amber">Medio</span>;
    return <span className="badge badge-emerald">Bajo</span>;
  };

  return (
    <div>
      {/* Banner de Resumen del Plan */}
      <div className="card" style={{ marginBottom: '24px', padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.3rem', fontWeight: 800, marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sparkles size={20} className="text-primary" /> Plan de Transformación Integral — {batchPlans.length} Tablas
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', margin: 0 }}>
              Se propone un total de <strong>{totalSteps} pasos de limpieza</strong> ejecutables para sanear todas las
              tablas del modelo de datos de una sola vez.
            </p>
          </div>

          <button
            type="button"
            className="btn btn-success"
            onClick={onExecuteAllPlans}
            disabled={executing || totalSteps === 0}
            style={{ padding: '12px 28px', fontSize: '1rem', fontWeight: 700, minWidth: '260px' }}
          >
            <CheckCircle2 size={18} />
            <span>{executing ? 'Limpiando todas las tablas...' : `Aprobar y Limpiar Todas (${totalSteps} pasos)`}</span>
          </button>
        </div>
      </div>

      {/* Lista de tablas con sus pasos desplegables */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '24px' }}>
        {batchPlans.map(({ datasetId, filename, plan }) => {
          const isExpanded = expandedTables[datasetId] ?? true;
          return (
            <div key={datasetId} className="card" style={{ padding: '0', overflow: 'hidden' }}>
              <div
                onClick={() => toggleTable(datasetId)}
                style={{
                  padding: '14px 20px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  cursor: 'pointer',
                  backgroundColor: 'var(--bg-input)',
                  borderBottom: isExpanded ? '1px solid var(--border-color)' : 'none',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  {isExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                  <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>{filename}</span>
                  <span className="badge badge-blue">{plan.steps.length} pasos</span>
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {plan.summary || 'Plan generado automáticamente'}
                </div>
              </div>

              {isExpanded && (
                <div style={{ padding: '16px 20px' }}>
                  {plan.steps.length === 0 ? (
                    <div style={{ color: 'var(--accent-emerald)', fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <CheckCircle2 size={16} /> Esta tabla no contiene anomalías detectadas; ya está limpia.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {plan.steps.map((step: TransformationStep, idx: number) => (
                        <div
                          key={step.step_id || idx}
                          style={{
                            padding: '12px 14px',
                            backgroundColor: 'var(--bg-main)',
                            borderRadius: '8px',
                            border: '1px solid var(--border-color)',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            flexWrap: 'wrap',
                            gap: '10px',
                          }}
                        >
                          <div style={{ flex: 1, minWidth: '240px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                              <span style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--primary)' }}>
                                #{idx + 1} {step.operation}
                              </span>
                              {step.column && (
                                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                                  en <code>{step.column}</code>
                                </span>
                              )}
                              {getRiskBadge(step.risk)}
                            </div>
                            <div style={{ fontSize: '0.825rem', color: 'var(--text-main)' }}>
                              {step.reason}
                            </div>
                          </div>
                          {step.affected_rows_estimate !== undefined && step.affected_rows_estimate > 0 && (
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textAlign: 'right' }}>
                              Afecta ~{step.affected_rows_estimate} filas
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Botón inferior de aprobación de todo el lote */}
      <div className="card" style={{ textAlign: 'center', padding: '20px' }}>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: '16px' }}>
          Principio Fundamental de Gobierno: <em>La IA propone. El usuario decide con el botón. Python ejecuta de forma determinista.</em>
        </p>
        <button
          type="button"
          className="btn btn-success"
          onClick={onExecuteAllPlans}
          disabled={executing || totalSteps === 0}
          style={{ padding: '12px 32px', fontSize: '1.05rem', fontWeight: 700 }}
        >
          <CheckCircle2 size={20} />
          <span>{executing ? 'Limpiando todas las tablas en lote...' : `Aprobar y Ejecutar Limpieza (${totalSteps} pasos)`}</span>
        </button>
      </div>
    </div>
  );
};
