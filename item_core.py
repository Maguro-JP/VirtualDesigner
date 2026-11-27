"""VirtualDesigner の道具（アイテム）のロジック（標準ライブラリのみ）。

仕様フォーマット: ``virtualdesigner.item.v1``

アイテムの描画は ``draw_item`` が担当し、空間（space_core）からも使う。
描画はローカル座標（幅 100 × 高さ 100、下中央が原点、y は -100〜0）で返し、
置く側が transform で位置・大きさ・反転を決める。
"""

from __future__ import annotations

import random

from vd_common import (VDError, background_elements, escape, num, require_choice,
                       require_int, require_text, shade, validate_background,
                       validate_hex)

__all__ = ["FORMAT", "ITEMS", "ITEM_LABELS", "CATEGORIES", "DECORATIONS",
           "CATALOG", "validate_spec", "build_svg", "draw_item",
           "random_spec", "PRESETS"]

FORMAT = "virtualdesigner.item.v1"

# id -> (日本語ラベル, カテゴリ, 空間に置くときの既定の幅, 既定の高さ) ※空間は 512 幅基準
CATALOG = {
    "chair":     ("椅子", "家具", 64, 84),
    "desk":      ("机", "家具", 130, 78),
    "table":     ("テーブル", "家具", 110, 62),
    "bed":       ("ベッド", "家具", 180, 84),
    "bookshelf": ("本棚", "家具", 96, 150),
    "sofa":      ("ソファ", "家具", 150, 84),
    "shelf":     ("棚", "家具", 100, 56),
    "lamp":      ("ランプ", "生活道具", 44, 96),
    "clock":     ("時計", "生活道具", 56, 72),
    "book":      ("本", "生活道具", 52, 40),
    "cup":       ("カップ", "生活道具", 44, 40),
    "bag":       ("バッグ", "生活道具", 56, 62),
    "plant":     ("植物", "装飾", 56, 88),
    "sword":     ("剣", "装飾", 40, 110),
    "staff":     ("杖", "装飾", 36, 120),
    "key":       ("鍵", "装飾", 34, 84),
    "tv":        ("テレビ", "電子機器", 120, 84),
    "robot":     ("ロボット", "電子機器", 64, 104),
}
ITEMS = tuple(CATALOG)
ITEM_LABELS = {key: value[0] for key, value in CATALOG.items()}
CATEGORIES = ("家具", "生活道具", "装飾", "電子機器")
DECORATIONS = ("none", "dots", "stripes", "stars")

DEFAULTS = {
    "format": FORMAT,
    "name": "",
    "item": "chair",
    "main": "#b07a45",
    "accent": "#7c4a21",
    "decoration": "none",
    "bg_style": "solid",
    "background": "#fdf6ec",
    "background2": "#f3e2c7",
    "bg_pattern": "dots",
    "size": 512,
}


def validate_spec(data) -> dict:
    """仕様 dict を検証し、正規化した dict を返す。"""
    if not isinstance(data, dict):
        raise VDError("仕様はオブジェクトである必要があります")
    fmt = data.get("format", FORMAT)
    if not isinstance(fmt, str) or fmt != FORMAT:
        raise VDError(f"format は {FORMAT} である必要があります")
    spec = {
        "format": FORMAT,
        "name": require_text(data, "name", "", 30),
        "item": require_choice(data, "item", ITEMS, "chair"),
        "main": validate_hex(data.get("main", "#b07a45"), "main"),
        "accent": validate_hex(data.get("accent", "#7c4a21"), "accent"),
        "decoration": require_choice(data, "decoration", DECORATIONS, "none"),
        "size": require_int(data, "size", 512, 128, 2048),
    }
    spec.update(validate_background(data))
    return spec


# --- アイテムの描画（ローカル座標: x -50〜50, y -100〜0） ---------------------

