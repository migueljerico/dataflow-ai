import React, { useRef } from 'react';
import { FileSpreadsheet } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';

interface Props {
  loading: boolean;
  onUpload: (f: File) => void;
  onUploadMultiple?: (files: File[]) => void;
}

export const FileDropzone: React.FC<Props> = ({ loading, onUpload, onUploadMultiple }) => {
  const { t } = useLanguage();
  const ref = useRef<HTMLInputElement>(null);

  const handleFiles = (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    if (fileList.length > 1 && onUploadMultiple) {
      onUploadMultiple(Array.from(fileList));
    } else {
      onUpload(fileList[0]);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files) {
      handleFiles(e.dataTransfer.files);
    }
  };

  return (
    <div
      className="dropzone"
      role="button"
      tabIndex={0}
      aria-label={t.upload?.dropzoneAriaLabel ?? 'Zona de arrastre'}
      onDragOver={(e) => e.preventDefault()}
      onDrop={handleDrop}
      onClick={() => !loading && ref.current?.click()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          ref.current?.click();
        }
      }}
      style={{ cursor: loading ? "not-allowed" : "pointer" }}
    >
      <input
        ref={ref}
        id="fileInput"
        type="file"
        accept=".csv,.xlsx"
        multiple
        style={{ display: "none" }}
        disabled={loading}
        onChange={(e) => handleFiles(e.target.files)}
      />
      <div style={{ marginBottom: "16px" }}>
        <FileSpreadsheet size={48} className="text-primary" style={{ margin: "0 auto" }} aria-hidden="true" />
      </div>
      <h3 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "8px" }}>
        {t.upload?.dropzoneHeading ?? 'Arrastra tus archivos CSV o XLSX aquí (uno o varios a la vez)'}
      </h3>
      <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
        {t.upload?.dropzoneMultiNotice ?? 'Soporta subida multi-archivo para modelado relacional y Esquema de Estrella (Northwind, ventas, etc.).'}
      </p>
    </div>
  );
};
