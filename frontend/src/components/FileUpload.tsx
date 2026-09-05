import React, { useState, useEffect, useRef, useMemo } from 'react';
import { 
  Upload, 
  FileSpreadsheet, 
  AlertCircle, 
  Sparkles, 
  PhoneCall, 
  ShoppingCart, 
  Users, 
  Truck,
  Play,
  Globe,
  Link2,
  Download,
  Loader2,
  ArrowRight,
  ShieldCheck,
  Database,
  Search,
  Building2,
  RefreshCw
} from 'lucide-react';
import { api } from '../services/api';
import { DatasetMetadata, SampleDataset, OpenDatasetItem } from '../types';
import { useLanguage } from '../context/LanguageContext';
import { FileDropzone } from './upload/FileDropzone';
import { UrlImporter } from './upload/UrlImporter';
import { OpenDataExplorer } from './upload/OpenDataExplorer';

interface Props {
  onUploadSuccess: (metadata: DatasetMetadata) => void;
  onBatchUploadSuccess?: (datasets: DatasetMetadata[]) => void;
}

type TabType = 'file' | 'url' | 'opendata';

const EXAMPLE_URLS = [
  {
    name: 'PIB Mundial (GDP)',
    desc: 'Series temporales macroeconómicas',
    url: 'https://raw.githubusercontent.com/datasets/gdp/master/data/gdp.csv'
  },
  {
    name: 'Carsharing & Movilidad',
    desc: 'Operaciones urbanas y tarifas',
    url: 'https://raw.githubusercontent.com/plotly/datasets/master/carshare_data.csv'
  },
  {
    name: 'Dataset Iris',
    desc: 'Métricas biológicas estándar',
    url: 'https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv'
  }
];

