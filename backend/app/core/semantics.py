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

# Nombres que denotan fracción/discount en rango [0, 1] (0.05 = 5 %).
# Se distinguen de los porcentajes [0, 100]: una columna es fracción cuando
# alguno de sus tokens es discount/descuento Y ningún token es de tipo
# porcentual (pct, rate, ...). Así "Discount" es fracción pero
# "Descuento_Pct" sigue siendo porcentaje.
_FRACTION_TOKENS = {"discount", "descuento", "descto", "dto"}
_PCT_LIKE_TOKENS = {
    "pct",
    "pcte",
    "percentage",
    "percent",
    "porcentaje",
    "porc",
    "rate",
    "ratio",
    "tasa",
    "score",
}

# Palabras inglesas/españolas comunes terminadas en "id" que NO son
# identificadores (evitan falsos positivos del detector de sufijo "id").
_NON_ID_SUFFIX_EXCEPTIONS = {
    "valid",
    "invalid",
    "solid",
    "fluid",
    "liquid",
    "humid",
    "acid",
    "grid",
    "arid",
    "rapid",
    "vivid",
    "lipid",
    "hybrid",
    "pyramid",
    "placid",
    "rancid",
    "rigid",
    "timid",
    "cupid",
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


_ID_NAME_EXACT = {
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
}

_ID_NAME_KEYWORDS = [
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


def is_fraction_or_discount_column(col_name: str, raw_series: Any = None) -> bool:
    """
    Determina si una columna representa una fracción/descuento en rango [0, 1].

    Requiere token discount/descuento en el nombre (separado por guiones bajos,
    espacios o CamelCase) y ausencia de tokens porcentuales (pct, rate, ...),
    para no confundir "Descuento_Pct" (porcentaje [0, 100]) con "Discount"
    (fracción [0, 1]). Ante la duda, exige además coherencia con los datos:
    si hay valores no nulos > 1.5 o negativos de magnitud relevante, no es fracción.
    """
    col_lower = str(col_name).lower().strip()
    tokens = set(re.split(r"[_\s\-./]+", col_lower))
    tokens.update(re.findall(r"[a-záéíóúñü]+", col_lower))
    tokens = {t for t in tokens if t}
    if not (tokens & _FRACTION_TOKENS):
        return False
    if tokens & _PCT_LIKE_TOKENS:
        return False

    if raw_series is not None:
        try:
            from app.core.number_parsing import to_numeric_series

            nums = to_numeric_series(pd.Series(raw_series)).dropna()
            if len(nums) > 0:
                # Si la mayoría de valores no nulos son números de gran escala (>10),
                # probablemente sea un importe monetario y no una fracción/descuento [0, 1].
                # Los valores negativos (e.g. -3) o fuera de rango (e.g. 1.2) son anomalías
                # a detectar y corregir en calidad, no invalidan la semántica de la columna.
                if (nums.abs() > 10.0).sum() / len(nums) > 0.4:
                    return False
        except Exception:
            pass
    return True


def _looks_like_id_name(col_lower: str) -> bool:
    """
    Heurística de nombre para identificadores, independiente de guiones bajos.

    Reconoce tanto customer_id como customerid/customerID/CUSTOMER_ID:
    prefijos y sufijos explícitos (id, cod, pk, fk, ...), palabras clave de
    código, y patrones */id, id/*, *_id, *-id, *id (CamelCase: CustomerID).
    """
    if not col_lower:
        return False
    if col_lower in _NON_ID_SUFFIX_EXCEPTIONS:
        return False
    # Prefijos/sufijos con o sin separador: id, *_id, *-id, id_*, *id (CamelCase
    # "CustomerID" llega aquí como "customerid" y casa con endswith("id")).
    # También "customer_id" (endswith _id) y "id_cliente" (startswith id_).
    if (
        col_lower.startswith(("id", "cod", "ref", "num_", "pk_", "fk_", "cpostal", "cp_"))
        or col_lower.endswith(("_id", "_cod", "_code", "_ref", "_num", "_pk", "_fk", "_ine", "_cp"))
        or col_lower in _ID_NAME_EXACT
    ):
        return True
    # CamelCase sin separador: CustomerID, OrderID, ProductID... La terminación
    # "id" en minúsculas + longitud mínima evita falsos positivos ("valid").
    if len(col_lower) >= 4 and col_lower.endswith("id"):
        stem = col_lower[:-2]
        if len(stem) >= 2 and stem.isalpha():
            return True
    if any(k in col_lower for k in _ID_NAME_KEYWORDS):
        return True
    return False


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

    # 1. Heurística de nombre (independiente de guiones bajos: CustomerID y customer_id).
    if _looks_like_id_name(col_lower):
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
