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
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                <div>
                  <span className="badge badge-blue" style={{ marginRight: '8px' }}>{step.step_id}</span>
                  <span className="badge badge-emerald" style={{ marginRight: '8px' }}>{step.operation}</span>
                  {step.column && <span className="badge badge-amber">Columna: {step.column}</span>}
                  <span
                    className={`badge ${
                      step.risk === 'high' ? 'badge-rose' : step.risk === 'medium' ? 'badge-amber' : 'badge-emerald'
                    }`}
                    style={{ marginLeft: '8px' }}
                  >
                    Riesgo {step.risk}
                  </span>
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
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

              <p style={{ fontSize: '0.9rem', color: 'var(--text-main)', margin: '8px 0' }}>
                <strong>Motivo:</strong> {step.reason}
              </p>

              <div style={{ display: 'flex', gap: '16px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                <span>Confianza IA/Reglas: {(step.confidence * 100).toFixed(0)}%</span>
                <span>Filas estimadas: {step.affected_rows_estimate}</span>
                <span>Parámetros: <code style={{ color: 'var(--primary)' }}>{JSON.stringify(step.parameters)}</code></span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
