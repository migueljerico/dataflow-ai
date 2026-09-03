import numpy as np
import pandas as pd
import pytest

from app.models.analytics import DriftStatusEnum
from app.services.drift_service import DriftService, _compute_ks_statistic


def test_compute_ks_statistic_identical_and_different():
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    stat_same = _compute_ks_statistic(x, y)
    assert stat_same == 0.0

    z = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
    stat_diff = _compute_ks_statistic(x, z)
    assert stat_diff == 1.0


def test_percentile_shift_calculation():
    raw_df = pd.DataFrame({"ventas": [100.0, 200.0, 300.0, 400.0, 500.0, 600.0, 700.0, 800.0, 900.0, 1000.0]})
    # Simular una limpieza que elimina valores extremos o añade valores
    clean_df = pd.DataFrame({"ventas": [120.0, 210.0, 305.0, 410.0, 515.0, 610.0, 705.0, 810.0, 905.0, 990.0]})

    report = DriftService.analyze_column("ventas", clean_df["ventas"], raw_df["ventas"])
    assert report is not None
    assert report.column_name == "ventas"
    assert report.clean_percentiles.p50 > 0
    assert report.raw_percentiles.p50 > 0
    assert report.shift is not None
    assert report.drift_status in [DriftStatusEnum.STABLE, DriftStatusEnum.MODERATE]
    assert len(report.alerts) > 0
    assert len(report.recommendations) > 0


def test_drift_service_analyze_drift_high_drift_detection():
    # Simular un desplazamiento fuerte de la distribución (High Drift)
    raw_df = pd.DataFrame({"salarios": [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900]})
    # Aumentar drásticamente los salarios en el dataframe transformado
    clean_df = pd.DataFrame({"salarios": [3000, 3200, 3400, 3600, 3800, 4000, 4200, 4400, 4600, 4800]})

    full_report = DriftService.analyze_drift(clean_df=clean_df, raw_df=raw_df)
    assert full_report.total_alerts > 0
    assert full_report.critical_columns_count >= 1
    assert full_report.overall_drift_status == DriftStatusEnum.CRITICAL

    sal_report = next(c for c in full_report.columns if c.column_name == "salarios")
    assert sal_report.drift_status == DriftStatusEnum.CRITICAL
    assert sal_report.drift_score > 25.0
    assert any(a.severity.value == "critical" for a in sal_report.alerts)
    assert any(r.action_type == "imputation_review" for r in sal_report.recommendations)


def test_drift_service_anomalies_and_proactive_recommendations():
    # Dataset con outliers severos
    clean_df = pd.DataFrame(
        {
            "tiempo": [10, 11, 10, 12, 11, 10, 11, 12, 10, 11, 500, 800],  # Outliers extremos
            "unidades": [1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2],
        }
    )

    full_report = DriftService.analyze_drift(clean_df=clean_df)
    assert len(full_report.columns) == 2

    tiempo_col = next(c for c in full_report.columns if c.column_name == "tiempo")
    assert tiempo_col.anomaly_count >= 2
    assert tiempo_col.anomaly_percentage > 10.0
    assert any(r.action_type == "capping" for r in tiempo_col.recommendations)
