import React from 'react';
import { ChevronDown, ChevronUp, Eye, EyeOff } from 'lucide-react';
import { DashboardBlueprint, VisualType } from '../types';
import { useLanguage } from '../context/LanguageContext';

interface Props {
  /** Borrador clonado del Blueprint; el editor nunca muta el original. */
  draft: DashboardBlueprint;
  /** Callback con el siguiente estado del borrador tras cada edición del usuario. */
  onChange: (next: DashboardBlueprint) => void;
}

const DASHBOARD_TYPES: string[] = [
  'sales',
  'finance',
  'operations',
  'hr',
  'marketing',
  'inventory',
  'customers',
  'logistics',
  'academic',
  'executive',
  'generic',
];

const DEFAULT_LABELS = {
  editBtn: 'Editar blueprint',
  hint: 'La IA propone, el usuario decide, Python ejecuta: los cambios se revalidan de forma determinista antes de guardarse.',
  nameLabel: 'Nombre del dashboard',
  objectiveLabel: 'Objetivo',
  typeLabel: 'Tipo de dashboard',
  kpisTitle: 'KPIs',
  visualsTitle: 'Visuales',
  filtersTitle: 'Filtros / Slicers',
  paletteLabel: 'Paleta de colores',
  visualTypeLabel: 'Tipo de visual',
  moveUp: 'Subir',
  moveDown: 'Bajar',
  hide: 'Ocultar',
  show: 'Mostrar',
  hiddenMark: 'Oculto',
  saveBtn: 'Guardar y revalidar',
  saving: 'Guardando…',
  cancelBtn: 'Descartar cambios',
  saveError: 'No se pudo guardar la edición del blueprint.',
};

type EditorLabels = typeof DEFAULT_LABELS;

/** Reordena una lista con campo `order` y renumera posiciones de forma determinista. */
function reorder<T extends { order: number }>(list: T[], index: number, delta: number): T[] {
  const target = index + delta;
  if (target < 0 || target >= list.length) return list;
  const next = [...list];
  const moved = next[index];
  next[index] = next[target];
  next[target] = moved;
  return next.map((item, i) => ({ ...item, order: i }));
}

const cardStyle: React.CSSProperties = {
  padding: '16px',
  backgroundColor: 'var(--bg-card)',
  borderRadius: '10px',
  border: '1px solid var(--border-color)',
};

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: '12px',
  fontWeight: 600,
  color: 'var(--text-muted)',
  marginBottom: '6px',
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '8px 10px',
  fontSize: '13px',
  color: 'var(--text-main)',
  backgroundColor: 'var(--bg-input)',
  border: '1px solid var(--border-color)',
  borderRadius: '6px',
};

const iconBtnStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: '28px',
  height: '28px',
  padding: 0,
  backgroundColor: 'transparent',
  border: '1px solid var(--border-color)',
  borderRadius: '6px',
  color: 'var(--text-muted)',
  cursor: 'pointer',
};

interface RowActionsProps {
  labels: EditorLabels;
  onUp: () => void;
  onDown: () => void;
  onToggle: () => void;
  hidden: boolean;
  name: string;
}

const RowActions: React.FC<RowActionsProps> = ({ labels, onUp, onDown, onToggle, hidden, name }) => (
  <div style={{ display: 'flex', gap: '6px', flexShrink: 0 }}>
    <button type="button" style={iconBtnStyle} aria-label={`${labels.moveUp}: ${name}`} onClick={onUp}>
      <ChevronUp size={14} />
    </button>
    <button type="button" style={iconBtnStyle} aria-label={`${labels.moveDown}: ${name}`} onClick={onDown}>
      <ChevronDown size={14} />
    </button>
    <button
      type="button"
      style={{ ...iconBtnStyle, color: hidden ? 'var(--accent-amber)' : 'var(--text-muted)' }}
      aria-label={`${hidden ? labels.show : labels.hide}: ${name}`}
      aria-pressed={hidden}
      onClick={onToggle}
    >
      {hidden ? <EyeOff size={14} /> : <Eye size={14} />}
    </button>
  </div>
);

