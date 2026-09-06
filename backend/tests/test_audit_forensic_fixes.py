# -*- coding: utf-8 -*-
"""
Tests forenses obligatorios para validación de:
- Test 1: Email duplicado detectado
- Test 2: Email NULL no considerado duplicado
- Test 3: CustomerID único sin issue
- Test 4: Foreign Key repetida (CustomerID en Orders) no genera issue
- Test 5: Coherencia entre Issue y Propuesta (Email = NULL -> flag_for_review / keep_null)
- Test 6: Comparación sin baseline (comparison_available=False, score_before=None)
- Test 7: Score determinista (misma entrada -> mismo score)
- Test 8: Detección de duplicados de Email en Northwind customers_dirty.csv
- Test 9: Ausencia de falsos positivos en FKs (CustomerID, OrderID, ProductID)
- Test 10: Consistencia sin doble conteo en Country de customers_dirty.csv
"""

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
from app.models.dataset import DatasetMetadata, ProcessingStateEnum
from app.models.quality import (
    ExecutionSummaryItem,
    QualityDimensionEnum,
    SeverityEnum,
)
from app.services.dataset_service import DATASET_CACHE
from app.services.etl_service import (
    ETLService,
)
from app.services.profiler_service import PROFILING_CACHE, ProfilerService
from app.services.quality_service import QUALITY_CACHE, QualityService

NORTHWIND_PATH = Path(r"D:\Downloads\Northwind_Dirty_Enterprise")


def test_1_email_duplicado_detectado():
    """Test 1: Email duplicado: ['a@example.com', 'b@example.com', 'a@example.com'] debe detectar duplicidad."""
    df = pd.DataFrame({"Email": ["a@example.com", "b@example.com", "a@example.com"]})
    prof = ProfilerService.profile_dataframe(df)
    q = QualityService.analyze_dataframe(df, prof)

    uniq_issues = [i for i in q.issues if i.dimension == QualityDimensionEnum.UNIQUENESS and i.column == "Email"]
    assert len(uniq_issues) == 1, "Debe existir un issue de unicidad en Email"
    assert uniq_issues[0].affected_rows == 1, "Debe detectar 1 fila redundante"
    assert uniq_issues[0].severity in (SeverityEnum.HIGH, SeverityEnum.MEDIUM)
    # Comprobar anonimización anti-PII en evidence_sample
    evidence_str = str(uniq_issues[0].evidence_sample)
    assert "a***@example.com" in evidence_str or "a***" in evidence_str
    assert "b@example.com" not in evidence_str


def test_2_email_null_no_es_duplicado():
    """Test 2: Email NULL: ['a@example.com', None, None] -> Los NULL no deben considerarse duplicados."""
    df = pd.DataFrame({"Email": ["a@example.com", None, None]})
    prof = ProfilerService.profile_dataframe(df)
    q = QualityService.analyze_dataframe(df, prof)

    uniq_issues = [i for i in q.issues if i.dimension == QualityDimensionEnum.UNIQUENESS and i.column == "Email"]
    assert len(uniq_issues) == 0, "Los NULLs o celdas vacías NO deben considerarse duplicados"

    # Los NULLs deben estar penalizados exclusivamente en Completeness
    compl_issues = [i for i in q.issues if i.dimension == QualityDimensionEnum.COMPLETENESS and i.column == "Email"]
    assert len(compl_issues) == 1
    assert compl_issues[0].affected_rows == 2


def test_3_customer_id_unico_sin_issue():
    """Test 3: CustomerID único: ['CUST001', 'CUST002', 'CUST003'] no genera issue de unicidad."""
    df = pd.DataFrame(
        {
            "CustomerID": ["CUST001", "CUST002", "CUST003"],
            "CustomerName": ["Alice", "Bob", "Charlie"],
        }
    )
    prof = ProfilerService.profile_dataframe(df)
    q = QualityService.analyze_dataframe(df, prof)

    uniq_issues = [i for i in q.issues if i.dimension == QualityDimensionEnum.UNIQUENESS]
    assert len(uniq_issues) == 0, "No debe haber issues de unicidad en identificadores únicos"
    assert q.quality_score.uniqueness.score == 100.0


