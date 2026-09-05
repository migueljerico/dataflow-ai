import React, { useState, useRef } from 'react';
import { 
  Network, 
  Download, 
  Copy, 
  Check, 
  ShieldCheck, 
  AlertTriangle, 
  Database, 
  Layers, 
  FileCode, 
  Key, 
  Table as TableIcon,
  ArrowRight,
  Sparkles
} from 'lucide-react';
import { MultiTableStarSchema, StarSchemaTableNode, RelationshipIntegrityAudit } from '../types';
import { api } from '../services/api';

interface Props {
  schema: MultiTableStarSchema;
  onBackToDatasets?: () => void;
}

export const MultiTableStarSchemaViewer: React.FC<Props> = ({ schema, onBackToDatasets }) => {
  const [selectedTable, setSelectedTable] = useState<StarSchemaTableNode | null>(schema.fact_table);
  const [selectedRel, setSelectedRel] = useState<RelationshipIntegrityAudit | null>(null);
  const [copiedDax, setCopiedDax] = useState<string | null>(null);
  const [isExportingPng, setIsExportingPng] = useState<boolean>(false);
  const svgRef = useRef<SVGSVGElement>(null);

  const W = 960;
  const H = 640;
  const cx = W / 2;
  const cy = H / 2;
  const rx = 340;
  const ry = 220;

  // Distribuir dimensiones radialmente alrededor de la tabla de hechos
  const dimensionsCount = schema.dimension_tables.length;
  const placedDimensions = schema.dimension_tables.map((dim, idx) => {
    const angle = (2 * Math.PI * idx) / Math.max(1, dimensionsCount) - Math.PI / 2;
    return {
      dim,
      x: cx + rx * Math.cos(angle),
      y: cy + ry * Math.sin(angle),
    };
  });

  const copyText = (label: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedDax(label);
    setTimeout(() => setCopiedDax(null), 2000);
  };

  const handleDownloadTmdl = () => {
    const blob = new Blob([schema.tmdl_definition], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${schema.model_name}.tmdl`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
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
        const scale = 2; // 2x Retina
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
          a.download = `esquema_estrella_${schema.fact_table.table_name}.png`;
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }} data-testid="multi-star-schema-visual">
      {/* Barra de KPIs y Acciones del Modelo */}
      <div className="card" style={{ padding: '16px 20px', backgroundColor: 'var(--bg-card)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: '36px', height: '36px', borderRadius: '8px', backgroundColor: 'rgba(59, 130, 246, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Network size={20} className="text-primary" />
              </div>
              <div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  Esquema de Estrella Multi-Tabla (Power BI)
                  <span className="badge badge-green" style={{ fontSize: '0.75rem' }}>
                    {schema.relationships.length} Relaciones (*:1)
                  </span>
                </h2>
                <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  Modelo relacional dimensional inferido automáticamente a partir de los datasets limpios.
                </p>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', backgroundColor: 'rgba(16, 185, 129, 0.1)', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
              <ShieldCheck size={16} style={{ color: '#10b981' }} />
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#10b981' }}>
                Integridad Referencial: {schema.referential_integrity_score}%
              </span>
            </div>

            <button
              type="button"
              className="btn btn-outline"
              onClick={exportAsPng}
              disabled={isExportingPng}
              style={{ fontSize: '0.85rem', padding: '8px 14px' }}
            >
              <Download size={14} /> {isExportingPng ? 'Generando PNG...' : 'Descargar Imagen PNG'}
            </button>

            <button
              type="button"
              className="btn btn-primary"
              onClick={handleDownloadTmdl}
              style={{ fontSize: '0.85rem', padding: '8px 14px' }}
            >
              <FileCode size={14} /> Descargar TMDL (Power BI)
            </button>
          </div>
        </div>
      </div>

      {/* Grid: Diagrama SVG Interactivo + Panel de Inspección */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(600px, 1fr) 340px', gap: '20px', alignItems: 'start' }}>
        
        {/* Diagrama SVG */}
        <div className="card" style={{ padding: '16px', backgroundColor: '#0f172a', borderRadius: '12px', border: '1px solid #1e293b', overflow: 'hidden' }}>
          <svg
            ref={svgRef}
            viewBox={`0 0 ${W} ${H}`}
            style={{ width: '100%', height: 'auto', display: 'block' }}
          >
            <defs>
              <linearGradient id="factGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#1e293b" />
                <stop offset="100%" stopColor="#0f172a" />
              </linearGradient>
              <linearGradient id="dimGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#1e293b" />
                <stop offset="100%" stopColor="#0b1329" />
              </linearGradient>
              <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>

            {/* Líneas de Relación con la tabla central o entre dimensiones */}
            {placedDimensions.map(({ dim, x, y }) => {
              // Buscar relación si existe
              const rel = schema.relationships.find(
                (r) =>
                  (r.to_table.toLowerCase().includes(dim.table_name.toLowerCase().replace('dim_', '')) ||
                   dim.table_name.toLowerCase().includes(r.to_table.toLowerCase())) &&
                  (r.from_table.toLowerCase().includes(schema.fact_table.table_name.toLowerCase()) ||
                   schema.fact_table.table_name.toLowerCase().includes(r.from_table.toLowerCase()))
              ) || schema.relationships.find(
                (r) => dim.table_name.toLowerCase().includes(r.to_table.toLowerCase()) ||
                       dim.table_name.toLowerCase().includes(r.from_table.toLowerCase())
              );

              const isClean = rel ? rel.is_referential_clean : true;
              const strokeColor = rel ? (isClean ? '#38bdf8' : '#f59e0b') : '#475569';
              const isSelected = selectedRel === rel;

              return (
                <g key={`rel-${dim.table_id}`} onClick={() => rel && setSelectedRel(rel)} style={{ cursor: rel ? 'pointer' : 'default' }}>
                  <line
                    x1={cx}
                    y1={cy}
                    x2={x}
                    y2={y}
                    stroke={strokeColor}
                    strokeWidth={isSelected ? 3 : 1.75}
                    strokeDasharray="5,4"
                    opacity={0.85}
                  />
                  {/* Cardinalidad en lado dimensión: 1 */}
                  <circle cx={x + (cx - x) * 0.28} cy={y + (cy - y) * 0.28} r={11} fill="#0f172a" stroke="#10b981" strokeWidth={1.5} />
                  <text
                    x={x + (cx - x) * 0.28}
                    y={y + (cy - y) * 0.28 + 4}
                    fill="#10b981"
                    fontSize={11}
                    fontWeight="700"
                    textAnchor="middle"
                  >
                    1
                  </text>

                  {/* Cardinalidad en lado hechos: * */}
                  <circle cx={cx + (x - cx) * 0.28} cy={cy + (y - cy) * 0.28} r={11} fill="#0f172a" stroke="#f59e0b" strokeWidth={1.5} />
                  <text
                    x={cx + (x - cx) * 0.28}
                    y={cy + (y - cy) * 0.28 + 4}
                    fill="#f59e0b"
                    fontSize={12}
                    fontWeight="700"
                    textAnchor="middle"
                  >
                    *
                  </text>

                  {/* Badge de Integridad Referencial en el centro de la línea */}
                  {rel && (
                    <g transform={`translate(${(cx + x) / 2}, ${(cy + y) / 2})`}>
                      <rect
                        x="-38"
                        y="-10"
                        width="76"
                        height="20"
                        rx="10"
                        fill="#0f172a"
                        stroke={isClean ? '#10b981' : '#f59e0b'}
                        strokeWidth="1"
                      />
                      <text
                        x="0"
                        y="4"
                        fill={isClean ? '#34d399' : '#fbbf24'}
                        fontSize="9"
                        fontWeight="700"
                        textAnchor="middle"
                      >
                        {rel.match_percentage}% OK
                      </text>
                    </g>
                  )}
                </g>
              );
            })}

            {/* NODO CENTRAL: TABLA DE HECHOS */}
            {(() => {
              const fact = schema.fact_table;
              const isSelected = selectedTable?.table_id === fact.table_id;
              const boxW = 230;
              const boxH = 135;

              return (
                <g
                  transform={`translate(${cx - boxW / 2}, ${cy - boxH / 2})`}
                  onClick={() => { setSelectedTable(fact); setSelectedRel(null); }}
                  style={{ cursor: 'pointer' }}
                >
                  <rect
                    width={boxW}
                    height={boxH}
                    rx="14"
                    fill="url(#factGrad)"
                    stroke="#f59e0b"
                    strokeWidth={isSelected ? 3 : 2}
                    filter={isSelected ? 'url(#glow)' : undefined}
                  />
                  {/* Encabezado Hechos */}
                  <text x={boxW / 2} y={26} fill="#f59e0b" fontSize="14" fontWeight="800" textAnchor="middle">
                    {fact.table_name}
                  </text>
                  <text x={boxW / 2} y={44} fill="#cbd5e1" fontSize="11" textAnchor="middle">
                    Tabla de Hechos · {fact.row_count.toLocaleString()} filas
                  </text>

                  <line x1="16" y1="54" x2={boxW - 16} y2="54" stroke="#334155" strokeWidth="1" />

                  {/* Medidas Principales */}
                  <text x={boxW / 2} y={72} fill="#94a3b8" fontSize="11" fontWeight="700" textAnchor="middle">
                    Medidas: {fact.measures.length || 1}
                  </text>
                  {fact.measures.slice(0, 3).map((m, i) => (
                    <text key={m} x={boxW / 2} y={90 + i * 14} fill="#f8fafc" fontSize="10" textAnchor="middle">
                      • {m}
                    </text>
                  ))}
                  {fact.measures.length > 3 && (
                    <text x={boxW / 2} y={90 + 3 * 14} fill="#64748b" fontSize="9" textAnchor="middle">
                      +{fact.measures.length - 3} más
                    </text>
                  )}
                </g>
              );
            })()}

            {/* NODOS PERIFÉRICOS: TABLAS DE DIMENSIÓN */}
            {placedDimensions.map(({ dim, x, y }) => {
              const isSelected = selectedTable?.table_id === dim.table_id;
              const boxW = 160;
              const boxH = 86;

              return (
                <g
                  key={dim.table_id}
                  transform={`translate(${x - boxW / 2}, ${y - boxH / 2})`}
                  onClick={() => { setSelectedTable(dim); setSelectedRel(null); }}
                  style={{ cursor: 'pointer' }}
                >
                  <rect
                    width={boxW}
                    height={boxH}
                    rx="12"
                    fill="url(#dimGrad)"
                    stroke="#38bdf8"
                    strokeWidth={isSelected ? 2.5 : 1.5}
                    filter={isSelected ? 'url(#glow)' : undefined}
                  />
                  <text x={boxW / 2} y={24} fill="#38bdf8" fontSize="12" fontWeight="700" textAnchor="middle">
                    {dim.table_name}
                  </text>
                  <text x={boxW / 2} y={42} fill="#94a3b8" fontSize="10" textAnchor="middle">
                    PK: {dim.primary_keys[0] || 'ID'}
                  </text>
                  <text x={boxW / 2} y={58} fill="#cbd5e1" fontSize="10" textAnchor="middle">
                    {dim.row_count.toLocaleString()} registros
                  </text>
                  <text x={boxW / 2} y={72} fill="#64748b" fontSize="9" textAnchor="middle">
                    {dim.attributes.length} atributos
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Panel Lateral de Inspección */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {selectedTable && (
            <div className="card" style={{ padding: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                <TableIcon size={18} className="text-primary" />
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0 }}>
                  {selectedTable.table_name}
                </h3>
                <span className={`badge ${selectedTable.role === 'fact' ? 'badge-blue' : 'badge-green'}`} style={{ marginLeft: 'auto', fontSize: '0.75rem' }}>
                  {selectedTable.role === 'fact' ? 'Hechos' : 'Dimensión'}
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '12px', fontSize: '0.82rem' }}>
                <div style={{ padding: '8px', backgroundColor: 'var(--bg-input)', borderRadius: '6px' }}>
                  <div style={{ color: 'var(--text-muted)' }}>Filas</div>
                  <div style={{ fontWeight: 700, fontSize: '1rem' }}>{selectedTable.row_count.toLocaleString()}</div>
                </div>
                <div style={{ padding: '8px', backgroundColor: 'var(--bg-input)', borderRadius: '6px' }}>
                  <div style={{ color: 'var(--text-muted)' }}>Columnas</div>
                  <div style={{ fontWeight: 700, fontSize: '1rem' }}>{selectedTable.column_count}</div>
                </div>
              </div>

              {selectedTable.primary_keys.length > 0 && (
                <div style={{ marginBottom: '10px' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Claves Primarias (PK):
                  </div>
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    {selectedTable.primary_keys.map(pk => (
                      <span key={pk} className="badge badge-blue" style={{ fontSize: '0.75rem' }}>
                        <Key size={10} style={{ marginRight: '4px' }} /> {pk}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {selectedTable.foreign_keys.length > 0 && (
                <div style={{ marginBottom: '10px' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Claves Foráneas (FK):
                  </div>
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    {selectedTable.foreign_keys.map(fk => (
                      <span key={fk} className="badge badge-amber" style={{ fontSize: '0.75rem' }}>
                        {fk}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {selectedTable.measures.length > 0 && (
                <div style={{ marginBottom: '10px' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Medidas Numéricas:
                  </div>
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    {selectedTable.measures.map(m => (
                      <span key={m} className="badge badge-green" style={{ fontSize: '0.75rem' }}>
                        {m}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Tarjeta de Relación Seleccionada */}
          {selectedRel && (
            <div className="card" style={{ padding: '16px', border: selectedRel.is_referential_clean ? '1px solid #10b981' : '1px solid #f59e0b' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <Layers size={16} className={selectedRel.is_referential_clean ? 'text-success' : 'text-warning'} />
                <h4 style={{ fontSize: '0.95rem', fontWeight: 700, margin: 0 }}>
                  Detalle de Relación
                </h4>
              </div>

              <div style={{ fontSize: '0.85rem', marginBottom: '8px' }}>
                <span style={{ fontWeight: 600 }}>{selectedRel.from_table}.{selectedRel.from_column}</span>
                <ArrowRight size={12} style={{ margin: '0 6px', display: 'inline' }} />
                <span style={{ fontWeight: 600 }}>{selectedRel.to_table}.{selectedRel.to_column}</span>
              </div>

              <div style={{ fontSize: '0.82rem', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div>Coincidencia: <strong>{selectedRel.match_percentage}%</strong></div>
                <div>Filas con FK: <strong>{selectedRel.total_fk_rows.toLocaleString()}</strong></div>
                <div>Filas huérfanas: <strong>{selectedRel.orphan_fk_rows}</strong></div>
                {selectedRel.orphan_samples.length > 0 && (
                  <div style={{ marginTop: '6px', padding: '6px', backgroundColor: 'rgba(245, 158, 11, 0.1)', borderRadius: '6px' }}>
                    <div style={{ color: '#d97706', fontSize: '0.75rem', fontWeight: 600 }}>Ejemplos de huérfanos:</div>
                    <div style={{ fontSize: '0.75rem', fontFamily: 'monospace' }}>
                      {selectedRel.orphan_samples.join(', ')}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Medidas DAX Generadas */}
          <div className="card" style={{ padding: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
              <Sparkles size={16} className="text-primary" />
              <h4 style={{ fontSize: '0.95rem', fontWeight: 700, margin: 0 }}>
                Medidas DAX Sugeridas
              </h4>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '200px', overflowY: 'auto' }}>
              {Object.entries(schema.suggested_dax_measures).map(([name, dax]) => (
                <div
                  key={name}
                  style={{
                    padding: '8px',
                    backgroundColor: 'var(--bg-input)',
                    borderRadius: '6px',
                    fontSize: '0.8rem',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    gap: '8px'
                  }}
                >
                  <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    <div style={{ fontWeight: 600 }}>{name}</div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem', fontFamily: 'monospace' }}>{dax}</div>
                  </div>
                  <button
                    type="button"
                    className="btn btn-outline"
                    onClick={() => copyText(name, `${name} = ${dax}`)}
                    style={{ padding: '4px 6px', height: 'auto' }}
                    title="Copiar DAX"
                  >
                    {copiedDax === name ? <Check size={12} color="#10b981" /> : <Copy size={12} />}
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
