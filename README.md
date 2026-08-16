# 🚀 DataFlow AI

**From raw business data to clean, trusted and actionable insights.**

> ⚠️ **Versión Piloto / MVP (En desarrollo activo)**  
> *Un copiloto inteligente y gobernado para preparación, calidad, transformación y análisis de datos empresariales.*

---

## 📌 1. Problema Empresarial

Las empresas reciben diariamente datos desordenados e inconsistentes procedentes de múltiples plataformas (CRMs, ERPs, Contact Centers, sistemas de RRHH, exportaciones de terceros). Estos datos presentan habitualmente:
- **Filas vacías o malformadas** (`,,,,,,,`).
- **Registros duplicados** que distorsionan los conteos de clientes o empleados.
- **Formatos de fecha heterogéneos** (`2026-01-05` vs `06/01/2026` vs `07-01-2026`).
- **Números almacenados como cadenas de texto** con símbolos (`1.200,50 €`, `$350.00`, `14.1%`) o marcadores como `"N/D"` / `"N/A"`.
- **Inconsistencias de formato en texto** (`Madrid`, `MADRID`, `madrid `) y rotura de acrónimos (`SOPORTE SA` $\rightarrow$ `Soporte Sa`).
- **Violaciones de reglas de negocio** (absentismos negativos que cancelan el absentismo real de otros empleados, productividades superiores al 100%).

Antes de poder construir reportes de Business Intelligence (BI) o modelos analíticos fiables en Power BI, estos problemas requieren horas de trabajo manual repetitivo. **DataFlow AI** automatiza y gobierna este proceso.

---

## 💡 2. Solución y Principio Fundamental

DataFlow AI sigue un principio estricto de gobierno de datos:

> **"La IA propone. El usuario decide. Python ejecuta."**

La IA nunca ejecuta código arbitrario ni modifica directamente los datos sin supervisión. La plataforma realiza la manipulación de datos a través de un **motor ETL determinista** escrito en Python/pandas sobre un catálogo estricto de transformaciones validadas con **auditoría de validación explícita**.

### Flujo de Trabajo:
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

## 📊 3. Modelo de Data Quality Score (Lenguaje de Negocio Natural)

La calidad del dataset se evalúa mediante una fórmula ponderada explicable basada en **5 dimensiones**:

$$\text{Quality Score} = (0.30 \times C) + (0.25 \times V) + (0.20 \times K) + (0.15 \times U) + (0.10 \times I)$$

| Dimensión | Ponderación | Descripción de Negocio |
| :--- | :---: | :--- |
| **Datos Completos ($C$)** | **30%** | Medición de campos sin valores nulos ni vacíos. |
| **Formatos Válidos ($V$)** | **25%** | Verificación de que fechas, números y tipos cumplan con el formato esperado. |
| **Formato Homogéneo ($K$)** | **20%** | Detección de espacios sobrantes y variaciones de mayúsculas/minúsculas (preservando siglas como SA, SL). |
| **Registros Únicos ($U$)** | **15%** | Identificación de registros y filas duplicadas exactas. |
| **Reglas de Negocio ($I$)** | **10%** | Comprobación de límites lógicos (e.g. Absentismo $\ge 0$, Productividad $\le 100\%$). |

---

## 🛠️ 4. Catálogo de Transformaciones ETL Controladas

Toda modificación sobre los datos utiliza operaciones estrictas del `TransformationRegistry`:
- `trim_text`: Limpieza de espacios iniciales, finales y dobles espacios internos.
- `normalize_case`: Estandarización a Title Case preservando siglas corporativas de negocio (`SA`, `SL`, `SLU`, `KPI`).
- `convert_datetime`: Conversión de cadenas a formato estandarizado ISO 8601 (`%Y-%m-%d`) respetando formatos europeos `DD/MM/AAAA` sin inversión de día/mes.
- `convert_numeric`: Eliminación de símbolos (`$`, `€`, `%`) y marcadores de texto (`N/D`, `N/A`) con **soporte de separadores europeos y americanos** (`1.200,50 €` → `1200.50`, `$1,234.56` → `1234.56`), tipando la columna a `float64` para Power BI.
- `clamp_range`: Acotación de valores negativos o fuera de rango lógico (`min_value`, `max_value`).
- `round_numeric`: Redondeo numérico a $N$ decimales.
- `fill_missing`: Imputación de valores faltantes por constante, media, mediana o moda.
- `remove_duplicates`: Eliminación de filas duplicadas exactas o por clave candidata.
- `rename_column`: Renombrado seguro de columnas.
- `drop_column`: Eliminación de columnas no deseadas.
- `normalize_category`: Reemplazo basado en diccionarios de mapeos explícitos.

