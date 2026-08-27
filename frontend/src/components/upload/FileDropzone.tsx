import React, { useRef } from 'react';
import { FileSpreadsheet } from 'lucide-react';
interface Props { loading: boolean; onUpload: (f: File) => void; }
export const FileDropzone: React.FC<Props> = ({ loading, onUpload }) => {
  const ref = useRef<HTMLInputElement>(null);
  const handleDrop = async (e: React.DragEvent) => { e.preventDefault(); if (e.dataTransfer.files[0]) await onUpload(e.dataTransfer.files[0]); };
  return (<div className="dropzone" role="button" tabIndex={0} aria-label="Zona de arrastre" onDragOver={(e)=>e.preventDefault()} onDrop={handleDrop} onClick={()=>!loading && ref.current?.click()} onKeyDown={(e)=>{ if(e.key==="Enter"||e.key===" "){e.preventDefault(); ref.current?.click();}}} style={{cursor: loading?"not-allowed":"pointer"}}><input ref={ref} id="fileInput" type="file" accept=".csv,.xlsx" style={{display:"none"}} disabled={loading} onChange={(e)=>{ if(e.target.files?.[0]) onUpload(e.target.files[0]);}} /><div style={{marginBottom:"16px"}}><FileSpreadsheet size={48} className="text-primary" style={{margin:"0 auto"}} aria-hidden="true"/></div><h3 style={{fontSize:"1.1rem",fontWeight:700,marginBottom:"8px"}}>Arrastra tu archivo CSV o XLSX aquí, o haz clic para examinar</h3><p style={{color:"var(--text-muted)",fontSize:"0.875rem"}}>Soporta ventas, operaciones, RRHH o Contact Center.</p></div>);
};
