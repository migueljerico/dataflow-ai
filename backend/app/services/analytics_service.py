from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from app.core.exceptions import FunctionalException
from app.core.storage import get_storage
from app.models.analytics import (
    BoxPlotData,
    BusinessKPI,
    CategoryDistribution,
    ClusterPoint,
    ClusterSummaryItem,
    ClusterVisualization,
    ExecutiveAnalyticsReport,
    OutlierScatterPoint,
    OutlierVisualization,
)
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
        outlier_viz = AnalyticsService._build_outlier_visualization(df)

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
    def _build_outlier_visualization(df: pd.DataFrame) -> Optional[OutlierVisualization]:
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
        flag_col = f"{active_col}_is_outlier"

        for idx, row in sample_df.iterrows():
            y_val = pd.to_numeric(pd.Series([row[active_col]]), errors="coerce").iloc[0]
            if pd.isna(y_val):
                continue
            is_out = bool(y_val < active_box.lower_whisker or y_val > active_box.upper_whisker)
            if flag_col in row and bool(row[flag_col]):
                is_out = True

            lbl = str(row[label_col]) if label_col and pd.notna(row[label_col]) else f"Fila #{int(idx) + 1}"
            scatter_points.append(
                OutlierScatterPoint(
                    row_index=int(idx),
                    x_value=float(idx) + 1.0,
                    y_value=round(float(y_val), 2),
                    is_outlier=is_out,
                    label=lbl,
                )
            )

        return OutlierVisualization(
            columns=boxplots,
            active_column=active_col,
            scatter_points=scatter_points,
            total_outliers_detected=total_outliers,
            detection_method="IQR (1.5x) / Z-Score (>3.0)",
        )
