"""
Validación determinista de contraste WCAG 2.x.

Implementa la fórmula oficial de luminancia relativa (sRGB linealizado) y las
ratios de contraste AA/AAA para texto normal, texto grande y componentes de UI.
Nunca se delega esta validación a un LLM: es matemática pura y reproducible.
"""

import re
from typing import Dict, Optional, Tuple

_HEX_RE = re.compile(r"^#?[0-9a-fA-F]{6}$")

# Umbrales WCAG 2.x
AA_NORMAL_TEXT = 4.5
AA_LARGE_TEXT = 3.0
AA_UI_COMPONENT = 3.0
_AA_NORMAL = AA_NORMAL_TEXT
_AAA_NORMAL = 7.0
_AA_LARGE = AA_LARGE_TEXT
_AAA_LARGE = 4.5
_MIN_UI_COMPONENT = AA_UI_COMPONENT

# Coeficientes sRGB → luminancia relativa (fórmula WCAG 2.x)
_R_COEF = 0.2126
_G_COEF = 0.7152
_B_COEF = 0.0722


def is_valid_hex(color: str) -> bool:
    """Comprueba si una cadena es un color hexadecimal #RRGGBB válido."""
    return bool(_HEX_RE.match(str(color).strip()))


def hex_to_rgb(hex_color: str) -> Tuple[float, float, float]:
    """Convierte un color #RRGGBB (con o sin '#') a componentes RGB 0-255."""
    value = str(hex_color).strip().lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Color hexadecimal no válido: {hex_color}")
    try:
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError as exc:
        raise ValueError(f"Color hexadecimal no válido: {hex_color}") from exc


def _linearize(channel_255: float) -> float:
    """Linealiza un canal sRGB 0-255 según la fórmula WCAG."""
    c = channel_255 / 255.0
    if c <= 0.03928:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    """Luminancia relativa WCAG de un color #RRGGBB."""
    r, g, b = hex_to_rgb(hex_color)
    return _R_COEF * _linearize(r) + _G_COEF * _linearize(g) + _B_COEF * _linearize(b)


def contrast_ratio(color_a: str, color_b: str, precision: int = 2) -> float:
    """Ratio de contraste entre dos colores (orden independiente), redondeada a 2 decimales."""
    lum_a = relative_luminance(color_a)
    lum_b = relative_luminance(color_b)
    lighter, darker = (lum_a, lum_b) if lum_a >= lum_b else (lum_b, lum_a)
    ratio = (lighter + 0.05) / (darker + 0.05)
    return round(ratio, precision)


def wcag_check(ratio: float, large_text: bool = False, ui_component: bool = False) -> Dict[str, bool]:
    """
    Evalúa una ratio de contraste contra los umbrales WCAG AA/AAA.

    - Texto normal: AA ≥ 4.5, AAA ≥ 7.0.
    - Texto grande (≥18pt o ≥14pt bold): AA ≥ 3.0, AAA ≥ 4.5.
    - Componentes de UI (bordes, iconos, controles): ≥ 3.0.
    """
    if ui_component:
        return {"aa": ratio >= _MIN_UI_COMPONENT, "aaa": ratio >= _AAA_NORMAL}
    if large_text:
        return {"aa": ratio >= _AA_LARGE, "aaa": ratio >= _AAA_LARGE}
    return {"aa": ratio >= _AA_NORMAL, "aaa": ratio >= _AAA_NORMAL}


def _clip_channel(value: float) -> int:
    return int(max(0, min(255, round(value))))


def adjust_lightness(hex_color: str, direction: str, factor: float = 0.06) -> str:
    """
    Aclara ('lighter') u oscurece ('darker') un color de forma determinista.

    Se aplica un factor multiplicativo por canal (L = c + (255-c)*f para aclarar,
    D = c * (1-f) para oscurecer), de modo que el ajuste es estable y repetible.
    """
    r, g, b = hex_to_rgb(hex_color)
    if direction == "to_darker":
        out = (_clip_channel(c * (1.0 - factor)) for c in (r, g, b))
    elif direction == "to_lighter":
        out = (_clip_channel(c + (255.0 - c) * factor) for c in (r, g, b))
    else:
        raise ValueError(f"Dirección no válida: {direction}")
    return "#{:02X}{:02X}{:02X}".format(*out)


def ensure_contrast(
    fg: str,
    bg: str,
    target_ratio: float,
    direction: str = "to_darker",
    max_steps: int = 60,
) -> Optional[str]:
    """
    Ajusta el color frontal (pasos deterministas) hasta alcanzar la ratio objetivo
    contra el fondo, o devuelve None si no se alcanza en max_steps iteraciones.

    direction puede ser 'to_darker' (texto sobre fondo claro) o 'to_lighter'
    (texto sobre fondo oscuro).
    """
    if not is_valid_hex(fg) or not is_valid_hex(bg):
        return None
    candidate = fg
    for _ in range(max_steps):
        ratio = contrast_ratio(candidate, bg, precision=3)
        if ratio >= target_ratio * 0.999:  # margen de redondeo
            return candidate
        candidate = adjust_lightness(candidate, direction)
    return None


def describe_text_contrast(fg: str, bg: str, large_text: bool = False) -> Dict[str, object]:
    """
    Devuelve el resumen completo (ratio, AA, AAA) para un par texto/fondo.
    Lanza ValueError si alguno de los colores no es un hexadecimal válido.
    """
    if not is_valid_hex(fg) or not is_valid_hex(bg):
        raise ValueError(f"Colores no válidos para contraste: {fg} sobre {bg}")
    ratio = contrast_ratio(fg, bg)
    levels = wcag_check(ratio, large_text=large_text)
    return {
        "foreground": fg.upper(),
        "background": bg.upper(),
        "contrast_ratio": ratio,
        "aa": levels["aa"],
        "aaa": levels["aaa"],
        "large_text": large_text,
    }
