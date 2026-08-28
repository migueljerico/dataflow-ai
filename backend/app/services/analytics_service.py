from typing import Dict, List

import numpy as np
import pandas as pd

from app.core.config import settings
from app.core.exceptions import FunctionalException
from app.models.analytics import BusinessKPI, CategoryDistribution, ExecutiveAnalyticsReport
from app.services.etl_service import ETLService

ANALYTICS_CACHE: Dict[str, ExecutiveAnalyticsReport] = {}


class AnalyticsService:
    @staticmethod
    def generate_report(run_id: str) -> ExecutiveAnalyticsReport:
        if run_id in ANALYTICS_CACHE:
            return ANALYTICS_CACHE[run_id]

        run_result = ETLService.get_run_result(run_id)
        candidates = [
            settings.UPLOAD_DIR / f"{run_id}_{run_result.clean_filename}",
            settings.UPLOAD_DIR / run_result.clean_filename,
        ]
        clean_filepath = next((p for p in candidates if p.exists()), None)

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

        report = ExecutiveAnalyticsReport(
            run_id=run_id,
            dataset_name=run_result.clean_filename,
            domain=domain,
            kpis=kpis,
            executive_summary=executive_summary,
            strategic_recommendations=recommendations,
            category_breakdown=breakdown,
        )

        ANALYTICS_CACHE[run_id] = report
        return report