def _decoration(kind: str, accent: str) -> list[str]:
    """本体の上に重ねる模様。範囲は本体のおおよその矩形にクリップする代わりに控えめに置く。"""
    if kind == "dots":
        return [f'<circle cx="{x}" cy="{y}" r="3" fill="{accent}" opacity="0.55"/>'
                for x, y in ((-24, -72), (0, -80), (24, -72), (-12, -52), (12, -52), (0, -32))]
    if kind == "stripes":
        return [f'<rect x="-30" y="{y}" width="60" height="5" fill="{accent}" opacity="0.5"/>'
                for y in (-78, -62, -46)]
    if kind == "stars":
        return [f'<path d="M {x} {y - 6} L {x + 1.8} {y - 1.8} L {x + 6} {y} L {x + 1.8} {y + 1.8} '
                f'L {x} {y + 6} L {x - 1.8} {y + 1.8} L {x - 6} {y} L {x - 1.8} {y - 1.8} Z" '
                f'fill="{accent}" opacity="0.7"/>'
                for x, y in ((-20, -66), (16, -76), (2, -40))]
    return []


def _chair(m, a):
    return [
        f'<rect x="-30" y="-96" width="10" height="52" fill="{m}"/>',
        f'<rect x="20" y="-96" width="10" height="52" fill="{m}"/>',
        f'<rect x="-30" y="-98" width="60" height="8" rx="3" fill="{a}"/>',
        f'<rect x="-30" y="-78" width="60" height="7" rx="3" fill="{a}"/>',
        f'<rect x="-34" y="-46" width="68" height="9" rx="3" fill="{m}"/>',
        f'<rect x="-28" y="-37" width="8" height="37" fill="{shade(m, 0.8)}"/>',
        f'<rect x="20" y="-37" width="8" height="37" fill="{shade(m, 0.8)}"/>',
    ]


def _desk(m, a):
    return [
        f'<rect x="-48" y="-74" width="96" height="9" rx="2" fill="{m}"/>',
        f'<rect x="-48" y="-65" width="10" height="65" fill="{shade(m, 0.8)}"/>',
        f'<rect x="38" y="-65" width="10" height="65" fill="{shade(m, 0.8)}"/>',
        f'<rect x="8" y="-65" width="30" height="22" fill="{shade(m, 0.9)}"/>',
        f'<rect x="12" y="-58" width="22" height="3" fill="{a}"/>',
        f'<circle cx="23" cy="-50" r="2.4" fill="{a}"/>',
    ]


def _table(m, a):
    return [
        f'<ellipse cx="0" cy="-62" rx="48" ry="10" fill="{m}"/>',
        f'<rect x="-48" y="-64" width="96" height="5" fill="{shade(m, 1.08)}"/>',
        f'<rect x="-5" y="-60" width="10" height="46" fill="{shade(m, 0.8)}"/>',
        f'<ellipse cx="0" cy="-12" rx="22" ry="5" fill="{shade(m, 0.8)}"/>',
        f'<circle cx="0" cy="-70" r="5" fill="{a}"/>',
    ]


def _bed(m, a):
    return [
        f'<rect x="-48" y="-78" width="10" height="62" rx="3" fill="{shade(m, 0.8)}"/>',
        f'<rect x="-48" y="-42" width="96" height="26" rx="4" fill="{m}"/>',
        f'<rect x="-44" y="-58" width="30" height="18" rx="5" fill="#ffffff"/>',
        f'<path d="M -12 -44 L 48 -44 L 48 -18 L -12 -18 Z" fill="{a}"/>',
        f'<rect x="-48" y="-16" width="96" height="5" fill="{shade(m, 0.75)}"/>',
    ]


def _bookshelf(m, a):
    spine_colors = [a, shade(a, 1.25), shade(m, 1.2), "#c9563c", "#3c6ec9", "#3f9e4d"]
    parts = [
        f'<rect x="-40" y="-98" width="80" height="98" rx="3" fill="{m}"/>',
        f'<rect x="-34" y="-92" width="68" height="86" fill="{shade(m, 0.72)}"/>',
    ]
    for row, top in enumerate((-92, -62, -32)):
        parts.append(f'<rect x="-34" y="{top + 24}" width="68" height="4" fill="{m}"/>')
        x = -31
        i = 0
        while x < 22:
            w = 6 + ((row * 3 + i) % 3) * 2
            color = spine_colors[(row * 2 + i) % len(spine_colors)]
            parts.append(f'<rect x="{x}" y="{top + 5}" width="{w}" height="19" fill="{color}"/>')
            x += w + 2
            i += 1
    return parts


