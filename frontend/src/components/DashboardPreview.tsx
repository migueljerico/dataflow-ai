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
} from 'lucide-react';
import { DashboardBlueprint } from '../types';

interface Props {
  blueprint: DashboardBlueprint;
  onBackToStarSchema?: () => void;
}

export const DashboardPreview: React.FC<Props> = ({ blueprint, onBackToStarSchema }) => {
  const [copiedDax, setCopiedDax] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'visuals' | 'design' | 'powerbi'>('overview');

  const copyText = (label: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedDax(label);
    setTimeout(() => setCopiedDax(null), 2000);
  };

  const validationStatus = blueprint.validation?.status || 'warning';
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
                <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
                  {blueprint.name}
                </h2>
                <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: 0 }}>
                  Tipo: {blueprint.dashboard_type} · Confianza: {blueprint.confidence}
                </p>
              </div>
            </div>
            <p style={{ fontSize: '14px', color: 'var(--text-main)', margin: '12px 0', lineHeight: 1.5 }}>
              {blueprint.objective}
            </p>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: 0 }}>
              Audiencia: {blueprint.audience}
            </p>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', alignItems: 'flex-end' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px', backgroundColor: validationStatus === 'valid' ? 'rgba(16, 185, 129, 0.1)' : validationStatus === 'invalid' ? 'rgba(244, 63, 94, 0.1)' : 'rgba(245, 158, 11, 0.1)', borderRadius: '8px' }}>
              {React.createElement(validationIcon, { size: 16, color: validationColor })}
              <span style={{ fontSize: '13px', fontWeight: 600, color: validationColor }}>
                {blueprint.validation?.passed_count}/{blueprint.validation?.total_count} checks
              </span>
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              {blueprint.design.accessibility.overall_label}
            </span>
          </div>
        </div>
      </div>

      {/* Tabs de navegación */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border-color)' }}>
        {[
          { id: 'overview', label: 'Resumen', icon: LayoutDashboard },
          { id: 'visuals', label: 'Visuales', icon: BarChart3 },
          { id: 'design', label: 'Diseño', icon: Palette },
          { id: 'powerbi', label: 'Power BI', icon: FileCode },
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

      {/* Panel 1: Resumen */}
      {activeTab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
          {/* KPIs */}
          <div className="card" style={{ padding: '16px', backgroundColor: 'var(--bg-card)' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <TrendingUp size={16} color="var(--primary)" />
              KPIs Recomendados
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {blueprint.kpis.map((kpi) => (
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
              Preguntas de Negocio
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
              Filtros / Slicers
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {blueprint.filters.map((f) => (
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
      {activeTab === 'visuals' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {blueprint.visuals.map((visual) => (
            <div key={visual.visual_id} className="card" style={{ padding: '16px', backgroundColor: 'var(--bg-card)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                <div>
                  <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-main)', margin: 0 }}>
                    {visual.title}
                  </h3>
                  <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
                    Tipo: {visual.visual_type} · Confianza: {visual.confidence}
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
      {activeTab === 'design' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
          {/* Paleta */}
          <div className="card" style={{ padding: '16px', backgroundColor: 'var(--bg-card)' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '12px' }}>
              Paleta de Colores
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
              Accesibilidad WCAG
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
              Sistema de Diseño
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px' }}>
              <div><span style={{ color: 'var(--text-muted)' }}>Estilo:</span> <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>{blueprint.design.style.style_name}</span></div>
              <div><span style={{ color: 'var(--text-muted)' }}>Canvas:</span> <span style={{ color: 'var(--text-main)' }}>{blueprint.design.style.canvas}</span></div>
              <div><span style={{ color: 'var(--text-muted)' }}>Layout:</span> <span style={{ color: 'var(--text-main)' }}>{blueprint.design.style.layout}</span></div>
              <div><span style={{ color: 'var(--text-muted)' }}>Densidad:</span> <span style={{ color: 'var(--text-main)' }}>{blueprint.design.style.density}</span></div>
              <div><span style={{ color: 'var(--text-muted)' }}>Tipografía:</span> <span style={{ color: 'var(--text-main)' }}>{blueprint.design.style.typography}</span></div>
            </div>
          </div>
        </div>
      )}

      {/* Panel 4: Power BI */}
      {activeTab === 'powerbi' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="card" style={{ padding: '16px', backgroundColor: 'var(--bg-card)' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '12px' }}>
              Medidas DAX
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
                      {copiedDax === measure.name ? 'Copiado' : 'Copiar'}
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
              Guía de Implementación
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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px', backgroundColor: 'var(--bg-card)', borderRadius: '10px', marginTop: '8px' }}>
        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
          Blueprint ID: {blueprint.blueprint_id} · Generado en {blueprint.generation_meta.duration_ms.toFixed(0)}ms
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          {onBackToStarSchema && (
            <button
              onClick={onBackToStarSchema}
              style={{ padding: '8px 16px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-main)', cursor: 'pointer', fontSize: '13px', fontWeight: 500 }}
            >
              Volver al Esquema Estrella
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
