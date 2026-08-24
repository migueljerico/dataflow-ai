import React, { useState } from 'react';
import { CheckCircle2, XCircle, Play, ShieldAlert, Sliders, Sparkles } from 'lucide-react';
import { TransformationPlan, TransformationStep } from '../types';

interface Props {
  plan: TransformationPlan;
  onExecutePlan: (approvedSteps: TransformationStep[]) => void;
  executing: boolean;
}

export const PlanReview: React.FC<Props> = ({ plan, onExecutePlan, executing }) => {
  const [steps, setSteps] = useState<TransformationStep[]>(plan.steps);

  const toggleStepStatus = (stepId: string, newStatus: 'approved' | 'rejected') => {
    setSteps((prev) =>
      prev.map((s) => (s.step_id === stepId ? { ...s, status: newStatus } : s))
    );
  };

  const approvedCount = steps.filter((s) => s.status !== 'rejected').length;

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2 className="card-title">
            <Sliders size={20} className="text-primary" /> Revisión Humana del Plan ETL (Human-in-the-Loop)
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '4px' }}>
            Origen: <strong style={{ color: 'var(--primary)' }}>{plan.source}</strong> | Resumen: {plan.summary}
          </p>
        </div>
        <button
          className="btn btn-success"
          disabled={executing || approvedCount === 0}
          onClick={() => onExecutePlan(steps)}
        >
          <Play size={16} /> {executing ? 'Ejecutando en Python...' : `Ejecutar Plan (${approvedCount} Pasos)`}
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
                    <CheckCircle2 size={14} /> Aprobar
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
                    <XCircle size={14} /> Rechazar
                  </button>
                </div>
              </div>

              <p style={{ fontSize: '0.875rem', color: 'var(--text-main)', margin: '8px 0', lineHeight: 1.5 }}>
                <strong>Motivo:</strong> {step.reason}
              </p>

              <div style={{ display: 'flex', gap: '12px', fontSize: '0.8rem', color: 'var(--text-muted)', flexWrap: 'wrap', marginTop: '8px' }}>
                <span>Confianza IA/Reglas: {(step.confidence * 100).toFixed(0)}%</span>
                <span>Filas estimadas: {step.affected_rows_estimate}</span>
                <span style={{ wordBreak: 'break-word' }}>Parámetros: <code style={{ color: 'var(--primary)' }}>{JSON.stringify(step.parameters)}</code></span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
