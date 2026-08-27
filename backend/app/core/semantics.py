"""
Helpers semanticos compartidos — evita duplicacion de logica de deteccion
de columnas de porcentaje/score en ETL, Quality y Profiling.
"""
import pandas as pd
from typing import Any

_PCT_SUFFIXES = ("_pct", "_percentage", "_porcentaje", "_rate", "_ratio", "_tasa", "_score")
_PCT_PREFIXES = ("pct_", "porcentaje_", "tasa_", "ratio_", "score_")
_PCT_EXACT = {"%", "pct", "porcentaje", "ctr", "cvr", "roi", "score", "score_calidad", "tasa_conversion", "conversion_rate", "churn_rate", "descuento_pct", "incidencias_pct"}

def is_percentage_or_score_column(col_name: str, raw_series: Any = None) -> bool:
    if raw_series is not None:
        try:
            if any("%" in str(x) for x in pd.Series(raw_series).dropna()):
                return True
        except Exception:
            pass
    col_lower = col_name.lower().strip()
    return col_lower.endswith(_PCT_SUFFIXES) or col_lower.startswith(_PCT_PREFIXES) or col_lower in _PCT_EXACT
