# Changelog — DataFlow AI

Todas las modificaciones notables de este proyecto se documentan en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/) y este proyecto sigue el [Versionado Semántico](https://semver.org/lang/es/).

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
