import React, { useRef, useState } from 'react';
import { Download, Image as ImageIcon } from 'lucide-react';
import { DashboardBlueprint, VisualRecommendation } from '../types';
import { useLanguage } from '../context/LanguageContext';

interface Props {
  blueprint: DashboardBlueprint;
}

const W = 1600;
const H = 1000;

const SERIES_COLORS = ['#2563eb', '#0ea5e9', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316'];

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
 * Maqueta de ejemplo del dashboard (estilo informe Power BI) generada con los
 * datos REALES del Blueprint: KPIs, series temporales, barras, composición,
 * ranking, slicers y consejos de construcción (DAX, KPI, visuales).
 * Se exporta a PNG en alta resolución (2x) con el patrón SVG → canvas.
 */
export const DashboardMockup: React.FC<Props> = ({ blueprint }) => {
  const { t, language } = useLanguage();
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [isExportingPng, setIsExportingPng] = useState<boolean>(false);
  const en = language === 'en';

  const labels = {
    filters: en ? 'Filters' : 'Filtros',
    tips: en ? 'Build tips (DAX · KPI · visuals)' : 'Consejos de construcción (DAX · KPI · visuales)',
    dax: en ? 'DAX measures to create' : 'Medidas DAX a crear',
    kpiCards: en ? 'KPI cards' : 'Tarjetas KPI',
    pbi: en ? 'Power BI assembly' : 'Montaje en Power BI',
    noData: en ? 'Not enough data — see the Power BI tab' : 'Sin datos suficientes — ver pestaña Power BI',
    noKpi: en ? 'No KPIs recommended for this model' : 'Sin KPIs recomendados para este modelo',
    governance: en
      ? 'AI proposes, the user decides, Python executes.'
      : 'La IA propone, el usuario decide, Python ejecuta.',
  };

  const visuals = blueprint.visuals ?? [];
  const kpis = (blueprint.kpis ?? []).slice(0, 4);
  const filters = (blueprint.filters ?? []).slice(0, 3);
  const daxMeasures = (blueprint.dax_measures ?? []).slice(0, 4);
  const pbiGuide = (blueprint.power_bi_implementation ?? []).slice(0, 3);

  const lineVisual = pickVisual(visuals, ['line', 'area']) ?? visuals.find((v) => v.preview_data.length >= 3);
  const barVisual = pickVisual(visuals, ['bar', 'horizontal_bar', 'stacked_bar']);
  const donutVisual =
    pickVisual(visuals, ['donut', 'pie']) ??
    visuals.find(
      (v) => v !== lineVisual && v !== barVisual && v.preview_data.length >= 2 && v.preview_data.length <= 6,
    );
  const tableVisual = pickVisual(visuals, ['table']);

  // ── Serie temporal (panel principal) ──────────────────────────────────────
  const linePoints = (lineVisual?.preview_data ?? []).slice(0, 12);
  const lineMax = Math.max(1, ...linePoints.map((p) => p.value));
  const plotX = 96;
  const plotY = 292;
  const plotW = 880;
  const plotH = 190;
  const lineCoords = linePoints.map((p, i) => ({
    x: plotX + (linePoints.length === 1 ? plotW / 2 : (i * plotW) / (linePoints.length - 1)),
    y: plotY + plotH - (p.value / lineMax) * plotH,
    point: p,
  }));
  const linePath = lineCoords.map((c, i) => `${i === 0 ? 'M' : 'L'}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(' ');
  const lineArea = `${linePath} L${(plotX + plotW).toFixed(1)},${(plotY + plotH).toFixed(1)} L${plotX},${(plotY + plotH).toFixed(1)} Z`;
  const lineLabelEvery = Math.max(1, Math.ceil(linePoints.length / 8));

  // ── Barras (panel secundario) ─────────────────────────────────────────────
  const barPoints = (barVisual?.preview_data ?? []).slice(0, 8);
  const barMax = Math.max(1, ...barPoints.map((p) => p.value));
  const barBaseY = 800;
  const barTopY = 640;
  const barSlotW = barPoints.length > 0 ? 700 / barPoints.length : 700;

  // ── Donut (composición) ───────────────────────────────────────────────────
  const donutPoints = (donutVisual?.preview_data ?? []).slice(0, 6);
  const donutTotal = donutPoints.reduce((acc, p) => acc + p.value, 0) || 1;
  let donutOffset = 25;
  const donutSegments = donutPoints.map((p, i) => {
    const pct = (p.value / donutTotal) * 100;
    const seg = { point: p, pct, offset: donutOffset, color: SERIES_COLORS[i % SERIES_COLORS.length] };
    donutOffset -= pct;
    return seg;
  });

  // ── Ranking (tabla top) ───────────────────────────────────────────────────
  const tableRows = (tableVisual?.preview_data ?? []).slice(0, 6);

  const exportAsPng = () => {
    const svgEl = svgRef.current;
    if (!svgEl) return;
    setIsExportingPng(true);
    try {
      const svgXml = new XMLSerializer().serializeToString(svgEl);
      const svgBlob = new Blob([svgXml], { type: 'image/svg+xml;charset=utf-8' });
      const url = URL.createObjectURL(svgBlob);
      const img = new Image();
      img.onload = () => {
        const scale = 2;
        const canvas = document.createElement('canvas');
        canvas.width = W * scale;
        canvas.height = H * scale;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.fillStyle = '#eef2f7';
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          const pngData = canvas.toDataURL('image/png');
          const a = document.createElement('a');
          a.download = `ejemplo_dashboard_${blueprint.blueprint_id}.png`;
          a.href = pngData;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
        }
        URL.revokeObjectURL(url);
        setIsExportingPng(false);
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        setIsExportingPng(false);
      };
      img.src = url;
    } catch {
      setIsExportingPng(false);
    }
  };

  const kpiCount = Math.max(kpis.length, 1);
  const kpiCardW = (1568 - (kpiCount - 1) * 16) / kpiCount;

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
                ? 'Example mockup built with the real Blueprint data: KPIs, charts, slicers and build tips (DAX, KPIs, visuals).'
                : 'Maqueta de ejemplo construida con los datos reales del Blueprint: KPIs, gráficos, slicers y consejos de construcción (DAX, KPI, visuales).')}
          </p>
        </div>
        <button
          type="button"
          className="btn btn-outline"
          onClick={exportAsPng}
          disabled={isExportingPng}
          data-testid="export-dashboard-mockup-png-btn"
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', padding: '8px 14px' }}
          title={t.powerBiExcel?.mockupExportPng || (en ? 'Download example as PNG image (2x)' : 'Descargar ejemplo en imagen PNG (2x)')}
        >
          <Download size={14} />
          {isExportingPng
            ? t.powerBiExcel?.mockupGenerating || (en ? 'Generating image...' : 'Generando imagen...')
            : t.powerBiExcel?.mockupExportPng || (en ? 'Download example PNG' : 'Descargar ejemplo PNG')}
        </button>
      </div>

      <div className="card" style={{ padding: '16px', backgroundColor: '#eef2f7', borderRadius: '12px', overflow: 'hidden' }}>
        <svg
          ref={svgRef}
          xmlns="http://www.w3.org/2000/svg"
          viewBox={`0 0 ${W} ${H}`}
          style={{ width: '100%', height: 'auto', display: 'block' }}
          role="img"
          aria-label="Ejemplo visual del dashboard"
          fontFamily="Arial, Helvetica, sans-serif"
        >
          <rect x="0" y="0" width={W} height={H} fill="#eef2f7" />

          {/* Cabecera del informe */}
          <rect x="16" y="16" width="1568" height="88" rx="12" fill="#ffffff" stroke="#e2e8f0" strokeWidth="1" />
          <text x="40" y="54" fill="#0f172a" fontSize="26" fontWeight="700">
            {truncate(blueprint.name, 52)}
          </text>
          <text x="40" y="80" fill="#64748b" fontSize="13">
            {truncate(`${blueprint.dashboard_type} · ${blueprint.audience}`, 92)}
          </text>
          <rect x="1330" y="34" width="150" height="30" rx="15" fill="rgba(37, 99, 235, 0.1)" />
          <text x="1405" y="54" fill="#2563eb" fontSize="12" fontWeight="700" textAnchor="middle">
            {truncate(`${blueprint.confidence}`, 16)}
          </text>
          <text x="1496" y="54" fill="#64748b" fontSize="12" textAnchor="end">
            {truncate(`Blueprint ${blueprint.blueprint_id}`, 26)}
          </text>

          {/* Fila de KPIs */}
          {kpis.length > 0 ? (
            kpis.map((kpi, i) => (
              <g key={kpi.kpi_id}>
                <rect
                  x={16 + i * (kpiCardW + 16)}
                  y="116"
                  width={kpiCardW}
                  height="104"
                  rx="12"
                  fill="#ffffff"
                  stroke="#e2e8f0"
                  strokeWidth="1"
                />
                <rect x={16 + i * (kpiCardW + 16)} y="116" width="5" height="104" rx="2" fill={SERIES_COLORS[i % SERIES_COLORS.length]} />
                <text x={34 + i * (kpiCardW + 16)} y="146" fill="#64748b" fontSize="13">
                  {truncate(kpi.title, 28)}
                </text>
                <text x={34 + i * (kpiCardW + 16)} y="182" fill="#0f172a" fontSize="30" fontWeight="700">
                  {truncate(kpi.value_label || '—', 18)}
                </text>
                <text x={34 + i * (kpiCardW + 16)} y="204" fill="#2563eb" fontSize="11" fontFamily="monospace, monospace">
                  {truncate(kpi.dax_measure_name, 34)}
                </text>
              </g>
            ))
          ) : (
            <g>
              <rect x="16" y="116" width="1568" height="104" rx="12" fill="#ffffff" stroke="#e2e8f0" strokeWidth="1" strokeDasharray="6 4" />
              <text x="800" y="174" fill="#64748b" fontSize="14" textAnchor="middle">
                {labels.noKpi}
              </text>
            </g>
          )}

          {/* Panel principal: serie temporal */}
          <rect x="16" y="232" width="1024" height="320" rx="12" fill="#ffffff" stroke="#e2e8f0" strokeWidth="1" />
          <text x="40" y="262" fill="#0f172a" fontSize="15" fontWeight="700">
            {truncate(lineVisual?.title ?? (en ? 'Trend' : 'Tendencia'), 62)}
          </text>
          <text x="40" y="282" fill="#64748b" fontSize="12">
            {truncate(lineVisual?.measure_name ?? lineVisual?.measure ?? '', 62)}
          </text>
          {lineCoords.length >= 2 ? (
            <g>
              {[0.25, 0.5, 0.75, 1].map((f) => (
                <g key={f}>
                  <line x1={plotX} y1={plotY + plotH * (1 - f)} x2={plotX + plotW} y2={plotY + plotH * (1 - f)} stroke="#e2e8f0" strokeWidth="1" />
                  <text x={plotX - 8} y={plotY + plotH * (1 - f) + 4} fill="#94a3b8" fontSize="11" textAnchor="end">
                    {shortNumber(lineMax * f)}
                  </text>
                </g>
              ))}
              <path d={lineArea} fill="rgba(37, 99, 235, 0.12)" />
              <path d={linePath} fill="none" stroke="#2563eb" strokeWidth="3" strokeLinejoin="round" />
              {lineCoords.map((c, i) => (
                <g key={i}>
                  <circle cx={c.x} cy={c.y} r="4" fill="#2563eb" stroke="#ffffff" strokeWidth="1.5" />
                  {i % lineLabelEvery === 0 && (
                    <text x={c.x} y={plotY + plotH + 20} fill="#64748b" fontSize="11" textAnchor="middle">
                      {truncate(c.point.label, 10)}
                    </text>
                  )}
                </g>
              ))}
            </g>
          ) : (
            <text x="528" y="420" fill="#94a3b8" fontSize="14" textAnchor="middle">
              {labels.noData}
            </text>
          )}

          {/* Panel derecho: composición */}
          <rect x="1056" y="232" width="528" height="200" rx="12" fill="#ffffff" stroke="#e2e8f0" strokeWidth="1" />
          <text x="1080" y="262" fill="#0f172a" fontSize="15" fontWeight="700">
            {truncate(donutVisual?.title ?? (en ? 'Composition' : 'Composición'), 34)}
          </text>
          {donutSegments.length >= 2 ? (
            <g>
              <circle cx="1160" cy="348" r="58" fill="none" stroke="#f1f5f9" strokeWidth="30" />
              {donutSegments.map((s, i) => (
                <circle
                  key={i}
                  cx="1160"
                  cy="348"
                  r="58"
                  fill="none"
                  stroke={s.color}
                  strokeWidth="30"
                  pathLength={100}
                  strokeDasharray={`${s.pct.toFixed(1)} ${(100 - s.pct).toFixed(1)}`}
                  strokeDashoffset={s.offset.toFixed(1)}
                  transform="rotate(90 1160 348)"
                />
              ))}
              {donutSegments.slice(0, 4).map((s, i) => (
                <g key={`leg-${i}`}>
                  <rect x="1252" y={306 + i * 26} width="12" height="12" rx="3" fill={s.color} />
                  <text x="1270" y={316 + i * 26} fill="#334155" fontSize="12">
                    {truncate(`${s.point.label} · ${s.pct.toFixed(1)}%`, 26)}
                  </text>
                </g>
              ))}
            </g>
          ) : (
            <text x="1320" y="348" fill="#94a3b8" fontSize="13" textAnchor="middle">
              {labels.noData}
            </text>
          )}

          {/* Panel derecho: slicers */}
          <rect x="1056" y="444" width="528" height="108" rx="12" fill="#ffffff" stroke="#e2e8f0" strokeWidth="1" />
          <text x="1080" y="470" fill="#0f172a" fontSize="14" fontWeight="700">
            {labels.filters}
          </text>
          {filters.length > 0 ? (
            filters.map((f, i) => (
              <text key={f.filter_id} x="1080" y={494 + i * 20} fill="#475569" fontSize="12">
                {truncate(`${f.label}: ${f.recommended_values.slice(0, 3).join(' · ')}`, 52)}
              </text>
            ))
          ) : (
            <text x="1080" y="500" fill="#94a3b8" fontSize="12">
              {labels.noData}
            </text>
          )}

          {/* Panel: barras */}
          <rect x="16" y="564" width="768" height="300" rx="12" fill="#ffffff" stroke="#e2e8f0" strokeWidth="1" />
          <text x="40" y="594" fill="#0f172a" fontSize="15" fontWeight="700">
            {truncate(barVisual?.title ?? (en ? 'Breakdown' : 'Desglose'), 44)}
          </text>
          {barPoints.length > 0 ? (
            barPoints.map((p, i) => {
              const bw = Math.min(64, barSlotW - 18);
              const bx = 56 + i * barSlotW + (barSlotW - bw) / 2;
              const bh = Math.max(4, ((barTopY + 160 - barBaseY) * p.value) / barMax);
              return (
                <g key={i}>
                  <rect x={bx} y={barBaseY - bh} width={bw} height={bh} rx="4" fill={SERIES_COLORS[i % SERIES_COLORS.length]} />
                  <text x={bx + bw / 2} y={barBaseY - bh - 8} fill="#0f172a" fontSize="11" fontWeight="700" textAnchor="middle">
                    {shortNumber(p.value)}
                  </text>
                  <text x={bx + bw / 2} y={barBaseY + 20} fill="#64748b" fontSize="11" textAnchor="middle">
                    {truncate(p.label, 12)}
                  </text>
                </g>
              );
            })
          ) : (
            <text x="400" y="724" fill="#94a3b8" fontSize="14" textAnchor="middle">
              {labels.noData}
            </text>
          )}

          {/* Panel: ranking */}
          <rect x="800" y="564" width="368" height="300" rx="12" fill="#ffffff" stroke="#e2e8f0" strokeWidth="1" />
          <text x="824" y="594" fill="#0f172a" fontSize="15" fontWeight="700">
            {truncate(tableVisual?.title ?? (en ? 'Ranking' : 'Ranking'), 24)}
          </text>
          {tableRows.length > 0 ? (
            tableRows.map((p, i) => (
              <g key={i}>
                <circle cx="842" cy={622 + i * 38} r="12" fill="rgba(37, 99, 235, 0.1)" />
                <text x="842" y={627 + i * 38} fill="#2563eb" fontSize="12" fontWeight="700" textAnchor="middle">
                  {i + 1}
                </text>
                <text x="862" y={627 + i * 38} fill="#0f172a" fontSize="12">
                  {truncate(p.label, 20)}
                </text>
                <text x="1144" y={627 + i * 38} fill="#0f172a" fontSize="12" fontWeight="700" textAnchor="end">
                  {shortNumber(p.value)}
                </text>
              </g>
            ))
          ) : (
            <text x="984" y="724" fill="#94a3b8" fontSize="13" textAnchor="middle">
              {labels.noData}
            </text>
          )}

          {/* Panel: consejos de construcción */}
          <rect x="1184" y="564" width="400" height="300" rx="12" fill="#0f172a" />
          <text x="1208" y="594" fill="#f8fafc" fontSize="14" fontWeight="700">
            {truncate(labels.tips, 34)}
          </text>
          <text x="1208" y="620" fill="#38bdf8" fontSize="12" fontWeight="700">
            {labels.dax}
          </text>
          {daxMeasures.map((m, i) => (
            <text key={m.name} x="1208" y={640 + i * 19} fill="#e2e8f0" fontSize="11.5" fontFamily="monospace, monospace">
              {truncate(`• ${m.name}`, 38)}
            </text>
          ))}
          <text x="1208" y={640 + daxMeasures.length * 19 + 8} fill="#34d399" fontSize="12" fontWeight="700">
            {labels.kpiCards}
          </text>
          {(blueprint.kpis ?? []).slice(0, 3).map((k, i) => (
            <text key={k.kpi_id} x="1208" y={640 + daxMeasures.length * 19 + 28 + i * 19} fill="#e2e8f0" fontSize="11.5">
              {truncate(`• ${k.title} → [${k.dax_measure_name}]`, 38)}
            </text>
          ))}
          <text
            x="1208"
            y={640 + daxMeasures.length * 19 + 28 + Math.min(3, (blueprint.kpis ?? []).length) * 19 + 8}
            fill="#fbbf24"
            fontSize="12"
            fontWeight="700"
          >
            {labels.pbi}
          </text>
          {pbiGuide.map((g, i) => (
            <text
              key={`${g.visual}-${i}`}
              x="1208"
              y={640 + daxMeasures.length * 19 + 28 + Math.min(3, (blueprint.kpis ?? []).length) * 19 + 28 + i * 19}
              fill="#e2e8f0"
              fontSize="11.5"
            >
              {truncate(`• ${g.visual} → ${g.visual_type}`, 38)}
            </text>
          ))}

          {/* Pie del informe */}
          <rect x="16" y="876" width="1568" height="108" rx="12" fill="#ffffff" stroke="#e2e8f0" strokeWidth="1" />
          <text x="40" y="906" fill="#334155" fontSize="13">
            {truncate(blueprint.power_bi_summary || blueprint.objective, 148)}
          </text>
          <text x="40" y="932" fill="#64748b" fontSize="12">
            {truncate(`${labels.governance} DataFlow AI · ${blueprint.design?.palette?.name ?? ''}`, 148)}
          </text>
          <text x="40" y="956" fill="#94a3b8" fontSize="11">
            {truncate(
              `${(blueprint.business_questions ?? []).length} preguntas · ${(blueprint.dax_measures ?? []).length} DAX · ${(blueprint.filters ?? []).length} slicers · ${blueprint.validation?.passed_count ?? 0}/${blueprint.validation?.total_count ?? 0} checks`,
              148,
            )}
          </text>
        </svg>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--text-muted)' }}>
        <ImageIcon size={14} />
        <span>
          {en
            ? 'The PNG mirrors this example mockup at 2x resolution, ready to attach to the Power BI report.'
            : 'El PNG reproduce esta maqueta de ejemplo a resolución 2x, lista para adjuntar al informe de Power BI.'}
        </span>
      </div>
    </div>
  );
};
