import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  TrendingUp,
  Lightbulb,
  Sparkles,
  Award,
  PieChart,
  Network,
  Target,
  BarChart2,
  Maximize2,
  Filter,
  FileDown,
  Printer,
  Copy,
  Check,
  Layers,
  ArrowLeftRight,
  Star,
  Table2,
  Download,
  Activity,
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  Sliders,
} from 'lucide-react';
import { api } from '../services/api';
import {
  ExecutiveAnalyticsReport,
  ClusterVisualization,
  BoxPlotData,
  OutlierVisualization,
  IntegrationGuide,
  IntegrationColumn,
  DaxMeasureItem,
  ExcelFormulaItem,
  StarSchemaDiagram,
  StarSchemaDimension,
  ColumnDriftReport,
  DriftAnalysisReport,
  DriftAlert,
  ProactiveRecommendation,
} from '../types';
import { useLanguage } from '../context/LanguageContext';

interface Props {
  runId: string;
}

const CLUSTER_COLORS = [
  '#3b82f6', // Azul
  '#10b981', // Esmeralda
  '#f59e0b', // Ámbar
  '#ec4899', // Rosa
  '#8b5cf6', // Púrpura
  '#06b6d4', // Cian
  '#f97316', // Naranja
  '#14b8a6', // Teal
];

const STAR_DIM_STYLES: Record<string, { border: string; fill: string; fillSelected: string; label: string }> = {
  calendar: { border: '#10b981', fill: 'rgba(16, 185, 129, 0.14)', fillSelected: 'rgba(16, 185, 129, 0.32)', label: 'Calendario' },
  attribute: { border: '#3b82f6', fill: 'rgba(59, 130, 246, 0.14)', fillSelected: 'rgba(59, 130, 246, 0.32)', label: 'Atributo' },
};

const STAR_TEXT_MAIN = '#e2e8f0';
const STAR_TEXT_MUTED = '#94a3b8';
const STAR_LINE = '#475569';

const truncateModelText = (value: string, max: number): string =>
  value.length > max ? `${value.slice(0, max - 1)}…` : value;

/**
 * Diagrama interactivo del modelo estrella (Star Schema) para previsualizar la
 * estructura semántica antes de cargar el archivo en Power BI: tabla de hechos
 * central, dimensiones en órbita y relaciones muchos-a-uno con su DAX de creación.
 */
