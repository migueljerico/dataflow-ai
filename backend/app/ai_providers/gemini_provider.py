import json
import os
import time
from typing import Any, Dict, List, Optional

import httpx
from app.ai_providers.base import AIMetrics, AISuggestionResponse, LLMProvider
from app.core.exceptions import FunctionalException


class GeminiProvider(LLMProvider):
    provider_name = "gemini"
    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        # El modelo es configurable vía GEMINI_MODEL para adaptarse a versiones futuras
        self.model = model or os.getenv("GEMINI_MODEL", self.DEFAULT_MODEL)

    async def suggest_transformations(
        self,
        filename: str,
        columns_schema: List[Dict[str, Any]],
        quality_issues: List[Dict[str, Any]],
        sample_rows: List[Dict[str, Any]],
    ) -> AISuggestionResponse:
        if not self.api_key:
            raise FunctionalException(
                message="No se ha configurado la API Key de Google Gemini (GEMINI_API_KEY).", code="AI_API_KEY_MISSING"
            )

        prompt = f"""
Eres DataFlow AI Copilot, un experto senior en Data Analytics, Data Quality y ETL.
Analiza la estructura del dataset '{filename}' y propón un plan de transformaciones en formato JSON preparado para carga directa en Power BI.

Columnas y tipos: {json.dumps(columns_schema)}
Problemas de calidad detectados: {json.dumps(quality_issues)}
Muestra anonimizada (3 filas): {json.dumps(sample_rows[:3])}

Reglas estrictas de negocio y gobernanza:
1. SOLO puedes utilizar operaciones del catálogo permitido:
   - trim_text, normalize_case, normalize_category, convert_datetime, convert_numeric, round_numeric, clamp_range, fill_missing, remove_duplicates, rename_column, drop_column, flag_for_review.
2. Los importes y números cuantitativos pueden usar separadores europeos (1.234,56 €, 2450,75) o americanos ($1,234.56), y marcadores de ausencia ('--', 'N/D', 'N/A', '-', 'null', 'nan'); SIEMPRE deben convertirse a float64 mediante 'convert_numeric'. NUNCA propongas 'convert_numeric' sobre columnas de texto libre (notas, observaciones, descripciones).
3. NUNCA propongas 'normalize_case' sobre columnas identificadoras o códigos (ej. CustomerID, ProductID, OrderID, ID_Pedido, Cod_Cliente, SKU, CIF, DNI, o patrones como PED-123, EMP-001, CUST0001) para no degradar claves primarias ni romper JOINs. Tampoco sobre emails, teléfonos o fechas: los emails NUNCA en Title/Upper Case (solo 'lower' si hay razón clara).
4. Para columnas porcentuales o scores (hint 'percentage', o sufijos _pct, tasa, ratio), cualquier operación 'clamp_range' DEBE acotar el intervalo de negocio completo [0.0, 100.0] fijando obligatoriamente 'min_value': 0.0 y 'max_value': 100.0.
5. Las columnas de descuento/fracción (hint 'fraction': Discount, Descuento) viven en [0, 1], NO en [0, 100]: NUNCA uses 'clamp_range' sobre ellas; si hay valores fuera de [0, 1], propón 'flag_for_review' para revisión humana.
6. Los valores negativos sin regla de negocio explícita (precios, cantidades) y los nulos de texto NO se corrigen ni imputan automáticamente: propón 'flag_for_review' y deja que el humano decida (mantener, corregir manualmente, aplicar regla o marcar incidencia). NUNCA imputes nulos de texto a 'Desconocido' por defecto.
7. Los países se unifican con 'normalize_category' y diccionario de equivalencias (ES/España/SPAIN → Spain), nunca solo con casing.
8. Responde EXCLUSIVAMENTE con un objeto JSON válido con esta estructura:
{{
  "dataset_summary": "Explicación breve del dataset y su propósito operativo",
  "suggestions": [
    {{
      "operation": "nombre_operacion",
      "column": "nombre_columna",
      "parameters": {{}},
      "reason": "Explicación clara del motivo de negocio",
      "confidence": 0.95,
      "risk": "low|medium|high"
    }}
  ],
  "warnings": []
}}
"""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        # La API Key viaja en cabecera (no en la URL) para evitar su exposición en logs y proxies
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        }

        start_time = time.perf_counter()
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(url, headers=headers, json=payload)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            if res.status_code != 200:
                raise FunctionalException(
                    message="Error de comunicación con el servicio de IA de Gemini.",
                    code="AI_PROVIDER_ERROR",
                    details={"model": self.model, "status_code": res.status_code, "response": res.text[:500]},
                )

            data = res.json()

        # Observabilidad de tokens y costes de inferencia
        usage = data.get("usageMetadata") or {}
        prompt_tokens = int(usage.get("promptTokenCount", 0))
        candidates_tokens = int(usage.get("candidatesTokenCount", 0))
        total_tokens = int(usage.get("totalTokenCount", prompt_tokens + candidates_tokens))

        # Tarificación oficial Google Gemini 2.5 Flash: $0.10/1M prompt, $0.40/1M completion
        estimated_cost_usd = round((prompt_tokens * 0.10 + candidates_tokens * 0.40) / 1_000_000, 6)
        metrics = AIMetrics(
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=candidates_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost_usd,
            model=self.model,
            provider=self.provider_name,
        )

        # Respuestas bloqueadas por filtros de seguridad o sin contenido procesable
        candidates = data.get("candidates") or []
        raw_json_str = ""
        if candidates:
            parts = (candidates[0].get("content") or {}).get("parts") or []
            raw_json_str = "".join(p.get("text", "") for p in parts).strip()

        if not raw_json_str:
            raise FunctionalException(
                message="El Copiloto de IA no devolvió contenido procesable (respuesta vacía o bloqueada por filtros de seguridad).",
                code="AI_EMPTY_RESPONSE",
                details={
                    "model": self.model,
                    "block_reason": (data.get("promptFeedback") or {}).get("blockReason"),
                    "finish_reason": candidates[0].get("finishReason") if candidates else None,
                },
            )

        try:
            parsed_dict = json.loads(raw_json_str)
        except json.JSONDecodeError as exc:
            raise FunctionalException(
                message="La respuesta del Copiloto de IA no es un JSON válido.",
                code="AI_INVALID_RESPONSE",
                details={"model": self.model, "parse_error": str(exc), "raw_prefix": raw_json_str[:300]},
            ) from exc

        parsed_dict["metrics"] = metrics
        return AISuggestionResponse(**parsed_dict)
