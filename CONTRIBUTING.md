# Contributing — DataFlow AI

## Setup rápido

```bash
git clone https://github.com/migueljerico/dataflow-ai.git && cd dataflow-ai
cd backend && pip install -r requirements.txt && pytest -q
cd ../frontend && npm ci && npx tsc --noEmit && npm run build
```

## Ramas

- `main` protegida: requiere `Backend Tests`, `Frontend Build & Typecheck`, `Secret Scan (Gitleaks)`, `Docker Build Check` en verde.
- Rama feature: `feat/<slug>` o `fix/<slug>` → PR a `main` con Conventional Commits.

## CI

- Backend: `pytest --tb=short -q` + ruff/black/bandit no bloqueantes.
- Frontend: `tsc --noEmit` + `vite build` + dependabot weekly.
- Secrets: `gitleaks` en toda la historia.

## Documentación

Actualiza `README.md`, `MANUAL_TECNICO.md`, `CHANGELOG.md` (Keep a Changelog) y `ROADMAP.md` en cada release. Atribución a colaboradores externos obligatoria en release notes.

*Guía creada por Muse Spark 1.2 Contributor (v1.2.4).*
