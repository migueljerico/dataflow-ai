import numpy as np
import pandas as pd
import pytest
from app.core.exceptions import FunctionalException
from app.models.etl import TransformationStep
from app.services.script_generator import ScriptGeneratorService
from app.transformations.cluster_ops import ClusterKMeansTransformation
from app.transformations.outlier_ops import (
    DetectOutliersIQRTransformation,
    DetectOutliersZScoreTransformation,
)
from app.transformations.registry import TransformationRegistry


# ==========================================
# 1. PRUEBAS DETECCIÓN OUTLIERS POR IQR
# ==========================================
def test_detect_outliers_iqr_cap():
    df = pd.DataFrame({"valor": [10.0, 12.0, 11.0, 13.0, 12.0, 11.0, 100.0, -50.0]})
    op = DetectOutliersIQRTransformation()

    res_df, affected = op.apply(df, {"column": "valor", "multiplier": 1.5, "action": "cap"})
    assert affected == 2
    # Comprobar que no hay valores extremos
    assert res_df["valor"].max() < 100.0
    assert res_df["valor"].min() > -50.0


def test_detect_outliers_iqr_nullify():
    df = pd.DataFrame({"valor": [10.0, 11.0, 12.0, 10.0, 11.0, 200.0]})
    op = DetectOutliersIQRTransformation()

    res_df, affected = op.apply(df, {"column": "valor", "multiplier": 1.5, "action": "nullify"})
    assert affected == 1
    assert res_df["valor"].isna().sum() == 1


def test_detect_outliers_iqr_drop():
    df = pd.DataFrame({"id": range(6), "valor": [10.0, 11.0, 12.0, 10.0, 11.0, 200.0]})
    op = DetectOutliersIQRTransformation()

    res_df, affected = op.apply(df, {"column": "valor", "multiplier": 1.5, "action": "drop"})
    assert affected == 1
    assert len(res_df) == 5
    assert 200.0 not in res_df["valor"].values


def test_detect_outliers_iqr_flag():
    df = pd.DataFrame({"valor": [10.0, 11.0, 12.0, 10.0, 11.0, 200.0]})
    op = DetectOutliersIQRTransformation()

    res_df, affected = op.apply(df, {"column": "valor", "multiplier": 1.5, "action": "flag"})
    assert affected == 1
    assert "valor_is_outlier" in res_df.columns
    assert res_df["valor_is_outlier"].iloc[-1] == True
    assert res_df["valor_is_outlier"].iloc[0] == False


def test_detect_outliers_iqr_validations():
    df = pd.DataFrame({"valor": [1, 2, 3]})
    op = DetectOutliersIQRTransformation()

    with pytest.raises(FunctionalException) as exc1:
        op.apply(df, {"column": "col_fantasma"})
    assert exc1.value.code == "INVALID_COLUMN"

    with pytest.raises(FunctionalException) as exc2:
        op.apply(df, {"column": "valor", "multiplier": -1.0})
    assert exc2.value.code == "INVALID_PARAMETER"

    with pytest.raises(FunctionalException) as exc3:
        op.apply(df, {"column": "valor", "action": "invalid_action"})
    assert exc3.value.code == "INVALID_PARAMETER"

    with pytest.raises(FunctionalException) as exc4:
        op.apply(df, {"column": "valor", "lower_quantile": 0.8, "upper_quantile": 0.2})
    assert exc4.value.code == "INVALID_PARAMETER"


# ==========================================
# 2. PRUEBAS DETECCIÓN OUTLIERS POR Z-SCORE
# ==========================================
def test_detect_outliers_zscore_cap():
    data = [10.0] * 30 + [100.0]
    df = pd.DataFrame({"score": data})
    op = DetectOutliersZScoreTransformation()

    res_df, affected = op.apply(df, {"column": "score", "threshold": 2.5, "action": "cap"})
    assert affected == 1
    assert res_df["score"].max() < 100.0


def test_detect_outliers_zscore_nullify_and_drop():
    data = [20.0] * 40 + [200.0, -100.0]
    df = pd.DataFrame({"score": data})
    op = DetectOutliersZScoreTransformation()

    # Nullify
    null_df, aff_null = op.apply(df, {"column": "score", "threshold": 2.0, "action": "nullify"})
    assert aff_null == 2
    assert null_df["score"].isna().sum() == 2

    # Drop
    drop_df, aff_drop = op.apply(df, {"column": "score", "threshold": 2.0, "action": "drop"})
    assert aff_drop == 2
    assert len(drop_df) == 40


def test_detect_outliers_zscore_flag():
    data = [15.0] * 25 + [300.0]
    df = pd.DataFrame({"score": data})
    op = DetectOutliersZScoreTransformation()

    res_df, affected = op.apply(df, {"column": "score", "threshold": 2.0, "action": "flag"})
    assert affected == 1
    assert "score_is_outlier" in res_df.columns
    assert res_df["score_is_outlier"].iloc[-1] == True
    assert res_df["score_is_outlier"].iloc[0] == False


def test_detect_outliers_zscore_zero_variance_or_empty():
    df_const = pd.DataFrame({"score": [5.0, 5.0, 5.0, 5.0]})
    op = DetectOutliersZScoreTransformation()
    res_df, affected = op.apply(df_const, {"column": "score", "threshold": 3.0, "action": "flag"})
    assert affected == 0
    assert not res_df["score_is_outlier"].any()


