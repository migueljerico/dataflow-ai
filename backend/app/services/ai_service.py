import uuid
from datetime import datetime
from typing import List, Optional

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

        sample_rows = df.head(3).to_dict(orient="records")

        # Invocar proveedor de IA con proxy/credencial del usuario o entorno
        ai_response = await provider.suggest_transformations(
            filename=metadata.filename,
            columns_schema=columns_schema,
            quality_issues=quality_issues,
            sample_rows=sample_rows
        )

        # GUARDRAILS DE IA: Filtrar operaciones no reconocidas en el registro
        valid_steps: List[TransformationStep] = []
        for idx, sug in enumerate(ai_response.suggestions, 1):
            op = sug.operation
            try:
                # Comprobar si existe en el registro
                TransformationRegistry.get_transformation(op)
                
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
            except Exception:
                # Guardrail activo: Descartar silenciosamente la operación desconocida
                continue

        plan_id = f"AI-PLAN-{uuid.uuid4().hex[:8]}"
        plan = TransformationPlan(
            plan_id=plan_id,
            dataset_id=dataset_id,
            summary=ai_response.dataset_summary,
            steps=valid_steps,
            source=f"ai_copilot_{provider.provider_name}",
            created_at=datetime.utcnow()
        )

        metadata.status = ProcessingStateEnum.PLAN_PROPOSED
        PLANS_CACHE[plan_id] = plan
        return plan