export const DashboardEditor: React.FC<Props> = ({ draft, onChange }) => {
  const { t } = useLanguage();
  const labels: EditorLabels = { ...DEFAULT_LABELS, ...(t.dashboardEdit ?? {}) };

  const palettes = [draft.design.palette, ...draft.design.palette_variants];

  const patchKpis = (next: DashboardBlueprint['kpis']) => onChange({ ...draft, kpis: next });
  const patchVisuals = (next: DashboardBlueprint['visuals']) => onChange({ ...draft, visuals: next });
  const patchFilters = (next: DashboardBlueprint['filters']) => onChange({ ...draft, filters: next });

  const toggleHidden = <T extends { hidden?: boolean }>(list: T[], index: number): T[] =>
    list.map((item, i) => (i === index ? { ...item, hidden: !item.hidden } : item));

  const setVisualType = (index: number, visualType: VisualType) =>
    patchVisuals(draft.visuals.map((v, i) => (i === index ? { ...v, visual_type: visualType } : v)));

  const setPalette = (index: number) => {
    if (index === 0) return;
    const chosen = palettes[index];
    const rest = palettes.filter((_, i) => i !== index);
    onChange({
      ...draft,
      design: { ...draft.design, palette: chosen, palette_variants: rest },
    });
  };

  const rowContainer: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '12px',
    padding: '10px 12px',
    backgroundColor: 'var(--bg-input)',
    borderRadius: '8px',
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }} data-testid="dashboard-editor">
      <div
        style={{
          padding: '10px 14px',
          fontSize: '12px',
          color: 'var(--text-muted)',
          backgroundColor: 'rgba(14, 165, 233, 0.06)',
          border: '1px solid rgba(14, 165, 233, 0.25)',
          borderRadius: '8px',
          lineHeight: 1.5,
        }}
      >
        {labels.hint}
      </div>

      {/* General */}
      <div style={{ ...cardStyle, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
        <div>
          <label style={labelStyle} htmlFor="edit-dashboard-name">
            {labels.nameLabel}
          </label>
          <input
            id="edit-dashboard-name"
            data-testid="edit-name-input"
            style={inputStyle}
            value={draft.name}
            onChange={(e) => onChange({ ...draft, name: e.target.value })}
          />
        </div>
        <div>
          <label style={labelStyle} htmlFor="edit-dashboard-type">
            {labels.typeLabel}
          </label>
          <select
            id="edit-dashboard-type"
            data-testid="edit-type-select"
            style={inputStyle}
            value={draft.dashboard_type}
            onChange={(e) => onChange({ ...draft, dashboard_type: e.target.value as DashboardBlueprint['dashboard_type'] })}
          >
            {DASHBOARD_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </div>
        <div style={{ gridColumn: '1 / -1' }}>
          <label style={labelStyle} htmlFor="edit-dashboard-objective">
            {labels.objectiveLabel}
          </label>
          <textarea
            id="edit-dashboard-objective"
            data-testid="edit-objective-input"
            style={{ ...inputStyle, minHeight: '64px', resize: 'vertical' }}
            value={draft.objective}
            onChange={(e) => onChange({ ...draft, objective: e.target.value })}
          />
        </div>
      </div>

      {/* KPIs */}
      <div style={cardStyle}>
        <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)', margin: '0 0 12px 0' }}>
          {labels.kpisTitle}
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {draft.kpis.map((kpi, index) => (
            <div key={kpi.kpi_id} style={{ ...rowContainer, opacity: kpi.hidden ? 0.55 : 1 }} data-testid={`edit-kpi-${kpi.kpi_id}`}>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-main)' }}>{kpi.title}</div>
                <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>{kpi.dax_measure_name}</div>
              </div>
              {kpi.hidden && (
                <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--accent-amber)', textTransform: 'uppercase' }}>
                  {labels.hiddenMark}
                </span>
              )}
              <RowActions
                labels={labels}
                name={kpi.title}
                hidden={!!kpi.hidden}
                onUp={() => patchKpis(reorder(draft.kpis, index, -1))}
                onDown={() => patchKpis(reorder(draft.kpis, index, 1))}
                onToggle={() => patchKpis(toggleHidden(draft.kpis, index))}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Visuales */}
      <div style={cardStyle}>
        <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)', margin: '0 0 12px 0' }}>
          {labels.visualsTitle}
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {draft.visuals.map((visual, index) => {
            const typeOptions = Array.from(new Set([visual.visual_type, ...visual.alternative_types]));
            return (
              <div
                key={visual.visual_id}
                style={{ ...rowContainer, opacity: visual.hidden ? 0.55 : 1 }}
                data-testid={`edit-visual-${visual.visual_id}`}
              >
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-main)' }}>{visual.title}</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '2px' }}>{visual.reason}</div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flexShrink: 0 }}>
                  <label style={{ ...labelStyle, marginBottom: 0 }} htmlFor={`edit-visual-type-${visual.visual_id}`}>
                    {labels.visualTypeLabel}
                  </label>
                  <select
                    id={`edit-visual-type-${visual.visual_id}`}
                    data-testid={`edit-visual-type-${visual.visual_id}`}
                    style={{ ...inputStyle, width: '190px' }}
                    value={visual.visual_type}
                    onChange={(e) => setVisualType(index, e.target.value as VisualType)}
                  >
                    {typeOptions.map((type) => (
                      <option key={type} value={type}>
                        {type}
                      </option>
                    ))}
                  </select>
                </div>
                <RowActions
                  labels={labels}
                  name={visual.title}
                  hidden={!!visual.hidden}
                  onUp={() => patchVisuals(reorder(draft.visuals, index, -1))}
                  onDown={() => patchVisuals(reorder(draft.visuals, index, 1))}
                  onToggle={() => patchVisuals(toggleHidden(draft.visuals, index))}
                />
              </div>
            );
          })}
        </div>
      </div>

      {/* Filtros */}
      <div style={cardStyle}>
        <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)', margin: '0 0 12px 0' }}>
          {labels.filtersTitle}
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {draft.filters.map((filter, index) => (
            <div
              key={filter.filter_id}
              style={{ ...rowContainer, opacity: filter.hidden ? 0.55 : 1 }}
              data-testid={`edit-filter-${filter.filter_id}`}
            >
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-main)' }}>{filter.label}</div>
                <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
                  {filter.table_ref}[{filter.column}]
                </div>
              </div>
              <RowActions
                labels={labels}
                name={filter.label}
                hidden={!!filter.hidden}
                onUp={() => patchFilters(reorder(draft.filters, index, -1))}
                onDown={() => patchFilters(reorder(draft.filters, index, 1))}
                onToggle={() => patchFilters(toggleHidden(draft.filters, index))}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Paleta */}
      <div style={cardStyle}>
        <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-main)', margin: '0 0 12px 0' }}>
          {labels.paletteLabel}
        </h3>
        <select
          data-testid="edit-palette-select"
          aria-label={labels.paletteLabel}
          style={{ ...inputStyle, maxWidth: '340px' }}
          value={0}
          onChange={(e) => setPalette(Number(e.target.value))}
        >
          {palettes.map((palette, index) => (
            <option key={`${palette.name}-${index}`} value={index}>
              {index === 0 ? `${palette.name} ✓` : palette.name}
            </option>
          ))}
        </select>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(80px, 1fr))', gap: '8px', marginTop: '12px' }}>
          {[
            { label: 'Primario', color: draft.design.palette.primary_color },
            { label: 'Secundario', color: draft.design.palette.secondary_color },
            { label: 'Acento', color: draft.design.palette.accent_color },
            { label: 'Fondo', color: draft.design.palette.background_color },
            { label: 'Texto', color: draft.design.palette.text_color },
            { label: 'Positivo', color: draft.design.palette.positive_color },
          ].map((swatch) => (
            <div key={swatch.label} style={{ textAlign: 'center' }} data-testid={`palette-swatch-${swatch.label}`}>
              <div
                style={{ width: '100%', height: '32px', backgroundColor: swatch.color, borderRadius: '6px', marginBottom: '4px', border: '1px solid var(--border-color)' }}
              />
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{swatch.label}</div>
              <div style={{ fontSize: '9px', color: 'var(--text-dim)' }}>{swatch.color}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default DashboardEditor;
