"""
Lógica compartida de capitalización inteligente (smart title case).

Fuente única de verdad usada por:
- NormalizeCaseTransformation (text_ops)
- SplitColumnTransformation (split_ops)
- ScriptGeneratorService (que emite un equivalente exacto en el script reproducible)

Reglas deterministas por palabra:
1. Acrónimos de negocio registrados (SA, SLU, KPI, HR...) → siempre en mayúsculas,
   sea cual sea su casing de entrada (hr → HR).
2. Compuestos con guion cuyas partes son todas alfabéticas (HR-California, DevOps-New,
   HR-New) → casing inteligente por cada parte, NUNCA .title() crudo ni upper total.
3. Tokens con forma de código (PED-201, ABC_123: contienen dígitos o guion bajo)
   → siempre en mayúsculas.
4. Tokens camelCase (DevOps, PowerBI, McDonald) → se preservan tal cual.
5. Resto (incluidos nombres propios gritados tipo LUIS, PARDO) → capitalize().
"""

import re
from typing import Any

import pandas as pd

BUSINESS_ACRONYMS = {
    "SA",
    "S.A.",
    "SL",
    "S.L.",
    "SLU",
    "S.L.U.",
    "CIF",
    "NIF",
    "DNI",
    "IVA",
    "ID",
    "KPI",
    "SLA",
    "AHT",
    "CRM",
    "ERP",
    "USA",
    "UE",
    "IA",
    "AI",
    "HR",
}

CODE_TOKEN_RE = re.compile(r"^[A-Za-z0-9]{2,6}[-_][A-Za-z0-9]{1,}$")
CAMEL_TOKEN_RE = re.compile(r"^[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+$")


def _smart_case_atomic(word: str) -> str:
    """Casing de una palabra simple (sin guiones): siglas registradas, camelCase o capitalize."""
    upper = word.upper()
    if upper in BUSINESS_ACRONYMS:
        return upper
    if CAMEL_TOKEN_RE.match(word):
        return word
    return word.capitalize()


def smart_case_word(word: str) -> str:
    """Aplica casing inteligente a una palabra suelta, incluidos compuestos con guion."""
    if not word:
        return word
    upper = word.upper()
    if upper in BUSINESS_ACRONYMS:
        return upper
    # Compuesto alfabético con guion (HR-California, DevOps-New) → casing por parte.
    # Los códigos con dígitos (PED-201) no entran aquí: sus partes no son isalpha().
    if "-" in word:
        parts = word.split("-")
        if all(len(p) >= 2 and p.isalpha() for p in parts):
            return "-".join(_smart_case_atomic(p) for p in parts)
    if CODE_TOKEN_RE.match(word):
        return upper
    return _smart_case_atomic(word)


def smart_case_token(token: str) -> str:
    """Alias de compatibilidad: aplica casing a un token (posible compuesto con guion)."""
    return smart_case_word(token)


def smart_title_text(value: Any) -> Any:
    """
    Title Case inteligente sobre un valor completo; preserva NaN/None y vacío (tras strip).
    """
    if value is None or pd.isna(value):
        return value
    stripped = str(value).strip()
    if not stripped:
        return stripped
    return " ".join(smart_case_word(w) for w in stripped.split(" "))
