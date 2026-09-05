import React, { useState, useCallback } from 'react';
import { Header } from './components/Header';
import { FileUpload } from './components/FileUpload';
import { ProfilingDashboard } from './components/ProfilingDashboard';
import { PlanReview } from './components/PlanReview';
import { ExecutionReport } from './components/ExecutionReport';
import { ToastContainer, ToastItem } from './components/Toast';
import { ErrorBoundary } from './components/ErrorBoundary';
import { LanguageProvider, useLanguage } from './context/LanguageContext';
import { api } from './services/api';
import {
  DatasetMetadata, ProfilingReport, QualityReport, TransformationPlan, TransformationStep, ExecutionResult,
  MultiTableStarSchema
} from './types';
import { MultiTableStarSchemaViewer } from './components/MultiTableStarSchema';
import { Network, Layers, RefreshCw, Sparkles } from 'lucide-react';

function toErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof Error && err.message) return err.message;
  if (typeof err === 'string') return err;
  return fallback;
}

const AppContent: React.FC = () => {
  const { t } = useLanguage();
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

  // Multi-table Star Schema state
  const [workspaceDatasets, setWorkspaceDatasets] = useState<DatasetMetadata[]>([]);
  const [starSchema, setStarSchema] = useState<MultiTableStarSchema | null>(null);
  const [viewMode, setViewMode] = useState<'single' | 'star-schema'>('single');
  const [loadingStarSchema, setLoadingStarSchema] = useState<boolean>(false);

  const pushToast = useCallback((message: string, kind: ToastItem['kind'] = 'error') => {
    const id = Math.random().toString(36).slice(2, 9);
    setToasts((prev) => [...prev, { id, kind, message }]);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const handleUploadSuccess = async (meta: DatasetMetadata) => {
    setMetadata(meta);
    setWorkspaceDatasets([meta]);
    setViewMode('single');
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
      pushToast(toErrorMessage(err, t.errors.fetchProfiling));
    } finally {
      setLoading(false);
    }
  };

  const handleBatchUploadSuccess = async (datasets: DatasetMetadata[]) => {
    setWorkspaceDatasets(datasets);
    if (datasets.length === 1) {
      await handleUploadSuccess(datasets[0]);
      return;
    }

    setLoadingStarSchema(true);
    setViewMode('star-schema');
    try {
      const schema = await api.generateStarSchema(datasets.map((d) => d.dataset_id));
      setStarSchema(schema);

      // Pre-seleccionar tabla de hechos o primera tabla para profiling individual
      const factMeta =
        datasets.find((d) => d.filename.toLowerCase().includes(schema.fact_table.table_name.toLowerCase())) ||
        datasets[0];
      setMetadata(factMeta);

      // Precargar profiling de la tabla preseleccionada
      api.getProfilingReport(factMeta.dataset_id).then((p) => setProfiling(p)).catch(() => {});
      api.getQualityReport(factMeta.dataset_id).then((q) => setQuality(q)).catch(() => {});
      setStep(2);
    } catch (err: unknown) {
      pushToast(toErrorMessage(err, 'Error al generar el esquema en estrella del lote.'), 'error');
    } finally {
      setLoadingStarSchema(false);
    }
  };

  const handleRefreshStarSchema = async () => {
    if (workspaceDatasets.length === 0) return;
    setLoadingStarSchema(true);
    try {
      const schema = await api.generateStarSchema(workspaceDatasets.map((d) => d.dataset_id));
      setStarSchema(schema);
      setViewMode('star-schema');
      pushToast('Esquema en estrella e integridad referencial actualizados.', 'success');
    } catch (err: unknown) {
      pushToast(toErrorMessage(err, 'Error al recalcular el esquema en estrella.'), 'error');
    } finally {
      setLoadingStarSchema(false);
    }
  };

  const handleSelectWorkspaceTable = async (datasetId: string) => {
    const ds = workspaceDatasets.find((d) => d.dataset_id === datasetId);
    if (!ds) return;
    setMetadata(ds);
    setPlan(null);
    setExecutionResult(null);
    setReportBeforeAfter(null);
    setLoading(true);
    setViewMode('single');
    try {
      const [profRes, qualRes] = await Promise.all([
        api.getProfilingReport(ds.dataset_id),
        api.getQualityReport(ds.dataset_id)
      ]);
      setProfiling(profRes);
      setQuality(qualRes);
      setStep(2);
    } catch (err: unknown) {
      pushToast(toErrorMessage(err, t.errors.fetchProfiling));
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
      pushToast(toErrorMessage(err, t.errors.generatePlan));
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

      // Si tenemos un espacio multi-tabla, recalcular el esquema en estrella en segundo plano
      if (workspaceDatasets.length > 1) {
        api.generateStarSchema(workspaceDatasets.map((d) => d.dataset_id))
          .then((updatedSchema) => setStarSchema(updatedSchema))
          .catch(() => {});
      }
    } catch (err: unknown) {
      pushToast(toErrorMessage(err, t.errors.executePlan));
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
    setWorkspaceDatasets([]);
    setStarSchema(null);
    setViewMode('single');
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-main)' }}>
      <Header />

      <main className="container">
        {/* Barra superior del espacio multi-tabla */}
        {workspaceDatasets.length > 1 && (
          <div
            className="card"
            style={{
              marginBottom: '20px',
              padding: '12px 18px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '12px',
              background: 'linear-gradient(135deg, rgba(14, 165, 233, 0.08), rgba(19, 27, 42, 0.95))',
              border: '1px solid var(--primary)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div
                style={{
                  width: 34,
                  height: 34,
                  borderRadius: 8,
                  background: 'var(--primary-light)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--primary)',
                }}
              >
                <Network size={18} />
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span>Espacio Multi-Tabla</span>
                  <span
                    style={{
                      fontSize: '0.75rem',
                      padding: '2px 8px',
                      borderRadius: '12px',
                      background: 'var(--primary)',
                      color: 'white',
                      fontWeight: 600,
                    }}
                  >
                    {workspaceDatasets.length} tablas
                  </span>
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Modelo relacional y limpieza ETL integral
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <button
                type="button"
                className={`btn ${viewMode === 'star-schema' ? 'btn-primary' : 'btn-outline'}`}
                style={{ fontSize: '0.85rem', padding: '6px 14px' }}
                onClick={() => setViewMode('star-schema')}
              >
                <Network size={15} />
                <span>Esquema Estrella</span>
              </button>

              <button
                type="button"
                className={`btn ${viewMode === 'single' ? 'btn-primary' : 'btn-outline'}`}
                style={{ fontSize: '0.85rem', padding: '6px 14px' }}
                onClick={() => setViewMode('single')}
              >
                <Layers size={15} />
                <span>Limpieza por Tabla</span>
              </button>

              {viewMode === 'single' && (
                <select
                  value={metadata?.dataset_id || ''}
                  onChange={(e) => handleSelectWorkspaceTable(e.target.value)}
                  style={{
                    padding: '6px 12px',
                    borderRadius: '6px',
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border-color)',
                    color: 'var(--text-main)',
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                  }}
                  aria-label="Seleccionar tabla del espacio de trabajo"
                >
                  {workspaceDatasets.map((ds) => (
                    <option key={ds.dataset_id} value={ds.dataset_id}>
                      {ds.filename} ({ds.row_count} filas)
                    </option>
                  ))}
                </select>
              )}

              <button
                type="button"
                className="btn btn-outline"
                style={{ fontSize: '0.85rem', padding: '6px 12px' }}
                onClick={handleRefreshStarSchema}
                disabled={loadingStarSchema}
                title="Recalcular modelo relacional e integridad"
              >
                <RefreshCw size={14} className={loadingStarSchema ? 'spin' : ''} />
                <span>Recalcular</span>
              </button>

              <button
                type="button"
                className="btn btn-outline"
                style={{ fontSize: '0.85rem', padding: '6px 12px', color: 'var(--text-muted)' }}
                onClick={handleResetSession}
                title="Reiniciar y subir otros archivos"
              >
                Nuevo
              </button>
            </div>
          </div>
        )}

        {viewMode === 'star-schema' ? (
          loadingStarSchema ? (
            <div className="card" style={{ padding: '60px 20px', textAlign: 'center' }}>
              <RefreshCw size={36} className="text-primary spin" style={{ margin: '0 auto 16px auto' }} />
              <h3 style={{ fontSize: '1.2rem', marginBottom: '8px' }}>Generando Esquema de Estrella</h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                Identificando hechos, dimensiones, claves foráneas y evaluando integridad referencial...
              </p>
            </div>
          ) : starSchema ? (
            <MultiTableStarSchemaViewer
              schema={starSchema}
              onBackToDatasets={() => setViewMode('single')}
            />
          ) : (
            <div className="card" style={{ padding: '40px 20px', textAlign: 'center' }}>
              <p style={{ color: 'var(--text-muted)', marginBottom: '16px' }}>
                No se ha generado el modelo relacional todavía.
              </p>
              <button type="button" className="btn btn-primary" onClick={handleRefreshStarSchema}>
                Generar Esquema de Estrella
              </button>
            </div>
          )
        ) : (
          <>
            <nav className="stepper" aria-label="Progreso del flujo / Workflow progress">
              <div className={`step-item ${step === 1 ? 'active' : step > 1 ? 'completed' : ''}`} aria-current={step === 1 ? 'step' : undefined}>
                <div className="step-num">1</div>
                <span>{t.stepper.step1}</span>
              </div>
              <div className={`step-item ${step === 2 ? 'active' : step > 2 ? 'completed' : ''}`} aria-current={step === 2 ? 'step' : undefined}>
                <div className="step-num">2</div>
                <span>{t.stepper.step2}</span>
              </div>
              <div className={`step-item ${step === 3 ? 'active' : step > 3 ? 'completed' : ''}`} aria-current={step === 3 ? 'step' : undefined}>
                <div className="step-num">3</div>
                <span>{t.stepper.step3}</span>
              </div>
              <div className={`step-item ${step === 4 ? 'active' : ''}`} aria-current={step === 4 ? 'step' : undefined}>
                <div className="step-num">4</div>
                <span>{t.stepper.step4}</span>
              </div>
            </nav>

            <ErrorBoundary>
              {step === 1 && (
                <FileUpload
                  onUploadSuccess={handleUploadSuccess}
                  onBatchUploadSuccess={handleBatchUploadSuccess}
                />
              )}
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
                  metadata={metadata}
                  profiling={profiling}
                />
              )}
              {step === 4 && executionResult && (
                <>
                  {workspaceDatasets.length > 1 && (
                    <div
                      className="card"
                      style={{
                        marginBottom: '16px',
                        padding: '14px 20px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        background: 'rgba(16, 185, 129, 0.08)',
                        border: '1px solid var(--accent-emerald)',
                        borderRadius: '8px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <Sparkles size={20} style={{ color: 'var(--accent-emerald)' }} />
                        <div>
                          <strong style={{ color: 'var(--text-main)', fontSize: '0.95rem' }}>
                            ¡Tabla limpia con éxito!
                          </strong>
                          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                            El esquema de estrella ha sido actualizado con los datos limpios.
                          </div>
                        </div>
                      </div>
                      <button
                        type="button"
                        className="btn btn-primary"
                        style={{ fontSize: '0.85rem', padding: '6px 14px' }}
                        onClick={() => setViewMode('star-schema')}
                      >
                        <Network size={15} />
                        <span>Ver Esquema de Estrella</span>
                      </button>
                    </div>
                  )}
                  <ExecutionReport
                    result={executionResult}
                    reportBeforeAfter={reportBeforeAfter}
                    onResetSession={handleResetSession}
                  />
                </>
              )}
            </ErrorBoundary>
          </>
        )}
      </main>
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <LanguageProvider>
      <AppContent />
    </LanguageProvider>
  );
};

export default App;

