"""
Tests de regresión del prompt maestro: el motor semántico protege IDs,
emails, nulos, negativos, fracciones, países y DAX con nombres reales.

Filosofía verificada: la IA propone, el usuario decide, Python ejecuta.
Ningún test aprueba una imputación o corrección silenciosa.
"""

import io

import pandas as pd
import pytest
from app.core.semantics import is_fraction_or_discount_column, is_id_or_code_column
from app.core.transformation_policy import (
    casing_policy,
    country_mappings_for_values,
    missing_policy,
)
from app.main import app
from app.models.etl import StepStatusEnum
from app.models.profiling import ColumnTypeEnum, SemanticHintEnum
from app.services.dataset_service import DatasetService
from app.services.etl_service import ETLService
from app.services.profiler_service import ProfilerService
from app.services.quality_service import QualityService
from app.transformations.registry import TransformationRegistry
from fastapi.testclient import TestClient

client = TestClient(app)


def _upload_csv(filename: str, content: str) -> str:
    res = client.post(
        "/api/v1/datasets/upload",
        files={"file": (filename, io.BytesIO(content.encode("utf-8")), "text/csv")},
    )
    assert res.status_code == 201
    return res.json()["dataset_id"]


# ---------- P1: IDs ----------


@pytest.mark.parametrize(
    "col",
    [
        "CustomerID",
        "CustomerId",
        "customerID",
        "CUSTOMER_ID",
        "customer_id",
        "ProductID",
        "ProductId",
        "Product_ID",
        "OrderID",
        "EmployeeID",
        "CategoryID",
        "OrderDetailID",
        "InvoiceID",
        "AccountID",
        "TransactionID",
        "ClientID",
    ],
)
def test_id_detector_recognizes_variants(col):
    assert is_id_or_code_column(col, pd.Series(["X-001", "X-002"])) is True


def test_id_detector_rejects_non_ids():
    for col in ["Valid", "Nombre", "Estado", "Observaciones", "Fecha", "Precio"]:
        assert is_id_or_code_column(col, pd.Series(["a", "b"])) is False


def test_customerid_values_survive_end_to_end():
    dataset_id = _upload_csv(
        "ids.csv",
        "CustomerID,CustomerName\nCUST0001, Ana Gil \nCUST0002,LUIS PARDO\n",
    )
    plan = ETLService.propose_plan_from_rules(dataset_id)
    assert not any(s.column == "CustomerID" and s.operation == "normalize_case" for s in plan.steps)
    for s in plan.steps:
        s.status = StepStatusEnum.APPROVED
    result = ETLService.execute_plan(dataset_id, plan.plan_id, plan.steps)
    df = DatasetService.load_dataframe(dataset_id)
    # Releer el limpio del storage
    from app.core.storage import get_storage

    raw = get_storage().read_file(f"{result.run_id}_clean_ids.csv").decode("utf-8")
    clean = pd.read_csv(io.StringIO(raw), dtype=str)
    assert clean["CustomerID"].tolist() == ["CUST0001", "CUST0002"]
    assert "Luis Pardo" in clean["CustomerName"].tolist()
    _ = df


# ---------- P2: semantic-aware ----------


def test_email_never_title_case_end_to_end():
    dataset_id = _upload_csv(
        "emails.csv",
        "Email,Name\ndavid.martin@example.com,Ana\nCARLOS.DIAZ@EXAMPLE.COM,Luis\n",
    )
    hint = ProfilerService._detect_semantic_hint("Email", pd.Series(["david.martin@example.com"]), ColumnTypeEnum.TEXT)
    assert hint == SemanticHintEnum.EMAIL
    plan = ETLService.propose_plan_from_rules(dataset_id)
    for s in plan.steps:
        if s.column == "Email" and s.operation == "normalize_case":
            assert s.parameters.get("mode") != "title", "Email nunca en Title Case"
    policy = casing_policy("email")
    assert policy["allow_normalize_case"] is True
    assert policy["allowed_modes"] == ["lower"]
    for h in ("id", "phone", "date"):
        assert casing_policy(h)["allow_normalize_case"] is False


def test_id_columns_excluded_from_normalize_case_policy():
    hint = ProfilerService._detect_semantic_hint("CustomerID", pd.Series(["CUST0001"]), ColumnTypeEnum.TEXT)
    assert hint == SemanticHintEnum.ID


# ---------- P3: nulos ----------


def test_text_nulls_flagged_not_filled_with_desconocido():
    dataset_id = _upload_csv(
        "nulls.csv",
        "Email,Status\nana@example.com,Delivered\n,Shipped\nluis@example.com,\n",
    )
    plan = ETLService.propose_plan_from_rules(dataset_id)
    assert not any(
        s.operation == "fill_missing"
        and s.parameters.get("value") == "Desconocido"
        and s.status == StepStatusEnum.APPROVED
        for s in plan.steps
    ), "Ningún fill a Desconocido sale aprobado por defecto"
    review_steps = [s for s in plan.steps if s.operation == "flag_for_review"]
    assert len(review_steps) >= 2
    pol = missing_policy("email", "Email", 1)
    assert pol["action"] == "flag_for_review"
    assert TransformationRegistry.get("flag_for_review") is not None