def test_4_foreign_key_repetida_no_genera_issue():
    """Test 4: Foreign key repetida (CustomerID en Orders) NO genera issue de unicidad."""
    df_orders = pd.DataFrame(
        {
            "OrderID": ["ORD001", "ORD002", "ORD003"],
            "CustomerID": ["CUST001", "CUST001", "CUST002"],
            "Amount": [100.0, 150.0, 200.0],
        }
    )
    # Simular metadatos de tabla de pedidos
    ds_id = "test_orders_fk_ds"
    DATASET_CACHE[ds_id] = DatasetMetadata(
        dataset_id=ds_id,
        filename="orders.csv",
        file_type="csv",
        size_bytes=1024,
        row_count=3,
        column_count=3,
        status=ProcessingStateEnum.UPLOADED,
    )
    prof = ProfilerService.profile_dataframe(df_orders, dataset_id=ds_id)
    q = QualityService.analyze_dataframe(df_orders, prof, dataset_id=ds_id)

    uniq_issues_cust = [
        i for i in q.issues if i.dimension == QualityDimensionEnum.UNIQUENESS and i.column == "CustomerID"
    ]
    assert len(uniq_issues_cust) == 0, "Una FK repetida en tabla de transacciones jamás debe marcarse como corrupta"


def test_5_issue_proposal_coherence_email_null():
    """Test 5: Coherencia issue -> propuesta para Email NULL (flag_for_review / keep_null)."""
    df = pd.DataFrame(
        {
            "CustomerID": ["CUST001", "CUST002", "CUST003"],
            "Email": ["a@example.com", None, "c@example.com"],
        }
    )
    ds_id = "test_coherence_email_null_ds"
    DATASET_CACHE[ds_id] = DatasetMetadata(
        dataset_id=ds_id,
        filename="customers.csv",
        file_type="csv",
        size_bytes=1024,
        row_count=3,
        column_count=2,
        status=ProcessingStateEnum.UPLOADED,
    )
    # Guardar dataframe simulado
    from app.core.storage import get_storage

    storage = get_storage()
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    storage.save_file(f"{ds_id}_customers.csv", csv_bytes)

    prof = ProfilerService.profile_dataframe(df, dataset_id=ds_id)
    PROFILING_CACHE[ds_id] = prof
    q = QualityService.analyze_dataframe(df, prof, dataset_id=ds_id)
    QUALITY_CACHE[ds_id] = q

    # 1. Comprobar texto del issue
    email_compl_issue = [
        i for i in q.issues if i.dimension == QualityDimensionEnum.COMPLETENESS and i.column == "Email"
    ][0]
    assert (
        "flag_for_review" in email_compl_issue.suggested_action
    ), f"El issue debe sugerir flag_for_review, pero tiene: {email_compl_issue.suggested_action}"
    assert "fill_missing" not in email_compl_issue.suggested_action

    # 2. Comprobar propuesta de plan
    plan = ETLService.propose_plan_from_rules(ds_id)
    email_steps = [s for s in plan.steps if s.column == "Email"]
    assert len(email_steps) >= 1
    # La operación debe ser flag_for_review, nunca fill_missing
    assert any(s.operation == "flag_for_review" for s in email_steps)
    assert not any(s.operation == "fill_missing" for s in email_steps)


def test_6_comparacion_sin_baseline_explicit_state():
    """Test 6: Simular ausencia de score_before -> comparison_available == False, score_before is None, sin delta ficticio."""
    item = ExecutionSummaryItem(
        run_id="RUN-TEST-001",
        dataset_id="DS-UNKNOWN",
        filename="test.csv",
        clean_filename="clean_test.csv",
        status="completed",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        execution_time_seconds=0.1,
        rows_before=100,
        rows_after=100,
        columns_before=5,
        columns_after=5,
        applied_steps_count=0,
        score_before=None,
        score_after=None,
        score_delta=None,
        comparison_available=False,
        input_hash_md5="abc",
        output_hash_md5="def",
        download_url="/download",
    )
    assert item.comparison_available is False
    assert item.score_before is None
    assert item.score_after is None
    assert item.score_delta is None


def test_7_score_determinista():
    """Test 7: Misma entrada -> exactamente el mismo score y desglose."""
    df = pd.DataFrame(
        {
            "CustomerID": ["C001", "C002", "C003", "C004"],
            "Email": ["a@example.com", "B@EXAMPLE.COM", "a@example.com", None],
            "Country": ["spain", "SPAIN", "France", "Germany"],
        }
    )
    prof1 = ProfilerService.profile_dataframe(df)
    q1 = QualityService.analyze_dataframe(df, prof1)

    prof2 = ProfilerService.profile_dataframe(df)
    q2 = QualityService.analyze_dataframe(df, prof2)

    assert q1.quality_score.overall_score == q2.quality_score.overall_score
    assert q1.quality_score.completeness.score == q2.quality_score.completeness.score
    assert q1.quality_score.validity.score == q2.quality_score.validity.score
    assert q1.quality_score.consistency.score == q2.quality_score.consistency.score
    assert q1.quality_score.uniqueness.score == q2.quality_score.uniqueness.score
    assert q1.quality_score.integrity.score == q2.quality_score.integrity.score
    assert len(q1.issues) == len(q2.issues)


