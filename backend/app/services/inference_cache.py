import copy
import hashlib
import json
import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

from app.ai_providers.base import AIMetrics, AISuggestionResponse


class InferenceCacheService:
    """
    Servicio de cache de inferencia semantica y de esquemas para LLM (Gemini / Copilot).
    Permite reutilizar planes y sugerencias de transformacion sobre datasets con esquemas
    identicos o estructuralmente equivalentes, reduciendo la latencia de ~2000ms a <1ms
    y eliminando el 100% de los costes de tokens en llamadas redundantes.
    """

    DEFAULT_TTL_SECONDS: float = 86400.0  # 24 horas
    MAX_ENTRIES: int = 500

    _cache: "OrderedDict[str, Tuple[float, AISuggestionResponse]]" = OrderedDict()
    _lock: threading.Lock = threading.Lock()

    # Metricas agregadas de observabilidad
    _hits: int = 0
    _misses: int = 0
    _saved_tokens: int = 0
    _saved_cost_usd: float = 0.0

    @classmethod
    def compute_cache_key(
        cls,
        columns_schema: List[Dict[str, Any]],
        quality_issues: List[Dict[str, Any]],
        model: str,
        provider: str = "gemini",
    ) -> str:
        """
        Calcula una huella canonica determinista (SHA-256) basada en:
        - Estructura de columnas (nombres normalizados, tipos inferidos, hints semanticos).
        - Patron de problemas de calidad detectados (columna, dimension, severidad).
        - Modelo y proveedor de IA seleccionado.
        """
        norm_cols = sorted(
            [
                (
                    str(c.get("name", "")).strip().lower(),
                    str(c.get("type", "")).strip().lower(),
                    str(c.get("semantic_hint", "")).strip().lower(),
                )
                for c in columns_schema
            ]
        )

        norm_issues = sorted(
            [
                (
                    str(i.get("column", "")).strip().lower() if i.get("column") else "",
                    str(i.get("dimension", "")).strip().lower(),
                    str(i.get("severity", "")).strip().lower(),
                )
                for i in quality_issues
            ]
        )

        fingerprint = {
            "version": 1,
            "provider": provider.strip().lower(),
            "model": model.strip().lower(),
            "columns": norm_cols,
            "issues": norm_issues,
        }

        canonical_json = json.dumps(fingerprint, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    @classmethod
    def get(cls, key: str, ttl_seconds: Optional[float] = None) -> Optional[AISuggestionResponse]:
        """
        Obtiene una respuesta cacheada si existe y no ha expirado.
        Si hay hit, clona la respuesta y ajusta las metricas para reflejar la latencia del lookup
        y el ahorro del 100% de coste en la llamada.
        """
        ttl = ttl_seconds if ttl_seconds is not None else cls.DEFAULT_TTL_SECONDS
        now = time.time()

        with cls._lock:
            if key not in cls._cache:
                cls._misses += 1
                return None

            timestamp, cached_resp = cls._cache[key]
            if (now - timestamp) > ttl:
                del cls._cache[key]
                cls._misses += 1
                return None

            # Reordenar para politica LRU
            cls._cache.move_to_end(key)
            cls._hits += 1

            orig_metrics = cached_resp.metrics
            if orig_metrics:
                cls._saved_tokens += orig_metrics.total_tokens
                cls._saved_cost_usd += orig_metrics.estimated_cost_usd

            # Clonar profundamente para no mutar el objeto en cache
            response_copy = copy.deepcopy(cached_resp)

            # Actualizar metricas para la respuesta servida
            response_copy.metrics = AIMetrics(
                latency_ms=0.5,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                estimated_cost_usd=0.0,
                model=orig_metrics.model if orig_metrics else "cached",
                provider=orig_metrics.provider if orig_metrics else "cache",
                cached=True,
            )

            return response_copy

    @classmethod
    def set(cls, key: str, response: AISuggestionResponse) -> None:
        """
        Almacena una respuesta de inferencia en la cache.
        """
        now = time.time()
        with cls._lock:
            if key in cls._cache:
                cls._cache.move_to_end(key)
            cls._cache[key] = (now, copy.deepcopy(response))

            # Eviccion LRU si se supera la capacidad maxima
            while len(cls._cache) > cls.MAX_ENTRIES:
                cls._cache.popitem(last=False)

    @classmethod
    def clear(cls) -> None:
        """Limpia la cache y reinicia los contadores (util para pruebas unitarias)."""
        with cls._lock:
            cls._cache.clear()
            cls._hits = 0
            cls._misses = 0
            cls._saved_tokens = 0
            cls._saved_cost_usd = 0.0

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Devuelve estadisticas operativas del servicio de cache."""
        with cls._lock:
            total_requests = cls._hits + cls._misses
            hit_rate = round((cls._hits / total_requests) * 100, 2) if total_requests > 0 else 0.0
            return {
                "hits": cls._hits,
                "misses": cls._misses,
                "total_requests": total_requests,
                "hit_rate_pct": hit_rate,
                "cached_entries": len(cls._cache),
                "saved_tokens": cls._saved_tokens,
                "saved_cost_usd": round(cls._saved_cost_usd, 6),
            }
