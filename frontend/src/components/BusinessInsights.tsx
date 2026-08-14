import React, { useState, useEffect } from 'react';
import { TrendingUp, BarChart3, Lightbulb, Sparkles, CheckCircle2, Award, PieChart } from 'lucide-react';
import { api } from '../services/api';
import { ExecutiveAnalyticsReport } from '../types';

interface Props {
  runId: string;
}

export const BusinessInsights: React.FC<Props> = ({ runId }) => {
  const [report, setReport] = useState<ExecutiveAnalyticsReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      setLoading(true);
      try {
        const data = await api.getBusinessAnalytics(runId);
        setReport(data);
      } catch (err: any) {
        setError(err.message || 'No se pudieron calcular los Business Analytics.');
      } finally {
        setLoading(false);
      }
    };
    fetchAnalytics();
  }, [runId]);

  if (loading) {
    return (
      <div style={{ padding: '24px', textAlign: 'center', color: 'var(--primary)' }}>
        ⚡ Calculando KPIs operativos con pandas y generando resumen ejecutivo de negocio...
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

  return (
    <div style={{ marginTop: '32px', borderTop: '1px solid var(--border-color)', paddingTop: '28px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <TrendingUp size={22} className="text-primary" /> Business Analytics & KPIs Ejecutivos
          </h3>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            Métricas de valor calculadas con pandas sobre el dataset depurado para soporte en la toma de decisiones.
          </p>
        </div>
        <span className="badge badge-emerald">
          <Sparkles size={12} /> Insights Listos para Power BI
        </span>
      </div>

      {/* Tarjetas de Business KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', marginBottom: '24px' }}>
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
            <div style={{ fontSize: '0.75rem', color: 'var(--text-main)', opacity: 0.8 }}>
              {kpi.subtitle}
            </div>
          </div>
        ))}
      </div>

      {/* Resumen Ejecutivo de Negocio */}
      <div
        style={{
          backgroundColor: 'rgba(59, 130, 246, 0.05)',
          border: '1px solid rgba(59, 130, 246, 0.2)',
          borderRadius: '10px',
          padding: '20px',
          marginBottom: '24px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
          <Award size={18} className="text-primary" />
          <h4 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Resumen Ejecutivo para Dirección</h4>
        </div>
        <p style={{ fontSize: '0.875rem', lineHeight: '1.6', color: 'var(--text-main)' }}>
          {report.executive_summary}
        </p>
      </div>

      {/* Distribución por Categorías y Recomendaciones */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
        {/* Distribución */}
        {report.category_breakdown && report.category_breakdown.length > 0 && (
          <div style={{ backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-color)', borderRadius: '10px', padding: '16px' }}>
            <h4 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <PieChart size={16} className="text-primary" /> Segmentación / Distribución Principal
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {report.category_breakdown.map((cat, idx) => (
                <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.825rem' }}>
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

        {/* Recomendaciones */}
        {report.strategic_recommendations && report.strategic_recommendations.length > 0 && (
          <div style={{ backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-color)', borderRadius: '10px', padding: '16px' }}>
            <h4 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Lightbulb size={16} className="text-primary" /> Recomendaciones de Negocio
            </h4>
            <ul style={{ paddingLeft: '18px', margin: 0, fontSize: '0.825rem', lineHeight: '1.5', color: 'var(--text-muted)' }}>
              {report.strategic_recommendations.map((rec, idx) => (
                <li key={idx} style={{ marginBottom: '6px' }}>{rec}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};
