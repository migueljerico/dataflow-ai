"""
Helpers semanticos compartidos — evita duplicacion de logica de deteccion
de columnas de porcentaje/score en ETL, Quality y Profiling.
"""

import re
from typing import Any

import pandas as pd

from app.core.number_parsing import get_numeric_parseable_ratio

_PCT_SUFFIXES = ("_pct", "_percentage", "_porcentaje", "_rate", "_ratio", "_tasa", "_score")
_PCT_PREFIXES = ("pct_", "porcentaje_", "tasa_", "ratio_", "score_")
_PCT_EXACT = {
    "%",
    "pct",
    "porcentaje",
    "ctr",
    "cvr",
    "roi",
    "score",
    "score_calidad",
    "tasa_conversion",
    "conversion_rate",
    "churn_rate",
    "descuento_pct",
    "incidencias_pct",
}


def is_percentage_or_score_column(col_name: str, raw_series: Any = None) -> bool:
    """
    Determina si una columna es de tipo porcentaje o score acotado a [0, 100].
    Garantiza que columnas de texto libre (ej. Observaciones) NUNCA se clasifiquen como porcentaje,
    exigiendo que al menos el 80% de sus valores no nulos con contenido real sean parseables a número.
    """
    col_lower = col_name.lower().strip()
    is_pct_name = col_lower.endswith(_PCT_SUFFIXES) or col_lower.startswith(_PCT_PREFIXES) or col_lower in _PCT_EXACT

    if raw_series is not None:
        try:
            s = pd.Series(raw_series)
            ratio, valid_cnt, total_real = get_numeric_parseable_ratio(s)
            # Regla de Oro: si menos del 80% es parseable como número, NUNCA es porcentaje
            if total_real > 0 and ratio < 0.8:
                return False
            # Si el ratio es >= 0.8 y contiene '%' en alguna celda o su nombre es de porcentaje
            non_null_vals = s.dropna().astype(str)
            if any("%" in x for x in non_null_vals):
                return True
            if is_pct_name and ratio >= 0.8:
                return True
            return False
        except Exception:
            pass

    return is_pct_name


def is_id_or_code_column(col_name: str, non_null_str: Any = None) -> bool:
    """
    Determina si una columna es identificador o código de negocio (IDs, códigos postales, CIF/NIF, etc.).
    Garantiza que valores numéricos con ceros a la izquierda (ej. '08001') o con semántica de clave
    se preserven como string/texto evitando su pérdida de ceros en la lectura y exportación.
    """
    col_lower = str(col_name).lower().strip()

    # Si el nombre de la columna es explícitamente una fecha (ej. 'fecha', 'date_created'), NO es ID
    is_date_named = (
        col_lower.startswith(("fecha", "date", "fec_"))
        or col_lower.endswith(("_fecha", "_date"))
        or col_lower in ["fecha", "date", "fec", "created_at", "updated_at", "timestamp"]
    )
    if is_date_named and not col_lower.startswith(("id_", "cod_", "pk_", "fk_")):
        return False

    # 1. Nombres y prefijos/sufijos explícitos de identificador o código
    if (
        col_lower.startswith(("id", "cod", "ref", "num_", "pk_", "fk_", "cpostal", "cp_"))
        or col_lower.endswith(("_id", "_cod", "_code", "_ref", "_num", "_pk", "_fk", "_ine", "_cp"))
        or col_lower
        in [
            "id",
            "cod",
            "code",
            "codigo",
            "ref",
            "referencia",
            "cpostal",
            "cp",
            "cif",
            "nif",
            "nie",
            "dni",
            "iban",
            "sku",
            "ean",
            "matricula",
            "tramo",
            "distrito",
            "seccion",
            "num_factura",
            "id_factura",
            "cod_factura",
            "num_pedido",
            "id_pedido",
            "cod_pedido",
        ]
        or any(
            k in col_lower
            for k in [
                "codigo",
                "code",
                "cpostal",
                "cod_postal",
                "codigo_postal",
                "cod_ine",
                "seccion_censal",
                "identificador",
                "cif",
                "nif",
                "nie",
                "dni",
                "iban",
                "sku",
                "ean",
                "matricula",
                "expediente",
                "tramo",
                "tracking",
            ]
        )
    ):
        return True

    if non_null_str is not None:
        try:
            sample = pd.Series(non_null_str).dropna().astype(str).head(50)
            # 2. Muestras con ceros a la izquierda en cadenas numéricas (ej. códigos postales '08001' o INE '01004')
            has_leading_zeros = any(
                val.strip().startswith("0") and len(val.strip()) > 1 and val.strip().isdigit() for val in sample
            )
            if has_leading_zeros:
                return True

            # 3. Patrones alfanuméricos típicos de códigos
            has_alphanumeric_code = any(
                bool(re.search(r"[A-Za-z]", val.strip()))
                and bool(re.match(r"^[A-Za-z0-9]{1,8}[-_][A-Za-z0-9]{1,}$", val.strip()))
                for val in sample
            )
            if has_alphanumeric_code:
                return True
        except Exception:
            pass

    return False
