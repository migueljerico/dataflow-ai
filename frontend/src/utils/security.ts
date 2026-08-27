/**
 * DataFlow AI — Almacenamiento ofuscado de credenciales del cliente (CWE-312)
 *
 * NOTA: La clave se ofusca con Base64 (btoa) para evitar texto plano casual en
 * localStorage. NO es cifrado — cualquier XSS puede leerla. La API Key nunca
 * se persiste en el servidor ni en logs.
 */

const STORAGE_VAULT_KEY = 'dataflow_vault_key_enc';
const LEGACY_STORAGE_KEY = 'dataflow_gemini_api_key';

function encodeSecret(secret: string): string {
  try {
    return btoa(encodeURIComponent(secret));
  } catch {
    return secret;
  }
}

function decodeSecret(encoded: string): string {
  try {
    return decodeURIComponent(atob(encoded));
  } catch {
    return encoded;
  }
}

/**
 * Guarda la API Key de forma codificada en el almacenamiento local.
 */
export function saveApiKey(key: string): void {
  const clean = key.trim();
  if (clean) {
    localStorage.setItem(STORAGE_VAULT_KEY, encodeSecret(clean));
    localStorage.removeItem(LEGACY_STORAGE_KEY);
  } else {
    removeApiKey();
  }
}

/**
 * Recupera la API Key descifrándola del vault del cliente.
 * Incluye migración transparente de claves previas en texto plano.
 */
export function getApiKey(): string | null {
  const encrypted = localStorage.getItem(STORAGE_VAULT_KEY);
  if (encrypted) {
    return decodeSecret(encrypted);
  }
  // Migración de retrocompatibilidad si existía una clave previa
  const legacy = localStorage.getItem(LEGACY_STORAGE_KEY);
  if (legacy) {
    saveApiKey(legacy);
    return legacy;
  }
  return null;
}

/**
 * Elimina de forma segura cualquier credencial almacenada.
 */
export function removeApiKey(): void {
  localStorage.removeItem(STORAGE_VAULT_KEY);
  localStorage.removeItem(LEGACY_STORAGE_KEY);
}
