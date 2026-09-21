"""
Motor de recomendación de visualizaciones (reglas deterministas).

Combina el análisis semántico con los datos reales del modelo para proponer
visuales coherentes. Cada recomendación está justificada y su nivel de
confianza (high/medium/low) se calcula con una rúbrica objetiva y aditiva;
no hay números arbitrarios ni aleatoriedad.

Reglas clave:
- Bar/horizontal bar para comparación categórica.
- Line para evolución temporal.
- Pie/donut SOLO con una única composición, ≤6 categorías y sin comparación precisa.
- Horizontal bar descendente para ranking de los principales valores.
- Scatter para relación entre dos variables numéricas.
- Histogram para distribución de una medida continua.
- Gobernanza estricta de agregación: jamás SUM sobre precios unitarios o ratios.
- Control de redundancia: jamás duplicar la misma dimensión con el mismo objetivo analítico.
"""

import re
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

from app.models.dashboard import (
    AggregationSemanticRoleEnum,
    ColumnSemanticTypeEnum,
    ConfidenceLevelEnum,
    PreviewDataPoint,
    PreviewModeEnum,
    SemanticColumnAnalysis,
    SemanticModelAnalysis,
    TableSemanticRoleEnum,
    VisualRecommendation,
    VisualTypeEnum,
)
from app.models.workspace import MultiTableStarSchema

MAX_CATEGORIES_BAR = 30
MAX_PIE_CATEGORIES = 6
MAX_PREVIEW_POINTS = 12
HIGH_CONFIDENCE_MIN = 75
MEDIUM_CONFIDENCE_MIN = 50

# Columna sintética derivada (Ventas netas = Cantidad × Precio × (1 − Descuento)),
# creada de forma determinista sobre el dataframe limpio cuando el hecho tiene
# cantidad y precio. Su medida DAX de referencia vive en el esquema estrella.
DERIVED_MEASURE_COL = "__ventas_netas"


def _slug(text: str) -> str:
    value = re.sub(r"[^\w]+", "_", text.lower()).strip("_")
    return value or "visual"


def _confidence_level(score: int) -> ConfidenceLevelEnum:
    if score >= HIGH_CONFIDENCE_MIN:
        return ConfidenceLevelEnum.HIGH
    if score >= MEDIUM_CONFIDENCE_MIN:
        return ConfidenceLevelEnum.MEDIUM
    return ConfidenceLevelEnum.LOW


def _natural_dimension_name(col_name: str) -> str:
    """Traduce nombres técnicos de columnas a denominaciones naturales ejecutivas en español."""
    translations = {
        "shipcountry": "País de Envío",
        "ship_country": "País de Envío",
        "country": "País",
        "pais": "País",
        "city": "Ciudad",
        "ciudad": "Ciudad",
        "shipcity": "Ciudad de Envío",
        "ship_city": "Ciudad de Envío",
        "customername": "Cliente",
        "customer_name": "Cliente",
        "companyname": "Empresa",
        "company_name": "Empresa",
        "contactname": "Contacto",
        "productname": "Producto",
        "product_name": "Producto",
        "categoryname": "Categoría",
        "category_name": "Categoría",
        "category": "Categoría",
        "subcategory": "Subcategoría",
        "suppliername": "Proveedor",
        "supplier_name": "Proveedor",
        "orderdate": "Fecha de Pedido",
        "order_date": "Fecha de Pedido",
        "shippeddate": "Fecha de Envío",
        "shipped_date": "Fecha de Envío",
        "status": "Estado",
        "orderstatus": "Estado del Pedido",
    }
    key = col_name.lower().replace(" ", "").replace("_", "")
    if key in translations:
        return translations[key]
    return col_name.replace("_", " ")


class RedundancyController:
    """Controla y previene la redundancia dimensional y analítica en las recomendaciones de visuales."""

    def __init__(self) -> None:
        self._visuals_by_dim_and_goal: Dict[Tuple[str, str], VisualRecommendation] = {}
        self._used_dimensions: Dict[str, Set[str]] = {
            "comparación": set(),
            "composición": set(),
            "ranking": set(),
            "evolución temporal": set(),
            "relación": set(),
            "distribución": set(),
        }
        self._all_dimensions_used: Set[str] = set()

    def can_add(
        self,
        dimension: Optional[str],
        goal: str,
        visual_type: VisualTypeEnum,
        category_count: Optional[int] = None,
    ) -> bool:
        if not dimension:
            return True

        # 1) Misma dimensión + mismo objetivo analítico -> Prohibido
        if (dimension, goal) in self._visuals_by_dim_and_goal:
            return False

        # 2) Donut:
        if visual_type in (VisualTypeEnum.DONUT, VisualTypeEnum.PIE):
            # Prohibido si la dimensión ya se utilizó para comparación en barras
            if dimension in self._used_dimensions["comparación"]:
                return False
            # Prohibido si no tiene entre 2 y 6 categorías
            if category_count is not None and not (2 <= category_count <= 6):
                return False

        return True

    def register(self, visual: VisualRecommendation) -> None:
        dim = visual.dimension or ""
        goal = visual.analytical_goal or "general"
        if dim:
            self._visuals_by_dim_and_goal[(dim, goal)] = visual
            if goal in self._used_dimensions:
                self._used_dimensions[goal].add(dim)
            self._all_dimensions_used.add(dim)

    def is_dimension_used(self, dimension: str) -> bool:
        return dimension in self._all_dimensions_used


