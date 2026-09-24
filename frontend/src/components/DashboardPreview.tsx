import React, { useState } from 'react';
import {
  LayoutDashboard,
  TrendingUp,
  BarChart3,
  Palette,
  FileCode,
  CheckCircle2,
  AlertTriangle,
  Copy,
  Check,
  Download,
  History,
  Image,
  Pencil,
} from 'lucide-react';
import { DashboardBlueprint, DashboardBlueprintList } from '../types';
import { DashboardMockup } from './DashboardMockup';
import { DashboardEditor } from './DashboardEditor';
import { useLanguage } from '../context/LanguageContext';
import { api } from '../services/api';

interface Props {
  blueprint: DashboardBlueprint;
  onBackToStarSchema?: () => void;
  /** Notifica al flujo (Paso 5) cuando el usuario guarda una edición HITL. */
  onBlueprintUpdated?: (blueprint: DashboardBlueprint) => void;
  /** Notifica al flujo (Paso 5) cuando el usuario carga un blueprint del historial. */
  onBlueprintLoad?: (blueprint: DashboardBlueprint) => void;
}

export const DashboardPreview: React.FC<Props> = ({ blueprint, onBackToStarSchema, onBlueprintUpdated, onBlueprintLoad }) => {
  const { t } = useLanguage();
  const [copiedDax, setCopiedDax] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'example' | 'visuals' | 'design' | 'powerbi'>('example');
  const [draft, setDraft] = useState<DashboardBlueprint | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  // ── Historial (v1.25.0): propuestas anteriores persistidas ────────────────
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyList, setHistoryList] = useState<DashboardBlueprintList | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [loadingItemId, setLoadingItemId] = useState<string | null>(null);

  const editing = draft !== null;
  const view = draft ?? blueprint;
  const editorLabels = { ...(t.dashboardEdit ?? {}) };

  const copyText = (label: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedDax(label);
    setTimeout(() => setCopiedDax(null), 2000);
  };

  // ── Edición HITL (Paso 5): la IA propone, el usuario decide ──────────────
  const startEditing = () => {
    setDraft(JSON.parse(JSON.stringify(blueprint)) as DashboardBlueprint);
    setSaveError(null);
  };

  const handleSaveEdit = async () => {
    if (!draft) return;
    setSaving(true);
    setSaveError(null);
    try {
      const updated = await api.updateDashboardBlueprint(draft);
      setDraft(null);
      onBlueprintUpdated?.(updated);
    } catch (err: unknown) {
      const fallback = editorLabels.saveError ?? 'No se pudo guardar la edición del blueprint.';
      setSaveError(err instanceof Error && err.message ? err.message : fallback);
    } finally {
      setSaving(false);
    }
  };

  const handleDiscardEdit = () => {
    setDraft(null);
    setSaveError(null);
  };

  // ── Historial: listar propuestas anteriores y cargarlas en el preview ─────
  const toggleHistory = async () => {
    if (historyOpen) {
      setHistoryOpen(false);
      return;
    }
    setHistoryOpen(true);
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      setHistoryList(await api.listDashboardBlueprints());
    } catch (err: unknown) {
      const fallback = editorLabels.historyError ?? 'No se pudo cargar el historial.';
      setHistoryError(err instanceof Error && err.message ? err.message : fallback);
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleLoadHistoryItem = async (blueprintId: string) => {
    setLoadingItemId(blueprintId);
    setHistoryError(null);
    try {
      const loaded = await api.getDashboardBlueprint(blueprintId);
      setDraft(null);
      setSaveError(null);
      onBlueprintLoad?.(loaded);
      setHistoryOpen(false);
    } catch (err: unknown) {
      const fallback = editorLabels.historyError ?? 'No se pudo cargar el historial.';
      setHistoryError(err instanceof Error && err.message ? err.message : fallback);
    } finally {
      setLoadingItemId(null);
    }
  };

  const validationStatus = view.validation?.status || 'warning';
  const validationIcon = validationStatus === 'valid' ? CheckCircle2 : AlertTriangle;
  const validationColor = validationStatus === 'valid' ? 'var(--accent-emerald)' : validationStatus === 'invalid' ? 'var(--accent-rose)' : 'var(--accent-amber)';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }} data-testid="dashboard-preview">
      {/* Header del Blueprint */}
      <div className="card" style={{ padding: '20px', backgroundColor: 'var(--bg-card)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
              <div style={{ width: '40px', height: '40px', borderRadius: '10px', backgroundColor: 'rgba(14, 165, 233, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <LayoutDashboard size={22} color="var(--primary)" />
              </div>
              <div>
                <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-main)', margin: 0 }} data-testid="blueprint-title">
                  {view.name}
                </h2>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: 0 }}>
                  {t.dashboardPreview?.typeLabel ?? 'Tipo:'} {view.dashboard_type} · {t.dashboardPreview?.confidenceLabel ?? 'Confianza:'} {view.confidence}
                </p>
              </div>
            </div>
            <p style={{ fontSize: '14px', color: 'var(--text-main)', margin: '12px 0', lineHeight: 1.5 }}>
              {view.objective}
            </p>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: 0 }}>
              Audiencia: {view.audience}
            </p>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', alignItems: 'flex-end' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px', backgroundColor: validationStatus === 'valid' ? 'rgba(16, 185, 129, 0.1)' : validationStatus === 'invalid' ? 'rgba(244, 63, 94, 0.1)' : 'rgba(245, 158, 11, 0.1)', borderRadius: '8px' }}>
              {React.createElement(validationIcon, { size: 16, color: validationColor })}
              <span style={{ fontSize: '13px', fontWeight: 600, color: validationColor }} data-testid="validation-badge">
                {view.validation?.passed_count}/{view.validation?.total_count} checks
              </span>
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              {view.design.accessibility.overall_label}
            </span>
          </div>
        </div>
      </div>

      {/* Panel de historial: propuestas anteriores persistidas (Paso 5) */}
      {!editing && historyOpen && (
        <div className="card" style={{ padding: '16px', backgroundColor: 'var(--bg-card)' }} data-testid="history-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', gap: '12px', flexWrap: 'wrap' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)', margin: 0 }}>
              {editorLabels.historyTitle ?? 'Historial de propuestas'}
            </h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              {historyList && historyList.retention_days > 0 && (
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  {editorLabels.historyRetention ?? 'Retención'}: {historyList.retention_days} {editorLabels.historyRetentionDays ?? 'días'}
                </span>
              )}
              <button
                onClick={() => setHistoryOpen(false)}
                data-testid="history-close-btn"
                style={{ padding: '4px 10px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '12px' }}
              >
                ✕
              </button>
            </div>
          </div>
          {historyLoading && !historyList && (
            <div style={{ fontSize: '13px', color: 'var(--text-muted)', padding: '8px 0' }} data-testid="history-loading">
              {editorLabels.historyLoading ?? 'Cargando…'}
            </div>
          )}
          {historyError && (
            <div style={{ fontSize: '12px', color: 'var(--accent-rose)', padding: '8px 0' }} data-testid="history-error">
              {historyError}
            </div>
          )}
          {historyList && historyList.items.length === 0 && !historyError && (
            <div style={{ fontSize: '13px', color: 'var(--text-muted)', padding: '8px 0' }} data-testid="history-empty">
              {editorLabels.historyEmpty ?? 'Sin propuestas guardadas todavía.'}
            </div>
          )}
          {historyList && historyList.items.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {historyList.items.map((item) => {
                const isCurrent = item.blueprint_id === view.blueprint_id;
                return (
                  <div
                    key={item.blueprint_id}
                    data-testid={`history-item-${item.blueprint_id}`}
                    style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', padding: '10px 12px', backgroundColor: 'var(--bg-input)', borderRadius: '8px', flexWrap: 'wrap' }}
                  >
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                        <span>{item.name}</span>
                        {isCurrent && (
                          <span
                            data-testid="history-current-mark"
                            style={{ fontSize: '10px', fontWeight: 700, color: 'var(--primary)', backgroundColor: 'rgba(14, 165, 233, 0.12)', padding: '2px 6px', borderRadius: '999px' }}
                          >
                            {editorLabels.historyCurrent ?? 'Actual'}
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                        {new Date(item.created_at).toLocaleString()} · {item.kpi_count} {editorLabels.historyKpis ?? 'KPIs'} · {item.visual_count}{' '}
                        {editorLabels.historyVisuals ?? 'visuales'}
                        {item.validation_status ? ` · ${item.passed_count}/${item.total_count}` : ''}
                      </div>
                    </div>
                    <button
                      onClick={() => handleLoadHistoryItem(item.blueprint_id)}
                      disabled={loadingItemId !== null}
                      data-testid={`history-load-${item.blueprint_id}`}
                      style={{ padding: '6px 14px', backgroundColor: 'var(--primary)', border: 'none', borderRadius: '6px', color: '#ffffff', cursor: loadingItemId !== null ? 'wait' : 'pointer', fontSize: '12px', fontWeight: 600, opacity: loadingItemId !== null ? 0.7 : 1 }}
                    >
                      {loadingItemId === item.blueprint_id ? (editorLabels.historyLoading ?? 'Cargando…') : (editorLabels.historyLoad ?? 'Cargar')}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Tabs de navegación (ocultos durante la edición HITL) */}
      {!editing && (
        <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border-color)' }}>
          {[
            { id: 'example', label: t.dashboardPreview?.tabExample ?? 'Ejemplo', icon: Image },
            { id: 'overview', label: t.dashboardPreview?.tabOverview ?? 'Resumen', icon: LayoutDashboard },
            { id: 'visuals', label: t.dashboardPreview?.tabVisuals ?? 'Visuales', icon: BarChart3 },
            { id: 'design', label: t.dashboardPreview?.tabDesign ?? 'Diseño', icon: Palette },
            { id: 'powerbi', label: t.dashboardPreview?.tabPowerbi ?? 'Power BI', icon: FileCode },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 16px',
                backgroundColor: activeTab === tab.id ? 'var(--bg-card)' : 'transparent',
                border: 'none',
                borderBottom: activeTab === tab.id ? '2px solid var(--primary)' : '2px solid transparent',
                color: activeTab === tab.id ? 'var(--text-main)' : 'var(--text-muted)',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: activeTab === tab.id ? 600 : 400,
                transition: 'all 0.2s',
              }}
            >
              <tab.icon size={16} />
              {tab.label}
            </button>
          ))}
        </div>
      )}

      {/* Panel de edición HITL: el usuario decide, Python revalida al guardar */}
      {editing && draft && <DashboardEditor draft={draft} onChange={setDraft} />}

      {/* Panel 0: Maqueta de ejemplo (estilo informe Power BI) exportable a PNG */}
      {!editing && activeTab === 'example' && <DashboardMockup blueprint={blueprint} />}

      {/* Panel 1: Resumen */}
      {!editing && activeTab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
          {/* KPIs */}
          <div className="card" style={{ padding: '16px', backgroundColor: 'var(--bg-card)' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <TrendingUp size={16} color="var(--primary)" />
              {t.dashboardPreview?.kpiRecommended ?? 'KPIs Recomendados'}
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {blueprint.kpis.filter((kpi) => !kpi.hidden).map((kpi) => (
                <div key={kpi.kpi_id} style={{ padding: '12px', backgroundColor: 'var(--bg-input)', borderRadius: '8px' }}>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px' }}>{kpi.title}</div>
                  <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-main)' }}>
                    {kpi.value_label || '—'}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
                    {kpi.dax_measure_name}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Preguntas de negocio */}
          <div className="card" style={{ padding: '16px', backgroundColor: 'var(--bg-card)' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '12px' }}>
              {t.dashboardPreview?.businessQuestions ?? 'Preguntas de Negocio'}
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {blueprint.business_questions.map((q) => (
                <div key={q.question_id} style={{ fontSize: '13px', color: 'var(--text-main)', padding: '8px', backgroundColor: 'var(--bg-input)', borderRadius: '6px', lineHeight: 1.4 }}>
                  {q.text}
                </div>
              ))}
            </div>
          </div>

          {/* Filtros */}
          <div className="card" style={{ padding: '16px', backgroundColor: 'var(--bg-card)' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '12px' }}>
              {t.dashboardPreview?.filtersSlicers ?? 'Filtros / Slicers'}
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {blueprint.filters.filter((f) => !f.hidden).map((f) => (
                <div key={f.filter_id} style={{ padding: '8px', backgroundColor: 'var(--bg-input)', borderRadius: '6px' }}>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-main)' }}>{f.label}</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                    {f.recommended_values.slice(0, 3).join(', ')}
                    {f.recommended_values.length > 3 && ` +${f.recommended_values.length - 3}`}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Panel 2: Visuales */}
      {!editing && activeTab === 'visuals' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {blueprint.visuals.filter((visual) => !visual.hidden).map((visual) => (
            <div key={visual.visual_id} className="card" style={{ padding: '16px', backgroundColor: 'var(--bg-card)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                <div>
                  <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-main)', margin: 0 }}>
                    {visual.title}
                  </h3>
                  <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
                    {t.dashboardPreview?.typeLabel ?? 'Tipo:'} {visual.visual_type} · {t.dashboardPreview?.confidenceLabel ?? 'Confianza:'} {visual.confidence}
                  </p>
                </div>
                <div style={{ padding: '4px 8px', backgroundColor: visual.confidence === 'high' ? 'rgba(16, 185, 129, 0.1)' : visual.confidence === 'medium' ? 'rgba(245, 158, 11, 0.1)' : 'rgba(244, 63, 94, 0.1)', borderRadius: '4px', fontSize: '11px', fontWeight: 600, color: visual.confidence === 'high' ? 'var(--accent-emerald)' : visual.confidence === 'medium' ? 'var(--accent-amber)' : 'var(--accent-rose)' }}>
                  {visual.confidence}
                </div>
              </div>
              <p style={{ fontSize: '13px', color: 'var(--text-main)', lineHeight: 1.5, margin: '8px 0' }}>
                {visual.reason}
              </p>
              {visual.data_quality_notes.length > 0 && (
                <div style={{ marginTop: '12px', padding: '8px', backgroundColor: 'rgba(245, 158, 11, 0.05)', borderRadius: '6px', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
                  {visual.data_quality_notes.map((note, i) => (
                    <div key={i} style={{ fontSize: '12px', color: 'var(--accent-amber)', display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
                      <AlertTriangle size={12} style={{ marginTop: '2px', flexShrink: 0 }} />
                      <span>{note}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Panel 3: Diseño */}
      {!editing && activeTab === 'design' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
          {/* Paleta */}
          <div className="card" style={{ padding: '16px', backgroundColor: 'var(--bg-card)' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '12px' }}>
              {t.dashboardPreview?.paletteTitle ?? 'Paleta de Colores'}
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '12px' }}>
              {blueprint.design.palette.name}
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
              {[
                { label: 'Primario', color: blueprint.design.palette.primary_color },
                { label: 'Secundario', color: blueprint.design.palette.secondary_color },
                { label: 'Acento', color: blueprint.design.palette.accent_color },
                { label: 'Fondo', color: blueprint.design.palette.background_color },
                { label: 'Texto', color: blueprint.design.palette.text_color },
                { label: 'Positivo', color: blueprint.design.palette.positive_color },
              ].map((item) => (
                <div key={item.label} style={{ textAlign: 'center' }}>
                  <div style={{ width: '100%', height: '40px', backgroundColor: item.color, borderRadius: '6px', marginBottom: '4px' }} />
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{item.label}</div>
                  <div style={{ fontSize: '10px', color: 'var(--text-dim)' }}>{item.color}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Accesibilidad */}
          <div className="card" style={{ padding: '16px', backgroundColor: 'var(--bg-card)' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '12px' }}>
              {t.dashboardPreview?.accessibilityTitle ?? 'Accesibilidad WCAG'}
            </h3>
            <div style={{ padding: '12px', backgroundColor: blueprint.design.accessibility.overall_label.includes('PASS') ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 94, 0.1)', borderRadius: '8px', marginBottom: '12px' }}>
              <div style={{ fontSize: '16px', fontWeight: 700, color: blueprint.design.accessibility.overall_label.includes('PASS') ? 'var(--accent-emerald)' : 'var(--accent-rose)' }}>
                {blueprint.design.accessibility.overall_label}
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {blueprint.design.accessibility.checklist.slice(0, 5).map((item, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '12px' }}>
                  {item.status === 'pass' ? <CheckCircle2 size={14} color="var(--accent-emerald)" /> : <AlertTriangle size={14} color="var(--accent-amber)" />}
                  <div>
                    <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{item.label}</div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>{item.detail}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Estilo */}
          <div className="card" style={{ padding: '16px', backgroundColor: 'var(--bg-card)' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '12px' }}>
              {t.dashboardPreview?.designSystemTitle ?? 'Sistema de Diseño'}
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px' }}>
              <div><span style={{ color: 'var(--text-muted)' }}>{t.dashboardPreview?.styleLabel ?? 'Estilo:'}</span> <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>{blueprint.design.style.style_name}</span></div>
              <div><span style={{ color: 'var(--text-muted)' }}>{t.dashboardPreview?.canvasLabel ?? 'Canvas:'}</span> <span style={{ color: 'var(--text-main)' }}>{blueprint.design.style.canvas}</span></div>
              <div><span style={{ color: 'var(--text-muted)' }}>{t.dashboardPreview?.layoutLabel ?? 'Layout:'}</span> <span style={{ color: 'var(--text-main)' }}>{blueprint.design.style.layout}</span></div>
              <div><span style={{ color: 'var(--text-muted)' }}>{t.dashboardPreview?.densityLabel ?? 'Densidad:'}</span> <span style={{ color: 'var(--text-main)' }}>{blueprint.design.style.density}</span></div>
              <div><span style={{ color: 'var(--text-muted)' }}>{t.dashboardPreview?.typographyLabel ?? 'Tipografía:'}</span> <span style={{ color: 'var(--text-main)' }}>{blueprint.design.style.typography}</span></div>
            </div>
          </div>
        </div>
      )}

      {/* Panel 4: Power BI */}
      {!editing && activeTab === 'powerbi' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Export del blueprint editado: TMDL y proyecto .pbip (v1.25.0) */}
          <div className="card" style={{ padding: '16px', backgroundColor: 'var(--bg-card)' }} data-testid="export-model-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
              <div>
                <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)', margin: 0 }}>
                  {editorLabels.exportTitle ?? 'Exportar modelo editado'}
                </h3>
                <p style={{ fontSize: '11px', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
                  {editorLabels.exportHint ?? 'Descarga generada desde el blueprint (ediciones incluidas).'}
                </p>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <a
                  href={api.dashboardExportUrl(view.blueprint_id, 'tmdl')}
                  data-testid="export-tmdl-btn"
                  download
                  style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-main)', fontSize: '13px', fontWeight: 500, textDecoration: 'none', cursor: 'pointer' }}
                >
                  <FileCode size={14} />
                  {editorLabels.exportTmdl ?? 'Script TMDL'}
                </a>
                <a
                  href={api.dashboardExportUrl(view.blueprint_id, 'pbip')}
                  data-testid="export-pbip-btn"
                  download
                  style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px', backgroundColor: 'var(--primary)', border: 'none', borderRadius: '6px', color: '#ffffff', fontSize: '13px', fontWeight: 600, textDecoration: 'none', cursor: 'pointer' }}
                >
                  <Download size={14} />
                  {editorLabels.exportPbip ?? 'Proyecto .pbip'}
                </a>
              </div>
            </div>
          </div>
          <div className="card" style={{ padding: '16px', backgroundColor: 'var(--bg-card)' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '12px' }}>
              {t.dashboardPreview?.daxMeasures ?? 'Medidas DAX'}
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {blueprint.dax_measures.slice(0, 6).map((measure) => (
                <div key={measure.name} style={{ padding: '12px', backgroundColor: 'var(--bg-input)', borderRadius: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-main)' }}>{measure.name}</div>
                    <button
                      onClick={() => copyText(measure.name, measure.formula)}
                      style={{ padding: '4px 8px', backgroundColor: 'transparent', border: '1px solid var(--border-color)', borderRadius: '4px', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}
                    >
                      {copiedDax === measure.name ? <Check size={12} /> : <Copy size={12} />}
                      {copiedDax === measure.name ? (t.dashboardPreview?.copiedBtn ?? 'Copiado') : (t.dashboardPreview?.copyBtn ?? 'Copiar')}
                    </button>
                  </div>
                  <code style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', display: 'block', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                    {measure.formula}
                  </code>
                </div>
              ))}
            </div>
          </div>

          <div className="card" style={{ padding: '16px', backgroundColor: 'var(--bg-card)' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '12px' }}>
              {t.dashboardPreview?.implementationGuide ?? 'Guía de Implementación'}
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-main)', lineHeight: 1.5, marginBottom: '12px' }}>
              {blueprint.power_bi_summary}
            </p>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              {blueprint.power_bi_implementation.length} instrucciones de visual · {blueprint.dax_measures.length} medidas DAX · {blueprint.filters.length} slicers
            </div>
          </div>
        </div>
      )}

      {/* Footer con acciones */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px', backgroundColor: 'var(--bg-card)', borderRadius: '10px', marginTop: '8px', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ fontSize: '12px', color: saveError ? 'var(--accent-rose)' : 'var(--text-muted)' }} data-testid="editor-save-error">
          {saveError ?? (
            <>
              {t.dashboardPreview?.blueprintIdLabel ?? 'Blueprint ID:'} {blueprint.blueprint_id} · {(t.dashboardPreview?.generatedInLabel ?? 'Generado en {n}ms').replace('{n}', blueprint.generation_meta.duration_ms.toFixed(0))}
            </>
          )}
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {editing ? (
            <>
              <button
                onClick={handleDiscardEdit}
                data-testid="edit-cancel-btn"
                style={{ padding: '8px 16px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-main)', cursor: 'pointer', fontSize: '13px', fontWeight: 500 }}
              >
                {editorLabels.cancelBtn ?? 'Descartar cambios'}
              </button>
              <button
                onClick={handleSaveEdit}
                disabled={saving}
                data-testid="edit-save-btn"
                style={{ padding: '8px 16px', backgroundColor: 'var(--primary)', border: 'none', borderRadius: '6px', color: '#ffffff', cursor: saving ? 'wait' : 'pointer', fontSize: '13px', fontWeight: 600, opacity: saving ? 0.7 : 1 }}
              >
                {saving ? (editorLabels.saving ?? 'Guardando…') : (editorLabels.saveBtn ?? 'Guardar y revalidar')}
              </button>
            </>
          ) : (
            <>
              <button
                onClick={toggleHistory}
                data-testid="history-btn"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 16px',
                  backgroundColor: historyOpen ? 'rgba(14, 165, 233, 0.1)' : 'var(--bg-input)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '6px',
                  color: 'var(--text-main)',
                  cursor: 'pointer',
                  fontSize: '13px',
                  fontWeight: 500,
                }}
              >
                <History size={14} />
                {editorLabels.historyBtn ?? 'Historial'}
              </button>
              <button
                onClick={startEditing}
                data-testid="edit-blueprint-btn"
                style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-main)', cursor: 'pointer', fontSize: '13px', fontWeight: 500 }}
              >
                <Pencil size={14} />
                {editorLabels.editBtn ?? 'Editar blueprint'}
              </button>
              {onBackToStarSchema && (
                <button
                  onClick={onBackToStarSchema}
                  style={{ padding: '8px 16px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-main)', cursor: 'pointer', fontSize: '13px', fontWeight: 500 }}
                >
                  {t.dashboardPreview?.backToStarSchema ?? 'Volver al Esquema Estrella'}
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};
