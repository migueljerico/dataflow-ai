"""
Analizador semántico del modelo estrella (capa de Dashboard Intelligence).

Consume el MultiTableStarSchema canónico del repositorio (sin crear una segunda
representación del modelo) y lo enriquece con clasificación semántica de tablas
y columnas. Combina nombre, tipo, cardinalidad, valores, relaciones y posición
en el modelo; toda clasificación heurística queda marcada explícitamente.
"""

import re
from typing import Dict, List, Optional, Tuple

import pandas as pd

from app.core.number_parsing import to_numeric_series
from app.core.semantics import _looks_like_id_name, is_percentage_or_score_column
from app.models.dashboard import (
    ColumnSemanticTypeEnum,
    SemanticColumnAnalysis,
    SemanticModelAnalysis,
    SemanticTableAnalysis,
    TableSemanticRoleEnum,
)
from app.models.workspace import MultiTableStarSchema

_TABLE_ROLE_KEYWORDS: List[Tuple[TableSemanticRoleEnum, List[str]]] = [
    (TableSemanticRoleEnum.DATE, ["fecha", "date", "tiempo", "calendario", "calendar", "periodo"]),
    (TableSemanticRoleEnum.CUSTOMER, ["cliente", "customer", "comprador", "client"]),
    (TableSemanticRoleEnum.PRODUCT, ["producto", "product", "articulo", "item", "sku"]),
    (TableSemanticRoleEnum.EMPLOYEE, ["empleado", "employee", "personal", "staff", "worker", "agent"]),
    (TableSemanticRoleEnum.STORE, ["tienda", "store", "sucursal", "local", "shop", "almacen"]),
    (TableSemanticRoleEnum.REGION, ["region", "zona", "territorio", "area", "market", "pais", "country"]),
]

_CURRENCY_NAME_TOKENS = (
    "precio",
    "price",
    "importe",
    "amount",
    "monto",
    "coste",
    "cost",
    "salario",
    "sueldo",
    "revenue",
    "ingreso",
    "factura",
    "venta",
    "total",
    "descuento",
)
_CURRENCY_SYMBOLS = ("€", "$", "usd", "eur", "£")
_QUANTITY_TOKENS = ("cantidad", "quantity", "qty", "unidades", "units", "stock", "volumen", "pedidos")
_DATE_NAME_TOKENS = ("fecha", "date", "dia", "day", "mes", "month", "ano", "anio", "year", "trimestre", "semana")
_GEOGRAPHY_TOKENS = (
    "pais",
    "país",
    "country",
    "ciudad",
    "city",
    "region",
    "estado",
    "state",
    "provincia",
    "territorio",
    "zona",
    "direccion",
    "address",
)
_ORDINAL_VOCABULARIES = [
    {"bajo", "medio", "alto"},
    {"low", "medium", "high"},
    {"si", "no", "sí"},
    {"bueno", "regular", "malo"},
    {"1", "2", "3", "4", "5"},
]

_NUMERIC_MIN_VALID_RATIO = 0.8
_DATE_MIN_VALID_RATIO = 0.8
# Prefiltro barato: solo se intenta el parseo datetime cuando los valores
# tienen pinta de fecha (evita ruido de dateutil sobre columnas de texto/ID).
_DATE_LIKE_RE = re.compile(r"\d{1,4}[-/]\d{1,2}[-/]\d{1,4}")


def _tokens(name: str) -> str:
    """Nombre normalizado a minúsculas para búsquedas de tokens."""
    return str(name).lower().replace("-", "_").replace(" ", "_")


