# Security Policy — DataFlow AI

## Reportar vulnerabilidades

Si encuentras una vulnerabilidad (SSRF, IP Pinning, BYOK, XSS), escribe a **migueljerico** vía GitHub Security Advisories (tab Security → Report a vulnerability). No publiques PoCs en issues públicos antes de 90 días.

## Alcance

- `backend/app/core/security_url.py` — Anti-SSRF, IP Pinning, DNS Rebinding
- `frontend/src/utils/security.ts` — BYOK ofuscación (Base64 reversible, no cifrado)
- `backend/app/core/exceptions.py` — CWE-209 sanitizado vía `error_id`

## Buenas prácticas

- No hardcodear `GEMINI_API_KEY`; usa `X-Gemini-Api-Key` header (BYOK).
- No exponer `.env`; `.gitignore` y `.dockerignore` bloquean secretos.

*Hardening adicional por Muse Spark 1.2 Contributor (v1.2.2+).*