def _sofa(m, a):
    return [
        f'<rect x="-46" y="-72" width="92" height="34" rx="9" fill="{shade(m, 0.85)}"/>',
        f'<rect x="-48" y="-52" width="96" height="36" rx="9" fill="{m}"/>',
        f'<rect x="-48" y="-58" width="14" height="44" rx="6" fill="{shade(m, 0.9)}"/>',
        f'<rect x="34" y="-58" width="14" height="44" rx="6" fill="{shade(m, 0.9)}"/>',
        f'<rect x="-30" y="-50" width="28" height="20" rx="4" fill="{a}"/>',
        f'<rect x="2" y="-50" width="28" height="20" rx="4" fill="{a}"/>',
        f'<rect x="-40" y="-14" width="8" height="10" fill="{shade(m, 0.7)}"/>',
        f'<rect x="32" y="-14" width="8" height="10" fill="{shade(m, 0.7)}"/>',
    ]


def _shelf(m, a):
    return [
        f'<rect x="-46" y="-58" width="92" height="7" fill="{m}"/>',
        f'<rect x="-46" y="-26" width="92" height="7" fill="{m}"/>',
        f'<path d="M -34 -51 L -26 -51 L -34 -38 Z" fill="{shade(m, 0.75)}"/>',
        f'<path d="M 34 -51 L 26 -51 L 34 -38 Z" fill="{shade(m, 0.75)}"/>',
        f'<path d="M -34 -19 L -26 -19 L -34 -6 Z" fill="{shade(m, 0.75)}"/>',
        f'<path d="M 34 -19 L 26 -19 L 34 -6 Z" fill="{shade(m, 0.75)}"/>',
        f'<rect x="-38" y="-76" width="12" height="18" fill="{a}"/>',
        f'<rect x="-22" y="-72" width="10" height="14" fill="{shade(a, 1.3)}"/>',
        f'<rect x="14" y="-40" width="18" height="14" rx="2" fill="{a}"/>',
        f'<circle cx="-8" cy="-66" r="7" fill="{shade(a, 0.8)}"/>',
    ]


def _lamp(m, a):
    return [
        f'<path d="M -20 -100 L 20 -100 L 30 -68 L -30 -68 Z" fill="{a}"/>',
        f'<rect x="-3" y="-68" width="6" height="52" fill="{shade(m, 0.8)}"/>',
        f'<ellipse cx="0" cy="-14" rx="20" ry="5" fill="{m}"/>',
        f'<circle cx="0" cy="-84" r="6" fill="#ffe9a8"/>',
    ]


def _clock(m, a):
    return [
        f'<rect x="-24" y="-98" width="48" height="62" rx="6" fill="{m}"/>',
        f'<circle cx="0" cy="-67" r="22" fill="#ffffff"/>',
        f'<circle cx="0" cy="-67" r="22" fill="none" stroke="{a}" stroke-width="3"/>',
        f'<path d="M 0 -67 L 0 -80 M 0 -67 L 10 -62" stroke="#333333" stroke-width="3" stroke-linecap="round"/>',
        f'<rect x="-14" y="-32" width="8" height="26" fill="{shade(m, 0.8)}"/>',
        f'<rect x="6" y="-32" width="8" height="26" fill="{shade(m, 0.8)}"/>',
        f'<path d="M -14 -6 L -20 0 M 14 -6 L 20 0" stroke="{shade(m, 0.8)}" stroke-width="4" stroke-linecap="round"/>',
    ]