export const FileUpload: React.FC<Props> = ({ onUploadSuccess, onBatchUploadSuccess }) => {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<TabType>('file');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const statusTimer1Ref = useRef<number | null>(null);
  const statusTimer2Ref = useRef<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [urlInput, setUrlInput] = useState<string>('');
  const [samples, setSamples] = useState<SampleDataset[]>([]);


  // Estado de Open Data (Fase 3)
  const [openDataSearchQuery, setOpenDataSearchQuery] = useState<string>('');
  const [openDataResults, setOpenDataResults] = useState<OpenDatasetItem[]>([]);
  const [openDataLoading, setOpenDataLoading] = useState<boolean>(false);
  const [selectedTag, setSelectedTag] = useState<string>('Todos');

  useEffect(() => {
    let cancelled = false;
    const fetchInitialData = async () => {
      try {
        const [sampleList, featuredOpenData] = await Promise.all([
          api.listSampleDatasets().catch(() => [] as SampleDataset[]),
          api.getFeaturedOpenDatasets().catch(() => [] as OpenDatasetItem[])
        ]);
        if (!cancelled) {
          setSamples(sampleList);
          setOpenDataResults(featuredOpenData);
        }
      } catch {
        // Fallback silencioso
      }
    };
    fetchInitialData();
    return () => { cancelled = true; };
  }, []);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 1) {
      await uploadMultipleFiles(Array.from(e.target.files));
    } else if (e.target.files && e.target.files[0]) {
      await uploadFile(e.target.files[0]);
    }
  };

  const uploadMultipleFiles = async (files: File[]) => {
    setLoading(true);
    setLoadingStatus(`Subiendo y analizando lote de ${files.length} archivos simultáneamente...`);
    setError(null);
    try {
      const datasets = await api.uploadDatasetsBatch(files);
      if (onBatchUploadSuccess) {
        onBatchUploadSuccess(datasets);
      } else if (datasets.length > 0) {
        onUploadSuccess(datasets[0]);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al subir el lote de archivos.');
    } finally {
      setLoading(false);
      setLoadingStatus('');
    }
  };

  const uploadFile = async (file: File) => {
    if (file.size > 10 * 1024 * 1024) {
      setError('El archivo supera el límite de 10 MB.');
      return;
    }
    setLoading(true);
    setLoadingStatus('Validando archivo y analizando estructura...');
    setError(null);
    try {
      const metadata = await api.uploadDataset(file);
      onUploadSuccess(metadata);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al subir el archivo.');
    } finally {
      setLoading(false);
      setLoadingStatus('');
    }
  };

  const importFromUrl = async (targetUrl: string) => {
    const cleanUrl = targetUrl.trim();
    if (!cleanUrl) {
      setError('Por favor, ingresa una URL válida que empiece por http:// o https://.');
      return;
    }

    if (!cleanUrl.startsWith('http://') && !cleanUrl.startsWith('https://')) {
      setError('La URL debe comenzar por http:// o https://.');
      return;
    }

    setLoading(true);
    setError(null);
    setLoadingStatus('Conectando de forma segura con el servidor remoto (Anti-SSRF)...');

    statusTimer1Ref.current = window.setTimeout(() => {
      setLoadingStatus('Descargando dataset en streaming (máx. 20 MB)...');
    }, 1200);

    statusTimer2Ref.current = window.setTimeout(() => {
      setLoadingStatus('Analizando calidad, tipos de datos y perfil semántico...');
    }, 2800);

    try {
      const metadata = await api.loadDatasetFromUrl(cleanUrl);
      if (statusTimer1Ref.current) window.clearTimeout(statusTimer1Ref.current);
      if (statusTimer2Ref.current) window.clearTimeout(statusTimer2Ref.current);
      onUploadSuccess(metadata);
    } catch (err: unknown) {
      if (statusTimer1Ref.current) window.clearTimeout(statusTimer1Ref.current);
      if (statusTimer2Ref.current) window.clearTimeout(statusTimer2Ref.current);
      setError(err instanceof Error ? err.message : 'No se pudo descargar el dataset desde la URL proporcionada.');
    } finally {
      setLoading(false);
      setLoadingStatus('');
    }
  };

  const handleUrlSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    importFromUrl(urlInput);
  };

  const handleOpenDataSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setOpenDataLoading(true);
    setError(null);
    try {
      const resp = await api.searchOpenDatasets(openDataSearchQuery, 12);
      setOpenDataResults(resp.results || []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al buscar en el catálogo Open Data.');
    } finally {
      setOpenDataLoading(false);
    }
  };

  const loadSample = async (sampleId: string) => {
    setLoading(true);
    setLoadingStatus('Cargando dataset demo de negocio...');
    setError(null);
    try {
      const metadata = await api.loadSampleDataset(sampleId);
      onUploadSuccess(metadata);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al cargar el dataset de demostración.');
    } finally {
      setLoading(false);
      setLoadingStatus('');
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 1) {
      await uploadMultipleFiles(Array.from(e.dataTransfer.files));
    } else if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await uploadFile(e.dataTransfer.files[0]);
    }
  };

  const getSampleIcon = (id: string) => {
    if (id === 'contact_center') return <PhoneCall size={20} className="text-primary" />;
    if (id === 'sales') return <ShoppingCart size={20} className="text-primary" />;
    if (id === 'logistics') return <Truck size={20} className="text-primary" />;
    return <Users size={20} className="text-primary" />;
  };

  const allTags = ['Todos', 'Economía', 'Movilidad', 'Población', 'Ventas', 'Medioambiente'] as const;
  const filteredOpenData = useMemo(() => selectedTag === 'Todos' 
    ? openDataResults 
    : openDataResults.filter(item => item.tags.some(t => t.toLowerCase().includes(selectedTag.toLowerCase()))), [openDataResults, selectedTag]);

  return (
    <div>
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-header" style={{ flexWrap: 'wrap', gap: '12px' }}>
          <h2 className="card-title">
            <Upload size={20} className="text-primary" /> {t.upload.title}
          </h2>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span className="badge badge-blue">
              {activeTab === 'file' ? 'Máx. 10 MB | CSV / XLSX' : 'Máx. 20 MB | HTTP / HTTPS'}
            </span>
          </div>
        </div>

        {/* Selector de Pestañas (Modos de Ingesta) */}
        <div 
          style={{ 
            display: 'flex', 
            gap: '8px', 
            padding: '4px', 
            backgroundColor: 'var(--bg-input)', 
            borderRadius: '10px', 
            marginBottom: '20px',
            border: '1px solid var(--border-color)',
            flexWrap: 'wrap'
          }}
        >
          <button
            type="button"
            className={`btn ${activeTab === 'file' ? 'btn-primary' : 'btn-outline'}`}
            style={{ 
              flex: '1 1 180px', 
              justifyContent: 'center', 
              border: 'none', 
              boxShadow: activeTab === 'file' ? 'var(--shadow-sm)' : 'none' 
            }}
            onClick={() => { setActiveTab('file'); setError(null); }}
            disabled={loading}
          >
            <Upload size={16} /> {t.stepper.step1}
          </button>
          <button
            type="button"
            className={`btn ${activeTab === 'url' ? 'btn-primary' : 'btn-outline'}`}
            style={{ 
              flex: '1 1 180px', 
              justifyContent: 'center', 
              border: 'none', 
              boxShadow: activeTab === 'url' ? 'var(--shadow-sm)' : 'none' 
            }}
            onClick={() => { setActiveTab('url'); setError(null); }}
            disabled={loading}
          >
            <Globe size={16} /> {t.upload.orRemote}
          </button>
          <button
            type="button"
            className={`btn ${activeTab === 'opendata' ? 'btn-primary' : 'btn-outline'}`}
            style={{ 
              flex: '1 1 180px', 
              justifyContent: 'center', 
              border: 'none', 
              boxShadow: activeTab === 'opendata' ? 'var(--shadow-sm)' : 'none' 
            }}
            onClick={() => { setActiveTab('opendata'); setError(null); }}
            disabled={loading}
          >
            <Database size={16} /> {t.upload.openDataBtn}
          </button>
        </div>

        {/* Pestaña 1: Carga por Archivo Local */}
        {activeTab === 'file' && (
          <div
            className="dropzone"
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            onClick={() => !loading && fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInputRef.current?.click(); } }}
            aria-label={t.upload.dropzoneMain}
            style={{ cursor: loading ? 'not-allowed' : 'pointer' }}
          >
            <input
              ref={fileInputRef}
              id="fileInput"
              type="file"
              accept=".csv,.xlsx"
              multiple
              style={{ display: 'none' }}
              onChange={handleFileChange}
              disabled={loading}
            />
            <div style={{ marginBottom: '16px' }}>
              <FileSpreadsheet size={48} className="text-primary" style={{ margin: '0 auto' }} />
            </div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '8px' }}>
              {t.upload.dropzoneMain}
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
              {t.upload.formatNotice}
            </p>
          </div>
        )}


        {/* Pestaña 2: Carga por Enlace Web (URL) */}
        {activeTab === 'url' && (
          <div style={{ padding: '8px 0' }}>
            <form onSubmit={handleUrlSubmit}>
              <div style={{ marginBottom: '16px' }}>
                <label 
                  htmlFor="urlInputField" 
                  style={{ 
                    display: 'block', 
                    fontSize: '0.875rem', 
                    fontWeight: 600, 
                    color: 'var(--text-main)', 
                    marginBottom: '8px' 
                  }}
                >
                  Enlace directo a archivo CSV o Excel remoto:
                </label>
                <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                  <div style={{ position: 'relative', flex: 1, minWidth: '260px' }}>
                    <div 
                      style={{ 
                        position: 'absolute', 
                        left: '12px', 
                        top: '50%', 
                        transform: 'translateY(-50%)', 
                        color: 'var(--text-muted)',
                        pointerEvents: 'none'
                      }}
                    >
                      <Link2 size={18} />
                    </div>
                    <input
                      id="urlInputField"
                      type="url"
                      placeholder="https://raw.githubusercontent.com/.../dataset.csv"
                      value={urlInput}
                      onChange={(e) => setUrlInput(e.target.value)}
                      disabled={loading}
                      style={{
                        width: '100%',
                        padding: '10px 14px 10px 38px',
                        backgroundColor: 'var(--bg-input)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '8px',
                        color: 'var(--text-main)',
                        fontSize: '0.9rem',
                        outline: 'none',
                        transition: 'border-color 0.2s'
                      }}
                    />
                  </div>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={loading || !urlInput.trim()}
                    style={{ whiteSpace: 'nowrap', padding: '10px 20px', minWidth: '160px', justifyContent: 'center' }}
                  >
                    {loading ? (
                      <>
                        <Loader2 size={16} className="spin" /> Descargando...
                      </>
                    ) : (
                      <>
                        <Download size={16} /> Importar Dataset
                      </>
                    )}
                  </button>
                </div>
              </div>
            </form>

            {/* Aviso de seguridad Anti-SSRF */}
            <div 
              style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '8px', 
                fontSize: '0.78rem', 
                color: 'var(--text-muted)',
                backgroundColor: 'rgba(14, 165, 233, 0.05)',
                padding: '8px 12px',
                borderRadius: '6px',
                marginBottom: '16px',
                border: '1px solid rgba(14, 165, 233, 0.15)'
              }}
            >
              <ShieldCheck size={16} className="text-primary" />
              <span>
                Conexión segura protegida contra SSRF con resolución DNS verificada y límite de 20 MB.
              </span>
            </div>

            {/* Ejemplos de URLs de Prueba Rápidas */}
            <div>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: '8px' }}>
                🔗 O prueba con un enlace público directo:
              </span>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {EXAMPLE_URLS.map((ex, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="btn btn-outline"
                    style={{ 
                      fontSize: '0.78rem', 
                      padding: '6px 12px', 
                      borderRadius: '20px',
                      backgroundColor: 'var(--bg-input)'
                    }}
                    onClick={() => {
                      setUrlInput(ex.url);
                      setError(null);
                    }}
                    disabled={loading}
                  >
                    <span style={{ fontWeight: 600 }}>{ex.name}</span>
                    <span style={{ color: 'var(--text-dim)', marginLeft: '4px' }}>({ex.desc})</span>
                    <ArrowRight size={12} style={{ marginLeft: '4px' }} />
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Pestaña 3: Explorador Open Data (Fase 3) */}
        {activeTab === 'opendata' && (
          <div style={{ padding: '8px 0' }}>
            {/* Buscador CKAN */}
            <form onSubmit={handleOpenDataSearch} style={{ marginBottom: '16px' }}>
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <div style={{ position: 'relative', flex: 1, minWidth: '260px' }}>
                  <div 
                    style={{ 
                      position: 'absolute', 
                      left: '12px', 
                      top: '50%', 
                      transform: 'translateY(-50%)', 
                      color: 'var(--text-muted)',
                      pointerEvents: 'none'
                    }}
                  >
                    <Search size={18} />
                  </div>
                  <input
                    type="text"
                    placeholder="Buscar por temática: precios, transporte, energía, demografía..."
                    value={openDataSearchQuery}
                    onChange={(e) => setOpenDataSearchQuery(e.target.value)}
                    disabled={loading || openDataLoading}
                    style={{
                      width: '100%',
                      padding: '10px 14px 10px 38px',
                      backgroundColor: 'var(--bg-input)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px',
                      color: 'var(--text-main)',
                      fontSize: '0.9rem',
                      outline: 'none'
                    }}
                  />
                </div>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={loading || openDataLoading}
                  style={{ padding: '10px 20px', minWidth: '130px', justifyContent: 'center' }}
                >
                  {openDataLoading ? (
                    <>
                      <Loader2 size={16} className="spin" /> Buscando...
                    </>
                  ) : (
                    <>
                      <Search size={16} /> Buscar
                    </>
                  )}
                </button>
                {openDataSearchQuery && (
                  <button
                    type="button"
                    className="btn btn-outline"
                    onClick={() => {
                      setOpenDataSearchQuery('');
                      api.getFeaturedOpenDatasets().then(setOpenDataResults);
                    }}
                    disabled={loading || openDataLoading}
                    title="Restablecer destacados"
                  >
                    <RefreshCw size={16} />
                  </button>
                )}
              </div>
            </form>

            {/* Filtro de Etiquetas Rápidas */}
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '16px' }}>
              {allTags.map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => setSelectedTag(tag)}
                  style={{
                    fontSize: '0.78rem',
                    padding: '4px 10px',
                    borderRadius: '16px',
                    border: '1px solid',
                    borderColor: selectedTag === tag ? 'var(--primary)' : 'var(--border-color)',
                    backgroundColor: selectedTag === tag ? 'var(--primary-light)' : 'var(--bg-input)',
                    color: selectedTag === tag ? 'var(--primary)' : 'var(--text-muted)',
                    cursor: 'pointer',
                    fontWeight: selectedTag === tag ? 700 : 500
                  }}
                >
                  {tag}
                </button>
              ))}
            </div>

            {/* Grid de Tarjetas de Datasets Open Data */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px' }}>
              {filteredOpenData.length > 0 ? (
                filteredOpenData.map((item) => (
                  <div
                    key={item.id}
                    style={{
                      backgroundColor: 'var(--bg-input)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '10px',
                      padding: '16px',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      gap: '12px',
                      transition: 'border-color 0.2s',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--primary)' }}>
                          <Building2 size={14} />
                          <span style={{ fontWeight: 600 }}>{item.organization}</span>
                        </div>
                        <span className="badge badge-emerald" style={{ fontSize: '0.7rem' }}>
                          {item.format}
                        </span>
                      </div>
                      <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '6px' }}>
                        {item.title}
                      </h4>
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: '1.4', marginBottom: '8px' }}>
                        {item.description}
                      </p>
                      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                        {item.tags.map((t, i) => (
                          <span key={i} style={{ fontSize: '0.7rem', color: 'var(--text-dim)', backgroundColor: 'rgba(255,255,255,0.04)', padding: '2px 6px', borderRadius: '4px' }}>
                            #{t}
                          </span>
                        ))}
                      </div>
                    </div>
                    <button
                      className="btn btn-outline"
                      style={{ width: '100%', justifyContent: 'center', fontSize: '0.8rem', padding: '8px 12px' }}
                      onClick={() => importFromUrl(item.resource_url)}
                      disabled={loading}
                    >
                      <Download size={14} /> Importar a DataFlow
                    </button>
                  </div>
                ))
              ) : (
                <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', gridColumn: '1 / -1' }}>
                  No se encontraron datasets para la búsqueda realizada. Prueba con otro término o selecciona "Todos".
                </div>
              )}
            </div>
          </div>
        )}

        {/* Indicador de Carga y Progreso */}
        {loading && (
          <div 
            style={{ 
              marginTop: '18px', 
              padding: '14px', 
              borderRadius: '8px', 
              backgroundColor: 'rgba(14, 165, 233, 0.1)', 
              color: 'var(--primary)', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center', 
              gap: '10px',
              fontWeight: 600,
              fontSize: '0.9rem'
            }}
          >
            <Loader2 size={18} className="spin" />
            <span>{loadingStatus || 'Procesando dataset...'}</span>
          </div>
        )}

        {/* Mensaje de Error */}
        {error && (
          <div 
            role="alert"
            aria-live="assertive"
            style={{ 
              marginTop: '16px', 
              padding: '12px 16px', 
              borderRadius: '8px', 
              backgroundColor: 'rgba(244, 63, 94, 0.1)', 
              color: 'var(--accent-rose)', 
              display: 'flex', 
              alignItems: 'center', 
              gap: '10px',
              border: '1px solid rgba(244, 63, 94, 0.2)',
              fontSize: '0.875rem'
            }}
          >
            <AlertCircle size={18} aria-hidden="true" style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Selector de Datasets de Demostración con 1 Clic */}
      <div className="card">
        <div className="card-header">
          <h3 style={{ fontSize: '1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={18} className="text-primary" /> {t.upload.sampleDataTitle}
          </h3>
          <span className="badge badge-emerald">Ready</span>
        </div>

        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '14px' }}>
          {t.upload.sampleDataDesc}
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px' }}>
          {samples.length > 0 ? (
            samples.map((s) => (
              <div
                key={s.id}
                style={{
                  backgroundColor: 'var(--bg-input)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '10px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  gap: '12px',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  transition: 'border-color 0.2s',
                }}
                onClick={() => !loading && loadSample(s.id)}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                    {getSampleIcon(s.id)}
                    <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>{s.title}</span>
                  </div>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                    {s.description}
                  </p>
                </div>
                <button
                  className="btn btn-outline"
                  style={{ width: '100%', justifyContent: 'center', fontSize: '0.8rem', padding: '6px 12px' }}
                  disabled={loading}
                >
                  <Play size={14} /> {s.title}
                </button>
              </div>
            ))
          ) : (
            <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Loading samples...</div>
          )}
        </div>
      </div>
    </div>
  );
};

