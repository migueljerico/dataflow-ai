import React, { useRef, useState } from 'react';
import { Download, FileText, Code, Image as ImageIcon } from 'lucide-react';
import {
  exportDashboardHtml,
  exportDashboardPdf,
  exportDashboardPng,
  type DashboardExportMeta,
} from '../utils/exportDashboard';
import { DashboardBlueprint, VisualRecommendation } from '../types';
import { useLanguage } from '../context/LanguageContext';

interface Props {
  blueprint: DashboardBlueprint;
}

const W = 1600;
const H = 1240;

const FALLBACK = {
  primary: '#2563eb',
  secondary: '#0ea5e9',
  accent: '#10b981',
  positive: '#059669',
  warning: '#b45309',
  rose: '#e11d48',
};

const INK = '#0f172a';
const MUTED = '#475569';
const FAINT = '#64748b';
const CARD_STROKE = '#e2e8f0';
/** Cabecera oscura derivada del primario de la paleta (garantiza contraste WCAG). */
const headerBgOf = (hex: string): string => {
  const match = /^#([0-9a-f]{6})$/i.exec((hex ?? '').trim());
  if (!match) return INK;
  const hex6 = match[1] ?? '';
  const num = parseInt(hex6, 16);
  if (Number.isNaN(num)) return INK;
  const r = Math.round(((num >> 16) & 255) * 0.45);
  const g = Math.round(((num >> 8) & 255) * 0.45);
  const b = Math.round((num & 255) * 0.45);
  return `#${((1 << 24) | (r << 16) | (g << 8) | b).toString(16).slice(1)}`;
};

const truncate = (value: string, max: number): string =>
  value.length > max ? `${value.slice(0, Math.max(0, max - 1))}…` : value;

const shortNumber = (value: number): string => {
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return `${(value / 1_000_000).toFixed(1)} M`;
  if (abs >= 10_000) return `${(value / 1_000).toFixed(1)} k`;
  if (abs >= 1_000) return value.toLocaleString('es-ES', { maximumFractionDigits: 0 });
  if (Number.isInteger(value)) return `${value}`;
  return value.toLocaleString('es-ES', { maximumFractionDigits: 2 });
};

const pickVisual = (visuals: VisualRecommendation[], types: string[]): VisualRecommendation | undefined =>
  visuals.find((v) => types.includes(v.visual_type));

/**
 * Maqueta ejecutiva del dashboard generada con datos REALES del Blueprint.
 * Layout limpio sin consejos técnicos (el PNG/PDF/HTML exportan este mismo SVG):
 * cabecera → filtros → KPIs → tendencia + composición → barras + ranking →
 * preguntas de negocio → pie de gobierno.
 */