def _book(m, a):
    return [
        f'<rect x="-34" y="-26" width="58" height="14" rx="2" fill="{a}"/>',
        f'<rect x="-34" y="-26" width="6" height="14" fill="{shade(a, 0.75)}"/>',
        f'<rect x="-28" y="-44" width="62" height="15" rx="2" fill="{m}"/>',
        f'<rect x="-28" y="-44" width="6" height="15" fill="{shade(m, 0.75)}"/>',
        f'<rect x="-20" y="-38" width="26" height="3" fill="#ffffff" opacity="0.75"/>',
        f'<rect x="-26" y="-62" width="44" height="15" rx="2" fill="{shade(m, 1.25)}"/>',
        f'<rect x="-26" y="-62" width="6" height="15" fill="{shade(m, 0.95)}"/>',
    ]


def _cup(m, a):
    return [
        f'<path d="M -22 -46 L 18 -46 L 14 -12 L -18 -12 Z" fill="{m}"/>',
        f'<path d="M 18 -42 C 32 -42 32 -20 16 -18" fill="none" stroke="{m}" stroke-width="6"/>',
        f'<rect x="-22" y="-40" width="40" height="6" fill="{a}"/>',
        f'<ellipse cx="-2" cy="-8" rx="26" ry="4" fill="{shade(m, 0.8)}"/>',
        f'<path d="M -8 -56 C -12 -64 -4 -68 -8 -76 M 4 -56 C 0 -64 8 -68 4 -76" stroke="{a}" stroke-width="3" fill="none" stroke-linecap="round" opacity="0.7"/>',
    ]


def _bag(m, a):
    return [
        f'<path d="M -14 -58 C -14 -76 14 -76 14 -58" fill="none" stroke="{shade(m, 0.75)}" stroke-width="6"/>',
        f'<rect x="-28" y="-60" width="56" height="52" rx="8" fill="{m}"/>',
        f'<path d="M -28 -44 L 28 -44 L 28 -34 L -28 -34 Z" fill="{a}"/>',
        f'<rect x="-6" y="-42" width="12" height="10" rx="2" fill="{shade(a, 0.8)}"/>',
    ]


def _plant(m, a):
    leaves = []
    for dx, dy, r in ((-14, -66, 13), (0, -78, 15), (14, -66, 13), (-7, -56, 11), (8, -57, 11)):
        leaves.append(f'<ellipse cx="{dx}" cy="{dy}" rx="{r}" ry="{r + 7}" fill="{m}"/>')
    return leaves + [
        f'<path d="M 0 -30 L 0 -58 M -12 -34 L -4 -52 M 12 -34 L 4 -52" stroke="{shade(m, 0.75)}" stroke-width="3.4" fill="none"/>',
        f'<path d="M -18 -34 L 18 -34 L 13 -6 L -13 -6 Z" fill="{a}"/>',
        f'<rect x="-18" y="-38" width="36" height="6" rx="2" fill="{shade(a, 0.85)}"/>',
    ]


def _sword(m, a):
    return [
        f'<path d="M -4 -100 L 4 -100 L 3 -34 L 0 -26 L -3 -34 Z" fill="{m}"/>',
        f'<path d="M 0 -100 L 3 -34 L 0 -26 Z" fill="{shade(m, 1.18)}"/>',
        f'<rect x="-17" y="-32" width="34" height="6" rx="3" fill="{a}"/>',
        f'<rect x="-3.4" y="-26" width="6.8" height="18" rx="3" fill="{shade(a, 0.6)}"/>',
        f'<circle cx="0" cy="-4" r="5" fill="{a}"/>',
    ]


def _staff(m, a):
    return [
        f'<rect x="-3" y="-72" width="6" height="66" rx="3" fill="{m}"/>',
        f'<circle cx="0" cy="-84" r="13" fill="{a}"/>',
        f'<circle cx="0" cy="-84" r="18" fill="none" stroke="{shade(a, 0.8)}" stroke-width="2.6"/>',
        f'<circle cx="-4" cy="-88" r="4" fill="#ffffff" opacity="0.65"/>',
        f'<path d="M -10 -66 L 0 -74 L 10 -66" stroke="{shade(a, 0.8)}" stroke-width="2.6" fill="none"/>',
    ]


