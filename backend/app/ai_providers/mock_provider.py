import re
import time
from typing import Any, Dict, List

from app.ai_providers.base import AIMetrics, AIOperationSuggestion, AISuggestionResponse, LLMProvider
from app.core.number_parsing import is_missing_value
from app.core.semantics import (
    is_fraction_or_discount_column,
    is_id_or_code_column,
    is_percentage_or_score_column,
)
from app.core.transformation_policy import build_review_step, casing_policy


class MockProvider(LLMProvider):
    provider_name = "mock"

    async def suggest_transformations(
        self,
        filename: str,
        columns_schema: List[Dict[str, Any]],
        quality_issues: List[Dict[str, Any]],
        sample_rows: List[Dict[str, Any]],
    ) -> AISuggestionResponse:
        start_time = time.perf_counter()
        suggestions: List[AIOperationSuggestion] = []

        # 1. Sugerencias basadas en Quality Issues
        for issue in quality_issues:
            col = issue.get("column")
            dim = issue.get("dimension")
            desc = issue.get("description", "")

            if dim == "uniqueness":
                suggestions.append(
                    AIOperationSuggestion(
                        operation="remove_duplicates",
                        column=None,
                        parameters={},
                        reason="La IA ha detectado registros duplicados idénticos que distorsionan el análisis. Se recomienda conservarlos una sola vez.",
                        confidence=0.98,
                        risk="high",
                    )
                )
            elif dim == "consistency" and col:
                if "espacios" in desc.lower() and not any(
                    s.column == col and s.operation == "trim_text" for s in suggestions
                ):
                    suggestions.append(
                        AIOperationSuggestion(
                            operation="trim_text",
                            column=col,
                            parameters={"column": col},
                            reason=f"Se identificaron espacios innecesarios al inicio/final en '{col}'. Se sugiere eliminarlos.",
                            confidence=0.95,
                            risk="low",
                        )
                    )
                elif ("mayúsculas" in desc.lower() or "formato" in desc.lower()) and not any(
                    s.column == col and s.operation in ("normalize_case", "normalize_category") for s in suggestions
                ):
                    col_info = next((c for c in columns_schema if c.get("name") == col), {})
                    policy = casing_policy(col_info.get("semantic_hint", "unknown"))
                    if not policy["allow_normalize_case"]:
                        payload = build_review_step(
                            col,
                            f"Se detectó inconsistencia de formato en '{col}', pero {policy['reason']} "
                            "No se propone normalize_case: queda marcado para revisión humana.",
                            context={"kind": "casing_skipped"},
                        )
                        suggestions.append(
                            AIOperationSuggestion(
                                operation=payload["operation"],
                                column=payload["column"],
                                parameters=payload["parameters"],
                                reason=payload["reason"],
                                confidence=0.9,
                                risk="high",
                            )
                        )
                    else:
                        modes = policy["allowed_modes"] or ["title"]
                        suggestions.append(
                            AIOperationSuggestion(
                                operation="normalize_case",
                                column=col,
                                parameters={"column": col, "mode": "title" if "title" in modes else modes[0]},
                                reason=f"Para homogeneizar el análisis por categorías o nombres de entidad, se sugiere convertir '{col}' a Title Case (preservando siglas de negocio como SA/SL).",
                                confidence=0.92,
                                risk="low",
                            )
                        )
            elif dim == "validity" and col:
                if "fecha" in desc.lower() and not any(
                    s.column == col and s.operation == "convert_datetime" for s in suggestions
                ):
                    suggestions.append(
                        AIOperationSuggestion(
                            operation="convert_datetime",
                            column=col,
                            parameters={"column": col, "target_format": "%Y-%m-%d"},
                            reason=f"Existen múltiples formatos de fecha en '{col}'. Se estandarizará a ISO 8601 (%Y-%m-%d) diferenciando fechas ISO YYYY-MM-DD y europeas DD/MM/AAAA sin traslapes ni pérdidas.",
                            confidence=0.96,
                            risk="medium",
                        )
                    )
                elif (
                    "símbolos" in desc.lower() or "cuantitativa" in desc.lower() or "marcadores" in desc.lower()
                ) and not any(s.column == col and s.operation == "convert_numeric" for s in suggestions):
                    suggestions.append(
                        AIOperationSuggestion(
                            operation="convert_numeric",
                            column=col,
                            parameters={"column": col},
                            reason=f"La columna '{col}' contiene formato texto, símbolos (€/$) o marcadores N/D / N/A. Se sugiere limpiar símbolos y asignar NaN para permitir tipado float64 en Power BI.",
                            confidence=0.95,
                            risk="medium",
                        )
                    )
            elif dim == "integrity" and col:
                col_info = next((c for c in columns_schema if c.get("name") == col), {})
                hint = col_info.get("semantic_hint", "unknown")
                is_pct = hint == "percentage" or "porcentual" in desc.lower() or is_percentage_or_score_column(col)
                is_fraction = hint == "fraction" or (hint != "percentage" and is_fraction_or_discount_column(col))

                if is_pct and not any(s.column == col and s.operation == "clamp_range" for s in suggestions):
                    suggestions.append(
                        AIOperationSuggestion(
                            operation="clamp_range",
                            column=col,
                            parameters={"column": col, "min_value": 0.0, "max_value": 100.0},
                            reason=f"Se detectó un valor fuera de rango en la columna porcentual '{col}'. Se acota el rango completo al intervalo de negocio [0.0, 100.0%].",
                            confidence=0.95,
                            risk="medium",
                        )
                    )
                elif is_fraction and not any(
                    s.column == col and s.operation in ("clamp_range", "flag_for_review") for s in suggestions
                ):
                    payload = build_review_step(
                        col,
                        f"⚠️ REVISIÓN HUMANA — Se detectaron valores fuera del intervalo [0, 1] en '{col}' "
                        "(fracción/descuento). Requiere revisión humana; no se modifica automáticamente.",
                        context={"kind": "fraction_out_of_range", "range": [0.0, 1.0]},
                    )
                    suggestions.append(
                        AIOperationSuggestion(
                            operation=payload["operation"],
                            column=payload["column"],
                            parameters=payload["parameters"],
                            reason=payload["reason"],
                            confidence=0.9,
                            risk="high",
                        )
                    )
                elif ("negativos" in desc.lower() or "negativo" in desc.lower()) and not any(
                    s.column == col and s.operation in ("clamp_range", "flag_for_review") for s in suggestions
                ):
                    payload = build_review_step(
                        col,
                        f"⚠️ REVISIÓN HUMANA — Se detectaron valores negativos en '{col}'. El sistema no puede "
                        "inferir el valor correcto: requiere revisión humana. No se propone conversión automática a 0.",
                        context={"kind": "negative_values", "condition": f"{col} < 0"},
                    )
                    suggestions.append(
                        AIOperationSuggestion(
                            operation=payload["operation"],
                            column=payload["column"],
                            parameters=payload["parameters"],
                            reason=payload["reason"],
                            confidence=0.9,
                            risk="high",
                        )
                    )
                elif (
                    "superiores" in desc.lower() or "rango" in desc.lower() or "porcentual" in desc.lower()
                ) and not any(s.column == col and s.operation == "clamp_range" for s in suggestions):
                    suggestions.append(
                        AIOperationSuggestion(
                            operation="clamp_range",
                            column=col,
                            parameters={"column": col, "min_value": 0.0, "max_value": 100.0},
                            reason=f"Se detectó un valor fuera de rango en '{col}'. Se acota al intervalo de negocio [0.0, 100.0%].",
                            confidence=0.94,
                            risk="medium",
                        )
                    )

        # 2. Heurística Semántica Universal sobre las Columnas del Dataset
        for col_info in columns_schema:
            col_name = col_info.get("name", "")
            col_lower = col_name.lower().strip()
            hint = col_info.get("semantic_hint", "unknown")
            dtype = col_info.get("inferred_type", "text")

            is_id_col = hint == "id" or is_id_or_code_column(col_name)
            # Columnas protegidas por política semántica: nunca normalize_case
            # destructivo (email solo admite lower, y únicamente con regla clara).
            is_protected_col = hint in ("email", "phone", "date", "fraction")

            # A. Nombres, personas, entidades o categorías de texto (excluyendo IDs y protegidas)
            is_name_or_cat = (
                not is_id_col
                and not is_protected_col
                and (
                    hint in ["name", "location"]
                    or any(
                        k in col_lower
                        for k in [
                            "nombre",
                            "cliente",
                            "empleado",
                            "agente",
                            "comercial",
                            "contacto",
                            "usuario",
                            "canal",
                            "categoria",
                            "departamento",
                            "ciudad",
                            "pais",
                        ]
                    )
                )
            )
            if is_name_or_cat and not any(
                s.column == col_name and s.operation == "normalize_case" for s in suggestions
            ):
                # Verificar en sample_rows si hay mayúsculas
                sample_vals = [str(r.get(col_name, "")) for r in sample_rows if r.get(col_name)]
                if any(len(v.strip()) > 2 and v.strip().isupper() for v in sample_vals):
                    suggestions.append(
                        AIOperationSuggestion(
                            operation="normalize_case",
                            column=col_name,
                            parameters={"column": col_name, "mode": "title"},
                            reason=f"Normalizar '{col_name}' a Title Case consistente (ej. CARLOS MENDOZA ➔ Carlos Mendoza, SOPORTE RRHH SL ➔ Soporte RRHH SL).",
                            confidence=0.92,
                            risk="low",
                        )
                    )

            # B. Columnas cuantitativas con marcadores N/D, N/A, comas decimales o símbolos
            is_quant = not is_id_col and (
                hint in ["currency", "percentage"]
                or dtype == "numeric"
                or any(
                    k in col_lower
                    for k in [
                        "precio",
                        "salario",
                        "sueldo",
                        "gasto",
                        "coste",
                        "horas",
                        "dias",
                        "cantidad",
                        "unidades",
                        "llamadas",
                        "aht",
                        "segundos",
                        "minutos",
                        "monto",
                        "importe",
                        "facturacion",
                        "stock",
                        "descuento",
                    ]
                )
            )
            if is_quant and not any(s.column == col_name and s.operation == "convert_numeric" for s in suggestions):
                sample_vals = [str(r.get(col_name, "")).strip() for r in sample_rows if r.get(col_name) is not None]
                has_dirty = any(
                    is_missing_value(v)
                    or any(sym in v for sym in ["€", "$", "%", "usd", "eur"])
                    or bool(re.search(r"\d,\d", v))
                    for v in sample_vals
                )
                if has_dirty:
                    suggestions.append(
                        AIOperationSuggestion(
                            operation="convert_numeric",
                            column=col_name,
                            parameters={"column": col_name},
                            reason=f"Convertir '{col_name}' a numérico puro float64 estandarizando separadores regionales y asignando NaN a marcadores de ausencia para Power BI.",
                            confidence=0.95,
                            risk="medium",
                        )
                    )

            # C. Columnas cuantitativas con valores fuera de rango.
            # Porcentajes [0,100] sí se acotan; fracciones [0,1] y negativos
            # genéricos van a revisión humana (nunca clamp silencioso a 0).
            if is_quant and not any(
                s.column == col_name and s.operation in ("clamp_range", "flag_for_review") for s in suggestions
            ):
                sample_vals = [str(r.get(col_name, "")).strip() for r in sample_rows if r.get(col_name)]
                clean_nums = []
                for v in sample_vals:
                    cleaned_str = re.sub(r"[^\d.-]", "", v.replace(",", "."))
                    try:
                        clean_nums.append(float(cleaned_str))
                    except ValueError:
                        pass

                is_pct = hint == "percentage" or is_percentage_or_score_column(col_name)
                is_fraction = hint == "fraction" or (hint != "percentage" and is_fraction_or_discount_column(col_name))
                if is_pct and (any(n > 100.0 for n in clean_nums) or any(n < 0 for n in clean_nums)):
                    suggestions.append(
                        AIOperationSuggestion(
                            operation="clamp_range",
                            column=col_name,
                            parameters={"column": col_name, "min_value": 0.0, "max_value": 100.0},
                            reason=f"Acotar valores fuera de rango en la columna porcentual '{col_name}' al intervalo de negocio [0.0, 100.0%].",
                            confidence=0.94,
                            risk="medium",
                        )
                    )
                elif is_fraction and (any(n > 1.0 for n in clean_nums) or any(n < 0 for n in clean_nums)):
                    payload = build_review_step(
                        col_name,
                        f"⚠️ REVISIÓN HUMANA — Se detectaron valores fuera del intervalo [0, 1] en '{col_name}' "
                        "(fracción/descuento). Requiere revisión humana; no se modifica automáticamente.",
                        context={"kind": "fraction_out_of_range", "range": [0.0, 1.0]},
                    )
                    suggestions.append(
                        AIOperationSuggestion(
                            operation=payload["operation"],
                            column=payload["column"],
                            parameters=payload["parameters"],
                            reason=payload["reason"],
                            confidence=0.9,
                            risk="high",
                        )
                    )
                elif not is_pct and not is_fraction and any(n < 0 for n in clean_nums):
                    payload = build_review_step(
                        col_name,
                        f"⚠️ REVISIÓN HUMANA — Se detectaron valores negativos en '{col_name}'. El sistema no puede "
                        "inferir el valor correcto: requiere revisión humana. No se propone conversión automática a 0.",
                        context={"kind": "negative_values", "condition": f"{col_name} < 0"},
                    )
                    suggestions.append(
                        AIOperationSuggestion(
                            operation=payload["operation"],
                            column=payload["column"],
                            parameters=payload["parameters"],
                            reason=payload["reason"],
                            confidence=0.9,
                            risk="high",
                        )
                    )

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        # Estimación realista de tokens para MockProvider
        estimated_prompt_tokens = max(120, len(str(columns_schema) + str(quality_issues) + str(sample_rows)) // 4)
        estimated_completion_tokens = max(60, len(str(suggestions)) // 4)
        total_tokens = estimated_prompt_tokens + estimated_completion_tokens
        metrics = AIMetrics(
            latency_ms=elapsed_ms,
            prompt_tokens=estimated_prompt_tokens,
            completion_tokens=estimated_completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=0.0,
            model="mock-deterministic",
            provider=self.provider_name,
        )

        return AISuggestionResponse(
            dataset_summary=f"Dataset '{filename}' analizado por el Copiloto de IA mediante heurística semántica de negocio.",
            suggestions=suggestions,
            warnings=["Sugerencia generada por el proveedor MockProvider mediante análisis semántico generalizado."],
            metrics=metrics,
        )
