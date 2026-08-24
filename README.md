# 🚀 DataFlow AI

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Pandas](https://img.shields.io/badge/pandas-2.2-150458?style=for-the-badge&logo=pandas&logoColor=white)
![React](https://img.shields.io/badge/React-18.3-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5.4-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-5-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![Google Cloud Run](https://img.shields.io/badge/Google%20Cloud%20Run-us--central1-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white)
![Cloud Build](https://img.shields.io/badge/CD-Cloud%20Build-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white)
![CI](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-76%20passed-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)
![Gemini](https://img.shields.io/badge/IA-Google%20Gemini-4285F4?style=for-the-badge&logo=googlegemini&logoColor=white)
![Licencia](https://img.shields.io/badge/Licencia-MIT-yellow?style=for-the-badge&logo=open-source-initiative&logoColor=white)

*From raw business data to clean, trusted and actionable insights.*  
*Un copiloto inteligente y gobernado para preparación, calidad, transformación y análisis de datos empresariales.*

> 🌐 **Despliegue en Producción:** [https://dataflow-ai-748914382449.us-central1.run.app](https://dataflow-ai-748914382449.us-central1.run.app)  
> ⚠️ **Versión Piloto / MVP:** Diseñado para equipos de BI, Analytics y Operaciones que necesitan datos fiables antes de construir reportes en Power BI.

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
    A[📁 Datos Brutos CSV / XLSX] --> B[🔍 Profiling y Detección Semántica]
    B --> C[📊 Data Quality Score 0-100]
    C --> D[🤖 Propuesta de Plan ETL Determinista o IA]
    D --> E[👤 Revisión Humana Human-in-the-Loop]
    E --> F[⚙️ Motor Determinista Python / Pandas]
    F --> G[✅ Dataset Limpio + Analytics + Script .py]
```

---

## ✨ Funcionalidades Principales

- 📁 **Carga y Validación de Datasets:** Subida de CSV/XLSX (hasta 10 MB), importación directa desde URLs públicas (hasta 20 MB) con protección Anti-SSRF o carga de datasets demo con 1 clic.
- 🛡️ **Seguridad Defensiva y Anti-SSRF:** Validación estricta de esquemas (`http`/`https`), bloqueo integral de rangos IPv4/IPv6 privados y de metadatos de Cloud, y mitigación de DNS Rebinding mediante IP Pinning.
- 🔍 **Data Profiling Automático:** Inferencia de tipos (`numeric`, `datetime`, `text`, `boolean`, `categorical`) y detección semántica (`email`, `currency`, `percentage`, `date`, `phone`, `name`, `id`).
- 📊 **Data Quality Score Explicable:** Puntuación 0-100 ponderada en 5 dimensiones con desglose de anomalías y muestras de evidencia.
- ⚙️ **Motor ETL Determinista:** Catálogo estricto de 11 operaciones registradas en `TransformationRegistry` con ejecución reproducible.
- 👤 **Human-in-the-Loop:** Control total para revisar, editar, aprobar o rechazar cada transformación antes de ejecutar.
- 📈 **Business Analytics & KPIs:** Cálculo en tiempo real con `pandas` de métricas de negocio por dominio (Ventas, RRHH, Contact Center).
- 🤖 **Copiloto IA Gobernado:** Asistente con Google Gemini para proponer transformaciones óptimas, con fallback 100% determinista sin coste.
- 🔑 **Seguridad BYOK / Local Vault:** Almacenamiento seguro y ofuscado en `localStorage` del cliente; la clave nunca se almacena en el servidor ni en logs.
- 🛡️ **Privacidad y RGPD:** Anonimización de datos personales (`[NOMBRE]`, `[EMAIL]`, `[TELÉFONO]`) en las muestras de análisis.
- 📝 **Auditoría y Trazabilidad:** Logs paso a paso, hashes MD5 de entrada/salida y exportación de script reproducible en Python (`.py`).

---

## 📊 Modelo de Data Quality Score

La calidad del dataset se calcula mediante una fórmula ponderada en **5 dimensiones de negocio**:

$$\text{Quality Score} = (0.30 \times C) + (0.25 \times V) + (0.20 \times K) + (0.15 \times U) + (0.10 \times I)$$

| Dimensión | Peso | Objetivo de Calidad |
| :--- | :---: | :--- |
| **Completitud ($C$)** | **30%** | Detección de campos nulos o vacíos. |
| **Validez ($V$)** | **25%** | Verificación de formatos de fecha, tipos y números. |
| **Consistencia ($K$)** | **20%** | Normalización de espacios y formatos de texto (respetando siglas). |
| **Unicidad ($U$)** | **15%** | Eliminación de registros y filas duplicadas exactas. |
| **Integridad ($I$)** | **10%** | Cumplimiento de límites lógicos (ej. valores $\ge 0$, porcentajes $[0, 100]$). |

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

---

## ⚙️ Instalación y Puesta en Marcha

### Requisitos Previos

- **Python 3.11+**
- **Node.js 18+** (recomendado Node 20)
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

### 3. Tests Automatizados (Pytest)

```bash
cd backend
pytest
```

> ✅ **29 tests automatizados — 100% pasando en verde** (unitarios, integración, calidad, parsing numérico y privacidad).

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
│   ├── ci.yml                 # CI: Pytest backend + Build frontend
│   └── codeql.yml             # Análisis estático de seguridad CodeQL
├── backend/
│   ├── app/
│   │   ├── ai_providers/      # Gemini Provider (BYOK) y Mock determinista
│   │   ├── api/v1/endpoints/  # Datasets, Profiling, Quality, Plans, Runs, Analytics
│   │   ├── core/              # Configuración, excepciones y parsing numérico
│   │   ├── models/            # Esquemas Pydantic y contratos de datos
│   │   ├── services/          # Profiler, Quality, ETL determinista y Analytics
│   │   ├── transformations/   # Catálogo TransformationRegistry
│   │   └── main.py            # FastAPI app, middleware CORS y servido SPA
│   ├── tests/                 # Suite de 29 pruebas automatizadas
│   ├── Dockerfile             # Imagen de backend
│   └── requirements.txt       # Dependencias Python
├── frontend/
│   ├── src/
│   │   ├── components/        # UI: Upload, Profiling, PlanReview, Execution, Insights
│   │   ├── services/          # Cliente API HTTP
│   │   ├── utils/             # Seguridad y Vault local (CWE-312)
│   │   ├── index.css          # Sistema de diseño responsivo mobile-first
│   │   └── App.tsx            # Componente raíz y stepper de navegación
│   ├── Dockerfile             # Imagen de frontend Nginx
│   └── package.json           # Dependencias React y TypeScript
├── data_samples/              # Datasets sintéticos de prueba
├── CHANGELOG.md               # Historial de versiones (Keep a Changelog)
├── MANUAL_TECNICO.md          # Documentación técnica de arquitectura
├── Dockerfile                 # Dockerfile unificado para Google Cloud Run
└── README.md
```

---

<p align="center">
  Creado por <a href="https://github.com/migueljerico">@migueljerico</a> y documentado por QwenCloud (deepseek-v4-pro-0813) desde la App Asistente de IA · 2026
</p>