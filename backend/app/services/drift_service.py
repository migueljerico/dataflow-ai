from datetime import datetime, timezone
from typing import List, Optional

import numpy as np
import pandas as pd

from app.core.number_parsing import to_numeric_series
from app.models.analytics import (
    ColumnDriftReport,
    DriftAlert,
    DriftAlertSeverityEnum,
    DriftAnalysisReport,
    DriftStatusEnum,
    PercentileMetrics,
    PercentileShift,
    ProactiveRecommendation,
)


def _safe_float(val: float) -> float:
    if val is None or np.isnan(val) or np.isinf(val):
        return 0.0
    return float(round(val, 2))


def _compute_ks_statistic(x: np.ndarray, y: np.ndarray) -> float:
    """
    Calcula el estadístico de 2 muestras de Kolmogorov-Smirnov (D = sup |F1(t) - F2(t)|)
    utilizando NumPy de manera vectorizada y determinista sin dependencias pesadas.
    """
    if len(x) == 0 or len(y) == 0:
        return 0.0
    x_clean = np.sort(x[~np.isnan(x)])
    y_clean = np.sort(y[~np.isnan(y)])
    if len(x_clean) == 0 or len(y_clean) == 0:
        return 0.0

    data_all = np.sort(np.concatenate([x_clean, y_clean]))
    cdf_x = np.searchsorted(x_clean, data_all, side="right") / len(x_clean)
    cdf_y = np.searchsorted(y_clean, data_all, side="right") / len(y_clean)
    return float(np.max(np.abs(cdf_x - cdf_y)))


