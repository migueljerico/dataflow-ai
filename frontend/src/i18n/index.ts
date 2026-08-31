export type Language =
  | 'es'
  | 'en'
  | 'zh'
  | 'hi'
  | 'fr'
  | 'ar'
  | 'bn'
  | 'pt'
  | 'id'
  | 'ur'
  | 'ru'
  | 'de'
  | 'ja';

export interface LanguageOption {
  code: Language;
  name: string;
  nativeName: string;
}

export const LANGUAGES: LanguageOption[] = [
  { code: 'es', name: 'Spanish', nativeName: 'Español' },
  { code: 'en', name: 'English', nativeName: 'English' },
  { code: 'zh', name: 'Chinese', nativeName: '中文 (简体)' },
  { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी' },
  { code: 'fr', name: 'French', nativeName: 'Français' },
  { code: 'ar', name: 'Arabic', nativeName: 'العربية' },
  { code: 'bn', name: 'Bengali', nativeName: 'বাংলা' },
  { code: 'pt', name: 'Portuguese', nativeName: 'Português' },
  { code: 'id', name: 'Indonesian', nativeName: 'Bahasa Indonesia' },
  { code: 'ur', name: 'Urdu', nativeName: 'اردو' },
  { code: 'ru', name: 'Russian', nativeName: 'Русский' },
  { code: 'de', name: 'German', nativeName: 'Deutsch' },
  { code: 'ja', name: 'Japanese', nativeName: '日本語' },
];

export interface Translations {
  brand: {
    title: string;
    tagline: string;
  };
  header: {
    installApp: string;
    installTitle: string;
    apiKey: string;
    apiKeyActive: string;
    apiKeyTitle: string;
    gdprPrivacy: string;
    gdprTitle: string;
    etlCopilot: string;
  };
  stepper: {
    step1: string;
    step2: string;
    step3: string;
    step4: string;
  };
  upload: {
    title: string;
    dropzoneMain: string;
    dropzoneSub: string;
    browse: string;
    orRemote: string;
    urlPlaceholder: string;
    importUrlBtn: string;
    importing: string;
    openDataBtn: string;
    openDataTitle: string;
    openDataClose: string;
    sampleDataTitle: string;
    sampleDataDesc: string;
    samples: {
      sales: string;
      contactCenter: string;
      hr: string;
      marketing: string;
    };
    formatNotice: string;
  };
  profiling: {
    title: string;
    summary: string;
    qualityScore: string;
    dimensions: {
      completeness: string;
      accuracy: string;
      consistency: string;
      validity: string;
      uniqueness: string;
    };
    detectedIssues: string;
    noIssues: string;
    columnsAnalysis: string;
    colName: string;
    colType: string;
    colSemantic: string;
    colNulls: string;
    colUnique: string;
    proposeRulesBtn: string;
    proposeAiBtn: string;
    loadingPlan: string;
  };
  plan: {
    title: string;
    humanInTheLoop: string;
    source: string;
    summary: string;
    executeBtn: string;
    executingBtn: string;
    approveBtn: string;
    rejectBtn: string;
    stepId: string;
    operation: string;
    column: string;
    risk: string;
    riskLow: string;
    riskMedium: string;
    riskHigh: string;
    reason: string;
    confidence: string;
    estimatedRows: string;
    parameters: string;
    warningsTitle: string;
    noSteps: string;
  };
  report: {
    title: string;
    subtitle: string;
    rowsBefore: string;
    rowsAfter: string;
    appliedSteps: string;
    inputHash: string;
    outputHash: string;
    downloadDataset: string;
    downloadScript: string;
    resetSession: string;
    auditLogTitle: string;
    businessInsightsTitle: string;
    beforeAfterTitle: string;
    cleanedFile: string;
  };
  apiKeyModal: {
    title: string;
    desc: string;
    label: string;
    placeholder: string;
    save: string;
    remove: string;
    cancel: string;
    note: string;
  };
  pwaModal: {
    title: string;
    desc: string;
    installNow: string;
    close: string;
    iosInstructions: string;
  };
  errors: {
    fetchProfiling: string;
    generatePlan: string;
    executePlan: string;
  };
}

export const translations: Partial<Record<Language, Translations>> = {
  es: {
    brand: {
      title: 'DataFlow AI',
      tagline: 'From raw business data to clean, trusted and actionable insights',
    },
    header: {
      installApp: 'Instalar App',
      installTitle: 'Instala DataFlow AI en tu móvil o escritorio',
      apiKey: 'API Key',
      apiKeyActive: 'Gemini: Activo',
      apiKeyTitle: 'Configura tu API Key de Google Gemini para usar la IA Copilot',
      gdprPrivacy: 'Privacidad RGPD',
      gdprTitle: 'Cumplimiento estricto de privacidad: procesamiento efímero y minimización de datos',
      etlCopilot: 'Copiloto ETL',
    },
    stepper: {
      step1: 'Subir Datos',
      step2: 'Data Quality',
      step3: 'Plan ETL & IA',
      step4: 'Resultados & Script',
    },
    upload: {
      title: 'Cargar Dataset Empresarial',
      dropzoneMain: 'Arrastra y suelta tu archivo CSV o Excel aquí',
      dropzoneSub: 'o haz clic para seleccionar desde tu dispositivo',
      browse: 'Explorar archivo',
      orRemote: 'o importa directamente desde una URL segura',
      urlPlaceholder: 'https://ejemplo.com/datos.csv',
      importUrlBtn: 'Importar por URL',
      importing: 'Descargando y validando...',
      openDataBtn: 'Explorar Open Data (CKAN)',
      openDataTitle: 'Catálogo de Datos Abiertos Públicos (CKAN)',
      openDataClose: 'Cerrar catálogo',
      sampleDataTitle: 'Datasets Empresariales de Prueba (1-Clic)',
      sampleDataDesc: 'Haz clic en una plantilla con anomalías reales para probar el flujo completo:',
      samples: {
        sales: 'Ventas B2B (Símbolos €, fechas heterogéneas, siglas)',
        contactCenter: 'Contact Center (AHT negativo, missing markers N/D)',
        hr: 'People Analytics (Formato europeo, absentismos negativos)',
        marketing: 'Campañas Marketing (Porcentajes fuera de rango [0,100%])',
      },
      formatNotice: 'Soporta CSV delimitado por coma/punto y coma, codificaciones UTF-8 / Windows-1252 / ISO-8859 y libros Excel (.xlsx). Límite de 10 MB.',
    },
    profiling: {
      title: 'Auditoría de Calidad y Profiling',
      summary: 'Resumen del dataset',
      qualityScore: 'Data Quality Score',
      dimensions: {
        completeness: 'Completitud',
        accuracy: 'Precisión',
        consistency: 'Consistencia',
        validity: 'Validez',
        uniqueness: 'Unicidad',
      },
      detectedIssues: 'Anomalías Detectadas',
      noIssues: 'No se detectaron problemas críticos en el dataset.',
      columnsAnalysis: 'Análisis de Columnas y Tipos Inferidos',
      colName: 'Columna',
      colType: 'Tipo Inferido',
      colSemantic: 'Hint Semántico',
      colNulls: 'Nulos',
      colUnique: 'Valores Únicos',
      proposeRulesBtn: 'Generar Plan con Reglas Deterministas',
      proposeAiBtn: 'Generar Plan Asistido por Copiloto IA (Gemini)',
      loadingPlan: 'Generando plan de transformaciones...',
    },
    plan: {
      title: 'Revisión Humana del Plan ETL (Human-in-the-Loop)',
      humanInTheLoop: 'La IA propone. El usuario decide. Python ejecuta.',
      source: 'Origen del plan',
      summary: 'Resumen',
      executeBtn: 'Ejecutar Plan',
      executingBtn: 'Ejecutando en Python...',
      approveBtn: 'Aprobar',
      rejectBtn: 'Rechazar',
      stepId: 'Paso',
      operation: 'Operación',
      column: 'Columna',
      risk: 'Riesgo',
      riskLow: 'Riesgo bajo',
      riskMedium: 'Riesgo medio',
      riskHigh: 'Riesgo alto',
      reason: 'Motivo',
      confidence: 'Confianza',
      estimatedRows: 'Filas estimadas',
      parameters: 'Parámetros',
      warningsTitle: 'Avisos y Guardrails de Seguridad',
      noSteps: 'No hay pasos disponibles en este plan.',
    },
    report: {
      title: 'Transformación Completada con Éxito',
      subtitle: 'El dataset ha sido limpiado y verificado con ejecución determinista en Python/pandas.',
      rowsBefore: 'Filas Iniciales',
      rowsAfter: 'Filas Finales',
      appliedSteps: 'Transformaciones Aplicadas',
      inputHash: 'MD5 Entrada',
      outputHash: 'MD5 Salida',
      downloadDataset: 'Descargar Dataset Limpio',
      downloadScript: 'Descargar Script Python (.py)',
      resetSession: 'Limpiar Otro Dataset',
      auditLogTitle: 'Trazabilidad y Log de Auditoría',
      businessInsightsTitle: 'Business Analytics & KPIs Calculados',
      beforeAfterTitle: 'Comparativa de Calidad Antes / Después',
      cleanedFile: 'Fichero limpio generado',
    },
    apiKeyModal: {
      title: 'Configuración de Google Gemini API Key',
      desc: 'Introduce tu clave de API personal (BYOK) para habilitar el Copiloto IA. Tu clave se almacena de forma segura en tu navegador y nunca se guarda en el servidor.',
      label: 'Gemini API Key',
      placeholder: 'AIzaSy...',
      save: 'Guardar Clave',
      remove: 'Eliminar Clave',
      cancel: 'Cancelar',
      note: 'Si no introduces una clave, podrás seguir usando DataFlow AI con el Motor de Reglas Deterministas al 100% de funcionalidad.',
    },
    pwaModal: {
      title: 'Instalar DataFlow AI',
      desc: 'Instala esta aplicación web progresiva (PWA) en tu dispositivo para acceder de forma rápida y trabajar con tus datasets empresariales sin conexión.',
      installNow: 'Instalar Ahora',
      close: 'Cerrar',
      iosInstructions: 'En iPhone/iPad: pulsa el botón Compartir y selecciona "Añadir a la pantalla de inicio".',
    },
    errors: {
      fetchProfiling: 'Error al obtener profiling del dataset.',
      generatePlan: 'Error al generar plan de transformaciones.',
      executePlan: 'Error al ejecutar plan ETL.',
    },
  },
  en: {
    brand: {
      title: 'DataFlow AI',
      tagline: 'From raw business data to clean, trusted and actionable insights',
    },
    header: {
      installApp: 'Install App',
      installTitle: 'Install DataFlow AI on your mobile or desktop',
      apiKey: 'API Key',
      apiKeyActive: 'Gemini: Active',
      apiKeyTitle: 'Configure your Google Gemini API Key to use the AI Copilot',
      gdprPrivacy: 'GDPR Privacy',
      gdprTitle: 'Strict privacy compliance: ephemeral processing and data minimization',
      etlCopilot: 'ETL Copilot',
    },
    stepper: {
      step1: 'Upload Data',
      step2: 'Data Quality',
      step3: 'ETL & AI Plan',
      step4: 'Results & Script',
    },
    upload: {
      title: 'Upload Enterprise Dataset',
      dropzoneMain: 'Drag and drop your CSV or Excel file here',
      dropzoneSub: 'or click to select from your device',
      browse: 'Browse file',
      orRemote: 'or import directly from a secure URL',
      urlPlaceholder: 'https://example.com/data.csv',
      importUrlBtn: 'Import from URL',
      importing: 'Downloading and validating...',
      openDataBtn: 'Explore Open Data (CKAN)',
      openDataTitle: 'Public Open Data Catalog (CKAN)',
      openDataClose: 'Close catalog',
      sampleDataTitle: 'Enterprise Sample Datasets (1-Click)',
      sampleDataDesc: 'Click on a sample with real anomalies to test the entire flow:',
      samples: {
        sales: 'B2B Sales (€ symbols, mixed dates, business acronyms)',
        contactCenter: 'Contact Center (Negative AHT, missing markers N/D)',
        hr: 'People Analytics (European numbers, negative leave days)',
        marketing: 'Marketing Campaigns (Out-of-range percentages [0,100%])',
      },
      formatNotice: 'Supports CSV delimited by comma/semicolon, UTF-8 / Windows-1252 / ISO-8859 encodings, and Excel spreadsheets (.xlsx). 10 MB limit.',
    },
    profiling: {
      title: 'Quality Audit & Profiling',
      summary: 'Dataset Summary',
      qualityScore: 'Data Quality Score',
      dimensions: {
        completeness: 'Completeness',
        accuracy: 'Accuracy',
        consistency: 'Consistency',
        validity: 'Validity',
        uniqueness: 'Uniqueness',
      },
      detectedIssues: 'Detected Issues',
      noIssues: 'No critical quality issues were detected in this dataset.',
      columnsAnalysis: 'Column Analysis & Inferred Types',
      colName: 'Column',
      colType: 'Inferred Type',
      colSemantic: 'Semantic Hint',
      colNulls: 'Nulls',
      colUnique: 'Unique Values',
      proposeRulesBtn: 'Generate Plan with Deterministic Rules',
      proposeAiBtn: 'Generate Plan Assisted by AI Copilot (Gemini)',
      loadingPlan: 'Generating transformation plan...',
    },
    plan: {
      title: 'Human-in-the-Loop ETL Plan Review',
      humanInTheLoop: 'AI proposes. User decides. Python executes.',
      source: 'Plan Origin',
      summary: 'Summary',
      executeBtn: 'Execute Plan',
      executingBtn: 'Executing in Python...',
      approveBtn: 'Approve',
      rejectBtn: 'Reject',
      stepId: 'Step',
      operation: 'Operation',
      column: 'Column',
      risk: 'Risk',
      riskLow: 'Low risk',
      riskMedium: 'Medium risk',
      riskHigh: 'High risk',
      reason: 'Reason',
      confidence: 'Confidence',
      estimatedRows: 'Estimated Rows',
      parameters: 'Parameters',
      warningsTitle: 'Security Warnings & Guardrails',
      noSteps: 'No steps available in this plan.',
    },
    report: {
      title: 'Transformation Successfully Completed',
      subtitle: 'The dataset has been cleaned and verified with deterministic execution in Python/pandas.',
      rowsBefore: 'Initial Rows',
      rowsAfter: 'Final Rows',
      appliedSteps: 'Applied Transformations',
      inputHash: 'Input MD5',
      outputHash: 'Output MD5',
      downloadDataset: 'Download Clean Dataset',
      downloadScript: 'Download Python Script (.py)',
      resetSession: 'Clean Another Dataset',
      auditLogTitle: 'Audit Trail & Validation Log',
      businessInsightsTitle: 'Business Analytics & Calculated KPIs',
      beforeAfterTitle: 'Quality Comparison Before / After',
      cleanedFile: 'Generated clean file',
    },
    apiKeyModal: {
      title: 'Google Gemini API Key Configuration',
      desc: 'Enter your personal API key (BYOK) to enable the AI Copilot. Your key is stored securely in your browser and is never stored on the server.',
      label: 'Gemini API Key',
      placeholder: 'AIzaSy...',
      save: 'Save Key',
      remove: 'Remove Key',
      cancel: 'Cancel',
      note: 'If you do not enter a key, you can continue using DataFlow AI with the 100% functional Deterministic Rules Engine.',
    },
    pwaModal: {
      title: 'Install DataFlow AI',
      desc: 'Install this Progressive Web App (PWA) on your device for fast access and working with enterprise datasets.',
      installNow: 'Install Now',
      close: 'Close',
      iosInstructions: 'On iPhone/iPad: tap Share and select "Add to Home Screen".',
    },
    errors: {
      fetchProfiling: 'Error retrieving dataset profiling.',
      generatePlan: 'Error generating transformation plan.',
      executePlan: 'Error executing ETL plan.',
    },
  },
};