def test_detect_outliers_zscore_validations():
    df = pd.DataFrame({"score": [1.0, 2.0]})
    op = DetectOutliersZScoreTransformation()

    with pytest.raises(FunctionalException) as exc1:
        op.apply(df, {"column": "no_col"})
    assert exc1.value.code == "INVALID_COLUMN"

    with pytest.raises(FunctionalException) as exc2:
        op.apply(df, {"column": "score", "threshold": 0})
    assert exc2.value.code == "INVALID_PARAMETER"


# ==========================================
# 3. PRUEBAS CLUSTERING DETERMINISTA K-MEANS
# ==========================================
def test_cluster_kmeans_deterministic_output():
    np.random.seed(0)
    # Crear 3 grupos claramente diferenciados
    g1 = np.random.normal(loc=5.0, scale=0.5, size=(20, 2))
    g2 = np.random.normal(loc=50.0, scale=0.5, size=(20, 2))
    g3 = np.random.normal(loc=100.0, scale=0.5, size=(20, 2))
    all_data = np.vstack([g1, g2, g3])

    df = pd.DataFrame(all_data, columns=["feat1", "feat2"])
    op = ClusterKMeansTransformation()

    res1, aff1 = op.apply(df, {"columns": ["feat1", "feat2"], "n_clusters": 3, "output_column": "cluster_id"})
    res2, aff2 = op.apply(df, {"columns": ["feat1", "feat2"], "n_clusters": 3, "output_column": "cluster_id"})

    assert aff1 == 60
    assert "cluster_id" in res1.columns
    assert set(res1["cluster_id"].unique()) == {0, 1, 2}
    # Determinismo absoluto: ambas ejecuciones producen exactamente los mismos clusters
    assert np.array_equal(res1["cluster_id"].values, res2["cluster_id"].values)


def test_cluster_kmeans_empty_dataframe():
    df = pd.DataFrame(columns=["f1", "f2"])
    op = ClusterKMeansTransformation()
    res, aff = op.apply(df, {"columns": ["f1", "f2"], "n_clusters": 2})
    assert aff == 0
    assert "cluster_id" in res.columns


def test_cluster_kmeans_validations():
    df = pd.DataFrame({"f1": [1, 2], "f2": [3, 4]})
    op = ClusterKMeansTransformation()

    with pytest.raises(FunctionalException) as exc1:
        op.apply(df, {"columns": []})
    assert exc1.value.code == "INVALID_PARAMETER"

    with pytest.raises(FunctionalException) as exc2:
        op.apply(df, {"columns": ["f1", "no_col"]})
    assert exc2.value.code == "INVALID_COLUMN"

    with pytest.raises(FunctionalException) as exc3:
        op.apply(df, {"columns": ["f1"], "n_clusters": 1})
    assert exc3.value.code == "INVALID_PARAMETER"

    with pytest.raises(FunctionalException) as exc4:
        op.apply(df, {"columns": ["f1"], "n_clusters": 25})
    assert exc4.value.code == "INVALID_PARAMETER"


# ==========================================
# 4. PRUEBAS REGISTRO Y MANIFIESTO
# ==========================================
def test_registry_contains_new_operations():
    manifest = TransformationRegistry.get_catalog_manifest()
    assert "detect_outliers_iqr" in manifest
    assert "detect_outliers_zscore" in manifest
    assert "cluster_kmeans" in manifest

    # Validar parámetros permitidos
    df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
    with pytest.raises(FunctionalException) as exc:
        TransformationRegistry.validate_operation_and_parameters(
            "detect_outliers_iqr", df, {"column": "x", "param_ilegal": 123}
        )
    assert exc.value.code == "UNAUTHORIZED_PARAMETER"


# ==========================================
# 5. PRUEBAS GENERADOR DE SCRIPTS PYTHON
# ==========================================
def test_script_generator_with_advanced_transformations():
    steps = [
        TransformationStep(
            step_id="S-001",
            operation="detect_outliers_iqr",
            column="salario",
            parameters={"column": "salario", "multiplier": 1.5, "action": "cap"},
            reason="Acotar salarios extremos",
            risk="medium",
        ),
        TransformationStep(
            step_id="S-002",
            operation="detect_outliers_zscore",
            column="ventas",
            parameters={"column": "ventas", "threshold": 2.5, "action": "flag"},
            reason="Marcar anomalías de ventas",
            risk="medium",
        ),
        TransformationStep(
            step_id="S-003",
            operation="cluster_kmeans",
            parameters={"columns": ["salario", "ventas"], "n_clusters": 3, "output_column": "segmento"},
            reason="Segmentación de clientes",
            risk="low",
        ),
    ]

    script = ScriptGeneratorService.generate_python_script("dataset.csv", steps)
    assert "detect_outliers_iqr" in script
    assert "detect_outliers_zscore" in script
    assert "cluster_kmeans" in script
    assert "salario" in script
    assert "segmento" in script

    # Verificar que el código generado tiene sintaxis Python válida
    compiled = compile(script, "<string>", "exec")
    assert compiled is not None
