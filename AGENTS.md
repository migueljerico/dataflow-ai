# AGENTS.md — Instrucciones para asistentes de IA y desarrollo autónomo

> **Fuente de verdad:** Este archivo es el **punto de entrada operativo** para asistentes de IA que trabajan en **DataFlow AI**. Define las reglas de sesión, estándares de arquitectura, gobernanza y la **rutina de publicación y release automática**.

---

## 🌐 Idioma y Principio Fundamental

- **Idioma:** UI, comentarios de código, documentación y mensajes al usuario **siempre en español (castellano)**. Identificadores técnicos (variables, funciones, tipos, clases) en inglés.
- **Principio Fundamental de Gobierno:**
  > **"La IA propone. El usuario decide. Python ejecuta."**
  La IA nunca ejecuta código arbitrario ni manipula datasets sin aprobación explícita humana (*Human-in-the-Loop*). Toda transformación se ejecuta de manera determinista en Python/Pandas mediante el `TransformationRegistry`.

---

## 🚀 Rutina de Cierre y Publicación Automática (OBLIGATORIA al terminar una gestión)

**Cuándo:** Al cerrar cualquier gestión con **tests verdes, linters limpios y build verificado**.
**Cómo:** Ejecútala **sin pedir permiso** (regla de oro del proyecto). El único motivo para frenar es que fallen los tests, linters o el build.

### Regla de Oro
> **Commit + Push + Tag + GitHub Release + Deploy van SIEMPRE JUNTOS.**
> Nunca commitees sin pushear, ni pushees sin tagear, ni tagees sin publicar el release en GitHub.
> Cada push a `main` dispara automáticamente el pipeline de CI y el despliegue continuo (CD) a **Google Cloud Run** vía Cloud Build.

### Flujo Paso a Paso de Cierre:

1. **Sincronización inicial contra el remoto:**
   ```bash
   git fetch origin
   git pull --ff-only origin main
   ```
2. **Bump de versión coordinado (`X.Y.Z`):**
   - `backend/app/core/config.py` (`VERSION = "X.Y.Z"`)
   - `frontend/package.json` (`"version": "X.Y.Z"`)
   - `README.md` (Badge de versión y tests)
   - `MANUAL_TECNICO.md` (`**Versión:** X.Y.Z`)
   - `CHANGELOG.md` (Entrada `## [X.Y.Z] — YYYY-MM-DD` con resumen, notas y atribución del modelo)
3. **Verificación Integral (Frenar inmediatamente si algo falla):**
   - **Backend Pytest:** `cd backend && .\venv\Scripts\pytest -v` (100% pasando).
   - **Backend Ruff Linter:** `.\venv\Scripts\ruff.exe check app --line-length 120 --ignore B008` (0 errores).
   - **Backend Black Formatter:** `.\venv\Scripts\black.exe --check app --line-length 120` (0 diferencias).
   - **Backend Bandit SAST:** `.\venv\Scripts\bandit.exe -r app -q -ll` (0 vulnerabilidades).
   - **Frontend Vitest:** `cd frontend && npm test` (100% pasando).
   - **Frontend Build (TS Estricto + Vite):** `npm run build` (0 errores).
4. **Commit Convencional:**
   ```bash
   git add .
   git commit -m "feat(vX.Y.Z): <descripción concisa de la entrega>"
   ```
5. **Push a `main`:**
   ```bash
   git push origin main
   ```
6. **Tag Anotado:**
   ```bash
   git tag -a vX.Y.Z -m "vX.Y.Z — <resumen de la release>"
   git push origin vX.Y.Z
   ```
7. **Publicación de GitHub Release con `gh` CLI:**
   ```bash
   gh release create vX.Y.Z --title "vX.Y.Z — <título descriptivo>" --notes "<notas de versión extraídas de CHANGELOG.md>"
   ```
8. **Deploy a Cloud Run:**
   - Automático: Disparado por Cloud Build trigger en cada push a `main`.
9. **Handoff en el Chat:**
   - Entregar el bloque de handoff formateado en el último mensaje de la sesión.

---

## 🛑 Regla Anti-HANDOFF en Repositorio

El handoff es un **mensaje en el chat**, **NUNCA un archivo en el repositorio**. No crees archivos como `HANDOFF_*.md`, `SESSION_*.md` ni notas temporales dentro del árbol de código.

### Formato del Handoff (Último mensaje, dentro de un bloque de código):

```text
## Handoff — vX.Y.Z (YYYY-MM-DD)
- **Repo:** migueljerico/dataflow-ai · **Rama:** main · **HEAD:** <hash corto> · **Tag:** vX.Y.Z · **Release:** Publicado
- **Cerrado:** <Resumen claro de lo completado en 1-3 frases>
- **Próximo trabajo priorizado:**
  1. <Siguiente ítem de evolución técnica o negocio>
- **Reglas de sesión:** Gobernanza estricta ("La IA propone, el usuario decide, Python ejecuta"); i18n español/inglés; suite de tests al 100%; push+tag+release automáticos al cerrar.
```

---

## 🛠️ Quick Reference — Comandos de Verificación

```bash
# Backend (desde /backend)
.\venv\Scripts\pytest -v                                        # Ejecutar suite de pruebas
.\venv\Scripts\ruff.exe check app --line-length 120 --ignore B008 # Linter rápido
.\venv\Scripts\black.exe --check app --line-length 120           # Formato de código
.\venv\Scripts\bandit.exe -r app -q -ll                         # SAST de seguridad

# Frontend (desde /frontend)
npm test                                                       # Tests unitarios con Vitest
npm run build                                                  # Typecheck TS y compilación Vite
```
