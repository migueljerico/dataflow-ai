"""
Política central de transformación semántica (transformation policy).

Conecta el `semantic_hint` del profiler con el motor de propuestas ETL:
dado un hint y el nombre de la columna, decide qué familias de operaciones
están permitidas y con qué parámetros. Toda la generación de propuestas
(reglas deterministas, MockProvider, guardrails de IA) debe consultar este
módulo en lugar de replicar heurísticas ad hoc.

Filosofía: la IA propone, el usuario decide, Python ejecuta. Las políticas
"review" no modifican datos: generan un paso de marcaje
(`flag_for_review`) pendiente de aprobación humana explícita.
"""

from typing import Any, Dict, List, Optional

FRACTION_RANGE = (0.0, 1.0)
PERCENTAGE_RANGE = (0.0, 100.0)

# Hints que nunca deben recibir normalización de casing destructiva.
PROTECTED_FROM_CASING = {"id", "email", "phone", "date"}

# Valor que marca visualmente una imputación/semilla pendiente de revisión.
REVIEW_PLACEHOLDER_PREFIX = "[REVISAR]"


def casing_policy(semantic_hint: str) -> Dict[str, Any]:
    """
    Devuelve la política de casing para un hint semántico.

    - id/phone/date: prohibido cualquier normalize_case.
    - email: solo se permite mode="lower" (nunca title/upper).
    - resto: se permite title/lower/upper según propuesta.
    """
    hint = (semantic_hint or "unknown").lower()
    if hint in ("id", "phone", "date"):
        return {
            "allow_normalize_case": False,
            "allowed_modes": [],
            "reason": f"La columna tiene semántica '{hint}': queda protegida frente a normalize_case.",
        }
    if hint == "email":
        return {
            "allow_normalize_case": True,
            "allowed_modes": ["lower"],
            "reason": "Los emails solo admiten normalización a minúsculas; Title/Upper Case los corrompe.",
        }
    return {"allow_normalize_case": True, "allowed_modes": ["title", "lower", "upper"], "reason": ""}


def missing_policy(semantic_hint: str, column: str, null_count: int) -> Dict[str, Any]:
    """
    Política de nulos: ninguna columna recibe imputación silenciosa a
    "Desconocido" por defecto. Las columnas sensibles (email, id, phone)
    proponen mantener NULL + revisión humana; el resto propone revisión
    con estrategias sugeridas pero sin ejecutar nada sin aprobación.
    """
    hint = (semantic_hint or "unknown").lower()
    sensitive = hint in ("email", "id", "phone")
    if sensitive:
        return {
            "action": "flag_for_review",
            "strategy": "keep_null",
            "value": None,
            "risk": "high",
            "reason": (
                f"Se han detectado {null_count} valor(es) ausente(s) en '{column}' "
                f"(semántica {hint}). No se recomienda inventar un valor: se propone "
                "mantener NULL y solicitar revisión humana."
            ),
        }
    return {
        "action": "flag_for_review",
        "strategy": "pending_decision",
        "value": None,
        "risk": "medium",
        "reason": (
            f"Se han detectado {null_count} valor(es) ausente(s) en '{column}'. "
            "El sistema no imputa automáticamente: el usuario debe elegir entre "
            "mantener NULL, mediana/moda o un valor constante explícito."
        ),
    }


def negative_policy(column: str, neg_count: int) -> Dict[str, Any]:
    """Política de negativos: detección + revisión humana, nunca corrección a 0."""
    return {
        "action": "flag_for_review",
        "risk": "high",
        "reason": (
            f"Se han detectado {neg_count} valor(es) negativo(s) en '{column}'. "
            "El sistema no puede inferir el valor correcto (error de origen, "
            "devolución, ajuste o dato corrupto): requiere revisión humana. "
            "No se propone conversión automática a 0."
        ),
    }


def fraction_policy(column: str, out_count: int) -> Dict[str, Any]:
    """Política de fracciones [0, 1]: detección + revisión humana."""
    return {
        "action": "flag_for_review",
        "range": list(FRACTION_RANGE),
        "risk": "high",
        "reason": (
            f"Se han detectado {out_count} valor(es) fuera del intervalo de negocio "
            f"[0, 1] en '{column}' (fracción/descuento). Requiere revisión humana."
        ),
    }


def build_review_step(
    column: Optional[str],
    reason: str,
    affected_rows: int = 0,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Construye el payload de un paso de marcaje para revisión humana."""
    params: Dict[str, Any] = {"column": column, "context": context or {}}
    return {
        "operation": "flag_for_review",
        "column": column,
        "parameters": params,
        "reason": reason,
        "confidence": 0.9,
        "risk": "high",
        "affected_rows_estimate": affected_rows,
    }


def country_mappings(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Diccionario base de equivalencias de país (ISO + nativo + variantes de
    casing) hacia la etiqueta canónica en inglés del dataset. Extensible:
    el llamante puede añadir o sobrescribir entradas sin tocar el motor.
    """
    base: Dict[str, str] = {}
    base.update(
        {
            "ES": "Spain",
            "Espa\u00f1a": "Spain",
            "SPAIN": "Spain",
            "spain": "Spain",
            "FR": "France",
            "Francia": "France",
            "FRANCE": "France",
            "DE": "Germany",
            "Alemania": "Germany",
            "GERMANY": "Germany",
            "IT": "Italy",
            "Italia": "Italy",
            "ITALY": "Italy",
            "PT": "Portugal",
            "Portugal": "Portugal",
            "PORTUGAL": "Portugal",
            "BE": "Belgium",
            "Belgica": "Belgium",
            "B\u00e9lgica": "Belgium",
            "BELGIUM": "Belgium",
            "NL": "Netherlands",
            "Holanda": "Netherlands",
            "Pa\u00edses Bajos": "Netherlands",
            "Paises Bajos": "Netherlands",
            "NETHERLANDS": "Netherlands",
            "UK": "United Kingdom",
            "GB": "United Kingdom",
            "Reino Unido": "United Kingdom",
            "UNITED KINGDOM": "United Kingdom",
            "US": "United States",
            "USA": "United States",
            "Estados Unidos": "United States",
        }
    )
    if extra:
        base.update(extra)
    return base


def country_mappings_for_values(values: List[str]) -> Dict[str, str]:
    """
    Genera el diccionario {variante_detectada: canónico} solo para los valores
    presentes en la columna, de modo que normalize_category solo mapee lo
    observado (sin listas gigantes ni efectos colaterales).
    """
    canon_lookup = {k.lower(): v for k, v in country_mappings().items()}
    mappings: Dict[str, str] = {}
    for v in values:
        raw = str(v)
        canon = canon_lookup.get(raw.strip().lower())
        if canon and raw != canon:
            mappings[raw] = canon
    return mappings
