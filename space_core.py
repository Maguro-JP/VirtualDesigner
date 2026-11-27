"""VirtualDesigner の空間（部屋）のロジック（標準ライブラリのみ）。

仕様フォーマット: ``virtualdesigner.space.v1``

壁・床・窓・ドア・照明と、家具（item_core のカタログ）の配置を組み合わせて
部屋の SVG を描く。描画は 512×384 の基準座標で組み立てる（決定的な出力）。
"""

from __future__ import annotations

import random

from vd_common import (VDError, escape, num, require_choice, require_int,
                       require_text, shade, validate_hex)
from item_core import CATALOG, ITEMS, item_group

__all__ = ["FORMAT", "WALL_PATTERNS", "FLOOR_PATTERNS", "WINDOWS", "DOORS",
           "LIGHTINGS", "validate_spec", "build_svg", "random_spec", "PRESETS"]

FORMAT = "virtualdesigner.space.v1"

WALL_PATTERNS = ("none", "dots", "stripes", "check", "wainscot")
FLOOR_PATTERNS = ("plain", "wood", "tile", "carpet")
WINDOWS = ("none", "left", "center", "right")
DOORS = ("none", "left", "right")
LIGHTINGS = ("bright", "warm", "dim", "night")

WALL_H = 250        # 壁と床の境目
BASE_W, BASE_H = 512, 384

DEFAULTS = {
    "format": FORMAT,
    "name": "",
    "wall_color": "#f3e9d7",
    "wall_pattern": "none",
    "floor_color": "#b07a45",
    "floor_pattern": "wood",
    "window": "center",
    "door": "none",
    "lighting": "bright",
    "items": [],
    "size": 512,
}