const StarSchemaVisual: React.FC<{ schema: StarSchemaDiagram }> = ({ schema }) => {
  const { t } = useLanguage();
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [copiedDax, setCopiedDax] = useState<string | null>(null);
  const [isExportingPng, setIsExportingPng] = useState<boolean>(false);
  const svgRef = useRef<SVGSVGElement | null>(null);

  const W = 860;
  const H = 520;
  const cx = W / 2;
  const cy = H / 2;
  const factW = 250;
  const factH = 140;
  const dimW = 168;
  const dimH = 72;
  const rx = 320;
  const ry = 195;

  const total = Math.max(schema.dimensions.length, 1);
  const positions = schema.dimensions.map((dim, idx) => {
    const angle = ((-90 + (360 / total) * idx) * Math.PI) / 180;
    return { dim, x: cx + rx * Math.cos(angle), y: cy + ry * Math.sin(angle) };
  });

  const selectedDim: StarSchemaDimension | null =
    schema.dimensions.find((d) => d.name === selectedName) || null;

  const copyDax = (label: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedDax(label);
    setTimeout(() => setCopiedDax(null), 2000);
  };

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
        const scale = 2; // Alta resolución (2x Retina)
        const canvas = document.createElement('canvas');
        canvas.width = W * scale;
        canvas.height = H * scale;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.fillStyle = '#0f172a';
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

          const pngData = canvas.toDataURL('image/png');
          const a = document.createElement('a');
          a.download = `esquema_estrella_${schema.fact_table}.png`;
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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }} data-testid="star-schema-visual">
      {/* Diagrama SVG: hechos al centro, dimensiones alrededor, relaciones *:1 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '16px', alignItems: 'start' }}>
        <div
          style={{
            backgroundColor: 'var(--bg-input)',
            border: '1px solid var(--border-color)',
            borderRadius: '10px',
            padding: '12px 14px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', flexWrap: 'wrap', gap: '8px' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-main, #f8fafc)' }}>
              {t.powerBiExcel?.tabStarSchema || 'Esquema Estrella'}
            </span>
            <button
              type="button"
              className="btn btn-outline"
              onClick={exportAsPng}
              disabled={isExportingPng}
              data-testid="export-star-schema-png-btn"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 10px',
                fontSize: '0.75rem',
                borderRadius: '6px',
                cursor: 'pointer',
              }}
              title={t.powerBiExcel?.exportStarSchemaPng || 'Descargar diagrama en imagen PNG (2x Retina)'}
            >
              <Download size={13} />
              {isExportingPng
                ? (t.powerBiExcel?.starPngDownloading || 'Generando...')
                : (t.powerBiExcel?.exportStarSchemaPng || 'Descargar PNG')}
            </button>
          </div>

          <svg
            ref={svgRef}
            xmlns="http://www.w3.org/2000/svg"
            viewBox={`0 0 ${W} ${H}`}
            style={{ width: '100%', height: 'auto', display: 'block' }}
            role="img"
            aria-label="Diagrama de modelo estrella"
          >
            {/* Relaciones (debajo de las cajas) */}
            {positions.map(({ dim, x, y }) => (
              <g key={`rel-${dim.name}`}>
                <line x1={cx} y1={cy} x2={x} y2={y} stroke={STAR_LINE} strokeWidth={1.5} strokeDasharray="5 4" />
                <text
                  x={cx + (x - cx) * 0.22}
                  y={cy + (y - cy) * 0.22 - 6}
                  fill="#f59e0b"
                  fontSize={15}
                  fontWeight={700}
                  textAnchor="middle"
                >
                  *
                </text>
                <text
                  x={cx + (x - cx) * 0.82}
                  y={cy + (y - cy) * 0.82 - 6}
                  fill="#10b981"
                  fontSize={15}
                  fontWeight={700}
                  textAnchor="middle"
                >
                  1
                </text>
              </g>
            ))}

            {/* Tabla de Hechos (centro) */}
            <g>
              <rect x={cx - factW / 2} y={cy - factH / 2} width={factW} height={factH} rx={12} fill="rgba(245, 158, 11, 0.14)" stroke="#f59e0b" strokeWidth={2.5} />
              <text x={cx} y={cy - factH / 2 + 26} fill="#f59e0b" fontSize={15} fontWeight={700} textAnchor="middle">
                {truncateModelText(schema.fact_table, 24)}
              </text>
              <text x={cx} y={cy - factH / 2 + 44} fill={STAR_TEXT_MUTED} fontSize={11} textAnchor="middle">
                {t.powerBiExcel?.starFactTable || 'Tabla de Hechos'} · {schema.fact_rows.toLocaleString()} {t.powerBiExcel?.starRows || 'filas'}
              </text>
              <line x1={cx - factW / 2 + 16} y1={cy - factH / 2 + 56} x2={cx + factW / 2 - 16} y2={cy - factH / 2 + 56} stroke={STAR_LINE} strokeWidth={1} />
              <text x={cx} y={cy - factH / 2 + 76} fill={STAR_TEXT_MAIN} fontSize={11} fontWeight={600} textAnchor="middle">
                {t.powerBiExcel?.starMeasures || 'Medidas'}: {schema.measures.length}
              </text>
              {schema.measures.slice(0, 2).map((m, idx) => (
                <text key={m} x={cx} y={cy - factH / 2 + 94 + idx * 16} fill={STAR_TEXT_MUTED} fontSize={10} textAnchor="middle">
                  {truncateModelText(m, 26)}
                </text>
              ))}
              {schema.measures.length > 2 && (
                <text x={cx} y={cy - factH / 2 + 94 + 2 * 16} fill={STAR_TEXT_MUTED} fontSize={10} textAnchor="middle">
                  +{schema.measures.length - 2} más
                </text>
              )}
            </g>

            {/* Dimensiones en órbita */}
            {positions.map(({ dim, x, y }) => {
              const style = STAR_DIM_STYLES[dim.kind] || STAR_DIM_STYLES.attribute;
              const isSelected = selectedName === dim.name;
              return (
                <g
                  key={dim.name}
                  onClick={() => setSelectedName(isSelected ? null : dim.name)}
                  style={{ cursor: 'pointer' }}
                  data-testid={`star-dim-${dim.name}`}
                >
                  <rect
                    x={x - dimW / 2}
                    y={y - dimH / 2}
                    width={dimW}
                    height={dimH}
                    rx={10}
                    fill={isSelected ? style.fillSelected : style.fill}
                    stroke={style.border}
                    strokeWidth={isSelected ? 3 : 1.8}
                  />
                  <text x={x} y={y - dimH / 2 + 22} fill={style.border} fontSize={12.5} fontWeight={700} textAnchor="middle">
                    {truncateModelText(dim.name, 20)}
                  </text>
                  <text x={x} y={y - dimH / 2 + 40} fill={STAR_TEXT_MUTED} fontSize={10} textAnchor="middle">
                    {truncateModelText(dim.source_column, 22)}
                  </text>
                  <text x={x} y={y - dimH / 2 + 58} fill={STAR_TEXT_MAIN} fontSize={10} textAnchor="middle">
                    {dim.kind === 'calendar'
                      ? style.label
                      : `${dim.distinct_count.toLocaleString()} ${t.powerBiExcel?.starDistinctValues || 'valores distintos'}`}
                  </text>
                </g>
              );
            })}
          </svg>
          <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap', justifyContent: 'center', fontSize: '0.725rem', color: 'var(--text-muted)', padding: '6px 4px 2px' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ width: 12, height: 12, borderRadius: 3, border: '2px solid #f59e0b', backgroundColor: 'rgba(245, 158, 11, 0.14)', display: 'inline-block' }} />
              {t.powerBiExcel?.starFactTable || 'Tabla de Hechos'}
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ width: 12, height: 12, borderRadius: 3, border: '2px solid #3b82f6', backgroundColor: 'rgba(59, 130, 246, 0.14)', display: 'inline-block' }} />
              {t.powerBiExcel?.starDimensions || 'Dimensiones'} (atributo)
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ width: 12, height: 12, borderRadius: 3, border: '2px solid #10b981', backgroundColor: 'rgba(16, 185, 129, 0.14)', display: 'inline-block' }} />
              Calendario
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <strong style={{ color: '#f59e0b' }}>*</strong> → <strong style={{ color: '#10b981' }}>1</strong> many-to-one
            </span>
          </div>
        </div>

        {/* Panel de detalle de la dimensión seleccionada */}
        <div
          style={{
            backgroundColor: 'var(--bg-input)',
            border: '1px solid var(--border-color)',
            borderRadius: '10px',
            padding: '14px 16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
            minHeight: '220px',
          }}
        >
          {selectedDim ? (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
                <strong style={{ color: (STAR_DIM_STYLES[selectedDim.kind] || STAR_DIM_STYLES.attribute).border, fontSize: '0.9rem' }}>
                  {selectedDim.name}
                </strong>
                <span className="badge badge-blue">{(STAR_DIM_STYLES[selectedDim.kind] || STAR_DIM_STYLES.attribute).label}</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.775rem' }}>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>{t.powerBiExcel?.starKeyColumn || 'Columna Clave'}:</span>{' '}
                  <code style={{ color: 'var(--primary)' }}>{selectedDim.key_column}</code>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>{t.powerBiExcel?.starDistinctValues || 'Valores Distintos'}:</span>{' '}
                  <strong>{selectedDim.kind === 'calendar' ? '—' : selectedDim.distinct_count.toLocaleString()}</strong>
                </div>
              </div>
              <div style={{ fontSize: '0.775rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>{t.powerBiExcel?.starSuggestedAttributes || 'Atributos Sugeridos'}:</span>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '5px' }}>
                  {selectedDim.suggested_attributes.map((attr) => (
                    <span key={attr} className="badge badge-blue" style={{ fontSize: '0.675rem' }}>{attr}</span>
                  ))}
                </div>
              </div>
              {selectedDim.dax_definition && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '5px', gap: '6px', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '0.725rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                      {t.powerBiExcel?.starDaxTablesLabel || 'Tablas Calculadas (DAX)'}:
                    </span>
                    <button
                      className="btn btn-outline"
                      style={{ padding: '3px 8px', fontSize: '0.7rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                      onClick={() => copyDax(selectedDim.name, selectedDim.dax_definition || '')}
                    >
                      {copiedDax === selectedDim.name ? <Check size={12} style={{ color: 'var(--accent-emerald)' }} /> : <Copy size={12} />}
                      {copiedDax === selectedDim.name ? (t.powerBiExcel?.copied || '¡Copiado!') : (t.powerBiExcel?.copySnippet || 'Copiar')}
                    </button>
                  </div>
                  <pre
                    style={{
                      backgroundColor: 'var(--bg-main)',
                      border: '1px solid var(--border-color)',
                      padding: '8px 10px',
                      borderRadius: '6px',
                      fontSize: '0.7rem',
                      fontFamily: 'var(--font-mono)',
                      color: 'var(--primary)',
                      overflowX: 'auto',
                      margin: 0,
                      maxHeight: '170px',
                      whiteSpace: 'pre',
                    }}
                  >
                    {selectedDim.dax_definition}
                  </pre>
                </div>
              )}
            </>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', flex: 1, gap: '8px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
              <Star size={28} style={{ color: '#f59e0b' }} />
              <p style={{ margin: 0 }}>{t.powerBiExcel?.starSelectDimension || 'Selecciona una dimensión del diagrama para ver su detalle.'}</p>
            </div>
          )}
        </div>
      </div>

      {/* Script consolidado de todas las tablas calculadas */}
      {schema.dax_calculated_tables && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px', flexWrap: 'wrap', gap: '6px' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Table2 size={14} style={{ color: '#10b981' }} />
              {t.powerBiExcel?.starDaxTablesLabel || 'Tablas Calculadas (DAX)'} ({schema.dimension_count})
            </span>
            <button
              className="btn btn-outline"
              style={{ padding: '3px 8px', fontSize: '0.725rem', display: 'flex', alignItems: 'center', gap: '4px' }}
              onClick={() => copyDax('__all__', schema.dax_calculated_tables)}
            >
              {copiedDax === '__all__' ? <Check size={12} style={{ color: 'var(--accent-emerald)' }} /> : <Copy size={12} />}
              {copiedDax === '__all__' ? (t.powerBiExcel?.copied || '¡Copiado!') : (t.powerBiExcel?.copySnippet || 'Copiar')}
            </button>
          </div>
          <pre
            style={{
              backgroundColor: 'var(--bg-main)',
              border: '1px solid var(--border-color)',
              padding: '10px 12px',
              borderRadius: '6px',
              fontSize: '0.725rem',
              fontFamily: 'var(--font-mono)',
              color: 'var(--primary)',
              overflowX: 'auto',
              margin: 0,
              maxHeight: '260px',
              whiteSpace: 'pre',
            }}
          >
            {schema.dax_calculated_tables}
          </pre>
          {schema.tmdl_relationships && (
            <p style={{ fontSize: '0.725rem', color: 'var(--text-muted)', margin: '8px 0 0' }}>
              Las relaciones <strong>many-to-one</strong> ya vienen incluidas en el archivo <code>model.tmdl</code> del proyecto PBIP exportable de esta misma tarjeta: al abrirlo en Power BI Desktop, el modelo estrella se reconstruye solo.
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export const BusinessInsights: React.FC<Props> = ({ runId }) => {
  const { t, language } = useLanguage();
  const [report, setReport] = useState<ExecutiveAnalyticsReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'kpis' | 'clusters' | 'outliers' | 'integration' | 'drift'>('kpis');
  const [copiedSnippet, setCopiedSnippet] = useState<string | null>(null);

  // Estados de visualización de Data Drift y Percentiles
  const [selectedDriftCol, setSelectedDriftCol] = useState<string>('');
  const [copiedRecId, setCopiedRecId] = useState<string | null>(null);

  // Estados de visualización de Clusters
  const [selectedClusterFilter, setSelectedClusterFilter] = useState<number | null>(null);
  const [selectedClusterXCol, setSelectedClusterXCol] = useState<string>('');
  const [selectedClusterYCol, setSelectedClusterYCol] = useState<string>('');
  const [hoveredClusterPoint, setHoveredClusterPoint] = useState<{
    x: number;
    y: number;
    valX: number;
    valY: number;
    label: string;
    clusterId: number;
  } | null>(null);

  // Estados de visualización de Outliers
  const [selectedOutlierCol, setSelectedOutlierCol] = useState<string>('');
  const [outlierViewMode, setOutlierViewMode] = useState<'boxplot' | 'scatter' | 'diff'>('boxplot');
  const [diffOnlyModified, setDiffOnlyModified] = useState<boolean>(false);
  const [hoveredOutlierPoint, setHoveredOutlierPoint] = useState<{
    x: number;
    y: number;
    valY: number;
    label: string;
    isOutlier: boolean;
    rawY?: number | null;
    wasModified?: boolean;
    diffStatus?: string;
  } | null>(null);

  // Estados de Integración Power BI / Excel adaptativa
  const [selectedPqFormat, setSelectedPqFormat] = useState<'csv' | 'parquet'>('csv');
  const [powerBiCodeView, setPowerBiCodeView] = useState<'dax' | 'powerquery' | 'tmdl' | 'star'>('dax');
  const [selectedExcelCategory, setSelectedExcelCategory] = useState<string>('all');
  const [selectedExcelMeasureIndex, setSelectedExcelMeasureIndex] = useState<number>(0);

  useEffect(() => {
    let cancelled = false;
    const fetchAnalytics = async () => {
      setLoading(true);
      try {
        const data = await api.getBusinessAnalytics(runId);
        if (!cancelled) {
          setReport(data);
          if (data.outlier_visualization && data.outlier_visualization.active_column) {
            setSelectedOutlierCol(data.outlier_visualization.active_column);
          }
          if (data.cluster_visualization) {
            setSelectedClusterXCol(data.cluster_visualization.x_column);
            setSelectedClusterYCol(data.cluster_visualization.y_column);
          }
        }
      } catch (err: unknown) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'No se pudieron calcular los Business Analytics.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchAnalytics();
    return () => {
      cancelled = true;
    };
  }, [runId]);

  // Selección de datos de BoxPlot activos
  const activeBoxPlot: BoxPlotData | undefined = useMemo(() => {
    if (!report?.outlier_visualization?.columns) return undefined;
    return (
      report.outlier_visualization.columns.find((c) => c.column === selectedOutlierCol) ||
      report.outlier_visualization.columns[0]
    );
  }, [report, selectedOutlierCol]);

  useEffect(() => {
    if (report?.drift_analysis?.columns && report.drift_analysis.columns.length > 0 && !selectedDriftCol) {
      setSelectedDriftCol(report.drift_analysis.columns[0].column_name);
    }
  }, [report, selectedDriftCol]);

  // Selección de datos de Drift activos
  const activeDriftColReport: ColumnDriftReport | undefined = useMemo(() => {
    if (!report?.drift_analysis?.columns) return undefined;
    return (
      report.drift_analysis.columns.find((c) => c.column_name === selectedDriftCol) ||
      report.drift_analysis.columns[0]
    );
  }, [report, selectedDriftCol]);

  if (loading) {
    return (
      <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--primary)' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '10px', fontSize: '1rem', fontWeight: 600 }}>
          <Sparkles size={20} className="animate-spin text-primary" />
          {t.analytics?.subtitle || 'Calculando KPIs y analítica avanzada...'}
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div style={{ padding: '16px', color: 'var(--accent-rose)' }}>
        {error || 'Información analítica no disponible.'}
      </div>
    );
  }

  const clusterViz: ClusterVisualization | undefined = report.cluster_visualization;
  const outlierViz: OutlierVisualization | undefined = report.outlier_visualization;

  return (
    <div style={{ marginTop: '32px', borderTop: '1px solid var(--border-color)', paddingTop: '28px' }}>
      {/* Encabezado Principal */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '12px',
          marginBottom: '20px',
        }}
      >
        <div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <TrendingUp size={22} className="text-primary" aria-hidden="true" /> {t.analytics?.title || 'Business Analytics & KPIs'}
          </h3>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            {t.analytics?.subtitle || 'Métricas de valor calculadas con pandas sobre el dataset depurado.'}
          </p>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <a
            href={api.getExecutiveReportExportUrl(runId, language)}
            download={`reporte_ejecutivo_${runId}.html`}
            className="btn btn-primary"
            style={{ textDecoration: 'none', padding: '8px 14px', fontSize: '0.825rem', display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <FileDown size={16} /> {t.export?.btnExportHtml || 'Exportar Reporte Ejecutivo'}
          </a>
          <button
            className="btn btn-outline"
            onClick={() => window.open(api.getExecutiveReportExportUrl(runId, language), '_blank')}
            style={{ padding: '8px 12px', fontSize: '0.825rem', display: 'flex', alignItems: 'center', gap: '6px' }}
            title={t.export?.btnExportPdf || 'Imprimir / Guardar en PDF'}
          >
            <Printer size={16} />
          </button>
          <span className="badge badge-emerald">
            <Sparkles size={12} /> {t.analytics?.powerBiBadge || 'Power BI Ready'}
          </span>
        </div>
      </div>

      {/* Selector de Pestañas Analíticas */}
      <div
        role="tablist"
        style={{
          display: 'flex',
          gap: '8px',
          borderBottom: '1px solid var(--border-color)',
          marginBottom: '24px',
          overflowX: 'auto',
          paddingBottom: '8px',
        }}
      >
        <button
          role="tab"
          aria-selected={activeTab === 'kpis'}
          onClick={() => setActiveTab('kpis')}
          className={`btn ${activeTab === 'kpis' ? 'btn-primary' : 'btn-outline'}`}
          style={{ fontSize: '0.85rem', padding: '8px 14px', display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <TrendingUp size={16} /> {t.analytics?.tabKpis || 'KPIs & Resumen Directivo'}
        </button>

        <button
          role="tab"
          aria-selected={activeTab === 'clusters'}
          onClick={() => setActiveTab('clusters')}
          className={`btn ${activeTab === 'clusters' ? 'btn-primary' : 'btn-outline'}`}
          style={{ fontSize: '0.85rem', padding: '8px 14px', display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <Network size={16} /> {t.analytics?.tabClusters || 'Segmentación de Clusters (Scatter 2D)'}
        </button>

        <button
          role="tab"
          aria-selected={activeTab === 'outliers'}
          onClick={() => setActiveTab('outliers')}
          className={`btn ${activeTab === 'outliers' ? 'btn-primary' : 'btn-outline'}`}
          style={{ fontSize: '0.85rem', padding: '8px 14px', display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <Target size={16} /> {t.analytics?.tabOutliers || 'Detección de Outliers (Boxplots)'}
        </button>

        <button
          role="tab"
          aria-selected={activeTab === 'integration'}
          onClick={() => setActiveTab('integration')}
          className={`btn ${activeTab === 'integration' ? 'btn-primary' : 'btn-outline'}`}
          style={{ fontSize: '0.85rem', padding: '8px 14px', display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <Layers size={16} /> {t.analytics?.tabIntegration || 'Integración Power BI / Excel'}
        </button>

        <button
          role="tab"
          aria-selected={activeTab === 'drift'}
          onClick={() => setActiveTab('drift')}
          className={`btn ${activeTab === 'drift' ? 'btn-primary' : 'btn-outline'}`}
          style={{ fontSize: '0.85rem', padding: '8px 14px', display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <Activity size={16} /> {t.driftAnalytics?.tabTitle || 'Alertas & Data Drift'}
          {report?.drift_analysis && report.drift_analysis.total_alerts > 0 && (
            <span
              className={`badge ${
                report.drift_analysis.critical_columns_count > 0 ? 'badge-rose' : 'badge-amber'
              }`}
              style={{ fontSize: '0.65rem', padding: '1px 6px', marginLeft: '4px' }}
            >
              {report.drift_analysis.total_alerts}
            </span>
          )}
        </button>
      </div>

      {/* PESTAÑA 1: KPIS Y RESUMEN EJECUTIVO */}
      {activeTab === 'kpis' && (
        <div>
          {/* Tarjetas de Business KPIs */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: '12px',
              marginBottom: '24px',
            }}
          >
            {report.kpis.map((kpi) => (
              <div
                key={kpi.id}
                style={{
                  backgroundColor: 'var(--bg-input)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '10px',
                  padding: '16px',
                }}
              >
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '6px' }}>{kpi.title}</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--primary)', marginBottom: '4px' }}>
                  {kpi.value}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-main)', opacity: 0.8 }}>{kpi.subtitle}</div>
              </div>
            ))}
          </div>

          {/* Resumen Ejecutivo de Negocio */}
          <div
            style={{
              backgroundColor: 'rgba(59, 130, 246, 0.05)',
              border: '1px solid rgba(59, 130, 246, 0.2)',
              borderRadius: '10px',
              padding: '16px 20px',
              marginBottom: '24px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
              <Award size={18} className="text-primary" />
              <h4 style={{ fontSize: '0.95rem', fontWeight: 700 }}>
                {t.analytics?.executiveSummaryTitle || 'Resumen Ejecutivo para Dirección'}
              </h4>
            </div>
            <p style={{ fontSize: '0.875rem', lineHeight: '1.6', color: 'var(--text-main)' }}>
              {report.executive_summary}
            </p>
          </div>

          {/* Distribución por Categorías y Recomendaciones */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
            {report.category_breakdown && report.category_breakdown.length > 0 && (
              <div
                style={{
                  backgroundColor: 'var(--bg-input)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '10px',
                  padding: '16px',
                }}
              >
                <h4
                  style={{
                    fontSize: '0.9rem',
                    fontWeight: 700,
                    marginBottom: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <PieChart size={16} className="text-primary" />{' '}
                  {t.analytics?.segmentationTitle || 'Segmentación / Distribución Principal'}
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {report.category_breakdown.map((cat, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        fontSize: '0.825rem',
                      }}
                    >
                      <span>{cat.category_name}</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontWeight: 600 }}>{cat.count}</span>
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>({cat.percentage}%)</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {report.strategic_recommendations && report.strategic_recommendations.length > 0 && (
              <div
                style={{
                  backgroundColor: 'var(--bg-input)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '10px',
                  padding: '16px',
                }}
              >
                <h4
                  style={{
                    fontSize: '0.9rem',
                    fontWeight: 700,
                    marginBottom: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <Lightbulb size={16} className="text-primary" />{' '}
                  {t.analytics?.recommendationsTitle || 'Recomendaciones de Negocio'}
                </h4>
                <ul
                  style={{
                    paddingLeft: '18px',
                    margin: 0,
                    fontSize: '0.825rem',
                    lineHeight: '1.5',
                    color: 'var(--text-muted)',
                  }}
                >
                  {report.strategic_recommendations.map((rec, idx) => (
                    <li key={idx} style={{ marginBottom: '6px' }}>
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* PESTAÑA 2: VISUALIZACIÓN DE CLUSTERS (SCATTER PLOT 2D) */}
      {activeTab === 'clusters' && (
        <div>
          {!clusterViz || clusterViz.points.length === 0 ? (
            <div
              style={{
                backgroundColor: 'var(--bg-input)',
                border: '1px dashed var(--border-color)',
                padding: '32px',
                textAlign: 'center',
                borderRadius: '10px',
                color: 'var(--text-muted)',
              }}
            >
              {t.analytics?.noClusterData || 'No hay datos numéricos suficientes para generar el gráfico de clusters.'}
            </div>
          ) : (
            <div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '12px',
                  marginBottom: '16px',
                }}
              >
                <div>
                  <h4 style={{ fontSize: '1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Network size={18} className="text-primary" /> {t.analytics?.clusterScatterTitle || 'Diagrama de Dispersión 2D de Clusters'}
                  </h4>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {t.analytics?.clusterScatterDesc || 'Visualización de observaciones segmentadas por similitud euclidiana.'}
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <span className="badge badge-blue">
                    Columna: {clusterViz.cluster_column}
                  </span>
                  <span className="badge badge-emerald">
                    {clusterViz.clusters.length} Clusters
                  </span>
                  <span className="badge badge-amber">
                    {clusterViz.total_points} Filas
                  </span>
                </div>
              </div>

              {/* Selector Dinámico de Ejes de Proyección 2D */}
              {clusterViz.available_numeric_columns && clusterViz.available_numeric_columns.length >= 2 && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '16px',
                    flexWrap: 'wrap',
                    backgroundColor: 'var(--bg-input)',
                    padding: '8px 14px',
                    borderRadius: '8px',
                    border: '1px solid var(--border-color)',
                    marginBottom: '12px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '0.775rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                      {t.analytics?.xAxis || 'Eje X'}:
                    </span>
                    <select
                      value={selectedClusterXCol || clusterViz.x_column}
                      onChange={(e) => setSelectedClusterXCol(e.target.value)}
                      style={{
                        padding: '4px 8px',
                        fontSize: '0.775rem',
                        borderRadius: '6px',
                        border: '1px solid var(--border-color)',
                        backgroundColor: 'var(--bg-main)',
                        color: 'var(--text-main)',
                      }}
                    >
                      {clusterViz.available_numeric_columns.map((col) => (
                        <option key={col} value={col}>
                          {col}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '0.775rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                      {t.analytics?.yAxis || 'Eje Y'}:
                    </span>
                    <select
                      value={selectedClusterYCol || clusterViz.y_column}
                      onChange={(e) => setSelectedClusterYCol(e.target.value)}
                      style={{
                        padding: '4px 8px',
                        fontSize: '0.775rem',
                        borderRadius: '6px',
                        border: '1px solid var(--border-color)',
                        backgroundColor: 'var(--bg-main)',
                        color: 'var(--text-main)',
                      }}
                    >
                      {clusterViz.available_numeric_columns.map((col) => (
                        <option key={col} value={col}>
                          {col}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              )}

              {/* Leyenda y Filtro de Clusters */}
              <div
                style={{
                  display: 'flex',
                  gap: '8px',
                  flexWrap: 'wrap',
                  marginBottom: '16px',
                  alignItems: 'center',
                  backgroundColor: 'var(--bg-input)',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  border: '1px solid var(--border-color)',
                }}
              >
                <span style={{ fontSize: '0.775rem', fontWeight: 600, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Filter size={14} /> {t.analytics?.clustersLegend || 'Grupos'}:
                </span>
                <button
                  className={`btn ${selectedClusterFilter === null ? 'btn-primary' : 'btn-outline'}`}
                  style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                  onClick={() => setSelectedClusterFilter(null)}
                >
                  Todos ({clusterViz.points.length})
                </button>
                {clusterViz.clusters.map((c, i) => {
                  const color = CLUSTER_COLORS[i % CLUSTER_COLORS.length];
                  const isSelected = selectedClusterFilter === c.cluster_id;
                  return (
                    <button
                      key={c.cluster_id}
                      className="btn"
                      style={{
                        padding: '4px 10px',
                        fontSize: '0.75rem',
                        backgroundColor: isSelected ? color : 'var(--bg-main)',
                        color: isSelected ? '#ffffff' : 'var(--text-main)',
                        border: `1px solid ${color}`,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                      }}
                      onClick={() => setSelectedClusterFilter(isSelected ? null : c.cluster_id)}
                    >
                      <span
                        style={{
                          width: '8px',
                          height: '8px',
                          borderRadius: '50%',
                          backgroundColor: isSelected ? '#ffffff' : color,
                        }}
                      />
                      {c.label} ({c.count} · {c.percentage}%)
                    </button>
                  );
                })}
              </div>

              {/* Renderizador SVG del Scatter Plot 2D */}
              {(() => {
                const points = clusterViz.points.filter(
                  (p) => selectedClusterFilter === null || p.cluster_id === selectedClusterFilter
                );
                if (points.length === 0) return null;

                const xs = points.map((p) => p.x);
                const ys = points.map((p) => p.y);
                const minX = Math.min(...xs);
                const maxX = Math.max(...xs);
                const minY = Math.min(...ys);
                const maxY = Math.max(...ys);

                const padX = (maxX - minX) * 0.1 || 1.0;
                const padY = (maxY - minY) * 0.1 || 1.0;
                const domainMinX = minX - padX;
                const domainMaxX = maxX + padX;
                const domainMinY = minY - padY;
                const domainMaxY = maxY + padY;

                const width = 640;
                const height = 360;
                const margin = { top: 25, right: 30, bottom: 45, left: 55 };
                const plotW = width - margin.left - margin.right;
                const plotH = height - margin.top - margin.bottom;

                const scaleX = (val: number) =>
                  margin.left + ((val - domainMinX) / (domainMaxX - domainMinX || 1)) * plotW;
                const scaleY = (val: number) =>
                  height - margin.bottom - ((val - domainMinY) / (domainMaxY - domainMinY || 1)) * plotH;

                return (
                  <div
                    style={{
                      position: 'relative',
                      backgroundColor: 'var(--bg-input)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '10px',
                      padding: '12px',
                      marginBottom: '20px',
                    }}
                  >
                    <svg
                      viewBox={`0 0 ${width} ${height}`}
                      style={{ width: '100%', height: 'auto', display: 'block' }}
                      role="img"
                      aria-label="Scatter Plot 2D de clusters"
                    >
                      {/* Cuadrícula de fondo */}
                      <line
                        x1={margin.left}
                        y1={margin.top}
                        x2={margin.left}
                        y2={height - margin.bottom}
                        stroke="var(--border-color)"
                        strokeWidth="1.5"
                      />
                      <line
                        x1={margin.left}
                        y1={height - margin.bottom}
                        x2={width - margin.right}
                        y2={height - margin.bottom}
                        stroke="var(--border-color)"
                        strokeWidth="1.5"
                      />

                      {/* Líneas de guía intermedias */}
                      {[0.25, 0.5, 0.75].map((pct) => (
                        <g key={pct}>
                          <line
                            x1={margin.left}
                            y1={margin.top + plotH * pct}
                            x2={width - margin.right}
                            y2={margin.top + plotH * pct}
                            stroke="var(--border-color)"
                            strokeDasharray="4 4"
                            opacity="0.4"
                          />
                          <line
                            x1={margin.left + plotW * pct}
                            y1={margin.top}
                            x2={margin.left + plotW * pct}
                            y2={height - margin.bottom}
                            stroke="var(--border-color)"
                            strokeDasharray="4 4"
                            opacity="0.4"
                          />
                        </g>
                      ))}

                      {/* Etiquetas de Ejes */}
                      <text
                        x={margin.left + plotW / 2}
                        y={height - 10}
                        textAnchor="middle"
                        fill="var(--text-muted)"
                        fontSize="11"
                        fontWeight="600"
                      >
                        {selectedClusterXCol || clusterViz.x_column} →
                      </text>
                      <text
                        x={16}
                        y={margin.top + plotH / 2}
                        textAnchor="middle"
                        fill="var(--text-muted)"
                        fontSize="11"
                        fontWeight="600"
                        transform={`rotate(-90 16 ${margin.top + plotH / 2})`}
                      >
                        {selectedClusterYCol || clusterViz.y_column} →
                      </text>

                      {/* Valores de extremo en ejes */}
                      <text x={margin.left} y={height - margin.bottom + 16} fill="var(--text-muted)" fontSize="9" textAnchor="middle">
                        {domainMinX.toFixed(1)}
                      </text>
                      <text x={width - margin.right} y={height - margin.bottom + 16} fill="var(--text-muted)" fontSize="9" textAnchor="middle">
                        {domainMaxX.toFixed(1)}
                      </text>
                      <text x={margin.left - 8} y={height - margin.bottom} fill="var(--text-muted)" fontSize="9" textAnchor="end" dominantBaseline="middle">
                        {domainMinY.toFixed(1)}
                      </text>
                      <text x={margin.left - 8} y={margin.top} fill="var(--text-muted)" fontSize="9" textAnchor="end" dominantBaseline="middle">
                        {domainMaxY.toFixed(1)}
                      </text>

                      {/* Puntos de datos */}
                      {points.map((p, idx) => {
                        const px = scaleX(p.x);
                        const py = scaleY(p.y);
                        const color = CLUSTER_COLORS[p.cluster_id % CLUSTER_COLORS.length];
                        return (
                          <circle
                            key={idx}
                            cx={px}
                            cy={py}
                            r="5"
                            fill={color}
                            fillOpacity="0.8"
                            stroke="#ffffff"
                            strokeWidth="1.2"
                            style={{ cursor: 'pointer', transition: 'r 0.15s ease' }}
                            onMouseEnter={(e) => {
                              const rect = e.currentTarget.getBoundingClientRect();
                              setHoveredClusterPoint({
                                x: px,
                                y: py,
                                valX: p.x,
                                valY: p.y,
                                label: p.label || `Fila #${p.row_index + 1}`,
                                clusterId: p.cluster_id,
                              });
                            }}
                            onMouseLeave={() => setHoveredClusterPoint(null)}
                          />
                        );
                      })}

                      {/* Centroides de Clusters */}
                      {clusterViz.clusters.map((c, i) => {
                        if (c.center_x === null || c.center_y === null || c.center_x === undefined || c.center_y === undefined) return null;
                        if (selectedClusterFilter !== null && selectedClusterFilter !== c.cluster_id) return null;
                        const cx = scaleX(c.center_x);
                        const cy = scaleY(c.center_y);
                        const color = CLUSTER_COLORS[i % CLUSTER_COLORS.length];
                        return (
                          <g key={`centroid-${c.cluster_id}`}>
                            <circle cx={cx} cy={cy} r="10" fill={color} fillOpacity="0.3" stroke={color} strokeWidth="2" />
                            <circle cx={cx} cy={cy} r="4" fill="#ffffff" stroke={color} strokeWidth="2" />
                          </g>
                        );
                      })}
                    </svg>

                    {/* Tooltip interactivo flotante */}
                    {hoveredClusterPoint && (
                      <div
                        style={{
                          position: 'absolute',
                          top: Math.max(10, (hoveredClusterPoint.y / 360) * 100 - 15) + '%',
                          left: Math.min(80, (hoveredClusterPoint.x / 640) * 100 + 3) + '%',
                          backgroundColor: 'rgba(15, 23, 42, 0.95)',
                          color: '#ffffff',
                          padding: '8px 12px',
                          borderRadius: '6px',
                          fontSize: '0.75rem',
                          pointerEvents: 'none',
                          boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                          zIndex: 10,
                          border: `1px solid ${CLUSTER_COLORS[hoveredClusterPoint.clusterId % CLUSTER_COLORS.length]}`,
                        }}
                      >
                        <div style={{ fontWeight: 700, marginBottom: '2px' }}>{hoveredClusterPoint.label}</div>
                        <div style={{ color: CLUSTER_COLORS[hoveredClusterPoint.clusterId % CLUSTER_COLORS.length], fontWeight: 600 }}>
                          Cluster {hoveredClusterPoint.clusterId}
                        </div>
                        <div>
                          {clusterViz.x_column}: <strong>{hoveredClusterPoint.valX}</strong>
                        </div>
                        <div>
                          {clusterViz.y_column}: <strong>{hoveredClusterPoint.valY}</strong>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })()}

              {/* Tabla de Perfiles y Medias de Clusters */}
              <div
                style={{
                  backgroundColor: 'var(--bg-input)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '10px',
                  padding: '16px',
                }}
              >
                <h4 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: '12px' }}>
                  {t.analytics?.clusterProfileTable || 'Perfil y Medias por Cluster'}
                </h4>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', fontSize: '0.8rem', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                        <th style={{ padding: '8px 10px' }}>Cluster</th>
                        <th style={{ padding: '8px 10px' }}>Registros</th>
                        <th style={{ padding: '8px 10px' }}>Porcentaje</th>
                        {clusterViz.available_numeric_columns.map((col) => (
                          <th key={col} style={{ padding: '8px 10px' }}>
                            Media ({col})
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {clusterViz.clusters.map((c, i) => {
                        const color = CLUSTER_COLORS[i % CLUSTER_COLORS.length];
                        return (
                          <tr key={c.cluster_id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                            <td style={{ padding: '8px 10px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: color }} />
                              {c.label}
                            </td>
                            <td style={{ padding: '8px 10px' }}>{c.count}</td>
                            <td style={{ padding: '8px 10px' }}>{c.percentage}%</td>
                            {clusterViz.available_numeric_columns.map((col) => (
                              <td key={col} style={{ padding: '8px 10px', fontFamily: 'var(--font-mono)' }}>
                                {c.feature_averages[col] !== undefined ? c.feature_averages[col] : '—'}
                              </td>
                            ))}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* PESTAÑA 3: DETECCIÓN DE OUTLIERS (BOXPLOTS & DISPERSIÓN) */}
      {activeTab === 'outliers' && (
        <div>
          {!outlierViz || outlierViz.columns.length === 0 || !activeBoxPlot ? (
            <div
              style={{
                backgroundColor: 'var(--bg-input)',
                border: '1px dashed var(--border-color)',
                padding: '32px',
                textAlign: 'center',
                borderRadius: '10px',
                color: 'var(--text-muted)',
              }}
            >
              {t.analytics?.noOutlierData || 'No se detectaron variables numéricas para calcular diagramas de outliers.'}
            </div>
          ) : (
            <div>
              {/* Encabezado y Selector de Variable */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '12px',
                  marginBottom: '16px',
                }}
              >
                <div>
                  <h4 style={{ fontSize: '1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Target size={18} className="text-primary" /> {t.analytics?.outlierTitle || 'Distribución y Detección de Outliers (Boxplots)'}
                  </h4>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {t.analytics?.outlierDesc || 'Análisis estadístico basado en Rango Intercuartílico (IQR 1.5x) y Z-Score.'}
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <span className="badge badge-rose">
                    {outlierViz.total_outliers_detected} Outliers Detectados
                  </span>
                  <span className="badge badge-blue">
                    Método: {outlierViz.detection_method}
                  </span>
                </div>
              </div>

              {/* Selector de Variable y Selector de Modo de Vista */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '12px',
                  backgroundColor: 'var(--bg-input)',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  border: '1px solid var(--border-color)',
                  marginBottom: '16px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '0.775rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                    {t.analytics?.selectColumn || 'Variable'}:
                  </span>
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    {outlierViz.columns.map((b) => (
                      <button
                        key={b.column}
                        className={`btn ${selectedOutlierCol === b.column ? 'btn-primary' : 'btn-outline'}`}
                        style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                        onClick={() => setSelectedOutlierCol(b.column)}
                      >
                        {b.column} {b.outliers_count > 0 && <span style={{ color: 'var(--accent-rose)', fontWeight: 700 }}>({b.outliers_count})</span>}
                      </button>
                    ))}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '6px' }}>
                  <button
                    className={`btn ${outlierViewMode === 'boxplot' ? 'btn-primary' : 'btn-outline'}`}
                    style={{ padding: '4px 10px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                    onClick={() => setOutlierViewMode('boxplot')}
                  >
                    <BarChart2 size={13} /> {t.analytics?.viewModeBoxplot || 'Box Plot'}
                  </button>
                  <button
                    className={`btn ${outlierViewMode === 'scatter' ? 'btn-primary' : 'btn-outline'}`}
                    style={{ padding: '4px 10px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                    onClick={() => setOutlierViewMode('scatter')}
                  >
                    <Maximize2 size={13} /> {t.analytics?.viewModeScatter || 'Dispersión'}
                  </button>
                  <button
                    className={`btn ${outlierViewMode === 'diff' ? 'btn-primary' : 'btn-outline'}`}
                    style={{ padding: '4px 10px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                    onClick={() => setOutlierViewMode('diff')}
                    data-testid="outlier-diff-view-btn"
                  >
                    <ArrowLeftRight size={13} /> {t.analytics?.viewModeDiff || 'Comparador Diff'}
                  </button>
                </div>
              </div>

              {/* RENDERIZADOR SVG: MODO BOXPLOT */}
              {outlierViewMode === 'boxplot' && (
                <div
                  style={{
                    backgroundColor: 'var(--bg-input)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '10px',
                    padding: '20px 16px',
                    marginBottom: '20px',
                  }}
                >
                  {(() => {
                    const b = activeBoxPlot;
                    const minVal = b.min;
                    const maxVal = b.max;
                    const span = maxVal - minVal || 1.0;
                    const pad = span * 0.1;
                    const dMin = minVal - pad;
                    const dMax = maxVal + pad;

                    const width = 640;
                    const height = 180;
                    const margin = { left: 40, right: 40 };
                    const plotW = width - margin.left - margin.right;
                    const centerY = 80;
                    const boxH = 44;

                    const scale = (val: number) => margin.left + ((val - dMin) / (dMax - dMin || 1)) * plotW;

                    const xMin = scale(b.min);
                    const xLw = scale(b.lower_whisker);
                    const xQ1 = scale(b.q1);
                    const xMed = scale(b.median);
                    const xMean = scale(b.mean);
                    const xQ3 = scale(b.q3);
                    const xUw = scale(b.upper_whisker);
                    const xMax = scale(b.max);

                    return (
                      <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto', display: 'block' }} role="img" aria-label={`Boxplot de ${b.column}`}>
                        {/* Eje de referencia */}
                        <line x1={margin.left} y1={centerY + boxH / 2 + 30} x2={width - margin.right} y2={centerY + boxH / 2 + 30} stroke="var(--border-color)" strokeWidth="1.5" />

                        {/* Ticks de valores */}
                        <text x={xLw} y={centerY + boxH / 2 + 45} fill="var(--text-muted)" fontSize="10" textAnchor="middle">
                          LW: {b.lower_whisker}
                        </text>
                        <text x={xQ1} y={centerY - boxH / 2 - 8} fill="var(--text-muted)" fontSize="10" textAnchor="middle">
                          Q1: {b.q1}
                        </text>
                        <text x={xMed} y={centerY + boxH / 2 + 45} fill="var(--primary)" fontSize="11" fontWeight="700" textAnchor="middle">
                          Med: {b.median}
                        </text>
                        <text x={xQ3} y={centerY - boxH / 2 - 8} fill="var(--text-muted)" fontSize="10" textAnchor="middle">
                          Q3: {b.q3}
                        </text>
                        <text x={xUw} y={centerY + boxH / 2 + 45} fill="var(--text-muted)" fontSize="10" textAnchor="middle">
                          UW: {b.upper_whisker}
                        </text>

                        {/* Líneas de bigotes */}
                        <line x1={xLw} y1={centerY} x2={xQ1} y2={centerY} stroke="var(--primary)" strokeWidth="2" strokeDasharray="3 3" />
                        <line x1={xQ3} y1={centerY} x2={xUw} y2={centerY} stroke="var(--primary)" strokeWidth="2" strokeDasharray="3 3" />

                        {/* Tapas de bigotes */}
                        <line x1={xLw} y1={centerY - 16} x2={xLw} y2={centerY + 16} stroke="var(--primary)" strokeWidth="2.5" strokeLinecap="round" />
                        <line x1={xUw} y1={centerY - 16} x2={xUw} y2={centerY + 16} stroke="var(--primary)" strokeWidth="2.5" strokeLinecap="round" />

                        {/* Caja IQR (Q1 a Q3) */}
                        <rect
                          x={Math.min(xQ1, xQ3)}
                          y={centerY - boxH / 2}
                          width={Math.abs(xQ3 - xQ1) || 4}
                          height={boxH}
                          fill="rgba(59, 130, 246, 0.15)"
                          stroke="var(--primary)"
                          strokeWidth="2"
                          rx="4"
                        />

                        {/* Línea de Mediana */}
                        <line x1={xMed} y1={centerY - boxH / 2} x2={xMed} y2={centerY + boxH / 2} stroke="var(--primary)" strokeWidth="3.5" />

                        {/* Indicador de Media (Rombo) */}
                        <polygon
                          points={`${xMean},${centerY - 6} ${xMean + 5},${centerY} ${xMean},${centerY + 6} ${xMean - 5},${centerY}`}
                          fill="var(--accent-emerald)"
                          stroke="#ffffff"
                          strokeWidth="1"
                        />

                        {/* Outliers individuales fuera de los bigotes */}
                        {b.sample_outliers.map((outVal, idx) => {
                          const ox = scale(outVal);
                          return (
                            <g key={idx}>
                              <circle cx={ox} cy={centerY} r="6" fill="var(--accent-rose)" stroke="#ffffff" strokeWidth="1.5" />
                              <text x={ox} y={centerY - 10} fill="var(--accent-rose)" fontSize="9" fontWeight="700" textAnchor="middle">
                                {outVal}
                              </text>
                            </g>
                          );
                        })}
                      </svg>
                    );
                  })()}
                </div>
              )}

              {/* RENDERIZADOR SVG: MODO SCATTER DE OUTLIERS */}
              {outlierViewMode === 'scatter' && outlierViz.scatter_points && (
                <div
                  style={{
                    backgroundColor: 'var(--bg-input)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '10px',
                    padding: '16px',
                    marginBottom: '20px',
                    position: 'relative',
                  }}
                >
                  {(() => {
                    const b = activeBoxPlot;
                    const pts = outlierViz.scatter_points;
                    const vals = pts.map((p) => p.y_value);
                    const minY = Math.min(b.min, ...vals);
                    const maxY = Math.max(b.max, ...vals);
                    const padY = (maxY - minY) * 0.1 || 1.0;
                    const dMinY = minY - padY;
                    const dMaxY = maxY + padY;

                    const width = 640;
                    const height = 260;
                    const margin = { top: 20, right: 30, bottom: 35, left: 55 };
                    const plotW = width - margin.left - margin.right;
                    const plotH = height - margin.top - margin.bottom;

                    const scaleX = (idx: number) => margin.left + ((idx - 1) / (pts.length || 1)) * plotW;
                    const scaleY = (val: number) =>
                      height - margin.bottom - ((val - dMinY) / (dMaxY - dMinY || 1)) * plotH;

                    const yLower = scaleY(b.lower_whisker);
                    const yUpper = scaleY(b.upper_whisker);

                    return (
                      <div>
                        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: 'auto', display: 'block' }} role="img" aria-label={`Scatter de outliers para ${b.column}`}>
                          {/* Líneas de Límites IQR */}
                          <line x1={margin.left} y1={yUpper} x2={width - margin.right} y2={yUpper} stroke="var(--accent-rose)" strokeDasharray="5 4" strokeWidth="1.5" />
                          <text x={width - margin.right + 4} y={yUpper + 3} fill="var(--accent-rose)" fontSize="9" textAnchor="start">
                            Max IQR
                          </text>

                          <line x1={margin.left} y1={yLower} x2={width - margin.right} y2={yLower} stroke="var(--accent-rose)" strokeDasharray="5 4" strokeWidth="1.5" />
                          <text x={width - margin.right + 4} y={yLower + 3} fill="var(--accent-rose)" fontSize="9" textAnchor="start">
                            Min IQR
                          </text>

                          {/* Puntos */}
                          {pts.map((p, idx) => {
                            const px = scaleX(p.x_value);
                            const py = scaleY(p.y_value);
                            return (
                              <circle
                                key={idx}
                                cx={px}
                                cy={py}
                                r={p.is_outlier ? '6' : '3.5'}
                                fill={p.is_outlier ? 'var(--accent-rose)' : 'var(--primary)'}
                                stroke="#ffffff"
                                strokeWidth="1"
                                style={{ cursor: 'pointer' }}
                                onMouseEnter={() =>
                                  setHoveredOutlierPoint({
                                    x: px,
                                    y: py,
                                    valY: p.y_value,
                                    label: p.label || `Fila #${p.row_index + 1}`,
                                    isOutlier: p.is_outlier,
                                  })
                                }
                                onMouseLeave={() => setHoveredOutlierPoint(null)}
                              />
                            );
                          })}
                        </svg>

                        {hoveredOutlierPoint && (
                          <div
                            style={{
                              position: 'absolute',
                              top: Math.max(10, (hoveredOutlierPoint.y / 260) * 100 - 15) + '%',
                              left: Math.min(80, (hoveredOutlierPoint.x / 640) * 100 + 3) + '%',
                              backgroundColor: 'rgba(15, 23, 42, 0.95)',
                              color: '#ffffff',
                              padding: '6px 10px',
                              borderRadius: '6px',
                              fontSize: '0.75rem',
                              pointerEvents: 'none',
                              boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                              zIndex: 10,
                              border: `1px solid ${hoveredOutlierPoint.isOutlier ? 'var(--accent-rose)' : 'var(--primary)'}`,
                            }}
                          >
                            <div>{hoveredOutlierPoint.label}</div>
                            <div>
                              Valor: <strong>{hoveredOutlierPoint.valY}</strong>{' '}
                              {hoveredOutlierPoint.isOutlier && <span style={{ color: 'var(--accent-rose)' }}>[OUTLIER]</span>}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </div>
              )}

              {/* RENDERIZADOR SVG: MODO COMPARADOR DIFF (CRUDO VS LIMPIO) */}
              {outlierViewMode === 'diff' && outlierViz.scatter_points && (
                <div
                  style={{
                    backgroundColor: 'var(--bg-input)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '10px',
                    padding: '16px',
                    marginBottom: '20px',
                    position: 'relative',
                  }}
                  data-testid="outlier-diff-container"
                >
                  {/* Resumen de Resolución de Outliers */}
                  {outlierViz.diff_summary && (
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                        gap: '10px',
                        marginBottom: '16px',
                        paddingBottom: '14px',
                        borderBottom: '1px solid var(--border-color)',
                      }}
                    >
                      <div style={{ backgroundColor: 'var(--card-bg, rgba(255,255,255,0.03))', padding: '10px 12px', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{t.analytics?.rawOutliers || 'Outliers en Crudo'}</div>
                        <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-rose, #f43f5e)', marginTop: '2px' }}>
                          {outlierViz.diff_summary.raw_outliers_count}
                        </div>
                      </div>
                      <div style={{ backgroundColor: 'var(--card-bg, rgba(255,255,255,0.03))', padding: '10px 12px', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{t.analytics?.cleanOutliers || 'Outliers en Limpio'}</div>
                        <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--primary)', marginTop: '2px' }}>
                          {outlierViz.diff_summary.clean_outliers_count}
                        </div>
                      </div>
                      <div style={{ backgroundColor: 'var(--card-bg, rgba(255,255,255,0.03))', padding: '10px 12px', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{t.analytics?.resolvedOutliers || 'Anomalías Resueltas'}</div>
                        <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-emerald, #10b981)', marginTop: '2px' }}>
                          {outlierViz.diff_summary.resolved_outliers_count}
                        </div>
                      </div>
                      <div style={{ backgroundColor: 'var(--card-bg, rgba(255,255,255,0.03))', padding: '10px 12px', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{t.analytics?.reductionRate || 'Tasa de Reducción'}</div>
                        <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-emerald, #10b981)', marginTop: '2px' }}>
                          {outlierViz.diff_summary.reduction_percentage}%
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Barra de Filtro y Leyenda */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px', marginBottom: '12px' }}>
                    <div style={{ display: 'flex', gap: '14px', alignItems: 'center', fontSize: '0.75rem' }}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                        <span style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: 'var(--accent-rose, #f43f5e)', display: 'inline-block' }} />
                        {t.analytics?.rawVal || 'Valor Crudo'}
                      </span>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                        <span style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: 'var(--primary)', display: 'inline-block' }} />
                        {t.analytics?.cleanVal || 'Valor Limpio'}
                      </span>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                        <span style={{ width: '14px', height: '2px', borderTop: '2px dashed var(--accent-amber, #f59e0b)', display: 'inline-block' }} />
                        {t.analytics?.diffStatusClamped || 'Ajuste / Clamp'}
                      </span>
                    </div>

                    <button
                      type="button"
                      className={`btn ${diffOnlyModified ? 'btn-primary' : 'btn-outline'}`}
                      style={{ padding: '4px 10px', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '5px' }}
                      onClick={() => setDiffOnlyModified((prev) => !prev)}
                      data-testid="toggle-diff-modified-btn"
                    >
                      <Filter size={12} />
                      {diffOnlyModified
                        ? (t.analytics?.filterAllPoints || 'Ver Todos')
                        : (t.analytics?.filterOnlyModified || 'Solo Anomalías Modificadas')}
                    </button>
                  </div>

                  {(() => {
                    const b = activeBoxPlot;
                    const allPts = outlierViz.scatter_points || [];
                    const pts = diffOnlyModified ? allPts.filter((p) => p.was_modified || p.is_outlier) : allPts;

                    const vals: number[] = [];
                    pts.forEach((p) => {
                      vals.push(p.y_value);
                      if (p.raw_y_value !== undefined && p.raw_y_value !== null) {
                        vals.push(p.raw_y_value);
                      }
                    });
                    if (vals.length === 0) vals.push(b.median);

                    const minY = Math.min(b.min, ...vals);
                    const maxY = Math.max(b.max, ...vals);
                    const padY = (maxY - minY) * 0.1 || 1.0;
                    const dMinY = minY - padY;
                    const dMaxY = maxY + padY;

                    const width = 640;
                    const height = 280;
                    const margin = { top: 20, right: 35, bottom: 35, left: 55 };
                    const plotW = width - margin.left - margin.right;
                    const plotH = height - margin.top - margin.bottom;

                    const scaleX = (idx: number) => margin.left + ((idx - 1) / (pts.length || 1)) * plotW;
                    const scaleY = (val: number) => height - margin.bottom - ((val - dMinY) / (dMaxY - dMinY || 1)) * plotH;

                    const yLower = scaleY(b.lower_whisker);
                    const yUpper = scaleY(b.upper_whisker);

                    return (
                      <div>
                        <svg
                          viewBox={`0 0 ${width} ${height}`}
                          style={{ width: '100%', height: 'auto', display: 'block' }}
                          role="img"
                          aria-label={`Comparador scatter diff para ${b.column}`}
                        >
                          {/* Líneas de Límites IQR */}
                          <line x1={margin.left} y1={yUpper} x2={width - margin.right} y2={yUpper} stroke="var(--accent-rose, #f43f5e)" strokeDasharray="5 4" strokeWidth="1.5" />
                          <text x={width - margin.right + 4} y={yUpper + 3} fill="var(--accent-rose, #f43f5e)" fontSize="9" textAnchor="start">
                            Max IQR
                          </text>

                          <line x1={margin.left} y1={yLower} x2={width - margin.right} y2={yLower} stroke="var(--accent-rose, #f43f5e)" strokeDasharray="5 4" strokeWidth="1.5" />
                          <text x={width - margin.right + 4} y={yLower + 3} fill="var(--accent-rose, #f43f5e)" fontSize="9" textAnchor="start">
                            Min IQR
                          </text>

                          {/* Líneas y Puntos */}
                          {pts.map((p, idx) => {
                            const px = scaleX(idx + 1);
                            const pyClean = scaleY(p.y_value);
                            const hasRaw = p.raw_y_value !== undefined && p.raw_y_value !== null;
                            const pyRaw = hasRaw ? scaleY(p.raw_y_value!) : null;

                            return (
                              <g key={idx}>
                                {p.was_modified && pyRaw !== null && (
                                  <>
                                    <line
                                      x1={px}
                                      y1={pyRaw}
                                      x2={px}
                                      y2={pyClean}
                                      stroke="var(--accent-amber, #f59e0b)"
                                      strokeWidth="1.5"
                                      strokeDasharray="3 3"
                                    />
                                    <circle
                                      cx={px}
                                      cy={pyRaw}
                                      r="4"
                                      fill="var(--accent-rose, #f43f5e)"
                                      stroke="#ffffff"
                                      strokeWidth="1"
                                      opacity="0.85"
                                    />
                                  </>
                                )}
                                <circle
                                  cx={px}
                                  cy={pyClean}
                                  r={p.was_modified ? '5' : p.is_outlier ? '5.5' : '3.5'}
                                  fill={p.was_modified ? 'var(--accent-emerald, #10b981)' : p.is_outlier ? 'var(--accent-rose, #f43f5e)' : 'var(--primary)'}
                                  stroke="#ffffff"
                                  strokeWidth="1"
                                  style={{ cursor: 'pointer' }}
                                  onMouseEnter={() =>
                                    setHoveredOutlierPoint({
                                      x: px,
                                      y: pyClean,
                                      valY: p.y_value,
                                      label: p.label || `Fila #${p.row_index + 1}`,
                                      isOutlier: p.is_outlier,
                                      rawY: p.raw_y_value,
                                      wasModified: p.was_modified,
                                      diffStatus: p.diff_status,
                                    })
                                  }
                                  onMouseLeave={() => setHoveredOutlierPoint(null)}
                                />
                              </g>
                            );
                          })}
                        </svg>

                        {hoveredOutlierPoint && (
                          <div
                            style={{
                              position: 'absolute',
                              top: Math.max(10, (hoveredOutlierPoint.y / 280) * 100 - 15) + '%',
                              left: Math.min(75, (hoveredOutlierPoint.x / 640) * 100 + 3) + '%',
                              backgroundColor: 'rgba(15, 23, 42, 0.95)',
                              color: '#ffffff',
                              padding: '8px 12px',
                              borderRadius: '6px',
                              fontSize: '0.75rem',
                              pointerEvents: 'none',
                              boxShadow: '0 4px 14px rgba(0,0,0,0.35)',
                              zIndex: 10,
                              border: `1px solid ${hoveredOutlierPoint.wasModified ? 'var(--accent-emerald, #10b981)' : 'var(--primary)'}`,
                            }}
                          >
                            <div style={{ fontWeight: 600 }}>{hoveredOutlierPoint.label}</div>
                            {hoveredOutlierPoint.rawY !== undefined && hoveredOutlierPoint.rawY !== null && (
                              <div style={{ color: 'var(--text-muted)', marginTop: '2px' }}>
                                {t.analytics?.rawVal || 'Crudo'}: <strong style={{ color: 'var(--accent-rose, #f43f5e)' }}>{hoveredOutlierPoint.rawY}</strong>
                              </div>
                            )}
                            <div style={{ marginTop: '2px' }}>
                              {t.analytics?.cleanVal || 'Limpio'}: <strong style={{ color: 'var(--accent-emerald, #10b981)' }}>{hoveredOutlierPoint.valY}</strong>{' '}
                              {hoveredOutlierPoint.isOutlier && <span style={{ color: 'var(--accent-rose, #f43f5e)' }}>[OUTLIER]</span>}
                            </div>
                            {hoveredOutlierPoint.wasModified && (
                              <div style={{ color: 'var(--accent-amber, #f59e0b)', fontSize: '0.7rem', marginTop: '4px' }}>
                                {hoveredOutlierPoint.diffStatus === 'resolved_outlier'
                                  ? (t.analytics?.diffStatusResolved || 'Anomalía corregida al rango')
                                  : (t.analytics?.diffStatusClamped || 'Valor acotado por regla clamp')}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Mini Tabla de Evidencia de Anomalías Modificadas */}
                        {pts.some((p) => p.was_modified) && (
                          <div style={{ marginTop: '16px', overflowX: 'auto' }}>
                            <table style={{ width: '100%', fontSize: '0.75rem', borderCollapse: 'collapse', textAlign: 'left' }}>
                              <thead>
                                <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
                                  <th style={{ padding: '6px 8px' }}>Registro</th>
                                  <th style={{ padding: '6px 8px' }}>{t.analytics?.rawVal || 'Crudo'}</th>
                                  <th style={{ padding: '6px 8px' }}>{t.analytics?.cleanVal || 'Limpio'}</th>
                                  <th style={{ padding: '6px 8px' }}>Variación</th>
                                  <th style={{ padding: '6px 8px' }}>Estado</th>
                                </tr>
                              </thead>
                              <tbody>
                                {pts
                                  .filter((p) => p.was_modified)
                                  .slice(0, 5)
                                  .map((p, idx) => (
                                    <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                      <td style={{ padding: '6px 8px', fontWeight: 600 }}>{p.label}</td>
                                      <td style={{ padding: '6px 8px', color: 'var(--accent-rose, #f43f5e)' }}>{p.raw_y_value ?? 'N/A'}</td>
                                      <td style={{ padding: '6px 8px', color: 'var(--accent-emerald, #10b981)' }}>{p.y_value}</td>
                                      <td style={{ padding: '6px 8px', fontFamily: 'monospace' }}>
                                        {p.raw_y_value != null ? (p.y_value - p.raw_y_value > 0 ? `+${(p.y_value - p.raw_y_value).toFixed(2)}` : (p.y_value - p.raw_y_value).toFixed(2)) : 'N/A'}
                                      </td>
                                      <td style={{ padding: '6px 8px' }}>
                                        <span
                                          style={{
                                            padding: '2px 6px',
                                            borderRadius: '4px',
                                            backgroundColor: p.diff_status === 'resolved_outlier' ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)',
                                            color: p.diff_status === 'resolved_outlier' ? 'var(--accent-emerald, #10b981)' : 'var(--accent-amber, #f59e0b)',
                                            fontWeight: 600,
                                          }}
                                        >
                                          {p.diff_status === 'resolved_outlier' ? 'Resuelto' : 'Acotado'}
                                        </span>
                                      </td>
                                    </tr>
                                  ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </div>
              )}

              {/* Tarjetas Estadísticas del BoxPlot */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                  gap: '10px',
                }}
              >
                <div style={{ backgroundColor: 'var(--bg-input)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>{t.analytics?.outlierStats?.min || 'Mínimo'}</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>{activeBoxPlot.min}</div>
                </div>
                <div style={{ backgroundColor: 'var(--bg-input)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>{t.analytics?.outlierStats?.q1 || 'Q1 (25%)'}</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>{activeBoxPlot.q1}</div>
                </div>
                <div style={{ backgroundColor: 'var(--bg-input)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>{t.analytics?.outlierStats?.median || 'Mediana (Q2)'}</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--primary)' }}>{activeBoxPlot.median}</div>
                </div>
                <div style={{ backgroundColor: 'var(--bg-input)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>{t.analytics?.outlierStats?.q3 || 'Q3 (75%)'}</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>{activeBoxPlot.q3}</div>
                </div>
                <div style={{ backgroundColor: 'var(--bg-input)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>{t.analytics?.outlierStats?.max || 'Máximo'}</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>{activeBoxPlot.max}</div>
                </div>
                <div style={{ backgroundColor: 'var(--bg-input)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>{t.analytics?.outlierStats?.iqr || 'Rango IQR'}</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>{activeBoxPlot.iqr}</div>
                </div>
                <div style={{ backgroundColor: 'var(--bg-input)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>{t.analytics?.detectedOutliers || 'Outliers'}</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: activeBoxPlot.outliers_count > 0 ? 'var(--accent-rose)' : 'var(--accent-emerald)' }}>
                    {activeBoxPlot.outliers_count} ({activeBoxPlot.outlier_percentage}%)
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* PESTAÑA 4: INTEGRACIÓN POWER BI / EXCEL */}
      {activeTab === 'integration' && (() => {
        const guide = report?.integration_guide;
        const columns: IntegrationColumn[] = guide?.columns || ((guide as unknown as { columns_metadata?: IntegrationColumn[] })?.columns_metadata) || [];
        const daxMeasures: DaxMeasureItem[] = guide?.dax_measures || [];
        const excelFormulas: ExcelFormulaItem[] = guide?.excel_formulas || [];

        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <h4 style={{ fontSize: '1.05rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--primary)' }}>
                <Layers size={18} /> {t.powerBiExcel?.title || 'Guía de Integración y Fórmulas para Power BI y Excel'}
              </h4>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                {t.powerBiExcel?.powerBiDesc || 'Conecte y modele el dataset depurado directamente en Microsoft Power BI Desktop o Servicio con medidas DAX y transformaciones M optimizadas adaptadas a sus columnas reales.'}
              </p>
            </div>

            {/* Banner de contexto del dataset */}
            {guide && (
              <div
                style={{
                  backgroundColor: 'rgba(59, 130, 246, 0.08)',
                  border: '1px solid rgba(59, 130, 246, 0.25)',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: '0.85rem',
                  flexWrap: 'wrap',
                  gap: '8px',
                }}
              >
                <div>
                  <strong>Tabla de Modelo:</strong> <code style={{ color: 'var(--primary)' }}>'{guide.table_name || 'DataFlow_Model'}'</code> · <strong>Total Registros:</strong> {(guide.row_count ?? 0).toLocaleString()} filas · <strong>Columnas tipadas:</strong> {columns.length}
                </div>
                <span className="badge badge-blue">Generación Adaptativa v1.9.0</span>
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '16px' }}>
              {/* Tarjeta Microsoft Power BI */}
              <div
                style={{
                  backgroundColor: 'var(--bg-input)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '10px',
                  padding: '16px 20px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '14px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                  <h5 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Award size={16} /> {t.powerBiExcel?.tabPowerBi || 'Microsoft Power BI'}
                  </h5>
                  <span className="badge badge-amber">TMDL + PBIP + DAX</span>
                </div>

                {/* Barra de Acciones de Exportación Directa */}
                <div>
                  <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                    Exportación directa de modelo semántico:
                  </label>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <a
                      href={api.getPbipExportUrl(runId)}
                      download={`proyecto_powerbi_${runId}.zip`}
                      className="btn btn-primary"
                      style={{ padding: '6px 12px', fontSize: '0.75rem', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '5px' }}
                      title="Descargar paquete completo de proyecto Power BI Developer Mode (.pbip) en archivo ZIP"
                    >
                      <FileDown size={14} /> {t.powerBiExcel?.btnExportPbip || 'Proyecto PBIP (.zip)'}
                    </a>
                    <a
                      href={api.getTmdlExportUrl(runId)}
                      download={`modelo_powerbi_${runId}.tmdl`}
                      className="btn btn-outline"
                      style={{ padding: '6px 12px', fontSize: '0.75rem', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '5px' }}
                      title="Descargar definición del modelo semántico en formato TMDL"
                    >
                      <FileDown size={14} /> {t.powerBiExcel?.btnExportTmdl || 'Modelo TMDL (.tmdl)'}
                    </a>
                    <a
                      href={api.getDaxExportUrl(runId)}
                      download={`medidas_powerbi_${runId}.dax`}
                      className="btn btn-outline"
                      style={{ padding: '6px 12px', fontSize: '0.75rem', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '5px' }}
                      title="Descargar script de medidas DAX calculadas (.dax)"
                    >
                      <FileDown size={14} /> {t.powerBiExcel?.btnExportDax || 'Medidas DAX (.dax)'}
                    </a>
                  </div>
                </div>

                {/* Selector de Vista de Código */}
                <div style={{ display: 'flex', gap: '6px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
                  <button
                    className={`btn ${powerBiCodeView === 'dax' ? 'btn-primary' : 'btn-outline'}`}
                    style={{ padding: '4px 10px', fontSize: '0.725rem' }}
                    onClick={() => setPowerBiCodeView('dax')}
                  >
                    {t.powerBiExcel?.tabDax || 'Medidas DAX'} ({daxMeasures.length})
                  </button>
                  <button
                    className={`btn ${powerBiCodeView === 'powerquery' ? 'btn-primary' : 'btn-outline'}`}
                    style={{ padding: '4px 10px', fontSize: '0.725rem' }}
                    onClick={() => setPowerBiCodeView('powerquery')}
                  >
                    {t.powerBiExcel?.tabMQuery || 'Power Query M'}
                  </button>
                  <button
                    className={`btn ${powerBiCodeView === 'tmdl' ? 'btn-primary' : 'btn-outline'}`}
                    style={{ padding: '4px 10px', fontSize: '0.725rem' }}
                    onClick={() => setPowerBiCodeView('tmdl')}
                  >
                    {t.powerBiExcel?.tabTmdl || 'Modelo TMDL'}
                  </button>
                  {guide?.star_schema && guide.star_schema.dimensions.length > 0 && (
                    <button
                      className={`btn ${powerBiCodeView === 'star' ? 'btn-primary' : 'btn-outline'}`}
                      style={{ padding: '4px 10px', fontSize: '0.725rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                      onClick={() => setPowerBiCodeView('star')}
                      data-testid="star-schema-view-btn"
                    >
                      <Star size={12} /> {t.powerBiExcel?.tabStarSchema || 'Esquema Estrella'} ({guide.star_schema.dimension_count})
                    </button>
                  )}
                </div>

                {/* VISTA 1: Medidas DAX Adaptadas */}
                {powerBiCodeView === 'dax' && (
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px', flexWrap: 'wrap', gap: '6px' }}>
                      <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-main)' }}>
                        {t.powerBiExcel?.daxFormulaLabel || 'Medidas DAX Adaptadas al Dataset'}:
                      </span>
                      <button
                        className="btn btn-outline"
                        style={{ padding: '3px 8px', fontSize: '0.725rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                        onClick={() => {
                          const allDax = guide?.dax_script || (daxMeasures.length > 0
                            ? daxMeasures.map((m) => `// ${m.description}\n${m.formula}`).join('\n\n')
                            : `Total_Registros = COUNTROWS('DataFlow_Cleaned_Dataset')`);
                          navigator.clipboard.writeText(allDax);
                          setCopiedSnippet('dax');
                          setTimeout(() => setCopiedSnippet(null), 2000);
                        }}
                      >
                        {copiedSnippet === 'dax' ? <Check size={12} style={{ color: 'var(--accent-emerald)' }} /> : <Copy size={12} />}
                        {copiedSnippet === 'dax' ? (t.powerBiExcel?.copied || '¡Copiado!') : 'Copiar todas las medidas'}
                      </button>
                    </div>

                    {daxMeasures.length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '240px', overflowY: 'auto' }}>
                        {daxMeasures.map((measure, idx) => {
                          const formulaCode = measure.formula || (measure as any).dax_formula || '';
                          return (
                            <div
                              key={idx}
                              style={{
                                backgroundColor: 'var(--bg-main)',
                                border: '1px solid var(--border-color)',
                                borderRadius: '6px',
                                padding: '8px 10px',
                              }}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                  <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--primary)' }}>
                                    [{measure.name}]
                                  </span>
                                  {measure.display_folder && (
                                    <span className="badge badge-amber" style={{ fontSize: '0.65rem', padding: '1px 5px' }}>
                                      {measure.display_folder}
                                    </span>
                                  )}
                                  {measure.format_string && (
                                    <span style={{ fontSize: '0.675rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                                      {measure.format_string}
                                    </span>
                                  )}
                                </div>
                                <button
                                  className="btn btn-outline"
                                  style={{ padding: '2px 6px', fontSize: '0.675rem' }}
                                  onClick={() => {
                                    navigator.clipboard.writeText(formulaCode);
                                    setCopiedSnippet(`dax-${idx}`);
                                    setTimeout(() => setCopiedSnippet(null), 1500);
                                  }}
                                >
                                  {copiedSnippet === `dax-${idx}` ? '¡Copiado!' : 'Copiar'}
                                </button>
                              </div>
                              <p style={{ margin: '0 0 4px 0', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                                {measure.description}
                              </p>
                              <pre
                                style={{
                                  margin: 0,
                                  fontSize: '0.725rem',
                                  fontFamily: 'var(--font-mono)',
                                  color: 'var(--primary)',
                                  whiteSpace: 'pre-wrap',
                                  wordBreak: 'break-word',
                                }}
                              >
                                {formulaCode}
                              </pre>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <pre
                        style={{
                          backgroundColor: 'var(--bg-main)',
                          border: '1px solid var(--border-color)',
                          padding: '10px 12px',
                          borderRadius: '6px',
                          fontSize: '0.75rem',
                          fontFamily: 'var(--font-mono)',
                          color: 'var(--primary)',
                          overflowX: 'auto',
                          margin: 0,
                        }}
                      >
{`Total_Registros = COUNTROWS('DataFlow_Cleaned_Dataset')

Registros_Validos = 
CALCULATE(
    COUNTROWS('DataFlow_Cleaned_Dataset'),
    'DataFlow_Cleaned_Dataset'[is_outlier] = FALSE()
)

Score_Calidad_Pct = 
DIVIDE([Registros_Validos], [Total_Registros], 1.0) * 100`}
                      </pre>
                    )}
                  </div>
                )}

                {/* VISTA 2: Consulta M (Power Query) */}
                {powerBiCodeView === 'powerquery' && (
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px', flexWrap: 'wrap', gap: '6px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-main)' }}>
                          {t.powerBiExcel?.mQueryLabel || 'Power Query M'}:
                        </span>
                        <div style={{ display: 'flex', gap: '4px' }}>
                          <button
                            className={`btn ${selectedPqFormat === 'csv' ? 'btn-primary' : 'btn-outline'}`}
                            style={{ padding: '2px 8px', fontSize: '0.675rem' }}
                            onClick={() => setSelectedPqFormat('csv')}
                          >
                            CSV
                          </button>
                          <button
                            className={`btn ${selectedPqFormat === 'parquet' ? 'btn-primary' : 'btn-outline'}`}
                            style={{ padding: '2px 8px', fontSize: '0.675rem' }}
                            onClick={() => setSelectedPqFormat('parquet')}
                          >
                            Parquet
                          </button>
                        </div>
                      </div>
                      <button
                        className="btn btn-outline"
                        style={{ padding: '3px 8px', fontSize: '0.725rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                        onClick={() => {
                          const mCode = guide
                            ? (selectedPqFormat === 'parquet' ? (guide.power_query_m_parquet || guide.power_query_m_csv) : guide.power_query_m_csv)
                            : `let\n    Source = Csv.Document(File.Contents("DataFlow_Cleaned_Dataset.csv"),[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),\n    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),\n    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{{"run_id", type text}})\nin\n    #"Changed Type"`;
                          navigator.clipboard.writeText(mCode);
                          setCopiedSnippet('m');
                          setTimeout(() => setCopiedSnippet(null), 2000);
                        }}
                      >
                        {copiedSnippet === 'm' ? <Check size={12} style={{ color: 'var(--accent-emerald)' }} /> : <Copy size={12} />}
                        {copiedSnippet === 'm' ? (t.powerBiExcel?.copied || '¡Copiado!') : (t.powerBiExcel?.copySnippet || 'Copiar')}
                      </button>
                    </div>
                    <pre
                      style={{
                        backgroundColor: 'var(--bg-main)',
                        border: '1px solid var(--border-color)',
                        padding: '10px 12px',
                        borderRadius: '6px',
                        fontSize: '0.725rem',
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--text-main)',
                        overflowX: 'auto',
                        margin: 0,
                        maxHeight: '240px',
                      }}
                    >
                      {guide
                        ? (selectedPqFormat === 'parquet' ? (guide.power_query_m_parquet || guide.power_query_m_csv) : guide.power_query_m_csv)
                        : `let\n    Source = Csv.Document(File.Contents("DataFlow_Cleaned_Dataset.csv"),[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),\n    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),\n    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{{"run_id", type text}})\nin\n    #"Changed Type"`}
                    </pre>
                  </div>
                )}

                {/* VISTA 3: Definición TMDL Semántica */}
                {powerBiCodeView === 'tmdl' && (
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px', flexWrap: 'wrap', gap: '6px' }}>
                      <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-main)' }}>
                        Definición TMDL (Power BI / Fabric):
                      </span>
                      <button
                        className="btn btn-outline"
                        style={{ padding: '3px 8px', fontSize: '0.725rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                        onClick={() => {
                          const tmdlText = guide?.tmdl_table_definition || '';
                          navigator.clipboard.writeText(tmdlText);
                          setCopiedSnippet('tmdl');
                          setTimeout(() => setCopiedSnippet(null), 2000);
                        }}
                      >
                        {copiedSnippet === 'tmdl' ? <Check size={12} style={{ color: 'var(--accent-emerald)' }} /> : <Copy size={12} />}
                        {copiedSnippet === 'tmdl' ? (t.powerBiExcel?.copied || '¡Copiado!') : (t.powerBiExcel?.copySnippet || 'Copiar')}
                      </button>
                    </div>
                    <pre
                      style={{
                        backgroundColor: 'var(--bg-main)',
                        border: '1px solid var(--border-color)',
                        padding: '10px 12px',
                        borderRadius: '6px',
                        fontSize: '0.725rem',
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--primary)',
                        overflowX: 'auto',
                        margin: 0,
                        maxHeight: '240px',
                        whiteSpace: 'pre',
                      }}
                    >
                      {guide?.tmdl_table_definition || '// Definición TMDL generada automáticamente al depurar el dataset.'}
                    </pre>
                  </div>
                )}

                {/* VISTA 4: Esquema Estrella (diagrama a ancho completo bajo la rejilla) */}
                {powerBiCodeView === 'star' && guide?.star_schema && (
                  <p style={{ fontSize: '0.775rem', color: 'var(--text-muted)', margin: 0, display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Star size={14} style={{ color: '#f59e0b', flexShrink: 0 }} />
                    {t.powerBiExcel?.starSchemaDesc || 'Vista previa interactiva del modelo semántico antes de cargarlo en Power BI.'}
                  </p>
                )}
              </div>

              {/* Tarjeta Microsoft Excel (Multi-Categoría Dinámica) */}
              <div
                style={{
                  backgroundColor: 'var(--bg-input)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '10px',
                  padding: '16px 20px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '14px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                  <h5 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#10b981', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Award size={16} /> {t.powerBiExcel?.tabExcel || 'Microsoft Excel'}
                  </h5>
                  <span className="badge badge-emerald">Fórmulas Dinámicas Adaptativas</span>
                </div>

                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
                  {t.powerBiExcel?.excelDesc || 'Fórmulas nativas adaptadas a las columnas cuantitativas, letras de columna y rangos reales de este dataset.'}
                </p>

                {/* Selector de Categorías de Fórmulas de Excel */}
                {excelFormulas.length > 0 && (
                  <div>
                    <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                      Tipo de Análisis / Categoría en Excel:
                    </label>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '10px' }}>
                      {[
                        { id: 'all', label: t.powerBiExcel?.excelCategoryAll || 'Todas' },
                        { id: 'outlier', label: t.powerBiExcel?.excelCategoryOutliers || 'Auditoría Outliers' },
                        { id: 'kpi', label: t.powerBiExcel?.excelCategoryKpis || 'KPIs & Estadísticas' },
                        { id: 'relative', label: t.powerBiExcel?.excelCategoryRelative || 'Participación %' },
                        { id: 'conditional', label: t.powerBiExcel?.excelCategoryConditional || 'Condicionales' },
                      ].map((cat) => (
                        <button
                          key={cat.id}
                          className={`btn ${selectedExcelCategory === cat.id ? 'btn-primary' : 'btn-outline'}`}
                          style={{ padding: '3px 8px', fontSize: '0.7rem' }}
                          onClick={() => {
                            setSelectedExcelCategory(cat.id);
                            setSelectedExcelMeasureIndex(0);
                          }}
                        >
                          {cat.label}
                        </button>
                      ))}
                    </div>

                    {/* Selector de Fórmulas según categoría activa */}
                    {(() => {
                      const filtered = selectedExcelCategory === 'all'
                        ? excelFormulas
                        : excelFormulas.filter((f) => f.category === selectedExcelCategory);
                      const displayList = filtered.length > 0 ? filtered : excelFormulas;

                      return (
                        <div>
                          <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                            Seleccionar fórmula o variable objetivo:
                          </label>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                            {displayList.map((item, idx) => {
                              const label = item.title || item.column || `Fórmula #${idx + 1}`;
                              return (
                                <button
                                  key={idx}
                                  className={`btn ${selectedExcelMeasureIndex === idx ? 'btn-primary' : 'btn-outline'}`}
                                  style={{ padding: '3px 8px', fontSize: '0.725rem' }}
                                  onClick={() => setSelectedExcelMeasureIndex(idx)}
                                >
                                  {label}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                )}

                {/* Visualizador de Fórmula Activa de Excel */}
                {(() => {
                  const filtered = selectedExcelCategory === 'all'
                    ? excelFormulas
                    : excelFormulas.filter((f) => f.category === selectedExcelCategory);
                  const displayList = filtered.length > 0 ? filtered : excelFormulas;
                  const currentItem = displayList[selectedExcelMeasureIndex] || displayList[0];
                  const formula = currentItem
                    ? (language === 'es' ? currentItem.formula_es : currentItem.formula_en)
                    : (language === 'es'
                        ? `=SI(ESNUMERO(A2); SI(Y(A2>=MEDIANA($A$2:$A$1000)-1,5*DESVEST($A$2:$A$1000); A2<=MEDIANA($A$2:$A$1000)+1,5*DESVEST($A$2:$A$1000)); "Válido"; "Outlier"); "Texto")`
                        : `=IF(ISNUMBER(A2), IF(AND(A2>=MEDIAN($A$2:$A$1000)-1.5*STDEV($A$2:$A$1000), A2<=MEDIAN($A$2:$A$1000)+1.5*STDEV($A$2:$A$1000)), "Valid", "Outlier"), "Text")`);
                  const desc = currentItem?.description || 'Fórmula de cálculo para hoja de cálculo.';
                  const targetCell = currentItem?.target_cell || `${currentItem?.excel_column_letter || 'A'}2`;
                  const title = currentItem?.title || 'Fórmula Excel';

                  return (
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px', flexWrap: 'wrap', gap: '6px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-main)' }}>
                            {title}:
                          </span>
                          <span className="badge badge-emerald" style={{ fontSize: '0.675rem', padding: '1px 6px' }}>
                            Pegar en: {targetCell}
                          </span>
                        </div>
                        <button
                          className="btn btn-outline"
                          style={{ padding: '3px 8px', fontSize: '0.725rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                          onClick={() => {
                            navigator.clipboard.writeText(formula);
                            setCopiedSnippet('excel');
                            setTimeout(() => setCopiedSnippet(null), 2000);
                          }}
                        >
                          {copiedSnippet === 'excel' ? <Check size={12} style={{ color: 'var(--accent-emerald)' }} /> : <Copy size={12} />}
                          {copiedSnippet === 'excel' ? (t.powerBiExcel?.copied || '¡Copiado!') : (t.powerBiExcel?.copySnippet || 'Copiar')}
                        </button>
                      </div>
                      <p style={{ margin: '0 0 6px 0', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {desc}
                      </p>
                      <pre
                        style={{
                          backgroundColor: 'var(--bg-main)',
                          border: '1px solid var(--border-color)',
                          padding: '10px 12px',
                          borderRadius: '6px',
                          fontSize: '0.75rem',
                          fontFamily: 'var(--font-mono)',
                          color: '#10b981',
                          overflowX: 'auto',
                          margin: 0,
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-word',
                        }}
                      >
                        {formula}
                      </pre>
                    </div>
                  );
                })()}

                {/* Resumen de Mapeo de Columnas */}
                {columns.length > 0 && (
                  <div style={{ marginTop: '4px' }}>
                    <span style={{ fontSize: '0.775rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
                      Mapeo de Columnas (Excel / Power BI):
                    </span>
                    <div style={{ maxHeight: '140px', overflowY: 'auto', border: '1px solid var(--border-color)', borderRadius: '6px' }}>
                      <table style={{ width: '100%', fontSize: '0.725rem', borderCollapse: 'collapse' }}>
                        <thead>
                          <tr style={{ backgroundColor: 'var(--bg-main)', borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                            <th style={{ padding: '4px 8px' }}>Columna</th>
                            <th style={{ padding: '4px 8px' }}>Excel</th>
                            <th style={{ padding: '4px 8px' }}>Tipo Power BI</th>
                          </tr>
                        </thead>
                        <tbody>
                          {columns.map((col, idx) => {
                            const pqType = col.power_bi_m_type || (col as any).power_query_type || 'type text';
                            const colLetter = col.excel_column_letter || 'A';
                            return (
                              <tr key={idx} style={{ borderBottom: '1px solid var(--border-color)' }}>
                                <td style={{ padding: '4px 8px', fontWeight: 600 }}>{col.name}</td>
                                <td style={{ padding: '4px 8px', color: 'var(--primary)' }}>Col {colLetter}</td>
                                <td style={{ padding: '4px 8px', color: 'var(--text-muted)' }}>{pqType}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                <div
                  style={{
                    backgroundColor: 'rgba(16, 185, 129, 0.08)',
                    border: '1px solid rgba(16, 185, 129, 0.25)',
                    borderRadius: '6px',
                    padding: '10px 12px',
                    fontSize: '0.775rem',
                    color: 'var(--text-muted)',
                  }}
                >
                  <strong>Nota regional:</strong> {t.powerBiExcel?.decimalNote || 'Ajuste los separadores de coma (,) o punto y coma (;) según la configuración regional de su sistema operativo.'}
                </div>
              </div>
            </div>

            {/* Diagrama interactivo del Modelo Estrella (a ancho completo) */}
            {powerBiCodeView === 'star' && guide?.star_schema && guide.star_schema.dimensions.length > 0 && (
              <div
                style={{
                  backgroundColor: 'var(--bg-input)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '10px',
                  padding: '16px 20px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                  <h5 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '6px', margin: 0 }}>
                    <Network size={16} /> {t.powerBiExcel?.tabStarSchema || 'Esquema Estrella'} — {guide.star_schema.fact_table}
                  </h5>
                  <span className="badge badge-amber">Vista Previa del Modelo Semántico</span>
                </div>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
                  {t.powerBiExcel?.starClickHint || 'Haz clic en una dimensión para ver su detalle'} · {guide.star_schema.dimension_count}{' '}
                  {(t.powerBiExcel?.starDimensions || 'Dimensiones').toLowerCase()} · {guide.star_schema.measures.length}{' '}
                  {(t.powerBiExcel?.starMeasures || 'Medidas').toLowerCase()} · {guide.star_schema.relationships.length}{' '}
                  {(t.powerBiExcel?.starRelationships || 'Relaciones').toLowerCase()}
                </p>
                <StarSchemaVisual schema={guide.star_schema} />
              </div>
            )}
          </div>
        );
      })()}

      {/* PESTAÑA 5: ALERTAS VISUALES, CONTROL DE DATA DRIFT Y RECOMENDACIONES PROACTIVAS */}
      {activeTab === 'drift' && (
        <div>
          {!report?.drift_analysis || report.drift_analysis.columns.length === 0 ? (
            <div
              style={{
                backgroundColor: 'var(--bg-input)',
                border: '1px dashed var(--border-color)',
                padding: '32px',
                textAlign: 'center',
                borderRadius: '10px',
                color: 'var(--text-muted)',
              }}
            >
              No se detectaron variables numéricas para calcular análisis de Data Drift.
            </div>
          ) : (
            <div>
              {/* Banner de Estado Global de Data Drift */}
              {(() => {
                const drift = report.drift_analysis;
                const isCrit = drift.overall_drift_status === 'critical';
                const isMod = drift.overall_drift_status === 'moderate';

                const bannerBg = isCrit
                  ? 'rgba(239, 68, 68, 0.12)'
                  : isMod
                  ? 'rgba(245, 158, 11, 0.12)'
                  : 'rgba(16, 185, 129, 0.12)';
                const bannerBorder = isCrit
                  ? 'var(--accent-rose)'
                  : isMod
                  ? 'var(--accent-amber)'
                  : 'var(--accent-emerald)';
                const statusText = isCrit
                  ? (t.driftAnalytics?.criticalStatus || 'Drift Crítico Detectado')
                  : isMod
                  ? (t.driftAnalytics?.moderateStatus || 'Desplazamiento Moderado de Percentiles')
                  : (t.driftAnalytics?.stableStatus || 'Distribución Estadística Estable');

                return (
                  <div
                    style={{
                      backgroundColor: bannerBg,
                      border: `1px solid ${bannerBorder}`,
                      borderRadius: '10px',
                      padding: '16px 20px',
                      marginBottom: '20px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      flexWrap: 'wrap',
                      gap: '12px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      {isCrit ? (
                        <AlertCircle size={28} className="text-rose" />
                      ) : isMod ? (
                        <AlertTriangle size={28} style={{ color: 'var(--accent-amber)' }} />
                      ) : (
                        <CheckCircle2 size={28} className="text-emerald" />
                      )}
                      <div>
                        <div style={{ fontSize: '1.1rem', fontWeight: 800 }}>{statusText}</div>
                        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0, marginTop: '2px' }}>
                          Evaluación de {drift.columns.length} variables numéricas con percentiles (P05 a P95) y test Kolmogorov-Smirnov.
                        </p>
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      <span className="badge badge-emerald">
                        {drift.stable_columns_count} {t.driftAnalytics?.stableCols || 'Estables'}
                      </span>
                      {drift.moderate_columns_count > 0 && (
                        <span className="badge badge-amber">{drift.moderate_columns_count} Moderadas</span>
                      )}
                      {drift.critical_columns_count > 0 && (
                        <span className="badge badge-rose">{drift.critical_columns_count} Críticas</span>
                      )}
                      <span className="badge badge-blue">
                        {drift.total_alerts} {t.driftAnalytics?.totalAlerts || 'Alertas Totales'}
                      </span>
                    </div>
                  </div>
                );
              })()}

              {/* Recomendaciones Proactivas Accionables */}
              {report.drift_analysis.global_recommendations.length > 0 && (
                <div style={{ marginBottom: '24px' }}>
                  <div style={{ marginBottom: '12px' }}>
                    <h4 style={{ fontSize: '1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Lightbulb size={18} className="text-primary" /> {t.driftAnalytics?.proactiveRecsTitle || 'Recomendaciones Proactivas de la IA'}
                    </h4>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                      {t.driftAnalytics?.proactiveRecsSubtitle || 'Acciones de gobernanza y optimización generadas de forma determinista para analítica.'}
                    </p>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '12px' }}>
                    {report.drift_analysis.global_recommendations.map((rec) => {
                      const isHigh = rec.priority === 'high';
                      const isMed = rec.priority === 'medium';
                      const isCopied = copiedRecId === rec.id;
                      return (
                        <div
                          key={rec.id}
                          style={{
                            backgroundColor: 'var(--bg-input)',
                            border: '1px solid var(--border-color)',
                            borderRadius: '10px',
                            padding: '14px',
                            display: 'flex',
                            flexDirection: 'column',
                            justifyContent: 'space-between',
                            gap: '10px',
                          }}
                        >
                          <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                              <span
                                className={`badge ${isHigh ? 'badge-rose' : isMed ? 'badge-amber' : 'badge-emerald'}`}
                                style={{ textTransform: 'uppercase', fontSize: '0.65rem' }}
                              >
                                Prioridad {rec.priority}
                              </span>
                              {rec.column && (
                                <code style={{ fontSize: '0.75rem', color: 'var(--primary)' }}>
                                  {rec.column}
                                </code>
                              )}
                            </div>
                            <h5 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: '4px' }}>{rec.title}</h5>
                            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0, lineHeight: 1.4 }}>
                              {rec.rationale}
                            </p>
                          </div>

                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px' }}>
                            {rec.suggested_step ? (
                              <code style={{ fontSize: '0.7rem', color: 'var(--accent-emerald)', wordBreak: 'break-all' }}>
                                {rec.suggested_step}
                              </code>
                            ) : (
                              <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>Gobernanza de Calidad</span>
                            )}
                            <button
                              className="btn btn-outline"
                              style={{ padding: '4px 8px', fontSize: '0.7rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                              onClick={() => {
                                navigator.clipboard.writeText(`${rec.title}: ${rec.rationale}`);
                                setCopiedRecId(rec.id);
                                setTimeout(() => setCopiedRecId(null), 2000);
                              }}
                            >
                              {isCopied ? <Check size={12} className="text-emerald" /> : <Copy size={12} />}
                              {isCopied ? (t.driftAnalytics?.copiedRecommendation || '¡Copiada!') : (t.driftAnalytics?.copyRecommendation || 'Copiar')}
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Inspector Interactivo de Percentiles y Shift */}
              <div
                style={{
                  backgroundColor: 'var(--bg-input)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '10px',
                  padding: '18px',
                  marginBottom: '24px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
                  <div>
                    <h4 style={{ fontSize: '1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Sliders size={18} className="text-primary" /> {t.driftAnalytics?.percentilesTitle || 'Desplazamiento de Percentiles (P05 a P95)'}
                    </h4>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                      {t.driftAnalytics?.percentilesSubtitle || 'Comparativa de percentiles entre datos originales y datos limpios.'}
                    </p>
                  </div>

                  {/* Selector de Columna */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <label htmlFor="drift-col-select" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      {t.driftAnalytics?.selectColumn || 'Variable:'}
                    </label>
                    <select
                      id="drift-col-select"
                      className="form-select"
                      value={selectedDriftCol}
                      onChange={(e) => setSelectedDriftCol(e.target.value)}
                      style={{ padding: '6px 10px', fontSize: '0.85rem' }}
                    >
                      {report.drift_analysis.columns.map((c) => (
                        <option key={c.column_name} value={c.column_name}>
                          {c.column_name} ({c.drift_status})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {activeDriftColReport && (
                  <div>
                    {/* Tarjetas KPI de la Columna Seleccionada */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '10px', marginBottom: '16px' }}>
                      <div style={{ backgroundColor: 'var(--bg-main)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Drift Score</div>
                        <div style={{ fontSize: '1.3rem', fontWeight: 800, marginTop: '2px' }}>
                          {activeDriftColReport.drift_score}%
                        </div>
                        <span
                          className={`badge ${
                            activeDriftColReport.drift_status === 'critical'
                              ? 'badge-rose'
                              : activeDriftColReport.drift_status === 'moderate'
                              ? 'badge-amber'
                              : 'badge-emerald'
                          }`}
                          style={{ marginTop: '4px', textTransform: 'uppercase', fontSize: '0.65rem' }}
                        >
                          {activeDriftColReport.drift_status}
                        </span>
                      </div>

                      <div style={{ backgroundColor: 'var(--bg-main)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Kolmogorov-Smirnov (KS)</div>
                        <div style={{ fontSize: '1.3rem', fontWeight: 800, marginTop: '2px', color: 'var(--primary)' }}>
                          {activeDriftColReport.ks_statistic !== undefined ? activeDriftColReport.ks_statistic : 'N/A'}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                          Distancia de distribución
                        </div>
                      </div>

                      <div style={{ backgroundColor: 'var(--bg-main)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Δ Mediana (P50)</div>
                        <div
                          style={{
                            fontSize: '1.3rem',
                            fontWeight: 800,
                            marginTop: '2px',
                            color:
                              (activeDriftColReport.shift?.p50_shift_pct ?? 0) === 0
                                ? 'var(--accent-emerald)'
                                : Math.abs(activeDriftColReport.shift?.p50_shift_pct ?? 0) > 15
                                ? 'var(--accent-rose)'
                                : 'var(--accent-amber)',
                          }}
                        >
                          {activeDriftColReport.shift ? `${activeDriftColReport.shift.p50_shift_pct > 0 ? '+' : ''}${activeDriftColReport.shift.p50_shift_pct}%` : '0%'}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                          Desvío tendencia central
                        </div>
                      </div>

                      <div style={{ backgroundColor: 'var(--bg-main)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Anomalías (IQR/P99)</div>
                        <div style={{ fontSize: '1.3rem', fontWeight: 800, marginTop: '2px' }}>
                          {activeDriftColReport.anomaly_count}{' '}
                          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                            ({activeDriftColReport.anomaly_percentage}%)
                          </span>
                        </div>
                        <span
                          className={`badge ${
                            activeDriftColReport.anomaly_percentage >= 10
                              ? 'badge-rose'
                              : activeDriftColReport.anomaly_percentage >= 3
                              ? 'badge-amber'
                              : 'badge-emerald'
                          }`}
                          style={{ marginTop: '4px', fontSize: '0.65rem' }}
                        >
                          {activeDriftColReport.anomaly_percentage >= 3 ? 'Outliers detectados' : 'Normal'}
                        </span>
                      </div>
                    </div>

                    {/* Visualizador Comparativo de los 5 Percentiles */}
                    <div
                      style={{
                        backgroundColor: 'var(--bg-main)',
                        borderRadius: '8px',
                        border: '1px solid var(--border-color)',
                        padding: '16px',
                        marginBottom: '16px',
                      }}
                    >
                      <h5 style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: '14px', color: 'var(--text-main)' }}>
                        Comparador Detallado de Percentiles (Datos Crudos vs. Limpios)
                      </h5>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {[
                          {
                            label: 'P05 (Cola Inferior)',
                            rawVal: activeDriftColReport.raw_percentiles?.p05,
                            cleanVal: activeDriftColReport.clean_percentiles.p05,
                            shiftVal: activeDriftColReport.shift?.p05_shift_pct,
                          },
                          {
                            label: 'P25 (Primer Cuartil Q1)',
                            rawVal: activeDriftColReport.raw_percentiles?.p25,
                            cleanVal: activeDriftColReport.clean_percentiles.p25,
                            shiftVal: activeDriftColReport.shift?.p25_shift_pct,
                          },
                          {
                            label: 'P50 (Mediana Central)',
                            rawVal: activeDriftColReport.raw_percentiles?.p50,
                            cleanVal: activeDriftColReport.clean_percentiles.p50,
                            shiftVal: activeDriftColReport.shift?.p50_shift_pct,
                            isCenter: true,
                          },
                          {
                            label: 'P75 (Tercer Cuartil Q3)',
                            rawVal: activeDriftColReport.raw_percentiles?.p75,
                            cleanVal: activeDriftColReport.clean_percentiles.p75,
                            shiftVal: activeDriftColReport.shift?.p75_shift_pct,
                          },
                          {
                            label: 'P95 (Cola Superior)',
                            rawVal: activeDriftColReport.raw_percentiles?.p95,
                            cleanVal: activeDriftColReport.clean_percentiles.p95,
                            shiftVal: activeDriftColReport.shift?.p95_shift_pct,
                          },
                        ].map((row, idx) => {
                          const shift = row.shiftVal ?? 0;
                          const isHigh = Math.abs(shift) > 20;
                          const isMod = Math.abs(shift) > 5;
                          return (
                            <div
                              key={idx}
                              style={{
                                display: 'grid',
                                gridTemplateColumns: '180px 1fr 1fr 100px',
                                alignItems: 'center',
                                gap: '12px',
                                padding: '8px 12px',
                                borderRadius: '6px',
                                backgroundColor: row.isCenter ? 'rgba(59, 130, 246, 0.08)' : 'var(--bg-input)',
                                border: row.isCenter ? '1px solid rgba(59, 130, 246, 0.3)' : undefined,
                                fontSize: '0.8rem',
                              }}
                            >
                              <div style={{ fontWeight: row.isCenter ? 700 : 500, color: row.isCenter ? 'var(--primary)' : undefined }}>
                                {row.label}
                              </div>
                              <div>
                                <span style={{ color: 'var(--text-muted)' }}>Crudo: </span>
                                <span style={{ fontWeight: 600 }}>{row.rawVal !== undefined ? row.rawVal : 'N/D'}</span>
                              </div>
                              <div>
                                <span style={{ color: 'var(--text-muted)' }}>Limpio: </span>
                                <span className="text-emerald" style={{ fontWeight: 700 }}>{row.cleanVal}</span>
                              </div>
                              <div style={{ textAlign: 'right' }}>
                                <span
                                  className={`badge ${isHigh ? 'badge-rose' : isMod ? 'badge-amber' : 'badge-emerald'}`}
                                  style={{ fontSize: '0.7rem' }}
                                >
                                  {shift > 0 ? `+${shift}` : shift}%
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Tabla de Estabilidad Estadística de Todas las Variables */}
              <div>
                <h4 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '12px' }}>
                  {t.driftAnalytics?.columnsTableTitle || 'Estabilidad Estadística por Variable'}
                </h4>
                <div className="table-wrapper">
                  <table style={{ width: '100%', fontSize: '0.8rem' }}>
                    <thead>
                      <tr>
                        <th>{t.driftAnalytics?.colName || 'Columna'}</th>
                        <th>{t.driftAnalytics?.colStatus || 'Estado Drift'}</th>
                        <th>Drift Score</th>
                        <th>{t.driftAnalytics?.colP50Shift || 'Δ P50'}</th>
                        <th>{t.driftAnalytics?.colMaxShift || 'Δ Máx'}</th>
                        <th>{t.driftAnalytics?.colKs || 'KS Stat'}</th>
                        <th>{t.driftAnalytics?.colAnomalies || 'Anomalías'}</th>
                        <th>Alertas</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.drift_analysis.columns.map((col) => (
                        <tr
                          key={col.column_name}
                          style={{
                            backgroundColor: col.column_name === selectedDriftCol ? 'rgba(59, 130, 246, 0.08)' : undefined,
                            cursor: 'pointer',
                          }}
                          onClick={() => setSelectedDriftCol(col.column_name)}
                        >
                          <td style={{ fontWeight: 600, color: 'var(--primary)' }}>{col.column_name}</td>
                          <td>
                            <span
                              className={`badge ${
                                col.drift_status === 'critical'
                                  ? 'badge-rose'
                                  : col.drift_status === 'moderate'
                                  ? 'badge-amber'
                                  : 'badge-emerald'
                              }`}
                              style={{ textTransform: 'uppercase', fontSize: '0.65rem' }}
                            >
                              {col.drift_status}
                            </span>
                          </td>
                          <td style={{ fontWeight: 600 }}>{col.drift_score}%</td>
                          <td>
                            {col.shift ? `${col.shift.p50_shift_pct > 0 ? '+' : ''}${col.shift.p50_shift_pct}%` : '0%'}
                          </td>
                          <td>
                            {col.shift ? `${col.shift.max_shift_pct}%` : '0%'}
                          </td>
                          <td>{col.ks_statistic !== undefined ? col.ks_statistic : 'N/A'}</td>
                          <td>
                            {col.anomaly_count > 0 ? (
                              <span className={col.anomaly_percentage > 5 ? 'text-rose' : 'text-amber'}>
                                {col.anomaly_count} ({col.anomaly_percentage}%)
                              </span>
                            ) : (
                              <span className="text-emerald">0 (0%)</span>
                            )}
                          </td>
                          <td>
                            {col.alerts.length > 0 ? (
                              <span
                                className={`badge ${
                                  col.alerts.some((a) => a.severity === 'critical') ? 'badge-rose' : 'badge-amber'
                                }`}
                                style={{ fontSize: '0.65rem' }}
                              >
                                {col.alerts.length} alertas
                              </span>
                            ) : (
                              <span style={{ color: 'var(--text-dim)' }}>0</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

