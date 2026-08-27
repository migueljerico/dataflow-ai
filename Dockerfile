# ─────────────────────────────────────────────────────────────────────────────
# DataFlow AI — Multi-stage Production Dockerfile
# Contenedor unificado para Google Cloud Run: Frontend React (Vite) + Backend FastAPI
# ─────────────────────────────────────────────────────────────────────────────

# ── Stage 1: Build React Frontend (Vite + TypeScript) ──────────────────────
FROM node:20-alpine AS builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ── Stage 2: Production Python Backend + Static SPA ────────────────────────
FROM python:3.11-slim AS production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app

# Instalar dependencias backend
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código backend
COPY backend/app ./app
RUN mkdir -p ./uploads

# Copiar frontend compilado desde Stage 1 a /app/static
COPY --from=builder /app/frontend/dist ./static

RUN groupadd -r app && useradd -r -g app app && chown -R app:app /app
USER app

EXPOSE 8080

# Health check para Cloud Run
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:' + str(__import__('os').environ.get('PORT', 8080)) + '/health')" || exit 1

# Uvicorn escucha en $PORT inyectado dinámicamente por Cloud Run
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]