def _date_parseable_ratio(series: pd.Series) -> float:
    """Proporción de valores no nulos parseables como fecha (ISO o europeo)."""
    s = series.dropna().astype(str).str.strip()
    s = s[s != ""]
    if len(s) == 0:
        return 0.0
    sample = s.head(200)
    if not bool(sample.str.contains(_DATE_LIKE_RE, regex=True).mean() >= 0.6):
        return 0.0
    parsed_iso = pd.to_datetime(s.unique(), errors="coerce", dayfirst=False)
    ok = {u for u, p in zip(s.unique(), parsed_iso, strict=True) if pd.notna(p)}
    if len(ok) < len(s.unique()):
        residual = [u for u in s.unique() if u not in ok]
        parsed_eur = pd.to_datetime(residual, errors="coerce", dayfirst=True)
        ok.update(u for u, p in zip(residual, parsed_eur, strict=True) if pd.notna(p))
    valid = int(s.isin(ok).sum())
    return valid / len(s)


def _is_boolean_like(series: pd.Series) -> bool:
    if pd.api.types.is_bool_dtype(series):
        return True
    normalized = {str(v).strip().lower() for v in series.dropna().unique()}
    if 0 < len(normalized) <= 2 and normalized <= {"true", "false", "si", "no", "sí", "1", "0", "verdadero", "falso"}:
        return True
    return False


