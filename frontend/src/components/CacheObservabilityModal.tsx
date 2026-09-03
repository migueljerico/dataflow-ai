import React, { useState, useEffect, useRef } from 'react';
import {
  Activity,
  Layers,
  Database,
  Cpu,
  RefreshCw,
  X,
  Zap,
  TrendingUp,
  Coins,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import { api } from '../services/api';
import { CacheStats } from '../types';
import { useLanguage } from '../context/LanguageContext';

interface CacheObservabilityModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CacheObservabilityModal: React.FC<CacheObservabilityModalProps> = ({ isOpen, onClose }) => {
  const { t } = useLanguage();
  const [stats, setStats] = useState<CacheStats | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getCacheStats();
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al consultar estadísticas de caché');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchStats();
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const m = t.cacheModal;
  const total = stats?.total_requests || 0;
  const l1Pct = total > 0 && stats ? ((stats.l1_hits / total) * 100).toFixed(1) : '0.0';
  const l2Pct = total > 0 && stats ? ((stats.l2_hits / total) * 100).toFixed(1) : '0.0';
  const missPct = total > 0 && stats ? ((stats.misses / total) * 100).toFixed(1) : '0.0';

  return (
    <div
      ref={overlayRef}
      className="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="cache-modal-title"
      data-testid="cache-observability-modal"
      onClick={(e) => {
        if (e.target === overlayRef.current) onClose();
      }}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.7)',
        backdropFilter: 'blur(5px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        padding: '16px',
      }}
    >
      <div
        className="card modal-card"
        style={{
          maxWidth: '680px',
          width: '100%',
          maxHeight: '90vh',
          overflowY: 'auto',
          backgroundColor: 'var(--bg-card, #1e293b)',
          borderRadius: '14px',
          boxShadow: 'var(--shadow-lg, 0 20px 25px -5px rgba(0, 0, 0, 0.5))',
          border: '1px solid var(--border-color, #334155)',
          padding: '24px',
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          gap: '18px',
        }}
      >
        {/* Botón de cerrar superior */}
        <button
          onClick={onClose}
          aria-label={m?.close || 'Cerrar'}
          data-testid="cache-modal-close-btn"
          style={{
            position: 'absolute',
            top: '18px',
            right: '18px',
            background: 'none',
            border: 'none',
            color: 'var(--text-muted, #94a3b8)',
            cursor: 'pointer',
            padding: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: '6px',
          }}
        >
          <X size={18} />
        </button>

        {/* Cabecera */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', paddingRight: '32px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                backgroundColor: 'rgba(14, 165, 233, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--primary, #0ea5e9)',
              }}
            >
              <Activity size={20} />
            </div>
            <div>
              <h2
                id="cache-modal-title"
                style={{ fontSize: '1.2rem', fontWeight: 700, margin: 0, color: 'var(--text-main, #f8fafc)' }}
              >
                {m?.title || 'Observabilidad de Caché Distribuida'}
              </h2>
              <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted, #94a3b8)' }}>
                {m?.subtitle || 'Métricas operativas y de ahorro en inferencia IA de dos niveles (L1 Memoria + L2 Redis)'}
              </p>
            </div>
          </div>

          {/* Badge de estado del backend */}
          {stats && (
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: '6px', flexWrap: 'wrap' }}>
              <span
                className={`badge ${stats.distributed ? 'badge-emerald' : 'badge-primary'}`}
                style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '0.75rem' }}
                data-testid="cache-backend-badge"
              >
                {stats.distributed ? <CheckCircle2 size={12} /> : <Cpu size={12} />}
                {stats.distributed
                  ? `${m?.redisStatus || 'Redis L2'}: ${m?.connected || 'Conectado y distribuido'}`
                  : `Motor: ${m?.notConfigured || 'Memoria Local (LRU)'}`}
              </span>

              {stats.redis_errors > 0 && (
                <span
                  className="badge badge-amber"
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '0.75rem' }}
                  title="Errores o timeouts detectados en Redis; degradación elegante a memoria activa"
                >
                  <AlertTriangle size={12} />
                  Redis timeouts: {stats.redis_errors}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Error o Loading */}
        {loading && !stats && (
          <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted, #94a3b8)' }}>
            <RefreshCw size={24} className="spin-animate" style={{ margin: '0 auto 8px' }} />
            <p style={{ fontSize: '0.85rem' }}>Cargando métricas de caché...</p>
          </div>
        )}

        {error && (
          <div
            style={{
              padding: '12px 14px',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: '8px',
              color: '#f87171',
              fontSize: '0.825rem',
            }}
          >
            {error}
          </div>
        )}

        {stats && (
          <>
            {/* Grid de KPIs principales */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                gap: '12px',
              }}
              data-testid="cache-kpi-grid"
            >
              {/* Tasa global */}
              <div
                style={{
                  backgroundColor: 'var(--bg-input, #0f172a)',
                  border: '1px solid var(--border-color, #334155)',
                  borderRadius: '10px',
                  padding: '12px 14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                }}
              >
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted, #94a3b8)', display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <TrendingUp size={13} style={{ color: '#10b981' }} />
                  {m?.globalHitRate || 'Tasa de Acierto Global'}
                </span>
                <strong style={{ fontSize: '1.4rem', color: '#10b981' }} data-testid="kpi-hit-rate">
                  {stats.hit_rate_pct.toFixed(1)}%
                </strong>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted, #94a3b8)' }}>
                  {stats.hits} aciertos / {stats.total_requests} peticiones
                </span>
              </div>

              {/* Aciertos L1 */}
              <div
                style={{
                  backgroundColor: 'var(--bg-input, #0f172a)',
                  border: '1px solid var(--border-color, #334155)',
                  borderRadius: '10px',
                  padding: '12px 14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                }}
              >
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted, #94a3b8)', display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <Zap size={13} style={{ color: '#0ea5e9' }} />
                  {m?.l1Hits || 'Aciertos L1 (Memoria)'}
                </span>
                <strong style={{ fontSize: '1.4rem', color: '#0ea5e9' }} data-testid="kpi-l1-hits">
                  {stats.l1_hits}
                </strong>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted, #94a3b8)' }}>
                  {stats.l1_hit_rate_pct.toFixed(1)}% del total · latencia &lt;1ms
                </span>
              </div>

              {/* Aciertos L2 */}
              <div
                style={{
                  backgroundColor: 'var(--bg-input, #0f172a)',
                  border: '1px solid var(--border-color, #334155)',
                  borderRadius: '10px',
                  padding: '12px 14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                }}
              >
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted, #94a3b8)', display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <Database size={13} style={{ color: '#8b5cf6' }} />
                  {m?.l2Hits || 'Aciertos L2 (Redis)'}
                </span>
                <strong style={{ fontSize: '1.4rem', color: '#8b5cf6' }} data-testid="kpi-l2-hits">
                  {stats.l2_hits}
                </strong>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted, #94a3b8)' }}>
                  {stats.l2_hit_rate_pct.toFixed(1)}% del total · multi-instancia
                </span>
              </div>

              {/* Fallos / Misses */}
              <div
                style={{
                  backgroundColor: 'var(--bg-input, #0f172a)',
                  border: '1px solid var(--border-color, #334155)',
                  borderRadius: '10px',
                  padding: '12px 14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                }}
              >
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted, #94a3b8)', display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <Cpu size={13} style={{ color: '#94a3b8' }} />
                  {m?.misses || 'Fallos (Llamada LLM)'}
                </span>
                <strong style={{ fontSize: '1.4rem', color: 'var(--text-main, #f8fafc)' }} data-testid="kpi-misses">
                  {stats.misses}
                </strong>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted, #94a3b8)' }}>
                  Inferencia generativa ejecutada
                </span>
              </div>

              {/* Tokens Ahorrados */}
              <div
                style={{
                  backgroundColor: 'var(--bg-input, #0f172a)',
                  border: '1px solid var(--border-color, #334155)',
                  borderRadius: '10px',
                  padding: '12px 14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                }}
              >
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted, #94a3b8)', display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <ShieldCheck size={13} style={{ color: '#10b981' }} />
                  {m?.savedTokens || 'Tokens Ahorrados'}
                </span>
                <strong style={{ fontSize: '1.4rem', color: '#10b981' }} data-testid="kpi-saved-tokens">
                  {stats.saved_tokens.toLocaleString()}
                </strong>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted, #94a3b8)' }}>
                  Cuota de API preservada
                </span>
              </div>

              {/* Coste Ahorrado */}
              <div
                style={{
                  backgroundColor: 'var(--bg-input, #0f172a)',
                  border: '1px solid var(--border-color, #334155)',
                  borderRadius: '10px',
                  padding: '12px 14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                }}
              >
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted, #94a3b8)', display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <Coins size={13} style={{ color: '#f59e0b' }} />
                  {m?.savedCost || 'Coste Ahorrado (USD)'}
                </span>
                <strong style={{ fontSize: '1.4rem', color: '#f59e0b' }} data-testid="kpi-saved-cost">
                  ${stats.saved_cost_usd.toFixed(6)}
                </strong>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted, #94a3b8)' }}>
                  Ahorro 100% en llamadas cacheadas
                </span>
              </div>
            </div>

            {/* Barra de distribución apilada */}
            <div
              style={{
                backgroundColor: 'var(--bg-input, #0f172a)',
                border: '1px solid var(--border-color, #334155)',
                borderRadius: '10px',
                padding: '14px',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem' }}>
                <span style={{ fontWeight: 600, color: 'var(--text-main, #f8fafc)' }}>
                  Distribución de Tráfico de Inferencia
                </span>
                <span style={{ color: 'var(--text-muted, #94a3b8)', fontSize: '0.75rem' }}>
                  {stats.cached_entries} entradas en LRU local (máx. 500)
                </span>
              </div>

              <div
                style={{
                  height: '14px',
                  width: '100%',
                  backgroundColor: 'rgba(148, 163, 184, 0.15)',
                  borderRadius: '7px',
                  overflow: 'hidden',
                  display: 'flex',
                }}
                data-testid="cache-stacked-bar"
              >
                {total > 0 ? (
                  <>
                    <div
                      style={{
                        width: `${l1Pct}%`,
                        backgroundColor: '#0ea5e9',
                        transition: 'width 0.3s ease',
                      }}
                      title={`L1 Hits: ${stats.l1_hits} (${l1Pct}%)`}
                    />
                    <div
                      style={{
                        width: `${l2Pct}%`,
                        backgroundColor: '#8b5cf6',
                        transition: 'width 0.3s ease',
                      }}
                      title={`L2 Hits: ${stats.l2_hits} (${l2Pct}%)`}
                    />
                    <div
                      style={{
                        width: `${missPct}%`,
                        backgroundColor: '#64748b',
                        transition: 'width 0.3s ease',
                      }}
                      title={`Misses: ${stats.misses} (${missPct}%)`}
                    />
                  </>
                ) : (
                  <div style={{ width: '100%', backgroundColor: 'rgba(148, 163, 184, 0.2)' }} />
                )}
              </div>

              <div
                style={{
                  display: 'flex',
                  gap: '16px',
                  flexWrap: 'wrap',
                  fontSize: '0.75rem',
                  color: 'var(--text-muted, #94a3b8)',
                }}
              >
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                  <span style={{ width: 10, height: 10, borderRadius: 2, backgroundColor: '#0ea5e9', display: 'inline-block' }} />
                  L1 Memoria ({l1Pct}%)
                </span>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                  <span style={{ width: 10, height: 10, borderRadius: 2, backgroundColor: '#8b5cf6', display: 'inline-block' }} />
                  L2 Redis ({l2Pct}%)
                </span>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                  <span style={{ width: 10, height: 10, borderRadius: 2, backgroundColor: '#64748b', display: 'inline-block' }} />
                  Misses / LLM ({missPct}%)
                </span>
              </div>
            </div>

            {/* Explicación de la arquitectura de dos niveles */}
            <div
              style={{
                backgroundColor: 'rgba(14, 165, 233, 0.06)',
                border: '1px solid rgba(14, 165, 233, 0.2)',
                borderRadius: '10px',
                padding: '12px 14px',
                fontSize: '0.785rem',
                color: 'var(--text-muted, #94a3b8)',
                lineHeight: 1.5,
              }}
            >
              <strong style={{ color: 'var(--primary, #0ea5e9)', display: 'block', marginBottom: '4px' }}>
                {m?.twoTierTitle || 'Arquitectura de Dos Niveles L1 + L2'}
              </strong>
              {m?.twoTierDesc ||
                'L1 en memoria local ofrece latencia ultrarrápida (<1ms) aislada por réplica. L2 en Redis comparte aciertos entre todas las instancias de Cloud Run con huella canónica determinista (SHA-256).'}
            </div>
          </>
        )}

        {/* Acciones inferiores */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px', flexWrap: 'wrap', gap: '10px' }}>
          <button
            type="button"
            className="btn btn-outline"
            onClick={fetchStats}
            disabled={loading}
            data-testid="cache-refresh-btn"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '0.8rem',
              padding: '6px 14px',
            }}
          >
            <RefreshCw size={14} className={loading ? 'spin-animate' : ''} />
            {m?.refresh || 'Actualizar Métricas'}
          </button>

          <button
            type="button"
            className="btn btn-primary"
            onClick={onClose}
            style={{ fontSize: '0.8rem', padding: '6px 18px' }}
          >
            {m?.close || 'Cerrar'}
          </button>
        </div>
      </div>
    </div>
  );
};