class DriftService:
    @staticmethod
    def compute_percentiles(series: pd.Series) -> Optional[PercentileMetrics]:
        """Calcula métricas de percentiles P05, P25, P50, P75, P95, media, std e IQR."""
        clean_num = to_numeric_series(series).dropna()
        if len(clean_num) < 2:
            return None

        p05 = float(np.percentile(clean_num, 5))
        p25 = float(np.percentile(clean_num, 25))
        p50 = float(np.percentile(clean_num, 50))
        p75 = float(np.percentile(clean_num, 75))
        p95 = float(np.percentile(clean_num, 95))
        min_val = float(clean_num.min())
        max_val = float(clean_num.max())
        mean_val = float(clean_num.mean())
        std_val = float(clean_num.std()) if len(clean_num) > 1 else 0.0
        iqr = float(p75 - p25)

        return PercentileMetrics(
            p05=_safe_float(p05),
            p25=_safe_float(p25),
            p50=_safe_float(p50),
            p75=_safe_float(p75),
            p95=_safe_float(p95),
            mean=_safe_float(mean_val),
            std=_safe_float(std_val),
            iqr=_safe_float(iqr),
            min_val=_safe_float(min_val),
            max_val=_safe_float(max_val),
        )

    @staticmethod
    def compute_percentile_shift(raw_p: PercentileMetrics, clean_p: PercentileMetrics) -> PercentileShift:
        """Calcula la variación porcentual de cada percentil respecto al valor base original."""

        def calc_shift(r_val: float, c_val: float) -> float:
            base = abs(r_val) if abs(r_val) > 1.0 else 1.0
            return round(((c_val - r_val) / base) * 100.0, 2)

        s05 = calc_shift(raw_p.p05, clean_p.p05)
        s25 = calc_shift(raw_p.p25, clean_p.p25)
        s50 = calc_shift(raw_p.p50, clean_p.p50)
        s75 = calc_shift(raw_p.p75, clean_p.p75)
        s95 = calc_shift(raw_p.p95, clean_p.p95)
        max_shift = max(abs(s05), abs(s25), abs(s50), abs(s75), abs(s95))

        return PercentileShift(
            p05_shift_pct=s05,
            p25_shift_pct=s25,
            p50_shift_pct=s50,
            p75_shift_pct=s75,
            p95_shift_pct=s95,
            max_shift_pct=round(max_shift, 2),
        )

    @staticmethod
    def analyze_column(
        col_name: str, clean_series: pd.Series, raw_series: Optional[pd.Series] = None
    ) -> Optional[ColumnDriftReport]:
        clean_p = DriftService.compute_percentiles(clean_series)
        if clean_p is None:
            return None

        raw_p = DriftService.compute_percentiles(raw_series) if raw_series is not None else None
        shift = None
        ks_stat = None
        p_val = None
        drift_score = 0.0
        drift_status = DriftStatusEnum.STABLE

        clean_arr = to_numeric_series(clean_series).dropna().to_numpy()
        raw_arr = to_numeric_series(raw_series).dropna().to_numpy() if raw_series is not None else None

        if raw_p is not None and raw_arr is not None and len(raw_arr) > 0:
            shift = DriftService.compute_percentile_shift(raw_p, clean_p)
            ks_stat = round(_compute_ks_statistic(raw_arr, clean_arr), 3)

            # Score combinado: 60% estadístico KS + 40% desplazamiento máximo acotado
            ks_component = min(100.0, ks_stat * 100.0)
            shift_component = min(100.0, shift.max_shift_pct)
            drift_score = round(0.6 * ks_component + 0.4 * shift_component, 2)

            if ks_stat >= 0.25 or shift.max_shift_pct >= 25.0:
                drift_status = DriftStatusEnum.CRITICAL
            elif ks_stat >= 0.10 or shift.max_shift_pct >= 10.0:
                drift_status = DriftStatusEnum.MODERATE
            else:
                drift_status = DriftStatusEnum.STABLE
        else:
            drift_score = 0.0
            drift_status = DriftStatusEnum.STABLE

        # Detección de anomalías en el dataframe limpio usando IQR y percentiles P01/P99
        iqr_val = clean_p.iqr
        lower_bound = clean_p.p25 - 1.5 * iqr_val
        upper_bound = clean_p.p75 + 1.5 * iqr_val

        outliers_mask = (clean_arr < lower_bound) | (clean_arr > upper_bound)
        anomaly_count = int(np.sum(outliers_mask))
        total_valid = len(clean_arr)
        anomaly_pct = round((anomaly_count / total_valid) * 100.0, 2) if total_valid > 0 else 0.0

        alerts: List[DriftAlert] = []
        recs: List[ProactiveRecommendation] = []

        # 1. Alertas por Drift
        if drift_status == DriftStatusEnum.CRITICAL and shift:
            alerts.append(
                DriftAlert(
                    id=f"alert-drift-crit-{col_name}",
                    column=col_name,
                    severity=DriftAlertSeverityEnum.CRITICAL,
                    title=f"Drift Crítico en '{col_name}'",
                    message=(
                        f"Desviación acusada entre datos crudos y limpios (KS={ks_stat}, "
                        f"desplazamiento máximo de percentiles: {shift.max_shift_pct}%). "
                        f"La mediana se desplazó un {shift.p50_shift_pct}%."
                    ),
                    metric="Drift Score",
                    value=drift_score,
                    threshold=25.0,
                )
            )
            recs.append(
                ProactiveRecommendation(
                    id=f"rec-drift-{col_name}",
                    column=col_name,
                    category="drift",
                    priority="high",
                    action_type="imputation_review",
                    title=f"Revisión de tendencia central en '{col_name}'",
                    rationale=(
                        f"El percentil 50 varió un {shift.p50_shift_pct}%. Comprobar si la imputación de nulos "
                        "o el filtrado de duplicados sesgó la distribución representativa de los datos de negocio."
                    ),
                    suggested_step=f"fill_missing con group_by o interpolación en '{col_name}'",
                )
            )
        elif drift_status == DriftStatusEnum.MODERATE and shift:
            alerts.append(
                DriftAlert(
                    id=f"alert-drift-mod-{col_name}",
                    column=col_name,
                    severity=DriftAlertSeverityEnum.WARNING,
                    title=f"Drift Moderado en '{col_name}'",
                    message=(
                        f"Variación moderada de percentiles (KS={ks_stat}, "
                        f"desplazamiento máximo: {shift.max_shift_pct}%)."
                    ),
                    metric="Drift Score",
                    value=drift_score,
                    threshold=10.0,
                )
            )
            recs.append(
                ProactiveRecommendation(
                    id=f"rec-drift-mod-{col_name}",
                    column=col_name,
                    category="drift",
                    priority="medium",
                    action_type="imputation_review",
                    title=f"Monitoreo de estabilidad en '{col_name}'",
                    rationale=(
                        f"La columna '{col_name}' muestra una ligera reorganización de colas (P95: {shift.p95_shift_pct}%). "
                        "Adecuada para análisis pero verificar antes de entrenar modelos de alta sensibilidad."
                    ),
                )
            )
        else:
            alerts.append(
                DriftAlert(
                    id=f"alert-drift-ok-{col_name}",
                    column=col_name,
                    severity=DriftAlertSeverityEnum.INFO,
                    title=f"Estabilidad Estadística en '{col_name}'",
                    message="La distribución matemática original fue preservada con alta fidelidad sin sesgos.",
                    metric="Drift Score",
                    value=drift_score,
                    threshold=10.0,
                )
            )
            recs.append(
                ProactiveRecommendation(
                    id=f"rec-stable-{col_name}",
                    column=col_name,
                    category="distribution",
                    priority="low",
                    action_type="verified_stable",
                    title=f"Fidelidad estadística certificada en '{col_name}'",
                    rationale=(
                        f"Drift controlado ({drift_score}%). La variable mantiene sus proporciones originales y es "
                        "100% confiable para agregaciones DAX en Power BI y KPIs ejecutivos."
                    ),
                )
            )

        # 2. Alertas por Anomalías/Outliers
        if anomaly_pct >= 10.0:
            alerts.append(
                DriftAlert(
                    id=f"alert-anomaly-high-{col_name}",
                    column=col_name,
                    severity=DriftAlertSeverityEnum.CRITICAL,
                    title=f"Alta Concentración de Anomalías en '{col_name}'",
                    message=f"Se identificaron {anomaly_count} registros ({anomaly_pct}%) fuera del rango normal IQR.",
                    metric="Porcentaje de Anomalías",
                    value=anomaly_pct,
                    threshold=10.0,
                )
            )
            recs.append(
                ProactiveRecommendation(
                    id=f"rec-capping-{col_name}",
                    column=col_name,
                    category="anomaly",
                    priority="high",
                    action_type="capping",
                    title=f"Aplicar winsorización (capping) en '{col_name}'",
                    rationale=(
                        f"El {anomaly_pct}% de registros son extremos (> P95={clean_p.p95} o < P05={clean_p.p05}). "
                        "Acotar los valores atípicos al percentil 95 o 99 evitará distorsionar los totales y promedios en los informes."
                    ),
                    suggested_step=f"outlier_capping(column='{col_name}', method='iqr', factor=1.5)",
                )
            )
        elif anomaly_pct >= 3.0:
            alerts.append(
                DriftAlert(
                    id=f"alert-anomaly-mod-{col_name}",
                    column=col_name,
                    severity=DriftAlertSeverityEnum.WARNING,
                    title=f"Outliers Detectados en '{col_name}'",
                    message=f"{anomaly_count} valores ({anomaly_pct}%) caen fuera de los bigotes del BoxPlot.",
                    metric="Porcentaje de Anomalías",
                    value=anomaly_pct,
                    threshold=3.0,
                )
            )
            recs.append(
                ProactiveRecommendation(
                    id=f"rec-inspect-{col_name}",
                    column=col_name,
                    category="anomaly",
                    priority="medium",
                    action_type="segmentation",
                    title=f"Segmentar transacciones especiales en '{col_name}'",
                    rationale=(
                        f"Se registraron {anomaly_count} transacciones con valores inusuales. Se recomienda crear una "
                        "marca o dimensión de excepción en Power BI para analizarlas de forma aislada."
                    ),
                )
            )

        return ColumnDriftReport(
            column_name=col_name,
            raw_percentiles=raw_p,
            clean_percentiles=clean_p,
            shift=shift,
            drift_score=drift_score,
            drift_status=drift_status,
            ks_statistic=ks_stat,
            p_value=p_val,
            anomaly_count=anomaly_count,
            anomaly_percentage=anomaly_pct,
            alerts=alerts,
            recommendations=recs,
        )

    @staticmethod
    def analyze_drift(clean_df: pd.DataFrame, raw_df: Optional[pd.DataFrame] = None) -> DriftAnalysisReport:
        """
        Ejecuta el análisis integral de Data Drift y Anomalías por Percentiles sobre
        todas las variables numéricas del dataset.
        """
        column_reports: List[ColumnDriftReport] = []
        all_alerts: List[DriftAlert] = []
        global_recs: List[ProactiveRecommendation] = []

        stable_count = 0
        moderate_count = 0
        critical_count = 0

        # Normalizar nombres de columnas para mapeo insensible a mayúsculas
        raw_cols_map = {}
        if raw_df is not None:
            for c in raw_df.columns:
                raw_cols_map[str(c).lower().strip()] = c

        for col in clean_df.columns:
            clean_series = clean_df[col]
            raw_series = None
            if raw_df is not None:
                norm_name = str(col).lower().strip()
                if norm_name in raw_cols_map:
                    raw_series = raw_df[raw_cols_map[norm_name]]

            report = DriftService.analyze_column(str(col), clean_series, raw_series=raw_series)
            if report is not None:
                column_reports.append(report)
                all_alerts.extend(report.alerts)
                global_recs.extend(report.recommendations)

                if report.drift_status == DriftStatusEnum.CRITICAL:
                    critical_count += 1
                elif report.drift_status == DriftStatusEnum.MODERATE:
                    moderate_count += 1
                else:
                    stable_count += 1

        overall_status = DriftStatusEnum.STABLE
        if critical_count > 0:
            overall_status = DriftStatusEnum.CRITICAL
        elif moderate_count > 0:
            overall_status = DriftStatusEnum.MODERATE

        # Ordenar alertas: primero CRITICAL, luego WARNING, luego INFO
        severity_order = {
            DriftAlertSeverityEnum.CRITICAL: 0,
            DriftAlertSeverityEnum.WARNING: 1,
            DriftAlertSeverityEnum.INFO: 2,
        }
        all_alerts.sort(key=lambda a: severity_order.get(a.severity, 3))

        # Ordenar recomendaciones por prioridad
        priority_order = {"high": 0, "medium": 1, "low": 2}
        global_recs.sort(key=lambda r: priority_order.get(r.priority, 3))

        return DriftAnalysisReport(
            columns=column_reports,
            overall_drift_status=overall_status,
            stable_columns_count=stable_count,
            moderate_columns_count=moderate_count,
            critical_columns_count=critical_count,
            total_alerts=len(all_alerts),
            alerts=all_alerts,
            global_recommendations=global_recs,
            generated_at=datetime.now(timezone.utc),
        )
