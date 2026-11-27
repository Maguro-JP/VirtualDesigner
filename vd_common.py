"""VirtualDesigner の共通部品（標準ライブラリのみ）。

3 つの対象（アバター・空間・道具）で共有する、色の検証・パレット・
背景の生成・数値整形などを置く。入出力やネットワークは行わない。
"""

from __future__ import annotations

import re
from xml.sax.saxutils import escape

__all__ = [
    "VDError", "escape", "num", "validate_hex", "require_choice",
    "require_text", "require_int", "shade", "background_elements",
    "SKIN_TONES", "HAIR_COLORS", "EYE_COLORS", "BG_STYLES", "BG_PATTERNS",
]

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class VDError(ValueError):
    """仕様が不正な場合に送出されるエラー。"""


# --- パレット（UI のスウォッチとランダム生成で使う） -----------------------

SKIN_TONES = (
    "#ffdfc4", "#ffd7ae", "#f5c99b", "#eebd8f", "#d9a066",
    "#b97a56", "#8d5524", "#5c3836", "#a8e6a1", "#a9c6e8",
)
HAIR_COLORS = (
    "#2b2b2b", "#6b4423", "#a9713a", "#e8c872", "#e07b2a",
    "#b5461f", "#f2a0c0", "#4a6fd4", "#4caf7d", "#7d4fc9", "#cfd4d9",
)
EYE_COLORS = (
    "#222222", "#5b3a1e", "#a06a2c", "#3a6fd8",
    "#3f9e4d", "#7a7f85", "#c03a3a", "#7d4fc9",
)

BG_STYLES = ("solid", "gradient", "pattern")
BG_PATTERNS = ("dots", "stripes", "check")


# --- 検証ヘルパー -----------------------------------------------------------

def _has_control_chars(value: str) -> bool:
    return any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value)


def validate_hex(value: object, key: str) -> str:
    """#RRGGBB を検証し、小文字に正規化して返す。"""
    if not isinstance(value, str) or not _HEX_RE.match(value):
        raise VDError(f"{key} は #RRGGBB 形式である必要があります: {value!r}")
    return value.lower()


def require_choice(data: dict, key: str, choices: tuple, default: str) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        raise VDError(f"{key} は文字列である必要があります")
    if value not in choices:
        raise VDError(f"{key} が不明です: {value!r}")
    return value


def require_text(data: dict, key: str, default: str = "", limit: int = 30) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        raise VDError(f"{key} は文字列である必要があります")
    value = value.strip()
    if len(value) > limit:
        raise VDError(f"{key} は {limit} 文字以内である必要があります")
    if _has_control_chars(value):
        raise VDError(f"{key} に制御文字を含めることはできません")
    return value


def require_int(data: dict, key: str, default: int, low: int, high: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise VDError(f"{key} は整数である必要があります")
    if value < low or value > high:
        raise VDError(f"{key} は {low} から {high} の範囲である必要があります")
    return value


def validate_background(data: dict) -> dict:
    """背景まわりの共通項目（bg_style / background / background2 / bg_pattern）。"""
    style = require_choice(data, "bg_style", BG_STYLES, "solid")
    background = validate_hex(data.get("background", "#ffffff"), "background")
    background2 = validate_hex(data.get("background2", "#dbeafe"), "background2")
    pattern = require_choice(data, "bg_pattern", BG_PATTERNS, "dots")
    return {"bg_style": style, "background": background,
            "background2": background2, "bg_pattern": pattern}


# --- 色の加工 ---------------------------------------------------------------

def shade(hex_color: str, factor: float) -> str:
    """色を factor 倍に暗く（<1）／明るく（>1）する。"""
    h = hex_color.lstrip("#")
    out = []
    for i in (0, 2, 4):
        v = int(h[i:i + 2], 16) * factor
        out.append(max(0, min(255, round(v))))
    return "#{:02x}{:02x}{:02x}".format(*out)


# --- SVG の部品 -------------------------------------------------------------

def num(value: float) -> str:
    """SVG 用の数値を短く整形する（整数は整数のまま）。"""
    rounded = round(float(value), 2)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.2f}".rstrip("0").rstrip(".")


def background_elements(style: str, pattern: str, c1: str, c2: str,
                        w: float, h: float, prefix: str) -> tuple[str, str]:
    """背景の (defs, rect) を返す。style は solid / gradient / pattern。"""
    if style == "gradient":
        defs = (f'<defs><linearGradient id="{prefix}-grad" x1="0" y1="0" x2="0" y2="1">'
                f'<stop offset="0" stop-color="{c1}"/>'
                f'<stop offset="1" stop-color="{c2}"/></linearGradient></defs>')
        return defs, f'<rect width="{num(w)}" height="{num(h)}" fill="url(#{prefix}-grad)"/>'
    if style == "pattern":
        if pattern == "stripes":
            motif = (f'<rect width="24" height="12" fill="{c2}"/>')
        elif pattern == "check":
            motif = (f'<rect width="12" height="12" fill="{c2}"/>'
                     f'<rect x="12" y="12" width="12" height="12" fill="{c2}"/>')
        else:  # dots
            motif = f'<circle cx="6" cy="6" r="3" fill="{c2}"/><circle cx="18" cy="18" r="3" fill="{c2}"/>'
        defs = (f'<defs><pattern id="{prefix}-pat" width="24" height="24" '
                f'patternUnits="userSpaceOnUse">{motif}</pattern></defs>')
        rect = (f'<rect width="{num(w)}" height="{num(h)}" fill="{c1}"/>'
                f'<rect width="{num(w)}" height="{num(h)}" fill="url(#{prefix}-pat)"/>')
        return defs, rect
    return "", f'<rect width="{num(w)}" height="{num(h)}" fill="{c1}"/>'
