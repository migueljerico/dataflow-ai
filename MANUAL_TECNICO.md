# MANUAL TÉCNICO — DataFlow AI

**Versión:** 1.15.1  
**Fecha de actualización:** 3 de septiembre de 2026  
**Autor:** migueljerico  
**Licencia:** MIT  
**Stack:** Python 3.11/3.14 (Pandas 3.0, Pydantic 2.13, PyArrow 25, Pytest 9.1) · FastAPI · React 19 · TypeScript 5.9 · Vite 8 · Vitest 4.1 · Node.js 24 · Docker


---

## Tabla de Contenido

1. [Descripción General del Sistema](#1-descripción-general-del-sistema)
2. [Arquitectura General](#2-arquitectura-general)
3. [Principios de Diseño y Gobierno de Datos](#3-principios-de-diseño-y-gobierno-de-datos)
4. [Estructura del Repositorio](#4-estructura-del-repositorio)
5. [Módulos y Componentes del Backend](#5-módulos-y-componentes-del-backend)
6. [Módulos y Componentes del Frontend](#6-módulos-y-componentes-del-frontend)
7. [Catálogo de Transformaciones ETL](#7-catálogo-de-transformaciones-etl)
8. [Modelo de Calidad de Datos](#8-modelo-de-calidad-de-datos)
9. [API de Endpoints](#9-api-de-endpoints)
10. [Variables de Entorno](#10-variables-de-entorno)
11. [Guía de Despliegue](#11-guía-de-despliegue)
12. [Pipeline de Integración Continua (CI)](#12-pipeline-de-integración-continua-ci)
13. [Suite de Pruebas](#13-suite-de-pruebas)
14. [Consideraciones de Seguridad y Privacidad](#14-consideraciones-de-seguridad-y-privacidad)
15. [Limitaciones Conocidas](#15-limitaciones-conocidas)
16. [Mejoras Futuras](#16-mejoras-futuras)

---

## 1. Descripción General del Sistema

**DataFlow AI** es una plataforma inteligente de preparación, calidad, transformación y análisis de datos empresariales. Su objetivo es automatizar el proceso de limpieza de datos crudos heterogéneos (CSV/XLSX) procedentes de CRMs, ERPs, Contact Centers, RRHH y exportaciones de terceros, para entregar un dataset limpio, tipado y listo para su carga en herramientas de Business Intelligence como Power BI.

El flujo de trabajo se resume en:

```text
DATOS BRUTOS (CSV/XLSX)
       ↓
DATA PROFILING AUTOMÁTICO (Tipos, Nulos, Detección Semántica)
       ↓
EVALUACIÓN DE DATA QUALITY (Score 0-100 en 5 dimensiones)
       ↓
SUGERENCIA DE PLAN ETL (Reglas Deterministas o IA Copilot BYOK)
       ↓
REVISIÓN HUMANA (Human-in-the-Loop: Aprobar/Editar/Rechazar paso a paso)
       ↓
MOTOR DETERMINISTA PYTHON / PANDAS
       ↓
DATASET LIMPIO + BUSINESS ANALYTICS + SCRIPT REPRODUCIBLE (.py)
```

La plataforma sigue el principio estricto de gobierno:

> **"La IA propone. El usuario decide. Python ejecuta."**

---

## 2. Arquitectura General

El sistema está construido como una aplicación monolítica desplegable en contenedores, con un backend FastAPI y un frontend React/Vite que en producción se sirve estáticamente desde el propio backend (para Google Cloud Run) o mediante Nginx (para docker-compose local).

### Diagrama ASCII de Capas

```text
┌────────────────────────────────────────────────────────────────────────┐
│                     CAPA DE PRESENTACIÓN (Frontend)                   │
│   React 18 + TypeScript + Vite                                        │
│   Componentes: FileUpload · ProfilingDashboard · PlanReview ·         │
│                ExecutionReport · BusinessInsights · ApiKeyModal       │
│   Servicio API: fetch HTTP a /api/v1/*                                │
└───────────────────────────────┬────────────────────────────────────────┘
                                │  HTTP/REST (JSON)
                                │  /api/v1/*  (proxy Vite o Nginx)
┌───────────────────────────────▼────────────────────────────────────────┐
│                     CAPA DE PRESENTACIÓN (Backend API)                │
│   FastAPI (app.main)                                                  │
│   Routers: datasets · profiling · quality · plans · runs · analytics  │
│   Modelos Pydantic (validation & serialization)                       │
│   Gestión central de excepciones (FunctionalException)                │
└───────────────────────────────┬────────────────────────────────────────┘
                                │  Llamadas a servicios estáticos
┌───────────────────────────────▼────────────────────────────────────────┐
│                        CAPA DE LÓGICA DE NEGOCIO                      │
│   Services:                                                           │
│   DatasetService · ProfilerService · QualityService · ETLService ·   │
│   AIService (Gemini/Mock) · AnalyticsService · ScriptGeneratorService│
│                                                                        │
│   Transformations Registry (catálogo controlado de operaciones ETL)   │
│   Core: config · exceptions · number_parsing                          │
└───────────────────────────────┬────────────────────────────────────────┘
                                │  Pandas / Python determinista
┌───────────────────────────────▼────────────────────────────────────────┐
│                      CAPA DE DATOS / PERSISTENCIA                     │
│   Sistema de ficheros local: backend/uploads/                         │
│   Cachés en memoria: DATASET_CACHE · PLANS_CACHE · RUNS_CACHE ·      │
│                      PROFILING_CACHE · QUALITY_CACHE · ANALYTICS_CACHE│
│   API externa: Google Gemini (GenerateContent) — solo si BYOK         │
│   Almacenamiento efímero (sin base de datos persistente en MVP)       │
└────────────────────────────────────────────────────────────────────────┘
```

### Flujo de Datos Simplificado

```text
[Frontend React] → HTTP → [FastAPI Router] → [Services] → [Pandas DataFrame]
                         │                         │
                         │                         ├─→ Profiling (tipos, semántica)
                         │                         ├─→ Quality (5 dimensiones)
                         │                         ├─→ Plan ETL (reglas o IA)
                         │                         ├─→ Ejecución ETL (determinista)
                         │                         └─→ Analytics / Script generado
                         │
                         └─ Upload CSV/XLSX → UPLOAD_DIR → DatasetService
```

---

## 3. Principios de Diseño y Gobierno de Datos

### 3.1 Human-in-the-Loop

Ninguna modificación de datos ocurre sin aprobación explícita del usuario. El flujo exige que cada paso del plan ETL (propuesto por reglas deterministas o por IA) sea revisado y aprobado/rechazado antes de la ejecución.

### 3.2 IA Determinista Supervisada

La IA (Google Gemini o el proveedor Mock) **solo propone** transformaciones. Las operaciones reales se ejecutan a través de un motor ETL determinista en Python/Pandas, utilizando únicamente un catálogo cerrado de transformaciones registradas en `TransformationRegistry`.

### 3.3 Trazabilidad y Auditoría

Cada ejecución ETL produce:
- **Audit logs** detallados por paso (celdas modificadas, validación de parámetros).
- **Hashes MD5** de entrada y salida.
- **Script Python reproducible** standalone generado automáticamente.

### 3.4 Privacidad / RGPD / BYOK

Las muestras enviadas al LLM son **anonimizadas** para nombres, emails y teléfonos. El dataset completo nunca sale del servidor. La API Key de Gemini puede ser propietaria del usuario final (BYOK - Bring Your Own Key), configurada en el navegador o mediante header HTTP.

### 3.5 Gestión de Estado Efímero

En el MVP, toda la sesión de trabajo se mantiene en cachés en memoria y ficheros temporales. Si el backend se reinicia, los planes y ejecuciones se pierden; el sistema detecta esta situación y devuelve 404 en lugar de operar sobre datos arbitrarios (gobierno de integridad del plan).

---

## 4. Estructura del Repositorio

```
migueljerico/dataflow-ai/
├── .github/workflows/ci.yml          # Pipeline CI (backend tests + frontend build)
├── docker-compose.yml                # Orquestación local multi-servicio
├── Dockerfile                        # Contenedor unificado para Cloud Run
├── LICENSE                           # Licencia MIT
├── README.md                         # Documentación funcional del producto
├── data_samples/                     # Datasets de demostración corruptos
│   ├── contact_center_corrupted.csv
│   ├── people_analytics_corrupted.csv
│   └── sales_sample_corrupted.csv
├── backend/
│   ├── Dockerfile                    # Imagen standalone del backend
│   ├── pytest.ini                    # Configuración de Pytest
│   ├── requirements.txt              # Dependencias Python
│   ├── uploads/.gitkeep              # Carpeta temporal de subidas
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # Punto de entrada FastAPI + SPA static
│   │   ├── core/
│   │   │   ├── config.py             # Settings de la aplicación
│   │   │   ├── exceptions.py         # Excepciones funcionales y manejadores
│   │   │   └── number_parsing.py     # Parseo centralizado de números EU/US
│   │   ├── ai_providers/
│   │   │   ├── base.py               # Interfaces abstractas LLMProvider
│   │   │   ├── gemini_provider.py    # Implementación Google Gemini
│   │   │   └── mock_provider.py      # Proveedor local determinista
│   │   ├── api/v1/
│   │   │   ├── router.py             # Agregador de endpoints /api/v1
│   │   │   └── endpoints/
│   │   │       ├── datasets.py       # Upload, samples, metadata
│   │   │       ├── profiling.py      # Informe de profiling
│   │   │       ├── quality.py        # Análisis de calidad
│   │   │       ├── plans.py          # Generación y aprobación de planes
│   │   │       ├── runs.py           # Resultados, descarga, script
│   │   │       └── analytics.py      # Business Analytics
│   │   ├── models/
│   │   │   ├── dataset.py            # Modelos DatasetMetadata, enums
│   │   │   ├── profiling.py          # Modelos de profiling
│   │   │   ├── quality.py            # Modelos de calidad
│   │   │   ├── etl.py                # Modelos de plan/ejecución
│   │   │   └── analytics.py          # Modelos de analytics
│   │   ├── services/
│   │   │   ├── dataset_service.py    # Carga, validación, limpieza de filas
│   │   │   ├── profiler_service.py   # Profiling y detección semántica
│   │   │   ├── quality_service.py    # Evaluación de 5 dimensiones
│   │   │   ├── etl_service.py        # Generación y ejecución de planes
│   │   │   ├── ai_service.py         # Orquestación del Copiloto IA
│   │   │   ├── analytics_service.py  # KPIs ejecutivos por dominio
│   │   │   └── script_generator.py   # Generación de código .py reproducible
│   │   └── transformations/
│   │       ├── base.py               # Clase abstracta BaseTransformation
│   │       ├── registry.py           # Registro central de operaciones
│   │       ├── text_ops.py           # trim_text, normalize_case, etc.
│   │       ├── datetime_ops.py       # convert_datetime
│   │       ├── numeric_ops.py        # convert_numeric, round, clamp
│   │       └── missing_ops.py        # fill_missing, dedup, rename, drop
│   └── tests/                        # Suite de pruebas Pytest
│       ├── conftest.py               # Fixtures de aislamiento
│       ├── test_ai_privacy.py
│       ├── test_ai_provider.py
│       ├── test_analytics.py
│       ├── test_dataset_upload.py
│       ├── test_etl.py
│       ├── test_european_numbers.py
│       ├── test_plan_governance.py
│       ├── test_profiler.py
│       └── test_quality.py
└── frontend/
    ├── Dockerfile                    # Imagen Nginx para frontend
    ├── nginx.conf                    # Proxy inverso para docker-compose
    ├── package.json                  # Dependencias npm
    ├── tsconfig.json                 # Configuración TypeScript
    ├── vite.config.ts                # Proxy de desarrollo a backend
    ├── index.html                    # Punto de entrada SPA
    └── src/
        ├── main.tsx                  # Bootstrap React
        ├── App.tsx                   # Máquina de estados de la sesión
        ├── index.css                 # Tema y estilos globales
        ├── services/api.ts           # Cliente HTTP a /api/v1
        ├── types/index.ts            # Tipos TypeScript de la API
        └── components/
            ├── Header.tsx
            ├── FileUpload.tsx
            ├── ProfilingDashboard.tsx
            ├── PlanReview.tsx
            ├── ExecutionReport.tsx
            ├── BusinessInsights.tsx
            └── ApiKeyModal.tsx
```

---

## 5. Módulos y Componentes del Backend

### 5.1 Capa Core (`backend/app/core/`)

| Archivo | Responsabilidad | Funciones/Claves Exportadas |
| :--- | :--- | :--- |
| `config.py` | Configuración central de la aplicación, rutas de almacenamiento, CORS, límites de ficheros. | `Settings` (PROJECT_NAME, VERSION, UPLOAD_DIR, MAX_FILE_SIZE_BYTES, ALLOWED_EXTENSIONS, BACKEND_CORS_ORIGINS), instancia global `settings` |
| `exceptions.py` | Define la excepción funcional de negocio y los manejadores globales que impiden exponer trazas técnicas crudas. | `FunctionalException`, `functional_exception_handler`, `global_exception_handler` |
| `number_parsing.py` | Parseo numérico centralizado con soporte de separadores europeos (1.234,56) y americanos (1,234.56), limpieza de símbolos y marcadores de ausencia. | `parse_numeric_string(value)`, `to_numeric_series(series)`, `MISSING_MARKERS` |

### 5.2 Modelos Pydantic (`backend/app/models/`)

| Archivo | Responsabilidad | Modelos |
| :--- | :--- | :--- |
| `dataset.py` | Metadatos de dataset y estados del pipeline. | `DatasetMetadata`, `FileTypeEnum`, `ProcessingStateEnum`, `ErrorResponse` |
| `profiling.py` | Informe de profiling y perfiles de columna. | `ProfilingReport`, `ColumnProfile`, `ColumnTypeEnum`, `SemanticHintEnum` |
| `quality.py` | Calidad de datos y desglose por dimensiones. | `QualityReport`, `QualityScore`, `QualityIssue`, `DimensionBreakdown`, `QualityDimensionEnum`, `SeverityEnum` |
| `etl.py` | Planes de transformación y resultados de ejecución. | `TransformationPlan`, `TransformationStep`, `StepStatusEnum`, `ExecutionResult`, `utc_now()` |
| `analytics.py` | Reporte ejecutivo de KPIs de negocio. | `ExecutiveAnalyticsReport`, `BusinessKPI`, `CategoryDistribution` |

### 5.3 Servicios (`backend/app/services/`)

| Archivo | Responsabilidad | Funciones/Claves Exportadas |
| :--- | :--- | :--- |
| `dataset_service.py` | Carga y validación de ficheros CSV/XLSX, detección de delimitadores, limpieza de filas vacías, gestión de metadatos. | `DatasetService.process_uploaded_file()`, `_detect_csv_delimiter()`, `_clean_empty_rows()`, `load_dataframe()`, `get_dataset_metadata()`, `DATASET_CACHE`, `EMPTY_ROWS_PURGED_CACHE` |
| `profiler_service.py` | Profiling automático: inferencia de tipos, detección semántica (email, moneda, fecha, teléfono, etc.), estadísticas por columna, detección de duplicados. | `ProfilerService.get_profiling_report()`, `_detect_semantic_hint()`, `PROFILING_CACHE`, `_safe_float()` |
| `quality_service.py` | Evaluación de calidad en 5 dimensiones (completitud, validez, consistencia, unicidad, integridad) y generación del Quality Score 0-100. | `QualityService.analyze_quality()`, `get_quality_report()`, `QUALITY_CACHE`, `_safe_evidence_sample()` |
| `etl_service.py` | Generación de planes ETL desde reglas deterministas, ejecución del plan aprobado, validación de cada paso, auditoría, generación de ficheros limpios y scripts. | `ETLService.propose_plan_from_rules()`, `execute_plan()`, `get_plan()`, `get_run_result()`, `_count_modified_cells()`, `PLANS_CACHE`, `RUNS_CACHE` |
| `ai_service.py` | Orquestación del Copiloto IA: enrutamiento de proveedores, guardrails de operaciones registradas, anonimización de PII. | `AIService.propose_ai_plan()`, `get_provider()`, `anonymize_sample_rows()`, `_mask_scalar()`, `PII_HINT_MASKS` |
| `analytics_service.py` | Cálculo de KPIs de negocio por dominio (Contact Center, Ventas, People Analytics, General) usando pandas sobre el dataset limpio. | `AnalyticsService.generate_report()`, `ANALYTICS_CACHE` |
| `script_generator.py` | Generación de script Python standalone reproducible con pandas puro. | `ScriptGeneratorService.generate_python_script()` |

### 5.4 Proveedores de IA (`backend/app/ai_providers/`)

| Archivo | Responsabilidad | Funciones/Claves Exportadas |
| :--- | :--- | :--- |
| `base.py` | Clases base abstractas y modelos de datos para sugerencias de IA. | `LLMProvider` (ABC), `AIOperationSuggestion`, `AISuggestionResponse` |
| `gemini_provider.py` | Conexión real con Google Gemini (modelo configurable). Prompt restringido al catálogo de operaciones. La API Key viaja en cabecera para evitar exposición en logs. | `GeminiProvider` (provider_name="gemini", DEFAULT_MODEL="gemini-2.5-flash"), `suggest_transformations()` |
| `mock_provider.py` | Proveedor local determinista que infiere sugerencias desde los issues de calidad sin llamadas externas. Útil para testing y demos. | `MockProvider` (provider_name="mock"), `suggest_transformations()` |

### 5.5 Transformaciones (`backend/app/transformations/`)

| Archivo | Responsabilidad | Operaciones |
| :--- | :--- | :--- |
| `base.py` | Clase abstracta que define la interfaz de toda transformación. | `BaseTransformation` (ABC), métodos `validate_parameters()`, `apply()` |
| `registry.py` | Registro central de operaciones permitidas. | `TransformationRegistry.get_transformation()`, `get()`, `list_all()`, `get_catalog_manifest()` |
| `text_ops.py` | Limpieza y normalización de texto. | `TrimTextTransformation` (trim_text), `NormalizeCaseTransformation` (normalize_case), `NormalizeCategoryTransformation` (normalize_category) |
| `datetime_ops.py` | Conversión y estandarización de fechas. | `ConvertDatetimeTransformation` (convert_datetime) |
| `numeric_ops.py` | Conversión, redondeo y acotación numérica. | `ConvertNumericTransformation` (convert_numeric), `RoundNumericTransformation` (round_numeric), `ClampRangeTransformation` (clamp_range) |
| `missing_ops.py` | Imputación de valores y manipulación de filas/columnas. | `FillMissingTransformation` (fill_missing), `RemoveDuplicatesTransformation` (remove_duplicates), `RenameColumnTransformation` (rename_column), `DropColumnTransformation` (drop_column) |
| `outlier_ops.py` | Detección y tratamiento de outliers estadísticos (IQR y Z-Score). | `DetectOutliersIQRTransformation` (detect_outliers_iqr), `DetectOutliersZScoreTransformation` (detect_outliers_zscore) |
| `cluster_ops.py` | Clustering determinista de observaciones en NumPy puro. | `ClusterKMeansTransformation` (cluster_kmeans) |

### 5.6 Endpoints API (`backend/app/api/v1/`)

| Archivo | Responsabilidad |
| :--- | :--- |
| `router.py` | Agregador central de todos los sub-routers bajo el prefijo `/api/v1`. |
| `endpoints/datasets.py` | Upload de ficheros, listado y carga de datasets de demostración, metadata por ID. |
| `endpoints/profiling.py` | Obtención del informe de profiling. |
| `endpoints/quality.py` | Obtención del análisis de calidad. |
| `endpoints/plans.py` | Generación de planes por reglas o IA, aprobación y ejecución. |
| `endpoints/runs.py` | Resultados de ejecución, comparativa de calidad, descarga de dataset limpio y script reproducible. |
| `endpoints/analytics.py` | Business Analytics por run ID. |

---

## 6. Módulos y Componentes del Frontend

### 6.1 Componentes React (`frontend/src/components/`)

| Componente | Responsabilidad |
| :--- | :--- |
| `Header.tsx` | Barra de navegación principal, selector de idiomas, indicadores de estado de API Key Gemini y badges de privacidad. |
| `FlagIcon.tsx` | Renderizado de 13 banderas vectoriales nativas SVG y fallback 🌐. |
| `LanguageSelector.tsx` | Menú desplegable interactivo accesible para seleccionar el idioma de la plataforma. |
| `FileUpload.tsx` | Carga de archivos CSV/XLSX mediante drag-and-drop o selector, listado de datasets demo con un clic. |
| `ProfilingDashboard.tsx` | Visualización del Quality Score global y las 5 dimensiones, badges de métricas. |
| `PlanReview.tsx` | Revisión humana del plan ETL: previsualización interactiva de esquemas de columnas (antes vs. después y visor por paso), aprobar/rechazar pasos individuales, configuración de clusters y ejecución del plan. |
| `ExecutionReport.tsx` | Comparativa antes/después de la ejecución, logs de auditoría, botones de descarga y reinicio. |
| `BusinessInsights.tsx` | Visualización de KPIs ejecutivos de negocio calculados por el backend. |
| `ApiKeyModal.tsx` | Modal para configurar/eliminar la API Key de Google Gemini almacenada en localStorage. |

### 6.2 Otros Archivos Frontend

| Archivo | Responsabilidad |
| :--- | :--- |
| `App.tsx` | Máquina de estados principal (pasos 1-4) y orquestación de llamadas a API. |
| `main.tsx` | Bootstrap de React 18 (StrictMode). |
| `services/api.ts` | Cliente HTTP tipado con manejo central de errores para todos los endpoints. |
| `types/index.ts` | Tipos TypeScript que reflejan los modelos Pydantic del backend. |
| `vite.config.ts` | Configuración de Vite con proxy `/api` al backend en desarrollo. |
| `index.css` | Tema visual oscuro, variables CSS y estilos globales. |
| `nginx.conf` | Servidor Nginx para producción: SPA + proxy inverso `/api` al backend. |

---

## 7. Catálogo de Transformaciones ETL

Todas las operaciones están registradas en `TransformationRegistry` y son las únicas que el motor puede ejecutar. La IA solo puede proponer operaciones de este catálogo (guardrails).

| Operación | Descripción | Riesgo | Parámetros |
| :--- | :--- | :---: | :--- |
| `trim_text` | Elimina espacios iniciales/finales y dobles espacios internos. | low | `column` |
| `normalize_case` | Normaliza a Title Case (preservando siglas de negocio), Lowercase o Uppercase. | low | `column`, `mode` (title/lower/upper) |
| `normalize_category` | Reemplazo basado en diccionarios de mapeos explícitos (categorías). | low | `column`, `mappings` |
| `convert_datetime` | Convierte cadenas de fecha a ISO 8601 (`%Y-%m-%d`), discriminando formatos ISO y europeos sin traslapes. | medium | `column`, `target_format` |
| `convert_numeric` | Elimina símbolos de moneda/porcentaje y marcadores N/D/N/A, convierte a float64. Soporta separadores EU/US. | medium | `column` |
| `round_numeric` | Redondea una columna numérica a N decimales. | low | `column`, `decimals` |
| `clamp_range` | Acota valores fuera de rango lógico de negocio (ej. negativos a 0, scores > 100 a 100). | medium | `column`, `min_value`, `max_value` |
| `fill_missing` | Imputa valores faltantes por constante, media, mediana o moda. | medium | `column`, `strategy`, `value` |
| `remove_duplicates` | Elimina filas duplicadas exactas o basadas en columnas clave. | high | `subset_columns` (opcional) |
| `rename_column` | Renombra una columna existente. | low | `column`, `new_name` |
| `drop_column` | Elimina una columna no deseada. | low | `column` |
| `detect_outliers_iqr` | Detecta outliers por rango intercuartílico con acciones cap, nullify, drop o flag. | medium | `column`, `multiplier`, `action`, `lower_quantile`, `upper_quantile` |
| `detect_outliers_zscore` | Detecta outliers mediante puntuación Z con acciones cap, nullify, drop o flag. | medium | `column`, `threshold`, `action` |
| `cluster_kmeans` | Segmentación determinista K-Means en k clusters sobre variables normalizadas. | low | `columns`, `n_clusters`, `output_column`, `scale_features` |

---

## 8. Modelo de Calidad de Datos

El **Data Quality Score** (0-100) se calcula mediante una fórmula ponderada explicable:

```text
Quality Score = (0.30 × C) + (0.25 × V) + (0.20 × K) + (0.15 × U) + (0.10 × I)
```

| Dimensión | Ponderación | Descripción |
| :--- | :---: | :--- |
| **Datos Completos (C)** | **30%** | Campos sin valores nulos ni vacíos. |
| **Formatos Válidos (V)** | **25%** | Fechas, números y tipos con formato esperado. |
| **Formato Homogéneo (K)** | **20%** | Espacios sobrantes y variaciones de mayúsculas/minúsculas. |
| **Registros Únicos (U)** | **15%** | Filas y registros duplicados exactos. |
| **Reglas de Negocio (I)** | **10%** | Límites lógicos (ej. Absentismo ≥ 0, Productividad ≤ 100%). |

Cada dimensión genera un `DimensionBreakdown` con score individual, ponderación, cantidad de issues y resumen. El informe incluye la lista completa de `QualityIssue` con severidad, columna afectada, filas impactadas, evidencia y acción sugerida.

---

## 9. API de Endpoints

Base URL: `/api/v1`

### 9.1 Datasets

| Método | Ruta | Descripción | Parámetros |
| :--- | :--- | :--- | :--- |
| `POST` | `/datasets/upload` | Sube un fichero CSV o XLSX y crea el dataset. | `file` (multipart, requerido, máx 10 MB) |
| `POST` | `/datasets/from-url` | Descarga e importa un dataset desde una URL pública con protección Anti-SSRF. | Body: `{"url": string}` (máx 20 MB) |
| `GET` | `/datasets/samples` | Lista los datasets de demostración preconfigurados. | — |
| `POST` | `/datasets/samples/{sample_id}/load` | Carga un dataset demo sin subir archivo. | `sample_id` (path): `contact_center` \| `sales` \| `people_analytics` \| `logistics` |
| `GET` | `/datasets/{dataset_id}` | Obtiene los metadatos de un dataset. | `dataset_id` (path) |

### 9.2 Profiling

| Método | Ruta | Descripción | Parámetros |
| :--- | :--- | :--- | :--- |
| `GET` | `/datasets/{dataset_id}/profiling` | Genera/obtiene el informe de profiling del dataset. | `dataset_id` (path) |

### 9.3 Quality

| Método | Ruta | Descripción | Parámetros |
| :--- | :--- | :--- | :--- |
| `GET` | `/datasets/{dataset_id}/quality` | Obtiene el análisis de Data Quality con score 0-100. | `dataset_id` (path) |

### 9.4 Plans

| Método | Ruta | Descripción | Parámetros |
| :--- | :--- | :--- | :--- |
| `POST` | `/plans/propose` | Genera plan ETL desde reglas deterministas. | Body: `{"dataset_id": string}` |
| `POST` | `/plans/propose/ai` | Genera plan ETL asistido por IA (Gemini/Mock) con guardrails. | Body: `{"dataset_id": string, "provider": "mock"\|"gemini", "api_key": optional}`; Header opcional: `X-Gemini-Api-Key` |
| `GET` | `/plans/{plan_id}` | Obtiene un plan por su ID. | `plan_id` (path) |
| `POST` | `/plans/{plan_id}/approve` | Aprueba y ejecuta el plan ETL revisado. | `plan_id` (path); Body: `{"steps": TransformationStep[]}` |

### 9.5 Runs

| Método | Ruta | Descripción | Parámetros |
| :--- | :--- | :--- | :--- |
| `GET` | `/runs/{run_id}` | Obtiene el resumen de la ejecución. | `run_id` (path) |
| `GET` | `/runs/{run_id}/report` | Comparativa de calidad antes vs después. | `run_id` (path) |
| `GET` | `/runs/{run_id}/download` | Descarga el dataset limpio resultante. | `run_id` (path) |
| `GET` | `/runs/{run_id}/script` | Descarga el script Python reproducible. | `run_id` (path) |
| `GET` | `/runs/{run_id}/download-script` | Alias del anterior para compatibilidad. | `run_id` (path) |

### 9.6 Analytics

| Método | Ruta | Descripción | Parámetros |
| :--- | :--- | :--- | :--- |
| `GET` | `/analytics/{run_id}` | Obtiene el reporte ejecutivo de Business Analytics y KPIs. | `run_id` (path) |

### 9.7 Health

| Método | Ruta | Descripción | Parámetros |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Healthcheck del servicio (para Cloud Run). | — |

### 9.8 Códigos de Error Comunes

| Código | Descripción | HTTP Status |
| :--- | :--- | :---: |
| `INVALID_FILE_TYPE` | Formato de fichero no permitido. | 400 |
| `EMPTY_FILE` | Fichero vacío (0 bytes o sin datos). | 400 |
| `FILE_TOO_LARGE` | El fichero supera el límite configurado (10 MB upload / 20 MB URL). | 400 |
| `SSRF_BLOCKED_IP` | Acceso bloqueado: la IP destino es privada, loopback o metadatos Cloud. | 400 |
| `INVALID_URL_SCHEME` | Esquema de URL prohibido (solo se admite http/https). | 400 |
| `DOWNLOAD_TIMEOUT` | Tiempo de espera agotado al descargar archivo remoto. | 408 |
| `INVALID_COLUMN` | Columna inexistente en la transformación. | 400 |
| `UNREGISTERED_OPERATION` | Operación no contemplada en el catálogo. | 400 |
| `AI_API_KEY_MISSING` | Falta la API Key de Gemini. | 400 |
| `AI_PROVIDER_ERROR` | Error de comunicación con el proveedor de IA. | 400 |
| `PLAN_NOT_FOUND` | Plan inexistente o perdido tras reinicio. | 404 |
| `SAMPLE_NOT_FOUND` | Dataset demo inexistente. | 404 |
| `SAMPLE_FILE_MISSING` | Archivo demo no disponible en servidor. | 404 |
| `CLEAN_FILE_NOT_FOUND` | Archivo limpio no disponible. | 404 |
| `FILE_NOT_FOUND` | Fichero subido no encontrado en disco. | 404 |

---

## 10. Variables de Entorno

| Variable | Requerida | Valor por defecto | Descripción |
| :--- | :---: | :--- | :--- |
| `PORT` | Cloud Run lo inyecta | `8080` | Puerto HTTP en el que escucha Uvicorn. |
| `PROJECT_NAME` | No | `DataFlow AI` | Nombre de la aplicación en FastAPI y metadatos. |
| `VERSION` | No | `1.4.0` | Versión semántica actual del backend. |
| `API_V1_STR` | No | `/api/v1` | Prefijo base para la API REST. |
| `MAX_FILE_SIZE_BYTES` | No | `10485760` (10 MB) | Límite máximo de tamaño para subida directa de datasets. |
| `MAX_URL_FILE_SIZE_BYTES` | No | `20971520` (20 MB) | Límite máximo de tamaño para importación desde URL. |
| `STORAGE_BACKEND` | No | `local` | Backend de almacenamiento: `local` (tmpfs/disco), `gcs` (Google Cloud Storage) o `s3` (AWS S3 / MinIO / R2). |
| `STORAGE_BUCKET_NAME` | Requerido para GCS/S3 | `""` | Nombre del bucket en Google Cloud Storage o AWS S3. |
| `STORAGE_GCS_PROJECT` | Opcional | `None` | ID de proyecto GCP para autenticación de Google Cloud Storage. |
| `STORAGE_S3_ENDPOINT_URL` | Opcional | `None` | Endpoint personalizado para S3 (MinIO, Cloudflare R2, LocalStack). |
| `STORAGE_S3_REGION_NAME` | No | `us-east-1` | Región AWS para el cliente S3. |
| `STORAGE_S3_ACCESS_KEY_ID` | Opcional | `None` | Access Key ID para S3 (si no se usan roles IAM). |
| `STORAGE_S3_SECRET_ACCESS_KEY` | Opcional | `None` | Secret Access Key para S3 (si no se usan roles IAM). |
| `STORAGE_PREFIX` | No | `dataflow/` | Prefijo de ruta de los objetos dentro del bucket. |
| `BACKEND_CORS_ORIGINS` | No | `["http://localhost:3000", ...]` | Lista separada por comas de orígenes autorizados para CORS. |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Modelo de Google Gemini utilizado para sugerencias IA. |
| `GEMINI_API_KEY` | Opcional | `None` | Clave API global de Gemini. En producción se prioriza el modo **BYOK** (cabecera HTTP enviada por el usuario). |

---

## 11. Guía de Despliegue

### 11.1 Despliegue en Google Cloud Run (Producción)

DataFlow AI está desplegado en **Google Cloud Run** en la región **`us-central1`** (Iowa) para mitigar restricciones geográficas europeas de la API de Gemini y garantizar acceso público de baja latencia.

* **URL de Producción**: [https://dataflow-ai-748914382449.us-central1.run.app](https://dataflow-ai-748914382449.us-central1.run.app)
* **Arquitectura de Contenedor Único**: El `Dockerfile` multi-stage construye la SPA de React en el Stage 1 (`node:20-alpine`) y la copia a `/app/static` en el Stage 2 (`python:3.11-slim`), donde FastAPI sirve tanto la API `/api/v1` como la interfaz estática.
* **Escalado a Cero (Coste 0 € en reposo)**: `min_instances=0` apaga los contenedores cuando no hay tráfico activo.
* **Despliegue Continuo (CD)**: Conectado mediante un **Activador de Cloud Build** que compila y publica una nueva revisión en cada `push` a la rama `main`.

### 11.2 Despliegue Manual con Google Cloud SDK

```bash
gcloud run deploy dataflow-ai \
  --source . \
  --project proyecto-app-antigravity \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated
```

### 11.3 Ejecución con Docker Compose (Local)

```bash
docker compose up --build
```

Levanta el servicio backend en el puerto `8000` y el frontend en Nginx en el puerto `3000` con proxy inverso hacia `/api`.

---

## 12. Pipeline de Integración Continua (CI)

El archivo `.github/workflows/ci.yml` ejecuta en cada `push` y `pull_request` a `main`:

1. **Job `test-backend`**:
   - Entorno: Ubuntu Latest + Python 3.11
   - Instalación de dependencias: `pip install -r requirements.txt`
   - Ejecución de suite completa: `pytest --tb=short -q` (23 tests).
2. **Job `build-frontend`**:
   - Entorno: Ubuntu Latest + Node.js 20
   - Chequeo estático de tipos: `npx tsc --noEmit`
   - Compilación del bundle de producción: `npm run build`

---

## 13. Suite de Pruebas

Ubicación: `backend/tests/`

| Fichero | Tests | Objetivo |
| :--- | :---: | :--- |
| `test_dataset_upload.py` | 7 | Validación de formatos (`.csv`, `.xlsx`), límites de tamaño, detección de delimitador y dataset vacío. |
| `test_dataset_from_url.py` | 8 | Ingesta remota por URL, validación de tamaños, streams defensivos y manejo de errores HTTP. |
| `test_security_url.py` | 40 | Protección exhaustiva Anti-SSRF (IPv4/IPv6/Metadata GCP), mitigación de DNS Rebinding mediante IP Pinning, no credenciales embebidas y validación de esquemas. |
| `test_security_url_ssrf_regression.py` | 8 | Batería de regresión automatizada que reproduce las 7 pruebas de penetración reales ejecutadas contra producción (Cloud Run) + caso de control. |
| `test_opendata.py` | 5 | Explorador de datos abiertos (catálogo curado, búsqueda en tiempo real e integración con API CKAN). |
| `test_phase4_guardrails.py` | 6 | Detección estadística con `charset-normalizer`, soporte de BOM, Windows-1252 y prioridad semántica de IDs/códigos sobre fechas/divisas. |
| `test_profiler.py` | 1 | Inferencia de tipos y sugerencias semánticas automáticas. |
| `test_quality.py` | 1 | Cálculo del Data Quality Score (0-100) en sus 5 dimensiones. |
| `test_european_numbers.py` | 3 | Parseo unificado de importes con coma decimal, moneda (`€`, `$`) y porcentajes. |
| `test_ai_privacy.py` | 3 | Enmascaramiento estricto de PII (`[NOMBRE]`, `[EMAIL]`, `[TELÉFONO]`) en muestras enviadas a la IA. |
| `test_plan_governance.py` | 2 | Gobierno estricto: rechazo de planes inexistentes (`404`) y ejecución únicamente de pasos aprobados. |
| `test_ai_provider.py` | 1 | Generación de sugerencias IA y guardrails de catálogo. |
| `test_etl.py` | 3 | Ejecución del motor determinista sobre transformaciones individuales y pipelines combinados. |
| `test_analytics.py` | 4 | Cálculo de KPIs ejecutivos, clusters 2D, boxplots y exportación de reportes ejecutivos en HTML5. |
| `test_parquet_export.py` | 2 | Exportación columnar nativa a Apache Parquet, validación de magic bytes PAR1 y descarga REST. |
| `test_dataset4_verification.py` | 6 | Verificación de marcadores de ausencia, preservación de mayúsculas en identificadores y no corrupción de conteos. |
| `test_copilot_metrics.py` | 3 | Métricas de inferencia y observabilidad del Copiloto IA (latencia, tokens consumidos, coste USD). |
| `test_outliers_scatter_diff.py` | 2 | Comparador de dispersión (Scatter Diff) de outliers entre dataset crudo y dataset limpio con trazabilidad de anomalías. |

**Total:** 151 tests backend (Pytest) + 38 tests frontend (Vitest) + 3 suites E2E (Playwright) — 100% pasando en verde.

---

## 14. Consideraciones de Seguridad y Privacidad

1. **BYOK (Bring Your Own Key)**: Las claves de API de Google Gemini se almacenan exclusivamente en el `localStorage` del navegador del cliente y se envían por cabecera HTTP efímera `x-goog-api-key`.
2. **Privacidad RGPD**: Nunca se envía el dataset completo a modelos externos. Únicamente se transfieren resúmenes estadísticos y 3 filas de muestra con datos sensibles enmascarados.
3. **Guardrails de Ejecución**: La IA no tiene capacidad de ejecución de código; sus propuestas se validan contra un catálogo cerrado de operaciones (`TransformationRegistry`).
4. **CORS Restrictivo**: En producción no se utilizan comodines (`*`) con credenciales activas.

---

## 15. Limitaciones Conocidas

- **Almacenamiento Volátil en Cloud Run**: Los datasets temporales subidos se almacenan en el sistema de archivos efímero del contenedor; si la instancia escala a cero, los archivos antiguos expiran (comportamiento esperado por privacidad).
- **Límite de Tamaño**: Tamaño máximo fijado en 10 MB por archivo en la versión piloto.
- **Concurrencia de Planes**: Los planes en memoria se gestionan efímeramente por sesión.

---

## 16. Mejoras Futuras

- [ ] Exportación directa a modelos semánticos de Power BI (Power BI REST API / `.pbix`).
- [ ] Conectores directos a bases de datos SQL (PostgreSQL, Snowflake, BigQuery).
- [ ] Persistencia de pipelines en base de datos PostgreSQL con autenticación de usuarios.
- [ ] Programación periódica de pipelines ETL (Cron Jobs / Webhooks).

---

<p align="center">Creado por <a href="https://github.com/migueljerico">@migueljerico</a> · Documentado por QwenCloud (deepseek-v4-pro-0813) y mejorado por <strong>Muse Spark 1.2 Contributor</strong> (27-08-2026) · Sin cambios en el disparador de Google Cloud Build</p>