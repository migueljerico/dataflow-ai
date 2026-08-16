import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from app.models.etl import TransformationPlan, TransformationStep
from app.models.dataset import ProcessingStateEnum
from app.transformations.registry import TransformationRegistry
from app.ai_providers.base import LLMProvider
from app.ai_providers.mock_provider import MockProvider
from app.ai_providers.gemini_provider import GeminiProvider
from app.services.dataset_service import DatasetService
from app.services.profiler_service import ProfilerService
from app.services.quality_service import QualityService
from app.services.etl_service import PLANS_CACHE

# Patrones PII para enmascaramiento de muestras enviadas al LLM (minimización RGPD)
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(\+34[\s.-]?)?[6789]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}")

#Hints semánticos sensibles -> máscara aplicada al valor completo de la muestra
PII_HINT_MASKS = {
    "name": "[NOMBRE]",
    "email": "[EMAIL]",
    "phone": "[TELÉFONO]",
}


def _mask_scalar(value: Any, hint: str) -> Any:
    """Enmascara un valor escalar si el hint semántico o el contenido revelan PII."""
    if value is None:
        return value
    try:
        if pd.isna(value):
            return value
    except (TypeError, ValueError):
        pass

    s = str(value).strip()
    if not s:
        return value

    if hint == "email" or _EMAIL_RE.fullmatch(s):
        return "[EMAIL]"
    if hint == "phone" or _PHONE_RE.fullmatch(s):
        return "[TELÉFONO]"
    if hint == "name":
        return "[NOMBRE]"

    # PII embebida en campos sin hint sensible
    if _EMAIL_RE.search(s):
        return _EMAIL_RE.sub("[EMAIL]", s)
    if _PHONE_RE.fullmatch(s):
        return "[TELÉFONO]"
    return value


def anonymize_sample_rows(df: pd.DataFrame, profiling, limit: int = 3) -> List[Dict[str, Any]]:
    """Devuelve hasta `limit` filas de muestra con PII enmascarada.

    Solo se envían al LLM el esquema, estadísticas y estas filas anonimizadas;
    el dataset completo nunca sale del servidor.
    """
    hint_by_col = {c.column_name: c.semantic_hint.value for c in profiling.columns}
    records: List[Dict[str, Any]] = df.head(limit).to_dict(orient="records")
    for record in records:
        for col in list(record.keys()):
            hint = hint_by_col.get(col, "unknown")
            if hint in PII_HINT_MASKS or hint == "unknown":
                record[col] = _mask_scalar(record[col], hint)
    return records


class AIService:
    @staticmethod
    def get_provider(provider_name: str = "mock", api_key: Optional[str] = None) -> LLMProvider:
        if provider_name == "gemini":
            return GeminiProvider(api_key=api_key)
        return MockProvider()

    @staticmethod
    async def propose_ai_plan(
        dataset_id: str,
        provider_name: str = "mock",
        api_key: Optional[str] = None
    ) -> TransformationPlan:
        provider = AIService.get_provider(provider_name, api_key=api_key)
        metadata = DatasetService.get_dataset_metadata(dataset_id)
        profiling = ProfilerService.get_profiling_report(dataset_id)
        quality = QualityService.get_quality_report(dataset_id)
        df = DatasetService.load_dataframe(dataset_id)

        columns_schema = [
            {
                "name": col.column_name,
                "type": col.inferred_type.value,
                "semantic_hint": col.semantic_hint.value,
                "null_count": col.null_count
            }
            for col in profiling.columns
        ]

        quality_issues = [
            {
                "column": issue.column,
                "dimension": issue.dimension.value,
                "severity": issue.severity.value,
                "description": issue.description
            }
            for issue in quality.issues
        ]

        # Minimización RGPD: 3 filas con PII enmascarada en lugar del dataset completo
        sample_rows = anonymize_sample_rows(df, profiling)

        # Invocar proveedor de IA con proxy/credencial del usuario o entorno
        ai_response = await provider.suggest_transformations(
            filename=metadata.filename,
            columns_schema=columns_schema,
            quality_issues=quality_issues,
            sample_rows=sample_rows
        )

        # GUARDRAILS DE IA: filtrar operaciones no reconocidas en el registro,
        # dejando constancia explícita en los warnings del plan (transparencia)
        plan_warnings: List[str] = list(ai_response.warnings or [])
        valid_steps: List[TransformationStep] = []
        for idx, sug in enumerate(ai_response.suggestions, 1):
            op = sug.operation
            if TransformationRegistry.get(op) is None:
                plan_warnings.append(
                    f"[GUARDRAIL] La operación '{op}' propuesta por el Copiloto fue descartada: no pertenece al catálogo permitido de transformaciones."
                )
                continue

            valid_steps.append(TransformationStep(
                step_id=f"AI-STEP-{idx:03d}",
                operation=op,
                column=sug.column,
                parameters=sug.parameters,
                reason=sug.reason,
                confidence=sug.confidence,
                risk=sug.risk,
                affected_rows_estimate=0
            ))

        plan_id = f"AI-PLAN-{uuid.uuid4().hex[:8]}"
        plan = TransformationPlan(
            plan_id=plan_id,
            dataset_id=dataset_id,
            summary=ai_response.dataset_summary,
            steps=valid_steps,
            source=f"ai_copilot_{provider.provider_name}",
            created_at=datetime.now(timezone.utc),
            warnings=plan_warnings
        )

        metadata.status = ProcessingStateEnum.PLAN_PROPOSED
        PLANS_CACHE[plan_id] = plan
        return plan