def _key(m, a):
    return [
        f'<circle cx="0" cy="-82" r="13" fill="none" stroke="{m}" stroke-width="6"/>',
        f'<path d="M 8 -72 L 26 -50" stroke="{m}" stroke-width="6" stroke-linecap="round"/>',
        f'<path d="M 20 -56 L 30 -60 M 25 -49 L 34 -52" stroke="{m}" stroke-width="5" stroke-linecap="round"/>',
        f'<circle cx="0" cy="-82" r="4" fill="{a}"/>',
    ]


def _tv(m, a):
    return [
        f'<rect x="-46" y="-88" width="92" height="58" rx="5" fill="#22242c"/>',
        f'<rect x="-41" y="-83" width="82" height="48" rx="3" fill="{a}"/>',
        f'<path d="M -41 -83 L -8 -83 L -28 -35 L -41 -35 Z" fill="#ffffff" opacity="0.16"/>',
        f'<rect x="-3" y="-30" width="6" height="12" fill="#22242c"/>',
        f'<rect x="-18" y="-17" width="36" height="4" rx="2" fill="#22242c"/>',
        f'<circle cx="40" cy="-33" r="2" fill="{m}"/>',
    ]


def _robot(m, a):
    return [
        f'<path d="M 0 -98 L 0 -88" stroke="{shade(m, 0.8)}" stroke-width="3"/>',
        f'<circle cx="0" cy="-99" r="3.4" fill="{a}"/>',
        f'<rect x="-22" y="-88" width="44" height="32" rx="8" fill="{m}"/>',
        f'<circle cx="-9" cy="-72" r="4.4" fill="{a}"/>',
        f'<circle cx="9" cy="-72" r="4.4" fill="{a}"/>',
        f'<rect x="-9" y="-62" width="18" height="3.4" rx="1.7" fill="{shade(m, 0.7)}"/>',
        f'<rect x="-18" y="-52" width="36" height="30" rx="6" fill="{shade(m, 0.92)}"/>',
        f'<rect x="-10" y="-46" width="20" height="12" rx="2" fill="{a}"/>',
        f'<path d="M -18 -48 L -28 -34 M 18 -48 L 28 -34" stroke="{shade(m, 0.8)}" stroke-width="6" stroke-linecap="round"/>',
        f'<path d="M -9 -22 L -9 -8 M 9 -22 L 9 -8" stroke="{shade(m, 0.8)}" stroke-width="6" stroke-linecap="round"/>',
    ]


_DRAWERS = {
    "chair": _chair, "desk": _desk, "table": _table, "bed": _bed,
    "bookshelf": _bookshelf, "sofa": _sofa, "shelf": _shelf, "lamp": _lamp,
    "clock": _clock, "book": _book, "cup": _cup, "bag": _bag,
    "plant": _plant, "sword": _sword, "staff": _staff, "key": _key,
    "tv": _tv, "robot": _robot,
}


def draw_item(item: str, main: str, accent: str, decoration: str = "none") -> list[str]:
    """アイテムをローカル座標（幅100×高さ100、下中央が原点）の要素列で返す。"""
    if item not in _DRAWERS:
        raise VDError(f"item が不明です: {item!r}")
    parts = list(_DRAWERS[item](main, accent))
    parts.extend(_decoration(decoration, accent))
    return parts


def item_group(item: str, main: str, accent: str, x: float, baseline: float,
               width: float, height: float, flip: bool = False,
               decoration: str = "none") -> str:
    """アイテムを (x, baseline) に幅・高さ・反転を指定して置く <g> を返す。"""
    sx = width / 100.0 * (-1 if flip else 1)
    sy = height / 100.0
    body = "".join(draw_item(item, main, accent, decoration))
    return (f'<g transform="translate({num(x)} {num(baseline)}) '
            f'scale({num(sx)} {num(sy)})">{body}</g>')