def test_flag_for_review_does_not_modify_data():
    dataset_id = _upload_csv("nulls2.csv", "Email\nana@example.com\n\n")
    plan = ETLService.propose_plan_from_rules(dataset_id)
    for s in plan.steps:
        s.status = StepStatusEnum.APPROVED
    result = ETLService.execute_plan(dataset_id, plan.plan_id, plan.steps)
    from app.core.storage import get_storage

    raw = get_storage().read_file(f"{result.run_id}_clean_nulls2.csv").decode("utf-8")
    clean = pd.read_csv(io.StringIO(raw), dtype=str, keep_default_na=False)
    assert "Desconocido" not in clean["Email"].tolist()


# ---------- P4: negativos ----------


def test_negatives_require_review_not_clamp():
    dataset_id = _upload_csv(
        "neg.csv",
        "ProductName,UnitPrice,Quantity\nA,10.0,2\nB,-23.50,3\nC,5.0,-4\n",
    )
    plan = ETLService.propose_plan_from_rules(dataset_id)
    assert not any(
        s.operation == "clamp_range" for s in plan.steps
    ), "Sin regla de negocio explícita no se propone clamp a 0"
    kinds = {(s.parameters or {}).get("context", {}).get("kind") for s in plan.steps}
    assert "negative_values" in kinds
    # Y quality lo describe como revisión, no como acotación
    quality = QualityService.get_quality_report(dataset_id)
    neg_issues = [i for i in quality.issues if "negativo" in i.description.lower()]
    assert neg_issues
    assert all("flag_for_review" in i.suggested_action for i in neg_issues)


def test_percentages_still_clamp_to_100():
    dataset_id = _upload_csv(
        "pct.csv",
        "ID,Incidencias_Pct\n1,-2.0%\n2,120.0%\n3,50.0%\n",
    )
    plan = ETLService.propose_plan_from_rules(dataset_id)
    clamp = [s for s in plan.steps if s.operation == "clamp_range" and s.column == "Incidencias_Pct"]
    assert clamp
    assert clamp[0].parameters["min_value"] == 0.0
    assert clamp[0].parameters["max_value"] == 100.0


# ---------- P5: discount fracción ----------


def test_discount_is_fraction_not_percentage():
    series = pd.Series(["0.05", "0.10", "0.20", "1.20"])
    assert is_fraction_or_discount_column("Discount", series) is True
    assert is_fraction_or_discount_column("Descuento", series) is True
    # Descuento_Pct sigue siendo porcentaje
    hint = ProfilerService._detect_semantic_hint("Descuento_Pct", pd.Series(["10.0%", "20.0%"]), ColumnTypeEnum.NUMERIC)
    assert hint == SemanticHintEnum.PERCENTAGE
    hint2 = ProfilerService._detect_semantic_hint("Discount", series, ColumnTypeEnum.NUMERIC)
    assert hint2 == SemanticHintEnum.FRACTION


@pytest.mark.parametrize(
    "value,valid",
    [("0", True), ("0.05", True), ("0.10", True), ("0.20", True), ("1", True), ("1.20", False), ("1.4876", False)],
)
def test_discount_range_values(value, valid):
    dataset_id = _upload_csv("disc.csv", f"Discount\n0.05\n{value}\n0.10\n")
    quality = QualityService.get_quality_report(dataset_id)
    frac_issues = [i for i in quality.issues if "fracción" in i.description.lower()]
    if valid:
        assert not frac_issues
    else:
        assert frac_issues
        assert "flag_for_review" in frac_issues[0].suggested_action


def test_discount_out_of_range_never_clamped():
    dataset_id = _upload_csv("disc2.csv", "Discount\n0.05\n1.20\n0.10\n1.4876\n")
    plan = ETLService.propose_plan_from_rules(dataset_id)
    assert not any(s.operation == "clamp_range" and s.column == "Discount" for s in plan.steps)
    assert any(
        s.operation == "flag_for_review"
        and (s.parameters or {}).get("context", {}).get("kind") == "fraction_out_of_range"
        for s in plan.steps
    )


# ---------- P6: países ----------


