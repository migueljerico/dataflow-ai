"""
Tests de privacidad del Copiloto IA: las filas de muestra enviadas al LLM
deben llegar con PII enmascarada (minimización RGPD / BYOK).
"""

import pandas as pd

from app.models.profiling import ProfilingReport, ColumnProfile, ColumnTypeEnum, SemanticHintEnum
from app.services.ai_service import anonymize_sample_rows


def _build_profiling_with_hints(columns: dict) -> ProfilingReport:
    return ProfilingReport(
        dataset_id="test-dataset",
        row_count=3,
        column_count=len(columns),
        duplicates_count=0,
        duplicates_percentage=0.0,
        memory_estimate_bytes=0,
        columns=[
            ColumnProfile(
                column_name=name,
                inferred_type=ColumnTypeEnum.TEXT,
                semantic_hint=hint,
                null_count=0,
                null_percentage=0.0,
                unique_count=3,
            )
            for name, hint in columns.items()
        ],
        global_warnings=[],
    )


def test_anonymize_masks_names_emails_and_phones():
    df = pd.DataFrame(
        {
            "Nombre_Cliente": [" Juan Pérez ", "María Gómez", "LUIS MARTINEZ"],
            "Email_Cliente": ["juan.perez@empresa.com", "maria@corp.es", "luis.m@org.org"],
            "Telefono": ["600123456", "+34 911 234 567", "699876543"],
            "Importe_EUR": ["1.200,50 €", "350,00 €", "N/D"],
        }
    )
    profiling = _build_profiling_with_hints(
        {
            "Nombre_Cliente": SemanticHintEnum.NAME,
            "Email_Cliente": SemanticHintEnum.EMAIL,
            "Telefono": SemanticHintEnum.PHONE,
            "Importe_EUR": SemanticHintEnum.CURRENCY,
        }
    )

    rows = anonymize_sample_rows(df, profiling, limit=3)

    assert len(rows) == 3
    for row in rows:
        assert row["Nombre_Cliente"] == "[NOMBRE]"
        assert row["Email_Cliente"] == "[EMAIL]"
        assert row["Telefono"] == "[TELÉFONO]"
        # Las columnas no sensibles se envían sin alterar
        assert row["Importe_EUR"] in {"1.200,50 €", "350,00 €", "N/D"}


def test_anonymize_masks_embedded_pii_in_unhinted_columns():
    df = pd.DataFrame(
        {
            "Observaciones": ["Contactar en juan@empresa.com", "Sin novedad", "Revisar contrato"],
        }
    )
    profiling = _build_profiling_with_hints(
        {
            "Observaciones": SemanticHintEnum.UNKNOWN,
        }
    )

    rows = anonymize_sample_rows(df, profiling, limit=3)

    assert rows[0]["Observaciones"] == "Contactar en [EMAIL]"
    assert rows[1]["Observaciones"] == "Sin novedad"


def test_anonymize_limits_rows_sent_to_llm():
    df = pd.DataFrame({"Nombre_Cliente": [f"Persona {i}" for i in range(10)]})
    profiling = _build_profiling_with_hints(
        {
            "Nombre_Cliente": SemanticHintEnum.NAME,
        }
    )

    rows = anonymize_sample_rows(df, profiling, limit=3)

    assert len(rows) == 3