def _validate_placement(data, index: int) -> dict:
    if not isinstance(data, dict):
        raise VDError(f"items[{index}] はオブジェクトである必要があります")
    item = data.get("item")
    if item not in ITEMS:
        raise VDError(f"items[{index}].item が不明です: {item!r}")
    x = data.get("x", 50)
    y = data.get("y", 50)
    scale = data.get("scale", 1.0)
    for key, value, low, high in (("x", x, 0, 100), ("y", y, 0, 100), ("scale", scale, 0.3, 3.0)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise VDError(f"items[{index}].{key} は数値である必要があります")
        if value < low or value > high:
            raise VDError(f"items[{index}].{key} は {low} から {high} の範囲である必要があります")
    flip = data.get("flip", False)
    if not isinstance(flip, bool):
        raise VDError(f"items[{index}].flip は真偽値である必要があります")
    _, _, def_w, def_h = CATALOG[item]
    return {
        "item": item,
        "x": x, "y": y, "scale": scale, "flip": flip,
        "main": validate_hex(data.get("main", "#b07a45"), f"items[{index}].main"),
        "accent": validate_hex(data.get("accent", "#7c4a21"), f"items[{index}].accent"),
        "width": def_w, "height": def_h,
    }


def validate_spec(data) -> dict:
    """仕様 dict を検証し、正規化した dict を返す。

    返り値の items には、カタログの既定サイズ（width / height）も付く。
    """
    if not isinstance(data, dict):
        raise VDError("仕様はオブジェクトである必要があります")
    fmt = data.get("format", FORMAT)
    if not isinstance(fmt, str) or fmt != FORMAT:
        raise VDError(f"format は {FORMAT} である必要があります")
    raw_items = data.get("items", [])
    if not isinstance(raw_items, list):
        raise VDError("items は配列である必要があります")
    if len(raw_items) > 30:
        raise VDError("items は 30 個までです")
    return {
        "format": FORMAT,
        "name": require_text(data, "name", "", 30),
        "wall_color": validate_hex(data.get("wall_color", "#f3e9d7"), "wall_color"),
        "wall_pattern": require_choice(data, "wall_pattern", WALL_PATTERNS, "none"),
        "floor_color": validate_hex(data.get("floor_color", "#b07a45"), "floor_color"),
        "floor_pattern": require_choice(data, "floor_pattern", FLOOR_PATTERNS, "wood"),
        "window": require_choice(data, "window", WINDOWS, "center"),
        "door": require_choice(data, "door", DOORS, "none"),
        "lighting": require_choice(data, "lighting", LIGHTINGS, "bright"),
        "items": [_validate_placement(p, i) for i, p in enumerate(raw_items)],
        "size": require_int(data, "size", 512, 128, 2048),
    }


# --- 部屋の部品 ---------------------------------------------------------------

def _wall(s) -> list[str]:
    color = s["wall_color"]
    parts = [f'<rect width="512" height="{WALL_H}" fill="{color}"/>']
    pattern = s["wall_pattern"]
    if pattern == "dots":
        for yy in range(30, WALL_H, 44):
            for xx in range(28, 512, 44):
                parts.append(f'<circle cx="{xx}" cy="{yy}" r="3.4" fill="{shade(color, 0.88)}"/>')
    elif pattern == "stripes":
        for xx in range(16, 512, 36):
            parts.append(f'<rect x="{xx}" y="0" width="12" height="{WALL_H}" fill="{shade(color, 0.93)}"/>')
    elif pattern == "check":
        for yy in range(0, WALL_H, 36):
            for xx in range(0, 512, 36):
                if (xx // 36 + yy // 36) % 2 == 0:
                    parts.append(f'<rect x="{xx}" y="{yy}" width="36" height="36" fill="{shade(color, 0.94)}"/>')
    elif pattern == "wainscot":
        parts.append(f'<rect y="168" width="512" height="82" fill="{shade(color, 0.86)}"/>')
        parts.append(f'<rect y="164" width="512" height="7" fill="{shade(color, 0.72)}"/>')
        for xx in range(24, 512, 64):
            parts.append(f'<rect x="{xx}" y="182" width="44" height="54" fill="none" '
                         f'stroke="{shade(color, 0.78)}" stroke-width="3"/>')
    return parts


def _floor(s) -> list[str]:
    color = s["floor_color"]
    parts = [f'<rect y="{WALL_H}" width="512" height="{BASE_H - WALL_H}" fill="{color}"/>']
    pattern = s["floor_pattern"]
    if pattern == "wood":
        for i, yy in enumerate((278, 306, 334, 360)):
            parts.append(f'<path d="M 0 {yy} L 512 {yy}" stroke="{shade(color, 0.8)}" stroke-width="2.6"/>')
            offset = 90 if i % 2 == 0 else 240
            parts.append(f'<path d="M {offset} {yy - 26} L {offset} {yy}" stroke="{shade(color, 0.8)}" stroke-width="2.2"/>')
        for xx, yy in ((120, 292), (330, 320), (200, 348)):
            parts.append(f'<path d="M {xx} {yy} q 18 -5 36 0" stroke="{shade(color, 0.86)}" stroke-width="1.8" fill="none"/>')
    elif pattern == "tile":
        for yy in (282, 314, 346):
            parts.append(f'<path d="M 0 {yy} L 512 {yy}" stroke="{shade(color, 0.82)}" stroke-width="2.2"/>')
        for xx in (86, 172, 258, 344, 430):
            parts.append(f'<path d="M {xx} {WALL_H} L {xx - 14} {BASE_H}" stroke="{shade(color, 0.82)}" stroke-width="2.2"/>')
    elif pattern == "carpet":
        for yy in range(264, BASE_H, 18):
            for xx in range(14, 512, 26):
                parts.append(f'<circle cx="{xx}" cy="{yy}" r="1.8" fill="{shade(color, 0.9)}"/>')
    return parts


_WINDOW_X = {"left": 66, "center": 196, "right": 326}


def _window(s) -> str:
    pos = s["window"]
    if pos == "none":
        return ""
    x = _WINDOW_X[pos]
    night = s["lighting"] == "night"
    sky = "#1c2a52" if night else "#bfe3f5"
    parts = [f'<rect x="{x - 6}" y="52" width="132" height="128" rx="4" fill="#ffffff"/>',
             f'<rect x="{x}" y="58" width="120" height="116" fill="{sky}"/>']
    if night:
        parts.append(f'<circle cx="{x + 88}" cy="84" r="13" fill="#f5eeda"/>')
        for dx, dy in ((22, 76), (44, 96), (66, 70), (100, 110), (30, 128)):
            parts.append(f'<circle cx="{x + dx}" cy="{dy}" r="1.9" fill="#ffffff"/>')
    else:
        parts.append(f'<circle cx="{x + 90}" cy="86" r="14" fill="#ffd94d"/>')
        parts.append(f'<path d="M {x + 6} 150 Q {x + 40} 128 {x + 70} 146 T {x + 118} 142 L {x + 118} 174 L {x + 6} 174 Z" fill="#8fce7e"/>')
    parts.append(f'<path d="M {x + 60} 58 L {x + 60} 174 M {x} 116 L {x + 120} 116" stroke="#ffffff" stroke-width="6"/>')
    parts.append(f'<rect x="{x - 10}" y="178" width="140" height="7" rx="3" fill="{shade(s["wall_color"], 0.8)}"/>')
    return "".join(parts)


def _door(s) -> str:
    pos = s["door"]
    if pos == "none":
        return ""
    x = 28 if pos == "left" else 398
    return (f'<rect x="{x}" y="86" width="86" height="164" rx="3" fill="#9a6a3f"/>'
            f'<rect x="{x + 9}" y="96" width="68" height="66" fill="none" stroke="#7c5228" stroke-width="3.4"/>'
            f'<rect x="{x + 9}" y="172" width="68" height="66" fill="none" stroke="#7c5228" stroke-width="3.4"/>'
            f'<circle cx="{x + (68 if pos == "left" else 18)}" cy="176" r="4.6" fill="#e8c872"/>')


_LIGHT_OVERLAY = {
    "bright": ("#ffffff", 0.0),
    "warm": ("#ff9d3c", 0.12),
    "dim": ("#1a2340", 0.22),
    "night": ("#0b1030", 0.42),
}


def build_svg(spec) -> str:
    """仕様から部屋の SVG を生成する。テキストはエスケープし、script は出さない。"""
    s = validate_spec(spec)
    size = s["size"]
    height = round(size * BASE_H / BASE_W)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{height}" '
        f'viewBox="0 0 {BASE_W} {BASE_H}" role="img">',
    ]
    parts.extend(_wall(s))
    parts.extend(_floor(s))
    parts.append(f'<rect y="{WALL_H - 4}" width="512" height="6" fill="{shade(s["wall_color"], 0.75)}"/>')
    parts.append(_window(s))
    parts.append(_door(s))
    if s["name"]:
        parts.append(
            f'<g><rect x="196" y="14" width="120" height="28" rx="6" fill="#ffffff" opacity="0.75"/>'
            f'<text x="256" y="29" text-anchor="middle" dominant-baseline="central" '
            f'font-family="system-ui, sans-serif" font-size="16" fill="#5a4632">'
            f'{escape(s["name"])}</text></g>')
    # 奥の物から描く（y が小さい＝奥）
    for p in sorted(s["items"], key=lambda q: q["y"]):
        baseline = WALL_H + 8 + (p["y"] / 100.0) * 108
        w = p["width"] * p["scale"]
        h = p["height"] * p["scale"]
        if p["item"] == "lamp" and s["lighting"] in ("dim", "night"):
            parts.append(f'<circle cx="{num(p["x"] / 100 * 512)}" cy="{num(baseline - h * 0.82)}" '
                         f'r="{num(h * 0.52)}" fill="#ffd97a" opacity="0.35"/>')
        parts.append(f'<ellipse cx="{num(p["x"] / 100 * 512)}" cy="{num(baseline)}" '
                     f'rx="{num(w * 0.4)}" ry="5" fill="#000000" opacity="0.10"/>')
        parts.append(item_group(p["item"], p["main"], p["accent"],
                                p["x"] / 100 * 512, baseline, w, h, p["flip"]))
    overlay_color, overlay_opacity = _LIGHT_OVERLAY[s["lighting"]]
    if overlay_opacity:
        parts.append(f'<rect width="512" height="384" fill="{overlay_color}" opacity="{overlay_opacity}"/>')
    parts.append("</svg>")
    return "".join(parts)


# --- プリセットとランダム -----------------------------------------------------

def _p(item, x, y, main, accent, scale=1.0, flip=False):
    return {"item": item, "x": x, "y": y, "scale": scale, "flip": flip,
            "main": main, "accent": accent}


PRESETS = [
    {"name": "書斎", "spec": {
        "name": "書斎", "wall_color": "#e9e2d0", "floor_color": "#8a5a33", "floor_pattern": "wood",
        "window": "left", "door": "right", "lighting": "warm",
        "items": [_p("bookshelf", 24, 8, "#7c4a21", "#c9563c"),
                  _p("desk", 58, 42, "#8a5a33", "#5e3a1c"),
                  _p("chair", 58, 66, "#5b7fa6", "#2f4a6b"),
                  _p("lamp", 82, 30, "#8a6d3b", "#d9a441"),
                  _p("book", 48, 40, "#c9563c", "#7c2c1e", 0.8),
                  _p("plant", 90, 62, "#3f9e4d", "#b5542c", 0.9)]}},
    {"name": "寝室", "spec": {
        "name": "寝室", "wall_color": "#dfe7f2", "floor_color": "#a9805a", "floor_pattern": "carpet",
        "window": "center", "door": "left", "lighting": "dim",
        "items": [_p("bed", 34, 46, "#7c9cc4", "#f2f2f2"),
                  _p("lamp", 62, 34, "#8a6d3b", "#f0d089", 0.85),
                  _p("shelf", 82, 10, "#b07a45", "#7c4a21"),
                  _p("clock", 82, 44, "#5b7fa6", "#2f4a6b", 0.9),
                  _p("plant", 90, 66, "#3f9e4d", "#b5542c", 0.8)]}},
    {"name": "リビング", "spec": {
        "name": "リビング", "wall_color": "#f5efe2", "wall_pattern": "wainscot",
        "floor_color": "#b07a45", "floor_pattern": "wood",
        "window": "right", "door": "none", "lighting": "bright",
        "items": [_p("tv", 30, 30, "#3a3f4a", "#7fb2e0"),
                  _p("sofa", 66, 58, "#c96f4a", "#f0d9b5"),
                  _p("table", 62, 82, "#8a5a33", "#d9a441", 0.9),
                  _p("cup", 62, 76, "#e2543e", "#ffffff", 0.7),
                  _p("plant", 12, 60, "#3f9e4d", "#b5542c"),
                  _p("lamp", 90, 40, "#8a6d3b", "#d9a441")]}},
    {"name": "子供部屋", "spec": {
        "name": "子供部屋", "wall_color": "#fdeef4", "wall_pattern": "dots",
        "floor_color": "#c9a06a", "floor_pattern": "tile",
        "window": "center", "door": "right", "lighting": "bright",
        "items": [_p("bed", 26, 48, "#e88bb0", "#ffffff"),
                  _p("desk", 68, 40, "#e8c872", "#b08d2f"),
                  _p("chair", 68, 64, "#3fbfae", "#227a6e"),
                  _p("robot", 88, 62, "#7f9bb3", "#e2543e", 0.9),
                  _p("bookshelf", 8, 14, "#e88bb0", "#3fbfae", 0.9),
                  _p("book", 56, 38, "#3fbfae", "#227a6e", 0.8)]}},
]

_ITEM_PAIRS = [("#b07a45", "#7c4a21"), ("#5b7fa6", "#2f4a6b"), ("#c96f4a", "#f0d9b5"),
               ("#3f9e4d", "#b5542c"), ("#7f9bb3", "#e2543e"), ("#8a6d3b", "#d9a441")]


def random_spec(seed) -> dict:
    """seed から決定的にランダムな部屋の仕様を作る。必ず validate_spec を通る。"""
    rng = random.Random(seed)
    items = []
    for item in rng.sample(list(ITEMS), rng.randint(4, 7)):
        main, accent = rng.choice(_ITEM_PAIRS)
        items.append({"item": item, "x": rng.randint(8, 92), "y": rng.randint(5, 95),
                      "scale": round(rng.uniform(0.7, 1.3), 2), "flip": rng.random() < 0.3,
                      "main": main, "accent": accent})
    spec = {
        "format": FORMAT,
        "name": "",
        "wall_color": rng.choice(("#f3e9d7", "#dfe7f2", "#fdeef4", "#e9e2d0", "#e6f2e6")),
        "wall_pattern": rng.choice(WALL_PATTERNS),
        "floor_color": rng.choice(("#b07a45", "#8a5a33", "#a9805a", "#9aa5ad")),
        "floor_pattern": rng.choice(FLOOR_PATTERNS),
        "window": rng.choice(WINDOWS),
        "door": rng.choice(DOORS),
        "lighting": rng.choice(LIGHTINGS),
        "items": items,
        "size": 512,
    }
    return validate_spec(spec)
