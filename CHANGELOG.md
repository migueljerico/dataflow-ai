# Changelog — DataFlow AI

Todas las modificaciones notables de este proyecto se documentan en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y este proyecto sigue el [Versionado Semántico](https://semver.org/lang/es/).

## [1.19.0] — 2026-09-05

### 🌟 Soporte Multiarchivo, Generador Visual de Esquema de Estrella & Corrección Forense de Calidad

> **Motivación:** Resolución completa de la auditoría forense sobre el pipeline de calidad y transformación en DataFlow AI, eliminando falsos 100% de Data Score, erradicando fallbacks numéricos simulados, preservando tipos de datos enteros en transformaciones numéricas y dotando a la aplicación de la capacidad de procesamiento multiarchivo para la construcción y auditoría automática de modelos relacionales en Esquema de Estrella con exportación Power BI TMDL.

#### 🔴 Correcciones Forenses de Calidad y Detección Real
- **Eliminación de falsos scores 100% (`semantics.py`, `quality_service.py`):** Corregida la invalidación indebida del tipo semántico `FRACTION` ante valores anómalos (`-3`, `1.2` en `Discount`), garantizando la detección honesta de valores fuera de rango y limitando las dimensiones con incidencias abiertas a 99.9% sin redondear falsamente a 100%.
- **Erradicación de números simulados (`runs.py`, `etl_service.py`):** Eliminadas todas las constantes arbitrarias (`80.0`, `98.0`, `18.0`) en favor de cálculos reales y transparentes de score antes y después de la ejecución.
- **Preservación estricta de tipos enteros (`numeric_ops.py`):** Las transformaciones de conversión y acotado numérico (`clamp_range`, `convert_numeric`) preservan tipos `int`/`Int64` cuando no existen decimales reales, impidiendo la mutación de campos enteros como `Quantity: 6` a `6.0`.
- **Verificación de consistencia geográfica:** Detección de mezclas de países y códigos (`ES`, `España`, `SPAIN` vs `Spain`).

#### 🌟 Nuevo Módulo: Subida Multiarchivo y Generador de Esquema de Estrella
- **Subida por lotes atómica (`POST /api/v1/datasets/upload-batch`):** Carga simultánea de múltiples archivos CSV/Excel con autodetección de codificación y delimitador.
- **Motor Relacional (`relational_service.py`):** Inferencia automática de Tabla de Hechos (Fact Table) y Tablas de Dimensiones, detección de claves foráneas, auditoría de integridad referencial fila por fila con cuantificación de registros huérfanos y generación de definiciones Power BI TMDL y medidas DAX. Carga automática de versiones limpias post-ETL.
- **Visualizador Interactivo SVG (`MultiTableStarSchema.tsx`):** Diagrama radial de hechos y dimensiones con insignias de cardinalidad (`1:*`), porcentaje de integridad, copiado de fórmulas DAX y exportación en PNG 2x Retina.
- **Espacio de Trabajo Multi-Tabla (`App.tsx`):** Barra superior de navegación para alternar entre el modelo relacional global y el flujo de limpieza y calidad por tabla individual.

#### 🧪 Tests y Verificación
- **Backend:** 267 tests pasando al 100% (`pytest`), incluyendo `test_relational_star_schema.py`.
- **Frontend:** 55 tests pasando al 100% (`vitest`) y build estricto TypeScript/Vite completado con éxito.
- **Linters:** Ruff, Black y Bandit SAST limpios.

## [1.18.0] — 2026-09-05

### 🧹 Planes con correcciones ejecutables: sube un archivo sucio, aprueba el plan con el botón y descarga el limpio para Power BI

> **Motivación:** verificación E2E con los 8 CSV reales de Northwind Dirty (`D:/Downloads/Northwind_Dirty_Enterprise`) tras v1.17.0: los archivos aparecían con **Data Score 100 y 0 pasos** (flujo sin salida) o con pasos `flag_for_review` que no modificaban datos. Esta release restaura el contrato **"la IA propone la corrección, el humano decide con el botón, Python ejecuta"**, verificada fila a fila contra los datasets reales.

#### 🔴 Causas raíz corregidas
- **P0 — Falso Data Score 100 (`quality_service.py`):** la dilución por volumen (10 celdas malas en 6.500 filas → integridad 99,85) y el redondeo a 1 decimal presentaban como 100.0 datasets con incidencias. Ahora un dataset con `issues_count > 0` nunca se muestra como 100 (tope 99,9): `order_details_dirty` pasa de 100.0 falso a 99.9 con plan real.
- **P0 — Bug `dayfirst=True` (v1.9.0, validación de fechas):** con pandas 3.x, `pd.to_datetime(dayfirst=True)` **intercambiaba mes/día** de las fechas ISO (`2024-03-12 → 3 de diciembre`) e invalidaba en bloque las de día > 12: 1.071 de 1.800 `OrderDate` y 552 de 912 `Date` eran issues falsos. Nueva validación consciente de formato **sobre valores únicos** (rápida: 100k filas por debajo del umbral de rendimiento) con doble interpretación ISO/europea: un valor solo es inválido si falla en ambas. La mezcla ISO + europeo en una misma columna se detecta como heterogeneidad a estandarizar (`convert_datetime`).
- **P0 — Keywords solo en español:** `Quantity`, `UnitPrice` no disparaban la regla de magnitudes positivas (solo `cantidad`, `precio`...). Listas bilingües (`quantity`, `qty`, `price`, `cost`, `amount`, `revenue`, `sales`, `units`): las 18 cantidades negativas de `order_details_dirty` ahora se detectan.
- **P0 — Callejón sin salida con plan vacío (`PlanReview.tsx`):** con 0 pasos el botón quedaba deshabilitado sin salida. Nuevo panel "Dataset sin incidencias: ya está limpio" + botón **"Generar archivo limpio para Power BI"** (ejecuta el plan vacío y deja el CSV/Parquet descargable). i18n completa en los 13 idiomas.

#### ✨ Política v1.18.0: corrección ejecutable propuesta, aprobación por botón
- **`transformation_policy.py`:** `negative_policy` propone `clamp_range` (min=0) y `fraction_policy` propone `clamp_range` [0.0, 1.0]; `missing_policy` propone `fill_missing` (mediana en numéricas, moda en categóricas de baja cardinalidad) y mantiene `flag_for_review` + NULL solo para lo no inferible (id/email/phone, texto de alta cardinalidad). Jamás se propone el constante "Desconocido"; **nada se ejecuta sin la aprobación humana del plan** (pulsar el botón).
- **`etl_service.py` + `mock_provider.py`:** las dos vías de propuesta (reglas y IA mock) construyen pasos ejecutables con las políticas centrales; el mock añade además la rama de nulos por tipo (numérica → mediana, categórica → moda).
- **Resultado verificado E2E (score antes → después):** `order_details` 99.9 → 100.0 (cantidades ≥ 0, descuentos ≤ 1, sin nulos), `products` 97.0 → 100.0 (precios limpios de "€ ," y negativos), `orders` 99.9 → 100.0 (países canónicos, `Status` imputado, fechas ISO), `customers` 99.0 → 99.8 (emails NULL preservados a propósito; IDs intactos).

#### 🧪 Tests
- **Contrato actualizado (12 tests):** `test_semantic_policy_regression.py` (negativos/fracciones proponen clamp aprobable; nulos por tipo), `test_etl.py` (auditoría de clamp y corrección real), `test_european_numbers.py`, `test_analytics.py` (KPI absentismo 3 días tras clamp), sin cambiar umbrales ni gobernanza. Suite **265 backend + 55 frontend en verde**; ruff, black, bandit y build TS estricto limpios.


## [1.17.1] — 2026-09-04

### 🔧 Parche CI: tests Northwind autocontenidos

- **Causa:** los 5 tests de regresión Northwind leían `D:/Downloads/Northwind_Dirty_Enterprise/*.csv`, inexistente en el runner de GitHub Actions → 5 `FileNotFoundError` y CI en rojo.
- **Solución:** réplicas sintéticas autocontenidas en `test_semantic_policy_regression.py` con los mismos patrones (8 negativos, 20/25 nulos, 18 cantidades negativas, 10 descuentos >1, países ES/España, IDs CamelCase). Sin cambios de motor; suite 265 + 55 en verde y CI de nuevo en verde.

## [1.17.0] — 2026-09-04

### 🧠 Motor Semántico de Calidad: la semántica gobierna las propuestas (Human-in-the-Loop reforzado)

> **Madurez & Evidencia:** Release centrada en corregir las 8 causas raíz detectadas por auditoría cruzada (Claude Sonnet 5 + ChatGPT + verificación propia con pandas) sobre el Northwind Dirty real: IDs CamelCase no detectados, reglas que ignoraban el `semantic_hint`, nulos imputados a "Desconocido", negativos corregidos a 0, `Discount` sin semántica, países por casing y DAX con nombres recapitalizados. 41 tests nuevos de regresión (`test_semantic_policy_regression.py`); 6 tests existentes actualizados al nuevo contrato; suite 265 backend + 55 frontend en verde; linters y SAST limpios; build verificado.

#### 🔴 Causas raíz corregidas
- **P1 — Detector de IDs (`backend/app/core/semantics.py`):** `_looks_like_id_name()` reconoce `CustomerID/ProductID/OrderID/EmployeeID/CategoryID/OrderDetailID` y variantes (`customerID`, `CUSTOMER_ID`, `InvoiceID`...) sin depender del guion bajo; con salvaguarda anti-falsos-positivos (`Valid` no es ID). `CUST0001 → CUST0001` (antes `Cust0001`).
- **P2 — Política semántica central (`backend/app/core/transformation_policy.py`, nuevo):** `casing_policy/missing_policy/negative_policy/fraction_policy` + `country_mappings()` gobiernan `ETLService`, `MockProvider`, guardrails de `AIService` y prompt de Gemini. `ID/PHONE/DATE` nunca reciben `normalize_case`; `EMAIL` solo admite `lower`.
- **P3 — Nulos (`etl_service.py`):** fin del fallback universal a `"Desconocido"`; toda columna con nulos propone `flag_for_review` (mantener NULL + estrategia sugerida) salvo decisión humana explícita.
- **P4 — Negativos (`etl_service.py`, `quality_service.py`, `mock_provider.py`):** fin del `clamp_range → 0` automático; `flag_for_review` con contexto `negative_values`. Los porcentajes `[0, 100]` sí se siguen acotando.
- **P5 — Descuentos (`semantics.py`, `profiling.py`, `quality_service.py`):** nuevo `SemanticHintEnum.FRACTION`; `Discount/Descuento` validados en `[0, 1]` (1.20 y 1.4876 detectados) sin confundirlos con `Descuento_Pct` (porcentaje `[0, 100]`).
- **P6 — Países (`etl_service.py` + `transformation_policy.py`):** `normalize_category` con diccionario extensible (`ES/España/SPAIN/spain → Spain`, `FR/Francia → France`...), ejecutado ANTES que `normalize_case` para no perder la equivalencia.
- **P7/P8 — DAX (`analytics_service.py`):** `table_name` fiel al nombre real del modelo (`clean_products_dirty`, sin recapitalizar); medidas numéricas solo sobre columnas numéricas reales, `TOTALYTD` solo con fecha válida, avisos explícitos en lugar de DAX roto.
- **Nueva operación `flag_for_review` (`transformations/review_ops.py`):** marcaje auditable sin modificar datos, con soporte en `script_generator.py`, auditoría de `execute_plan` y tipo `fraction` en el frontend.

#### 🧪 Tests
- **Nuevos (41):** `backend/tests/test_semantic_policy_regression.py` — IDs, emails, nulos, negativos, porcentajes, fracciones, países, DAX y regresión Northwind Dirty real (products/customers/orders/details + integridad referencial).
- **Actualizados (6):** `test_etl.py`, `test_analytics.py`, `test_performance_large_dataset.py`, `test_european_numbers.py`, `test_governance_hardening.py` (manifiesto 15 → 16 ops) al nuevo contrato de revisión humana.

## [1.16.0] — 2026-09-03

### 📑 Reportes Ejecutivos Programados (PDF/HTML) con Webhooks de Drift + 🧪 Simulador de Drift Hipotético + 🔏 Gobernanza de Aprobación Reforzada

> **Madurez & Evidencia:** Release centrada en cerrar el hueco de gobernanza detectado en la revisión externa del endpoint de aprobación (diff canónico + auditoría explícita), corregir la corrupción de casing de `split_column` sobre el dataset real (`DevOps`→`Devops`, `HR`→`Hr`) y entregar las dos evoluciones priorizadas: exportación programada de reportes ejecutivos con notificaciones webhook por drift crítico, y simulación interactiva de transformaciones hipotéticas sobre los percentiles de drift antes de la aprobación formal.

#### 🐛 Correcciones (Fixes)
- **Casing inteligente compartido (`backend/app/transformations/casing.py`, nuevo):** Fuente única de verdad para `normalize_case` y `split_column`. Preserva siglas registradas (`HR`, `SLU`, `KPI`), códigos con dígitos (`PED-201`) y camelCase (`DevOps`, `PowerBI`); los compuestos con guion (`HR-California`, `HR-New`) se procesan por segmento. Corrige el bug de v1.15.2 donde `.title()` crudo corrompía 12 de los 36 valores reales de `Department_Region` (`Devops`, `Hr`).
- **Fidelidad motor ↔ script reproducible (`backend/app/services/script_generator.py`):** El script generado emite el mismo casing inteligente que el motor (antes usaba `.str.title()`, divergente) y replica la semántica exacta de `split_column` (NaN → nulo, valor sin separador → segunda columna nula). Verificado con compile+exec y comparación fila a fila.
- **Analytics robusto ante booleanos (`backend/app/services/analytics_service.py`):** Las columnas booleanas reales (ej. `Remote_Work`) se excluyen de boxplots/clustering; `np.quantile` fallaba con `TypeError: numpy boolean subtract` (bug latente que rompía `/analytics/{run_id}` y cualquier reporte PDF/HTML con datasets que contuvieran booleanos).

#### 🔏 Gobernanza de Aprobación Reforzada (P0 de la revisión externa)
- **Reconciliación canónica (`ETLService.reconcile_reviewed_steps`):** `/plans/{id}/approve` ya no ejecuta ciegamente los pasos del cliente: contrasta cada `step_id` contra la copia canónica del plan (fingerprint MD5 auditado), ejecuta la copia del servidor cuando el contenido es idéntico, marca `EDITED` + `[MODIFICADO POR HUMANO]` con diff explícito (operation/column/parameters) cuando diverge, registra `[AÑADIDO POR HUMANO]` para pasos fuera del plan (validados igualmente por `TransformationRegistry`), `[OMITIDO]` para pasos ausentes, rechaza `step_id` duplicados (`400 DUPLICATE_STEP`) y fuerza el orden canónico de ejecución.

#### ✨ Ítem 1 — Reportes Ejecutivos Programados & Webhooks
- **`ReportService` (`backend/app/services/report_service.py`, nuevo):** Generación determinista de reportes ejecutivos en **PDF** (`fpdf2`, nueva dependencia) y HTML (resumen ejecutivo, KPIs, calidad antes/después por dimensión, drift por percentiles con alertas top-5 y recomendaciones), en español e inglés.
- **Exportación programada desatendida:** Alta de schedules por run (formato, intervalo 5-1440 min, idioma) con bucle `asyncio` en el lifespan de FastAPI, regeneración periódica persistida en storage y endpoint `run-now` + descarga del último reporte generado.
- **Webhooks con trigger de drift:** Notificación JSON (métricas de calidad, resumen de drift, top alertas, KPIs y reporte adjunto en base64) con trigger `always` o `critical_drift`. La URL se valida contra **SSRF en el alta y en cada envío** reutilizando `validate_and_resolve_url` + `PinnedAsyncHTTPTransport` (IP Pinning anti DNS-rebinding).
- **Endpoints (`/api/v1/reports`):** `GET /{run_id}/pdf`, `GET /{run_id}/html`, CRUD de `schedules`, `run-now`, `last-report` y `logs`.
- **Frontend (`ScheduledReportsPanel.tsx`):** Panel en el paso 4 con botones PDF/HTML, formulario de programación (formato, intervalo, trigger, webhook) y gestión de schedules (ejecutar ahora, último reporte, eliminar).

#### ✨ Ítem 2 — Simulación Interactiva de Drift Hipotética
- **`SimulationService` (`backend/app/services/simulation_service.py`, nuevo) + `POST /api/v1/simulations/drift`:** Aplica los pasos hipotéticos (máx. 50) sobre una copia efímera del dataset, validando cada paso contra el Registry, y devuelve el análisis de drift por percentiles (raw vs simulado) con resultado paso a paso. **No modifica el dataset, no crea ejecuciones ni alimenta el historial** (nota de gobernanza incluida en la respuesta).
- **Frontend (`DriftSimulator.tsx`):** Panel en la revisión del plan (paso 3) que simula en tiempo real los pasos no rechazados: estado global de drift, P50 antes→después, Δ por percentil (P05/P95/máx), errores de validación por paso y milisegundos de cálculo.

#### 🧪 Verificación
- **Dataset real:** `Messy_Employee_dataset.csv` (1020 filas) E2E vía API: `Department` = `['Admin', 'Cloud Tech', 'DevOps', 'Finance', 'HR', 'Sales']`, `Region` = 6 valores correctos (incluido `New York`), 0 nulos, PDF/HTML/analytics/simulación en verde.
- **Suite:** 224 backend (+53: casing 16, gobernanza 11, reportes 19, simulación 7) + 55 frontend (+8) + 3 E2E — 100% en verde. Ruff, Black y Bandit sin incidencias.

#### 🤖 Atribución del Modelo
- **Atribución del Modelo:** Qwen 3.8 Max (vía ZCode).

## [1.15.2] — 2026-09-03

### ✂️ División Automática de Columnas Compuestas: `Department_Region` → `Department` + `Region`

> **Modelado Dimensional:** Nueva transformación determinista `split_column` que divide columnas compuestas por un separador en dos dimensiones atómicas listas para Power BI (ej. `Sales-Florida` → `Sales` | `Florida`).

#### ✨ Nueva Transformación `split_column`
- **Nueva clase `SplitColumnTransformation` (`backend/app/transformations/split_ops.py`):**
  - Divide una columna por un separador (`-`, `_`, etc.) en dos columnas nuevas con `Title Case` por segmento y eliminación opcional de la original (`keep_original`).
  - Validación de columnas destino y prevención de colisiones con el esquema existente.
- **Registro y Catálogo (`backend/app/transformations/registry.py`):**
  - Nueva operación `split_column` disponible en `TransformationRegistry` y expuesta en el catálogo/manifest para la UI.
- **Generación de Script (`backend/app/services/script_generator.py`):**
  - Plantilla reproducible para `split_column` usando `str.split(n=1, expand=True)` con `Title` por parte.
- **Heurística de Proposición Automática (`backend/app/services/etl_service.py`):**
  - `Department_Region` (y variantes `dept_region`, `department-region`) se propone automáticamente como `split_column` con separador `-` → `Department` + `Region`, tras el resto de heurísticas y sin colisionar con columnas ya existentes.

#### 🧪 Verificación
- **Dataset Validado:** `Messy_Employee_dataset.csv` (1020 filas): `Department_Region` ahora se divide en `Department` (`Sales`, `Admin`…) y `Region` (`Florida`, `Nevada`…) con tipos `TEXT` correctos para modelo estrella en Power BI.
- **Suite:** 171 backend + 47 frontend en verde.

#### 🤖 Atribución del Modelo
- **Atribución del Modelo:** Gemini 3.8 Flash (High) (vía Google Antigravity).

## [1.15.1] — 2026-09-03

### 🛠️ Corrección del Motor Determinista: Crash de Parquet y Tipos Boolean para Datasets Corporativos

> **Estabilidad & Fidelidad:** Parche crítico que corrige el error interno 500 (ArrowInvalid) al procesar datasets corporativos con columnas booleanas (`Remote_Work` True/False), columnas compuestas con guion (`Department_Region`) y valores nulos numéricos (`Age`, `Salary`).

#### 🐛 Correcciones (Fixes)
- **Imputación de Nulos (`backend/app/services/etl_service.py`):**
  - Las columnas numéricas con valores perdidos (`Age` 211 nulos, `Salary` 24 nulos en Messy_Employee) ahora se imputan con estrategia `median` en lugar de la constante textual `Desconocido`. El valor `Desconocido` rompía el dtype float64 y provocaba `ArrowInvalid` al serializar a Parquet.
- **Profiling de Tipos (`backend/app/services/profiler_service.py`):**
  - Detección temprana de columnas booleanas (`bool` dtype o valores True/False, Sí/No, 1/0) antes de las reglas de ID y numérico. `Remote_Work` (513 True / 507 False) ya se clasifica como `BOOLEAN` y no como `NUMERIC`.
- **Motor de Calidad (`backend/app/services/quality_service.py`):**
  - Exclusión de columnas `BOOLEAN` y `PHONE` de los chequeos de validez cuantitativa e integridad (negativos, rangos). `Remote_Work` ya no genera un issue de validez con 1020 celdas y una sugerencia `convert_numeric` destructiva; `Phone` ya no recibe `clamp_range` a 0.
- **Motor de Reglas ETL (`backend/app/services/etl_service.py`):**
  - Guardrails en la heurística de `convert_numeric` y `clamp_range`: las candidatas `BOOLEAN`/`PHONE` se descartan aunque su ratio parseable sea bajo.
- **Normalización de Texto (`backend/app/transformations/text_ops.py`):**
  - `Department_Region` del tipo `Sales-Florida` (ambos lados palabras alfabéticas) ya no se trata como código identificador y no se convierte a `SALES-FLORIDA`. Ahora produce `Sales-Florida` con Title en cada segmento. Códigos cortos con dígitos (`PED-201`, `EMP-101`) siguen protegidos como `PED-201`.
- **Resiliencia de Parquet (`backend/app/services/etl_service.py`):**
  - `df.to_parquet()` ahora está envuelto en `try/except`: si la serialización columnar falla por tipos mixtos, el pipeline completa igual y reporta el incidente en `warnings` con el CSV limpio intacto. Nunca más un 500 interno por Parquet.

#### 🧪 Verificación
- **Dataset Afectado:** `Messy_Employee_dataset.csv` (1020 filas, 12 columnas) usado como caso de reproducción: 3 pasos deterministas (`median` en Age/Salary + `convert_datetime` en Join_Date), 0 errores, Parquet generado correctamente y `Department_Region` con `Sales-Florida` intacto.
- **Suite Completa:** 171 tests backend (pytest) y 47 frontend (Vitest) en verde; linters (Ruff/Black/Bandit) y build de Vite sin incidencias.

#### 🤖 Atribución del Modelo
- **Atribución del Modelo:** Gemini 3.8 Flash (High) (vía Google Antigravity).

## [1.15.0] — 2026-09-03

### 📊 Historial de Ejecuciones, Comparador Dimensional de Calidad, Control de Data Drift por Percentiles y Alertas Proactivas

> **Gobernanza & Control Estadístico:** Incorporación del historial cronológico de ejecuciones y comparador visual de calidad multidimensional entre versiones en la UI; motor determinista de detección de Data Drift y anomalías basado en percentiles ($P_{05}$ a $P_{95}$) y estadístico Kolmogorov-Smirnov sin dependencias pesadas; alertas visuales y recomendaciones proactivas en el dashboard de analítica; e integración de la captura real descargada del Esquema Estrella en la documentación.

#### 📜 Historial de Ejecuciones y Comparador de Versiones (UI & API)
- **Modelos de Calidad y Registro (`backend/app/models/quality.py`):**
  - Nuevos esquemas Pydantic `DimensionComparison`, `QualityComparisonReport` y `ExecutionSummaryItem`.
  - Estructuración de las 5 dimensiones fundamentales de calidad (Completitud, Validez, Consistencia, Unicidad, Integridad) con deltas numéricos, conteos de anomalías resueltas y explicación textual.
- **Servicio y Endpoints REST (`backend/app/services/etl_service.py`, `backend/app/api/v1/endpoints/runs.py`):**
  - `GET /api/v1/runs/`: Listado cronológico de ejecuciones filtrable por `dataset_id`.
  - `GET /api/v1/runs/compare?run_a={id}&run_b={id}`: Comparador bidireccional entre dos ejecuciones arbitrarias del histórico.
  - `GET /api/v1/runs/{run_id}/quality-comparison`: Comparativa de calidad detallada antes vs después de la ejecución.
  - Enriquecimiento de `GET /api/v1/runs/{run_id}/report` con `score_before`, `score_after` y `score_delta` calculados deterministamente.
- **Frontend Interactivo (`frontend/src/components/ExecutionHistoryModal.tsx`):**
  - Modal accesible con tabla de ejecuciones (Run ID, fecha, variación de filas, evolución de Quality Score, pasos aplicados y botones directos de descarga CSV, Parquet y Script).
  - Selector por radio buttons para comparar versión A vs versión B en vivo.
  - Panel comparativo con barras de evolución para cada una de las 5 dimensiones y delta global de calidad (+pts).
- **Integración en Reporte (`frontend/src/components/ExecutionReport.tsx`):**
  - Sustitución de valores estáticos de referencia por métricas reales calculadas por `QualityService` sobre el dataset limpio.
  - Tarjetas de evolución por dimensión y nuevo botón de acceso directo al modal de historial.

#### 📈 Control de Data Drift por Percentiles y Alertas Proactivas
- **Motor de Drift Determinista (`backend/app/services/drift_service.py`):**
  - Algoritmo de 2 muestras para el test Kolmogorov-Smirnov (`_compute_ks_statistic`) implementado directamente en NumPy vectorizado sin requerir dependencias externas pesadas como SciPy.
  - Cálculo de percentiles estadísticos ($P_{05}, P_{25}, P_{50}, P_{75}, P_{95}$), media, desviación estándar y Rango Intercuartílico (IQR).
  - Cálculo de desplazamiento de percentiles ($\Delta P$) respecto al dataset original crudo.
  - Clasificación determinista en estados `STABLE` (< 5% shift), `MODERATE` (5%-20%) y `CRITICAL` (> 20%).
  - Detección de anomalías en datos limpios basada en IQR y percentiles extremos.
  - Generador de recomendaciones proactivas accionables de gobernanza (`imputation_review`, `capping`, `segmentation`, `verified_stable`).
- **Dashboard de Analítica y Nueva Pestaña (`frontend/src/components/BusinessInsights.tsx`):**
  - Pestaña «Alertas & Data Drift» integrada en el panel directivo con contador de alertas.
  - Banner global de estado (Estable, Moderado, Crítico) con conteo de variables analizadas y alertas.
  - Tarjetas de recomendaciones proactivas categorizadas con botón de copia rápida al portapapeles.
  - Inspector interactivo con selector de variable, score de drift, KS stat, variación de mediana y anomalías.
  - Comparador detallado de los 5 percentiles (Crudo vs Limpio con tags de $\Delta \%$).
  - Tabla de estabilidad estadística completa para todas las variables numéricas.

#### 📸 Actualización de Captura del Esquema Estrella
- Sustitución de la imagen de vista previa del esquema estrella (`docs/capturas/captura_dataflow_ai_esquema_estrella.png`) con el archivo PNG real exportado directamente desde el visualizador interactivo del sistema (tabla de hechos de ventas, 6 dimensiones y relaciones `*:1`).

#### 🧪 Verificación Integral y Pruebas
- **Backend:** 171 pruebas unitarias y de integración pasando al 100% (+5 pruebas nuevas en `test_drift_service.py` y `test_runs_history_and_comparison.py`).
- **Frontend:** 47 pruebas con Vitest pasando al 100% (+2 pruebas nuevas en `ExecutionHistoryModal.test.tsx` y `BusinessInsights.test.tsx`).
- **Linters & SAST:** Ruff 0 errores, Black 0 diferencias de formato, Bandit 0 vulnerabilidades. Compilación estricta TypeScript + Vite en 1.34s sin errores.

#### 🤖 Atribución del Modelo
- **Atribución del Modelo:** Gemini 3.8 Flash (High) (vía Google Antigravity).

## [1.14.0] — 2026-09-03

### ⚡ Panel de Observabilidad de Caché Distribuida y Exportación PNG / TMDL para Power BI Desktop

> **Observabilidad & Power BI Real:** Incorporación de un panel interactivo de observabilidad de la caché de inferencia semántica de dos niveles (L1 memoria + L2 Redis) en el frontend, exportación directa en PNG de alta resolución (2x Retina) del diagrama interactivo de Esquema Estrella, y validación exhaustiva de las definiciones canónicas TMDL de tablas de dimensión y relaciones en el proyecto PBIP descargable.

#### ⚡ Observabilidad de Caché Distribuida (Frontend & Backend)
- **Endpoint REST (`backend/app/api/v1/endpoints/cache.py`):**
  - Nuevo endpoint `GET /api/v1/cache/stats` con modelo Pydantic `CacheStatsResponse`.
  - Desglose matemático explícito de aciertos L1 (memoria local <1ms) y L2 (Redis distribuido), tasas porcentuales independientes (`l1_hit_rate_pct`, `l2_hit_rate_pct`, `hit_rate_pct`), total de peticiones, fallos (llamadas LLM), entradas activas en LRU y ahorro acumulado de tokens y coste en USD.
- **Frontend Interactivo (`frontend/src/components/CacheObservabilityModal.tsx`):**
  - Modal interactivo con 6 tarjetas de KPIs en vivo (Tasa Global, Aciertos L1, Aciertos L2, Fallos, Tokens Ahorrados, Coste USD Ahorrado).
  - Barra de distribución apilada (stacked bar) con proporciones relativas de tráfico L1 vs L2 vs Misses.
  - Indicador de estado de conexión Redis L2 / Memoria local LRU con alertas visuales de timeout.
  - Botón de refresco en vivo (`RefreshCw`) y soporte completo de accesibilidad (Escape, ARIA).
- **Puntos de Integración UI:**
  - Botón «Caché IA» con icono `Activity` en la barra superior de navegación (`Header.tsx`).
  - Badge interactivo `ai-cached-badge` en la vista de revisión del plan (`PlanReview.tsx`), que permite abrir el panel de observabilidad directamente al detectar un hit.
  - Internacionalización completa en español e inglés.

#### ⭐ Exportación PNG de Star Schema y TMDL para Power BI Desktop
- **Exportación en Alta Resolución (`frontend/src/components/BusinessInsights.tsx`):**
  - Nuevo botón «Exportar PNG» en el visualizador interactivo de Esquema Estrella.
  - Renderizado en canvas HTML5 a escala 2x Retina con fondo `#0f172a` coherente con la aplicación y descarga automática del archivo `esquema_estrella_{fact_table}.png`.
- **Generación Canónica de TMDL para Dimensiones (`backend/app/services/analytics_service.py`):**
  - Nuevo método `_build_tmdl_dimension_table_definition(...)` que genera la estructura oficial TMDL de Microsoft Fabric / Power BI Desktop para tablas calculadas (`CALENDAR` y `DISTINCT`) con `lineageTag`, `partition ... = calculated`, `mode: import`, tipos de datos inferidos y referencias de columna.
  - El empaquetador del proyecto PBIP (`generate_powerbi_pbip_zip`) ahora escribe en el ZIP los archivos `.SemanticModel/definition/tables/{dim.name}.tmdl` para cada dimensión del modelo estrella, eliminando referencias huérfanas en `model.tmdl` y garantizando apertura inmediata y sin errores en Power BI Desktop Developer Mode.

#### 🧪 Verificación y Pruebas
- **Backend:** 166 pruebas unitarias y de integración pasando al 100% (+3 pruebas nuevas en `test_cache_observability.py` y `test_star_schema_visualizer.py`).
- **Frontend:** 45 pruebas con Vitest pasando al 100% (+4 pruebas nuevas en `CacheObservabilityModal.test.tsx`, `PlanReview.test.tsx` y `BusinessInsights.test.tsx`).
- **Linters & SAST:** Ruff 0 errores, Black 0 diferencias de formato, Bandit 0 vulnerabilidades. TypeScript + Vite compilando en 1.35s sin errores.

#### 🤖 Atribución del Modelo
- **Atribución del Modelo:** Gemini 3.8 Flash (High) (vía Google Antigravity).

## [1.13.1] — 2026-09-02

### 📸 Corrección del Badge de Versión y Nueva Captura del Esquema Estrella en el README

> **Documentación:** Parche de documentación que sincroniza el badge de versión del README con la versión real del proyecto y añade la séptima captura a la galería de vistas previas.

#### 📖 Mejoras de Documentación
- **README.md:** Badge de versión actualizado a 1.13.1 (había quedado desfasado en 1.12.0 respecto a `backend/app/core/config.py` y `frontend/package.json` desde la v1.13.0).
- **Galería de Vistas Previas:** Nueva sección «7️⃣ Esquema Estrella del Modelo Semántico (Star Schema Preview)» con la captura del visualizador interactivo incorporado en la v1.13.0 (`docs/capturas/captura_dataflow_ai_esquema_estrella.png`): diagrama SVG con tabla de hechos, dimensiones y relaciones `*:1`, panel de inspección y DAX de tablas calculadas propagado al `model.tmdl` del PBIP.

#### 🤖 Atribución del Modelo
- **Atribución del Modelo:** GLM-5.3-Flash (vía ZCode, app de desarrollo asistido por IA).

## [1.13.0] — 2026-09-02

### ⭐ Visualizador de Modelo Estrella (Star Schema) para Power BI y Caché de Inferencia Distribuida (Redis / Cloud Memorystore)

> **Integración Power BI & Escalabilidad Multi-Instancia:** Incorporación de un diagrama interactivo de modelo estrella que permite previsualizar la estructura semántica del dataset (tabla de hechos, dimensiones, relaciones y DAX de tablas calculadas) antes de cargar el archivo en Power BI; y de una capa de caché de inferencia distribuida en dos niveles (L1 memoria + L2 Redis) para compartir aciertos entre instancias de Cloud Run con degradación elegante.

#### ⭐ Visualizador de Modelo Estrella (Star Schema)
- **Modelos Pydantic (`backend/app/models/analytics.py`):**
  - Nuevos `StarSchemaDiagram`, `StarSchemaDimension` y `StarSchemaRelationship` con campo `star_schema` en `IntegrationGuide`.
- **Inferencia del Modelo Estrella (`backend/app/services/analytics_service.py`):**
  - Tabla de hechos central con filas y medidas del dataset; dimensiones de atributo inferidas de columnas id/categoría con cardinalidad razonable (`DISTINCT` DAX) y dimensión calendario `Dim_Fecha` con `CALENDAR` + `ADDCOLUMNS` (Año, Trimestre, Mes, Día, Día de Semana).
  - Relaciones muchos-a-uno (`*:1`) desde los hechos hacia cada dimensión, script DAX consolidado de tablas calculadas y fragmento TMDL de relaciones.
  - `model.tmdl` del proyecto PBIP exportable ahora incluye las referencias a tablas de dimensión y sus relaciones, reconstruyendo el modelo estrella automáticamente en Power BI Desktop.
- **Frontend Interactivo (`frontend/src/components/BusinessInsights.tsx`):**
  - Nueva vista "Esquema Estrella" en la tarjeta de Power BI con diagrama SVG: hechos al centro, dimensiones en órbita con código de color (calendario esmeralda / atributo azul), cardinalidad `* → 1` sobre cada relación y leyenda.
  - Panel de detalle al hacer clic en una dimensión: columna clave, valores distintos, atributos sugeridos y DAX de creación con copiado al portapapeles; botón de copiado del script consolidado.
  - Claves i18n en español e inglés con fallback.

#### 🌐 Caché de Inferencia Distribuida (L2 Redis / Cloud Memorystore)
- **Arquitectura de Dos Niveles (`backend/app/services/inference_cache.py`):**
  - L1 memoria LRU local (siempre activa, < 1 ms) + L2 Redis compartida entre instancias de Cloud Run, con promoción automática de hits L2 a L1.
  - Activación mediante `INFERENCE_CACHE_BACKEND=redis` y `REDIS_URL` (compatible con `rediss://` TLS de Memorystore); serialización JSON del `AISuggestionResponse` con TTL y metadato `stored_at`.
  - Degradación elegante: si `redis` no está instalado, la URL no existe o la conexión falla, el servicio opera solo-memoria sin interrumpir jamás la inferencia, con cooldown de reintento y contador de errores.
- **Observabilidad Ampliada:** `get_stats()` expone `backend`, `distributed`, `redis_hits` y `redis_errors` además de las métricas clásicas de aciertos y ahorro.
- **Configuración:** Nuevas variables en `Settings`, `.env.example` (`INFERENCE_CACHE_BACKEND`, `REDIS_URL`, `REDIS_SOCKET_TIMEOUT_SECONDS`) y dependencia `redis>=5.2.1` en `requirements.txt`.

#### 🤖 Atribución del Modelo
- **Atribución del Modelo:** GLM-5.3-Flash (vía ZCode, app de desarrollo asistido por IA).

## [1.12.0] — 2026-09-02

### 📸 Mejora Integral de la Documentación: Galería de Vistas Previas en el README y Consistencia de Métricas

> **Documentación:** Renovación completa del `README.md` con galería de capturas reales de la aplicación y actualización de métricas de tests.

#### 📸 Galería de Vistas Previas
- **Nueva sección "📸 Vista Previa de la Aplicación"** en el README con 6 capturas reales de la interfaz en `docs/capturas/`, ordenadas según el flujo de trabajo de la plataforma:
  1. Subida de datasets (CSV/XLSX, URL y Open Data CKAN).
  2. Auditoría de calidad y profiling (Data Quality Score).
  3. Revisión humana del plan ETL (Human-in-the-Loop).
  4. Transformación determinista con log de validación y trazabilidad.
  5. Segmentación de clusters (Business Analytics).
  6. Guía de integración y fórmulas para Power BI y Excel.

#### 📖 Mejoras de Documentación
- **README.md:** Adición de índice navegable (TOC), descripciones en español bajo cada captura, actualización de las cifras de tests a los valores reales (156 backend + 39 frontend = 195 + 3 E2E), funcionalidades ampliadas con exportación TMDL/PBIP, fórmulas dinámicas de Excel y caché de inferencia, y estructura del repositorio actualizada (`docs/capturas/`, servicios de exportación y caché).
- **Nueva sección de Atribución** reconociendo la autoría, la documentación previa y las herramientas de IA utilizadas.

#### 🤖 Atribución del Modelo
- **Atribución del Modelo:** GLM-5.3-Flash (vía ZCode, app de desarrollo asistido por IA).

## [1.11.0] — 2026-09-02

### 📊 Exportación Nativa de Modelos Semánticos Power BI (TMDL / PBIP / DAX), Fórmulas Dinámicas Multi-Categoría para Excel y Caché de Inferencia Gemini

> **Integración Avanzada con Power BI & Excel, Optimización de Costes y Latencia de IA:** Incorporación de exportación directa de modelos semánticos a formatos TMDL (`.tmdl`), scripts DAX (`.dax`) y paquetes de proyecto Power BI Developer Mode (`.pbip` en archivo ZIP); diversificación y enriquecimiento de las fórmulas adaptativas de Microsoft Excel en 4 categorías analíticas (Outliers IQR, KPIs Directivos, Participación Relativa y Validación Condicional) resolviendo la monotonía en la interfaz; y despliegue de una capa de caché semántica LRU/TTL para el Copiloto IA (Gemini 2.5 Flash) que reduce la latencia a < 1 ms y ahorra el 100% de costes y tokens en datasets con esquemas similares.

#### 📊 Exportación a Power BI (TMDL, DAX y Proyecto PBIP)
- **Modelos Pydantic Enriquecidos (`backend/app/models/analytics.py`):**
  - Adición de `format_string` y `display_folder` a `DaxMeasureItem` para organización jerárquica en Power BI Desktop.
  - Adición de `tmdl_table_definition`, `tmdl_model_definition` y `dax_script` a `IntegrationGuide`.
- **Motor de Generación TMDL y PBIP (`backend/app/services/analytics_service.py`):**
  - Generador declarativo de sintaxis TMDL compatible con Power BI Desktop y Microsoft Fabric (`table`, `lineageTag`, `column`, `summarizeBy`, `measure`, `partition` con Power Query M embebido).
  - Ensamblador de proyectos `.pbip` (Developer Mode) en ZIP conteniendo `{Nombre}.pbip`, `definition.pbidataset`, `diagramLayout.json`, `database.tmdl`, `model.tmdl` y `tables/{Nombre}.tmdl`.
- **Nuevos Endpoints REST (`backend/app/api/v1/endpoints/analytics.py`):**
  - `GET /api/v1/analytics/{run_id}/export/tmdl`: Descarga de definición TMDL.
  - `GET /api/v1/analytics/{run_id}/export/dax`: Descarga de script DAX consolidado.
  - `GET /api/v1/analytics/{run_id}/export/pbip`: Descarga de proyecto PBIP empaquetado en `.zip`.
- **UI Interactiva en Frontend (`frontend/src/components/BusinessInsights.tsx`):**
  - Botones de descarga directa para Proyecto PBIP, Modelo TMDL y Medidas DAX.
  - Selector de vistas de código: `[Medidas DAX]` | `[Power Query M]` | `[Modelo Semántico TMDL]` con copiado instantáneo al portapapeles.

#### 📗 Fórmulas Dinámicas Adaptativas Multi-Categoría para Excel
- **Diversificación Analítica (`backend/app/services/analytics_service.py`):**
  - Adición de 4 categorías de fórmulas nativas adaptadas a la configuración regional (español e inglés):
    - `outlier`: Auditoría fila a fila por método IQR/Desviación evaluando el rango real del dataset.
    - `kpi`: Métricas acumuladas y estadísticas de resumen (`SUMA`, `PROMEDIO`, `MEDIANA`, `DESVEST.M`).
    - `relative`: Participación porcentual de cada registro sobre el total acumulado (`H2/SUMA(...)`).
    - `conditional`: Validación de registros por encima de la media (`CONTAR.SI(...)`).
- **Selector de Categorías en Frontend (`frontend/src/components/BusinessInsights.tsx`):**
  - Filtro por categoría mediante botones pills (`Todas`, `Auditoría Outliers`, `KPIs & Estadísticas`, `Participación %`, `Condicionales`).
  - Guía visual de celda de destino recomendada (`target_cell`) e instrucciones de pegado.

#### ⚡ Caché de Inferencia Semántica para Copiloto IA (Gemini)
- **Servicio de Caché LRU/TTL (`backend/app/services/inference_cache.py`):**
  - Cálculo de hash canónico (SHA-256) invariante al orden de columnas, tipo de datos, inferencias semánticas y anomalías de calidad.
  - Almacén en memoria con límite de 500 entradas y TTL configurable (24 horas).
  - Telemetría de rendimiento y métricas acumuladas (`hits`, `misses`, `saved_tokens`, `saved_cost_usd`).
- **Integración Transparente (`backend/app/services/ai_service.py` & `backend/app/ai_providers/base.py`):**
  - Consulta y persistencia automática en `propose_ai_plan`. En caso de acierto (cache hit), retorna respuesta con `cached = True`, `estimated_cost_usd = 0.0` y `latency_ms < 1 ms`.
- **Indicador Visual en UI (`frontend/src/components/PlanReview.tsx`):**
  - Badge distintivo `ai-cached-badge` (`Caché de Inferencia (100% Ahorro)`) en el banner de telemetría IA.

#### 🧪 Pruebas, Calidad de Código y Validación
- **Tests Automatizados de Backend (`backend/tests/`):**
  - `test_powerbi_tmdl_export.py`: Validación de endpoints y sintaxis TMDL/DAX/PBIP.
  - `test_inference_cache.py`: Validación de cache hits, ahorro de costes e invariancia de orden de columnas.
  - 156/156 tests PASSED (`pytest -v`).
  - 0 errores de Ruff, 0 diferencias de Black, 0 vulnerabilidades de Bandit.
- **Tests Automatizados de Frontend (`frontend/src/`):**
  - 39/39 tests PASSED (`vitest run`).
  - Compilación TypeScript estricta y bundle Vite exitoso al 100%.

## [1.10.0] — 2026-09-02

### ⚡ Observabilidad de Inferencia IA (Latencia, Tokens y Coste USD), Comparador Scatter Diff de Outliers (Crudo vs. Limpio) y Actualización de Dependencias a Node 24 / jsdom 30

> **Observabilidad de IA, Diagnóstico Visual de Calidad y Modernización del Stack:** Incorporación de métricas completas de telemetría en la propuesta de planes asistidos por el Copiloto IA (Gemini 2.5 Flash); implementación de un comparador interactivo de dispersión (Scatter Diff) en la pestaña de Outliers contrastando el dataset crudo con el limpio; y consolidación exhaustiva de las actualizaciones de dependencias de Dependabot (PRs #12 al #21) con actualización a Node.js 24 en CI/CD y en el Dockerfile multi-stage para compatibilidad con `jsdom 30.0.1`.

#### 🤖 Copiloto IA & Observabilidad
- **Modelo de Telemetría e Inferencia (`backend/app/ai_providers/base.py`):**
  - Creación del contrato Pydantic `AIMetrics` con `latency_ms`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `estimated_cost_usd`, `model` y `provider`.
- **Integración con Gemini 2.5 Flash (`backend/app/ai_providers/gemini_provider.py`):**
  - Cronometrado de alta precisión mediante `time.perf_counter()`.
  - Extracción de metadatos de uso (`usageMetadata.promptTokenCount`, `candidatesTokenCount`, `totalTokenCount`) desde la API de Gemini.
  - Cálculo determinista del coste estimado en USD (\$0.10 por 1M tokens de entrada, \$0.40 por 1M tokens de salida).
- **Soporte Mock Determinista (`backend/app/ai_providers/mock_provider.py`):**
  - Generación de métricas y estimación de tokens para pruebas unitarias sin dependencias externas.
- **Trazabilidad en Planes ETL (`backend/app/models/etl.py` & `backend/app/services/ai_service.py`):**
  - Campo `ai_metrics` incorporado en `TransformationPlan` y propagado en la respuesta JSON de la API.
- **Visualización en Frontend (`frontend/src/components/PlanReview.tsx`):**
  - Franja informativa de observabilidad con badges para modelo (`gemini-2.5-flash`), latencia (`ms` o `s`), tokens de entrada/salida y coste estimado en dólares.

#### 🎯 Analytics: Comparador Interactivo de Dispersión (Scatter Diff)
- **Contratos y Modelos de Visualización (`backend/app/models/analytics.py`):**
  - Adición de `raw_y_value`, `was_modified` y `diff_status` a `OutlierScatterPoint`.
  - Creación del modelo `OutlierDiffSummary` (`raw_outliers_count`, `clean_outliers_count`, `resolved_outliers_count`, `reduction_percentage`).
- **Motor Estadístico de Comparación (`backend/app/services/analytics_service.py`):**
  - Carga del dataframe original crudo (`raw_df`) para calcular IQR comparativo, balance de resolución de anomalías y etiquetado individual por registro (`resolved_outlier`, `clamped`, `unchanged`, `imputed`).
- **Componente Interactivo en Frontend (`frontend/src/components/BusinessInsights.tsx`):**
  - Selector de vista con tercer modo: `Comparador Diff (Crudo vs. Limpio)`.
  - Resumen KPI con conteo de outliers en crudo frente a limpio, anomalías resueltas y tasa porcentual de reducción.
  - Diagrama SVG interactivo con puntos crudos (ámbar/rosa), puntos limpios (azul/verde), líneas conectoras discontinuas de ajuste/clamp, límites IQR e información contextual en tooltip.
  - Filtro interactivo para alternar entre todas las observaciones o solo las modificadas.
  - Mini tabla de evidencia con registro, valor crudo, valor limpio, variación $\Delta$ y estado.

#### 📦 Dependencias, CI/CD y Entorno de Ejecución (PRs #12 al #21)
- **Resolución de Conflicto en PR #21 (`jsdom 30.0.1`):**
  - Actualización de entorno Node.js a versión 24 en GitHub Actions (`.github/workflows/ci.yml`) y en la fase de compilación del `Dockerfile` multi-stage (`node:24-alpine`).
- **Actualizaciones Dependabot Consolidadas:**
  - `pandas >= 3.0.5`
  - `pydantic >= 2.13.5`
  - `pyarrow >= 25.0.1`
  - `pytest >= 9.1.1`
  - `uvicorn >= 0.52.4`
  - `vitest 4.1.11`
  - `@vitejs/plugin-react 6.1.1`
  - `lucide-react 1.37.0`
  - `@testing-library/jest-dom 7.0.1`
  - `jsdom 30.0.1`
- **Atribución del Modelo:** Antigravity (Advanced Agentic Coding).

---

## [1.9.3] — 2026-09-02

### 🐛 Corrección de Exclusión en `.dockerignore` para Inclusión de Datasets de Demostración en Contenedor Cloud Run

> **Solución de Empaquetado Docker y CI/CD:** Eliminación de la regla de exclusión de `data_samples` en `.dockerignore`, resolviendo el fallo de compilación `ERROR: "/data_samples": not found` en el pipeline de GitHub Actions (`docker-build`) y en el disparador de Cloud Build para Cloud Run, garantizando la disponibilidad completa de las muestras empresariales en el contenedor de producción.

#### 🐳 Infraestructura & Contenedores
- **Configuración de Contexto de Construcción (`.dockerignore`):**
  - Se removió `data_samples` de `.dockerignore` para permitir que la instrucción `COPY data_samples ./data_samples` en `Dockerfile` encuentre los ficheros en el contexto de compilación.
- **Atribución del Modelo:** Antigravity (Advanced Agentic Coding).

---

## [1.9.2] — 2026-09-02

### 🔍 Botones de Previsualización de Esquema en Plan ETL, Optimización de Despliegue en Cloud Run con Datasets Empresariales Variados y Alineación de Terminología DQS

> **Visibilidad de Esquemas y Excelencia en Producción Cloud:** Incorporación de botones de previsualización de esquema de columnas previo a la ejecución del plan ETL en el Paso 3 (`PlanReview`), tanto a nivel global con proyección antes/después como mediante visor contextual por paso; resolución de rutas y empaquetado de `data_samples` en el contenedor `Dockerfile` para Cloud Run; adición de un 4º dataset empresarial de demostración para Logística & Cadena de Suministro B2B; y actualización exhaustiva de la documentación del Data Quality Score con los 5 términos en castellano natural consolidados en la aplicación.

#### 🖥️ Frontend: Previsualización de Esquemas y Experiencia de Usuario
- **Previsualización Global del Esquema Proyectado (`frontend/src/components/PlanReview.tsx`):**
  - Nuevo botón en la cabecera del plan ETL (`Previsualizar Esquema ({N})`) que conmuta un panel completo con la tabla comparativa de columnas.
  - Proyección determinista del estado final de cada columna tras aplicar los pasos aprobados: *Sin cambios*, *Modificada ({N} ops)*, *Renombrada a {nuevo_nombre}*, *Eliminada* o *Nueva Columna* (ej. `cluster` en segmentación K-Means).
  - Visualización del tipo inferido, categoría semántica, porcentaje y conteo de nulos, valores únicos y muestras de valores reales por columna.
- **Visor Contextual por Paso y Columna:**
  - Botón individual `Ver esquema de columna` en cada tarjeta de transformación para inspeccionar instantáneamente la distribución y muestra de datos de la columna antes de ejecutar el pipeline.
- **Soporte de Iconos y Datasets Demostrativos (`FileUpload.tsx`):**
  - Integración del icono `Truck` para el dataset demo de Logística.
- **Internacionalización i18n (`frontend/src/i18n/index.ts`):**
  - Cadenas y etiquetas agregadas para los botones y paneles de previsualización en español e inglés.
- **Suite de Pruebas Unitarias Frontend (`frontend/src/components/PlanReview.test.tsx`):**
  - 3 nuevos tests unitarios validando la conmutación del panel global de esquema proyectado, el visor por paso y la ejecución del plan aprobado. Total: 37 tests pasando al 100%.

#### ☁️ Backend & Contenedores: Despliegue en Cloud Run
- **Empaquetado de Datasets en Dockerfile (`Dockerfile`):**
  - Inclusión de `COPY data_samples ./data_samples` en el contenedor de producción para garantizar la disponibilidad de las muestras en Google Cloud Run.
- **Resolución Multiplataforma de Rutas (`backend/app/api/v1/endpoints/datasets.py`):**
  - Eliminación de rutas fijas dependientes del sistema operativo anfitrión y soporte explícito para rutas de contenedor `/app/data_samples` y rutas de entorno local.
- **4º Dataset Demostrativo Empresarial (`data_samples/logistics_pedidos_corrupted.csv`):**
  - Cobertura de pedidos B2B, acrónimos mercantiles (`S.L.U.`), valores atípicos, marcadores universales de nulos (`--`), divisas múltiples (`€`, `$`) y plazos de entrega negativos.
- **Suite de Pruebas Backend (`backend/tests/test_analytics.py`):**
  - Verificación del listado y carga de los 4 datasets empresariales de muestra y prueba integral end-to-end de logística. Total: 146 tests pasando al 100%.

#### 📚 Documentación
- **Alineación del Modelo de Data Quality Score (`README.md`):**
  - Actualización de la fórmula y tabla con los 5 términos consolidados en castellano: Datos Completos (30%), Formatos Válidos (25%), Formato Homogéneo (20%), Registros Únicos (15%) y Reglas de Negocio (10%), acompañados de sus métricas de ejemplo.
  - Inclusión del nuevo dataset demo de Logística y actualización de badges a 146 backend / 37 frontend.
- **Atribución del Modelo:** Antigravity (Advanced Agentic Coding).

---

## [1.9.1] — 2026-09-01

### 🐛 Corrección de Excepción en Renderizado de Integración Power BI / Excel y Alineación de Esquema

> **Blindaje de la Pestaña de Integración:** Corrección del error en tiempo de ejecución `TypeError: Cannot read properties of undefined (reading 'length')` al acceder a la pestaña "Integración Power BI / Excel"; alineación estricta de las interfaces de TypeScript (`columns`, `formula`, `title`, `column`, `power_bi_m_type`, `excel_column_letter`) con los modelos Pydantic del backend; e incorporación de protecciones defensivas y valores por defecto para garantizar un renderizado fluido incluso con datasets previos o sin guía analítica precalculada.

#### 🔧 Frontend: Robustez de la Interfaz y Resiliencia
- **Alineación de Esquema de Datos (`frontend/src/types/index.ts`):**
  - Corrección de la interfaz `IntegrationGuide`: se renombró `columns_metadata` a `columns` para coincidir exactamente con el campo emitido por el backend FastAPI/Pydantic.
  - Actualización de campos en `DaxMeasureItem` (`formula` en lugar de `dax_formula`) y `ExcelFormulaItem` (`title`, `column`, `excel_column_letter`).
- **Renderizado Seguro y Resiliente (`frontend/src/components/BusinessInsights.tsx`):**
  - Adición de encadenamiento opcional defensivo (`guide?.columns?.length ?? 0`, `(guide.row_count ?? 0).toLocaleString()`) y desestructuración con fallbacks vacíos (`[]`) para todas las listas (`columns`, `daxMeasures`, `excelFormulas`).
  - Soporte bidireccional retrocompatible para atributos legacy y nuevos en las medidas DAX y fórmulas de Excel.
  - Prevención de desbordamientos en el ErrorBoundary al conmutar entre pestañas.
- **Suite de Pruebas Frontend:**
  - Nuevo test unitario en `BusinessInsights.test.tsx` comprobando que la pestaña de integración renderiza correctamente con valores por defecto y sin excepciones cuando `report.integration_guide` es `undefined`. Total: 34 tests unitarios de frontend pasando al 100%.
- **Atribución del Modelo:** Antigravity (Advanced Agentic Coding).

---

## [1.9.0] — 2026-09-01

### 🛡️ Remediación XSS CodeQL, Benchmarks de Carga Masiva (>100k Filas), Protección Interactiva de Datos y Guía Adaptativa para Power BI y Excel

> **Remediación AppSec, Rendimiento a Gran Escala e Integración Adaptativa:** Mitigación completa de la alerta CodeQL #10 (`py/reflective-xss`) mediante validación estricta con expresiones regulares, sanitización whitelist de idioma, cabeceras HTTP defensivas y escape HTML exhaustivo; suite automatizada de pruebas de rendimiento y carga con datasets de 100.000 filas; feedback interactivo en la interfaz de usuario para prevenir la pérdida irreversible de texto libre con confirmación explícita del operador humano; y desarrollo del motor adaptativo de Guía de Integración y Fórmulas para Microsoft Power BI (Power Query M nativo para CSV y Parquet, medidas DAX contextuales) y Microsoft Excel (fórmulas dinámicas por columna y mapeo regional ES/EN).

#### 🔒 Seguridad y Remediación de Código (CodeQL #10)
- **Mitigación Reflected Server-Side XSS (`backend/app/api/v1/endpoints/analytics.py`):**
  - Validación de ruta para `run_id` mediante expresión regular restrictiva `^[a-zA-Z0-9_\-]+$`, bloqueando inyecciones de caracteres `<script>`, comillas o caracteres de control HTTP con respuesta 400 Bad Request.
  - Validación del parámetro `lang` contra whitelist estricta de 13 idiomas internacionales permitidos (`es`, `en`, `zh`, `hi`, `fr`, `ar`, `bn`, `pt`, `id`, `ur`, `ru`, `de`, `ja`), con fallback seguro a `"es"`.
  - Inclusión de cabecera de respuesta HTTP defensiva `X-Content-Type-Options: nosniff` en `/api/v1/analytics/{run_id}/export`.
- **Sanitización Exhaustiva en Generación de Informes HTML (`backend/app/services/analytics_service.py`):**
  - Todas las variables dinámicas incrustadas en `generate_html_report` (`safe_lang`, `safe_run_id`, `safe_output_hash`, `safe_summary`, métricas de KPI, recomendaciones estratégicas y filas de clusters) se escapan obligatoriamente con `html.escape(..., quote=True)`.
  - Adición de tests de regresión de seguridad específicos en `tests/test_analytics.py::test_xss_protection_and_sanitization_in_analytics_export`.

#### ⚡ Rendimiento Vectorizado y Tests de Carga (>100.000 Filas)
- **Suite de Pruebas de Rendimiento (`backend/tests/test_performance_large_dataset.py`):**
  - Incorporación de 5 tests exhaustivos de rendimiento sobre datasets de 100.000 filas verificando tiempos de perfilado (<30s), análisis de calidad (<25s), transformaciones vectorizadas `ConvertNumeric`, `ClampRange` y `TrimText` (<3s), serialización columnar Apache Parquet (<3s) y generación de guías de integración (<1s).
- **Optimización de Motores de Perfilado y Calidad (`profiler_service.py`, `quality_service.py`, `number_parsing.py`):**
  - Extracción de métodos `ProfilerService.profile_dataframe` y `QualityService.analyze_dataframe` para permitir análisis directos en memoria.
  - Optimización de `is_missing_series`: omite conversiones innecesarias a string en columnas numéricas y booleanas vectorizadas.
  - Comprobación previa de palabras clave y símbolos antes del cálculo de parseabilidad numérica en inferencia de tipos y sugerencias de divisas.
  - Vectorización en C de la detección de espacios sobrantes (`series != series.str.strip() | series.str.contains("  ")`) y mayúsculas en `QualityService`.

#### ⚠️ Protección Interactiva de Pérdida de Datos en UI
- **Advertencias Proactivas (`TransformationStep.data_loss_warning`):**
  - Backend calcula y adjunta advertencias explicativas cuando una transformación (`convert_numeric`) convertirá texto libre a números descartando contenido no numérico.
- **Interfaz React Interactiva (`PlanReview.tsx`):**
  - Renderizado de tarjeta de aviso destacado con icono `AlertTriangle` y explicación clara de la pérdida irreversible de datos.
  - Checkbox de confirmación explícita (*Human-in-the-Loop*): el usuario debe marcar la casilla de confirmación para autorizar la conversión antes de la ejecución.

#### 📊 Guía de Integración y Fórmulas Adaptativas para Power BI y Excel
- **Arquitectura de Metadatos de Integración (`models/analytics.py` & `frontend/src/types/index.ts`):**
  - Modelos `IntegrationGuide`, `IntegrationColumn`, `DaxMeasureItem`, `ExcelFormulaItem` incorporados en el reporte analítico ejecutivo.
- **Generación Dinámica Adaptada al Dataset (`backend/app/services/analytics_service.py`):**
  - Mapeo automático de nombres y tipos de columna nativos para scripts de Power Query M (`type text`, `type number`, `Int64.Type`, `type date`, `type logical`).
  - Scripts M independientes optimizados tanto para ingesta de CSV delimitado como para Apache Parquet de alto rendimiento.
  - Generación de medidas DAX adaptadas a cada variable cuantitativa real (sumas, promedios, KPI de calidad sin outliers, periodo temporal máximo) con comentarios descriptivos.
  - Fórmulas de Excel dinámicas basadas en la letra real de cada columna (ej. `Col C (C2:C150)`), adaptadas con sintaxis regional en castellano (`=SI(ESNUMERO(...); ...; ...)`) e inglés (`=IF(ISNUMBER(...), ..., ...)`).
- **Componente Visual Adaptativo (`BusinessInsights.tsx`):**
  - Conmutador interactivo entre conectores CSV y Parquet para Power Query M.
  - Botón de copiado masivo de todas las medidas DAX y copiado individual por medida.
  - Selector interactivo de columna para generar al instante la fórmula de validación de outliers de Excel para cualquier variable del dataset.
  - Tabla de mapeo de columnas con letra de Excel asignada y tipo de Power BI.

#### 🧪 Verificación Integral de Calidad
- **145 Tests Backend (Pytest):** 100% pasando en verde.
- **33 Tests Frontend (Vitest):** 100% pasando en verde.
- **Linters y SAST:** Ruff (0 errores), Black (0 diferencias), Bandit SAST (0 vulnerabilidades), TypeScript estricto (0 errores), Vite build verificado (0 errores).
- **Atribución del Modelo:** Antigravity (Advanced Agentic Coding).

---

## [1.8.1] — 2026-09-01

### 🛡️ Endurecimiento de Gobernanza de Datos, Integridad Semántica y Auditoría de Calidad Determinista

> **Resolución de Hallazgos de Auditoría Externa:** Corrección integral y blindaje determinista ante los 5 hallazgos críticos y altos detectados sobre datasets empresariales con formato español y marcadores mixtos de ausencia: prevención absoluta de pérdida de datos en texto libre, preservación de ceros a la izquierda en identificadores y códigos postales, acotamiento de rango bidireccional en porcentajes [0.0, 100.0%], unificación del catálogo de valores ausentes entre perfilado y motor ETL, y detección nativa de separadores decimales regionales europeos (coma decimal).

#### 🛡️ Backend: Integridad de Negocio y Gobernanza
- **FIX 1 — Prevención de Pérdida de Datos en Texto Libre (`ConvertNumericTransformation` & `semantics.py`):**
  - Implementación de `get_numeric_parseable_ratio`: exige un ratio de parseabilidad numérica $\ge 80\%$ sobre valores no vacíos para que una columna pueda clasificarse como `percentage` o inferirse como `numeric`.
  - Columnas como `Observaciones` que contienen el carácter `%` dentro de prosa textual ya nunca reciben sugerencias ni transformaciones de `convert_numeric`.
  - Mecanismo de seguridad (*Circuit Breaker*) en `ConvertNumericTransformation.apply`: aborta inmediatamente con excepción funcional `CONVERT_NUMERIC_DATA_LOSS` si más del 50% de las celdas con contenido real fueran a convertirse en `NaN`.
- **FIX 2 — Preservación de Ceros a la Izquierda en Identificadores (`DatasetService`, `datasets.py`, `profiler_service.py` & `etl_service.py`):**
  - Escaneo previo a la ingestión (`pd.read_csv(nrows=100, dtype=str)`) para detectar columnas de códigos o identificadores mediante `is_id_or_code_column`.
  - Forzado explícito de `dtype=str` durante la carga de CSVs (`pd.read_csv(..., dtype=id_dtypes)`), garantizando que códigos postales españoles como `08001`, `07001` y `01001` nunca se degraden a enteros truncados (`8001`, `7001`, `1001`).
  - Protección activa de columnas ID en `ProfilerService.profile_dataset` y reconversión estricta a texto antes de la exportación a CSV y Apache Parquet.
- **FIX 3 — Acotamiento Bidireccional en Porcentajes [0.0, 100.0%] (`mock_provider.py`, `gemini_provider.py`, `ai_service.py` & `etl_service.py`):**
  - Cualquier operación `clamp_range` propuesta o ejecutada sobre columnas de porcentaje fija obligatoriamente tanto `min_value: 0.0` como `max_value: 100.0`, corrigiendo tanto valores negativos (ej. `-5,20%` $\rightarrow 0.0$) como superiores al 100% (ej. `105,30%` $\rightarrow 100.0$).
  - Guardrail en `AIService` que reescribe automáticamente los parámetros de acotamiento propuestos por cualquier proveedor LLM sobre columnas porcentuales.
- **FIX 4 — Unificación del Catálogo de Marcadores de Ausencia (`number_parsing.py`, `profiler_service.py` & `quality_service.py`):**
  - Funciones centralizadas `is_missing_value(val)` e `is_missing_series(series)` basadas en el catálogo exhaustivo `MISSING_MARKERS` (`--`, `---`, `n/d`, `n/a`, `s/n`, `nan`, `null`, `undefined`, `nd`, `na`).
  - `ProfilerService` reporta con precisión matemática el 100% de los nulos reales (ej. 14 nulos / 43.75% en `Unidades_Stock`, 2 nulos / 6.25% en `Tasa_Conversion_Pct`, `Descuento_Pct` y `Score_Calidad`), coincidiendo exactamente con los `NaN` resultantes de la transformación determinista.
- **FIX 5 — Detección y Conversión de Formato Numérico Español (`quality_service.py`, `mock_provider.py` & `etl_service.py`):**
  - Detección de números almacenados como texto con comas decimales europeas (`2450,75`) y palabras clave financieras (`gasto`, `facturacion`).
  - `QualityService` y el motor de reglas generan advertencias y proponen automáticamente `convert_numeric` para columnas como `Gasto_Medio_Mensual`, convirtiéndolas a `float64` (`2450.75`).
  - Protección de claves e identificadores (`ID_Cliente`, `ID_Pedido`) para que el Copiloto nunca proponga `normalize_case` sobre códigos alfanuméricos.

#### 🧪 Testing y Verificación Integral (173 Tests Totales)
- **138 Tests Backend (Pytest) + 32 Tests Frontend (Vitest) + 3 Suites E2E (Playwright):** 100% pasando en verde (+6 tests dedicados de regresión de auditoría en `test_audit_v180_fixes.py`).
- **Linters y SAST Verificados:** Ruff (0 errores), Black (0 diferencias), Bandit SAST (0 vulnerabilidades), TypeScript estricto (0 errores), Vite build verificado (0 errores).
- **Atribución del Modelo:** Antigravity (Advanced Agentic Coding).

---

## [1.8.0] — 2026-08-31

### 🏹 Exportación Nativa a Apache Parquet / Arrow y Suite de Pruebas E2E Automatizadas con Playwright

> **Serialización Columnar de Alto Rendimiento y Calidad E2E en Navegadores Reales:** Incorporación de exportación nativa de datasets limpios en formato Apache Parquet (`.parquet`) impulsado por `PyArrow` para interoperabilidad directa con Data Lakes, Power BI, DuckDB y Apache Spark; adición de endpoints dedicados `/api/v1/runs/{run_id}/download-parquet` y botones de descarga directos en el informe de ejecución; generación de snippets reproducibles para Parquet en scripts de Python; y despliegue de una suite completa de pruebas End-to-End (E2E) con **Playwright** en navegador Chromium headless que valida flujos completos de carga, perfilado, revisión de planes, descargas multiformato y conmutación de 13 idiomas con layout bidireccional (LTR/RTL).

#### 🏹 Backend: Serialización y Endpoints Apache Parquet
- **Soporte Nativo PyArrow (`requirements.txt` & `ETLService.execute_plan`):** Serialización vectorial y columnar automática del dataset limpio generado tras la ejecución del pipeline determinista.
- **Endpoints REST Columnar (`GET /api/v1/runs/{run_id}/download-parquet`):** Descarga directa con MIME type `application/vnd.apache.parquet` y alias compatibles (`/parquet`, `/download/parquet`).
- **Generador de Scripts Reproducibles (`ScriptGeneratorService`):** Inclusión de snippet opcional para exportación en Parquet (`df_clean.to_parquet('clean_dataset.parquet', index=False)`).
- **Cobertura de Tests Unitarios e Integración (`test_parquet_export.py`):** Validación de magic bytes `PAR1`, paridad de dimensiones/tipos y deserialización completa con pandas.

#### 🎭 Frontend & E2E: Pruebas con Playwright y Botón Parquet
- **Configuración de Playwright (`playwright.config.ts`):** Orquestación automatizada de servidores web (FastAPI backend + Vite dev server) y ejecución headless en Chromium.
- **Suite de Idiomas y Layout RTL (`e2e/language-switching.spec.ts`):** Comprobación en navegador de conmutación dinámica en español, inglés, francés, alemán, árabe, etc., y validación del atributo `dir="rtl"`.
- **Suite de Flujos y Exportaciones (`e2e/export-flows.spec.ts`):** Validación E2E del ciclo completo de datos y descarga íntegra de los 4 artefactos (CSV, Parquet, Script Python, Reporte HTML).
- **Suite de Business Analytics (`e2e/analytics-tabs.spec.ts`):** Navegación por pestañas (KPIs, Clusters 2D, Outliers Boxplot, Integración Power BI / Excel) e interactividad de gráficos SVG.
- **Botón de Descarga Parquet en `ExecutionReport.tsx`:** Botón accesible con icono de base de datos e internacionalización completa en los 13 idiomas.

#### 🧪 Testing y Verificación Integral (167 Tests Totales)
- **132 Tests Backend (Pytest) + 32 Tests Frontend (Vitest) + 3 Suites E2E (Playwright):** 100% pasando en verde.
- **Linters y SAST Verificados:** Ruff (0 errores), Black (0 diferencias), Bandit SAST (0 vulnerabilidades), TypeScript estricto (0 errores), Vite build verificado (0 errores).
- **Atribución del Modelo:** Gemini 3.7 Flash (High).

---

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
