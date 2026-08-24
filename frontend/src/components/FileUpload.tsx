import React, { useState, useEffect } from 'react';
import { 
  Upload, 
  FileSpreadsheet, 
  AlertCircle, 
  Sparkles, 
  PhoneCall, 
  ShoppingCart, 
  Users, 
  Play,
  Globe,
  Link2,
  Download,
  Loader2,
  ArrowRight,
  ShieldCheck
} from 'lucide-react';
import { api } from '../services/api';
import { DatasetMetadata, SampleDataset } from '../types';

interface Props {
  onUploadSuccess: (metadata: DatasetMetadata) => void;
}

type TabType = 'file' | 'url';

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

export const FileUpload: React.FC<Props> = ({ onUploadSuccess }) => {
  const [activeTab, setActiveTab] = useState<TabType>('file');
  const [loading, setLoading] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [urlInput, setUrlInput] = useState<string>('');
  const [samples, setSamples] = useState<SampleDataset[]>([]);

  useEffect(() => {
    const fetchSamples = async () => {
      try {
        const list = await api.listSampleDatasets();
        setSamples(list);
      } catch {
        // Fallback silencioso si la API aún no responde
      }
    };
    fetchSamples();
  }, []);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      await uploadFile(e.target.files[0]);
    }
  };

  const uploadFile = async (file: File) => {
    setLoading(true);
    setLoadingStatus('Validando archivo y analizando estructura...');
    setError(null);
    try {
      const metadata = await api.uploadDataset(file);
      onUploadSuccess(metadata);
    } catch (err: any) {
      setError(err.message || 'Error al subir el archivo.');
    } finally {
      setLoading(false);
      setLoadingStatus('');
    }
  };

  const handleUrlSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const cleanUrl = urlInput.trim();
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

    const statusTimer1 = setTimeout(() => {
      setLoadingStatus('Descargando dataset en streaming (máx. 20 MB)...');
    }, 1200);

    const statusTimer2 = setTimeout(() => {
      setLoadingStatus('Analizando calidad, tipos de datos y perfil semántico...');
    }, 2800);

    try {
      const metadata = await api.loadDatasetFromUrl(cleanUrl);
      clearTimeout(statusTimer1);
      clearTimeout(statusTimer2);
      onUploadSuccess(metadata);
    } catch (err: any) {
      clearTimeout(statusTimer1);
      clearTimeout(statusTimer2);
      setError(err.message || 'No se pudo descargar el dataset desde la URL proporcionada.');
    } finally {
      setLoading(false);
      setLoadingStatus('');
    }
  };

  const loadSample = async (sampleId: string) => {
    setLoading(true);
    setLoadingStatus('Cargando dataset demo de negocio...');
    setError(null);
    try {
      const metadata = await api.loadSampleDataset(sampleId);
      onUploadSuccess(metadata);
    } catch (err: any) {
      setError(err.message || 'Error al cargar el dataset de demostración.');
    } finally {
      setLoading(false);
      setLoadingStatus('');
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await uploadFile(e.dataTransfer.files[0]);
    }
  };

  const getSampleIcon = (id: string) => {
    if (id === 'contact_center') return <PhoneCall size={20} className="text-primary" />;
    if (id === 'sales') return <ShoppingCart size={20} className="text-primary" />;
    return <Users size={20} className="text-primary" />;
  };

  return (
    <div>
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-header" style={{ flexWrap: 'wrap', gap: '12px' }}>
          <h2 className="card-title">
            <Upload size={20} className="text-primary" /> Ingesta de Dataset Empresarial
          </h2>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span className="badge badge-blue">
              {activeTab === 'file' ? 'Máx. 10 MB | CSV / XLSX' : 'Máx. 20 MB | HTTP / HTTPS'}
            </span>
          </div>
        </div>

        {/* Selector de Pestañas (Modo de Ingesta) */}
        <div 
          style={{ 
            display: 'flex', 
            gap: '8px', 
            padding: '4px', 
            backgroundColor: 'var(--bg-input)', 
            borderRadius: '10px', 
            marginBottom: '20px',
            border: '1px solid var(--border-color)'
          }}
        >
          <button
            type="button"
            className={`btn ${activeTab === 'file' ? 'btn-primary' : 'btn-outline'}`}
            style={{ 
              flex: 1, 
              justifyContent: 'center', 
              border: 'none', 
              boxShadow: activeTab === 'file' ? 'var(--shadow-sm)' : 'none' 
            }}
            onClick={() => { setActiveTab('file'); setError(null); }}
            disabled={loading}
          >
            <Upload size={16} /> Subir Archivo Local
          </button>
          <button
            type="button"
            className={`btn ${activeTab === 'url' ? 'btn-primary' : 'btn-outline'}`}
            style={{ 
              flex: 1, 
              justifyContent: 'center', 
              border: 'none', 
              boxShadow: activeTab === 'url' ? 'var(--shadow-sm)' : 'none' 
            }}
            onClick={() => { setActiveTab('url'); setError(null); }}
            disabled={loading}
          >
            <Globe size={16} /> Pegar Enlace Web (URL)
          </button>
        </div>

        {/* Pestaña 1: Carga por Archivo Local */}
        {activeTab === 'file' && (
          <div
            className="dropzone"
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            onClick={() => !loading && document.getElementById('fileInput')?.click()}
            style={{ cursor: loading ? 'not-allowed' : 'pointer' }}
          >
            <input
              id="fileInput"
              type="file"
              accept=".csv,.xlsx"
              style={{ display: 'none' }}
              onChange={handleFileChange}
              disabled={loading}
            />
            <div style={{ marginBottom: '16px' }}>
              <FileSpreadsheet size={48} className="text-primary" style={{ margin: '0 auto' }} />
            </div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '8px' }}>
              Arrastra tu archivo CSV o XLSX aquí, o haz clic para examinar
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
              Soporta formatos estandarizados de ventas, operaciones, RRHH o Contact Center.
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
            <AlertCircle size={18} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Selector de Datasets de Demostración con 1 Clic */}
      <div className="card">
        <div className="card-header">
          <h3 style={{ fontSize: '1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={18} className="text-primary" /> ¿No tienes un archivo a mano? Prueba con 1 clic un caso real:
          </h3>
          <span className="badge badge-emerald">Datos Sintéticos Listos</span>
        </div>

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
                  <Play size={14} /> Cargar Caso Demo
                </button>
              </div>
            ))
          ) : (
            <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Cargando casos demo...</div>
          )}
        </div>
      </div>
    </div>
  );
};
