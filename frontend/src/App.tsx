import React, { useState, useCallback } from 'react';
import { Header } from './components/Header';
import { FileUpload } from './components/FileUpload';
import { ProfilingDashboard } from './components/ProfilingDashboard';
import { PlanReview } from './components/PlanReview';
import { ExecutionReport } from './components/ExecutionReport';
import { ToastContainer, ToastItem } from './components/Toast';
import { ErrorBoundary } from './components/ErrorBoundary';
import { api } from './services/api';
import {
  DatasetMetadata, ProfilingReport, QualityReport, TransformationPlan, TransformationStep, ExecutionResult
} from './types';

function toErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof Error && err.message) return err.message;
  if (typeof err === 'string') return err;
  return fallback;
}

export const App: React.FC = () => {
  const [step, setStep] = useState<number>(1);
  const [metadata, setMetadata] = useState<DatasetMetadata | null>(null);
  const [profiling, setProfiling] = useState<ProfilingReport | null>(null);
  const [quality, setQuality] = useState<QualityReport | null>(null);
  const [plan, setPlan] = useState<TransformationPlan | null>(null);
  const [executionResult, setExecutionResult] = useState<ExecutionResult | null>(null);
  const [reportBeforeAfter, setReportBeforeAfter] = useState<ExecutionResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [executing, setExecuting] = useState<boolean>(false);
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const pushToast = useCallback((message: string, kind: ToastItem['kind'] = 'error') => {
    const id = Math.random().toString(36).slice(2, 9);
    setToasts((prev) => [...prev, { id, kind, message }]);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const handleUploadSuccess = async (meta: DatasetMetadata) => {
    setMetadata(meta);
    setLoading(true);
    try {
      const [profRes, qualRes] = await Promise.all([
        api.getProfilingReport(meta.dataset_id),
        api.getQualityReport(meta.dataset_id)
      ]);
      setProfiling(profRes);
      setQuality(qualRes);
      setStep(2);
    } catch (err: unknown) {
      pushToast(toErrorMessage(err, 'Error al obtener profiling del dataset.'));
    } finally {
      setLoading(false);
    }
  };

  const handleGeneratePlan = async (provider: string = 'mock') => {
    if (!metadata) return;
    setLoading(true);
    try {
      let proposedPlan: TransformationPlan;
      if (provider === 'rules') {
        proposedPlan = await api.proposePlanFromRules(metadata.dataset_id);
      } else {
        proposedPlan = await api.proposeAIPlan(metadata.dataset_id, provider);
      }
      setPlan(proposedPlan);
      setStep(3);
    } catch (err: unknown) {
      pushToast(toErrorMessage(err, 'Error al generar plan de transformaciones.'));
    } finally {
      setLoading(false);
    }
  };

  const handleExecutePlan = async (approvedSteps: TransformationStep[]) => {
    if (!plan) return;
    setExecuting(true);
    try {
      const res = await api.approveAndExecutePlan(plan.plan_id, approvedSteps);
      const rep = await api.getRunQualityReport(res.run_id);
      setExecutionResult(res);
      setReportBeforeAfter(rep);
      setStep(4);
    } catch (err: unknown) {
      pushToast(toErrorMessage(err, 'Error al ejecutar plan ETL.'));
    } finally {
      setExecuting(false);
    }
  };

  const handleResetSession = () => {
    setStep(1);
    setMetadata(null);
    setProfiling(null);
    setQuality(null);
    setPlan(null);
    setExecutionResult(null);
    setReportBeforeAfter(null);
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-main)' }}>
      <Header />

      <main className="container">
        <nav className="stepper" aria-label="Progreso del flujo">
          <div className={`step-item ${step === 1 ? 'active' : step > 1 ? 'completed' : ''}`} aria-current={step === 1 ? 'step' : undefined}>
            <div className="step-num">1</div>
            <span>Subir Datos</span>
          </div>
          <div className={`step-item ${step === 2 ? 'active' : step > 2 ? 'completed' : ''}`} aria-current={step === 2 ? 'step' : undefined}>
            <div className="step-num">2</div>
            <span>Data Quality</span>
          </div>
          <div className={`step-item ${step === 3 ? 'active' : step > 3 ? 'completed' : ''}`} aria-current={step === 3 ? 'step' : undefined}>
            <div className="step-num">3</div>
            <span>Plan ETL & IA</span>
          </div>
          <div className={`step-item ${step === 4 ? 'active' : ''}`} aria-current={step === 4 ? 'step' : undefined}>
            <div className="step-num">4</div>
            <span>Resultados & Script</span>
          </div>
        </nav>

        <ErrorBoundary>
          {step === 1 && <FileUpload onUploadSuccess={handleUploadSuccess} />}
          {step === 2 && metadata && profiling && quality && (
            <ProfilingDashboard
              metadata={metadata}
              profiling={profiling}
              quality={quality}
              onGeneratePlan={handleGeneratePlan}
              loadingPlan={loading}
            />
          )}
          {step === 3 && plan && (
            <PlanReview
              plan={plan}
              onExecutePlan={handleExecutePlan}
              executing={executing}
            />
          )}
          {step === 4 && executionResult && (
            <ExecutionReport
              result={executionResult}
              reportBeforeAfter={reportBeforeAfter}
              onResetSession={handleResetSession}
            />
          )}
        </ErrorBoundary>
      </main>
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
};

export default App;
