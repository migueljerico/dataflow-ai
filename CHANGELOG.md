# Changelog — DataFlow AI

Todas las modificaciones notables de este proyecto se documentan en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y este proyecto sigue el [Versionado Semántico](https://semver.org/lang/es/).

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
- **Suite de Pruebas Automatizadas**:
  - Se añadieron 47 nuevos tests unitarios y de integración (`test_security_url.py`, `test_dataset_from_url.py`), alcanzando **76 tests automatizados (100% pasando en verde)**.

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