def test_8_northwind_email_duplicates_detection():
    """Test 8: Debe detectar duplicados semánticos de Email en customers_dirty.csv sin contar vacíos."""
    csv_path = NORTHWIND_PATH / "customers_dirty.csv"
    if not csv_path.exists():
        pytest.skip(f"No existe el archivo de pruebas {csv_path}")

    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    prof = ProfilerService.profile_dataframe(df)
    q = QualityService.analyze_dataframe(df, prof, dataset_id="customers_test_ds")

    email_uniq = [i for i in q.issues if i.dimension == QualityDimensionEnum.UNIQUENESS and i.column == "Email"]
    assert len(email_uniq) == 1, "Debe detectarse exactamente 1 grupo de anomalía de unicidad en Email"
    # 10 emails duplicados reales (20 filas implicadas)
    assert email_uniq[0].affected_rows == 10
    assert "10 valores duplicados" in email_uniq[0].description
    assert "20 filas implicadas" in email_uniq[0].description

    # Y la completitud debe registrar los 20 vacíos
    email_compl = [i for i in q.issues if i.dimension == QualityDimensionEnum.COMPLETENESS and i.column == "Email"]
    assert len(email_compl) == 1
    assert email_compl[0].affected_rows == 20


def test_9_no_falsos_positivos_en_fks_northwind():
    """Test 9: Verificar que las FKs en orders_dirty y order_details_dirty no se declaran erróneamente como corruptas."""
    orders_path = NORTHWIND_PATH / "orders_dirty.csv"
    od_path = NORTHWIND_PATH / "order_details_dirty.csv"
    if not orders_path.exists() or not od_path.exists():
        pytest.skip("No existen los archivos de prueba Northwind")

    # 1. orders_dirty: CustomerID no debe ser marcado como duplicado
    df_orders = pd.read_csv(orders_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    ds_o = "ds_orders_test"
    DATASET_CACHE[ds_o] = DatasetMetadata(
        dataset_id=ds_o,
        filename="orders_dirty.csv",
        file_type="csv",
        size_bytes=1024,
        row_count=len(df_orders),
        column_count=len(df_orders.columns),
        status=ProcessingStateEnum.UPLOADED,
    )
    prof_o = ProfilerService.profile_dataframe(df_orders, dataset_id=ds_o)
    q_o = QualityService.analyze_dataframe(df_orders, prof_o, dataset_id=ds_o)
    fk_cust_issues = [
        i for i in q_o.issues if i.dimension == QualityDimensionEnum.UNIQUENESS and i.column == "CustomerID"
    ]
    assert len(fk_cust_issues) == 0, "CustomerID en orders es una FK legítima y no debe tener issue de unicidad"

    # 2. order_details_dirty: OrderID y ProductID no deben ser marcados como duplicados
    df_od = pd.read_csv(od_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    ds_od = "ds_od_test"
    DATASET_CACHE[ds_od] = DatasetMetadata(
        dataset_id=ds_od,
        filename="order_details_dirty.csv",
        file_type="csv",
        size_bytes=1024,
        row_count=len(df_od),
        column_count=len(df_od.columns),
        status=ProcessingStateEnum.UPLOADED,
    )
    prof_od = ProfilerService.profile_dataframe(df_od, dataset_id=ds_od)
    q_od = QualityService.analyze_dataframe(df_od, prof_od, dataset_id=ds_od)
    fk_od_issues = [
        i
        for i in q_od.issues
        if i.dimension == QualityDimensionEnum.UNIQUENESS and i.column in ("OrderID", "ProductID")
    ]
    assert len(fk_od_issues) == 0, "OrderID y ProductID en order_details son FKs y no deben tener issue de unicidad"


def test_10_consistency_no_doble_conteo_country():
    """Test 10: En Country de customers_dirty, las variantes categóricas unificadas evitan el doble conteo de casing."""
    cust_path = NORTHWIND_PATH / "customers_dirty.csv"
    if not cust_path.exists():
        pytest.skip("No existe customers_dirty.csv")

    df = pd.read_csv(cust_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    prof = ProfilerService.profile_dataframe(df)
    q = QualityService.analyze_dataframe(df, prof, dataset_id="customers_consistency_ds")

    country_issues = [i for i in q.issues if i.dimension == QualityDimensionEnum.CONSISTENCY and i.column == "Country"]
    # Debe existir 1 solo issue consolidado para Country (inconsistencia categórica con 38 celdas), sin duplicar con casing
    assert (
        len(country_issues) == 1
    ), f"Se esperaba 1 issue de consistencia para Country (variantes de país), pero se encontraron {len(country_issues)}"
    assert country_issues[0].affected_rows == 38