def build_svg(spec) -> str:
    """仕様から単体の道具の SVG を生成する。"""
    s = validate_spec(spec)
    size = s["size"]
    defs, bg = background_elements(s["bg_style"], s["bg_pattern"], s["background"],
                                   s["background2"], 512, 512, "item")
    _, _, def_w, def_h = CATALOG[s["item"]]
    scale = min(300 / def_w, 340 / def_h)
    w, h = def_w * scale * 1.6, def_h * scale * 1.6
    w = min(w, 360)
    h = min(h, 380)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 512 512" role="img">',
        defs, bg,
        f'<ellipse cx="256" cy="428" rx="{num(w * 0.42)}" ry="12" fill="#000000" opacity="0.10"/>',
        item_group(s["item"], s["main"], s["accent"], 256, 424, w, h, False, s["decoration"]),
    ]
    if s["name"]:
        parts.append(
            f'<g><rect x="156" y="452" width="200" height="34" rx="17" fill="#000000" opacity="0.45"/>'
            f'<text x="256" y="470" text-anchor="middle" dominant-baseline="central" '
            f'font-family="system-ui, sans-serif" font-size="19" fill="#ffffff">'
            f'{escape(s["name"])}</text></g>')
    parts.append("</svg>")
    return "".join(parts)


# --- プリセットとランダム -----------------------------------------------------

PRESETS = [
    {"name": "木の椅子", "spec": {"item": "chair", "main": "#b07a45", "accent": "#7c4a21"}},
    {"name": "真鍮のランプ", "spec": {"item": "lamp", "main": "#8a6d3b", "accent": "#d9a441",
                                      "background": "#2e3440", "background2": "#4c566a", "bg_style": "gradient"}},
    {"name": "魔法の杖", "spec": {"item": "staff", "main": "#6b4423", "accent": "#7d4fc9",
                                   "decoration": "stars", "background": "#1f2440",
                                   "background2": "#3b2f5e", "bg_style": "gradient"}},
    {"name": "騎士の剣", "spec": {"item": "sword", "main": "#c8ccd4", "accent": "#b08d2f"}},
    {"name": "相棒ロボット", "spec": {"item": "robot", "main": "#7f9bb3", "accent": "#e2543e",
                                       "background": "#eaf2f8"}},
    {"name": "観葉植物", "spec": {"item": "plant", "main": "#3f9e4d", "accent": "#b5542c",
                                   "background": "#f2f7e8"}},
    {"name": "真鍮の鍵", "spec": {"item": "key", "main": "#c9a227", "accent": "#7c5e10",
                                   "decoration": "dots", "background": "#f7f1de"}},
]

_ITEM_COLOR_PAIRS = [
    ("#b07a45", "#7c4a21"), ("#8a6d3b", "#d9a441"), ("#7f9bb3", "#e2543e"),
    ("#c8ccd4", "#b08d2f"), ("#3f9e4d", "#b5542c"), ("#5b7fa6", "#2f4a6b"),
    ("#a65a7a", "#6e3550"), ("#4a4a52", "#c9a227"),
]


def random_spec(seed) -> dict:
    """seed から決定的にランダムな道具の仕様を作る。必ず validate_spec を通る。"""
    rng = random.Random(seed)
    main, accent = rng.choice(_ITEM_COLOR_PAIRS)
    spec = {
        "format": FORMAT,
        "name": "",
        "item": rng.choice(ITEMS),
        "main": main,
        "accent": accent,
        "decoration": rng.choice(DECORATIONS),
        "bg_style": rng.choice(("solid", "gradient", "pattern")),
        "background": rng.choice(("#fdf6ec", "#eaf2f8", "#f2f7e8", "#f7f1de", "#eef0f7")),
        "background2": rng.choice(("#f3e2c7", "#c9dcee", "#d8ecc4", "#e8d9a8", "#d4d8ea")),
        "bg_pattern": rng.choice(("dots", "stripes", "check")),
        "size": 512,
    }
    return validate_spec(spec)