class VisualRecommendationEngine:
    """Motor determinista de recomendación de visuales sobre un modelo estrella."""

    def __init__(
        self,
        analysis: SemanticModelAnalysis,
        schema: MultiTableStarSchema,
        dataframes: Dict[str, pd.DataFrame],
    ):
        self.analysis = analysis
        self.schema = schema
        self.dataframes = dataframes
        self.fact_name = schema.fact_table.table_name
        self.fact_df = dataframes.get(self.fact_name, pd.DataFrame())
        self._ensure_derived_measures()
        self._column_index = self._build_column_index()
        self.primary_measure = self._select_primary_measure()

    def _ensure_derived_measures(self) -> None:
        """Calcula de forma determinista la columna sintética de ventas netas si existen cantidad y precio."""
        if self.fact_df.empty:
            return
        cols = {str(c).lower(): str(c) for c in self.fact_df.columns}
        qty_col = next((cols[k] for k in ("quantity", "cantidad", "qty", "unidades", "units") if k in cols), None)
        price_col = next((cols[k] for k in ("unitprice", "precio", "unit_price", "price") if k in cols), None)
        disc_col = next((cols[k] for k in ("discount", "descuento", "disc") if k in cols), None)

        if qty_col and price_col and DERIVED_MEASURE_COL not in self.fact_df.columns:
            qty = pd.to_numeric(self.fact_df[qty_col], errors="coerce").fillna(0)
            price = pd.to_numeric(self.fact_df[price_col], errors="coerce").fillna(0)
            disc = pd.to_numeric(self.fact_df[disc_col], errors="coerce").fillna(0) if disc_col else 0
            self.fact_df[DERIVED_MEASURE_COL] = qty * price * (1.0 - disc)

    # ─────────────────────── utilidades de índice ───────────────────────────

    def _build_column_index(self) -> Dict[str, Dict[str, object]]:
        """Índice plano 'Tabla[Columna]' → análisis semántico."""
        index: Dict[str, Dict[str, object]] = {}
        for table in self.analysis.tables:
            for col in table.columns:
                index[f"{table.table_name}[{col.column_name}]"] = {
                    "table": table.table_name,
                    "column": col.column_name,
                    "analysis": col,
                    "semantic_role": table.semantic_role,
                }
        if DERIVED_MEASURE_COL in self.fact_df.columns:
            analysis_col = SemanticColumnAnalysis(
                table_name=self.fact_name,
                column_name=DERIVED_MEASURE_COL,
                semantic_type=ColumnSemanticTypeEnum.CURRENCY,
                data_type="float64",
                cardinality=int(self.fact_df[DERIVED_MEASURE_COL].nunique()),
                null_percentage=0.0,
                completeness_pct=100.0,
                inferred_from="derived: quantity * price * (1 - discount)",
                is_heuristic=False,
                aggregation_role=AggregationSemanticRoleEnum.ADDITIVE_AMOUNT,
            )
            index[f"{self.fact_name}[{DERIVED_MEASURE_COL}]"] = {
                "table": self.fact_name,
                "column": DERIVED_MEASURE_COL,
                "analysis": analysis_col,
                "semantic_role": TableSemanticRoleEnum.FACT,
            }
        return index

    def columns_of_type(self, semantic_type: ColumnSemanticTypeEnum) -> List[Dict[str, object]]:
        return [v for v in self._column_index.values() if v["analysis"].semantic_type == semantic_type]

    def _completeness(self, table: str, column: str) -> float:
        entry = self._column_index.get(f"{table}[{column}]")
        if entry:
            return float(entry["analysis"].completeness_pct)
        df = self.dataframes.get(table, pd.DataFrame())
        if column in df.columns and len(df) > 0:
            return round(100.0 * df[column].notna().mean(), 2)
        return 0.0

    # ─────────────────────── selección de medida ────────────────────────────

    def _select_primary_measure(self) -> Optional[Dict[str, object]]:
        """Elige la medida principal con estricta gobernanza semántica de agregación."""
        derived_key = f"{self.fact_name}[{DERIVED_MEASURE_COL}]"
        if derived_key in self._column_index:
            entry = self._column_index[derived_key]
            dax_measures = self.schema.suggested_dax_measures
            dax_name = "Ventas_Netas"
            sources = self._derived_source_columns()
            if len(sources) >= 2:
                q, p = sources[0], sources[1]
                d = sources[2] if len(sources) > 2 else None
                default_formula = f"SUMX('{self.fact_name}', '{self.fact_name}'[{q}] * '{self.fact_name}'[{p}]"
                if d:
                    default_formula += f" * (1 - '{self.fact_name}'[{d}])"
                default_formula += ")"
            else:
                default_formula = f"SUM('{self.fact_name}'[{DERIVED_MEASURE_COL}])"
            dax_formula = dax_measures.get(dax_name, default_formula)
            return {
                "table": self.fact_name,
                "column": DERIVED_MEASURE_COL,
                "analysis": entry["analysis"],
                "label": "Ventas netas",
                "derived": True,
                "dax_name": dax_name,
                "dax_formula": dax_formula,
                "source_columns": sources,
                "aggregation_role": AggregationSemanticRoleEnum.ADDITIVE_AMOUNT,
                "aggregation_func": "sum",
            }

        # Si no hay ventas netas derivadas, buscar candidatos numéricos en la tabla de hechos
        for preferred in (
            ColumnSemanticTypeEnum.CURRENCY,
            ColumnSemanticTypeEnum.QUANTITY,
            ColumnSemanticTypeEnum.MEASURE,
        ):
            candidates = [c for c in self.columns_of_type(preferred) if c["table"] == self.fact_name]
            if candidates:
                # Preferir medidas aditivas sobre unitarias/ratios
                candidates.sort(
                    key=lambda c: (
                        (
                            1
                            if getattr(c["analysis"], "aggregation_role", None)
                            in (
                                AggregationSemanticRoleEnum.UNIT_PRICE_OR_RATE,
                                AggregationSemanticRoleEnum.RATIO_OR_PERCENTAGE,
                            )
                            else 0
                        ),
                        -float(c["analysis"].completeness_pct),
                        -int(c["analysis"].cardinality),
                        str(c["column"]),
                    )
                )
                best = candidates[0]
                role = getattr(best["analysis"], "aggregation_role", AggregationSemanticRoleEnum.ADDITIVE_AMOUNT)
                is_unit = role in (
                    AggregationSemanticRoleEnum.UNIT_PRICE_OR_RATE,
                    AggregationSemanticRoleEnum.RATIO_OR_PERCENTAGE,
                )
                agg_func = "mean" if is_unit else "sum"
                label = self._measure_label(best, is_unit=is_unit)
                col_name = str(best["column"])
                dax_op = "AVERAGE" if is_unit else "SUM"
                is_price = any(k in col_name.lower() for k in ("price", "precio", "rate", "tarifa"))
                dax_name = f"{'Precio_Medio' if is_price else 'Promedio' if is_unit else 'Total'}_{col_name}"
                dax_formula = f"{dax_op}('{best['table']}'[{col_name}])"
                return {
                    "table": str(best["table"]),
                    "column": col_name,
                    "analysis": best["analysis"],
                    "label": label,
                    "derived": False,
                    "aggregation_role": role,
                    "aggregation_func": agg_func,
                    "dax_name": dax_name,
                    "dax_formula": dax_formula,
                }
        return None

    def _derived_source_columns(self) -> List[str]:
        """Columnas reales del hecho que alimentan la medida derivada de ventas."""
        cols = {str(c).lower(): str(c) for c in self.fact_df.columns}
        qty = next((cols[k] for k in ("quantity", "cantidad", "qty", "unidades", "units") if k in cols), None)
        price = next((cols[k] for k in ("unitprice", "precio", "unit_price", "price") if k in cols), None)
        disc = next((cols[k] for k in ("discount", "descuento", "disc") if k in cols), None)
        return [c for c in (qty, price, disc) if c]

    def _measure_reference(self) -> Optional[str]:
        """Referencia de la medida principal: [MedidaDAX] si es derivada, o columna cualificada."""
        if self.primary_measure is None:
            return None
        if self.primary_measure.get("derived"):
            return f"[{self.primary_measure['dax_name']}]"
        return f"{self.primary_measure['table']}[{self.primary_measure['column']}]"

    def _measure_dax_formula(self) -> Optional[str]:
        """Fórmula DAX de la medida principal para la ficha técnica del visual."""
        if self.primary_measure is None:
            return None
        return str(self.primary_measure.get("dax_formula") or f"[{self.primary_measure.get('dax_name', '')}]")

    def _measure_fields(self) -> List[str]:
        """Campos reales del modelo que respaldan la medida principal (nunca columnas sintéticas)."""
        if self.primary_measure is None:
            return []
        if self.primary_measure.get("derived"):
            return [f"{self.fact_name}[{c}]" for c in self.primary_measure.get("source_columns", [])]
        return [f"{self.primary_measure['table']}[{self.primary_measure['column']}]"]

    @staticmethod
    def _measure_label(entry: Dict[str, object], is_unit: bool = False) -> str:
        column = str(entry["column"])
        role = getattr(entry.get("analysis"), "aggregation_role", None)
        if is_unit or role == AggregationSemanticRoleEnum.UNIT_PRICE_OR_RATE:
            if any(k in column.lower() for k in ("unitprice", "precio", "unit_price", "price")):
                return "Precio unitario medio"
            return f"{column.replace('_', ' ')} medio"
        if role == AggregationSemanticRoleEnum.RATIO_OR_PERCENTAGE:
            return f"{column.replace('_', ' ')} medio"
        semantic_type = getattr(entry.get("analysis"), "semantic_type", None)
        if semantic_type == ColumnSemanticTypeEnum.CURRENCY:
            return (
                "Ingresos"
                if any(k in column.lower() for k in ("revenue", "ingreso", "venta"))
                else column.replace("_", " ")
            )
        return column.replace("_", " ")

    # ─────────────────────── preparación de datos ───────────────────────────

    def _relations_to(self, table_name: str):
        return [r for r in self.schema.relationships if r.to_table == table_name]

    def _merge_with_dim(self, dim_table: str, dim_column: str) -> Optional[pd.DataFrame]:
        """Une la tabla de hechos con una dimensión y devuelve [dim_column, medida_principal]."""
        if self.primary_measure is None:
            return None
        measure_col = str(self.primary_measure["column"])
        if measure_col not in self.fact_df.columns:
            return None
        if dim_table == self.fact_name:
            if dim_column not in self.fact_df.columns:
                return None
            return self.fact_df[[dim_column, measure_col]].copy()
        relations = self._relations_to(dim_table)
        dim_df = self.dataframes.get(dim_table, pd.DataFrame())
        if not relations or dim_df.empty or dim_column not in dim_df.columns:
            return None
        rel = relations[0]
        if rel.from_column not in self.fact_df.columns or rel.to_column not in dim_df.columns:
            return None
        fact_part = self.fact_df[[rel.from_column, measure_col]]
        dim_part = dim_df[[rel.to_column, dim_column]].drop_duplicates()
        merged = fact_part.merge(dim_part, left_on=rel.from_column, right_on=rel.to_column, how="left")
        return merged[[dim_column, measure_col]]

    def _aggregate_by(
        self,
        dim_table: str,
        dim_column: str,
        top_n: int = 8,
        sort_desc: bool = True,
    ) -> Tuple[List[PreviewDataPoint], int]:
        """Agrega la medida principal por una dimensión respetando la función agregadora gobernada."""
        frame = self._merge_with_dim(dim_table, dim_column)
        if frame is None or self.primary_measure is None:
            return [], 0
        measure_col = str(self.primary_measure["column"])
        numeric_frame = frame.copy()
        numeric_frame[measure_col] = pd.to_numeric(numeric_frame[measure_col], errors="coerce")
        agg_func = self.primary_measure.get("aggregation_func", "sum")
        if agg_func == "mean":
            grouped = (
                numeric_frame.dropna(subset=[dim_column])
                .groupby(dim_column)[measure_col]
                .mean()
                .sort_values(ascending=not sort_desc)
            )
        else:
            grouped = (
                numeric_frame.dropna(subset=[dim_column])
                .groupby(dim_column)[measure_col]
                .sum()
                .sort_values(ascending=not sort_desc)
            )
        total_cardinality = int(grouped.shape[0])
        points = [
            PreviewDataPoint(label=str(label)[:24], value=round(float(value), 2))
            for label, value in grouped.head(top_n).items()
        ]
        return points, total_cardinality

    # ─────────────────────── rúbrica de confianza ───────────────────────────

    def _score(
        self,
        base: int,
        dimension_entry: Optional[Dict[str, object]],
        extra: Optional[List[Tuple[int, str]]] = None,
    ) -> Tuple[int, ConfidenceLevelEnum, str]:
        parts: List[str] = [f"base del tipo de visual: {base}"]
        score = base
        if dimension_entry is not None:
            analysis = dimension_entry["analysis"]
            if not analysis.is_heuristic:
                score += 15
                parts.append("+15 evidencia semántica sólida de la dimensión")
            else:
                score -= 10
                parts.append("-10 clasificación heurística de la dimensión")
            completeness = float(analysis.completeness_pct)
            if completeness >= 90:
                score += 10
                parts.append("+10 completitud ≥ 90%")
            elif completeness < 70:
                score -= 20
                parts.append("-20 completitud < 70%")
        if self.primary_measure is not None:
            score += 10
            parts.append("+10 medida principal validada disponible")
        else:
            score -= 25
            parts.append("-25 sin medida principal validada")
        for delta, why in extra or []:
            score += delta
            parts.append(f"{delta:+d} {why}")
        score = max(0, min(100, score))
        return score, _confidence_level(score), " · ".join(parts)

    def _dq_notes(self, fields: List[Tuple[str, str]]) -> List[str]:
        notes: List[str] = []
        for table, column in fields:
            completeness = self._completeness(table, column)
            if completeness < 85.0:
                notes.append(
                    f"⚠ {table}[{column}] tiene completitud del {completeness:.1f}%: la visualización es válida "
                    "pero existen valores nulos en esta dimensión."
                )
        return notes

    # ─────────────────────── reglas individuales ────────────────────────────

    def _time_series_candidate(self) -> Optional[Dict[str, object]]:
        """Busca una columna temporal en el hecho o en una dimensión fecha unida."""
        for entry in self.columns_of_type(ColumnSemanticTypeEnum.DATE) + self.columns_of_type(
            ColumnSemanticTypeEnum.DATETIME
        ):
            table = str(entry["table"])
            column = str(entry["column"])
            df = self.dataframes.get(table, pd.DataFrame())
            if df.empty or column not in df.columns:
                continue
            series = pd.to_datetime(df[column], errors="coerce", dayfirst=False)
            valid = series.dropna()
            if len(valid) < max(10, int(len(df) * 0.5)) or valid.nunique() < 3:
                continue
            joinable = table == self.fact_name or bool(self._relations_to(table))
            if not joinable:
                continue
            return {"table": table, "column": column, "entry": entry, "series": series}
        return None

    def _line_visual(self, redundancy: RedundancyController) -> Optional[VisualRecommendation]:
        if self.primary_measure is None:
            return None
        candidate = self._time_series_candidate()
        if candidate is None:
            return None
        table = str(candidate["table"])
        column = str(candidate["column"])
        measure_col = str(self.primary_measure["column"])
        dim_df = self.dataframes.get(table, pd.DataFrame())

        if table == self.fact_name:
            base = pd.DataFrame({"__fecha": candidate["series"].values, measure_col: self.fact_df[measure_col].values})
        else:
            relations = self._relations_to(table)
            if not relations:
                return None
            rel = relations[0]
            if (
                rel.from_column not in self.fact_df.columns
                or rel.to_column not in dim_df.columns
                or column not in dim_df.columns
            ):
                return None
            fact_part = self.fact_df[[rel.from_column, measure_col]]
            dim_part = dim_df[[rel.to_column, column]].drop_duplicates()
            merged = fact_part.merge(dim_part, left_on=rel.from_column, right_on=rel.to_column, how="left")
            base = pd.DataFrame({"__fecha": merged[column].values, measure_col: merged[measure_col].values})

        base["__fecha"] = pd.to_datetime(base["__fecha"], errors="coerce")
        base = base.dropna(subset=["__fecha"])
        if base.empty:
            return None
        base[measure_col] = pd.to_numeric(base[measure_col], errors="coerce")
        granularity = "M" if base["__fecha"].nunique() > 60 else "D"
        if granularity == "M":
            base["__periodo"] = base["__fecha"].dt.to_period("M").astype(str)
        else:
            base["__periodo"] = base["__fecha"].dt.strftime("%Y-%m-%d")

        agg_func = self.primary_measure.get("aggregation_func", "sum")
        if agg_func == "mean":
            grouped = base.groupby("__periodo")[measure_col].mean().sort_index()
        else:
            grouped = base.groupby("__periodo")[measure_col].sum().sort_index()

        if len(grouped) < 3:
            return None
        points = [
            PreviewDataPoint(label=str(label), value=round(float(value), 2))
            for label, value in grouped.tail(MAX_PREVIEW_POINTS).items()
        ]
        extra = [(10, "cardinalidad temporal adecuada")] if len(grouped) >= 6 else [(-10, "pocos puntos temporales")]
        score, level, rationale = self._score(55, candidate["entry"], extra)
        measure_ref = self._measure_reference()
        measure_label = str(self.primary_measure["label"])
        dim_ref = f"{table}[{column}]"

        if not redundancy.can_add(dim_ref, "evolución temporal", VisualTypeEnum.LINE):
            return None

        visual = VisualRecommendation(
            visual_id=f"vis_line_{_slug(column)}",
            title=f"Evolución de {measure_label} por {'mes' if granularity == 'M' else 'día'}",
            visual_type=VisualTypeEnum.LINE,
            page_id="page_overview",
            dimension=dim_ref,
            measure=measure_ref,
            measure_name=measure_label,
            fields=[dim_ref] + self._measure_fields(),
            axis_label=dim_ref,
            legend_field=None,
            filter_suggestion=f"{dim_ref} (año)",
            reason="La evolución temporal de la medida principal debe leerse como tendencia continua; el gráfico de líneas preserva el orden cronológico y facilita detectar patrones estacionales.",
            confidence=level,
            confidence_rationale=rationale,
            alternative_types=[VisualTypeEnum.AREA],
            preview_data=points,
            preview_mode=PreviewModeEnum.REAL,
            data_quality_notes=self._dq_notes([(table, column)]),
            accessibility_note="Incluir valores numéricos en el tooltip y no codificar la tendencia solo con color.",
            order=0,
            business_question="¿Cómo evoluciona la métrica en el tiempo y cuál es su tendencia?",
            analytical_goal="evolución temporal",
            measure_dax=self._measure_dax_formula(),
            priority=1,
        )
        redundancy.register(visual)
        return visual

    def _category_visuals(self, redundancy: RedundancyController) -> List[VisualRecommendation]:
        visuals: List[VisualRecommendation] = []
        if self.primary_measure is None:
            return visuals
        category_entries = (
            self.columns_of_type(ColumnSemanticTypeEnum.CATEGORY)
            + self.columns_of_type(ColumnSemanticTypeEnum.SUBCATEGORY)
            + self.columns_of_type(ColumnSemanticTypeEnum.GEOGRAPHY)
        )

        # Ordenar por completitud descendente y cardinalidad moderada
        sorted_entries = sorted(
            category_entries,
            key=lambda e: (
                -float(e["analysis"].completeness_pct),
                abs(int(e["analysis"].cardinality) - 8),
                str(e["table"]),
                str(e["column"]),
            ),
        )

        for entry in sorted_entries:
            table = str(entry["table"])
            column = str(entry["column"])
            dim_key = f"{table}[{column}]"
            if (
                column.lower() in ("id",)
                or str(entry["analysis"].semantic_type) == ColumnSemanticTypeEnum.IDENTIFIER.value
            ):
                continue
            joinable = table == self.fact_name or bool(self._relations_to(table))
            if not joinable:
                continue

            points, total_cardinality = self._aggregate_by(table, column, top_n=8)
            if total_cardinality < 2 or not points or total_cardinality > MAX_CATEGORIES_BAR:
                continue

            longest_label = max(len(p.label) for p in points)
            use_horizontal = longest_label > 18 or total_cardinality > 12
            visual_type = VisualTypeEnum.HORIZONTAL_BAR if use_horizontal else VisualTypeEnum.BAR

            if not redundancy.can_add(dim_key, "comparación", visual_type, total_cardinality):
                continue

            dim_display_name = _natural_dimension_name(column)
            title = f"{self.primary_measure['label']} por {dim_display_name}"

            cardinality_bonus = 10 if 3 <= total_cardinality <= 15 else (-5 if total_cardinality > 20 else 0)
            score, level, rationale = self._score(
                50, entry, [(cardinality_bonus, f"cardinalidad {total_cardinality} adecuada para comparación")]
            )
            reason = (
                f"Comparación directa de {self.primary_measure['label']} entre {total_cardinality} valores de "
                f"'{dim_display_name}'; el gráfico de barras permite leer con precisión el peso relativo de cada categoría."
            )
            alternatives = (
                [VisualTypeEnum.BAR, VisualTypeEnum.STACKED_BAR]
                if use_horizontal
                else [VisualTypeEnum.HORIZONTAL_BAR, VisualTypeEnum.STACKED_BAR]
            )

            visual = VisualRecommendation(
                visual_id=f"vis_bar_{_slug(table + '_' + column)}",
                title=title,
                visual_type=visual_type,
                page_id="page_overview",
                dimension=dim_key,
                measure=self._measure_reference(),
                measure_name=self.primary_measure["label"],
                fields=[dim_key] + self._measure_fields(),
                axis_label=dim_display_name,
                legend_field=None,
                filter_suggestion=dim_key,
                reason=reason,
                confidence=level,
                confidence_rationale=rationale,
                alternative_types=alternatives,
                preview_data=points,
                preview_mode=PreviewModeEnum.REAL,
                data_quality_notes=self._dq_notes([(table, column)]),
                accessibility_note="Etiquetar cada barra con su valor exacto para no depender solo de la longitud.",
                order=0,
                business_question=f"¿Cómo se distribuye {self.primary_measure['label'].lower()} entre los principales segmentos de {dim_display_name.lower()}?",
                analytical_goal="comparación",
                measure_dax=self._measure_dax_formula(),
                priority=2,
            )
            redundancy.register(visual)
            visuals.append(visual)
            if len(visuals) >= 3:
                break
        return visuals

    def _donut_visual(self, redundancy: RedundancyController) -> Optional[VisualRecommendation]:
        """Donut SOLO para composición única de 2..6 categorías, nunca geografía, ni dimensión ya usada."""
        if self.primary_measure is None:
            return None

        # Evaluar columnas categóricas puras (excluir expresamente geografía)
        candidates = self.columns_of_type(ColumnSemanticTypeEnum.CATEGORY) + self.columns_of_type(
            ColumnSemanticTypeEnum.SUBCATEGORY
        )
        for entry in candidates:
            if entry["analysis"].semantic_type == ColumnSemanticTypeEnum.GEOGRAPHY:
                continue
            table = str(entry["table"])
            column = str(entry["column"])
            dim_key = f"{table}[{column}]"

            # No reutilizar dimensión ya usada para comparación en barras
            if redundancy.is_dimension_used(dim_key):
                continue

            joinable = table == self.fact_name or bool(self._relations_to(table))
            if not joinable:
                continue

            points, total_cardinality = self._aggregate_by(table, column, top_n=MAX_PIE_CATEGORIES + 1)
            if not (2 <= total_cardinality <= MAX_PIE_CATEGORIES) or len(points) != total_cardinality:
                continue

            if not redundancy.can_add(dim_key, "composición", VisualTypeEnum.DONUT, total_cardinality):
                continue

            dim_display_name = _natural_dimension_name(column)
            score, level, rationale = self._score(40, None, [(10, f"composición única con {total_cardinality} partes")])

            visual = VisualRecommendation(
                visual_id=f"vis_donut_{_slug(column)}",
                title=f"Composición de {self.primary_measure['label']} por {dim_display_name}",
                visual_type=VisualTypeEnum.DONUT,
                page_id="page_overview",
                dimension=dim_key,
                measure=self._measure_reference(),
                measure_name=self.primary_measure["label"],
                fields=[dim_key] + self._measure_fields(),
                axis_label=None,
                legend_field=dim_key,
                filter_suggestion=None,
                reason=(
                    f"Única composición de un total con {total_cardinality} categorías; el donut comunica la parte "
                    "del total sin exigir comparación precisa entre categorías."
                ),
                confidence=level,
                confidence_rationale=rationale,
                alternative_types=[VisualTypeEnum.HORIZONTAL_BAR, VisualTypeEnum.PIE],
                preview_data=points,
                preview_mode=PreviewModeEnum.REAL,
                data_quality_notes=self._dq_notes([(table, column)]),
                accessibility_note="Añadir leyenda con porcentajes explícitos; nunca diferenciar solo por color.",
                order=0,
                business_question=f"¿Cuál es la proporción de {self.primary_measure['label'].lower()} por {dim_display_name.lower()}?",
                analytical_goal="composición",
                measure_dax=self._measure_dax_formula(),
                priority=4,
            )
            redundancy.register(visual)
            return visual
        return None

    def _ranking_visual(self, redundancy: RedundancyController) -> Optional[VisualRecommendation]:
        """Ranking de los principales valores en una dimensión de alta cardinalidad usando barras horizontales."""
        if self.primary_measure is None:
            return None

        candidates = (
            self.columns_of_type(ColumnSemanticTypeEnum.CATEGORY)
            + self.columns_of_type(ColumnSemanticTypeEnum.SUBCATEGORY)
            + self.columns_of_type(ColumnSemanticTypeEnum.GEOGRAPHY)
            + self.columns_of_type(ColumnSemanticTypeEnum.NAME)
        )

        valid_candidates = []
        for entry in candidates:
            table = str(entry["table"])
            column = str(entry["column"])
            dim_key = f"{table}[{column}]"
            if (
                column.lower() in ("id",)
                or str(entry["analysis"].semantic_type) == ColumnSemanticTypeEnum.IDENTIFIER.value
            ):
                continue
            joinable = table == self.fact_name or bool(self._relations_to(table))
            if not joinable:
                continue
            cardinality = int(entry["analysis"].cardinality)
            if cardinality < 2:
                continue
            is_used = redundancy.is_dimension_used(dim_key)
            valid_candidates.append((is_used, -cardinality, table, column, entry))

        if not valid_candidates:
            return None

        # Ordenar: primero no utilizadas, luego mayor cardinalidad
        valid_candidates.sort(key=lambda x: (x[0], x[1]))

        for _, _, dim_table, dim_column, _best_entry in valid_candidates:
            dim_key = f"{dim_table}[{dim_column}]"
            if not redundancy.can_add(dim_key, "ranking", VisualTypeEnum.HORIZONTAL_BAR):
                continue
            points, total_cardinality = self._aggregate_by(dim_table, dim_column, top_n=5, sort_desc=True)
            if not points:
                continue

            dim_display_name = _natural_dimension_name(dim_column)
            score, level, rationale = self._score(55, None, [(10, "ranking de detalle sobre dimensión relevante")])

            visual = VisualRecommendation(
                visual_id=f"vis_ranking_{_slug(dim_column)}",
                title=f"Top 5 {dim_display_name} por {self.primary_measure['label']}",
                visual_type=VisualTypeEnum.HORIZONTAL_BAR,
                page_id="page_detail",
                dimension=dim_key,
                measure=self._measure_reference(),
                measure_name=self.primary_measure["label"],
                fields=[dim_key] + self._measure_fields(),
                axis_label=dim_display_name,
                legend_field=None,
                filter_suggestion=dim_key,
                reason=f"El ranking en barra horizontal ordenada descendente destaca de inmediato los 5 {dim_display_name.lower()} con mayor volumen de negocio.",
                confidence=level,
                confidence_rationale=rationale,
                alternative_types=[VisualTypeEnum.TABLE],
                preview_data=points,
                preview_mode=PreviewModeEnum.REAL,
                data_quality_notes=self._dq_notes([(dim_table, dim_column)]),
                accessibility_note="Barra horizontal ordenada descendente con etiquetas de valor legibles.",
                order=0,
                business_question=f"¿Cuáles son los 5 principales {dim_display_name.lower()} con mayor volumen de {self.primary_measure['label'].lower()}?",
                analytical_goal="ranking",
                measure_dax=self._measure_dax_formula(),
                priority=3,
            )
            redundancy.register(visual)
            return visual

        return None

    def _scatter_visual(self, redundancy: RedundancyController) -> Optional[VisualRecommendation]:
        numeric_columns = [
            c
            for c in self.columns_of_type(ColumnSemanticTypeEnum.MEASURE)
            + self.columns_of_type(ColumnSemanticTypeEnum.CURRENCY)
            + self.columns_of_type(ColumnSemanticTypeEnum.QUANTITY)
            if c["table"] == self.fact_name and c["column"] != DERIVED_MEASURE_COL
        ]
        usable = [
            c
            for c in numeric_columns
            if int(c["analysis"].cardinality) >= 10 and float(c["analysis"].completeness_pct) >= 85
        ]
        if len(usable) < 2 or len(self.fact_df) < 30:
            return None
        usable.sort(key=lambda c: (str(c["column"])))
        x_entry, y_entry = usable[0], usable[1]
        x_col, y_col = str(x_entry["column"]), str(y_entry["column"])
        sample = self.fact_df[[x_col, y_col]].dropna()
        if len(sample) < 30:
            return None
        head = sample.head(100)
        x_values = head[x_col].tolist()
        y_values = head[y_col].tolist()
        points = [
            PreviewDataPoint(label=f"{i + 1}", value=round(float(x), 2), secondary_value=round(float(y), 2))
            for i, (x, y) in enumerate(zip(x_values, y_values, strict=True))
        ]
        score, level, rationale = self._score(
            45, None, [(10, "dos variables numéricas continuas con datos suficientes")]
        )
        dim_ref = f"{self.fact_name}[{x_col}]"
        measure_ref = f"{self.fact_name}[{y_col}]"

        visual = VisualRecommendation(
            visual_id="vis_scatter_primary",
            title=f"Relación entre {x_col.replace('_', ' ')} y {y_col.replace('_', ' ')}",
            visual_type=VisualTypeEnum.SCATTER,
            page_id="page_analysis",
            dimension=dim_ref,
            measure=measure_ref,
            measure_name=y_col.replace("_", " "),
            fields=[dim_ref, measure_ref],
            axis_label=x_col.replace("_", " "),
            legend_field=None,
            filter_suggestion=None,
            reason="Ambas variables son numéricas continuas; el diagrama de dispersión revela correlaciones y valores atípicos que una agregación ocultaría.",
            confidence=level,
            confidence_rationale=rationale,
            alternative_types=[VisualTypeEnum.TABLE],
            preview_data=points,
            preview_mode=PreviewModeEnum.REAL,
            data_quality_notes=self._dq_notes([(self.fact_name, x_col), (self.fact_name, y_col)]),
            accessibility_note="Complementar el scatter con la tabla de detalle accesible.",
            order=0,
            business_question=f"¿Existe correlación o patrones entre {x_col.replace('_', ' ')} y {y_col.replace('_', ' ')}?",
            analytical_goal="relación",
            measure_dax=f"{self.fact_name}[{y_col}]",
            priority=5,
        )
        redundancy.register(visual)
        return visual

    def _histogram_visual(self, redundancy: RedundancyController) -> Optional[VisualRecommendation]:
        if self.primary_measure is None:
            return None
        measure_col = str(self.primary_measure["column"])
        if str(self.primary_measure["table"]) != self.fact_name or measure_col not in self.fact_df.columns:
            return None
        series = pd.to_numeric(self.fact_df[measure_col], errors="coerce").dropna()
        if series.nunique() <= 30 or len(series) < 30:
            return None
        binned = pd.cut(series, bins=8)
        grouped = binned.value_counts().sort_index()
        points: List[PreviewDataPoint] = []
        for interval, count in grouped.items():
            points.append(
                PreviewDataPoint(
                    label=f"{round(float(interval.left), 1)}–{round(float(interval.right), 1)}",
                    value=int(count),
                )
            )
        if not points:
            return None
        score, level, rationale = self._score(45, None, [(10, "medida continua con distribución analizable")])
        measure_ref = self._measure_reference()
        measure_label = str(self.primary_measure["label"])

        visual = VisualRecommendation(
            visual_id=f"vis_hist_{_slug(measure_col)}",
            title=f"Distribución de {measure_label}",
            visual_type=VisualTypeEnum.HISTOGRAM,
            page_id="page_analysis",
            dimension=None,
            measure=measure_ref,
            measure_name=measure_label,
            fields=self._measure_fields(),
            axis_label=measure_label,
            legend_field=None,
            filter_suggestion=None,
            reason="La distribución de la medida principal ayuda a identificar sesgos, colas largas y concentración de valores; el histograma es la forma estándar de mostrarla.",
            confidence=level,
            confidence_rationale=rationale,
            alternative_types=[VisualTypeEnum.BAR],
            preview_data=points,
            preview_mode=PreviewModeEnum.REAL,
            data_quality_notes=self._dq_notes([(self.fact_name, measure_col)]),
            accessibility_note="Mostrar el rango de cada intervalo como etiqueta de texto.",
            order=0,
            business_question=f"¿Cómo se distribuyen los valores de {measure_label.lower()} en el dataset?",
            analytical_goal="distribución",
            measure_dax=self._measure_dax_formula(),
            priority=6,
        )
        redundancy.register(visual)
        return visual

    @staticmethod
    def _parse_field(field: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        if not field or "[" not in field or not field.endswith("]"):
            return None, None
        table, rest = field.split("[", 1)
        return table, rest[:-1]

    # ─────────────────────── generación completa ────────────────────────────

    def generate(self) -> List[VisualRecommendation]:
        """Genera el pool completo de visuales recomendados con control de redundancia (determinista)."""
        redundancy = RedundancyController()
        visuals: List[VisualRecommendation] = []

        line = self._line_visual(redundancy)
        if line:
            visuals.append(line)

        category_visuals = self._category_visuals(redundancy)
        visuals.extend(category_visuals)

        donut = self._donut_visual(redundancy)
        if donut:
            visuals.append(donut)

        ranking = self._ranking_visual(redundancy)
        if ranking:
            visuals.append(ranking)

        scatter = self._scatter_visual(redundancy)
        if scatter:
            visuals.append(scatter)

        histogram = self._histogram_visual(redundancy)
        if histogram:
            visuals.append(histogram)

        for index, visual in enumerate(visuals):
            visual.order = index
        return visuals
