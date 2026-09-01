"""
Parseo numérico centralizado para datos empresariales europeos y americanos.

Toda la plataforma (profiling, quality, ETL y auditoría) debe interpretar los
números con el mismo criterio para que los conteos de calidad y los logs de
auditoría sean coherentes con la transformación ejecutada.

Convenciones soportadas tras limpiar símbolos (€, $, %, USD, EUR) y espacios:
- Europeo:  1.234,56 / 1.234.567,89 / 1234,56 / 1.200  ->  coma decimal, punto de millares
- Americano: 1,234.56 / 1,234,567.89                    ->  punto decimal, coma de millares
- Marcadores de ausencia (N/D, N/A, --, -, null, ...)       ->  None
"""

import re
from typing import Any, Optional, Tuple

import numpy as np
import pandas as pd

MISSING_MARKERS = {
    "n/d",
    "n/a",
    "nd",
    "na",
    "-",
    "--",
    "---",
    "–",
    "—",
    "null",
    "none",
    "nan",
    "undefined",
    "",
    "n.a.",
    "n.d.",
    "s/n",
    "s/d",
    "nil",
    "n_a",
    "n_d",
}

_SYMBOLS_RE = re.compile(r"[€$%\s\u00a0]")
_CURRENCY_WORDS_RE = re.compile(r"(?i)\b(usd|eur)\b")
_DASH_ONLY_RE = re.compile(r"^[-_—–\s]+$")
_EUROPEAN_THOUSANDS_RE = re.compile(r"^[+-]?\d{1,3}(\.\d{3})+(,\d+)?$")
_EUROPEAN_DECIMAL_RE = re.compile(r"^[+-]?\d*,\d+$")
_AMERICAN_THOUSANDS_RE = re.compile(r"^[+-]?\d{1,3}(,\d{3})+(\.\d+)?$")


def parse_numeric_string(value: Any) -> Optional[float]:
    """Convierte un valor (str/num) con símbolos y separadores mixtos a float.

    Devuelve None para marcadores de ausencia y valores no parseables
    (equivalente a errors="coerce" pero con semántica de negocio europea).
    """
    if value is None:
        return None
    if isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, bool):
        f = float(value)
        return None if (np.isnan(f) or np.isinf(f)) else f

    raw_str = str(value).strip()
    if not raw_str or raw_str.lower() in MISSING_MARKERS or _DASH_ONLY_RE.fullmatch(raw_str):
        return None

    s = _SYMBOLS_RE.sub("", raw_str)
    s = _CURRENCY_WORDS_RE.sub("", s)
    if not s or s.lower() in MISSING_MARKERS or _DASH_ONLY_RE.fullmatch(s):
        return None

    if _EUROPEAN_THOUSANDS_RE.match(s) or _EUROPEAN_DECIMAL_RE.match(s):
        s = s.replace(".", "").replace(",", ".")
    elif _AMERICAN_THOUSANDS_RE.match(s):
        s = s.replace(",", "")

    try:
        f = float(s)
        return None if np.isinf(f) else f
    except ValueError:
        return None


def to_numeric_series(series: pd.Series) -> pd.Series:
    """Versión vectorizada de parse_numeric_string sobre una Series cualquiera."""
    return pd.to_numeric(series.map(parse_numeric_string), errors="coerce")


def is_missing_value(value: Any) -> bool:
    """Comprueba si un valor es nulo, NaN o coincide con un marcador de ausencia de negocio."""
    if value is None or pd.isna(value):
        return True
    s = str(value).strip()
    if not s or s.lower() in MISSING_MARKERS or bool(_DASH_ONLY_RE.fullmatch(s)):
        return True
    return False


def is_missing_series(series: pd.Series) -> pd.Series:
    """Devuelve una Series booleana indicando si cada elemento es nulo o marcador de ausencia."""
    if series is None or len(series) == 0:
        return pd.Series(dtype=bool)
    # pd.isna cubre None, np.nan, pd.NA
    na_mask = series.isna()
    if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
        return na_mask
    # Para los no nulos, convertir a str y comprobar el catálogo unificado
    str_series = series.astype(str).str.strip()
    marker_mask = str_series.str.lower().isin(MISSING_MARKERS) | str_series.str.match(r"^[-_—–\s]*$")
    return na_mask | marker_mask


def get_numeric_parseable_ratio(series: pd.Series) -> Tuple[float, int, int]:
    """Calcula el ratio de valores parseables a numérico sobre las celdas con contenido real.

    Ignora marcadores de ausencia (N/D, --, etc.) del denominador para no penalizar
    columnas con nulos legítimos. Devuelve (ratio, parseables_count, total_real_content).
    """
    if series is None or len(series) == 0:
        return 0.0, 0, 0

    missing_mask = is_missing_series(series)
    real_content = series[~missing_mask]
    total_real = len(real_content)
    if total_real == 0:
        return 0.0, 0, 0

    parsed = to_numeric_series(real_content)
    valid_count = int(parsed.notna().sum())
    ratio = valid_count / total_real
    return ratio, valid_count, total_real