export const DashboardMockup: React.FC<Props> = ({ blueprint }) => {
  const { t, language } = useLanguage();
  const svgRef = useRef<SVGSVGElement | null>(null);
  const en = language === 'en';
  const [exporting, setExporting] = useState<'png' | 'pdf' | 'html' | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  const labels = {
    filters: t.mockup?.filters ?? (en ? 'Filters' : 'Filtros'),
    questions: t.mockup?.questions ?? (en ? 'Business questions answered' : 'Preguntas de negocio que responde'),
    noData: t.mockup?.noData ?? (en ? 'Not enough data — see the Power BI tab' : 'Sin datos suficientes — ver pestaña Power BI'),
    noKpi: t.mockup?.noKpi ?? (en ? 'No KPIs recommended for this model' : 'Sin KPIs recomendados para este modelo'),
    noFilters: t.mockup?.noFilters ?? (en ? 'No slicers recommended' : 'Sin slicers recomendados'),
    governance:
      t.mockup?.governance ??
      (en
        ? 'AI proposes, the user decides, Python executes.'
        : 'La IA propone, el usuario decide, Python ejecuta.'),
    exportFail: t.mockup?.exportFail ?? (en ? 'Export not supported in this browser.' : 'Exportación no soportada en este navegador.'),
  };

  const palette = blueprint.design?.palette;
  const primary = palette?.primary_color || FALLBACK.primary;
  const secondary = palette?.secondary_color || FALLBACK.secondary;
  const accent = palette?.accent_color || FALLBACK.accent;
  const positive = palette?.positive_color || FALLBACK.positive;
  const warning = palette?.warning_color || FALLBACK.warning;
  const categorical = [primary, secondary, accent, positive, warning, FALLBACK.rose];

  const visuals = (blueprint.visuals ?? []).filter((v) => !v.hidden);
  const kpis = (blueprint.kpis ?? []).filter((k) => !k.hidden).slice(0, 4);
  const filters = (blueprint.filters ?? []).filter((f) => !f.hidden).slice(0, 4);
  const questions = (blueprint.business_questions ?? []).slice(0, 3);

  const lineVisual = pickVisual(visuals, ['line', 'area']) ?? visuals.find((v) => v.preview_data.length >= 3);
  const barVisual = pickVisual(visuals, ['bar', 'horizontal_bar', 'stacked_bar']);
  const donutVisual =
    pickVisual(visuals, ['donut', 'pie']) ??
    visuals.find(
      (v) => v !== lineVisual && v !== barVisual && v.preview_data.length >= 2 && v.preview_data.length <= 6,
    );
  const tableVisual = pickVisual(visuals, ['table', 'horizontal_bar']);

  // ── Serie temporal ──────────────────────────────────────────────────────────
  const linePoints = (lineVisual?.preview_data ?? []).slice(0, 12);
  const lineMax = Math.max(1, ...linePoints.map((p) => p.value));
  const plotX = 56;
  const plotY = 468;
  const plotW = 920;
  const plotH = 190;
  const lineCoords = linePoints.map((p, i) => ({
    x: plotX + (linePoints.length === 1 ? plotW / 2 : (i * plotW) / (linePoints.length - 1)),
    y: plotY + plotH - (p.value / lineMax) * plotH,
    point: p,
  }));
  const linePath = lineCoords.map((c, i) => `${i === 0 ? 'M' : 'L'}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(' ');
  const lineArea = linePath
    ? `${linePath} L${(plotX + plotW).toFixed(1)},${(plotY + plotH).toFixed(1)} L${plotX},${(plotY + plotH).toFixed(1)} Z`
    : '';
  const lineLabelEvery = Math.max(1, Math.ceil(linePoints.length / 8));

  // ── Barras ──────────────────────────────────────────────────────────────────
  // Barras horizontales del desglose (estilo Power BI ejecutivo)
  const barPoints = (barVisual?.preview_data ?? []).slice(0, 5);
  const barMax = Math.max(1, ...barPoints.map((p) => p.value));

  // ── Donut ───────────────────────────────────────────────────────────────────
  const donutPoints = (donutVisual?.preview_data ?? []).slice(0, 6);
  const donutTotal = donutPoints.reduce((acc, p) => acc + p.value, 0) || 1;
  // Inicio en las 12 en punto (estándar Power BI); tMid sitúa el % sobre el anillo
  let donutOffset = 50;
  const donutSegments = donutPoints.map((p, i) => {
    const pct = (p.value / donutTotal) * 100;
    const tMid = (((-donutOffset) % 100) + 100 + pct / 2) % 100;
    const seg = { point: p, pct, tMid, offset: donutOffset, color: categorical[i % categorical.length] };
    donutOffset -= pct;
    return seg;
  });

  // ── Ranking (barras horizontales proporcionales) ────────────────────────────
  const tableRows = (tableVisual?.preview_data ?? []).slice(0, 5);
  const rankMax = Math.max(1, ...tableRows.map((p) => p.value));

  const exportMeta: DashboardExportMeta = {
    name: blueprint.name,
    objective: blueprint.objective,
    businessQuestions: (blueprint.business_questions ?? []).map((q) => q.text),
    filtersLabel: `${filters.length} slicers`,
    checksLabel: `${blueprint.validation?.passed_count ?? 0}/${blueprint.validation?.total_count ?? 0} checks`,
    paletteName: palette?.name ?? '',
    governance: labels.governance,
  };

  const handleExport = async (type: 'png' | 'pdf' | 'html') => {
    const svg = svgRef.current;
    if (!svg) return;
    setExporting(type);
    setExportError(null);
    try {
      let ok = false;
      if (type === 'png') ok = await exportDashboardPng(svg, blueprint.blueprint_id);
      if (type === 'pdf') ok = await exportDashboardPdf(svg, blueprint.blueprint_id, exportMeta);
      if (type === 'html') ok = await exportDashboardHtml(svg, blueprint.blueprint_id, exportMeta);
      if (!ok) setExportError(labels.exportFail);
    } finally {
      setExporting(null);
    }
  };

  const kpiCount = Math.max(kpis.length, 1);
  const kpiCardW = (1568 - (kpiCount - 1) * 16) / kpiCount;

  const confidenceInk =
    blueprint.confidence === 'high' ? '#166534' : blueprint.confidence === 'medium' ? '#92400e' : '#9f1239';

  const filterPillW = filters.length > 0 ? (1418 - (filters.length - 1) * 12) / filters.length : 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }} data-testid="dashboard-mockup">
      <div
        className="card"
        style={{
          padding: '14px 16px',
          backgroundColor: 'var(--bg-card)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div>
          <h3 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-main)', margin: 0 }}>
            {t.powerBiExcel?.mockupTitle || (en ? 'Dashboard visual example' : 'Ejemplo visual del dashboard')}
          </h3>
          <p style={{ fontSize: '12.5px', color: 'var(--text-muted)', margin: '4px 0 0 0', lineHeight: 1.5 }}>
            {t.powerBiExcel?.mockupDesc ||
              (en
                ? 'Executive mockup built with the real Blueprint data: KPIs, trend, composition, breakdown and ranking.'
                : 'Maqueta ejecutiva construida con los datos reales del Blueprint: KPIs, tendencia, composición, desglose y ranking.')}
          </p>
          {exportError && (
            <p style={{ fontSize: '12px', color: 'var(--accent-amber)', margin: '6px 0 0 0' }}>{exportError}</p>
          )}
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn btn-outline"
            onClick={() => handleExport('png')}
            disabled={exporting !== null}
            data-testid="export-dashboard-mockup-png-btn"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', padding: '8px 14px' }}
            title={t.mockup?.exportPngTitle ?? (en ? 'Download executive PNG (3x)' : 'Descargar PNG ejecutivo (3x)')}
          >
            <Download size={14} />
            {exporting === 'png' ? (t.mockup?.exporting ?? (en ? 'Exporting...' : 'Exportando...')) : 'PNG'}
          </button>
          <button
            type="button"
            className="btn btn-outline"
            onClick={() => handleExport('pdf')}
            disabled={exporting !== null}
            data-testid="export-dashboard-mockup-pdf-btn"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', padding: '8px 14px' }}
            title={t.mockup?.exportPdfTitle ?? (en ? 'Download executive PDF' : 'Descargar PDF ejecutivo')}
          >
            <FileText size={14} />
            {exporting === 'pdf' ? (t.mockup?.exporting ?? (en ? 'Exporting...' : 'Exportando...')) : 'PDF'}
          </button>
          <button
            type="button"
            className="btn btn-outline"
            onClick={() => handleExport('html')}
            disabled={exporting !== null}
            data-testid="export-dashboard-mockup-html-btn"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', padding: '8px 14px' }}
            title={t.mockup?.exportHtmlTitle ?? (en ? 'Download executive HTML' : 'Descargar HTML ejecutivo')}
          >
            <Code size={14} />
            {exporting === 'html' ? (t.mockup?.exporting ?? (en ? 'Exporting...' : 'Exportando...')) : 'HTML'}
          </button>
        </div>
      </div>

      <div className="card" style={{ padding: '16px', backgroundColor: '#f1f5f9', borderRadius: '12px', overflow: 'hidden' }}>
        <svg
          ref={svgRef}
          xmlns="http://www.w3.org/2000/svg"
          viewBox={`0 0 ${W} ${H}`}
          style={{ width: '100%', height: 'auto', display: 'block', backgroundColor: '#ffffff', borderRadius: '8px' }}
          role="img"
          aria-label={t.mockup?.svgLabel ?? 'Ejemplo visual del dashboard'}
          fontFamily="Arial, Helvetica, sans-serif"
        >
          <rect x="0" y="0" width={W} height={H} fill="#ffffff" />

          {/* Cabecera ejecutiva: franja temática en el color de la paleta */}
          <rect x="16" y="16" width="1568" height="100" rx="12" fill={headerBgOf(primary)} />
          <text x="40" y="46" fill="#ffffff" fillOpacity="0.75" fontSize="11" fontWeight="700" letterSpacing="1.5">
            {truncate(`DATAFLOW AI · ${blueprint.dashboard_type.toUpperCase()} · ${blueprint.audience.toUpperCase()}`, 96)}
          </text>
          <text x="40" y="76" fill="#ffffff" fontSize="26" fontWeight="700">
            {truncate(blueprint.name, 54)}
          </text>
          <text x="40" y="99" fill="#ffffff" fillOpacity="0.85" fontSize="13">
            {truncate(blueprint.objective, 110)}
          </text>
          <rect x="1290" y="36" width="130" height="30" rx="15" fill="#ffffff" />
          <text x="1355" y="56" fill={confidenceInk} fontSize="12" fontWeight="700" textAnchor="middle">
            {truncate(`${blueprint.confidence}`, 16)}
          </text>
          <text x="1544" y="56" fill="#ffffff" fillOpacity="0.7" fontSize="11" textAnchor="end">
            {truncate(blueprint.blueprint_id, 24)}
          </text>
          <text x="1544" y="76" fill="#ffffff" fillOpacity="0.7" fontSize="11" textAnchor="end">
            {truncate(palette?.name ?? '', 28)}
          </text>
          {/* Franja de acento de la paleta bajo la cabecera */}
          <rect x="16" y="119" width="1568" height="6" rx="3" fill={accent} />

          {/* Filtros / slicers */}
          <rect x="16" y="134" width="1568" height="62" rx="12" fill="#ffffff" stroke={CARD_STROKE} strokeWidth="1" />
          <text x="40" y="171" fill={INK} fontSize="14" fontWeight="700">
            {labels.filters}
          </text>
          {filters.length > 0 ? (
            filters.map((f, i) => {
              const px = 150 + i * (filterPillW + 12);
              return (
                <g key={f.filter_id}>
                  <rect x={px} y="146" width={filterPillW} height="44" rx="10" fill="#f8fafc" stroke={CARD_STROKE} strokeWidth="1" />
                  <rect x={px + 14} y="156" width="8" height="8" rx="2" fill={primary} />
                  <text x={px + 30} y="164" fill={INK} fontSize="12" fontWeight="700">
                    {truncate(f.label, 18)}
                  </text>
                  <text x={px + 30} y="180" fill={FAINT} fontSize="11">
                    {truncate(f.recommended_values.slice(0, 3).join(' · '), 34)}
                  </text>
                </g>
              );
            })
          ) : (
            <text x="150" y="171" fill={FAINT} fontSize="12">
              {labels.noFilters}
            </text>
          )}

          {/* KPIs ejecutivos: tarjeta de borde fino + icono circular + número grande */}
          {kpis.length > 0 ? (
            kpis.map((kpi, i) => {
              const cx0 = 16 + i * (kpiCardW + 16);
              const kColor = categorical[i % categorical.length];
              const compact = kpiCardW < 430;
              return (
                <g key={kpi.kpi_id}>
                  <rect x={cx0} y="208" width={kpiCardW} height="128" rx="12" fill="#ffffff" stroke={CARD_STROKE} strokeWidth="1.5" />
                  <text x={cx0 + 20} y="234" fill={MUTED} fontSize="11" fontWeight="700" letterSpacing="0.8">
                    {truncate(kpi.title.toUpperCase(), compact ? 26 : 44)}
                  </text>
                  <circle cx={cx0 + 54} cy="284" r="24" fill={kColor} fillOpacity="0.12" stroke={kColor} strokeWidth="1.5" />
                  <path
                    d={`M ${cx0 + 44} 291 L ${cx0 + 50} 283 L ${cx0 + 55} 287 L ${cx0 + 64} 277`}
                    fill="none"
                    stroke={kColor}
                    strokeWidth="3"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <circle cx={cx0 + 64} cy="277" r="3" fill={kColor} />
                  <text x={cx0 + 92} y="296" fill={INK} fontSize={compact ? 28 : 34} fontWeight="700">
                    {truncate(kpi.value_label || '—', compact ? 14 : 20)}
                  </text>
                  <text x={cx0 + 92} y="318" fill={FAINT} fontSize="11">
                    {truncate(kpi.description || '', compact ? 34 : 60)}
                  </text>
                </g>
              );
            })
          ) : (
            <g>
              <rect x="16" y="208" width="1568" height="128" rx="12" fill="#ffffff" stroke={CARD_STROKE} strokeWidth="1" strokeDasharray="6 4" />
              <text x="800" y="278" fill={MUTED} fontSize="14" textAnchor="middle">
                {labels.noKpi}
              </text>
            </g>
          )}

          {/* Tendencia hero */}
          <rect x="16" y="348" width="1000" height="360" rx="12" fill="#ffffff" stroke={CARD_STROKE} strokeWidth="1" />
          <text x="40" y="380" fill={INK} fontSize="16" fontWeight="700">
            {truncate(lineVisual?.title ?? (t.mockup?.trendTitle ?? (en ? 'Trend' : 'Tendencia')), 58)}
          </text>
          <text x="40" y="402" fill={MUTED} fontSize="12">
            {truncate(lineVisual?.measure_name ?? lineVisual?.measure ?? '', 66)}
          </text>
          {lineCoords.length >= 2 ? (
            <g>
              {[0.25, 0.5, 0.75, 1].map((f) => (
                <g key={f}>
                  <line x1={plotX} y1={plotY + plotH * (1 - f)} x2={plotX + plotW} y2={plotY + plotH * (1 - f)} stroke="#e2e8f0" strokeWidth="1" />
                  <text x={plotX - 8} y={plotY + plotH * (1 - f) + 4} fill={MUTED} fontSize="11" textAnchor="end">
                    {shortNumber(lineMax * f)}
                  </text>
                </g>
              ))}
              <path d={lineArea} fill={primary} opacity="0.12" />
              <path d={linePath} fill="none" stroke={primary} strokeWidth="3.5" strokeLinejoin="round" strokeLinecap="round" />
              {lineCoords.map((c, i) => (
                <g key={i}>
                  {lineCoords.length <= 8 && (
                    <text
                      x={i === 0 ? c.x + 16 : c.x}
                      y={c.y - 12}
                      fill={MUTED}
                      fontSize="10"
                      fontWeight="700"
                      textAnchor="middle"
                    >
                      {shortNumber(c.point.value)}
                    </text>
                  )}
                  <circle cx={c.x} cy={c.y} r="4.5" fill={primary} stroke="#ffffff" strokeWidth="1.5" />
                  {i % lineLabelEvery === 0 && (
                    <text x={c.x} y={plotY + plotH + 22} fill={MUTED} fontSize="11" textAnchor="middle">
                      {truncate(c.point.label, 10)}
                    </text>
                  )}
                </g>
              ))}
            </g>
          ) : (
            <text x="516" y="540" fill={FAINT} fontSize="14" textAnchor="middle">
              {labels.noData}
            </text>
          )}

          {/* Composición donut */}
          <rect x="1032" y="348" width="552" height="360" rx="12" fill="#ffffff" stroke={CARD_STROKE} strokeWidth="1" />
          <text x="1056" y="380" fill={INK} fontSize="16" fontWeight="700">
            {truncate(donutVisual?.title ?? (t.mockup?.compositionTitle ?? (en ? 'Composition' : 'Composición')), 32)}
          </text>
          <text x="1056" y="402" fill={MUTED} fontSize="12">
            {truncate(donutVisual?.measure_name ?? donutVisual?.measure ?? '', 38)}
          </text>
          {donutSegments.length >= 2 ? (
            <g>
              <circle cx="1170" cy="540" r="72" fill="none" stroke="#f1f5f9" strokeWidth="34" />
              {donutSegments.map((s, i) => (
                <circle
                  key={i}
                  cx="1170"
                  cy="540"
                  r="72"
                  fill="none"
                  stroke={s.color}
                  strokeWidth="34"
                  pathLength={100}
                  strokeDasharray={`${s.pct.toFixed(1)} ${(100 - s.pct).toFixed(1)}`}
                  strokeDashoffset={s.offset.toFixed(1)}
                  transform="rotate(90 1170 540)"
                />
              ))}
              {/* Porcentaje impreso sobre el anillo (segmentos suficientemente grandes) */}
              {donutSegments
                .filter((s) => s.pct >= 9)
                .map((s, i) => {
                  const phi = ((90 + s.tMid * 3.6) * Math.PI) / 180;
                  return (
                    <text
                      key={`pct-${i}`}
                      x={(1170 + 72 * Math.cos(phi)).toFixed(1)}
                      y={(540 + 72 * Math.sin(phi) + 4).toFixed(1)}
                      fill="#ffffff"
                      fontSize="12"
                      fontWeight="700"
                      textAnchor="middle"
                      stroke="#0f172a"
                      strokeOpacity="0.45"
                      strokeWidth="3"
                      paintOrder="stroke"
                    >
                      {`${s.pct.toFixed(1).replace('.', en ? '.' : ',')}%`}
                    </text>
                  );
                })}
              <text x="1170" y="534" fill={INK} fontSize="20" fontWeight="700" textAnchor="middle">
                {shortNumber(donutTotal)}
              </text>
              <text x="1170" y="552" fill={MUTED} fontSize="11" textAnchor="middle">
                Total
              </text>
              {donutSegments.slice(0, 5).map((s, i) => (
                <g key={`leg-${i}`}>
                  <rect x="1280" y={468 + i * 34} width="14" height="14" rx="4" fill={s.color} />
                  <text x="1300" y={479 + i * 34} fill={INK} fontSize="12" fontWeight="600">
                    {truncate(s.point.label, 20)}
                  </text>
                  <text x="1300" y={493 + i * 34} fill={MUTED} fontSize="11">
                    {shortNumber(s.point.value)}
                  </text>
                </g>
              ))}
            </g>
          ) : (
            <text x="1308" y="540" fill={FAINT} fontSize="13" textAnchor="middle">
              {labels.noData}
            </text>
          )}

          {/* Desglose: barras horizontales con etiqueta a la izquierda y valor al final */}
          <rect x="16" y="720" width="768" height="330" rx="12" fill="#ffffff" stroke={CARD_STROKE} strokeWidth="1" />
          <text x="40" y="752" fill={INK} fontSize="16" fontWeight="700">
            {truncate(barVisual?.title ?? (t.mockup?.breakdownTitle ?? (en ? 'Breakdown' : 'Desglose')), 42)}
          </text>
          <text x="40" y="774" fill={MUTED} fontSize="12">
            {truncate(barVisual?.measure_name ?? barVisual?.measure ?? '', 48)}
          </text>
          {barPoints.length > 0 ? (
            barPoints.map((p, i) => {
              const rowY = 794 + i * 50;
              const barW = Math.max(10, (440 * p.value) / barMax);
              return (
                <g key={i}>
                  <text x="40" y={rowY + 13} fill={INK} fontSize="12" fontWeight="600">
                    {truncate(p.label, 20)}
                  </text>
                  <rect x="200" y={rowY} width="440" height="18" rx="9" fill="#f1f5f9" />
                  <rect x="200" y={rowY} width={barW} height="18" rx="9" fill={categorical[i % categorical.length]} />
                  <text x="760" y={rowY + 13} fill={INK} fontSize="12" fontWeight="700" textAnchor="end">
                    {shortNumber(p.value)}
                  </text>
                </g>
              );
            })
          ) : (
            <text x="400" y="900" fill={FAINT} fontSize="14" textAnchor="middle">
              {labels.noData}
            </text>
          )}

          {/* Ranking con barras proporcionales */}
          <rect x="800" y="720" width="784" height="330" rx="12" fill="#ffffff" stroke={CARD_STROKE} strokeWidth="1" />
          <text x="824" y="752" fill={INK} fontSize="16" fontWeight="700">
            {truncate(tableVisual?.title ?? (t.mockup?.rankingTitle ?? (en ? 'Ranking' : 'Ranking')), 46)}
          </text>
          <text x="824" y="774" fill={MUTED} fontSize="12">
            {truncate(tableVisual?.measure_name ?? tableVisual?.measure ?? '', 52)}
          </text>
          {tableRows.length > 0 ? (
            tableRows.map((p, i) => {
              const rowY = 796 + i * 48;
              const rw = Math.max(8, (380 * p.value) / rankMax);
              const medal = i === 0 ? '#fef3c7' : i === 1 ? '#f1f5f9' : i === 2 ? '#ffedd5' : '#eff6ff';
              const medalInk = i === 0 ? '#92400e' : i === 1 ? '#475569' : i === 2 ? '#9a3412' : primary;
              return (
                <g key={i}>
                  <circle cx="838" cy={rowY + 13} r="11" fill={medal} />
                  <text x="838" y={rowY + 17} fill={medalInk} fontSize="11" fontWeight="700" textAnchor="middle">
                    {i + 1}
                  </text>
                  <text x="858" y={rowY + 17} fill={INK} fontSize="12" fontWeight="600">
                    {truncate(p.label, 22)}
                  </text>
                  <rect x="1060" y={rowY + 5} width="380" height="16" rx="8" fill="#f1f5f9" />
                  <rect x="1060" y={rowY + 5} width={rw} height="16" rx="8" fill={categorical[i % categorical.length]} />
                  <text x="1548" y={rowY + 17} fill={INK} fontSize="12" fontWeight="700" textAnchor="end">
                    {shortNumber(p.value)}
                  </text>
                </g>
              );
            })
          ) : (
            <text x="1192" y="900" fill={FAINT} fontSize="13" textAnchor="middle">
              {labels.noData}
            </text>
          )}

          {/* Preguntas de negocio */}
          <rect x="16" y="1062" width="1568" height="92" rx="12" fill="#f8fafc" stroke={CARD_STROKE} strokeWidth="1" />
          <text x="40" y="1090" fill={INK} fontSize="13" fontWeight="700">
            {labels.questions}
          </text>
          {questions.length > 0 ? (
            questions.map((q, i) => (
              <text key={q.question_id} x={40 + i * 510} y="1116" fill="#334155" fontSize="12">
                {truncate(`${i + 1}. ${q.text}`, 62)}
              </text>
            ))
          ) : (
            <text x="40" y="1116" fill={FAINT} fontSize="12">
              {truncate(blueprint.objective, 120)}
            </text>
          )}

          {/* Pie de gobierno */}
          <rect x="16" y="1166" width="1568" height="58" rx="12" fill="#ffffff" stroke={CARD_STROKE} strokeWidth="1" />
          <text x="40" y="1190" fill={MUTED} fontSize="12">
            {truncate(`${labels.governance} DataFlow AI · ${palette?.name ?? ''}`, 120)}
          </text>
          <text x="1544" y="1190" fill={FAINT} fontSize="11" textAnchor="end">
            {truncate(
              `${(blueprint.business_questions ?? []).length} preguntas · ${filters.length} slicers · ${blueprint.validation?.passed_count ?? 0}/${blueprint.validation?.total_count ?? 0} checks`,
              60,
            )}
          </text>
          <text x="40" y="1208" fill={FAINT} fontSize="11">
            {truncate(blueprint.power_bi_summary || '', 120)}
          </text>
        </svg>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--text-muted)' }}>
        <ImageIcon size={14} />
        <span>
          {t.mockup?.exportHint ?? (en
            ? 'PNG, PDF and HTML export this same executive layout at 3x resolution, without build tips.'
            : 'PNG, PDF y HTML exportan este mismo layout ejecutivo a resolución 3x, sin consejos de construcción.')}
        </span>
      </div>
    </div>
  );
};
