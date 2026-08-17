# 🚀 DataFlow AI

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Pandas](https://img.shields.io/badge/pandas-2.2-150458?style=for-the-badge&logo=pandas&logoColor=white)
![React](https://img.shields.io/badge/React-18.3-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5.4-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-5-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Estado](https://img.shields.io/badge/Estado-En%20desarrollo-orange?style=for-the-badge)
![Licencia](https://img.shields.io/badge/Licencia-MIT-yellow?style=for-the-badge&logo=open-source-initiative&logoColor=white)
![CI](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-23%20passed-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)
![Gemini](https://img.shields.io/badge/IA-Google%20Gemini-4285F4?style=for-the-badge&logo=googlegemini&logoColor=white)

*From raw business data to clean, trusted and actionable insights.*  
*Un copiloto inteligente y gobernado para preparación, calidad, transformación y análisis de datos empresariales.*

> ⚠️ **Versión Piloto / MVP (En desarrollo activo)**  
> *Diseñado para equipos de Business Intelligence, Analytics y Operaciones que necesitan datos fiables antes de construir reportes en Power BI.*

---

## 🔗 Acceso / Demo

El proyecto se ejecuta en local. Tras arrancar los servicios, tendrás disponibles:

| Recurso | URL |
| :--- | :--- |
| Aplicación web (frontend) | `http://localhost:3000` |
| API REST (backend FastAPI) | `http://localhost:8000/api/v1` |
| Documentación interactiva Swagger | `http://localhost:8000/docs` |
| Healthcheck | `http://localhost:8000/health` |

También puedes levantar el stack completo con Docker Compose:

| Recurso | URL |
| :--- | :--- |
| Frontend (Nginx) | `http://localhost:3000` |
| Backend (FastAPI, vía proxy `/api`) | `http://localhost:3000/api/v1` |

No existe despliegue público actual; el roadmap contempla Google Cloud Run.

---

## 📋 Descripción

### 📌 Problema Empresarial

Las empresas reciben diariamente datos desordenados e inconsistentes procedentes de múltiples plataformas (CRMs, ERPs, Contact Centers, sistemas de RRHH, exportaciones de terceros). Estos datos presentan habitualmente:

- **Filas vacías o malformadas** (`,,,,,,,`).
- **Registros duplicados** que distorsionan los conteos de clientes o empleados.
- **Formatos de fecha heterogéneos** (`2026-01-05` vs `06/01/2026` vs `07-01-2026`).
- **Números almacenados como cadenas de texto** con símbolos (`1.200,50 €`, `$350.00`, `14.1%`) o marcadores como `"N/D"` / `"N/A"`.
- **Inconsistencias de formato en texto** (`Madrid`, `MADRID`, `madrid `) y rotura de acrónimos (`SOPORTE SA` → `Soporte Sa`).
- **Violaciones de reglas de negocio** (absentismos negativos que cancelan el absentismo real de otros empleados, productividades superiores al 100%).

Antes de poder construir reportes de Business Intelligence (BI) o modelos analíticos fiables en Power BI, estos problemas requieren horas de trabajo manual repetitivo. **DataFlow AI** automatiza y gobierna este proceso.

### 💡 Solución y Principio Fundamental

DataFlow AI sigue un principio estricto de gobierno de datos:

> **"La IA propone. El usuario decide. Python ejecuta."**

La IA nunca ejecuta código arbitrario ni modifica directamente los datos sin supervisión. La plataforma realiza la manipulación de datos a través de un **motor ETL determinista** escrito en Python/pandas sobre un catálogo estricto de transformaciones validadas con **auditoría de validación explícita**.

**Flujo de Trabajo:**

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

---

## ✨ Funcionalidades

| Funcionalidad | Descripción |
| :--- | :--- |
| **Carga de datasets** | Subida de archivos CSV/XLSX (máx. 10 MB) o carga de datasets demo con 1 clic. Detección automática de delimitador, limpieza de filas vacías y validación de formato. |
| **Data Profiling automático** | Inferencia de tipos (`numeric`, `datetime`, `text`, `boolean`, `categorical`) y sugerencias semánticas (`email`, `currency`, `percentage`, `date`, `phone`, `name`, etc.). |
| **Data Quality Score explicable** | Puntuación 0-100 ponderada en 5 dimensiones de negocio, con issues accionables y evidencia muestral. |
| **Motor ETL determinista** | Catálogo de 11 transformaciones controladas registradas en `TransformationRegistry`. |
| **Human-in-the-Loop** | Revisión, edición y aprobación/rechazo de cada paso antes de ejecutar. Los pasos rechazados no se ejecutan. |
| **Business Analytics & KPIs** | Cálculo en tiempo real de KPIs ejecutivos por dominio (RRHH, Ventas, Contact Center) con pandas. |
| **Copiloto IA gobernado** | Sugerencias de transformaciones con Google Gemini o motor determinista gratuito. Guardrails estrictos: solo operaciones del catálogo. |
| **BYOK / Zero-Storage** | La API Key de Gemini se guarda solo en `localStorage` del navegador y viaja por cabecera `x-goog-api-key`. Nunca se persiste en backend ni en logs. |
| **Privacidad RGPD** | Al LLM solo se envían esquema, estadísticas y 3 filas de muestra con PII enmascarada (`[NOMBRE]`, `[EMAIL]`, `[TELÉFONO]`). |
| **Auditoría y trazabilidad** | Logs de auditoría por paso, hashes MD5 de entrada/salida, conteo de filas/columnas antes-después y script reproducible `.py`. |

### 📊 Modelo de Data Quality Score (Lenguaje de Negocio Natural)

La calidad del dataset se evalúa mediante una fórmula ponderada explicable basada en **5 dimensiones**:

$$\text{Quality Score} = (0.30 \times C) + (0.25 \times V) + (0.20 \times K) + (0.15 \times U) + (0.10 \times I)$$

| Dimensión | Ponderación | Descripción de Negocio |
| :--- | :---: | :--- |
| **Datos Completos ($C$)** | **30%** | Medición de campos sin valores nulos ni vacíos. |
| **Formatos Válidos ($V$)** | **25%** | Verificación de que fechas, números y tipos cumplan con el formato esperado. |
| **Formato Homogéneo ($K$)** | **20%** | Detección de espacios sobrantes y variaciones de mayúsculas/minúsculas (preservando siglas como SA, SL). |
| **Registros Únicos ($U$)** | **15%** | Identificación de registros y filas duplicadas exactas. |
| **Reglas de Negocio ($I$)** | **10%** | Comprobación de límites lógicos (e.g. Absentismo $\ge 0$, Productividad $\le 100\%$). |

### 🛠️ Catálogo de Transformaciones ETL Controladas

Toda modificación sobre los datos utiliza operaciones estrictas del `TransformationRegistry`:

| Operación | Descripción |
| :--- | :--- |
| `trim_text` | Limpieza de espacios iniciales, finales y dobles espacios internos. |
| `normalize_case` | Estandarización a Title Case preservando siglas corporativas (`SA`, `SL`, `SLU`, `KPI`). |
| `convert_datetime` | Conversión a ISO 8601 (`%Y-%m-%d`) respetando formatos europeos `DD/MM/AAAA` sin inversión de día/mes. |
| `convert_numeric` | Eliminación de símbolos (`$`, `€`, `%`) y marcadores (`N/D`, `N/A`) con soporte de separadores europeos y americanos. |
| `clamp_range` | Acotación de valores negativos o fuera de rango lógico (`min_value`, `max_value`). |
| `round_numeric` | Redondeo numérico a $N$ decimales. |
| `fill_missing` | Imputación de valores faltantes por constante, media, mediana o moda. |
| `remove_duplicates` | Eliminación de filas duplicadas exactas o por clave candidata. |
| `rename_column` | Renombrado seguro de columnas. |
| `drop_column` | Eliminación de columnas no deseadas. |
| `normalize_category` | Reemplazo basado en diccionarios de mapeos explícitos. |

### 📈 Módulo de Business Analytics & Executive Insights

Una vez transformados los datos, DataFlow AI calcula en tiempo real con `pandas`:

- **KPIs Operativos Clave por Dominio**:
  - **RRHH / People Analytics**: Plantilla activa, salario medio, productividad media acotada y absentismo total acumulado.
  - **Ventas & Retail**: Facturación total neta, ticket medio y unidades vendidas.
  - **Contact Center**: Total llamadas, AHT medio operativo y CSAT/Score de calidad medio.
- **Distribución Categórica**: Desglose por departamento, canal o agente.
- **Resumen Ejecutivo de Negocio**: Informe estructurado para Dirección destacando el impacto de la calidad de datos y recomendaciones operativas.

### 🤖 Rol de la IA, Guardrails y BYOK (Bring Your Own Key)

El Copiloto de IA asiste en la propuesta de transformaciones con máximas garantías:

- **Modo BYOK**: El usuario puede configurar su propia clave `GEMINI_API_KEY` desde la interfaz, almacenada únicamente en su navegador (`localStorage`). La clave viaja al backend por cabecera HTTP (`x-goog-api-key`) y nunca se persiste ni se registra en logs.
- **Modelo configurable**: El Copiloto usa por defecto `gemini-2.5-flash`, configurable mediante la variable de entorno `GEMINI_MODEL`.
- **Modo Determinista Gratuito**: Si no se dispone de API Key, el motor de reglas heurístico opera al 100% de capacidad sin coste.
- **Minimización de Datos (RGPD)**: **Nunca se envía el dataset completo al LLM**. Solamente se envía el esquema, estadísticas descriptivas, conteo de nulos y 3 filas de muestra con **PII enmascarada**.
- **Filtrado por Registro (Guardrails)**: Cualquier operación propuesta por la IA que no esté en el catálogo permitido es descartada automáticamente y **queda registrada como warning visible** en el plan de transformación.

### 💼 Datasets Demostrativos Incluidos

En el selector de demo de 1 clic o en el directorio [`data_samples/`](./data_samples) se incluyen:

| Dataset | Archivo | Contenido |
| :--- | :--- | :--- |
| Contact Center & Operaciones | `contact_center_corrupted.csv` | KPIs de Contact Center (AHT, Conversión, Score de Calidad, Absentismo) con marcadores N/D, AHTs negativos y fechas `DD/MM/AAAA`. |
| Ventas & Comercial | `sales_sample_corrupted.csv` | Transacciones comerciales con precios formateados como texto (`1200.50 €`, `$350.00`), fechas mezcladas, espacios y filas duplicadas. |
| People Analytics & RRHH | `people_analytics_corrupted.csv` | Datos de RRHH con salarios multimoneda (`€`/`$`), absentismo negativo (`-3`), productividad > 100% (`112%`) y fila vacía corrupta. |

---

## ⚙️ Instalación

### Requisitos Previos

- **Python 3.11+**
- **Node.js 18+** (recomendado Node 20 para Docker)
- *(Opcional)* Docker y Docker Compose

### 1. Clonar el repositorio

```bash
git clone https://github.com/migueljerico/dataflow-ai.git
cd dataflow-ai
```

### 2. Ejecutar Backend (FastAPI)

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

La API Swagger interactiva quedará disponible en: `http://localhost:8000/docs`.

### 3. Ejecutar Tests Automatizados (Pytest)

```bash
cd backend
pytest
```

El resultado esperado es **23 tests unitarios, de integración y de gobierno — 100% en verde**. Cada test ejecuta aislado sobre un directorio temporal, sin dejar residuos en `uploads/`.

### 4. Ejecutar Frontend (React + Vite + TypeScript)

En una terminal aparte:

```bash
cd frontend
npm install
npm run dev
```

La aplicación web estará disponible en: `http://localhost:3000`.

### 5. Ejecución con Docker Compose (opcional)

Desde la raíz del repositorio:

```bash
docker compose up --build
```

Esto levanta:

- **Backend** expuesto en el puerto `8000`.
- **Frontend** servido por Nginx en el puerto `3000`, con proxy `/api` hacia el backend sobre el mismo origen.

---

## 🚀 Uso

### Flujo interactivo desde la UI

1. Abre `http://localhost:3000`.
2. Sube un archivo CSV/XLSX o selecciona un dataset demo de 1 clic.
3. Revisa el **Data Profiling** y el **Data Quality Score** con sus 5 dimensiones.
4. Pulsa **Generar Plan** (motor de reglas determinista o Copiloto IA).
5. Revisa, aprueba o rechaza cada paso del plan (Human-in-the-Loop).
6. Ejecuta el plan y consulta el **Business Analytics**, la comparativa Antes vs Después, descarga el dataset limpio o el script reproducible `.py`.

### Ejemplos de uso con la API REST

#### Subir un dataset

```bash
curl -X POST http://localhost:8000/api/v1/datasets/upload \
  -F "file=@data_samples/sales_sample_corrupted.csv"
```

#### Listar datasets demo

```bash
curl http://localhost:8000/api/v1/datasets/samples
```

#### Cargar un dataset demo de 1 clic

```bash
curl -X POST http://localhost:8000/api/v1/datasets/samples/sales/load
```

#### Obtener profiling y calidad

```bash
curl http://localhost:8000/api/v1/datasets/{dataset_id}/profiling
curl http://localhost:8000/api/v1/datasets/{dataset_id}/quality
```

#### Proponer un plan de transformaciones (reglas deterministas)

```bash
curl -X POST http://localhost:8000/api/v1/plans/propose \
  -H "Content-Type: application/json" \
  -d '{"dataset_id":"TU_DATASET_ID"}'
```

#### Proponer un plan asistido por Copiloto IA (Gemini)

```bash
curl -X POST http://localhost:8000/api/v1/plans/propose/ai \
  -H "Content-Type: application/json" \
  -H "X-Gemini-Api-Key: TU_API_KEY" \
  -d '{"dataset_id":"TU_DATASET_ID","provider":"gemini"}'
```

#### Aprobar y ejecutar un plan ETL

```bash
curl -X POST http://localhost:8000/api/v1/plans/{plan_id}/approve \
  -H "Content-Type: application/json" \
  -d '{"steps":[...]}'
```

#### Consultar Business Analytics de una ejecución

```bash
curl http://localhost:8000/api/v1/analytics/{run_id}
```

#### Descargar dataset limpio y script reproducible

```bash
curl -o clean_dataset.csv http://localhost:8000/api/v1/runs/{run_id}/download
curl -o pipeline.py http://localhost:8000/api/v1/runs/{run_id}/script
```

---

## 📁 Estructura del proyecto

```text
dataflow-ai/
├── .github/
│   └── workflows/
│       └── ci.yml                     # CI/GitHub Actions: tests backend + build frontend
├── backend/
│   ├── app/
│   │   ├── ai_providers/
│   │   │   ├── base.py                # Contratos del LLMProvider y modelos de respuesta
│   │   │   ├── gemini_provider.py     # Integración con Google Gemini (BYOK, cabecera x-goog-api-key)
│   │   │   └── mock_provider.py       # Motor heurístico gratuito (sin API Key)
│   │   ├── api/v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── analytics.py       # Endpoint de Business Analytics
│   │   │   │   ├── datasets.py        # Carga, listado y muestras demo
│   │   │   │   ├── plans.py           # Propuesta, revisión y ejecución de planes ETL
│   │   │   │   ├── profiling.py       # Data Profiling automático
│   │   │   │   ├── quality.py         # Data Quality Score explicable
│   │   │   │   └── runs.py            # Resultados, comparativas, descargas y scripts
│   │   │   └── router.py              # Router principal /api/v1
│   │   ├── core/
│   │   │   ├── config.py              # Settings, CORS, límites de archivo
│   │   │   ├── exceptions.py          # Excepciones funcionales y handler global
│   │   │   └── number_parsing.py      # Parseo numérico europeo/americano centralizado
│   │   ├── models/
│   │   │   ├── analytics.py           # Modelos Pydantic de KPIs y reporte ejecutivo
│   │   │   ├── dataset.py             # DatasetMetadata, estados, file types
│   │   │   ├── etl.py                 # TransformationPlan, Steps, ExecutionResult
│   │   │   ├── profiling.py           # ColumnProfile, SemanticHints
│   │   │   └── quality.py             # QualityReport, QualityScore, Issues
│   │   ├── services/
│   │   │   ├── ai_service.py          # Servicio IA, guardrails y anonimización PII
│   │   │   ├── analytics_service.py   # KPIs ejecutivos por dominio con pandas
│   │   │   ├── dataset_service.py     # Validación, limpieza y caché de datasets
│   │   │   ├── etl_service.py         # Motor ETL determinista y auditoría
│   │   │   ├── profiler_service.py    # Profiling y detección semántica
│   │   │   ├── quality_service.py     # Evaluación de calidad en 5 dimensiones
│   │   │   └── script_generator.py    # Generador de script .py reproducible
│   │   ├── transformations/
│   │   │   ├── base.py                # Contrato BaseTransformation
│   │   │   ├── datetime_ops.py        # convert_datetime
│   │   │   ├── missing_ops.py         # fill_missing, remove_duplicates, rename, drop
│   │   │   ├── numeric_ops.py         # convert_numeric, round, clamp
│   │   │   ├── registry.py            # Registro estricto de transformaciones
│   │   │   └── text_ops.py            # trim_text, normalize_case, normalize_category
│   │   └── main.py                    # FastAPI app, CORS, SPA, healthcheck
│   ├── tests/
│   │   ├── conftest.py                # Aislamiento de tests (dir temporal + cachés limpias)
│   │   ├── test_ai_privacy.py         # Privacidad PII y minimización RGPD
│   │   ├── test_ai_provider.py        # Generación de planes IA
│   │   ├── test_analytics.py          # Business Analytics end-to-end
│   │   ├── test_dataset_upload.py     # Carga y validación de archivos
│   │   ├

<p align="center">Creado por <a href="https://github.com/migueljerico">@migueljerico</a> y documentado por QwenCloud (deepseek-v4-pro-0813) desde la App Asistente de IA · 2026</p>