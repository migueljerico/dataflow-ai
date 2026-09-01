import React, { useState, useEffect, useMemo } from 'react';
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

export const BusinessInsights: React.FC<Props> = ({ runId }) => {
  const { t, language } = useLanguage();
  const [report, setReport] = useState<ExecutiveAnalyticsReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'kpis' | 'clusters' | 'outliers' | 'integration'>('kpis');
  const [copiedSnippet, setCopiedSnippet] = useState<string | null>(null);

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
  const [outlierViewMode, setOutlierViewMode] = useState<'boxplot' | 'scatter'>('boxplot');
  const [hoveredOutlierPoint, setHoveredOutlierPoint] = useState<{
    x: number;
    y: number;
    valY: number;
    label: string;
    isOutlier: boolean;
  } | null>(null);

  // Estados de Integración Power BI / Excel adaptativa
  const [selectedPqFormat, setSelectedPqFormat] = useState<'csv' | 'parquet'>('csv');
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
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h5 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Award size={16} /> {t.powerBiExcel?.tabPowerBi || 'Microsoft Power BI'}
                  </h5>
                  <span className="badge badge-amber">DAX + Power Query M</span>
                </div>

                {/* Medidas DAX Adaptadas */}
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px', flexWrap: 'wrap', gap: '6px' }}>
                    <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-main)' }}>
                      {t.powerBiExcel?.daxFormulaLabel || 'Medidas DAX Adaptadas al Dataset'}:
                    </span>
                    <button
                      className="btn btn-outline"
                      style={{ padding: '3px 8px', fontSize: '0.725rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                      onClick={() => {
                        const allDax = daxMeasures.length > 0
                          ? daxMeasures
                              .map((m) => `// ${m.description}\n${m.formula || (m as any).dax_formula}`)
                              .join('\n\n')
                          : `// Medidas DAX calculadas por DataFlow AI\nTotal_Registros = COUNTROWS('DataFlow_Cleaned_Dataset')\n\nRegistros_Validos = \nCALCULATE(\n    COUNTROWS('DataFlow_Cleaned_Dataset'),\n    'DataFlow_Cleaned_Dataset'[is_outlier] = FALSE()\n)\n\nScore_Calidad_Pct = \nDIVIDE([Registros_Validos], [Total_Registros], 1.0) * 100`;
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
                              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--primary)' }}>
                                [{measure.name}]
                              </span>
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

                {/* Consulta M (Power Query) */}
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
                      maxHeight: '180px',
                    }}
                  >
                    {guide
                      ? (selectedPqFormat === 'parquet' ? (guide.power_query_m_parquet || guide.power_query_m_csv) : guide.power_query_m_csv)
                      : `let\n    Source = Csv.Document(File.Contents("DataFlow_Cleaned_Dataset.csv"),[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),\n    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),\n    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{{"run_id", type text}})\nin\n    #"Changed Type"`}
                  </pre>
                </div>
              </div>

              {/* Tarjeta Microsoft Excel */}
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
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h5 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#10b981', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Award size={16} /> {t.powerBiExcel?.tabExcel || 'Microsoft Excel'}
                  </h5>
                  <span className="badge badge-emerald">Fórmulas Dinámicas Adaptativas</span>
                </div>

                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
                  {t.powerBiExcel?.excelDesc || 'Fórmulas nativas adaptadas a las columnas cuantitativas, letras de columna y rangos reales de este dataset.'}
                </p>

                {/* Selector de Columna / Métrica de Excel */}
                {excelFormulas.length > 0 && (
                  <div>
                    <label style={{ fontSize: '0.775rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                      Seleccionar variable para auditar outliers con fórmula Excel:
                    </label>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {excelFormulas.map((item, idx) => {
                        const label = item.column || item.title || (item as any).measure_name || `Columna #${idx + 1}`;
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
                )}

                {/* Fórmula de Excel Dinámica */}
                {(() => {
                  const currentItem = excelFormulas[selectedExcelMeasureIndex] || excelFormulas[0];
                  const formula = currentItem
                    ? (language === 'es' ? currentItem.formula_es : currentItem.formula_en)
                    : (language === 'es'
                        ? `=SI(ESNUMERO(A2); SI(Y(A2>=MEDIANA($A$2:$A$1000)-1,5*DESVEST($A$2:$A$1000); A2<=MEDIANA($A$2:$A$1000)+1,5*DESVEST($A$2:$A$1000)); "Válido"; "Outlier"); "Texto")`
                        : `=IF(ISNUMBER(A2), IF(AND(A2>=MEDIAN($A$2:$A$1000)-1.5*STDEV($A$2:$A$1000), A2<=MEDIAN($A$2:$A$1000)+1.5*STDEV($A$2:$A$1000)), "Valid", "Outlier"), "Text")`);
                  const desc = currentItem?.description || 'Fórmula de validación de outliers por método IQR/Desviación.';
                  const colLetter = currentItem?.excel_column_letter || 'A';
                  const cellTarget = `${colLetter}2`;
                  const colName = currentItem ? (currentItem.column || currentItem.title || (currentItem as any).measure_name) : null;

                  return (
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-main)' }}>
                          {colName ? `Fórmula para ${colName} (pegar en celda ${cellTarget}):` : (t.powerBiExcel?.excelFormulaLabel || 'Fórmula de Validación')}:
                        </span>
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
          </div>
        );
      })()}
    </div>
  );
};

