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

import pandas as pd

from app.core.number_parsing import get_numeric_parseable_ratio

FRACTION_RANGE = (0.0, 1.0)
PERCENTAGE_RANGE = (0.0, 100.0)

# Hints que nunca deben recibir normalización de casing destructiva.
PROTECTED_FROM_CASING = {"id", "email", "phone", "date"}

# Cardinalidad máxima de una columna categórica para proponer imputación por moda.
MODE_CARDINALITY_LIMIT = 20

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


def missing_policy(semantic_hint: str, column: str, null_count: int, series: Any = None) -> Dict[str, Any]:
    """
    Política de nulos. La propuesta por defecto es una corrección ejecutable
    que el humano aprueba o rechaza desde el plan (nunca se ejecuta sola):

    - id/email/phone: flag_for_review con keep_null (no se inventa identidad).
    - columna numérica: fill_missing con mediana.
    - texto de baja cardinalidad: fill_missing con moda.
    - texto de alta cardinalidad o sin serie: flag_for_review (no hay valor
      representativo fiable; jamás se propone el constante "Desconocido").
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
    if series is not None:
        try:
            s = pd.Series(series)
            non_null = s.dropna()
            if len(non_null) > 0:
                ratio, _, total_real = get_numeric_parseable_ratio(s)
                if total_real > 0 and ratio >= 0.8:
                    return {
                        "action": "fill_missing",
                        "strategy": "median",
                        "value": None,
                        "risk": "medium",
                        "reason": (
                            f"Se han detectado {null_count} valor(es) ausente(s) en '{column}' (numérica). "
                            "Propuesta: imputar con la mediana ('fill_missing' strategy=median). "
                            "Se ejecutará solo si apruebas el plan; si prefieres mantener NULL u otra "
                            "estrategia, rechaza o edita este paso."
                        ),
                    }
                if non_null.nunique() <= MODE_CARDINALITY_LIMIT:
                    mode_val = non_null.mode()
                    mode_repr = str(mode_val.iloc[0]) if len(mode_val) > 0 else "el valor más frecuente"
                    return {
                        "action": "fill_missing",
                        "strategy": "mode",
                        "value": None,
                        "risk": "medium",
                        "reason": (
                            f"Se han detectado {null_count} valor(es) ausente(s) en '{column}' (categórica). "
                            f"Propuesta: imputar con la moda ('fill_missing' strategy=mode; valor más frecuente: "
                            f"'{mode_repr}'). Se ejecutará solo si apruebas el plan."
                        ),
                    }
        except Exception:
            pass
    return {
        "action": "flag_for_review",
        "strategy": "keep_null",
        "value": None,
        "risk": "medium",
        "reason": (
            f"Se han detectado {null_count} valor(es) ausente(s) en '{column}' (texto de alta cardinalidad). "
            "No existe un valor representativo fiable: se propone mantener NULL y revisar manualmente."
        ),
    }


def negative_policy(column: str, neg_count: int) -> Dict[str, Any]:
    """
    Política de negativos: propone la corrección ejecutable (clamp al mínimo 0)
    que el humano aprueba o rechaza desde el plan. Nunca se ejecuta sola: si los
    negativos son legítimos (devoluciones, ajustes), el paso se rechaza.
    """
    return {
        "action": "clamp_range",
        "parameters": {"column": column, "min_value": 0.0},
        "risk": "medium",
        "reason": (
            f"Se han detectado {neg_count} valor(es) negativo(s) en '{column}'. "
            "Propuesta de corrección: acotar al mínimo 0 ('clamp_range' min=0). "
            "Se ejecutará solo si apruebas el plan; si los negativos son legítimos "
            "(devoluciones o ajustes contables), rechaza este paso."
        ),
    }


def fraction_policy(column: str, out_count: int) -> Dict[str, Any]:
    """Política de fracciones [0, 1]: propuesta de corrección acotando al rango."""
    return {
        "action": "clamp_range",
        "range": list(FRACTION_RANGE),
        "parameters": {"column": column, "min_value": 0.0, "max_value": 1.0},
        "risk": "medium",
        "reason": (
            f"Se han detectado {out_count} valor(es) fuera del intervalo de negocio "
            f"[0, 1] en '{column}' (fracción/descuento). Propuesta de corrección: acotar al "
            "intervalo ('clamp_range' [0.0, 1.0]). Se ejecutará solo si apruebas el plan."
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
