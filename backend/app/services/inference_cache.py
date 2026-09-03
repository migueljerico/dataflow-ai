import copy
import hashlib
import json
import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

from app.ai_providers.base import AIMetrics, AISuggestionResponse
from app.core.config import settings


class InferenceCacheService:
    """
    Servicio de cache de inferencia semantica y de esquemas para LLM (Gemini / Copilot)
    con arquitectura de dos niveles (L1 memoria + L2 Redis distribuido).

    - L1 (memoria local, LRU): latencia <1ms, siempre activo. Aislado por instancia.
    - L2 (Redis / Cloud Memorystore): persistencia distribuida opcional que permite
      compartir hits entre multiples instancias de Cloud Run. Se activa configurando
      INFERENCE_CACHE_BACKEND=redis y REDIS_URL (p.ej. rediss://memorystore:6379).

    Degradacion elegante: si el paquete `redis` no esta instalado, REDIS_URL no esta
    configurada o la conexion falla, el servicio sigue operando en modo solo-memoria
    sin interrumpir jamas la inferencia (los errores se contabilizan en metricas).
    """

    DEFAULT_TTL_SECONDS: float = 86400.0  # 24 horas
    MAX_ENTRIES: int = 500
    KEY_PREFIX: str = "dataflow:inference:v1"
    REDIS_RETRY_COOLDOWN_SECONDS: float = 30.0

    _cache: "OrderedDict[str, Tuple[float, AISuggestionResponse]]" = OrderedDict()
    _lock: threading.Lock = threading.Lock()

    # Metricas agregadas de observabilidad
    _hits: int = 0
    _misses: int = 0
    _saved_tokens: int = 0
    _saved_cost_usd: float = 0.0
    _redis_hits: int = 0
    _redis_errors: int = 0

    # Cliente Redis perezoso (L2) y estado de disponibilidad
    _redis_client: Any = None
    _redis_initialized: bool = False
    _redis_down_until: float = 0.0

    # ------------------------------------------------------------------
    # Clave canonica
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Nivel L2: Redis distribuido (opcional)
    # ------------------------------------------------------------------

    @classmethod
    def _get_redis(cls):
        """
        Resuelve el cliente Redis de forma perezosa y tolerante a fallos.
        Devuelve None si el backend configurado es memoria, si la dependencia no
        esta disponible o si la conexion esta en periodo de enfriamiento tras un error.
        """
        if settings.INFERENCE_CACHE_BACKEND != "redis" or not settings.REDIS_URL:
            return None

        if cls._redis_client is not None:
            return cls._redis_client

        now = time.time()
        if now < cls._redis_down_until:
            return None

        if cls._redis_initialized:
            return None

        try:
            import redis  # type: ignore

            client = redis.Redis.from_url(
                settings.REDIS_URL,
                socket_connect_timeout=settings.REDIS_SOCKET_TIMEOUT_SECONDS,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT_SECONDS,
                decode_responses=True,
            )
            client.ping()
            cls._redis_client = client
            return client
        except Exception:
            # Degradacion elegante: reintentar tras el cooldown sin bloquear inferencia
            cls._redis_down_until = now + cls.REDIS_RETRY_COOLDOWN_SECONDS
            cls._redis_initialized = True
            with cls._lock:
                cls._redis_errors += 1
            return None

    @classmethod
    def _serialize_payload(cls, response: AISuggestionResponse) -> str:
        return json.dumps(
            {"stored_at": time.time(), "response": response.model_dump_json()},
            separators=(",", ":"),
        )

    @classmethod
    def _deserialize_payload(cls, raw: str, ttl_seconds: float) -> Optional[AISuggestionResponse]:
        try:
            payload = json.loads(raw)
            stored_at = float(payload.get("stored_at", 0.0))
            if (time.time() - stored_at) > ttl_seconds:
                return None
            return AISuggestionResponse.model_validate_json(payload["response"])
        except Exception:
            return None

    @classmethod
    def _redis_get(cls, key: str, ttl_seconds: float) -> Optional[AISuggestionResponse]:
        client = cls._get_redis()
        if client is None:
            return None
        try:
            raw = client.get(f"{cls.KEY_PREFIX}:{key}")
        except Exception:
            cls._mark_redis_down()
            return None
        if not raw:
            return None
        response = cls._deserialize_payload(raw, ttl_seconds)
        if response is not None:
            with cls._lock:
                cls._redis_hits += 1
        return response

    @classmethod
    def _redis_set(cls, key: str, response: AISuggestionResponse, ttl_seconds: float) -> None:
        client = cls._get_redis()
        if client is None:
            return
        try:
            client.setex(
                f"{cls.KEY_PREFIX}:{key}",
                max(int(ttl_seconds), 1),
                cls._serialize_payload(response),
            )
        except Exception:
            cls._mark_redis_down()

    @classmethod
    def _mark_redis_down(cls) -> None:
        """Enfria la conexion Redis ante errores de red sin interrumpir el servicio."""
        cls._redis_down_until = time.time() + cls.REDIS_RETRY_COOLDOWN_SECONDS
        with cls._lock:
            cls._redis_errors += 1

    # ------------------------------------------------------------------
    # API publica (L1 + L2)
    # ------------------------------------------------------------------

    @classmethod
    def get(cls, key: str, ttl_seconds: Optional[float] = None) -> Optional[AISuggestionResponse]:
        """
        Obtiene una respuesta cacheada si existe y no ha expirado.
        Orden de resolucion: L1 memoria (hit caliente) -> L2 Redis (hit distribuido).
        Si hay hit, clona la respuesta y ajusta las metricas para reflejar la latencia
        del lookup y el ahorro del 100% de coste en la llamada.
        """
        ttl = ttl_seconds if ttl_seconds is not None else cls.DEFAULT_TTL_SECONDS
        now = time.time()

        with cls._lock:
            if key in cls._cache:
                timestamp, cached_resp = cls._cache[key]
                if (now - timestamp) <= ttl:
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
                del cls._cache[key]

        # L1 miss: intentar L2 Redis distribuido
        redis_response = cls._redis_get(key, ttl)
        if redis_response is not None:
            # Promover a L1 para hits calientes en esta instancia
            cls._promote_to_memory(key, redis_response)
            return cls._build_hit_response(redis_response)

        with cls._lock:
            cls._misses += 1
        return None

    @classmethod
    def _promote_to_memory(cls, key: str, response: AISuggestionResponse) -> None:
        with cls._lock:
            cls._cache[key] = (time.time(), copy.deepcopy(response))
            while len(cls._cache) > cls.MAX_ENTRIES:
                cls._cache.popitem(last=False)

    @classmethod
    def _build_hit_response(cls, cached_resp: AISuggestionResponse) -> AISuggestionResponse:
        orig_metrics = cached_resp.metrics
        with cls._lock:
            if orig_metrics:
                cls._hits += 1
                cls._saved_tokens += orig_metrics.total_tokens
                cls._saved_cost_usd += orig_metrics.estimated_cost_usd

        response_copy = copy.deepcopy(cached_resp)
        response_copy.metrics = AIMetrics(
            latency_ms=0.8,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            estimated_cost_usd=0.0,
            model=orig_metrics.model if orig_metrics else "cached",
            provider=orig_metrics.provider if orig_metrics else "redis-cache",
            cached=True,
        )
        return response_copy

    @classmethod
    def set(cls, key: str, response: AISuggestionResponse) -> None:
        """
        Almacena una respuesta de inferencia en la cache (L1 memoria y L2 Redis).
        """
        ttl = cls.DEFAULT_TTL_SECONDS
        now = time.time()
        with cls._lock:
            if key in cls._cache:
                cls._cache.move_to_end(key)
            cls._cache[key] = (now, copy.deepcopy(response))

            # Eviccion LRU si se supera la capacidad maxima
            while len(cls._cache) > cls.MAX_ENTRIES:
                cls._cache.popitem(last=False)

        # Escritura best-effort en L2 distribuido
        cls._redis_set(key, response, ttl)

    @classmethod
    def clear(cls) -> None:
        """Limpia la cache (L1 y L2) y reinicia los contadores (util para pruebas)."""
        with cls._lock:
            cls._cache.clear()
            cls._hits = 0
            cls._misses = 0
            cls._saved_tokens = 0
            cls._saved_cost_usd = 0.0
            cls._redis_hits = 0
            cls._redis_errors = 0

        client = cls._get_redis()
        if client is not None:
            try:
                keys_to_delete = list(client.scan_iter(match=f"{cls.KEY_PREFIX}:*"))
                if keys_to_delete:
                    client.delete(*keys_to_delete)
            except Exception:
                cls._mark_redis_down()

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Devuelve estadisticas operativas del servicio de cache (L1 + L2)."""
        redis_client = cls._get_redis()
        with cls._lock:
            total_requests = cls._hits + cls._misses
            l2_hits = cls._redis_hits
            l1_hits = max(0, cls._hits - l2_hits)
            total_hits = cls._hits
            hit_rate = round((total_hits / total_requests) * 100, 2) if total_requests > 0 else 0.0
            l1_hit_rate = round((l1_hits / total_requests) * 100, 2) if total_requests > 0 else 0.0
            l2_hit_rate = round((l2_hits / total_requests) * 100, 2) if total_requests > 0 else 0.0
            return {
                "backend": settings.INFERENCE_CACHE_BACKEND,
                "distributed": redis_client is not None,
                "redis_available": redis_client is not None,
                "redis_hits": l2_hits,
                "redis_errors": cls._redis_errors,
                "hits": total_hits,
                "l1_hits": l1_hits,
                "l2_hits": l2_hits,
                "misses": cls._misses,
                "total_requests": total_requests,
                "hit_rate_pct": hit_rate,
                "l1_hit_rate_pct": l1_hit_rate,
                "l2_hit_rate_pct": l2_hit_rate,
                "cached_entries": len(cls._cache),
                "saved_tokens": cls._saved_tokens,
                "saved_cost_usd": round(cls._saved_cost_usd, 6),
            }

    @classmethod
    def reset_runtime_state(cls) -> None:
        """Restablece el cliente Redis y su estado de salud (uso exclusivo en pruebas)."""
        cls._redis_client = None
        cls._redis_initialized = False
        cls._redis_down_until = 0.0
