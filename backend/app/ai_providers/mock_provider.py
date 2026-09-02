import re
import time
from typing import Any, Dict, List

from app.ai_providers.base import AIMetrics, AIOperationSuggestion, AISuggestionResponse, LLMProvider
from app.core.number_parsing import is_missing_value
from app.core.semantics import is_id_or_code_column, is_percentage_or_score_column


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
                    s.column == col and s.operation == "normalize_case" for s in suggestions
                ):
                    suggestions.append(
                        AIOperationSuggestion(
                            operation="normalize_case",
                            column=col,
                            parameters={"column": col, "mode": "title"},
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
                elif ("negativos" in desc.lower() or "negativo" in desc.lower()) and not any(
                    s.column == col and s.operation == "clamp_range" for s in suggestions
                ):
                    suggestions.append(
                        AIOperationSuggestion(
                            operation="clamp_range",
                            column=col,
                            parameters={"column": col, "min_value": 0, "max_value": None},
                            reason=f"Se detectó un valor numérico negativo ilógico en '{col}'. Se acota el piso mínimo a 0 para no distorsionar los agregados de negocio.",
                            confidence=0.94,
                            risk="medium",
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

            # A. Nombres, personas, entidades o categorías de texto (excluyendo IDs)
            is_name_or_cat = not is_id_col and (
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

            # C. Columnas cuantitativas con valores fuera de rango
            if is_quant and not any(s.column == col_name and s.operation == "clamp_range" for s in suggestions):
                sample_vals = [str(r.get(col_name, "")).strip() for r in sample_rows if r.get(col_name)]
                clean_nums = []
                for v in sample_vals:
                    cleaned_str = re.sub(r"[^\d.-]", "", v.replace(",", "."))
                    try:
                        clean_nums.append(float(cleaned_str))
                    except ValueError:
                        pass

                is_pct = hint == "percentage" or is_percentage_or_score_column(col_name)
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
                elif not is_pct and any(n < 0 for n in clean_nums):
                    suggestions.append(
                        AIOperationSuggestion(
                            operation="clamp_range",
                            column=col_name,
                            parameters={"column": col_name, "min_value": 0, "max_value": None},
                            reason=f"Acotar valores negativos imposibles (< 0) en '{col_name}' al límite mínimo 0.",
                            confidence=0.93,
                            risk="medium",
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