class SemanticModelAnalyzer:
    """Clasificación semántica determinista de tablas y columnas del modelo estrella."""

    @classmethod
    def classify_table_role(cls, table_name: str, star_role: str) -> Tuple[TableSemanticRoleEnum, Optional[str]]:
        name = _tokens(table_name)
        if star_role == "fact":
            return TableSemanticRoleEnum.FACT, None
        for role, keywords in _TABLE_ROLE_KEYWORDS:
            if any(k in name for k in keywords):
                return role, None
        return (
            TableSemanticRoleEnum.DIMENSION,
            "Rol semántico inferido por posición (dimensión sin nombre reconocible).",
        )

    @classmethod
    def classify_column(
        cls,
        table_name: str,
        column_name: str,
        series: pd.Series,
        node_keys: Optional[List[str]] = None,
        measure_names: Optional[List[str]] = None,
    ) -> SemanticColumnAnalysis:
        """Clasifica una columna combinando nombre, tipo, cardinalidad y valores."""
        signals: List[str] = []
        name_lower = _tokens(column_name)
        total = len(series)
        non_null = series.dropna()
        null_pct = round(100.0 * (1.0 - (len(non_null) / total)), 2) if total > 0 else 100.0
        cardinality = int(non_null.nunique())
        node_keys = node_keys or []
        measure_names = measure_names or []

        signals.append(f"tipo:{series.dtype}")

        # 1) Email: nombre o valores con '@'
        if "email" in name_lower or "correo" in name_lower:
            signals.append("nombre:email")
            return cls._build(
                table_name, column_name, ColumnSemanticTypeEnum.EMAIL, cardinality, null_pct, signals, False
            )
        if len(non_null) > 0:
            at_ratio = float(non_null.astype(str).str.contains("@").mean())
            if at_ratio >= 0.7:
                signals.append(f"valores:{round(at_ratio * 100)}% contienen '@'")
                return cls._build(
                    table_name, column_name, ColumnSemanticTypeEnum.EMAIL, cardinality, null_pct, signals, False
                )

        # 2) Fechas
        date_ratio = _date_parseable_ratio(series)
        name_is_date = any(k in name_lower for k in _DATE_NAME_TOKENS)
        if name_is_date:
            signals.append("nombre:fecha")
        if date_ratio >= _DATE_MIN_VALID_RATIO and (cardinality >= 3 or name_is_date):
            signals.append(f"valores:{round(date_ratio * 100)}% parseables como fecha")
            # Date vs Datetime: si el componente temporal es siempre 00:00 es DATE
            parsed = pd.to_datetime(non_null, errors="coerce", dayfirst=False)
            has_time = parsed.dropna().apply(lambda d: d.hour != 0 or d.minute != 0 or d.second != 0)
            if bool(has_time.sum()) > 0:
                return cls._build(
                    table_name, column_name, ColumnSemanticTypeEnum.DATETIME, cardinality, null_pct, signals, False
                )
            return cls._build(
                table_name, column_name, ColumnSemanticTypeEnum.DATE, cardinality, null_pct, signals, False
            )

        # 3) Identificadores (por posición en el modelo: PK/FK, o por nombre)
        if column_name in node_keys:
            signals.append("relacion:clave en el modelo estrella")
            return cls._build(
                table_name, column_name, ColumnSemanticTypeEnum.IDENTIFIER, cardinality, null_pct, signals, False
            )
        if _looks_like_id_name(name_lower):
            signals.append("nombre:identificador")
            # Heurística si la cardinalidad no respalda el patrón de identificador
            heuristic = total > 0 and cardinality < max(3, int(total * 0.2))
            return cls._build(
                table_name, column_name, ColumnSemanticTypeEnum.IDENTIFIER, cardinality, null_pct, signals, heuristic
            )

        # 4) Boolean
        if _is_boolean_like(series):
            signals.append("valores:booleano")
            return cls._build(
                table_name, column_name, ColumnSemanticTypeEnum.BOOLEAN, cardinality, null_pct, signals, False
            )

        # 5) Rama numérica
        numeric = to_numeric_series(series)
        non_null_numeric = numeric[series.notna()]
        valid_ratio = (non_null_numeric.notna().sum() / len(non_null_numeric)) if len(non_null_numeric) > 0 else 0.0

        if valid_ratio >= _NUMERIC_MIN_VALID_RATIO:
            signals.append(f"valores:{round(valid_ratio * 100)}% parseables como número")
            if is_percentage_or_score_column(column_name, series):
                signals.append("nombre:porcentaje")
                return cls._build(
                    table_name, column_name, ColumnSemanticTypeEnum.PERCENTAGE, cardinality, null_pct, signals, False
                )
            sample_text = " ".join(non_null.head(200).astype(str).str.lower()).replace(" ", "")
            has_currency_symbol = any(sym in sample_text for sym in _CURRENCY_SYMBOLS)
            name_currency = any(t in name_lower for t in _CURRENCY_NAME_TOKENS)
            name_quantity = any(t in name_lower for t in _QUANTITY_TOKENS)
            if name_quantity:
                signals.append("nombre:cantidad")
                return cls._build(
                    table_name, column_name, ColumnSemanticTypeEnum.QUANTITY, cardinality, null_pct, signals, False
                )
            if has_currency_symbol or name_currency:
                signals.append("nombre/simbolos:monetario")
                heuristic = name_currency and not has_currency_symbol
                return cls._build(
                    table_name, column_name, ColumnSemanticTypeEnum.CURRENCY, cardinality, null_pct, signals, heuristic
                )
            if column_name in measure_names:
                signals.append("modelo:medida declarada en el esquema estrella")
                return cls._build(
                    table_name, column_name, ColumnSemanticTypeEnum.MEASURE, cardinality, null_pct, signals, False
                )
            if cardinality > 30:
                return cls._build(
                    table_name, column_name, ColumnSemanticTypeEnum.MEASURE, cardinality, null_pct, signals, True
                )
            return cls._build(
                table_name, column_name, ColumnSemanticTypeEnum.CATEGORY, cardinality, null_pct, signals, True
            )

        # 6) Geografía por nombre
        if any(t in name_lower for t in _GEOGRAPHY_TOKENS):
            signals.append("nombre:geografía")
            return cls._build(
                table_name, column_name, ColumnSemanticTypeEnum.GEOGRAPHY, cardinality, null_pct, signals, True
            )

        # 7) Nombre de persona/entidad
        if any(k in name_lower for k in ("nombre", "name", "contacto", "contact", "razon_social")):
            signals.append("nombre:nombre")
            return cls._build(
                table_name, column_name, ColumnSemanticTypeEnum.NAME, cardinality, null_pct, signals, True
            )

        # 8) Subcategoría
        if any(
            k in name_lower for k in ("subcategoria", "subcategory", "subtipo", "tipo", "type", "segmento", "segment")
        ):
            signals.append("nombre:subcategoría")
            return cls._build(
                table_name, column_name, ColumnSemanticTypeEnum.SUBCATEGORY, cardinality, null_pct, signals, False
            )

        # 9) Ordinal por vocabulario
        lowered = {str(v).strip().lower() for v in non_null.unique()}
        for vocab in _ORDINAL_VOCABULARIES:
            if lowered and lowered <= vocab:
                signals.append("valores:escala ordinal conocida")
                return cls._build(
                    table_name, column_name, ColumnSemanticTypeEnum.ORDINAL, cardinality, null_pct, signals, False
                )

        # 10) Categoría vs texto libre
        avg_len = float(non_null.astype(str).str.len().mean()) if len(non_null) > 0 else 0.0
        if cardinality <= 60 and avg_len <= 40:
            name_categorical = any(
                k in name_lower for k in ("categoria", "category", "familia", "grupo", "canal", "channel")
            )
            if name_categorical:
                signals.append("nombre:categoría")
            return cls._build(
                table_name,
                column_name,
                ColumnSemanticTypeEnum.CATEGORY,
                cardinality,
                null_pct,
                signals,
                not name_categorical,
            )

        return cls._build(table_name, column_name, ColumnSemanticTypeEnum.TEXT, cardinality, null_pct, signals, True)

    @staticmethod
    def _build(
        table_name: str,
        column_name: str,
        semantic_type: ColumnSemanticTypeEnum,
        cardinality: int,
        null_pct: float,
        signals: List[str],
        is_heuristic: bool,
    ) -> SemanticColumnAnalysis:
        return SemanticColumnAnalysis(
            table_name=table_name,
            column_name=column_name,
            semantic_type=semantic_type,
            cardinality=cardinality,
            null_percentage=null_pct,
            completeness_pct=round(100.0 - null_pct, 2),
            inferred_from=", ".join(signals),
            is_heuristic=is_heuristic,
        )

    @classmethod
    def analyze(cls, schema: MultiTableStarSchema, dataframes: Dict[str, pd.DataFrame]) -> SemanticModelAnalysis:
        """
        Analiza todas las tablas del modelo estrella.

        `dataframes` mapea nombre de tabla → DataFrame (versión limpia). Las tablas
        sin DataFrame disponible se analizan solo por metadatos del esquema.
        """
        uncertainty_notes: List[str] = []
        tables: List[SemanticTableAnalysis] = []
        ordered_nodes = [schema.fact_table] + sorted(schema.dimension_tables, key=lambda n: n.table_name)

        for node in ordered_nodes:
            df = dataframes.get(node.table_name, pd.DataFrame())
            role, role_note = cls.classify_table_role(node.table_name, node.role.value)
            if role_note:
                uncertainty_notes.append(f"{node.table_name}: {role_note}")

            column_analyses: List[SemanticColumnAnalysis] = []
            for column in df.columns:
                column_analyses.append(
                    cls.classify_column(
                        table_name=node.table_name,
                        column_name=str(column),
                        series=df[column],
                        node_keys=node.primary_keys + node.foreign_keys,
                        measure_names=node.measures,
                    )
                )

            tables.append(
                SemanticTableAnalysis(
                    table_id=node.table_id,
                    table_name=node.table_name,
                    star_role=node.role.value,
                    semantic_role=role,
                    row_count=node.row_count,
                    columns=column_analyses,
                    heuristic_note=role_note,
                )
            )

        if not any(t.semantic_role == TableSemanticRoleEnum.DATE for t in tables):
            uncertainty_notes.append("No se detectó una tabla de fechas explícita en el modelo.")

        return SemanticModelAnalysis(model_id=schema.model_id, tables=tables, uncertainty_notes=uncertainty_notes)
