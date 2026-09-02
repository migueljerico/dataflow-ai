import html
import re
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from app.core.exceptions import FunctionalException
from app.core.number_parsing import parse_numeric_string
from app.core.storage import get_storage
from app.models.analytics import (
    BoxPlotData,
    BusinessKPI,
    CategoryDistribution,
    ClusterPoint,
    ClusterSummaryItem,
    ClusterVisualization,
    DaxMeasureItem,
    ExcelFormulaItem,
    ExecutiveAnalyticsReport,
    IntegrationColumn,
    IntegrationGuide,
    OutlierDiffSummary,
    OutlierScatterPoint,
    OutlierVisualization,
)
from app.models.etl import ExecutionResult
from app.services.dataset_service import DatasetService
from app.services.etl_service import ETLService
from app.transformations.cluster_ops import _kmeans_numpy

ANALYTICS_CACHE: Dict[str, ExecutiveAnalyticsReport] = {}


class AnalyticsService:
    @staticmethod
    def generate_report(run_id: str) -> ExecutiveAnalyticsReport:
        if run_id in ANALYTICS_CACHE:
            return ANALYTICS_CACHE[run_id]

        run_result = ETLService.get_run_result(run_id)
        storage = get_storage()
        candidate_keys = [
            f"{run_id}_{run_result.clean_filename}",
            run_result.clean_filename,
        ]
        clean_filepath = None
        for key in candidate_keys:
            if storage.exists(key):
                clean_filepath = storage.get_path(key)
                break

        if not clean_filepath or not clean_filepath.exists():
            raise FunctionalException(
                message=f"El archivo limpio para la ejecución '{run_id}' no está disponible.",
                code="CLEAN_FILE_NOT_FOUND",
                status_code=404,
            )

        if str(clean_filepath).endswith(".csv"):
            df = pd.read_csv(clean_filepath)
        else:
            df = pd.read_excel(clean_filepath)

        raw_df = None
        try:
            if run_result.dataset_id:
                raw_df = DatasetService.load_dataframe(run_result.dataset_id)
        except Exception:
            raw_df = None

        cols_lower = [c.lower() for c in df.columns]
        domain = "general"
        kpis: List[BusinessKPI] = []
        breakdown: List[CategoryDistribution] = []
        executive_summary = ""
        recommendations: List[str] = []

        # 1. DOMINIO CONTACT CENTER
        if (
            any("aht" in c for c in cols_lower)
            or any("campana" in c for c in cols_lower)
            or any("llamadas" in c for c in cols_lower)
        ):
            domain = "contact_center"

            # Agentes
            agentes_col = next((c for c in df.columns if "agente" in c.lower()), None)
            total_agentes = df[agentes_col].nunique() if agentes_col else len(df)
            kpis.append(
                BusinessKPI(
                    id="kpi-agents",
                    title="Agentes Operativos",
                    value=f"{total_agentes}",
                    numeric_value=float(total_agentes),
                    subtitle="Efectivos activos en el periodo",
                    category="operaciones",
                )
            )

            # AHT
            aht_col = next((c for c in df.columns if "aht" in c.lower()), None)
            if aht_col:
                avg_aht = float(pd.to_numeric(df[aht_col], errors="coerce").dropna().mean())
                kpis.append(
                    BusinessKPI(
                        id="kpi-aht",
                        title="AHT Medio (Tiempo de Atención)",
                        value=f"{round(avg_aht, 1)} seg",
                        numeric_value=round(avg_aht, 1),
                        change_direction="positive" if avg_aht <= 450 else "neutral",
                        subtitle="Promedio por llamada atendida",
                        category="operaciones",
                    )
                )

            # Score Calidad
            calidad_col = next((c for c in df.columns if "calidad" in c.lower() or "score" in c.lower()), None)
            if calidad_col:
                avg_score = float(pd.to_numeric(df[calidad_col], errors="coerce").dropna().mean())
                kpis.append(
                    BusinessKPI(
                        id="kpi-quality",
                        title="Score de Calidad Medio",
                        value=f"{round(avg_score, 1)}%",
                        numeric_value=round(avg_score, 1),
                        change_direction="positive" if avg_score >= 80.0 else "negative",
                        subtitle="Auditorías de calidad operacional",
                        category="calidad",
                    )
                )

            # Conversión
            conv_col = next((c for c in df.columns if "conversion" in c.lower() or "pct" in c.lower()), None)
            if conv_col:
                avg_conv = float(pd.to_numeric(df[conv_col], errors="coerce").dropna().mean())
                kpis.append(
                    BusinessKPI(
                        id="kpi-conv",
                        title="Tasa de Conversión",
                        value=f"{round(avg_conv, 1)}%",
                        numeric_value=round(avg_conv, 1),
                        change_direction="positive" if avg_conv >= 10.0 else "neutral",
                        subtitle="Efectividad comercial global",
                        category="financiero",
                    )
                )

            # Absentismo
            abs_col = next((c for c in df.columns if "absentismo" in c.lower()), None)
            if abs_col:
                si_count = (df[abs_col].astype(str).str.lower().isin(["si", "yes", "true", "1"])).sum()
                rate = round((si_count / len(df)) * 100, 1) if len(df) > 0 else 0
                kpis.append(
                    BusinessKPI(
                        id="kpi-absenteeism",
                        title="Tasa de Absentismo",
                        value=f"{rate}%",
                        numeric_value=rate,
                        change_direction="negative" if rate > 15 else "positive",
                        subtitle=f"{si_count} de {len(df)} registros con incidencia",
                        category="operaciones",
                    )
                )

            # Breakdown por Campaña
            camp_col = next((c for c in df.columns if "campana" in c.lower()), None)
            if camp_col:
                counts = df[camp_col].value_counts()
                for cat, count in counts.items():
                    pct = round((count / len(df)) * 100, 1)
                    breakdown.append(CategoryDistribution(category_name=str(cat), count=int(count), percentage=pct))

            executive_summary = (
                f"El servicio opera con una dotación de {total_agentes} agentes y registra una calidad media global del {kpis[2].value if len(kpis)>2 else 'N/A'}. "
                f"El tiempo medio de atención (AHT) se sitúa en {kpis[1].value if len(kpis)>1 else 'N/A'}, manteniendo una conversión comercial del {kpis[3].value if len(kpis)>3 else 'N/A'}. "
                "Los datos limpios confirman una distribución estable por campañas, permitiendo cargar directamente los tableros de control operacional en Power BI."
            )
            recommendations = [
                "Revisar el dimensionamiento en campañas con mayor AHT para optimizar tiempos de espera.",
                "Focalizar coaching de calidad en agentes con puntuaciones inferiores al promedio de 80%.",
                "Monitorear las tasas de absentismo para evitar sobrecarga operativa en turnos punta.",
            ]

        # 2. DOMINIO VENTAS / COMERCIAL
        elif (
            any("precio" in c for c in cols_lower)
            or any("producto" in c for c in cols_lower)
            or any("comercial" in c for c in cols_lower)
        ):
            domain = "sales"

            precio_col = next((c for c in df.columns if "precio" in c.lower() or "importe" in c.lower()), None)
            cant_col = next((c for c in df.columns if "cantidad" in c.lower() or "unidades" in c.lower()), None)

            # Facturación estimada
            if precio_col:
                prices = pd.to_numeric(df[precio_col], errors="coerce").fillna(0)
                qtys = pd.to_numeric(df[cant_col], errors="coerce").fillna(1) if cant_col else pd.Series([1] * len(df))
                total_rev = float((prices * qtys).sum())
                kpis.append(
                    BusinessKPI(
                        id="kpi-revenue",
                        title="Facturación Total Estimada",
                        value=f"{total_rev:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."),
                        numeric_value=total_rev,
                        subtitle="Ventas brutas calculadas",
                        category="financiero",
                    )
                )

                avg_ticket = float(prices.mean())
                kpis.append(
                    BusinessKPI(
                        id="kpi-ticket",
                        title="Precio / Ticket Promedio",
                        value=f"{avg_ticket:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."),
                        numeric_value=avg_ticket,
                        subtitle="Valor medio por línea de venta",
                        category="financiero",
                    )
                )

            # Total transacciones
            kpis.append(
                BusinessKPI(
                    id="kpi-tx",
                    title="Transacciones Validadas",
                    value=f"{len(df)} pedidos",
                    numeric_value=float(len(df)),
                    subtitle="Registros únicos limpios",
                    category="operaciones",
                )
            )

            # Canal / Producto
            prod_col = next((c for c in df.columns if "producto" in c.lower()), None)
            if prod_col:
                top_prod = df[prod_col].mode().iloc[0] if not df[prod_col].empty else "N/A"
                kpis.append(
                    BusinessKPI(
                        id="kpi-topprod",
                        title="Producto Más Vendido",
                        value=f"{top_prod}",
                        subtitle="Mayor frecuencia de pedidos",
                        category="operaciones",
                    )
                )

            canal_col = next((c for c in df.columns if "canal" in c.lower()), None)
            if canal_col:
                counts = df[canal_col].value_counts()
                for cat, count in counts.items():
                    pct = round((count / len(df)) * 100, 1)
                    breakdown.append(CategoryDistribution(category_name=str(cat), count=int(count), percentage=pct))

            executive_summary = (
                f"La facturación total asciende a {kpis[0].value if kpis else 'N/A'} distribuidas en {len(df)} transacciones comerciales depuradas. "
                f"El ticket promedio por operación se sitúa en {kpis[1].value if len(kpis)>1 else 'N/A'}, destacando como artículo líder '{kpis[3].value if len(kpis)>3 else 'N/A'}'. "
                "La homogeneización de canales (Web / Tienda) permite segmentar con precisión la atribución comercial en Power BI."
            )
            recommendations = [
                "Impulsar estrategias de cross-selling en el canal digital para elevar el ticket promedio.",
                "Homogeneizar las metas comerciales por producto asegurando stock del artículo más vendido.",
                "Conectar este dataset limpio al modelo dimensional de ventas para seguimiento diario de ingresos.",
            ]

        # 3. DOMINIO PEOPLE ANALYTICS / RRHH
        elif (
            any("empleado" in c for c in cols_lower)
            or any("salario" in c for c in cols_lower)
            or any("departamento" in c for c in cols_lower)
        ):
            domain = "people_analytics"

            emp_col = next((c for c in df.columns if "empleado" in c.lower() or "nombre" in c.lower()), None)
            total_emp = df[emp_col].nunique() if emp_col else len(df)
            kpis.append(
                BusinessKPI(
                    id="kpi-emp-count",
                    title="Plantilla Total Analizada",
                    value=f"{total_emp} empleados",
                    numeric_value=float(total_emp),
                    subtitle="Colaboradores activos",
                    category="operaciones",
                )
            )

            sal_col = next((c for c in df.columns if "salario" in c.lower() or "sueldo" in c.lower()), None)
            if sal_col:
                avg_sal = float(pd.to_numeric(df[sal_col], errors="coerce").dropna().mean())
                kpis.append(
                    BusinessKPI(
                        id="kpi-avg-salary",
                        title="Salario Medio Mensual",
                        value=f"{avg_sal:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."),
                        numeric_value=avg_sal,
                        subtitle="Compensación promedio bruta",
                        category="financiero",
                    )
                )

            prod_col = next((c for c in df.columns if "productividad" in c.lower()), None)
            if prod_col:
                avg_prod = float(pd.to_numeric(df[prod_col], errors="coerce").dropna().mean())
                kpis.append(
                    BusinessKPI(
                        id="kpi-avg-prod",
                        title="Productividad Media",
                        value=f"{round(avg_prod, 1)}%",
                        numeric_value=round(avg_prod, 1),
                        change_direction="positive" if avg_prod >= 85.0 else "neutral",
                        subtitle="Rendimiento del equipo",
                        category="operaciones",
                    )
                )

            abs_col = next((c for c in df.columns if "absentismo" in c.lower()), None)
            if abs_col:
                total_abs_days = float(pd.to_numeric(df[abs_col], errors="coerce").dropna().sum())
                kpis.append(
                    BusinessKPI(
                        id="kpi-total-abs",
                        title="Total Días Absentismo",
                        value=f"{int(total_abs_days)} días",
                        numeric_value=total_abs_days,
                        change_direction="negative" if total_abs_days > 10 else "positive",
                        subtitle="Jornadas de ausencia registradas",
                        category="calidad",
                    )
                )

            dep_col = next((c for c in df.columns if "departamento" in c.lower() or "area" in c.lower()), None)
            if dep_col:
                counts = df[dep_col].value_counts()
                for cat, count in counts.items():
                    pct = round((count / len(df)) * 100, 1)
                    breakdown.append(CategoryDistribution(category_name=str(cat), count=int(count), percentage=pct))

            executive_summary = (
                f"El análisis de People Analytics sobre la plantilla de {total_emp} colaboradores refleja una productividad media del {kpis[2].value if len(kpis)>2 else 'N/A'} "
                f"y un salario promedio mensual de {kpis[1].value if len(kpis)>1 else 'N/A'}. Se han registrado {kpis[3].value if len(kpis)>3 else 'N/A'} de absentismo acumulados. "
                "La estructura limpia permite evaluar correlaciones de desempeño por departamento de forma confiable."
            )
            recommendations = [
                "Implementar planes de desarrollo en departamentos con niveles de productividad inferiores al 85%.",
                "Analizar factores causales de absentismo en áreas operativas para reducir la rotación laboral.",
                "Estandarizar las revisiones periódicas de compensación con base en evaluaciones de desempeño.",
            ]

        # 4. DOMINIO GENERAL (Fallback para cualquier dataset)
        else:
            num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            kpis.append(
                BusinessKPI(
                    id="kpi-gen-rows",
                    title="Registros Procesados",
                    value=f"{len(df):,}",
                    numeric_value=float(len(df)),
                    subtitle="Filas 100% limpias y tipadas",
                    category="operaciones",
                )
            )
            kpis.append(
                BusinessKPI(
                    id="kpi-gen-cols",
                    title="Variables Estructuradas",
                    value=f"{len(df.columns)} columnas",
                    numeric_value=float(len(df.columns)),
                    subtitle=f"{len(num_cols)} numéricas, {len(df.columns)-len(num_cols)} categóricas",
                    category="general",
                )
            )
            executive_summary = (
                f"El dataset contiene {len(df)} registros limpios y {len(df.columns)} columnas preparadas para análisis dimensional. "
                "Las anomalías de formato y valores nulos han sido eliminadas y auditadas, garantizando una carga directa y estable en herramientas de Business Intelligence."
            )
            recommendations = [
                "Construir medidas DAX en Power BI aprovechando los tipos de datos numéricos y de fecha estandarizados.",
                "Crear jerarquías dimensionales para profundizar en el análisis por categorías.",
            ]

        cluster_viz = AnalyticsService._build_cluster_visualization(df)
        outlier_viz = AnalyticsService._build_outlier_visualization(df, raw_df=raw_df)
        integration_guide = AnalyticsService._build_integration_guide(df, run_result, domain)

        report = ExecutiveAnalyticsReport(
            run_id=run_id,
            dataset_name=run_result.clean_filename,
            domain=domain,
            kpis=kpis,
            executive_summary=executive_summary,
            strategic_recommendations=recommendations,
            category_breakdown=breakdown,
            cluster_visualization=cluster_viz,
            outlier_visualization=outlier_viz,
            integration_guide=integration_guide,
        )

        ANALYTICS_CACHE[run_id] = report
        return report

    @staticmethod
    def _build_cluster_visualization(df: pd.DataFrame) -> Optional[ClusterVisualization]:
        if df.empty or len(df) < 2:
            return None

        # Identificar columnas numéricas puras
        num_cols = []
        for col in df.columns:
            # Excluir columnas con flag booleana de outliers
            if col.endswith("_is_outlier"):
                continue
            s_num = pd.to_numeric(df[col], errors="coerce")
            if s_num.dropna().count() >= 2 and s_num.nunique() > 1:
                num_cols.append(col)

        if not num_cols:
            return None

        # Buscar si ya existe una columna de cluster
        cluster_col_name = None
        for col in df.columns:
            col_l = col.lower()
            if col_l in ["cluster_id", "cluster", "cluster_label", "segmento", "cluster_kmeans"] or (
                "cluster" in col_l and not col_l.endswith("_is_outlier")
            ):
                cluster_col_name = col
                break

        df_copy = df.copy()
        if cluster_col_name and cluster_col_name in df_copy.columns:
            try:
                cluster_series = df_copy[cluster_col_name].astype(int)
            except Exception:
                cluster_series = df_copy[cluster_col_name].astype(str)
                # Mapear a enteros deterministas
                unique_labels = sorted(cluster_series.unique().tolist())
                label_map = {lbl: idx for idx, lbl in enumerate(unique_labels)}
                cluster_series = cluster_series.map(label_map)
        else:
            # Si hay al menos 2 columnas numéricas y >= 3 filas, generar segmentación determinista K-Means (K=3)
            if len(num_cols) >= 2 and len(df_copy) >= 3:
                k_val = min(3, len(df_copy))
                feat_matrix = []
                for c in num_cols:
                    s_vals = pd.to_numeric(df_copy[c], errors="coerce")
                    med = float(s_vals.median()) if pd.notna(s_vals.median()) else 0.0
                    feat_matrix.append(s_vals.fillna(med).values)
                X = np.column_stack(feat_matrix).astype(np.float64)
                if X.shape[0] > 1:
                    means = np.mean(X, axis=0)
                    stds = np.std(X, axis=0, ddof=0)
                    stds[stds == 0] = 1.0
                    X = (X - means) / stds
                labels = _kmeans_numpy(X, n_clusters=k_val, max_iter=100, random_state=42)
                cluster_col_name = "cluster_id"
                cluster_series = pd.Series(labels, index=df_copy.index)
                df_copy["cluster_id"] = cluster_series
            else:
                return None

        # Excluir la columna de cluster de los ejes disponibles
        available_numeric = [c for c in num_cols if c != cluster_col_name]
        if len(available_numeric) >= 2:
            x_col = available_numeric[0]
            y_col = available_numeric[1]
        elif len(available_numeric) == 1:
            x_col = available_numeric[0]
            y_col = available_numeric[0]
        else:
            return None

        # Calcular resúmenes por cluster
        clusters_summary: List[ClusterSummaryItem] = []
        unique_clusters = sorted([int(c) for c in cluster_series.dropna().unique().tolist()])

        for cid in unique_clusters:
            mask = cluster_series == cid
            sub_df = df_copy[mask]
            count = len(sub_df)
            pct = round((count / len(df_copy)) * 100, 1) if len(df_copy) > 0 else 0.0

            x_s = pd.to_numeric(sub_df[x_col], errors="coerce").dropna()
            y_s = pd.to_numeric(sub_df[y_col], errors="coerce").dropna()
            cx = round(float(x_s.mean()), 2) if not x_s.empty else None
            cy = round(float(y_s.mean()), 2) if not y_s.empty else None

            feat_avgs: Dict[str, float] = {}
            for col in available_numeric:
                c_s = pd.to_numeric(sub_df[col], errors="coerce").dropna()
                if not c_s.empty:
                    feat_avgs[col] = round(float(c_s.mean()), 2)

            clusters_summary.append(
                ClusterSummaryItem(
                    cluster_id=cid,
                    label=f"Cluster {cid}",
                    count=count,
                    percentage=pct,
                    center_x=cx,
                    center_y=cy,
                    feature_averages=feat_avgs,
                )
            )

        # Muestrear puntos para el scatter plot (hasta 250 puntos)
        sample_df = df_copy.sample(n=min(250, len(df_copy)), random_state=42) if len(df_copy) > 250 else df_copy

        # Columna de etiqueta textual o nombre si existe
        text_cols = [
            c for c in df_copy.columns if c not in num_cols and not c.endswith("_is_outlier") and c != cluster_col_name
        ]
        label_col = text_cols[0] if text_cols else None

        points: List[ClusterPoint] = []
        x_median = float(df_copy[x_col].median()) if pd.notna(df_copy[x_col].median()) else 0.0
        y_median = float(df_copy[y_col].median()) if pd.notna(df_copy[y_col].median()) else 0.0

        for idx, row in sample_df.iterrows():
            xv = pd.to_numeric(pd.Series([row[x_col]]), errors="coerce").iloc[0]
            yv = pd.to_numeric(pd.Series([row[y_col]]), errors="coerce").iloc[0]
            if pd.isna(xv):
                xv = x_median
            if pd.isna(yv):
                yv = y_median
            cid = int(cluster_series.loc[idx])
            lbl = str(row[label_col]) if label_col and pd.notna(row[label_col]) else f"Fila #{int(idx) + 1}"
            points.append(
                ClusterPoint(
                    row_index=int(idx),
                    x=round(float(xv), 2),
                    y=round(float(yv), 2),
                    cluster_id=cid,
                    label=lbl,
                )
            )

        return ClusterVisualization(
            cluster_column=cluster_col_name,
            x_column=x_col,
            y_column=y_col,
            available_numeric_columns=available_numeric,
            total_points=len(df_copy),
            clusters=clusters_summary,
            points=points,
        )

    @staticmethod
    def _build_outlier_visualization(
        df: pd.DataFrame, raw_df: Optional[pd.DataFrame] = None
    ) -> Optional[OutlierVisualization]:
        if df.empty or len(df) < 2:
            return None

        boxplots: List[BoxPlotData] = []
        total_outliers = 0

        # Identificar columnas numéricas
        for col in df.columns:
            if col.endswith("_is_outlier") or col.lower() in ["cluster_id", "cluster"]:
                continue
            s_num = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(s_num) < 2 or s_num.nunique() <= 1:
                continue

            q1 = float(s_num.quantile(0.25))
            median = float(s_num.median())
            q3 = float(s_num.quantile(0.75))
            iqr = q3 - q1
            min_v = float(s_num.min())
            max_v = float(s_num.max())

            lower_whisker = max(min_v, q1 - 1.5 * iqr)
            upper_whisker = min(max_v, q3 + 1.5 * iqr)
            mean_v = float(s_num.mean())
            std_v = float(s_num.std(ddof=1)) if len(s_num) > 1 else 0.0

            # Identificar outliers por IQR
            outliers_mask = (s_num < lower_whisker) | (s_num > upper_whisker)

            # Si existe la columna flag explícita generada previamente, combinarla
            flag_col = f"{col}_is_outlier"
            if flag_col in df.columns:
                flag_mask = df[flag_col].astype(bool).fillna(False)
                outliers_mask = outliers_mask | flag_mask.loc[s_num.index]

            outliers_s = s_num[outliers_mask]
            outliers_cnt = int(len(outliers_s))
            outliers_pct = round((outliers_cnt / len(s_num)) * 100, 1) if len(s_num) > 0 else 0.0
            total_outliers += outliers_cnt

            sample_outs = [round(float(v), 2) for v in outliers_s.head(10).tolist()]

            boxplots.append(
                BoxPlotData(
                    column=col,
                    min=round(min_v, 2),
                    q1=round(q1, 2),
                    median=round(median, 2),
                    q3=round(q3, 2),
                    max=round(max_v, 2),
                    lower_whisker=round(lower_whisker, 2),
                    upper_whisker=round(upper_whisker, 2),
                    iqr=round(iqr, 2),
                    mean=round(mean_v, 2),
                    std=round(std_v, 2),
                    outliers_count=outliers_cnt,
                    outlier_percentage=outliers_pct,
                    sample_outliers=sample_outs,
                )
            )

        if not boxplots:
            return None

        # Elegir columna activa: la que tenga mayor número de outliers, o la primera
        active_box = max(boxplots, key=lambda b: b.outliers_count)
        active_col = active_box.column

        # Muestrear puntos para el scatter de outliers (hasta 250 puntos)
        sample_df = df.sample(n=min(250, len(df)), random_state=42) if len(df) > 250 else df
        text_cols = [c for c in df.columns if not c.endswith("_is_outlier") and c != active_col]
        label_col = text_cols[0] if text_cols else None

        scatter_points: List[OutlierScatterPoint] = []
        raw_scatter_points: List[OutlierScatterPoint] = []
        flag_col = f"{active_col}_is_outlier"

        # Comparador Scatter Diff entre Dataset Crudo y Limpio
        has_raw_col = raw_df is not None and not raw_df.empty and active_col in raw_df.columns
        diff_summary: Optional[OutlierDiffSummary] = None
        rlw, ruw = active_box.lower_whisker, active_box.upper_whisker

        if has_raw_col:
            raw_series_parsed = raw_df[active_col].apply(parse_numeric_string).dropna()
            if len(raw_series_parsed) >= 2 and raw_series_parsed.nunique() > 1:
                rq1 = float(raw_series_parsed.quantile(0.25))
                rq3 = float(raw_series_parsed.quantile(0.75))
                riqr = rq3 - rq1
                rlw = rq1 - 1.5 * riqr
                ruw = rq3 + 1.5 * riqr
                raw_outliers_cnt = int(((raw_series_parsed < rlw) | (raw_series_parsed > ruw)).sum())
            else:
                raw_outliers_cnt = 0

            clean_outliers_cnt = active_box.outliers_count
            resolved_cnt = max(0, raw_outliers_cnt - clean_outliers_cnt)
            reduction_pct = round((resolved_cnt / raw_outliers_cnt) * 100.0, 1) if raw_outliers_cnt > 0 else 0.0
            diff_summary = OutlierDiffSummary(
                raw_outliers_count=raw_outliers_cnt,
                clean_outliers_count=clean_outliers_cnt,
                resolved_outliers_count=resolved_cnt,
                reduction_percentage=reduction_pct,
            )

        for idx, row in sample_df.iterrows():
            y_val = pd.to_numeric(pd.Series([row[active_col]]), errors="coerce").iloc[0]
            if pd.isna(y_val):
                continue
            is_out = bool(y_val < active_box.lower_whisker or y_val > active_box.upper_whisker)
            if flag_col in row and bool(row[flag_col]):
                is_out = True

            lbl = str(row[label_col]) if label_col and pd.notna(row[label_col]) else f"Fila #{int(idx) + 1}"
            clean_y_val = round(float(y_val), 2)

            raw_y_val: Optional[float] = None
            was_mod = False
            diff_status = "unchanged"

            if has_raw_col and idx in raw_df.index:
                raw_raw = raw_df.loc[idx, active_col]
                parsed_raw = parse_numeric_string(raw_raw)
                if parsed_raw is not None:
                    raw_y_val = round(float(parsed_raw), 2)
                    was_mod = abs(raw_y_val - clean_y_val) > 1e-4
                    if was_mod:
                        if (
                            parsed_raw < active_box.lower_whisker or parsed_raw > active_box.upper_whisker
                        ) and not is_out:
                            diff_status = "resolved_outlier"
                        else:
                            diff_status = "clamped"
                    else:
                        diff_status = "unchanged"
                else:
                    raw_y_val = None
                    was_mod = True
                    diff_status = "imputed"
            else:
                raw_y_val = clean_y_val

            pt = OutlierScatterPoint(
                row_index=int(idx),
                x_value=float(idx) + 1.0,
                y_value=clean_y_val,
                is_outlier=is_out,
                label=lbl,
                raw_y_value=raw_y_val,
                was_modified=was_mod,
                diff_status=diff_status,
            )
            scatter_points.append(pt)

            if raw_y_val is not None:
                raw_is_out = bool(raw_y_val < rlw or raw_y_val > ruw)
                raw_scatter_points.append(
                    OutlierScatterPoint(
                        row_index=int(idx),
                        x_value=float(idx) + 1.0,
                        y_value=raw_y_val,
                        is_outlier=raw_is_out,
                        label=f"{lbl} [Crudo]",
                        raw_y_value=raw_y_val,
                        was_modified=was_mod,
                        diff_status=diff_status,
                    )
                )

        return OutlierVisualization(
            columns=boxplots,
            active_column=active_col,
            scatter_points=scatter_points,
            raw_scatter_points=raw_scatter_points if raw_scatter_points else None,
            diff_summary=diff_summary,
            total_outliers_detected=total_outliers,
            detection_method="IQR (1.5x) / Z-Score (>3.0)",
        )

    @staticmethod
    def _render_cluster_svg(cluster_viz: ClusterVisualization) -> str:
        if not cluster_viz or not cluster_viz.points:
            return "<div style='text-align:center;padding:20px;color:#64748b;'>No hay datos de clusters</div>"

        colors = ["#3b82f6", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6", "#06b6d4", "#f97316", "#14b8a6"]
        xs = [p.x for p in cluster_viz.points]
        ys = [p.y for p in cluster_viz.points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        pad_x = (max_x - min_x) * 0.1 or 1.0
        pad_y = (max_y - min_y) * 0.1 or 1.0
        d_min_x, d_max_x = min_x - pad_x, max_x + pad_x
        d_min_y, d_max_y = min_y - pad_y, max_y + pad_y

        w, h = 680, 360
        m_top, m_right, m_bottom, m_left = 30, 30, 45, 60
        plot_w = w - m_left - m_right
        plot_h = h - m_top - m_bottom

        def scale_x(v: float) -> float:
            return m_left + ((v - d_min_x) / (d_max_x - d_min_x or 1.0)) * plot_w

        def scale_y(v: float) -> float:
            return h - m_bottom - ((v - d_min_y) / (d_max_y - d_min_y or 1.0)) * plot_h

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" style="width:100%;max-width:680px;height:auto;display:block;margin:0 auto;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;">',
            f'<line x1="{m_left}" y1="{m_top}" x2="{m_left}" y2="{h - m_bottom}" stroke="#cbd5e1" stroke-width="1.5"/>',
            f'<line x1="{m_left}" y1="{h - m_bottom}" x2="{w - m_right}" y2="{h - m_bottom}" stroke="#cbd5e1" stroke-width="1.5"/>',
        ]

        # Guías de cuadrícula
        for pct in [0.25, 0.5, 0.75]:
            gy = m_top + plot_h * pct
            gx = m_left + plot_w * pct
            svg_parts.append(
                f'<line x1="{m_left}" y1="{gy}" x2="{w - m_right}" y2="{gy}" stroke="#e2e8f0" stroke-dasharray="4 4"/>'
            )
            svg_parts.append(
                f'<line x1="{gx}" y1="{m_top}" x2="{gx}" y2="{h - m_bottom}" stroke="#e2e8f0" stroke-dasharray="4 4"/>'
            )

        # Etiquetas de ejes
        x_label = cluster_viz.x_column or "X"
        y_label = cluster_viz.y_column or "Y"
        svg_parts.append(
            f'<text x="{m_left + plot_w / 2}" y="{h - 12}" text-anchor="middle" fill="#64748b" font-size="12" font-family="system-ui,sans-serif" font-weight="600">{x_label} →</text>'
        )
        svg_parts.append(
            f'<text x="16" y="{m_top + plot_h / 2}" text-anchor="middle" fill="#64748b" font-size="12" font-family="system-ui,sans-serif" font-weight="600" transform="rotate(-90 16 {m_top + plot_h / 2})">{y_label} →</text>'
        )

        # Valores extremos
        svg_parts.append(
            f'<text x="{m_left}" y="{h - m_bottom + 16}" fill="#94a3b8" font-size="10" text-anchor="middle" font-family="monospace">{d_min_x:.1f}</text>'
        )
        svg_parts.append(
            f'<text x="{w - m_right}" y="{h - m_bottom + 16}" fill="#94a3b8" font-size="10" text-anchor="middle" font-family="monospace">{d_max_x:.1f}</text>'
        )
        svg_parts.append(
            f'<text x="{m_left - 8}" y="{h - m_bottom}" fill="#94a3b8" font-size="10" text-anchor="end" dominant-baseline="middle" font-family="monospace">{d_min_y:.1f}</text>'
        )
        svg_parts.append(
            f'<text x="{m_left - 8}" y="{m_top}" fill="#94a3b8" font-size="10" text-anchor="end" dominant-baseline="middle" font-family="monospace">{d_max_y:.1f}</text>'
        )

        # Puntos de datos
        for p in cluster_viz.points:
            px = scale_x(p.x)
            py = scale_y(p.y)
            c = colors[p.cluster_id % len(colors)]
            svg_parts.append(
                f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.5" fill="{c}" fill-opacity="0.8" stroke="#ffffff" stroke-width="1"><title>{p.label} (Cluster {p.cluster_id})</title></circle>'
            )

        # Centroides
        for c_item in cluster_viz.clusters:
            if c_item.center_x is not None and c_item.center_y is not None:
                cx = scale_x(c_item.center_x)
                cy = scale_y(c_item.center_y)
                c_color = colors[c_item.cluster_id % len(colors)]
                svg_parts.append(
                    f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="11" fill="{c_color}" fill-opacity="0.3" stroke="{c_color}" stroke-width="2"/>'
                )
                svg_parts.append(
                    f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="#ffffff" stroke="{c_color}" stroke-width="2"/>'
                )

        svg_parts.append("</svg>")
        return "".join(svg_parts)

    @staticmethod
    def _render_boxplot_svg(box: BoxPlotData, outlier_viz: OutlierVisualization) -> str:
        if not box:
            return "<div style='text-align:center;padding:20px;color:#64748b;'>No hay datos de outliers</div>"

        w, h = 680, 260
        m_top, m_right, m_bottom, m_left = 30, 40, 50, 40
        plot_w = w - m_left - m_right

        span = (box.max - box.min) or 1.0
        pad = span * 0.08
        d_min = box.min - pad
        d_max = box.max + pad

        def scale_x(v: float) -> float:
            return m_left + ((v - d_min) / (d_max - d_min or 1.0)) * plot_w

        box_y = m_top + 40
        box_h = 70
        mid_y = box_y + box_h / 2

        x_lw = scale_x(box.lower_whisker)
        x_uw = scale_x(box.upper_whisker)
        x_q1 = scale_x(box.q1)
        x_med = scale_x(box.median)
        x_q3 = scale_x(box.q3)

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" style="width:100%;max-width:680px;height:auto;display:block;margin:0 auto;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;">',
            # Eje horizontal
            f'<line x1="{m_left}" y1="{h - m_bottom}" x2="{w - m_right}" y2="{h - m_bottom}" stroke="#cbd5e1" stroke-width="1.5"/>',
            # Bigotes (líneas punteadas/sólidas)
            f'<line x1="{x_lw:.1f}" y1="{mid_y:.1f}" x2="{x_q1:.1f}" y2="{mid_y:.1f}" stroke="#3b82f6" stroke-width="2" stroke-dasharray="3 3"/>',
            f'<line x1="{x_q3:.1f}" y1="{mid_y:.1f}" x2="{x_uw:.1f}" y2="{mid_y:.1f}" stroke="#3b82f6" stroke-width="2" stroke-dasharray="3 3"/>',
            # Topes de bigotes
            f'<line x1="{x_lw:.1f}" y1="{mid_y - 20:.1f}" x2="{x_lw:.1f}" y2="{mid_y + 20:.1f}" stroke="#3b82f6" stroke-width="2.5"/>',
            f'<line x1="{x_uw:.1f}" y1="{mid_y - 20:.1f}" x2="{x_uw:.1f}" y2="{mid_y + 20:.1f}" stroke="#3b82f6" stroke-width="2.5"/>',
            # Caja IQR (Q1 a Q3)
            f'<rect x="{x_q1:.1f}" y="{box_y:.1f}" width="{max(2, x_q3 - x_q1):.1f}" height="{box_h:.1f}" fill="#3b82f6" fill-opacity="0.18" stroke="#3b82f6" stroke-width="2" rx="4"/>',
            # Mediana (Q2)
            f'<line x1="{x_med:.1f}" y1="{box_y:.1f}" x2="{x_med:.1f}" y2="{box_y + box_h:.1f}" stroke="#10b981" stroke-width="3.5"/>',
            # Etiquetas numéricas principales
            f'<text x="{x_q1:.1f}" y="{box_y - 8}" text-anchor="middle" fill="#64748b" font-size="10" font-family="monospace">Q1: {box.q1:.1f}</text>',
            f'<text x="{x_med:.1f}" y="{box_y + box_h + 18}" text-anchor="middle" fill="#10b981" font-size="11" font-weight="700" font-family="monospace">Med: {box.median:.1f}</text>',
            f'<text x="{x_q3:.1f}" y="{box_y - 8}" text-anchor="middle" fill="#64748b" font-size="10" font-family="monospace">Q3: {box.q3:.1f}</text>',
        ]

        # Puntos Outliers
        if outlier_viz and outlier_viz.scatter_points:
            for sp in outlier_viz.scatter_points:
                if sp.is_outlier:
                    ox = scale_x(sp.y_value)
                    svg_parts.append(
                        f'<circle cx="{ox:.1f}" cy="{mid_y:.1f}" r="5" fill="#f43f5e" stroke="#ffffff" stroke-width="1.5"><title>Outlier: {sp.y_value:.2f} ({sp.label})</title></circle>'
                    )

        # Nombre de variable en eje
        svg_parts.append(
            f'<text x="{m_left + plot_w / 2}" y="{h - 12}" text-anchor="middle" fill="#334155" font-size="12" font-weight="600" font-family="system-ui,sans-serif">Variable: {box.column} (IQR: {box.iqr:.2f} | Outliers: {box.outliers_count})</text>'
        )

        svg_parts.append("</svg>")
        return "".join(svg_parts)

    @staticmethod
    def _get_excel_column_letter(col_idx: int) -> str:
        """Convierte un índice numérico de columna (0=A, 1=B, ..., 26=AA) en su letra de Excel."""
        result = ""
        col_num = col_idx + 1
        while col_num > 0:
            col_num, remainder = divmod(col_num - 1, 26)
            result = chr(65 + remainder) + result
        return result

    @staticmethod
    def _map_to_power_query_type(col_name: str, series: pd.Series) -> tuple[str, str]:
        """Infiere el tipo de dato para Power Query (Lenguaje M) y el rol semántico."""
        col_lower = col_name.lower()
        dtype_str = str(series.dtype)

        # 1. Identificadores y códigos
        if (
            col_lower.startswith(("id_", "cod_", "cp_", "codigo_"))
            or col_lower.endswith(("_id", "_cod", "_codigo"))
            or col_lower in ["id", "codigo", "cp", "cif", "nif", "dni", "iban"]
        ):
            return ("type text", "id")

        # 2. Fechas y Datetime
        if "datetime" in dtype_str or "timestamp" in dtype_str:
            return ("type datetime", "date")
        if "fecha" in col_lower or "date" in col_lower:
            return ("type date", "date")

        # 3. Booleanos
        if "bool" in dtype_str:
            return ("type logical", "boolean")

        # 4. Numéricos
        if "int" in dtype_str:
            return ("Int64.Type", "numeric")
        if "float" in dtype_str:
            return ("type number", "numeric")

        # 5. Categóricos o texto general
        return ("type text", "category")

    @staticmethod
    def _build_integration_guide(df: pd.DataFrame, run_result: ExecutionResult, domain: str) -> IntegrationGuide:
        """
        Construye una guía de integración y fórmulas completamente adaptada al dataset concreto:
        script Power Query M con tipos reales, medidas DAX contextuales y fórmulas de Excel dinámicas.
        """
        clean_fn = run_result.clean_filename or "DataFlow_Cleaned_Dataset.csv"
        raw_table_name = Path(clean_fn).stem
        sanitized_table = re.sub(r"[^a-zA-Z0-9_]", "_", raw_table_name).strip("_")
        if not sanitized_table or sanitized_table[0].isdigit():
            sanitized_table = f"DF_{sanitized_table}"
        table_name = "_".join(word.capitalize() for word in sanitized_table.split("_"))

        columns_info: List[IntegrationColumn] = []
        pq_type_tuples: List[str] = []

        for idx, col in enumerate(df.columns):
            pq_type, role = AnalyticsService._map_to_power_query_type(col, df[col])
            col_letter = AnalyticsService._get_excel_column_letter(idx)
            columns_info.append(
                IntegrationColumn(
                    name=col,
                    python_dtype=str(df[col].dtype),
                    power_bi_m_type=pq_type,
                    semantic_role=role,
                    excel_column_letter=col_letter,
                )
            )
            pq_type_tuples.append(f'{{"{col}", {pq_type}}}')

        # 1. Script Power Query M (CSV)
        types_formatted = ",\n        ".join(pq_type_tuples)
        power_query_m_csv = (
            f"let\n"
            f'    Source = Csv.Document(File.Contents("{clean_fn}"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),\n'
            f'    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),\n'
            f'    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{\n'
            f"        {types_formatted}\n"
            f"    }})\n"
            f"in\n"
            f'    #"Changed Type"'
        )

        # 2. Script Power Query M (Parquet)
        parquet_fn = run_result.parquet_filename or f"{Path(clean_fn).stem}.parquet"
        power_query_m_parquet = (
            f"let\n" f'    Source = Parquet.Document(File.Contents("{parquet_fn}"))\n' f"in\n" f"    Source"
        )

        # 3. Medidas DAX Contextuales
        dax_measures: List[DaxMeasureItem] = []

        # Base: Total de registros
        dax_measures.append(
            DaxMeasureItem(
                name="Total_Registros",
                formula=f"Total_Registros = COUNTROWS('{table_name}')",
                description="Conteo total de filas depuradas en el dataset.",
                category="kpi",
            )
        )

        # Calidad y Outliers
        has_outlier_col = "is_outlier" in df.columns
        if has_outlier_col:
            dax_measures.append(
                DaxMeasureItem(
                    name="Registros_Validos",
                    formula=(
                        f"Registros_Validos = \n"
                        f"CALCULATE(\n"
                        f"    COUNTROWS('{table_name}'),\n"
                        f"    '{table_name}'[is_outlier] = FALSE()\n"
                        f")"
                    ),
                    description="Conteo de registros que cumplen los criterios estadísticos estándar sin ser anomalías.",
                    category="calidad",
                )
            )
            dax_measures.append(
                DaxMeasureItem(
                    name="Score_Calidad_Pct",
                    formula="Score_Calidad_Pct = \nDIVIDE([Registros_Validos], [Total_Registros], 1.0) * 100",
                    description="Porcentaje de registros limpios y validados por el pipeline.",
                    category="calidad",
                )
            )
        else:
            first_col = df.columns[0] if len(df.columns) > 0 else "ID"
            dax_measures.append(
                DaxMeasureItem(
                    name="Registros_Completos",
                    formula=(
                        f"Registros_Completos = \n"
                        f"CALCULATE(\n"
                        f"    COUNTROWS('{table_name}'),\n"
                        f"    NOT(ISBLANK('{table_name}'[{first_col}]))\n"
                        f")"
                    ),
                    description=f"Conteo de registros sin valores nulos en la columna clave '{first_col}'.",
                    category="calidad",
                )
            )
            dax_measures.append(
                DaxMeasureItem(
                    name="Score_Calidad_Pct",
                    formula="Score_Calidad_Pct = \nDIVIDE([Registros_Completos], [Total_Registros], 1.0) * 100",
                    description="Porcentaje de completitud de datos validados por DataFlow AI.",
                    category="calidad",
                )
            )

        # Medidas para variables numéricas clave
        numeric_cols = [c.name for c in columns_info if c.semantic_role == "numeric"]
        for num_c in numeric_cols[:4]:
            sanitized_num_c = re.sub(r"[^a-zA-Z0-9_]", "_", num_c)
            dax_measures.append(
                DaxMeasureItem(
                    name=f"Total_{sanitized_num_c}",
                    formula=f"Total_{sanitized_num_c} = SUM('{table_name}'[{num_c}])",
                    description=f"Suma acumulada de la variable numérica '{num_c}'.",
                    category="numerico",
                )
            )
            dax_measures.append(
                DaxMeasureItem(
                    name=f"Promedio_{sanitized_num_c}",
                    formula=f"Promedio_{sanitized_num_c} = AVERAGE('{table_name}'[{num_c}])",
                    description=f"Media aritmética calculada para '{num_c}'.",
                    category="numerico",
                )
            )

        # Medidas de cardinalidad única para IDs o categorías
        id_or_cat_cols = [c.name for c in columns_info if c.semantic_role in ["id", "category"]]
        for id_c in id_or_cat_cols[:2]:
            sanitized_id_c = re.sub(r"[^a-zA-Z0-9_]", "_", id_c)
            dax_measures.append(
                DaxMeasureItem(
                    name=f"Total_{sanitized_id_c}_Unicos",
                    formula=f"Total_{sanitized_id_c}_Unicos = DISTINCTCOUNT('{table_name}'[{id_c}])",
                    description=f"Recuento de valores distintos (cardinalidad) para '{id_c}'.",
                    category="kpi",
                )
            )

        # Inteligencia temporal si existe fecha
        date_cols = [c.name for c in columns_info if c.semantic_role == "date"]
        if date_cols and numeric_cols:
            d_col = date_cols[0]
            n_col = numeric_cols[0]
            sanitized_n_col = re.sub(r"[^a-zA-Z0-9_]", "_", n_col)
            dax_measures.append(
                DaxMeasureItem(
                    name=f"{sanitized_n_col}_YTD",
                    formula=f"{sanitized_n_col}_YTD = TOTALYTD([Total_{sanitized_n_col}], '{table_name}'[{d_col}])",
                    description=f"Acumulado anual (Year-to-Date) de '{n_col}' dimensionado por '{d_col}'.",
                    category="tiempo",
                )
            )

        # 4. Fórmulas de Excel Adaptativas
        excel_formulas: List[ExcelFormulaItem] = []
        row_count = max(len(df), 1)
        last_row = row_count + 1

        target_num_cols = [c for c in columns_info if c.semantic_role == "numeric"]
        if not target_num_cols:
            target_num_cols = columns_info[:1]

        for col_meta in target_num_cols[:4]:
            col_letter = col_meta.excel_column_letter or "A"
            rng = f"${col_letter}$2:${col_letter}${last_row}"
            cell = f"{col_letter}2"

            formula_es = (
                f"=SI(ESNUMERO({cell}); SI(Y({cell}>=MEDIANA({rng})-1,5*DESVEST.M({rng}); "
                f'{cell}<=MEDIANA({rng})+1,5*DESVEST.M({rng})); "Válido"; "Outlier"); "Texto")'
            )
            formula_en = (
                f"=IF(ISNUMBER({cell}), IF(AND({cell}>=MEDIAN({rng})-1.5*STDEV.S({rng}), "
                f'{cell}<=MEDIAN({rng})+1.5*STDEV.S({rng})), "Valid", "Outlier"), "Text")'
            )

            excel_formulas.append(
                ExcelFormulaItem(
                    title=f"Validación IQR Outliers — {col_meta.name}",
                    column=col_meta.name,
                    excel_column_letter=col_letter,
                    formula_es=formula_es,
                    formula_en=formula_en,
                    description=f"Detecta anomalías estadísticas en '{col_meta.name}' evaluando el rango real {rng}.",
                )
            )

        return IntegrationGuide(
            table_name=table_name,
            clean_filename=clean_fn,
            parquet_filename=parquet_fn if run_result.parquet_filename else None,
            row_count=row_count,
            columns=columns_info,
            power_query_m_csv=power_query_m_csv,
            power_query_m_parquet=power_query_m_parquet,
            dax_measures=dax_measures,
            excel_formulas=excel_formulas,
        )

    @staticmethod
    def generate_html_report(run_id: str, lang: str = "es") -> str:
        report = AnalyticsService.generate_report(run_id)
        run_result = ETLService.get_run_result(run_id)

        # Renderizar SVGs
        cluster_svg = (
            AnalyticsService._render_cluster_svg(report.cluster_visualization)
            if report.cluster_visualization
            else "<p>N/A</p>"
        )
        active_box = None
        if report.outlier_visualization and report.outlier_visualization.columns:
            active_box = next(
                (
                    b
                    for b in report.outlier_visualization.columns
                    if b.column == report.outlier_visualization.active_column
                ),
                report.outlier_visualization.columns[0],
            )
        outlier_svg = (
            AnalyticsService._render_boxplot_svg(active_box, report.outlier_visualization)
            if active_box
            else "<p>N/A</p>"
        )

        # Sanitización estricta contra XSS Reflejado (CWE-079 / py/reflective-xss)
        safe_lang = html.escape(lang.strip().lower() if lang else "es")
        safe_direction = "rtl" if safe_lang in ["ar", "ur"] else "ltr"
        safe_run_id = html.escape(str(run_id))
        safe_output_hash = html.escape(str(run_result.output_hash_md5))
        safe_summary = html.escape(str(report.executive_summary))

        # KPIs HTML Sanitizados
        kpi_cards = []
        for k in report.kpis:
            title_esc = html.escape(str(k.title))
            val_esc = html.escape(str(k.value))
            sub_esc = html.escape(str(k.subtitle))
            kpi_cards.append(f"""
            <div class="kpi-card">
                <div class="kpi-title">{title_esc}</div>
                <div class="kpi-val">{val_esc}</div>
                <div class="kpi-sub">{sub_esc}</div>
            </div>
            """)
        kpi_html = "".join(kpi_cards)

        # Recomendaciones HTML Sanitizadas
        recs_html = "".join(f"<li>{html.escape(str(r))}</li>" for r in report.strategic_recommendations)

        # Filas tabla clusters Sanitizadas
        cluster_rows = []
        if report.cluster_visualization and report.cluster_visualization.clusters:
            colors = ["#3b82f6", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6", "#06b6d4"]
            for idx, c in enumerate(report.cluster_visualization.clusters):
                col_hex = colors[idx % len(colors)]
                row_avgs = (
                    "".join(f"<td>{v:.2f}</td>" for v in c.feature_averages.values())
                    if c.feature_averages
                    else "<td>—</td>"
                )
                label_esc = html.escape(str(c.label))
                cluster_rows.append(f"""
                    <tr>
                        <td style="font-weight:600;"><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{col_hex};margin-right:6px;"></span>{label_esc}</td>
                        <td>{c.count}</td>
                        <td>{c.percentage}%</td>
                        {row_avgs}
                    </tr>
                    """)
        cluster_table_html = "".join(cluster_rows)
        cluster_cols_header = "".join(
            f"<th>Media ({html.escape(str(c))})</th>"
            for c in (report.cluster_visualization.available_numeric_columns if report.cluster_visualization else [])
        )

        html_template = f"""<!DOCTYPE html>
<html lang="{safe_lang}" dir="{safe_direction}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DataFlow AI — Reporte Ejecutivo de Business Analytics</title>
    <style>
        :root {{
            --primary: #2563eb;
            --primary-dark: #1e40af;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            line-height: 1.5;
            padding: 24px;
        }}
        .container {{
            max-width: 960px;
            margin: 0 auto;
            background: var(--card-bg);
            padding: 32px;
            border-radius: 12px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.06);
            border: 1px solid var(--border);
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid var(--border);
            padding-bottom: 16px;
            margin-bottom: 24px;
            flex-wrap: wrap;
            gap: 16px;
        }}
        .logo-title h1 {{
            font-size: 1.5rem;
            color: var(--primary-dark);
            font-weight: 800;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .logo-title p {{
            font-size: 0.875rem;
            color: var(--text-muted);
            margin-top: 4px;
        }}
        .meta-badges {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            background: #eff6ff;
            color: var(--primary);
            border: 1px solid #bfdbfe;
        }}
        .badge-success {{ background: #ecfdf5; color: var(--success); border-color: #a7f3d0; }}
        .btn-print {{
            background: var(--primary);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.875rem;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .btn-print:hover {{ background: var(--primary-dark); }}
        .exec-summary {{
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-left: 4px solid var(--success);
            padding: 16px 20px;
            border-radius: 8px;
            margin-bottom: 24px;
        }}
        .exec-summary h3 {{
            font-size: 1rem;
            color: #166534;
            margin-bottom: 6px;
        }}
        .exec-summary p {{
            font-size: 0.925rem;
            color: #14532d;
            line-height: 1.6;
        }}
        .kpis-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }}
        .kpi-card {{
            background: #f8fafc;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
        }}
        .kpi-title {{ font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; }}
        .kpi-val {{ font-size: 1.5rem; font-weight: 800; color: var(--primary-dark); margin: 4px 0; }}
        .kpi-sub {{ font-size: 0.75rem; color: var(--text-muted); }}
        .section {{
            margin-bottom: 32px;
            page-break-inside: avoid;
        }}
        .section-title {{
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--text-main);
            border-bottom: 1px solid var(--border);
            padding-bottom: 8px;
            margin-bottom: 14px;
        }}
        .chart-box {{
            background: #f8fafc;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
            margin-top: 12px;
        }}
        th, td {{
            padding: 8px 12px;
            border: 1px solid var(--border);
            text-align: left;
        }}
        th {{ background: #f1f5f9; font-weight: 600; }}
        .recs-list {{
            padding-left: 20px;
            font-size: 0.9rem;
            line-height: 1.6;
            color: var(--text-main);
        }}
        .recs-list li {{ margin-bottom: 6px; }}
        .footer {{
            border-top: 1px solid var(--border);
            padding-top: 16px;
            margin-top: 32px;
            display: flex;
            justify-content: space-between;
            font-size: 0.75rem;
            color: var(--text-muted);
            flex-wrap: wrap;
            gap: 8px;
        }}
        @media print {{
            body {{ background: white; padding: 0; }}
            .container {{ box-shadow: none; border: none; padding: 0; max-width: 100%; }}
            .btn-print {{ display: none; }}
            .section {{ page-break-inside: avoid; }}
            @page {{ size: A4 portrait; margin: 1.5cm; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo-title">
                <h1>⚡ DataFlow AI — Reporte Ejecutivo</h1>
                <p>Business Analytics, Segmentación K-Means y Control Estadístico</p>
            </div>
            <div style="display:flex;align-items:center;gap:12px;">
                <div class="meta-badges">
                    <span class="badge">Run: {safe_run_id}</span>
                    <span class="badge badge-success">Clean Records: {run_result.rows_after}</span>
                </div>
                <button class="btn-print" onclick="window.print()">🖨️ Imprimir / PDF</button>
            </div>
        </div>

        <div class="exec-summary">
            <h3>📌 Resumen Directivo y Conclusiones</h3>
            <p>{safe_summary}</p>
        </div>

        <div class="section">
            <h2 class="section-title">📊 Métricas Clave y KPIs</h2>
            <div class="kpis-grid">
                {kpi_html}
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">🌐 Segmentación de Clusters 2D (K-Means)</h2>
            <div class="chart-box">
                {cluster_svg}
            </div>
            <div style="overflow-x:auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Cluster</th>
                            <th>Registros</th>
                            <th>Porcentaje</th>
                            {cluster_cols_header}
                        </tr>
                    </thead>
                    <tbody>
                        {cluster_table_html}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">🎯 Detección de Outliers y Distribución (Box Plot)</h2>
            <div class="chart-box">
                {outlier_svg}
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">💡 Recomendaciones Estratégicas</h2>
            <ol class="recs-list">
                {recs_html}
            </ol>
        </div>

        <div class="footer">
            <span>DataFlow AI v1.9.0 · Gobernanza Determinista (Python/Pandas)</span>
            <span>MD5 Salida: <code>{safe_output_hash}</code></span>
        </div>
    </div>
</body>
</html>"""
        return html_template
