# Changelog — DataFlow AI

Todas las modificaciones notables de este proyecto se documentan en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y este proyecto sigue el [Versionado Semántico](https://semver.org/lang/es/).

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
