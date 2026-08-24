# 🗺️ DataFlow AI — Roadmap de Evolución Arquitectónica

**Versión del Roadmap:** 1.2  
**Estado General:** Fase 1 Completada (v1.2.0) · Fase 2 en Curso  
**Stack Base:** Python 3.11 · FastAPI · Pandas 2.2 · React 18 · TypeScript · Google Cloud Run  
**Autor:** [migueljerico](https://github.com/migueljerico)  

---

## 🎯 Visión y Principios Rectores

DataFlow AI es una plataforma ágil de preparación, calidad y transformación de datos diseñada para alimentar modelos y cuadros de mando en **Power BI**. 

El presente roadmap define la evolución del sistema desde la subida manual de archivos hacia la **ingesta directa por URL** y la **conexión con portales de Open Data**, bajo cuatro principios innegociables:

1. **Cero Infraestructura Adicional:** La app corre al 100% en el contenedor existente de Google Cloud Run sin añadir bases de datos externas, colas de mensajes (Redis/Celery) ni almacenamiento persistente de pago (S3/GCS).
2. **No Sobre-Ingeniería:** Diseñado para datasets de uso real y portfolio (hasta 20–30 MB), priorizando simplicidad y velocidad frente a complejidad distribuida innecesaria.
3. **Seguridad Defensiva en Profundidad (Security by Design):** Protección activa contra ataques *Server-Side Request Forgery* (SSRF) y *DNS Rebinding* (TOCTOU) para proteger la infraestructura interna de Cloud Run.
4. **Verificabilidad sin Programar:** Cada fase es entregable de forma independiente y verificable por una sola persona mediante pruebas funcionales de entrada/salida (I/O) y paneles visuales.

---

## 🧭 Diagrama General de Fases

```mermaid
flowchart TD
    subgraph F1["✅ FASE 1 (Completada - v1.2.0)"]
        A1["Motor Ingesta URL Backend"] --> A2["Blindaje Anti-SSRF (IPv4/IPv6)"]
        A2 --> A3["IP Pinning vs DNS Rebinding"]
        A3 --> A4["Control de Memoria tmpfs (20 MB)"]
    end

    subgraph F2["⏳ FASE 2 (Siguiente Paso)"]
        B1["Pestaña 'Pegar Enlace Web' en UI"] --> B2["Feedback de Progreso en Vivo"]
        B2 --> B3["Mapeo Visual de Errores Remotos"]
    end

    subgraph F3["📋 FASE 3 (Planificada)"]
        C1["Conector CKAN REST API"] --> C2["Buscador Temático de Datasets"]
        C2 --> C3["Tarjetas con 1-Click Import"]
    end

    subgraph F4["📋 FASE 4 (Planificada)"]
        D1["Autodetección de Encoding (charset-normalizer)"] --> D2["Ajuste Fino de Profiler Semántico"]
        D2 --> D3["Protección de IDs y Códigos INE"]
    end

    F1 --> F2
    F2 --> F3
    F3 --> F4
```

---

## 📌 Detalle de Fases

### 🔹 Fase 1: Motor Backend de Ingesta por URL Segura
* **Estado:** ✅ **Completada (Release v1.2.0 — 24 de agosto de 2026)**
* **Objetivo:** Permitir que el backend descargue y procese datasets CSV/XLSX desde enlaces públicos con protección de red y control de memoria.
* **Qué se construyó:**
  1. **Módulo de Seguridad (`app/core/security_url.py`):**
     - Validación estricta de esquemas (`http://`, `https://`).
     - Bloqueo exhaustivo de rangos IPv4/IPv6 privados, loopback (`127.0.0.1`, `::1`), link-local (`fe80::/10`, `169.254.0.0/16` **GCP Metadata**), ULA (`fc00::/7`) e IPv4-mapped IPv6 (`::ffff:0:0/96`).
     - **IP Pinning:** Conexión fijada a la IP pública validada (`PinnedAsyncNetworkBackend`), mitigando ataques de *DNS Rebinding (TOCTOU)* y preservando *TLS SNI* en HTTPS.
     - Intercepción y revalidación de redirecciones HTTP (máx. 3 saltos).
  2. **Control de Memoria en Cloud Run (`tmpfs`):**
     - Streaming defensivo con límite de **20 MB** (`MAX_URL_FILE_SIZE_BYTES`) y timeout de 20s.
     - Limpieza automática preventiva (`_cleanup_old_uploads`) de archivos huérfanos en `uploads/`.
  3. **Endpoint:** `POST /api/v1/datasets/from-url` conectado al pipeline determinista.
  4. **Tests:** 47 nuevos tests automatizados (**76 tests en total, 100% en verde**).
* **Verificación Manual:** Pruebas en Swagger `/docs` con CSV público de GitHub (éxito 201), IP de metadatos `169.254.169.254` (bloqueo 400), e IPv6 `[::1]` (bloqueo 400).

---

### 🔹 Fase 2: Interfaz en React para Carga por URL con Feedback
* **Estado:** ⏳ **En Curso / Siguiente Paso**
* **Objetivo:** Dotar a la aplicación web de una experiencia fluida para importar datasets pegando enlaces, sin necesidad de usar Swagger.
* **Qué se construye:**
  1. Selector de modo en `FileUpload.tsx`: **"Subir Archivo Local"** | **"Pegar Enlace Web (URL)"**.
  2. Campo de entrada con validación en tiempo real (`http://` / `https://`) y botón *"Descargar e Importar"*.
  3. Indicadores de estado visual: *"Conectando con el servidor..."* $\rightarrow$ *"Descargando dataset..."* $\rightarrow$ *"Analizando calidad..."*.
  4. Gestión de errores amigable ante enlaces inaccesibles, bloqueos de seguridad o exceso de tamaño.
* **Esfuerzo Relativo:** **Pequeño** (modificaciones contenidas en frontend).
* **Cómo se verifica (sin programar):**
  1. Pegar una URL pública en la web y observar la transición automática hacia el panel de Profiling y Plan ETL.
  2. Pegar una URL inválida o privada y comprobar que la interfaz muestra un mensaje de aviso claro en rojo.

---

### 🔹 Fase 3: Conector a Portal Open Data (CKAN / Datos Abiertos)
* **Estado:** 📋 **Planificada**
* **Objetivo:** Integrar un catálogo de datos abiertos para explorar y cargar datasets públicos reales con 1 solo clic.
* **Por qué CKAN (ej. *datos.gob.es* o *data.gov*):** Estándar abierto más extendido a nivel gubernamental; API REST en JSON sin registro ni claves obligatorias que entrega enlaces directos a recursos CSV.
* **Qué se construye:**
  1. **Backend:** Endpoint `GET /api/v1/datasets/open-data/search?query=...` que consulta la API pública de CKAN (`package_search`), filtra recursos CSV limpios y extrae título, descripción y tamaño.
  2. **Frontend:** Tercera pestaña en la UI: **"Explorar Open Data"**, con barra de búsqueda rápida y 3–4 datasets de ejemplo preconfigurados (ej. *Carburantes*, *Calidad del aire*, *Tráfico*).
  3. Botón *"Importar a DataFlow"* que canaliza la URL seleccionada al motor seguro de la Fase 1.
* **Esfuerzo Relativo:** **Mediano** (integración API externa + nuevo componente UI).
* **Cómo se verifica (sin programar):**
  1. Buscar un término (ej. *"precios"*) en la pestaña de Open Data.
  2. Hacer clic en *"Importar"* y comprobar que el dataset se descarga, limpia y genera su correspondiente script reproducible de Python.

---

### 🔹 Fase 4: Guardrails de Ingesta, `charset-normalizer` y Corrección Semántica
* **Estado:** 📋 **Planificada**
* **Objetivo:** Blindar la ingesta contra codificaciones problemáticas y evitar falsos positivos en la clasificación de datos públicos.
* **Qué se construye:**
  1. **Detección Estadística de Codificación (`charset-normalizer`):** Reconocimiento automático de `UTF-8`, `UTF-8 con BOM`, `Windows-1252` e `ISO-8859-1/15` en los primeros bloques del archivo, evitando caracteres corruptos (`Ã±`, ``).
  2. **Ajuste de Inferencia Semántica:** Reforzar reglas para que códigos de INE, códigos postales o identificadores alfanuméricos no se clasifiquen erróneamente como dinero o fechas.
* **Esfuerzo Relativo:** **Pequeño-Mediano** (ajustes defensivos en backend).
* **Cómo se verifica (sin programar):**
  1. Cargar un dataset oficial en formato `Windows-1252` y comprobar que las tildes y la `ñ` se visualizan perfectamente.
  2. Comprobar en el Profiler que columnas como `codigo_postal` o `id_tramo` se etiquetan como texto/código y no como divisa.

---

## 🚫 Decisiones de Diseño: Fuera de Alcance Justificado

Para garantizar la mantenibilidad y sostenibilidad del proyecto por una sola persona:

| Característica Excluida | Motivo Técnico de Exclusión |
| :--- | :--- |
| **Colas de Tareas (Celery, Redis, RabbitMQ, SQS)** | Añadiría costes y servicios adicionales innecesarios. Con descargas en streaming síncronas de < 20 MB, las peticiones se completan en 1–3 segundos. |
| **Almacenamiento S3 / Cloud Storage / MinIO** | Complejidad de credenciales IAM y costes recurrentes. El sistema de ficheros efímero (`tmpfs`) de Cloud Run es suficiente para el ciclo de vida de transformación. |
| **Protocolo TUS / Subida Multipart compleja** | Diseñado para archivos de gigabytes; sobre-ingeniería para datasets de análisis moderado. |
| **Migración a DuckDB, Polars o Spark** | Rompería la compatibilidad del motor determinista (`TransformationRegistry`) y los 76 tests existentes sin aportar valor perceptible para archivos ≤ 20 MB. |
| **Múltiples APIs Open Data simultáneas** | Cada portal tiene esquemas dispares. Implementar el estándar CKAN cubre miles de fuentes públicas con una sola base de código limpia. |

---

## 📊 Matriz de Esfuerzo y Trazabilidad

| Fase | Entregable Principal | Esfuerzo | Tests Pytest | Estado |
| :---: | :--- | :---: | :---: | :---: |
| **1** | Backend URL Loader + Anti-SSRF + IP Pinning + `tmpfs` | Pequeño-Medio | 76 / 76 | ✅ **Completada (v1.2.0)** |
| **2** | UI React Carga URL + Feedback en Vivo | Pequeño | — | ⏳ **En Curso** |
| **3** | Conector CKAN Open Data + Buscador en UI | Mediano | ~85 esperados | 📋 Planificada |
| **4** | `charset-normalizer` + Profiler Semántico Robusto | Pequeño-Medio | ~95 esperados | 📋 Planificada |

---

<p align="center">
  <b>DataFlow AI</b> · <i>From raw business data to clean, trusted and actionable insights.</i><br>
  Documentado y mantenido por <a href="https://github.com/migueljerico">@migueljerico</a> · 2026
</p>
