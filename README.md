# 🚀 DataFlow AI

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Pandas](https://img.shields.io/badge/pandas-3.0-150458?style=for-the-badge&logo=pandas&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-8-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![Google Cloud Run](https://img.shields.io/badge/Google%20Cloud%20Run-us--central1-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white)
![Cloud Build](https://img.shields.io/badge/CD-Cloud%20Build-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white)
![PyArrow](https://img.shields.io/badge/PyArrow-Parquet-FF6600?style=for-the-badge&logo=apachearrow&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-E2E-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-163%20backend%20%7C%2041%20frontend%20%7C%203%20E2E%20passed-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)
![Versión](https://img.shields.io/badge/Versi%C3%B3n-1.12.0-blue?style=for-the-badge&logo=git&logoColor=white)
![Gemini](https://img.shields.io/badge/IA-Google%20Gemini-4285F4?style=for-the-badge&logo=googlegemini&logoColor=white)

![Licencia](https://img.shields.io/badge/Licencia-MIT-yellow?style=for-the-badge&logo=open-source-initiative&logoColor=white)

*From raw business data to clean, trusted and actionable insights.*  
*Un copiloto inteligente y gobernado para preparación, calidad, transformación y análisis de datos empresariales.*

> 🌐 **Despliegue en Producción:** [https://dataflow-ai-748914382449.us-central1.run.app](https://dataflow-ai-748914382449.us-central1.run.app)  
> ⚠️ **Versión Piloto / MVP:** Diseñado para equipos de BI, Analytics y Operaciones que necesitan datos fiables antes de construir reportes en Power BI.

---

## 📑 Índice

1. [Acceso y Despliegue](#-acceso-y-despliegue)
2. [Vista Previa de la Aplicación](#-vista-previa-de-la-aplicación)
3. [Descripción del Proyecto](#-descripción-del-proyecto)
4. [Funcionalidades Principales](#-funcionalidades-principales)
5. [Evidencia de Seguridad Verificada](#%EF%B8%8F-evidencia-de-seguridad-verificada-penetration-testing-en-producción)
6. [Modelo de Data Quality Score](#-modelo-de-data-quality-score)
7. [Catálogo de Transformaciones ETL](#%EF%B8%8F-catálogo-de-transformaciones-etl)
8. [Datasets Demostrativos Incluidos](#-datasets-demostrativos-incluidos)
9. [Instalación y Puesta en Marcha](#%EF%B8%8F-instalación-y-puesta-en-marcha)
10. [Estructura del Repositorio](#-estructura-del-repositorio)

---

## 🔗 Acceso y Despliegue

### 🌐 Despliegue en Producción (Google Cloud Run)

La plataforma está operativa en **Google Cloud Run** (`us-central1`) con despliegue continuo (CD) en cada push a `main`:

| Recurso | Enlace Directo |
| :--- | :--- |
| 🌐 **Aplicación Web** | [Abrir DataFlow AI](https://dataflow-ai-748914382449.us-central1.run.app) |
| 🔌 **API REST / OpenAPI** | [Endpoints /api/v1](https://dataflow-ai-748914382449.us-central1.run.app/api/v1) |
| 📖 **Documentación Swagger** | [Swagger UI /docs](https://dataflow-ai-748914382449.us-central1.run.app/docs) |
| 💓 **Healthcheck** | [Estado del Servicio /health](https://dataflow-ai-748914382449.us-central1.run.app/health) |

### 💻 Entorno Local y Docker

| Entorno | Frontend | Backend / API | Swagger Docs |
| :--- | :--- | :--- | :--- |
| **Local Dev** | `http://localhost:3000` | `http://localhost:8000/api/v1` | `http://localhost:8000/docs` |
| **Docker Compose** | `http://localhost:3000` | `http://localhost:3000/api/v1` | `http://localhost:8000/docs` |

### 📚 Documentación y Trazabilidad

| Documento | Descripción |
| :--- | :--- |
| 🗺️ **[ROADMAP.md](ROADMAP.md)** | Plan de evolución arquitectónica (Ingesta URL, Open Data CKAN, Guardrails). |
| 📜 **[CHANGELOG.md](CHANGELOG.md)** | Historial completo de versiones, fixes y notas de release. |
| 📖 **[MANUAL_TECNICO.md](MANUAL_TECNICO.md)** | Manual de arquitectura, catálogo ETL, modelos y seguridad. |

---

## 📸 Vista Previa de la Aplicación

Recorrido completo por el flujo de trabajo de DataFlow AI, desde la ingesta del dataset crudo hasta la exportación a Power BI y Excel:

### 1️⃣ Carga de Datasets Empresariales (Subida, URL o Open Data)

*Paso 1 del stepper: carga de CSV/XLSX por arrastre, importación directa desde URL segura o explorador de portales Open Data (CKAN).*

![Vista Previa — Subida de Datasets](./docs/capturas/captura_dataflow_ai_subida.png)

### 2️⃣ Auditoría de Calidad y Profiling (Data Quality Score)

*Paso 2: puntuación explicable 0-100 en 5 dimensiones, análisis de columnas, tipos inferidos y hints semánticos con guardrails de códigos.*

![Vista Previa — Auditoría de Calidad y Profiling](./docs/capturas/captura_dataflow_ai_auditoria.png)

### 3️⃣ Revisión Humana del Plan ETL (Human-in-the-Loop)

*Paso 3: el copiloto IA (Gemini) propone transformaciones con confianza, riesgo y parámetros; el usuario aprueba o rechaza cada paso antes de ejecutar.*

![Vista Previa — Revisión Humana del Plan ETL](./docs/capturas/captura_dataflow_ai_plan.png)

### 4️⃣ Transformación Determinista y Trazabilidad (Resultados & Script)

*Paso 4: ejecución determinista en Python/pandas con log de validación explícita, hashes MD5 de entrada/salida y descargas en CSV, Parquet y script Python reproducible.*

![Vista Previa — Transformación Completada](./docs/capturas/captura_dataflow_ai_transformacion.png)

### 5️⃣ Business Analytics: Segmentación de Clusters

*Diagrama de dispersión 2D interactivo de clusters con centroides calculados, filtros por grupo y detección visual de outliers.*

![Vista Previa — Clusters](./docs/capturas/captura_dataflow_ai_clusters.png)

### 6️⃣ Guía de Integración y Fórmulas para Power BI y Excel

*Generación adaptativa de medidas DAX, código Power Query M, modelo semántico TMDL/PBIP y fórmulas dinámicas de Excel localizadas para la configuración regional en español.*

![Vista Previa — Integración Power BI y Excel](./docs/capturas/captura_dataflow_ai_powerbi.png)

---

## 📋 Descripción del Proyecto

### 📌 El Problema Empresarial

Las organizaciones reciben a diario datos desestructurados e inconsistentes procedentes de CRMs, ERPs, Contact Centers o exportaciones de terceros. Estos archivos presentan problemas recurrentes:

- **Filas vacías o corruptas** que rompen los pipelines de ingesta.
- **Registros duplicados** que alteran los conteos de clientes y ventas.
- **Formatos de fecha heterogéneos** mezclados en la misma columna (`YYYY-MM-DD`, `DD/MM/AAAA`).
- **Números guardados como texto** con monedas o porcentajes (`1.200,50 €`, `$350.00`, `14.1%`) y marcadores como `N/D`, `N/A`, `--`.
- **Inconsistencias tipográficas** y rotura de siglas (`SOPORTE SA` → `Soporte Sa`).
- **Violaciones de lógica de negocio** (absentismos negativos que distorsionan medias, porcentajes fuera de rango).

Resolver esto manualmente en Excel o Power Query consume horas y carece de trazabilidad. **DataFlow AI** automatiza y audita todo este proceso.

### 💡 Principio Fundamental de Gobierno

> **"La IA propone. El usuario decide. Python ejecuta."**

La IA nunca ejecuta código arbitrario ni manipula datos sin supervisión. Todo cambio se realiza a través de un **motor determinista en Python/pandas** basado en un catálogo cerrado de operaciones auditadas.

### 🔄 Flujo de Trabajo

```mermaid
flowchart TD
    A["📁 1. Ingesta Multicanal<br/>CSV · Excel · URL · Open Data"] --> B["🔍 2. Profiling Automático<br/>Inferencia de Tipos y Códigos"]
    B --> C["📊 3. Data Quality Score<br/>Evaluación 0-100 en 5 Dimensiones"]
    C --> D["🤖 4. Propuesta de Plan ETL<br/>Motor Determinista o Copiloto IA"]
    D --> E["👤 5. Revisión Humana<br/>Control Human-in-the-Loop"]
    E --> F["⚙️ 6. Motor Determinista<br/>Transformación en Python/Pandas"]
    F --> G["✅ 7. Salida para Power BI<br/>Dataset Limpio + KPIs + Script .py"]
```

---

## ✨ Funcionalidades Principales

- 📁 **Carga y Validación Multicanal:** Subida de CSV/XLSX locales, importación directa por URL remota (streaming con tope de 20 MB) y explorador de portales **Open Data (CKAN)** con buscador temático y tarjetas de 1 clic.
- 🛡️ **Seguridad Defensiva y Blindaje Anti-SSRF:** Validación estricta de esquemas (`http`/`https`), bloqueo integral de rangos IPv4/IPv6 privados y de metadatos de GCP, y mitigación de DNS Rebinding mediante IP Pinning a nivel de socket.
- 🌐 **Detección Estadística de Codificación (`charset-normalizer`):** Reconocimiento transparente de `UTF-8`, `UTF-8 con BOM`, `Windows-1252` e `ISO-8859-1/15` con normalización automática a UTF-8 y preservación de `ñ`, tildes y monedas (`€`).
- 🔍 **Data Profiling Automático con Guardrails de Códigos:** Inferencia de tipos (`numeric`, `datetime`, `text`, `boolean`, `categorical`) y detección semántica con protección de ceros iniciales en códigos postales (`08001`), códigos INE y referencias.
- 📊 **Data Quality Score Explicable:** Puntuación 0-100 ponderada en 5 dimensiones con desglose de anomalías y muestras de evidencia.
- ⚙️ **Motor ETL Determinista:** Catálogo estricto de 11 operaciones registradas en `TransformationRegistry` con ejecución reproducible.
- 📈 **Business Analytics & KPIs:** Cálculo en tiempo real con `pandas` de métricas de negocio por dominio (Ventas, RRHH, Contact Center), segmentación de clusters con centroides y diagrama de dispersión interactivo.
- ⚡ **Observabilidad y Métricas de Inferencia IA:** Diagnóstico en tiempo real de latencia (`ms`/`s`), balance de tokens (`prompt` / `completion` / `total`), cálculo de coste estimado en USD y modelo activo (`gemini-2.5-flash`) en la propuesta de planes asistidos por IA, con caché semántica LRU/TTL que reduce la latencia a < 1 ms en esquemas repetidos.
- 🎯 **Comparador Interactivo de Outliers (Scatter Diff):** Diagnóstico visual antes/después entre dataset crudo y limpio en la pestaña de Outliers, con trazado de acotación/clamp, balance global de resolución de anomalías por IQR y tabla interactiva de variación.
- 📊 **Exportación de Modelos Semánticos Power BI:** Descarga directa de definiciones TMDL (`.tmdl`), scripts DAX (`.dax`) y proyectos Power BI Developer Mode (`.pbip` en ZIP), además de la guía clásica de medidas DAX y Power Query M.
- 📗 **Fórmulas Dinámicas Adaptativas para Excel:** Generación multi-categoría (Auditoría Outliers IQR, KPIs & Estadísticas, Participación % y Condicionales) compatible con la configuración regional en español e inglés.
- 🌐 **Caché de Inferencia Distribuida (Redis / Cloud Memorystore):** Arquitectura de dos niveles (L1 memoria LRU + L2 Redis compartida) que multiplica la tasa de aciertos entre instancias de Cloud Run, con degradación elegante a memoria local si Redis no está disponible.
- ⭐ **Visualizador de Modelo Estrella (Star Schema):** Diagrama interactivo que previsualiza la estructura semántica antes de cargar el archivo en Power BI: tabla de hechos central, dimensiones de atributo y calendario en órbita, relaciones muchos-a-uno inspeccionables y DAX de tablas calculadas listo para pegar.
- 🤖 **Copiloto IA Gobernado:** Asistente con Google Gemini para proponer transformaciones óptimas, con fallback 100% determinista sin coste.
- 🔑 **Seguridad BYOK / Local Vault:** Almacenamiento seguro y ofuscado en `localStorage` del cliente; la clave nunca se almacena en el servidor ni en logs.
- 🛡️ **Privacidad y RGPD:** Anonimización de datos personales (`[NOMBRE]`, `[EMAIL]`, `[TELÉFONO]`) en las muestras de análisis.
- 📝 **Auditoría y Trazabilidad:** Logs paso a paso, hashes MD5 de entrada/salida y exportación de script reproducible en Python (`.py`).

---

## 🛡️ Evidencia de Seguridad Verificada (Penetration Testing en Producción)

Para validar el blindaje **Anti-SSRF** y la resistencia a técnicas de evasión en el endpoint de ingesta remota (`POST /api/v1/datasets/from-url`), el **2026-08-24** se ejecutó una batería manual de **7 pruebas de penetración reales** directamente contra el contenedor desplegado en **Google Cloud Run** (no simuladas).

Los resultados obtenidos confirman el bloqueo determinista en todas las categorías de ataque:

| # | Categoría de Ataque SSRF | URL Probada en Producción | Resultado Real | Código de Error | Comportamiento Observado / Evidencia |
| :-: | :--- | :--- | :---: | :--- | :--- |
| **1** | **Metadatos de Google Cloud** | `http://169.254.169.254/computeMetadata/v1/` | **400 Bad Request** | `SSRF_BLOCKED_IP` | Bloqueo estricto del servicio de metadatos de Cloud Run (`blocked_ip: 169.254.169.254`). |
| **2** | **Loopback Directo IPv4** | `http://127.0.0.1/` | **400 Bad Request** | `SSRF_BLOCKED_IP` | Bloqueo inmediato de rangos locales (`blocked_ip: 127.0.0.1`). |
| **3** | **Bypass por Nombre de Host** | `http://localhost/` | **400 Bad Request** | `SSRF_BLOCKED_IP` | **Resolución DNS previa a la validación**: el hostname se traduce a IP antes del chequeo (`host: localhost` $\rightarrow$ `127.0.0.1`). |
| **4** | **Evasión Notación Decimal** | `http://2130706433/` | **400 Bad Request** | `SSRF_BLOCKED_IP` | **Normalización de IP**: el entero decimal `2130706433` se normaliza a `127.0.0.1` antes de cotejar contra la lista de redes bloqueadas. |
| **5** | **Evasión Notación Hexadecimal** | `http://0x7f.0.0.1/` | **400 Bad Request** | `SSRF_BLOCKED_IP` | Reconocimiento y normalización de octetos hexadecimales (`0x7f.0.0.1` $\rightarrow$ `127.0.0.1`). |
| **6** | **Evasión Notación Octal** | `http://0177.0.0.1/` | **400 Bad Request** | `SSRF_BLOCKED_IP` | Reconocimiento y normalización de octetos octales (`0177.0.0.1` $\rightarrow$ `127.0.0.1`). |
| **7** | **Userinfo / Credenciales Embebidas** | `http://169.254.169.254@raw.githubusercontent.com/` | **400 Bad Request** | `EMBEDDED_CREDENTIALS_DISALLOWED` | Rechazo directo de userinfo/credenciales en URL sin interpretar ambigüedades del parser (`Body: {}`). |
| **Control** | **Caso Positivo de Control** | `https://raw.githubusercontent.com/datasets/gdp/master/data/gdp.csv` | **201 Created** | *(Éxito)* | Ingesta correcta: `dataset_id` generado, 13.979 filas, 4 columnas, 562.767 bytes y `status: "validated"`. |

> 🧪 **Cobertura de Regresión Automatizada:** Toda esta batería de ataques reales está además codificada en la suite de pruebas unitarias y de integración ([`test_security_url_ssrf_regression.py`](backend/tests/test_security_url_ssrf_regression.py)), asegurando que ningún cambio futuro pueda reabrir estas vulnerabilidades en CI/CD.

---

## 📊 Modelo de Data Quality Score

La calidad del dataset se calcula mediante una fórmula ponderada en **5 dimensiones de negocio**:

$$\text{Quality Score} = (0.30 \times C) + (0.25 \times V) + (0.20 \times K) + (0.15 \times U) + (0.10 \times I)$$

| Dimensión | Ponderación | Objetivo de Calidad y Métrica de Ejemplo |
| :--- | :---: | :--- |
| **Datos Completos ($C$)** | **30%** | Detección de campos nulos o vacíos *(ej. 91.67% · 8 columnas con nulos)*. |
| **Formatos Válidos ($V$)** | **25%** | Verificación de formatos de fecha, tipos y números *(ej. 75.87% · 7 correcciones de tipo/fecha)*. |
| **Formato Homogéneo ($K$)** | **20%** | Normalización de espacios y formatos de texto respetando siglas *(ej. 100% · 0 variantes de texto)*. |
| **Registros Únicos ($U$)** | **15%** | Eliminación de registros y filas duplicadas exactas *(ej. 100% · 0 filas duplicadas)*. |
| **Reglas de Negocio ($I$)** | **10%** | Cumplimiento de límites lógicos y rangos válidos *(ej. Absentismo $\ge 0$, Productividad $[0, 100\%]$)*. |

---

## 🛠️ Catálogo de Transformaciones ETL

Operaciones deterministas controladas por el motor de transformación:

| Operación | Finalidad de Limpieza |
| :--- | :--- |
| `trim_text` | Limpieza de espacios iniciales, finales y dobles espacios internos. |
| `normalize_case` | Estandarización a Title Case preservando siglas corporativas (`SA`, `SL`, `SLU`, `KPI`). |
| `convert_datetime` | Conversión a ISO 8601 (`%Y-%m-%d`) soportando formatos europeos (`DD/MM/AAAA`). |
| `convert_numeric` | Eliminación de símbolos (`€`, `$`, `%`) y marcadores (`N/D`, `N/A`, `--`) a numérico float64. |
| `clamp_range` | Acotación de valores negativos o fuera de intervalo lógico (`min_value`, `max_value`). |
| `round_numeric` | Redondeo de precisión a $N$ decimales. |
| `fill_missing` | Imputación controlada por constante, media, mediana o moda. |
| `remove_duplicates` | Eliminación de duplicados exactos o por clave candidata. |
| `rename_column` | Renombrado seguro de columnas. |
| `drop_column` | Eliminación de columnas irrelevantes o vacías. |
| `normalize_category` | Mapeo explícito según diccionario de equivalencias. |

---

## 💼 Datasets Demostrativos Incluidos

Disponibles para pruebas de 1 clic en la interfaz o en [`data_samples/`](./data_samples):

- **Contact Center & Operaciones** (`contact_center_corrupted.csv`): Métricas de llamadas (AHT, Conversión, Score de Calidad) con valores `N/D`, AHT negativo y fechas europeas.
- **Ventas & Retail** (`sales_sample_corrupted.csv`): Transacciones con precios como texto multimoneda (`1200.50 €`, `$350.00`), fechas mixtas y filas duplicadas.
- **People Analytics & RRHH** (`people_analytics_corrupted.csv`): Salarios con símbolos, absentismo negativo (`-3`), productividad $>100\%$ y fila vacía.
- **Logística & Cadena de Suministro** (`logistics_pedidos_corrupted.csv`): Pedidos B2B con acrónimos mercantiles (`S.L.U.`), marcadores universales de nulo (`--`), divisas combinadas (`€`, `$`) y outliers.

---

## ⚙️ Instalación y Puesta en Marcha

### Requisitos Previos y Dependencias Principales

- **Python 3.11+** (compatible con Python 3.14)
  - `pandas >= 3.0.5`, `pydantic >= 2.13.5`, `pyarrow >= 25.0.1`, `pytest >= 9.1.1`, `uvicorn >= 0.52.4`, `fastapi >= 0.115.0`.
- **Node.js 22.22+ / 24+** (Node.js 24 configurado en CI/CD y Dockerfile multi-stage por requerimiento de `jsdom 30.0.1+`).
  - `react 19`, `typescript 5.9`, `vite 8`, `vitest 4.1.11`, `@vitejs/plugin-react 6.1.1`, `lucide-react 1.37.0`, `@testing-library/jest-dom 7.0.1`, `jsdom 30.0.1`.
- *(Opcional)* Docker y Docker Compose

### 1. Clonar el Repositorio

```bash
git clone https://github.com/migueljerico/dataflow-ai.git
cd dataflow-ai
```

### 2. Backend (FastAPI)

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Documentación interactiva disponible en: `http://localhost:8000/docs`.

### 3. Tests Automatizados (Pytest & Vitest)

```bash
# Backend (163 tests)
cd backend
.\venv\Scripts\pytest -v

# Frontend (41 tests)
cd ../frontend
npm test
```

> ✅ **206 tests automatizados totales (163 backend + 41 frontend) + 3 tests E2E con Playwright — 100% pasando en verde** (gobernanza determinista, esquemas proyectados de transformación, observabilidad IA con latencia y tokens, exportación de modelos semánticos Power BI TMDL/DAX/PBIP, visualizador de modelo estrella (Star Schema), fórmulas dinámicas multi-categoría de Excel, caché de inferencia Gemini y caché distribuida Redis, comparador scatter diff de outliers, Excel y números en español, seguridad Anti-SSRF con regresión de penetration testing, IP Pinning, Open Data CKAN, detección de encodings con `charset-normalizer`, guardrails semánticos, ETL, calidad y privacidad).

### 4. Frontend (React + Vite + TypeScript)

```bash
cd frontend
npm install
npm run dev
```

Aplicación disponible en: `http://localhost:3000`.

### 5. Despliegue con Docker Compose

```bash
docker compose up --build
```

---

## 📁 Estructura del Repositorio

```text
dataflow-ai/
├── .github/workflows/
│   └── ci.yml                 # CI: Pytest backend (163 tests) + Build React Vite
├── backend/
│   ├── app/
│   │   ├── ai_providers/      # Gemini Provider (BYOK), Mock determinista y caché de inferencia
│   │   ├── api/v1/endpoints/  # Datasets (URL & Open Data), Profiling, Quality, Plans, Runs, Analytics & Export
│   │   ├── core/              # Configuración, excepciones, parsing numérico y seguridad Anti-SSRF (IP Pinning)
│   │   ├── models/            # Esquemas Pydantic y contratos de datos
│   │   ├── services/          # Profiler, Quality, ETL determinista, Open Data (CKAN), Analytics, TMDL/PBIP y caché de inferencia
│   │   ├── transformations/   # Catálogo TransformationRegistry
│   │   └── main.py            # FastAPI app, middleware CORS y servido SPA
│   ├── tests/                 # Suite de 163 pruebas automatizadas
│   ├── Dockerfile             # Imagen de backend
│   └── requirements.txt       # Dependencias Python
├── frontend/
│   ├── src/
│   │   ├── components/        # UI: FileUpload (Local/URL/OpenData), Profiling, PlanReview, Execution, Insights
│   │   ├── services/          # Cliente API HTTP
│   │   ├── utils/             # Seguridad y Vault local (CWE-312)
│   │   ├── index.css          # Sistema de diseño responsivo mobile-first
│   │   └── App.tsx            # Componente raíz y stepper de navegación
│   ├── Dockerfile             # Imagen de frontend Nginx
│   └── package.json           # Dependencias React 19, Vite 8 y TypeScript
├── data_samples/              # Datasets sintéticos de prueba
├── docs/capturas/             # Capturas de la aplicación usadas en este README
├── CHANGELOG.md               # Historial de versiones (Keep a Changelog)
├── MANUAL_TECNICO.md          # Documentación técnica de arquitectura
├── ROADMAP.md                 # Roadmap de evolución arquitectónica (Fases 1 a 4)
├── Dockerfile                 # Dockerfile multi-stage unificado para Google Cloud Run
└── README.md
```

---

## 🤝 Atribución

- **Creación y desarrollo:** Creado por [@migueljerico](https://github.com/migueljerico).
- **Documentación:** Documentado por QwenCloud (deepseek-v4-pro-0813) y mejorado por **Muse Spark 1.2 Contributor** — Sprints de hardening de seguridad (CWE-209/918), accesibilidad WCAG, resiliencia frontend y blindaje de generación de scripts · 2026.
- **Última mejora (v1.13.0):** Visualizador de modelo estrella (Star Schema), caché de inferencia distribuida Redis/Memorystore, rediseño del README con índice navegable y galería de vistas previas (`docs/capturas/`), desarrollados con **GLM-5.3-Flash** a través de **[ZCode](https://z.ai)**, la app de desarrollo asistido por IA desde la que se gestionó esta release.

---

<p align="center">
  ⭐ ¡Si este proyecto te resulta útil, considere darle una estrella en GitHub! ⭐
</p>
