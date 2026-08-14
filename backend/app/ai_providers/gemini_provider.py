import os
import json
import httpx
from typing import List, Dict, Any
from app.ai_providers.base import LLMProvider, AISuggestionResponse, AIOperationSuggestion
from app.core.exceptions import FunctionalException

class GeminiProvider(LLMProvider):
    provider_name = "gemini"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")

    async def suggest_transformations(
        self,
        filename: str,
        columns_schema: List[Dict[str, Any]],
        quality_issues: List[Dict[str, Any]],
        sample_rows: List[Dict[str, Any]]
    ) -> AISuggestionResponse:
        if not self.api_key:
            raise FunctionalException(
                message="No se ha configurado la API Key de Google Gemini (GEMINI_API_KEY).",
                code="AI_API_KEY_MISSING"
            )

        prompt = f"""
Eres DataFlow AI Copilot, un experto senior en Data Analytics, Data Quality y ETL.
Analiza la estructura del dataset '{filename}' y propón un plan de transformaciones en formato JSON preparado para carga directa en Power BI.

Columnas y tipos: {json.dumps(columns_schema)}
Problemas de calidad detectados: {json.dumps(quality_issues)}
Muestra anonimizada (3 filas): {json.dumps(sample_rows[:3])}

Reglas estrictas:
1. SOLO puedes utilizar operaciones del catálogo permitido:
   - trim_text, normalize_case, normalize_category, convert_datetime, convert_numeric, round_numeric, clamp_range, fill_missing, remove_duplicates, rename_column, drop_column.
2. Responde EXCLUSIVAMENTE con un objeto JSON válido con esta estructura:
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

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(url, headers=headers, json=payload)
            if res.status_code != 200:
                raise FunctionalException(
                    message="Error de comunicación con el servicio de IA de Gemini.",
                    code="AI_PROVIDER_ERROR",
                    details={"status_code": res.status_code, "response": res.text}
                )

            data = res.json()
            raw_json_str = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed_dict = json.loads(raw_json_str)

            return AISuggestionResponse(**parsed_dict)
