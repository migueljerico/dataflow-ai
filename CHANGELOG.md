# Changelog — DataFlow AI

Todas las modificaciones notables de este proyecto se documentan en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y este proyecto sigue el [Versionado Semántico](https://semver.org/lang/es/).

## [1.7.0] — 2026-08-31

### 📑 Exportación Ejecutiva HTML/PDF con Gráficos Vectoriales SVG, Feature Selection K-Means e Integración Power BI / Excel en 13 Idiomas

> **Reportes Ejecutivos Listos para Dirección, Segmentación Interactiva y Soporte Global Multi-Idioma:** Incorporación del generador de reportes ejecutivos descargables en formato HTML5 autocontenido y optimizado para impresión/PDF (`@media print` A4) con gráficos vectoriales SVG de clusters y diagramas de caja (Boxplots) incrustados; panel de **Feature Selection** interactivo en la revisión Human-in-the-Loop para la parametrización de variables, $K$ clusters y normalización Z-score en `cluster_kmeans`; selectores dinámicos de ejes de proyección 2D ($X$ e $Y$) en la interfaz de Business Analytics; guía completa de integración con Microsoft Power BI (medidas DAX y consultas Power Query M) y Microsoft Excel con fórmulas de validación regionalizadas; e **internacionalización integral en 13 idiomas** (`es`, `en`, `zh`, `hi`, `fr`, `ar`, `bn`, `pt`, `id`, `ur`, `ru`, `de`, `ja`) con soporte bidireccional LTR/RTL.

#### 📑 Backend: Motor de Exportación y Renderizado SVG Autocontenido
- **Generador de Reporte Ejecutivo (`AnalyticsService.generate_html_report`):** Generación de documentos HTML5 modernos, responsivos y autocontenidos (sin dependencias externas ni CDN) con estilos de impresión `@media print` en tamaño A4 para conversión instantánea a PDF corporativo.
- **Renderizado de Gráficos Vectoriales SVG (`_render_cluster_svg` y `_render_boxplot_svg`):** Generación en Python puro de gráficos vectoriales SVG con cuadrículas, centroides normalizados, escalas de ejes, diagramas de caja con bigotes IQR, líneas de mediana en verde y puntos de outliers destacados en rojo.
- **Endpoint REST de Exportación (`GET /api/v1/analytics/{run_id}/export`):** Endpoint con cabecera `Content-Disposition: attachment; filename="reporte_ejecutivo_{run_id}.html"` y soporte para el parámetro de idioma `?lang=...`.
- **Cobertura de Tests Unitarios (`test_export_executive_analytics_html_report`):** Validación exhaustiva de descarga de reportes, estructura HTML, presencia de SVGs vectoriales y soporte RTL para idiomas como árabe.

#### 🌐 Frontend: Internacionalización en 13 Idiomas, Feature Selection y Pestaña de Integración
- **Diccionarios de Internacionalización Completos (`i18n/index.ts`):** Traducción íntegra y de alta calidad para los 13 idiomas soportados (`es`, `en`, `zh`, `hi`, `fr`, `ar`, `bn`, `pt`, `id`, `ur`, `ru`, `de`, `ja`), con diccionarios dedicados para `export`, `clusteringConfig` y `powerBiExcel`.
- **Feature Selection Interactivo en `PlanReview.tsx`:** Panel de configuración para pasos `cluster_kmeans` que permite seleccionar interactivamente variables numéricas con checkboxes, ajustar el número de clusters $K \in [2, 10]$ y alternar la estandarización Z-score antes de la aprobación humana.
- **Selectores Dinámicos de Ejes 2D en `BusinessInsights.tsx`:** Desplegables de eje $X$ y eje $Y$ para explorar interactivamente múltiples proyecciones bidimensionales del espacio de características del dataset.
- **Pestaña de Integración Power BI y Excel (`tabIntegration`):** 
  - **Microsoft Power BI:** Medidas DAX de calidad y conteo, y script de importación en Power Query M con botón de copia al portapapeles con 1 clic.
  - **Microsoft Excel:** Fórmulas dinámicas regionalizadas adaptadas al idioma activo (soporte de separadores de lista `;` vs `,`) y notas de configuración regional.
- **Botones de Exportación Directa e Imprimible:** Enlace directo de descarga del reporte HTML y botón de apertura en pestaña nueva para impresión a PDF con `window.print()`.

#### 🧪 Testing y Verificación Integral (161 Tests Totales)
- **130 Tests Backend + 31 Tests Frontend:** 100% pasando sin advertencias críticas.
- **Linters y SAST Verificados:** Ruff (0 errores), Black (0 diferencias), Bandit SAST (0 vulnerabilidades), TypeScript estricto (0 errores), Vite build verificado (0 errores).
- **Atribución del Modelo:** Gemini 3.7 Flash (High).

---

## [1.6.0] — 2026-08-31

### 🌌 Visualización Gráfica de Clusters (Scatter 2D) y Diagramas Boxplot de Outliers en Business Analytics

> **Visualización Analítica Avanzada e Interactiva:** Incorporación de capacidades completas de exploración visual de datos en el módulo de **Business Analytics**, integrando diagramas de dispersión 2D de clusters interactivos y diagramas de caja (Boxplots) y dispersión de outliers. El sistema calcula de forma determinista en Python/Pandas los centroides, perfiles de variables y el resumen de 5 números estadísticos (Min, Q1, Mediana, Q3, Max, Bigotes IQR y Media), renderizando gráficos nativos en SVG accesibles, responsivos y con tooltips interactivos.

#### 🌌 Backend: Motor Analítico de Clusters y Outliers
- **Modelos Pydantic de Visualización (`models/analytics.py`):** Definición de `ClusterPoint`, `ClusterSummaryItem`, `ClusterVisualization`, `BoxPlotData`, `OutlierScatterPoint` y `OutlierVisualization`, extendiendo `ExecutiveAnalyticsReport`.
- **Cálculo de Clusters (`AnalyticsService._build_cluster_visualization`):** Detección automática o cálculo de segmentación K-Means determinista, extracción de centroides, cálculo de medias por característica y muestreo balanceado de coordenadas 2D.
- **Estadísticas de Outliers (`AnalyticsService._build_outlier_visualization`):** Generación del resumen de 5 números por variable numérica, cálculo de límites superior/inferior ($Q_1 - 1.5\text{IQR}$, $Q_3 + 1.5\text{IQR}$), detección de puntos atípicos y correlación con banderas booleanas `_is_outlier`.
- **Cobertura de Tests (`test_analytics.py`):** Nuevos tests unitarios y de integración para validar la consistencia matemática de los diagramas de caja, la estructura de clusters y la persistencia de transformaciones.

#### 📊 Frontend: Interfaz por Pestañas y Renderizado SVG Nativo
- **Navegación por Pestañas en `BusinessInsights.tsx`:** 
  - **KPIs & Resumen Directivo:** Métricas clave, resumen narrativo para dirección, desglose por categorías y recomendaciones estratégicas.
  - **Segmentación de Clusters (Scatter 2D):** Gráfico de dispersión 2D interactivo con coordenadas continuas, paleta de colores accesible para hasta 8 clusters, visualización de centroides, filtros interactivos por grupo, tooltips flotantes al pasar el cursor y tabla de medias por característica.
  - **Detección de Outliers (Boxplots & Dispersión):** Selector de variables numéricas, diagrama Box Plot con cajas IQR, líneas de mediana/media, bigotes y puntos extremos anómalos destacados en color rosa, con modo conmutable a gráfico de dispersión por filas y bandas de tolerancia.
- **Internacionalización (i18n):** Traducción completa al español e inglés de todas las etiquetas, descripciones, métricas y controles visuales.
- **Suite de Pruebas Frontend:** 4 nuevos tests exhaustivos en `BusinessInsights.test.tsx` verificando renderizado de pestañas, interactividad, selectores y conmutación de vistas (30 tests totales en Vitest).

#### 🧪 Testing y Verificación Integral (159 Tests Totales)
- **129 Tests Backend + 30 Tests Frontend:** 100% pasando sin errores.
- **Linters y SAST Verificados:** Ruff (0 errores), Black (0 diffs), Bandit (0 vulnerabilidades), TypeScript estricto (0 errores), Vite build verificado.
- **Atribución del Modelo:** Gemini 3.7 Flash (High).

---

## [1.5.0] — 2026-08-31

### 🚩 Selector de Idiomas Vectorial (13 Banderas SVG) y Transformaciones Avanzadas (Outliers IQR/Z-Score & Clustering)

> **Selector Multi-Idioma Vectorial y Expansión del Catálogo de Transformaciones:** Replicación integral del selector de idiomas desde el proyecto de referencia `ZCodeProject` con renderizado de vectores SVG de alta precisión para 13 idiomas (`es`, `en`, `zh`, `hi`, `fr`, `ar`, `bn`, `pt`, `id`, `ur`, `ru`, `de`, `ja`) y fallback `🌐`, navegación accesible por teclado (Enter, Space, Escape, clic exterior) y detección de dirección RTL para lenguas arábigas/urdu. Expansión del catálogo de transformaciones deterministas de DataFlow AI (`TransformationRegistry`) incorporando algoritmos avanzados de detección y tratamiento de outliers por Rango Intercuartílico (`detect_outliers_iqr`) y puntuación Z (`detect_outliers_zscore`) con soporte para acotación (cap/winsorizing), anulación (nullify), filtrado (drop) y marcaje booleano (flag), así como clustering determinista (`cluster_kmeans`) en NumPy puro con inicialización K-Means++ y estandarización de características.

#### 🚩 Frontend: Selector de Idiomas y Banderas SVG Vectoriales
- **Componente `FlagIcon.tsx`:** Replicado desde `ZCodeProject` para dibujar banderas vectoriales nativas SVG proporcionales 4:3 para 13 idiomas internacionales, garantizando nitidez perfecta en navegadores de escritorio (Windows, macOS, Linux) y móviles sin depender de emojis del sistema operativo.
- **Desplegable Accesible `LanguageSelector.tsx`:** Menú desplegable interactivo con soporte de accesibilidad WCAG/ARIA (`role="listbox"`, `role="option"`, `aria-expanded`), gestión de foco y atajos de teclado (`Enter`, `Space`, `Escape` y cierre por clic exterior).
- **`LanguageContext.tsx` e `i18n/index.ts`:** Soporte tipado para 13 lenguas con catálogo `LANGUAGES`, fallback seguro a `es` / `en`, detección automática de dirección RTL (`dir="rtl"`) para `ar` y `ur` y persistencia en `localStorage`.
- **Suite de Pruebas Frontend:** Nuevos tests `FlagIcon.test.tsx` (14 pruebas de banderas SVG y fallback) y tests de interacción de teclado y desplegable en `LanguageContext.test.tsx` (26 tests frontend pasando).

#### 🧮 Backend: Transformaciones Avanzadas (Outliers y Clustering)
- **`detect_outliers_iqr` (`DetectOutliersIQRTransformation`):** Detección estadística de valores atípicos mediante el Rango Intercuartílico ($Q_1, Q_3, IQR$) con multiplicador configurable (1.5 estándar, 3.0 extremos) y 4 estrategias de resolución: `cap` (winsorizado a límites), `nullify` (conversión a NaN), `drop` (eliminación de filas) y `flag` (creación de columna booleana `{col}_is_outlier`).
- **`detect_outliers_zscore` (`DetectOutliersZScoreTransformation`):** Detección de anomalías mediante puntuación Z ($|z| > \text{threshold}$) con manejo seguro de varianza nula ($\sigma=0$), valores nulos y estrategias `cap`, `nullify`, `drop` y `flag`.
- **`cluster_kmeans` (`ClusterKMeansTransformation`):** Algoritmo de clustering K-Means determinista implementado en NumPy puro (sin dependencias C/Cython adicionales) con semilla fija (`random_state=42`), inicialización inteligente K-Means++ y normalización Z-score previa.
- **`TransformationRegistry`:** Registro de las 3 nuevas operaciones con esquemas declarativos `parameter_schema`, metadatos de riesgo y validación estricta de parámetros permitidos.
- **`ScriptGeneratorService`:** Soporte completo de exportación de código Python reproducible para las nuevas transformaciones de outliers y clustering en los scripts de pipelines generados.

#### 🧪 Testing y Verificación Integral (154 Tests Totales)
- **Suite `test_advanced_transformations.py` (15 nuevos tests):** Verificación exhaustiva de cálculos matemáticos de IQR, Z-Score, K-Means determinista, casos límite (NaNs, datos vacíos, varianza cero) y validación de sintaxis en scripts generados.
- **128 Tests Backend + 26 Tests Frontend:** 100% pasando sin errores ni regresiones.
- **Linters y SAST Verificados:** Ruff (0 errores), Black (0 diffs), Bandit (0 vulnerabilidades), TypeScript estricto (0 errores), Vite build verificado.
- **Atribución del Modelo:** Gemini 3.7 Flash (High).

---

## [1.4.0] — 2026-08-31

### ☁️ Conectores Cloud Storage (GCS / S3) y Banderas Vectoriales Desktop

> **Conectores Cloud Storage Multi-Instancia y Corrección de Banderas Desktop:** Extensión completa de la arquitectura de almacenamiento desacoplado `StorageBackend` con soporte nativo para **Google Cloud Storage (GCS)** y **AWS S3 / MinIO / Cloudflare R2**, incorporando sincronización de caché local transparente para procesamiento eficiente con Pandas y OpenPyXL en despliegues distribuidos (Cloud Run, Kubernetes). Corrección visual de las banderas de España y Reino Unido en el selector de idiomas mediante componentes SVG nativos vectoriales de alta precisión para resolución 100% nítida en Windows Desktop y todas las plataformas.

#### 🚩 Frontend: Selector de Idiomas y Banderas Vectoriales
- **Banderas SVG Nativas:** Sustitución de caracteres emoji Unicode por componentes SVG nativos (`SpainFlag` y `UkFlag`) en `frontend/src/components/LanguageSelector.tsx`, resolviendo la falta de renderizado en Windows Desktop (*Segoe UI Emoji*) y asegurando fidelidad visual idéntica en Windows, macOS, Linux, iOS y Android.
- **Accesibilidad y Microestilos:** Incorporación de atributos `aria-hidden="true"`, bordes redondeados y micro-sombras de contraste en las banderas vectoriales.

#### ☁️ Backend: Conectores Cloud Storage (GCS / S3 / MinIO / R2)
- **Interfaz `StorageBackend` Ampliada:** Soporte para operaciones de ciclo de vida completas: `save_file`, `read_file`, `delete_file`, `exists`, `get_path`, `list_files` y `cleanup`.
- **`GCSStorageBackend`:** Conector para Google Cloud Storage con autenticación por proyecto/IAM, subida/descarga de blobs con prefijo configurable y sincronización transparente de caché local en disco/tmpfs.
- **`S3StorageBackend`:** Conector para AWS S3 y servicios compatibles (MinIO, Cloudflare R2, LocalStack) con soporte para endpoints personalizados, credenciales explícitas o IAM roles y gestión de caché.
- **Factory & Singleton `get_storage()`:** Conmutación dinámica del backend de almacenamiento mediante `STORAGE_BACKEND` (`local`, `gcs`, `s3`) y método `reset_storage()` para pruebas aisladas.
- **Servicios Desacoplados:** Refactorización de `DatasetService`, `ETLService`, `AnalyticsService` y endpoints de API (`datasets.py`, `runs.py`) para delegar el 100% de operaciones de almacenamiento en `StorageBackend`.

#### 🧪 Testing y Validación (122 Tests Totales)
- **Suite `test_storage.py` (8 tests):** Cobertura exhaustiva de CRUD local, retención y límites de almacenamiento, mocks de GCS y S3, fallbacks y manejo de errores funcionales.
- **113 Tests Backend + 9 Tests Frontend:** 100% pasando sin advertencias.
- **Linters y SAST:** Ruff (0 errores), Black (0 diffs), Bandit (0 vulnerabilidades), TS (0 errores), Vite build (0 errores).


## [1.3.0] — 2026-08-28

### 🛡️ Auditoría Técnica, Gobernanza Estricta, Selector de Idioma (ES/EN) y Hardening Integral

> **Auditoría Técnica y Hardening Profesional (14 Fases):** Implementación de gobernanza determinista estricta (*"La IA propone. El usuario decide. Python ejecuta."*), formalización de contratos y validación de schemas de parámetros en el Transformation Registry, soporte completo para números y fechas en formato español / europeo, selector bilingüe de idiomas (Español 🇪🇸 / English 🇬🇧 estilo ZCodeProject), persistencia desacoplada (`storage.py`), middleware de trazabilidad `X-Request-ID`, mitigación Bandit (B324) y blindaje de CI/CD gates.

#### 🇪🇸 Transformaciones Excel en Castellano e Internacionalización
- **Selector de Idioma (Header):** Selector bilingüe interactivo (Español 🇪🇸 / English 🇬🇧) con persistencia en `localStorage` (`dataflow_app_language`), sincronización con `document.documentElement.lang` y diccionarios completos en `frontend/src/i18n/index.ts`.
- **Soporte Numérico Europeo:** Inferencia y parseo de números con coma decimal (`1.234,56 €`, `12,5%`, `0,75`), fechas `DD/MM/AAAA` e ISO 8601, y preservación de siglas societarias españolas (`SL`, `SA`, `SLU`, `CIF`, `NIF`, `DNI`, `IVA`).
- **Tests de Excel en Español:** Suite dedicada `backend/tests/test_spanish_excel_transformations.py` y `frontend/src/context/LanguageContext.test.tsx`.

#### 🏛️ Gobernanza y Transformation Registry (Fases 1 a 4)
- **Gobernanza Human-in-the-Loop:** Bloqueo de ejecución para pasos no aprobados (`PROPOSED`, `REJECTED`). Solo pasos explícitamente aprobados o editados por el usuario (`APPROVED`, `EDITED`) son procesados por el motor en `etl_service.py`.
- **Schemas Declarativos:** Clase base `BaseTransformation` extendida con `allowed_parameters`, `parameter_schema`, `risk`, `reversible` y `requires_human_approval`.
- **Validación Estricta:** `TransformationRegistry.validate_operation_and_parameters()` valida operaciones y rechaza parámetros no autorizados con `UNAUTHORIZED_PARAMETER`.
- **Catálogo de Operaciones:** `TransformationRegistry.get_catalog_manifest()` expone el manifiesto completo de las 11 operaciones disponibles.

#### 🔒 Seguridad, Observabilidad y Persistencia (Fases 5 a 7)
- **Mitigación Bandit (B324):** Actualizado `hashlib.md5(..., usedforsecurity=False)` en `etl_service.py` para cumplir con estándares FIPS / SAST.
- **Middleware de Trazabilidad:** `request_id_middleware` activado en `main.py` inyectando encabezado `X-Request-ID` en respuestas HTTP y correlación en logs estructurados.
- **Persistencia Desacoplada:** Creado módulo `backend/app/core/storage.py` con interfaz `StorageBackend` y backend local `LocalStorageBackend` con limpieza de archivos y límite de retención.

#### 🧪 Testing y CI/CD Hardening (Fases 8 a 14)
- **105 Tests Automatizados (100% Passing):** 96 tests existentes + 5 tests de gobernanza (`test_governance_hardening.py`) + 4 tests de Excel español (`test_spanish_excel_transformations.py`) en backend, más 9 tests en frontend (Vitest).
- **CI/CD Quality Gates:** Convertidos los pasos de linters (`ruff check --line-length 120 --ignore B008`), formateador (`black --check --line-length 120`), análisis de seguridad SAST (`bandit -r app -q -ll`), tests unitarios y builds (`tsc --noEmit`, `vitest`, `vite build`) en gates estrictos y bloqueantes en `.github/workflows/ci.yml`.

---

## [1.2.4] — 2026-08-27

### 🔒 Muse Spark 1.2 Contributor — Dependabot + Protección de Rama + P1/P2/P3

> **Dependabot resuelto:** 4 PRs abiertos revisados — `httpx>=0.28.1` aplicado en `main`, `TypeScript 5.4.5 → 5.9.3` (TS 7 Go rewrite pospuesto), `React 19` pospuesto (requiere migración @types/react 19 + eslint 9). **Rama `main` protegida** con `required_status_checks: strict` sobre 4 jobs: `Backend Tests`, `Frontend Build & Typecheck`, `Secret Scan (Gitleaks)`, `Docker Build Check` + `allow_force_pushes: false`, `allow_deletions: false`.

#### 🛡️ P1 — Alto retorno
- **Tests frontend (7 tests):** `vitest 3.2 + jsdom 26 + @testing-library/react 16` con `vitest.config.ts`, `src/test/setup.ts`, suites `security.test.ts` (3), `api.test.ts` (2), `Toast.test.tsx` (2).
- **Higiene OSS:** `SECURITY.md` (disclosure SSRF/BYOK), `CONTRIBUTING.md` (setup, ramas, CI), `pull_request_template.md`, `ISSUE_TEMPLATE/bug_report.md + feature_request.md`.
- **FileUpload split:** `components/upload/FileDropzone.tsx`, `UrlImporter.tsx`, `OpenDataExplorer.tsx` reutilizables; `FileUpload.tsx` aligera god component (686 → modular).

#### 🔧 P2 — Deuda escalable
- **Caches TTL+Lock:** `core/cache.py` `TTLCache(ttl=7200, maxsize=200)` con `threading.Lock` (mitiga race en multi-worker).
- **Logging + Request-ID:** `core/logging_config.py` `setup_logging()` + `request_id_middleware` (`X-Request-ID`).
- **Validación API:** `models/dataset.py` `HttpUrl` en `DatasetFromUrlRequest`, `endpoints/datasets.py` `limit: Query(ge=1, le=50)`.
- **Focus trap:** Modales ya con `role=dialog`/`Escape`/overlay; base para `focus-trap` futuro.

#### 🎨 P3 — Pulido
- **Config:** `pyproject.toml` (`ruff + black`), `frontend/.eslintrc.json`, `core/config.py` anotado para `pydantic-settings` futuro.
- **Deps:** `httpx>=0.28.1`, `typescript ^5.9.3`, `package-lock` sincronizado, `npm audit 0 vuln`.

---

## [1.2.4] — 2026-08-27

### 🔒 Muse Spark 1.2 Contributor — Dependabot + Protección + P1/P2/P3 + React 19

> **Dependabot resuelto:** 4 PRs abiertos — `httpx>=0.28.1` aplicado, `TypeScript 5.4.5 → 5.9.3` (TS 7 Go rewrite pospuesto por incompatibilidad `TS2882` con `index.css`), **`React 18.3.1 → 19.2.8` + `@types/react 19.2.18` + `@types/react-dom 19.2.5` + `lucide-react 1.34.0` validados** (`tsc 0`, `vite build ok` 183 kB vendor, `vitest 7 passed`). **Vite 8.2.2 se mantiene** (sin breaking). **Rama `main` protegida** con `required_status_checks: strict` (4 jobs) + `allow_force_pushes/deletions: false`.

#### 🛡️ P1 — Alto retorno
- **Tests frontend (7 tests):** `vitest 3.2 + jsdom 26 + @testing-library/react 16` con `vitest.config.ts`, `setup.ts`, suites `security`/`api`/`Toast`.
- **Higiene OSS:** `SECURITY.md`, `CONTRIBUTING.md`, `pull_request_template.md`, `ISSUE_TEMPLATE/bug+feature`.
- **FileUpload split:** `upload/FileDropzone.tsx`, `UrlImporter.tsx`, `OpenDataExplorer.tsx` (god component 686 → modular).

#### 🔧 P2 — Deuda escalable
- **Caches TTL+Lock:** `core/cache.py` `TTLCache(ttl=7200, maxsize=200)` con `threading.Lock`.
- **Logging + Request-ID:** `core/logging_config.py` + `X-Request-ID` middleware.
- **Validación API:** `HttpUrl` en `DatasetFromUrlRequest`, `limit: Query(ge=1, le=50)`.

#### 🎨 P3 — Pulido
- **Config:** `pyproject.toml` (ruff/black), `frontend/.eslintrc.json`, `config.py` preparado para `pydantic-settings`.
- **Backend deps:** `fastapi 0.115 + uvicorn 0.34 + pydantic 2.9 + pandas 2.2.3 + openpyxl 3.1.5 + pytest 8.3 + charset 3.4 + httpx 0.28.1`.
- **Frontend deps:** `React 19.2.8 + @types/react 19.2.18 + @types/react-dom 19.2.5 + lucide 1.34.0 + TS 5.9.3`.

---

## [1.2.3] — 2026-08-27

### 🔧 Muse Spark 1.2 Contributor — Hardening de Infra y DX (v1.2.3)

> **Continuación sin impacto en CD:** Esta release culmina el hardening pendiente. El `Dockerfile` raíz validado en `v1.2.2` se mantiene; los cambios de Docker/CI son **no bloqueantes** y no alteran el disparador **Cloud Build → Cloud Run**.

#### 🐳 Docker & Deploy
- `Dockerfile` raíz añade usuario no-root (`USER app`) y `exec` en CMD — validado con build local.
- `backend/Dockerfile` multi-stage (`builder` → `python:3.11-slim`) con `pip --prefix=/install` y `HEALTHCHECK`.
- `frontend/Dockerfile` con `npm ci` y `HEALTHCHECK` vía `wget`.
- `.dockerignore` para aligerar contexto de Cloud Build (sin afectar `COPY` necesarios).

#### ⚙️ CI & Seguridad Supply Chain
- `ci.yml` añade `concurrency/cancel-in-progress`, `timeout-minutes`, jobs **no bloqueantes** `ruff/black/bandit/pip-audit` (`|| true`), `gitleaks` y `docker build check` con `buildx` + `gha` cache.
- `dependabot.yml` (pip + npm, weekly).
- `.gitignore` ignora `.mypy_cache/.ruff_cache/.hypothesis/coverage.xml/*.log`.

#### 🧠 Backend
- `core/semantics.py` helper compartido `is_percentage_or_score_column` (evita duplicación en 4 ficheros).
- `.env.example` con `GEMINI_API_KEY`, `BACKEND_CORS_ORIGINS`, `PORT`, límites.

#### 🎨 Frontend & Infra
- `vite.config.ts` `manualChunks` (`vendor` + `icons`) con split real en build.
- `nginx.conf` `gzip` + `expires 1y` en `/assets` + headers `X-Frame-Options/nosniff/Referrer-Policy`.
- `docker-compose.yml` sin `version: 3.8` obsoleto, `healthcheck`, `restart: unless-stopped`, `env_file: .env`, `depends_on: condition: service_healthy`.

---

## [1.2.2] — 2026-08-27

### 🚀 Muse Spark 1.2 Contributor — Sprints de Hardening (sin impacto en despliegue Cloud Build)

> **Atribución:** Este release fue implementado por **Muse Spark 1.2 Contributor** a petición del autor. El disparador automático de **Google Cloud Build → Cloud Run (`us-central1`)** permanece intacto: el `Dockerfile` raíz no se modifica y el CD sigue compilando en cada push a `main` sin intervención manual.

#### 🛡️ Seguridad
- **CWE-209 — Exposición de detalles técnicos en 500:** `backend/app/core/exceptions.py` ya no devuelve `str(exc)` al cliente; responde con `error_id` correlacionado y traza solo en logs del servidor.
- **Inyección en script reproducible:** `backend/app/services/script_generator.py` escapa columnas/filenames con `json.dumps`/`repr`, neutralizando payloads tipo `a"; os.system("...`.
- **CORS endurecido:** `backend/app/main.py` restringe `allow_methods` y `allow_headers` a lista explícita (`GET/POST/PUT/DELETE/OPTIONS` y `Content-Type, Authorization, X-Gemini-Api-Key`).
- **BYOK single-send:** `frontend/src/services/api.ts` envía la API Key solo por header `X-Gemini-Api-Key` (ya no duplica en `body.api_key`).
- **Ofuscación honesta (CWE-312):** `frontend/src/utils/security.ts` y `ApiKeyModal` aclaran que `localStorage` es Base64 reversible, no cifrado.

#### ♿ Accesibilidad (WCAG 2.2)
- `frontend/index.html` elimina `user-scalable=no` / `maximum-scale=1.0` para permitir zoom 200% (1.4.4).
- Modales `ApiKeyModal`/`InstallPwaModal` con `role="dialog"`, `aria-modal`, `Escape` y cierre por overlay, `aria-hidden` en iconos decorativos.
- `ProfilingDashboard` con `caption`/`scope="col"`, `aria-busy` en botones; `FileUpload` con `role="alert"` en errores y `role="button"` en dropzone; `BusinessInsights` con guard de desmontaje; `App` stepper con `aria-label`/`aria-current`.

#### 🧩 Resiliencia Frontend
- **Toasts no bloqueantes + ErrorBoundary:** `frontend/src/App.tsx` reemplaza `alert()` por `Toast` (auto-dismiss 6s) y envuelve el wizard en `ErrorBoundary`.
- **Tipado estricto:** `frontend/src/types/index.ts` reemplaza `any[]/Record<string,any>` por `unknown[]/unknown`; `frontend/src/services/api.ts` tipa `getRunQualityReport` como `ExecutionResult | null`; `Header` tipa `BeforeInstallPromptEvent` sin `any`.
- **FileUpload:** `useRef` en lugar de `getElementById`, `useMemo` en filtrado Open Data, guard de `Abort` en efectos, validación cliente de 10 MB y `aria` en errores.
- **PlanReview:** sincroniza `plan.steps` con `useEffect`; `ExecutionReport`/`BusinessInsights` corrigen props y evitan `setState` tras unmount.

---

## [1.2.0] — 2026-08-24

### 🌐 Ingesta Segura por URL y Blindaje Anti-SSRF (Fase 1)
- **Endpoint de Ingesta Remota (`POST /api/v1/datasets/from-url`)**: Descarga y procesamiento automático de datasets CSV/XLSX desde URLs públicas HTTP/HTTPS, integrándose directamente en el flujo determinista de DataFlow AI.
- **Protección Integral Anti-SSRF (`app/core/security_url.py`)**:
  - Restricción estricta de esquemas a `http` y `https` (bloqueo de `file://`, `ftp://`, `gopher://`, etc.).
  - Cobertura exhaustiva de rangos prohibidos: Loopback (`127.0.0.0/8`, `::1`), Metadatos de Google Cloud (`169.254.0.0/16`), Redes privadas RFC1918 (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), Link-Local IPv6 (`fe80::/10`), ULA IPv6 (`fc00::/7`), e IPv4-mapped IPv6 (`::ffff:0:0/96`).
- **Mitigación de DNS Rebinding mediante IP Pinning**:
  - Resolución DNS única con `socket.getaddrinfo()` y validación previa de todas las IPs candidatas.
  - Conexión TCP directa fijada a la IP pública validada (`PinnedAsyncNetworkBackend`), preservando `server_hostname` (SNI) y la cabecera `Host` para validación estricta de certificados TLS en conexiones HTTPS.
  - Intercepción y revalidación segura de redirecciones HTTP salto a salto (máx. 3 saltos).
- **Gestión de Memoria y Ciclo de Vida en Cloud Run (`tmpfs`)**:
  - Límite defensivo fijado en 20 MB (`MAX_URL_FILE_SIZE_BYTES`) con streaming en bloques de 64 KB y corte inmediato en caso de exceso.
  - Limpieza automática preventiva (`_cleanup_old_uploads`) de archivos temporales huérfanos para evitar acumulación en la RAM del contenedor.

### 🎨 Interfaz React para Ingesta por URL y Feedback en Vivo (Fase 2)
- **Selector de Modo en UI (`FileUpload.tsx`)**: Pestañas de alternancia fluida entre *"Subir Archivo Local"*, *"Pegar Enlace Web (URL)"* y *"Explorar Open Data"*.
- **Chips de Prueba Rápida con 1 Clic**: Datasets de prueba inmediatos (PIB Mundial, Carsharing & Movilidad, Dataset Iris) para verificación instantánea sin buscar enlaces externos.
- **Feedback de Progreso en Vivo**: Indicadores animados secuenciales durante la conexión Anti-SSRF, descarga en streaming y profiling semántico.

### 🏛️ Conector a Portal Open Data (CKAN) y Buscador Integrado (Fase 3)
- **Integración con API CKAN (`app/services/open_data_service.py`)**: Endpoints `GET /open-data/search` y `GET /open-data/featured` para buscar y filtrar recursos CSV/XLSX en portales públicos gubernamentales (datos.gob.es, data.gov).
- **Catálogo Curado con Fallback Resiliente**: Repositorio local de 5 datasets de calidad garantizada ante fallos o latencias de la API externa de CKAN.

### 🛡️ Detección de Encoding con `charset-normalizer` y Guardrails Semánticos (Fase 4)
- **Detección Estadística de Codificación**: Normalización automática de archivos en `Windows-1252`, `ISO-8859-1`, `latin-1` y `UTF-8 con BOM` (`\xef\xbb\xbf`) sin corrupción de caracteres españoles (`ñ`, tildes, `€`).
- **Prioridad Semántica de Identificadores y Códigos**: Corrección en `ProfilerService` para garantizar que códigos postales (`08001`), códigos INE (`28079`) o identificadores alfanuméricos (`id_precio`, `id_alta`) se clasifiquen como `ID` y se preserven como `TEXT` (evitando su pérdida de ceros o suma errónea en Power BI).

### 🛡️ Evidencia de Seguridad y Penetration Testing en Producción
- **Pruebas Manuales Reales en Producción (2026-08-24)**: Ejecución y verificación manual de 7 vectores de ataque SSRF reales (metadatos GCP `169.254.169.254`, loopback `127.0.0.1`, bypass por nombre `localhost`, evasión decimal `2130706433`, evasión hexadecimal `0x7f.0.0.1`, evasión octal `0177.0.0.1` y userinfo spoofing) directamente contra el contenedor desplegado en Google Cloud Run, confirmando el bloqueo `400` y `SSRF_BLOCKED_IP`/`EMBEDDED_CREDENTIALS_DISALLOWED` en todos los casos.
- **Suite de Regresión Automatizada**: Conversión de los 7 vectores más el caso positivo de control a tests automatizados en `test_security_url_ssrf_regression.py`.

### 🧪 Suite de Pruebas Automatizadas
- Se alcanzaron **96 tests unitarios y de integración automatizados (100% pasando en verde)** con cobertura de seguridad Anti-SSRF, regresión de pentesting, Open Data, encodings y guardrails semánticos.

---

## [1.1.3] — 2026-08-24

### 📱 Soporte PWA e Instalación en Móvil (Progressive Web App)
- **Instalabilidad en Móviles y Escritorio**: Creación del Web App Manifest (`manifest.webmanifest`), Service Worker con pre-caching del App Shell (`sw.js`) y generación de iconos multi-resolución (192px, 512px, SVG y Apple Touch Icon).
- **Experiencia de Usuario Nativa**: Botón interactivo "Instalar App" en la cabecera para Android/Chrome y modal de asistencia para iOS Safari ("Añadir a pantalla de inicio").
- **Diseño Mobile-First y Responsivo**: Optimización completa de componentes UI para smartphones y tablets (Stepper táctil, rejillas fluidas de KPIs y catálogo de perfiles).
- **Legibilidad Móvil en GitHub**: Reestructuración del `README.md` con enlaces compactos, diagramas Mermaid nativos y secciones adaptadas para la app de GitHub Mobile.

---

## [1.1.2] — 2026-08-19

### 🐛 Corrección Crítica — Protección de Datos e Inferencia Semántica (Anti Data Corruption)
- **Eliminación de Falso Positivo en Porcentajes**: Corrección en `ProfilerService`, `QualityService` y `ETLService` para evitar clasificar erróneamente columnas de conteo métrico absoluto (ej. `Conversiones`, `Leads`, `Visitas`, `Ventas`, `Llamadas`, `Clicks`, `Unidades`) como porcentajes.
- **Protección contra Truncamiento Accidental**: Se restringió la aplicación de `clamp_range [0.0, 100.0]` exclusivamente a columnas con evidencia explícita (`%`, `_pct`, `_rate`, `_score`, `_ratio`, `_tasa`, `score_calidad`), garantizando la preservación al 100% de métricas con valores superiores a 100 (ej. `Conversiones = 210, 180, 120`).

### 🧪 Suite de Pruebas
- Incorporación de `test_marketing_campaigns_dataset_no_false_percentage_clamp`, alcanzando **29 tests automatizados (100% pasando en verde)**.

---

## [1.1.1] — 2026-08-19

### 🛡️ Seguridad y Remediación CodeQL
- **Prevención de Path Traversal (CWE-022)**: Saneamiento y confinamiento estricto de la ruta de servido SPA en `backend/app/main.py` mediante `Path.resolve()` y validación `is_relative_to(STATIC_DIR)`.
- **Almacenamiento Seguro de Credenciales (CWE-312)**: Implementación de vault cifrado en el cliente (`frontend/src/utils/security.ts`) para evitar almacenar la API Key en texto plano en `localStorage`, manteniendo la arquitectura BYOK con retrocompatibilidad.

### 🚀 Lógica de Negocio y Calidad
- **Acotación Completa de Porcentajes `[0.0, 100.0%]`**: Ampliación del rango de acotación (`clamp_range`) para columnas de porcentaje y ratio en `ETLService`, recortando tanto valores negativos ilógicos (ej. `-2%` $\rightarrow$ `0.0%`) como valores por encima de `100.0%`.

### 🧪 Suite de Pruebas
- Incorporación de `test_percentage_clamp_floor_and_ceiling`, alcanzando **28 tests automatizados (100% pasando en verde)**.

---

## [1.1.0] — 2026-08-18

### 🚀 Novedades y Mejoras
- **Marcadores de Ausencia Universales**:
  - Ampliación del catálogo centralizado de marcadores en `number_parsing.py` para reconocer `--`, `---`, `-`, `–` (en-dash), `—` (em-dash), `n/d`, `n/a`, `nd`, `na`, `null`, `none`, `nan`, `nil`, `s/n`, `s/d`, `undefined`.
  - Inferencia robusta en `ProfilerService`: columnas cuantitativas con marcadores mixtos se tipan automáticamente como `NUMERIC` sin importar el tamaño de la muestra.
- **Protección Multicapa de Identificadores y Códigos (Defensa en Profundidad)**:
  - **Capa 1 (Calidad)**: `QualityService` excluye explícitamente columnas de identificador (`ID_*`, `*_ID`, `COD_*`, `PED-`, etc.) del detector de inconsistencias de formato.
  - **Capa 2 (Planificador & Copiloto IA)**: Reglas de guardrails y prompt de `GeminiProvider` prohíben taxativamente proponer `normalize_case` sobre claves primarias o códigos para preservar integridad referencial en bases de datos y Power BI.
  - **Capa 3 (Transformación Determinista)**: `NormalizeCaseTransformation` preserva tokens alfanuméricos con guiones (`PED-201`, `EMP-04`) en mayúsculas intactas.
- **Suite de Pruebas Automatizadas**:
  - Incorporación de `test_dataset4_verification.py`, alcanzando **27 tests automatizados (100% pasando en verde)**.

### 🐛 Correcciones (Bug Fixes)
- Corregido fallo donde `Unidades_Stock` permanecía como texto literal `"--"` en lugar de convertirse a `NaN`/`float64`.
- Corregida degradación de `ID_Pedido` (`PED-201` $\rightarrow$ `Ped-201`), manteniendo el código en mayúsculas estrictas.

---

## [1.0.0] — 2026-08-18

### 🚀 Despliegue en Producción
- **Google Cloud Run (`us-central1`)**: Aplicación 100% operativa en producción con contenedor unificado multi-stage (React + FastAPI + pandas).
- **Despliegue Continuo (CD)**: Activador de Google Cloud Build conectado a la rama `main` de GitHub.
- **Integración Continua (CI)**: Pipeline de GitHub Actions ejecutando tests de backend y compilación de TypeScript en cada push/PR.
- **BYOK (Bring Your Own Key)**: Gestión de API Key de Google Gemini en `localStorage` del cliente con envío efímero por cabecera HTTP.
- **Business Analytics**: Motor de KPIs de negocio por dominio (Contact Center, Ventas, People Analytics) con cálculo en tiempo real.
- **Gobierno de Datos**: Motor ETL determinista con catálogo cerrado de 11 transformaciones y auditoría reproducible en Python.

---

<p align="center">Creado por <a href="https://github.com/migueljerico">@migueljerico</a> y documentado por QwenCloud (deepseek-v4-pro-0813) desde la App Asistente de IA · 2026</p>
