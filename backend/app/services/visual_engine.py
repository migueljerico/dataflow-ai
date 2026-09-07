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
- Scatter para relación entre dos variables numéricas.
- Histogram para distribución de una medida continua.
"""

import re
from typing import Dict, List, Optional, Tuple

import pandas as pd

from app.models.dashboard import (
    ColumnSemanticTypeEnum,
    ConfidenceLevelEnum,
    PreviewDataPoint,
    PreviewModeEnum,
    SemanticModelAnalysis,
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
        self._column_index = self._build_column_index()
        self.primary_measure = self._select_primary_measure()

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
        """Elige la medida principal: Ventas netas derivadas > monetaria > cantidad > medida continua."""
        derived_key = f"{self.fact_name}[{DERIVED_MEASURE_COL}]"
        if derived_key in self._column_index:
            entry = self._column_index[derived_key]
            dax_measures = self.schema.suggested_dax_measures
            dax_name = (
                "Ventas_Netas"
                if "Ventas_Netas" in dax_measures
                else ("Ventas_Totales" if "Ventas_Totales" in dax_measures else "Ventas_Netas")
            )
            return {
                "table": self.fact_name,
                "column": DERIVED_MEASURE_COL,
                "analysis": entry["analysis"],
                "label": "Ventas netas",
                "derived": True,
                "dax_name": dax_name,
                "dax_formula": dax_measures.get(dax_name, ""),
                "source_columns": self._derived_source_columns(),
            }
        for preferred in (
            ColumnSemanticTypeEnum.CURRENCY,
            ColumnSemanticTypeEnum.QUANTITY,
            ColumnSemanticTypeEnum.MEASURE,
        ):
            candidates = [c for c in self.columns_of_type(preferred) if c["table"] == self.fact_name]
            if candidates:
                # Orden determinista: completitud desc, luego cardinalidad desc, luego nombre
                candidates.sort(
                    key=lambda c: (
                        -float(c["analysis"].completeness_pct),
                        -int(c["analysis"].cardinality),
                        str(c["column"]),
                    )
                )
                best = candidates[0]
                return {
                    "table": str(best["table"]),
                    "column": str(best["column"]),
                    "analysis": best["analysis"],
                    "label": self._measure_label(best),
                    "derived": False,
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

    def _measure_fields(self) -> List[str]:
        """Campos reales del modelo que respaldan la medida principal (nunca columnas sintéticas)."""
        if self.primary_measure is None:
            return []
        if self.primary_measure.get("derived"):
            return [f"{self.fact_name}[{c}]" for c in self.primary_measure.get("source_columns", [])]
        return [f"{self.primary_measure['table']}[{self.primary_measure['column']}]"]

    @staticmethod
    def _measure_label(entry: Dict[str, object]) -> str:
        column = str(entry["column"])
        semantic_type = entry["analysis"].semantic_type
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
        """Agrega la medida principal por una dimensión. Devuelve puntos y cardinalidad total."""
        frame = self._merge_with_dim(dim_table, dim_column)
        if frame is None or self.primary_measure is None:
            return [], 0
        measure_col = str(self.primary_measure["column"])
        numeric_frame = frame.copy()
        numeric_frame[measure_col] = pd.to_numeric(numeric_frame[measure_col], errors="coerce")
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
            parts.append("+10 medida principal sumable disponible")
        else:
            score -= 25
            parts.append("-25 sin medida principal sumable")
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

    def _line_visual(self) -> Optional[VisualRecommendation]:
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
        grouped = base.groupby("__periodo")[measure_col].sum().sort_index()
        if len(grouped) < 3:
            return None
        points = [
            PreviewDataPoint(label=str(label), value=round(float(value), 2))
            for label, value in grouped.tail(MAX_PREVIEW_POINTS).items()
        ]
        table = str(candidate["table"])
        column = str(candidate["column"])
        extra = [(10, "cardinalidad temporal adecuada")] if len(grouped) >= 6 else [(-10, "pocos puntos temporales")]
        score, level, rationale = self._score(55, candidate["entry"], extra)
        measure_ref = f"{self.primary_measure['table']}[{self.primary_measure['column']}]"
        return VisualRecommendation(
            visual_id=f"vis_line_{_slug(column)}",
            title=f"Evolución de {self.primary_measure['label']} por {'mes' if granularity == 'M' else 'día'}",
            visual_type=VisualTypeEnum.LINE,
            page_id="page_overview",
            dimension=f"{table}[{column}]",
            measure=measure_ref,
            measure_name=self.primary_measure["label"],
            fields=[f"{table}[{column}]", measure_ref],
            axis_label=f"{table}[{column}]",
            legend_field=None,
            filter_suggestion=f"{table}[{column}] (año)",
            reason="La evolución temporal de la medida principal debe leerse como tendencia continua; el gráfico de líneas preserva el orden cronológico y facilita detectar patrones estacionales.",
            confidence=level,
            confidence_rationale=rationale,
            alternative_types=[VisualTypeEnum.AREA],
            preview_data=points,
            preview_mode=PreviewModeEnum.REAL,
            data_quality_notes=self._dq_notes([(table, column)]),
            accessibility_note="Incluir valores numéricos en el tooltip y no codificar la tendencia solo con color.",
            order=0,
        )

    def _category_visuals(self) -> List[VisualRecommendation]:
        visuals: List[VisualRecommendation] = []
        if self.primary_measure is None:
            return visuals
        seen_titles: set = set()
        category_entries = (
            self.columns_of_type(ColumnSemanticTypeEnum.CATEGORY)
            + self.columns_of_type(ColumnSemanticTypeEnum.SUBCATEGORY)
            + self.columns_of_type(ColumnSemanticTypeEnum.GEOGRAPHY)
        )

        for entry in sorted(category_entries, key=lambda e: (str(e["table"]), str(e["column"]))):
            table = str(entry["table"])
            column = str(entry["column"])
            if (
                column.lower() in ("id",)
                or str(entry["analysis"].semantic_type) == ColumnSemanticTypeEnum.IDENTIFIER.value
            ):
                continue
            joinable = table == self.fact_name or bool(self._relations_to(table))
            if not joinable:
                continue
            points, total_cardinality = self._aggregate_by(table, column, top_n=8)
            if total_cardinality < 2 or not points:
                continue
            if total_cardinality > MAX_CATEGORIES_BAR:
                continue
            title = f"{self.primary_measure['label']} por {column.replace('_', ' ')}"
            if title in seen_titles:
                continue
            seen_titles.add(title)

            longest_label = max(len(p.label) for p in points)
            use_horizontal = longest_label > 18 or total_cardinality > 12
            visual_type = VisualTypeEnum.HORIZONTAL_BAR if use_horizontal else VisualTypeEnum.BAR

            cardinality_bonus = 10 if 3 <= total_cardinality <= 15 else (-5 if total_cardinality > 20 else 0)
            score, level, rationale = self._score(
                50, entry, [(cardinality_bonus, f"cardinalidad {total_cardinality} adecuada para comparación")]
            )
            reason = (
                f"Comparación directa de {self.primary_measure['label']} entre {total_cardinality} valores de "
                f"'{column}'; el gráfico de barras permite leer con precisión el peso relativo de cada categoría."
            )
            alternatives = (
                [VisualTypeEnum.BAR, VisualTypeEnum.STACKED_BAR]
                if use_horizontal
                else [VisualTypeEnum.HORIZONTAL_BAR, VisualTypeEnum.STACKED_BAR]
            )
            visuals.append(
                VisualRecommendation(
                    visual_id=f"vis_bar_{_slug(table + '_' + column)}",
                    title=title,
                    visual_type=visual_type,
                    page_id="page_overview",
                    dimension=f"{table}[{column}]",
                    measure=f"{self.primary_measure['table']}[{self.primary_measure['column']}]",
                    measure_name=self.primary_measure["label"],
                    fields=[f"{table}[{column}]", f"{self.primary_measure['table']}[{self.primary_measure['column']}]"],
                    axis_label=column.replace("_", " "),
                    legend_field=None,
                    filter_suggestion=f"{table}[{column}]",
                    reason=reason,
                    confidence=level,
                    confidence_rationale=rationale,
                    alternative_types=alternatives,
                    preview_data=points,
                    preview_mode=PreviewModeEnum.REAL,
                    data_quality_notes=self._dq_notes([(table, column)]),
                    accessibility_note="Etiquetar cada barra con su valor exacto para no depender solo de la longitud.",
                    order=0,
                )
            )
            if len(visuals) >= 4:
                break
        return visuals

    def _donut_visual(self, category_visuals: List[VisualRecommendation]) -> Optional[VisualRecommendation]:
        """Donut SOLO con una única composición de pocas categorías (2..6)."""
        for visual in category_visuals:
            dim_table, dim_column = self._parse_field(visual.dimension)
            if not dim_table:
                continue
            points, total_cardinality = self._aggregate_by(dim_table, dim_column, top_n=MAX_PIE_CATEGORIES + 1)
            if not (2 <= total_cardinality <= MAX_PIE_CATEGORIES) or len(points) != total_cardinality:
                continue
            score, level, rationale = self._score(40, None, [(10, f"composición única con {total_cardinality} partes")])
            return VisualRecommendation(
                visual_id=f"vis_donut_{_slug(dim_column)}",
                title=f"Composición de {self.primary_measure['label']} por {dim_column.replace('_', ' ')}",
                visual_type=VisualTypeEnum.DONUT,
                page_id="page_overview",
                dimension=visual.dimension,
                measure=visual.measure,
                measure_name=self.primary_measure["label"] if self.primary_measure else None,
                fields=visual.fields,
                axis_label=None,
                legend_field=visual.dimension,
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
                data_quality_notes=visual.data_quality_notes,
                accessibility_note="Añadir leyenda con porcentajes explícitos; nunca diferenciar solo por color.",
                order=0,
            )
        return None

    def _scatter_visual(self) -> Optional[VisualRecommendation]:
        numeric_columns = [
            c
            for c in self.columns_of_type(ColumnSemanticTypeEnum.MEASURE)
            + self.columns_of_type(ColumnSemanticTypeEnum.CURRENCY)
            + self.columns_of_type(ColumnSemanticTypeEnum.QUANTITY)
            if c["table"] == self.fact_name
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
        points = [
            PreviewDataPoint(
                label=f"{i + 1}", value=round(float(row[x_col]), 2), secondary_value=round(float(row[y_col]), 2)
            )
            for i, row in enumerate(head.itertuples(index=False))
        ]
        score, level, rationale = self._score(
            45, None, [(10, "dos variables numéricas continuas con datos suficientes")]
        )
        return VisualRecommendation(
            visual_id="vis_scatter_primary",
            title=f"Relación entre {x_col.replace('_', ' ')} y {y_col.replace('_', ' ')}",
            visual_type=VisualTypeEnum.SCATTER,
            page_id="page_analysis",
            dimension=f"{self.fact_name}[{x_col}]",
            measure=f"{self.fact_name}[{y_col}]",
            measure_name=y_col.replace("_", " "),
            fields=[f"{self.fact_name}[{x_col}]", f"{self.fact_name}[{y_col}]"],
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
        )

    def _histogram_visual(self) -> Optional[VisualRecommendation]:
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
        return VisualRecommendation(
            visual_id=f"vis_hist_{_slug(measure_col)}",
            title=f"Distribución de {self.primary_measure['label']}",
            visual_type=VisualTypeEnum.HISTOGRAM,
            page_id="page_analysis",
            dimension=None,
            measure=f"{self.fact_name}[{measure_col}]",
            measure_name=self.primary_measure["label"],
            fields=[f"{self.fact_name}[{measure_col}]"],
            axis_label=measure_col.replace("_", " "),
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
        )

    def _ranking_visual(self, category_visuals: List[VisualRecommendation]) -> Optional[VisualRecommendation]:
        """Tabla de detalle/ranking sobre la dimensión con más categorías."""
        if self.primary_measure is None or not category_visuals:
            return None
        best = max(
            category_visuals,
            key=lambda v: len(self._aggregate_by(*self._parse_field(v.dimension), top_n=100)[0]),
        )
        dim_table, dim_column = self._parse_field(best.dimension)
        points, total_cardinality = self._aggregate_by(dim_table, dim_column, top_n=5)
        if not points:
            return None
        score, level, rationale = self._score(55, None, [(10, "ranking de detalle sobre dimensión validada")])
        return VisualRecommendation(
            visual_id=f"vis_table_{_slug(dim_column)}",
            title=f"Top {dim_column.replace('_', ' ')} por {self.primary_measure['label']}",
            visual_type=VisualTypeEnum.TABLE,
            page_id="page_detail",
            dimension=best.dimension,
            measure=best.measure,
            measure_name=self.primary_measure["label"],
            fields=best.fields,
            axis_label=None,
            legend_field=None,
            filter_suggestion=best.filter_suggestion,
            reason="El ranking en tabla ofrece el detalle exacto que completa la lectura de los gráficos agregados.",
            confidence=level,
            confidence_rationale=rationale,
            alternative_types=[VisualTypeEnum.HORIZONTAL_BAR],
            preview_data=points,
            preview_mode=PreviewModeEnum.REAL,
            data_quality_notes=best.data_quality_notes,
            accessibility_note="Tabla con encabezados semánticos y orden descendente explícito.",
            order=0,
        )

    @staticmethod
    def _parse_field(field: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        if not field or "[" not in field or not field.endswith("]"):
            return None, None
        table, rest = field.split("[", 1)
        return table, rest[:-1]

    # ─────────────────────── generación completa ────────────────────────────

    def generate(self) -> List[VisualRecommendation]:
        """Genera el pool completo de visuales recomendados (determinista)."""
        visuals: List[VisualRecommendation] = []
        line = self._line_visual()
        if line:
            visuals.append(line)
        category_visuals = self._category_visuals()
        visuals.extend(category_visuals)
        donut = self._donut_visual(category_visuals)
        if donut:
            visuals.append(donut)
        scatter = self._scatter_visual()
        if scatter:
            visuals.append(scatter)
        histogram = self._histogram_visual()
        if histogram:
            visuals.append(histogram)
        ranking = self._ranking_visual(category_visuals)
        if ranking:
            visuals.append(ranking)
        for index, visual in enumerate(visuals):
            visual.order = index
        return visuals