---

## 📈 5. Módulo de Business Analytics & Executive Insights

Una vez transformados los datos, DataFlow AI calcula en tiempo real con `pandas`:
- **KPIs Operativos Clave por Dominio**:
  - **RRHH / People Analytics**: Plantilla activa, salario medio, productividad media acotada y absentismo total acumulado.
  - **Ventas & Retail**: Facturación total neta, ticket medio y unidades vendidas.
  - **Contact Center**: Total llamadas, AHT medio operativo y CSAT/Score de calidad medio.
- **Distribución Categórica**: Desglose por departamento, canal o agente.
- **Resumen Ejecutivo de Negocio**: Informe estructurado para Dirección destacando el impacto de la calidad de datos y recomendaciones operativas.

---

## 🤖 6. Rol de la IA, Guardrails y BYOK (Bring Your Own Key)

El Copiloto de IA asiste en la propuesta de transformaciones con máximas garantías:
- **Modo BYOK**: El usuario puede configurar su propia clave `GEMINI_API_KEY` desde la interfaz, almacenada únicamente en su navegador (`localStorage`). La clave viaja al backend por cabecera HTTP (`x-goog-api-key`) y nunca se persiste ni se registra en logs.
- **Modelo configurable**: El Copiloto usa por defecto `gemini-2.5-flash`, configurable mediante la variable de entorno `GEMINI_MODEL`.
- **Modo Determinista Gratuito**: Si no se dispone de API Key, el motor de reglas heurístico opera al 100% de capacidad sin coste.
- **Minimización de Datos (RGPD)**: **Nunca se envía el dataset completo al LLM**. Solamente se envía el esquema, estadísticas descriptivas, conteo de nulos y 3 filas de muestra con **PII enmascarada** (nombres, emails y teléfonos se sustituyen por `[NOMBRE]` / `[EMAIL]` / `[TELÉFONO]`).
- **Filtrado por Registro (Guardrails)**: Cualquier operación propuesta por la IA que no esté en el catálogo permitido es descartada automáticamente y **queda registrada como warning visible** en el plan de transformación (transparencia total del guardrail).

---

## 💼 7. Datasets Demostrativos Incluidos

