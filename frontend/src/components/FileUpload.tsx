import React, { useState, useEffect } from 'react';
import { Upload, FileSpreadsheet, AlertCircle, Sparkles, PhoneCall, ShoppingCart, Users, Play } from 'lucide-react';
import { api } from '../services/api';
import { DatasetMetadata, SampleDataset } from '../types';

interface Props {
  onUploadSuccess: (metadata: DatasetMetadata) => void;
}

export const FileUpload: React.FC<Props> = ({ onUploadSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [samples, setSamples] = useState<SampleDataset[]>([]);

  useEffect(() => {
    const fetchSamples = async () => {
      try {
        const list = await api.listSampleDatasets();
        setSamples(list);
      } catch {
        // Fallback si la API aún no responde
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
    setError(null);
    try {
      const metadata = await api.uploadDataset(file);
      onUploadSuccess(metadata);
    } catch (err: any) {
      setError(err.message || 'Error al subir el archivo.');
    } finally {
      setLoading(false);
    }
  };

  const loadSample = async (sampleId: string) => {
    setLoading(true);
    setError(null);
    try {
      const metadata = await api.loadSampleDataset(sampleId);
      onUploadSuccess(metadata);
    } catch (err: any) {
      setError(err.message || 'Error al cargar el dataset de demostración.');
    } finally {
      setLoading(false);
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
        <div className="card-header">
          <h2 className="card-title">
            <Upload size={20} className="text-primary" /> Carga de Dataset Empresarial
          </h2>
          <span className="badge badge-blue">Máx. 10 MB | CSV / XLSX</span>
        </div>

        <div
          className="dropzone"
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => document.getElementById('fileInput')?.click()}
        >
          <input
            id="fileInput"
            type="file"
            accept=".csv,.xlsx"
            style={{ display: 'none' }}
            onChange={handleFileChange}
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

        {loading && (
          <div style={{ marginTop: '16px', textAlign: 'center', color: 'var(--primary)', fontWeight: 600 }}>
            ⚡ Validando estructura del archivo y cargando dataset...
          </div>
        )}

        {error && (
          <div style={{ marginTop: '16px', padding: '12px', borderRadius: '8px', backgroundColor: 'rgba(244, 63, 94, 0.1)', color: 'var(--accent-rose)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertCircle size={18} /> {error}
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

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
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