def test_country_variants_unified_via_category():
    mappings = country_mappings_for_values(["Spain", "SPAIN", "spain", "España", "ES"])
    assert mappings == {"SPAIN": "Spain", "spain": "Spain", "España": "Spain", "ES": "Spain"}
    dataset_id = _upload_csv(
        "country.csv",
        "CustomerID,Country\nCUST0001,Spain\nCUST0002,ES\nCUST0003,España\nCUST0004,France\n",
    )
    plan = ETLService.propose_plan_from_rules(dataset_id)
    cat = [s for s in plan.steps if s.operation == "normalize_category" and s.column == "Country"]
    assert cat, "País debe unificarse con normalize_category"
    assert cat[0].parameters["mappings"]["ES"] == "Spain"
    for s in plan.steps:
        s.status = StepStatusEnum.APPROVED
    result = ETLService.execute_plan(dataset_id, plan.plan_id, plan.steps)
    from app.core.storage import get_storage

    raw = get_storage().read_file(f"{result.run_id}_clean_country.csv").decode("utf-8")
    clean = pd.read_csv(io.StringIO(raw), dtype=str)
    assert set(clean["Country"].tolist()) == {"Spain", "France"}
    assert clean["CustomerID"].tolist()[0] == "CUST0001"


# ---------- P7/P8: DAX ----------


def test_dax_uses_real_table_name_and_validates():
    from datetime import datetime, timezone

    from app.models.etl import ExecutionResult
    from app.services.analytics_service import AnalyticsService

    df = pd.DataFrame(
        {
            "ProductID": ["PROD0001", "PROD0002"],
            "UnitPrice": [10.0, 20.0],
            "OrderDate": pd.to_datetime(["2024-01-01", "2024-02-01"]),
        }
    )
    run = ExecutionResult(
        run_id="RUN-x",
        dataset_id="d",
        plan_id="p",
        status="completed",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        rows_before=2,
        rows_after=2,
        columns_before=3,
        columns_after=3,
        applied_steps_count=0,
        input_hash_md5="a",
        output_hash_md5="b",
        clean_filename="clean_products_dirty.csv",
        download_url="x",
        script_url="y",
    )
    guide = AnalyticsService._build_integration_guide(df, run, domain="general")
    assert guide.table_name == "clean_products_dirty"
    assert any("COUNTROWS('clean_products_dirty')" in m.formula for m in guide.dax_measures)
    assert not any("Clean_Products_Dirty" in m.formula for m in guide.dax_measures)
    # TOTALYTD solo con fecha válida
    assert any("_YTD" in m.name for m in guide.dax_measures)


def test_dax_without_numeric_or_date_gives_warnings_not_broken_dax():
    from datetime import datetime, timezone

    from app.models.etl import ExecutionResult
    from app.services.analytics_service import AnalyticsService

    df = pd.DataFrame({"Name": ["a", "b"]})
    run = ExecutionResult(
        run_id="RUN-y",
        dataset_id="d",
        plan_id="p",
        status="completed",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        rows_before=2,
        rows_after=2,
        columns_before=1,
        columns_after=1,
        applied_steps_count=0,
        input_hash_md5="a",
        output_hash_md5="b",
        clean_filename="clean_test.csv",
        download_url="x",
        script_url="y",
    )
    guide = AnalyticsService._build_integration_guide(df, run, domain="general")
    assert any("No se puede generar" in m.formula for m in guide.dax_measures)
    assert not any("TOTALYTD" in (m.formula or "") and "No se puede" not in m.formula for m in guide.dax_measures)


# ---------- Réplicas sintéticas del Northwind Dirty ----------
#
# Los CSV originales viven en el disco local del autor (D:/Downloads) y no
# existen en CI. Estas réplicas autocontenidas reproducen los mismos patrones
# (IDs CamelCase, emails NULL/Title, negativos, Discount>1, países ES/España)
# sin depender de rutas locales.


def _load_synthetic_northwind_products() -> str:
    rows = ["ProductID,ProductName,CategoryID,UnitPrice,UnitsInStock"]
    for i in range(1, 11):
        price = "-23.50" if i <= 8 else "10.00"
        rows.append(f"PROD{i:04d},Product {i},CAT01,{price},100")
    return _upload_csv("products_dirty.csv", "\n".join(rows) + "\n")


def _load_synthetic_northwind_customers() -> str:
    rows = ["CustomerID,CustomerName,Email,Phone,City,Country"]
    for i in range(1, 26):
        rows.append(f"CUST{i:04d},Name {i},user{i}@example.com,+34 600000000,Madrid,Spain")
    rows.append("CUST0026,Sin Email,,+34 600000000,Madrid,ES")
    rows.append("CUST0027,Sin Email 2,,+34 600000000,Madrid,España")
    rows.append("CUST0028,Mayus,CARLOS.DIAZ@EXAMPLE.COM,+34 600000000,Madrid,Spain")
    return _upload_csv("customers_dirty.csv", "\n".join(rows) + "\n")