En el selector de demo de 1 clic o en el directorio [`data_samples/`](file:///d:/DataFlow%20Project/data_samples) se incluyen:
1. `contact_center_corrupted.csv`: KPIs de Contact Center (AHT, Conversión, Score de Calidad, Absentismo) con marcadores N/D, AHTs negativos y fechas `DD/MM/AAAA`.
2. `sales_sample_corrupted.csv`: Transacciones comerciales con precios formateados como texto (`1200.50 €`, `$350.00`), fechas mezcladas, espacios y filas duplicadas.
3. `people_analytics_corrupted.csv`: Datos de RRHH con salarios multimoneda (`€`/`$`), absentismo negativo (`-3`), productividad > 100% (`112%`) y fila vacía corrupta.

---

## ⚡ 8. Guía de Ejecución Local y Pruebas

### Requisitos Previos:
- Python 3.11+
- Node.js 18+

### 1. Ejecutar Backend (FastAPI):
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # En Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
*API Swagger interactiva:* `http://localhost:8000/docs`

### 2. Ejecutar Tests Automatizados (Pytest):
```bash
cd backend
pytest
```
*(23 tests unitarios, de integración y de gobierno — 100% en verde. Cada test ejecuta aislado sobre un directorio temporal, sin dejar residuos en `uploads/`.)*

### 3. Ejecutar Frontend (React + Vite + TypeScript):
```bash
cd frontend
npm install
npm run dev
```
*Aplicación web disponible en:* `http://localhost:3000`

---

## ☁️ 9. Roadmap de Despliegue CI/CD

- [x] Motor ETL determinista y catálogo de 11 transformaciones.
- [x] Motor de Data Quality explicable (5 dimensiones).
- [x] Módulo de Business Analytics & Executive Insights.
- [x] Soporte BYOK para Google Gemini AI Copilot (modelo `gemini-2.5-flash` configurable vía `GEMINI_MODEL`, clave por cabecera `x-goog-api-key`).
- [x] Selector interactivo de datasets demo de 1 clic.
- [x] Parseo numérico centralizado con separadores europeos (`1.200,50`) y americanos (`1,234.56`).
- [x] Gobierno estricto de planes: 404 explícito ante planes inexistentes (sin ejecuciones silenciosas contra datasets arbitrarios).
- [x] Anonimización PII de las muestras enviadas al LLM y guardrails transparentes con warnings en el plan.
- [x] CORS configurable por entorno (`BACKEND_CORS_ORIGINS`) y proxy nginx `/api` para despliegue Docker de un solo origen.
- [ ] Pipeline CI/CD en GitHub Actions (`.github/workflows/deploy.yml`).
- [ ] Despliegue automatizado en Google Cloud Run.

---

## 👨‍💻 10. Perfil Profesional del Autor

Este proyecto ha sido diseñado e implementado por un profesional con **15 años de trayectoria en operaciones, liderazgo de equipos (hasta 150 personas), KPIs, SLAs y gestión de productividad**, en transición hacia **Data Analytics, Business Intelligence e IA aplicada al negocio**.

Refleja una mentalidad fuertemente enfocada a resolver problemas empresariales reales mediante soluciones analíticas reproducibles, gobernadas y eficientes.

---

## 🤖 11. Ingeniería Asistida por IA (Historia de Desarrollo)

Este proyecto es también un ejemplo real de desarrollo humano + agentes de IA en dos fases:

| Fase | Herramienta | Modelo | Alcance |
| :--- | :--- | :--- | :--- |
| **1. Lanzamiento inicial (MVP v0.1.0)** | Google Antigravity | Gemini Flash 3.7 | Arquitectura completa del piloto: motor ETL determinista, catálogo de 11 transformaciones, Data Quality Score de 5 dimensiones, Business Analytics, frontend React y suite inicial de 15 tests. |
| **2. Endurecimiento (v0.2.0)** | ZCode | **GLM-5.3** | Revisión técnica completa y correcciones: parseo de números europeos, eliminación de fallbacks silenciosos, migración del proveedor Gemini, anonimización PII, higiene de tests y preparación para despliegue. |

### Mejoras implementadas por GLM-5.3 (ZCode) sobre el MVP inicial:

1. **Parseo numérico europeo**: `convert_numeric` ahora conserva el valor real de importes como `1.200,50 €` (antes se perdían silenciosamente como `NaN`), con un módulo de parseo centralizado (`app/core/number_parsing.py`) usado por profiling, quality, ETL y auditoría.
2. **Gobierno estricto de planes**: los planes inexistentes devuelven `404 PLAN_NOT_FOUND` en lugar de ejecutarse de forma resiliente contra un dataset arbitrario — nunca se transforma un archivo sin trazabilidad de su plan.
3. **Guardrails transparentes**: las operaciones IA descartadas por el catálogo quedan registradas como warnings visibles en el plan (frontend incluido), en lugar de descartarse silenciosamente.
4. **Proveedor Gemini modernizado**: modelo `gemini-2.5-flash` (configurable vía `GEMINI_MODEL`), API Key por cabecera en lugar de URL, y manejo robusto de respuestas vacías, bloqueadas por filtros de seguridad o JSON inválido.
5. **Privacidad BYOK reforzada**: las 3 filas de muestra enviadas al LLM viajan con PII enmascarada (`[NOMBRE]` / `[EMAIL]` / `[TELÉFONO]`), haciendo efectiva la minimización RGPD documentada.
6. **Compatibilidad pandas 3**: corrección de la semántica de `astype(str)` con missing values y conteos de auditoría NaN-safe.
7. **Higiene de tests**: suite aislada por test (directorio temporal + caches limpias vía `conftest.py`), 8 tests nuevos (23 en total) y eliminación de ~400 archivos residuales acumulados en `uploads/`.
8. **Preparación para despliegue**: CORS configurable por entorno (`BACKEND_CORS_ORIGINS`), proxy nginx `/api` para el `docker-compose` end-to-end, `datetime` timezone-aware y licencia MIT.