def _load_synthetic_northwind_orders() -> str:
    rows = ["OrderID,CustomerID,EmployeeID,OrderDate,ShipCountry,Status"]
    for i in range(1, 28):
        status = "" if i <= 25 else "Delivered"
        rows.append(f"ORD{i:05d},CUST0001,EMP001,2024-01-01,Spain,{status}")
    return _upload_csv("orders_dirty.csv", "\n".join(rows) + "\n")


def _load_synthetic_northwind_details() -> str:
    rows = ["OrderDetailID,OrderID,ProductID,Quantity,UnitPrice,Discount"]
    for i in range(1, 19):
        rows.append(f"DET{i:06d},ORD00001,PROD0001,-{i},10.0,0.05")
    for i in range(19, 29):
        rows.append(f"DET{i:06d},ORD00001,PROD0001,2,10.0,1.20")
    return _upload_csv("order_details_dirty.csv", "\n".join(rows) + "\n")


def test_northwind_products_negatives_need_review_and_ids_intact():
    dataset_id = _load_synthetic_northwind_products()
    df = DatasetService.load_dataframe(dataset_id)
    neg = int((pd.to_numeric(df["UnitPrice"], errors="coerce") < 0).sum())
    assert neg == 8
    plan = ETLService.propose_plan_from_rules(dataset_id)
    assert not any(s.operation == "clamp_range" and s.column == "UnitPrice" for s in plan.steps)
    assert any(s.operation == "flag_for_review" and s.column == "UnitPrice" for s in plan.steps)
    assert not any(s.column == "ProductID" and s.operation == "normalize_case" for s in plan.steps)


def test_northwind_customers_emails_and_ids():
    dataset_id = _load_synthetic_northwind_customers()
    plan = ETLService.propose_plan_from_rules(dataset_id)
    assert not any(
        s.operation == "fill_missing" and s.column == "Email" for s in plan.steps
    ), "Email NULL no se imputa automáticamente"
    assert not any(
        s.column == "Email" and s.operation == "normalize_case" and s.parameters.get("mode") == "title"
        for s in plan.steps
    )
    assert not any(s.column == "CustomerID" and s.operation == "normalize_case" for s in plan.steps)


def test_northwind_orders_status_null_and_ids():
    dataset_id = _load_synthetic_northwind_orders()
    df = DatasetService.load_dataframe(dataset_id)
    assert int(df["Status"].isna().sum()) == 25
    plan = ETLService.propose_plan_from_rules(dataset_id)
    assert not any(s.operation == "fill_missing" and s.column == "Status" for s in plan.steps)
    for c in ("OrderID", "CustomerID", "EmployeeID"):
        assert not any(s.column == c and s.operation == "normalize_case" for s in plan.steps)


def test_northwind_details_quantity_discount_and_country_mapping():
    dataset_id = _load_synthetic_northwind_details()
    df = DatasetService.load_dataframe(dataset_id)
    assert int((pd.to_numeric(df["Quantity"], errors="coerce") < 0).sum()) == 18
    assert int((pd.to_numeric(df["Discount"], errors="coerce") > 1).sum()) == 10
    plan = ETLService.propose_plan_from_rules(dataset_id)
    assert not any(s.operation == "clamp_range" and s.column == "Quantity" for s in plan.steps)
    assert not any(s.operation == "clamp_range" and s.column == "Discount" for s in plan.steps)
    kinds = {(s.column, (s.parameters or {}).get("context", {}).get("kind")) for s in plan.steps}
    assert ("Quantity", "negative_values") in kinds
    assert ("Discount", "fraction_out_of_range") in kinds


def test_northwind_referential_integrity_intact_ids():
    cust = _load_synthetic_northwind_customers()
    ords = _load_synthetic_northwind_orders()
    det = _load_synthetic_northwind_details()
    prods = _load_synthetic_northwind_products()
    for ds, expected_op in [
        (cust, "CustomerID"),
        (ords, "OrderID"),
        (det, "OrderDetailID"),
        (prods, "ProductID"),
    ]:
        df = DatasetService.load_dataframe(ds)
        assert expected_op in df.columns
        vals = df[expected_op].dropna().astype(str)
        # Los IDs conservan mayúsculas originales (CUST/ORD/DET/PROD)
        assert vals.str.contains(r"^[A-Z]+0").any(), f"{expected_op} debe conservar formato original"
    df_o = DatasetService.load_dataframe(ords)
    df_c = DatasetService.load_dataframe(cust)
    df_d = DatasetService.load_dataframe(det)
    df_p = DatasetService.load_dataframe(prods)
    assert set(df_o["CustomerID"].dropna().astype(str)).issubset(set(df_c["CustomerID"].dropna().astype(str)))
    assert set(df_d["OrderID"].dropna().astype(str)).issubset(set(df_o["OrderID"].dropna().astype(str)))
    assert set(df_d["ProductID"].dropna().astype(str)).issubset(set(df_p["ProductID"].dropna().astype(str)))
