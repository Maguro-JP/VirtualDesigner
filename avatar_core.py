"""VirtualDesigner のアバター（人物の見た目）のロジック（標準ライブラリのみ）。

仕様フォーマット: ``virtualdesigner.avatar.v1``

顔・髪・目・服などのパーツを組み合わせて、正面のアバターを SVG で描く。
検証・正規化・SVG 生成だけを担当し、入出力やネットワークは行わない。
描画は 512×512 の基準座標で組み立て、viewBox で拡縮する（決定的な出力）。
"""

from __future__ import annotations

import random

from vd_common import (EYE_COLORS, HAIR_COLORS, SKIN_TONES, VDError,
                       background_elements, escape, num, require_choice,
                       require_int, require_text, shade, validate_background,
                       validate_hex)

__all__ = ["FORMAT", "FACE_SHAPES", "HAIR_STYLES", "EYE_SHAPES", "BROW_STYLES",
           "NOSE_STYLES", "MOUTH_STYLES", "FACIAL_HAIRS", "GLASSES", "EARRINGS",
           "HATS", "HAIR_ACCESSORIES", "OUTFITS",
           "validate_spec", "build_svg", "random_spec", "PRESETS"]

FORMAT = "virtualdesigner.avatar.v1"

FACE_SHAPES = ("round", "oval", "square", "sharp")
HAIR_STYLES = ("none", "buzz", "short", "bob", "long", "twintails", "ponytail",
               "bun", "mohawk", "wavy", "curly", "sidepart")
EYE_SHAPES = ("round", "almond", "upturned", "downturned", "closed")
BROW_STYLES = ("straight", "arch", "angled", "gentle")
NOSE_STYLES = ("dot", "line", "shadow", "none")
MOUTH_STYLES = ("smile", "grin", "open", "flat", "small", "surprised")
FACIAL_HAIRS = ("none", "stubble", "mustache", "beard", "full")
GLASSES = ("none", "round", "square", "sunglasses")
EARRINGS = ("none", "stud", "hoop", "drop")
HATS = ("none", "cap", "beret", "beanie", "straw")
HAIR_ACCESSORIES = ("none", "ribbon", "hairpin", "flower")
OUTFITS = ("tshirt", "shirt", "hoodie", "suit", "dress", "kimono")

DEFAULTS = {
    "format": FORMAT,
    "name": "",
    "face_shape": "round",
    "skin": "#ffd7ae",
    "hair_style": "short",
    "hair_color": "#6b4423",
    "eye_shape": "round",
    "eye_color": "#5b3a1e",
    "brow_style": "straight",
    "nose_style": "line",
    "mouth_style": "smile",
    "facial_hair": "none",
    "glasses": "none",
    "earrings": "none",
    "hat": "none",
    "hair_accessory": "none",
    "outfit": "tshirt",
    "outfit_color": "#4a6fd4",
    "outfit_accent": "#f5f5f5",
    "bg_style": "solid",
    "background": "#eaf2f8",
    "background2": "#c9dcee",
    "bg_pattern": "dots",
    "size": 512,
}

CX = 256          # 顔の中心 x
EYE_Y = 226       # 目の高さ
EYE_DX = 38       # 中心から目までの距離


def validate_spec(data) -> dict:
    """仕様 dict を検証し、正規化した dict を返す。欠けた任意項目は既定値で補う。"""
    if not isinstance(data, dict):
        raise VDError("仕様はオブジェクトである必要があります")
    fmt = data.get("format", FORMAT)
    if not isinstance(fmt, str) or fmt != FORMAT:
        raise VDError(f"format は {FORMAT} である必要があります")
    spec = {
        "format": FORMAT,
        "name": require_text(data, "name", "", 30),
        "face_shape": require_choice(data, "face_shape", FACE_SHAPES, "round"),
        "skin": validate_hex(data.get("skin", "#ffd7ae"), "skin"),
        "hair_style": require_choice(data, "hair_style", HAIR_STYLES, "short"),
        "hair_color": validate_hex(data.get("hair_color", "#6b4423"), "hair_color"),
        "eye_shape": require_choice(data, "eye_shape", EYE_SHAPES, "round"),
        "eye_color": validate_hex(data.get("eye_color", "#5b3a1e"), "eye_color"),
        "brow_style": require_choice(data, "brow_style", BROW_STYLES, "straight"),
        "nose_style": require_choice(data, "nose_style", NOSE_STYLES, "line"),
        "mouth_style": require_choice(data, "mouth_style", MOUTH_STYLES, "smile"),
        "facial_hair": require_choice(data, "facial_hair", FACIAL_HAIRS, "none"),
        "glasses": require_choice(data, "glasses", GLASSES, "none"),
        "earrings": require_choice(data, "earrings", EARRINGS, "none"),
        "hat": require_choice(data, "hat", HATS, "none"),
        "hair_accessory": require_choice(data, "hair_accessory", HAIR_ACCESSORIES, "none"),
        "outfit": require_choice(data, "outfit", OUTFITS, "tshirt"),
        "outfit_color": validate_hex(data.get("outfit_color", "#4a6fd4"), "outfit_color"),
        "outfit_accent": validate_hex(data.get("outfit_accent", "#f5f5f5"), "outfit_accent"),
        "size": require_int(data, "size", 512, 128, 2048),
    }
    spec.update(validate_background(data))
    return spec


# --- 顔まわり ---------------------------------------------------------------

_EAR_OFFSET = {"round": 80, "oval": 71, "square": 75, "sharp": 78}


def _face(s) -> str:
    skin = s["skin"]
    shape = s["face_shape"]
    if shape == "round":
        body = f'<ellipse cx="256" cy="218" rx="80" ry="76" fill="{skin}"/>'
    elif shape == "oval":
        body = f'<ellipse cx="256" cy="222" rx="70" ry="88" fill="{skin}"/>'
    elif shape == "square":
        body = '<rect x="182" y="140" width="148" height="152" rx="30" fill="{}"/>'.format(skin)
    else:  # sharp
        body = (f'<path d="M 256 306 C 210 288 182 240 180 190 C 178 140 214 116 256 116 '
                f'C 298 116 334 140 332 190 C 330 240 302 288 256 306 Z" fill="{skin}"/>')
    off = _EAR_OFFSET[shape]
    ears = (f'<ellipse cx="{256 - off}" cy="228" rx="12" ry="18" fill="{skin}"/>'
            f'<ellipse cx="{256 + off}" cy="228" rx="12" ry="18" fill="{skin}"/>')
    return ears + body


def _eye_white(cx: float, shape: str) -> str:
    if shape == "round":
        return f'<ellipse cx="{num(cx)}" cy="{EYE_Y}" rx="16" ry="12" fill="#ffffff"/>'
    if shape == "almond":
        return (f'<path d="M {num(cx - 16)} {EYE_Y} Q {num(cx)} {EYE_Y - 13} {num(cx + 16)} {EYE_Y} '
                f'Q {num(cx)} {EYE_Y + 9} {num(cx - 16)} {EYE_Y} Z" fill="#ffffff"/>')
    if shape == "upturned":
        return (f'<path d="M {num(cx - 16)} {EYE_Y + 2} Q {num(cx - 2)} {EYE_Y - 14} {num(cx + 16)} {EYE_Y - 4} '
                f'Q {num(cx + 2)} {EYE_Y + 8} {num(cx - 16)} {EYE_Y + 2} Z" fill="#ffffff"/>')
    if shape == "downturned":
        return (f'<path d="M {num(cx - 16)} {EYE_Y - 3} Q {num(cx)} {EYE_Y - 12} {num(cx + 16)} {EYE_Y + 1} '
                f'Q {num(cx)} {EYE_Y + 10} {num(cx - 16)} {EYE_Y - 3} Z" fill="#ffffff"/>')
    return ""


def _eyes(s) -> str:
    shape = s["eye_shape"]
    color = s["eye_color"]
    parts = []
    for cx in (CX - EYE_DX, CX + EYE_DX):
        if shape == "closed":
            parts.append(f'<path d="M {num(cx - 15)} {EYE_Y} Q {num(cx)} {EYE_Y + 11} {num(cx + 15)} {EYE_Y}" '
                         f'stroke="#333333" stroke-width="3.4" fill="none" stroke-linecap="round"/>')
            continue
        parts.append(_eye_white(cx, shape))
        parts.append(f'<circle cx="{num(cx)}" cy="{EYE_Y}" r="8" fill="{color}"/>')
        parts.append(f'<circle cx="{num(cx)}" cy="{EYE_Y}" r="3.6" fill="#1a1a1a"/>')
        parts.append(f'<circle cx="{num(cx - 2.6)}" cy="{EYE_Y - 3}" r="2.4" fill="#ffffff"/>')
        parts.append(f'<path d="M {num(cx - 17)} {EYE_Y - 3} Q {num(cx)} {EYE_Y - 15} {num(cx + 17)} {EYE_Y - 4}" '
                     f'stroke="#333333" stroke-width="3" fill="none" stroke-linecap="round"/>')
    return "".join(parts)


def _brows(s) -> str:
    style = s["brow_style"]
    color = s["hair_color"]
    y = 196
    parts = []
    for cx, mirror in ((CX - EYE_DX, 1), (CX + EYE_DX, -1)):
        if style == "straight":
            d = f'M {num(cx - 16)} {y} L {num(cx + 16)} {y - 2}'
        elif style == "arch":
            d = f'M {num(cx - 16)} {y + 2} Q {num(cx)} {y - 10} {num(cx + 16)} {y}'
        elif style == "angled":  # 内側（顔の中心側）が下がる
            d = f'M {num(cx - 16 * mirror)} {y - 5} L {num(cx + 16 * mirror)} {y + 3}'
        else:  # gentle: 外側が下がる
            d = f'M {num(cx - 16 * mirror)} {y + 3} Q {num(cx)} {y - 6} {num(cx + 16 * mirror)} {y - 2}'
        parts.append(f'<path d="{d}" stroke="{color}" stroke-width="5" fill="none" stroke-linecap="round"/>')
    return "".join(parts)


def _nose(s) -> str:
    style = s["nose_style"]
    dark = shade(s["skin"], 0.78)
    if style == "dot":
        return f'<ellipse cx="256" cy="252" rx="3.2" ry="4.6" fill="{dark}"/>'
    if style == "line":
        return (f'<path d="M 256 238 L 252.6 252 Q 256 255.6 260.4 253" stroke="{dark}" '
                f'stroke-width="2.6" fill="none" stroke-linecap="round"/>')
    if style == "shadow":
        return f'<path d="M 247 257 Q 256 248 265 257 Q 256 261.4 247 257 Z" fill="{shade(s["skin"], 0.86)}"/>'
    return ""


_LIP = "#b0503f"


def _mouth(s) -> str:
    style = s["mouth_style"]
    if style == "smile":
        return f'<path d="M 238 269 Q 256 286 274 269" stroke="{_LIP}" stroke-width="3.6" fill="none" stroke-linecap="round"/>'
    if style == "grin":
        return (f'<path d="M 236 267 Q 256 291 276 267 Q 256 278 236 267 Z" fill="#ffffff" '
                f'stroke="{_LIP}" stroke-width="2.6"/>')
    if style == "open":
        return (f'<ellipse cx="256" cy="276" rx="9" ry="12" fill="#7c2d2d"/>'
                f'<ellipse cx="256" cy="282" rx="6" ry="4.6" fill="#d96a6a"/>')
    if style == "flat":
        return f'<path d="M 242 274 L 270 274" stroke="{_LIP}" stroke-width="3.4" stroke-linecap="round"/>'
    if style == "small":
        return f'<path d="M 248 271 Q 256 278 264 271" stroke="{_LIP}" stroke-width="3" fill="none" stroke-linecap="round"/>'
    return f'<ellipse cx="256" cy="275" rx="6" ry="8.4" fill="none" stroke="{_LIP}" stroke-width="3"/>'


def _facial_hair(s) -> str:
    """髭。口より前に描く（口はこの後で上から描く）。"""
    style = s["facial_hair"]
    if style == "none":
        return ""
    color = s["hair_color"]
    parts = []
    if style in ("beard", "full"):
        parts.append(f'<path d="M 194 236 C 198 300 224 326 256 326 C 288 326 314 300 318 236 '
                     f'C 302 288 282 300 256 300 C 230 300 210 288 194 236 Z" fill="{color}"/>')
    if style == "stubble":
        dots = []
        for i, (dx, dy) in enumerate(((-38, 62), (-24, 74), (-8, 80), (8, 80), (24, 74), (38, 62),
                                      (-46, 44), (46, 44), (-16, 84), (16, 84), (0, 86), (-32, 56), (32, 56))):
            dots.append(f'<circle cx="{256 + dx}" cy="{196 + dy}" r="1.7" fill="{color}" opacity="0.55"/>')
        parts.extend(dots)
    if style in ("mustache", "full"):
        parts.append(f'<path d="M 256 262 C 246 254 232 254 228 264 C 238 270 250 269 256 266 '
                     f'C 262 269 274 270 284 264 C 280 254 266 254 256 262 Z" fill="{color}"/>')
    return "".join(parts)


def _earrings(s) -> str:
    style = s["earrings"]
    if style == "none":
        return ""
    off = _EAR_OFFSET[s["face_shape"]]
    gold = "#d9a441"
    parts = []
    for cx in (256 - off, 256 + off):
        if style == "stud":
            parts.append(f'<circle cx="{cx}" cy="246" r="4" fill="{gold}"/>')
        elif style == "hoop":
            parts.append(f'<circle cx="{cx}" cy="252" r="8" fill="none" stroke="{gold}" stroke-width="2.6"/>')
        else:  # drop
            parts.append(f'<path d="M {cx} 242 L {cx} 250" stroke="{gold}" stroke-width="2"/>'
                         f'<ellipse cx="{cx}" cy="256" rx="4" ry="6.6" fill="{gold}"/>')
    return "".join(parts)


def _glasses(s) -> str:
    style = s["glasses"]
    if style == "none":
        return ""
    frame = "#3a3a3a"
    parts = []
    if style == "sunglasses":
        for cx in (CX - EYE_DX, CX + EYE_DX):
            parts.append(f'<rect x="{num(cx - 23)}" y="206" width="46" height="38" rx="10" fill="#1f2430" opacity="0.94"/>')
    elif style == "round":
        for cx in (CX - EYE_DX, CX + EYE_DX):
            parts.append(f'<circle cx="{num(cx)}" cy="{EYE_Y}" r="21" fill="none" stroke="{frame}" stroke-width="3.4"/>')
    else:  # square
        for cx in (CX - EYE_DX, CX + EYE_DX):
            parts.append(f'<rect x="{num(cx - 22)}" y="205" width="44" height="40" rx="6" fill="none" stroke="{frame}" stroke-width="3.4"/>')
    parts.append(f'<path d="M {CX - 17} 220 Q 256 212 {CX + 17} 220" stroke="{frame}" stroke-width="3.4" fill="none"/>')
    parts.append(f'<path d="M {CX - EYE_DX - 22} 216 L 182 208 M {CX + EYE_DX + 22} 216 L 330 208" stroke="{frame}" stroke-width="3.2"/>')
    return "".join(parts)


# --- 髪 ---------------------------------------------------------------------

def _hair_back(s) -> str:
    style = s["hair_style"]
    color = s["hair_color"]
    if style == "long":
        return (f'<path d="M 256 82 C 178 82 148 152 150 262 L 144 472 L 368 472 L 362 262 '
                f'C 364 152 334 82 256 82 Z" fill="{color}"/>')
    if style == "bob":
        return (f'<path d="M 256 84 C 186 84 158 140 160 230 L 158 336 L 354 336 L 352 230 '
                f'C 354 140 326 84 256 84 Z" fill="{color}"/>')
    if style == "twintails":
        return (f'<path d="M 158 168 C 124 236 128 332 152 404 C 176 332 180 238 170 172 Z" fill="{color}"/>'
                f'<path d="M 354 168 C 388 236 384 332 360 404 C 336 332 332 238 342 172 Z" fill="{color}"/>'
                f'<circle cx="162" cy="166" r="10" fill="{shade(color, 0.7)}"/>'
                f'<circle cx="350" cy="166" r="10" fill="{shade(color, 0.7)}"/>')
    if style == "ponytail":
        return (f'<path d="M 318 108 C 356 160 366 260 352 366 C 330 280 318 190 306 128 Z" fill="{color}"/>'
                f'<circle cx="316" cy="112" r="10" fill="{shade(color, 0.7)}"/>')
    if style == "wavy":
        return (f'<path d="M 256 84 C 184 84 156 146 160 250 L 164 330 L 348 330 L 352 250 '
                f'C 356 146 328 84 256 84 Z" fill="{color}"/>')
    if style == "curly":
        circles = "".join(
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>'
            for x, y, r in ((168, 210, 22), (344, 210, 22), (164, 258, 19), (348, 258, 19)))
        return circles
    return ""


def _hair_front(s) -> str:
    style = s["hair_style"]
    color = s["hair_color"]
    if style in ("none",):
        return ""
    cap_top = "M 174 214 C 170 118 212 90 256 90 C 300 90 342 118 338 214"
    if style == "buzz":
        return (f'<path d="{cap_top} C 322 148 292 128 256 128 C 220 128 190 148 174 214 Z" '
                f'fill="{color}" opacity="0.85"/>')
    if style == "short":
        return f'<path d="{cap_top} C 318 158 292 148 256 142 C 220 148 194 158 174 214 Z" fill="{color}"/>'
    if style == "sidepart":
        return (f'<path d="{cap_top} C 306 140 238 138 178 190 Z" fill="{color}"/>'
                f'<path d="M 292 108 C 262 128 226 140 196 146" stroke="{shade(color, 0.7)}" '
                f'stroke-width="3" fill="none"/>')
    if style == "wavy":
        fringe = " C ".join(["330 168", "306 150 288 172", "268 150 250 172", "230 150 210 172", "192 152 180 190"])
        return f'<path d="{cap_top} C {fringe} Z" fill="{color}"/>'
    if style == "curly":
        circles = "".join(
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>'
            for x, y, r in ((196, 138, 21), (226, 112, 23), (256, 104, 24), (286, 112, 23),
                            (316, 138, 21), (332, 172, 19), (180, 172, 19)))
        return circles
    if style == "bob":
        return (f'<path d="{cap_top} C 316 152 288 146 256 144 C 224 146 196 152 174 214 Z" fill="{color}"/>'
                f'<path d="M 172 190 L 196 190 L 196 302 C 184 306 174 300 172 286 Z" fill="{color}"/>'
                f'<path d="M 340 190 L 316 190 L 316 302 C 328 306 338 300 340 286 Z" fill="{color}"/>')
    if style == "long":
        return (f'<path d="{cap_top} C 316 152 288 146 256 144 C 224 146 196 152 174 214 Z" fill="{color}"/>'
                f'<path d="M 186 196 L 202 196 L 198 336 C 190 338 185 330 186 318 Z" fill="{color}"/>'
                f'<path d="M 326 196 L 310 196 L 314 336 C 322 338 327 330 326 318 Z" fill="{color}"/>')
    if style == "twintails":
        return f'<path d="{cap_top} C 314 154 290 146 256 144 C 222 146 198 154 174 214 Z" fill="{color}"/>'
    if style == "ponytail":
        return f'<path d="{cap_top} C 314 154 290 146 256 144 C 222 146 198 154 174 214 Z" fill="{color}"/>'
    if style == "bun":
        return (f'<circle cx="256" cy="80" r="30" fill="{color}"/>'
                f'<path d="{cap_top} C 314 154 290 146 256 144 C 222 146 198 154 174 214 Z" fill="{color}"/>')
    if style == "mohawk":
        return (f'<path d="M 238 208 C 234 122 242 68 256 52 C 270 68 278 122 274 208 '
                f'C 266 164 246 164 238 208 Z" fill="{color}"/>')
    return ""


def _hair_accessory(s) -> str:
    style = s["hair_accessory"]
    if style == "none" or s["hair_style"] == "none":
        return ""
    accent = s["outfit_accent"]
    if style == "ribbon":
        return (f'<g><path d="M 322 126 L 292 108 L 296 140 Z" fill="{accent}"/>'
                f'<path d="M 322 126 L 352 108 L 348 140 Z" fill="{accent}"/>'
                f'<circle cx="322" cy="126" r="8" fill="{shade(accent, 0.8)}"/></g>')
    if style == "hairpin":
        return (f'<g stroke="#d9a441" stroke-width="3.4" stroke-linecap="round">'
                f'<path d="M 296 138 L 322 158"/><path d="M 288 148 L 314 168"/></g>')
    return (f'<g><circle cx="326" cy="128" r="6.4" fill="#ffffff"/><circle cx="338" cy="138" r="6.4" fill="#ffffff"/>'
            f'<circle cx="330" cy="150" r="6.4" fill="#ffffff"/><circle cx="316" cy="146" r="6.4" fill="#ffffff"/>'
            f'<circle cx="314" cy="132" r="6.4" fill="#ffffff"/><circle cx="326" cy="140" r="5" fill="#f5c542"/></g>')


def _hat(s) -> str:
    style = s["hat"]
    if style == "none":
        return ""
    main = s["outfit_color"]
    accent = s["outfit_accent"]
    if style == "cap":
        return (f'<path d="M 186 130 C 190 84 222 64 256 64 C 290 64 322 84 326 130 Z" fill="{main}"/>'
                f'<ellipse cx="256" cy="134" rx="94" ry="12" fill="{shade(main, 0.8)}"/>'
                f'<path d="M 186 130 C 220 118 292 118 326 130" stroke="{accent}" stroke-width="5" fill="none"/>')
    if style == "beret":
        return (f'<ellipse cx="248" cy="94" rx="76" ry="23" fill="{main}"/>'
                f'<path d="M 248 72 L 248 62" stroke="{shade(main, 0.75)}" stroke-width="5" stroke-linecap="round"/>')
    if style == "beanie":
        return (f'<circle cx="256" cy="56" r="12" fill="{accent}"/>'
                f'<path d="M 190 126 C 194 82 224 62 256 62 C 288 62 318 82 322 126 Z" fill="{main}"/>'
                f'<rect x="188" y="118" width="136" height="19" rx="9" fill="{accent}"/>')
    return (f'<path d="M 214 122 C 218 88 234 76 256 76 C 278 76 294 88 298 122 Z" fill="#ecd9a0"/>'
            f'<rect x="214" y="112" width="84" height="11" fill="{accent}"/>'
            f'<ellipse cx="256" cy="126" rx="112" ry="15" fill="#e8cf8f"/>')


# --- 服 ---------------------------------------------------------------------

def _outfit(s) -> str:
    style = s["outfit"]
    main = s["outfit_color"]
    accent = s["outfit_accent"]
    if style == "dress":
        base = ('<path d="M 256 322 C 196 322 150 352 128 408 L 84 512 L 428 512 L 384 408 '
                'C 362 352 316 322 256 322 Z" fill="{}"/>').format(main)
    else:
        base = ('<path d="M 256 322 C 190 322 128 356 108 420 L 96 512 L 416 512 L 404 420 '
                'C 384 356 322 322 256 322 Z" fill="{}"/>').format(main)
    dark = shade(main, 0.82)
    if style == "tshirt":
        detail = (f'<path d="M 224 328 Q 256 350 288 328 L 288 344 Q 256 364 224 344 Z" fill="{dark}"/>'
                  f'<rect x="150" y="428" width="212" height="13" fill="{accent}" opacity="0.9"/>'
                  f'<path d="M 128 396 L 168 410 M 384 396 L 344 410" stroke="{dark}" stroke-width="5"/>')
    elif style == "shirt":
        detail = (f'<path d="M 224 326 L 256 356 L 240 372 L 218 336 Z" fill="{dark}"/>'
                  f'<path d="M 288 326 L 256 356 L 272 372 L 294 336 Z" fill="{dark}"/>'
                  f'<path d="M 256 356 L 256 512" stroke="{dark}" stroke-width="4"/>'
                  + "".join(f'<circle cx="256" cy="{y}" r="3.6" fill="{accent}"/>' for y in (388, 424, 460)))
    elif style == "hoodie":
        detail = (f'<path d="M 220 340 C 224 306 288 306 292 340 C 276 324 236 324 220 340 Z" fill="{dark}"/>'
                  f'<path d="M 244 344 L 240 372 M 268 344 L 272 372" stroke="{accent}" stroke-width="4" stroke-linecap="round"/>'
                  f'<rect x="204" y="428" width="104" height="58" rx="12" fill="{shade(main, 0.93)}" stroke="{dark}" stroke-width="3"/>')
    elif style == "suit":
        detail = (f'<path d="M 230 328 L 282 328 L 256 424 Z" fill="#f5f5f5"/>'
                  f'<path d="M 230 328 L 256 424 L 224 352 Z" fill="{dark}"/>'
                  f'<path d="M 282 328 L 256 424 L 288 352 Z" fill="{dark}"/>'
                  f'<path d="M 256 344 L 246 362 L 252 412 L 256 424 L 260 412 L 266 362 Z" fill="{accent}"/>'
                  f'<path d="M 248 336 L 264 336 L 256 350 Z" fill="{accent}"/>')
    elif style == "dress":
        detail = (f'<path d="M 226 326 Q 256 352 286 326 L 286 342 Q 256 366 226 342 Z" fill="{shade(s["skin"], 0.98)}"/>'
                  f'<rect x="150" y="402" width="212" height="17" fill="{accent}"/>')
    else:  # kimono
        detail = (f'<path d="M 224 326 L 288 402 L 272 414 L 214 340 Z" fill="{accent}" opacity="0.92"/>'
                  f'<path d="M 288 326 L 224 402 L 240 414 L 298 340 Z" fill="{shade(accent, 0.85)}" opacity="0.92"/>'
                  f'<rect x="128" y="398" width="256" height="32" fill="{shade(accent, 0.72)}"/>'
                  f'<rect x="238" y="402" width="36" height="24" rx="4" fill="{accent}"/>')
    return base + detail


def build_svg(spec) -> str:
    """仕様からアバターの SVG を生成する。テキストはエスケープし、script は出さない。"""
    s = validate_spec(spec)
    size = s["size"]
    defs, bg = background_elements(s["bg_style"], s["bg_pattern"], s["background"],
                                   s["background2"], 512, 512, "avatar")
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 512 512" role="img">',
        defs, bg,
        _hair_back(s),
        f'<rect x="240" y="284" width="32" height="46" fill="{shade(s["skin"], 0.92)}"/>',
        _outfit(s),
        _face(s),
        _facial_hair(s),
        _nose(s),
        _mouth(s),
        _eyes(s),
        _brows(s),
        _earrings(s),
        _glasses(s),
        _hair_front(s),
        _hair_accessory(s),
        _hat(s),
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
    {"name": "さくら", "spec": {"name": "さくら", "hair_style": "bob", "hair_color": "#f2a0c0",
                                "eye_color": "#a06a2c", "mouth_style": "grin",
                                "hair_accessory": "ribbon", "outfit": "dress",
                                "outfit_color": "#e2547a", "outfit_accent": "#ffffff",
                                "background": "#fdeef4"}},
    {"name": "そら", "spec": {"name": "そら", "hair_style": "short", "hair_color": "#4a6fd4",
                              "eye_shape": "almond", "eye_color": "#3a6fd8",
                              "outfit": "hoodie", "outfit_color": "#5b8dd4",
                              "outfit_accent": "#ffffff", "background": "#e8f1fc"}},
    {"name": "レン", "spec": {"name": "レン", "hair_style": "sidepart", "hair_color": "#2b2b2b",
                              "eye_shape": "upturned", "glasses": "round",
                              "outfit": "shirt", "outfit_color": "#e8e8e8",
                              "outfit_accent": "#7c4a21", "background": "#f4f1ea"}},
    {"name": "ツインテールのミク風", "spec": {"name": "ミク", "hair_style": "twintails",
                                              "hair_color": "#3fbfae", "eye_color": "#3a6fd8",
                                              "mouth_style": "open", "outfit": "tshirt",
                                              "outfit_color": "#3a3f4a", "outfit_accent": "#e2547a",
                                              "background": "#e6f7f4"}},
    {"name": "スーツの課長", "spec": {"name": "課長", "hair_style": "sidepart", "hair_color": "#4a4a4a",
                                      "facial_hair": "mustache", "brow_style": "angled",
                                      "mouth_style": "flat", "outfit": "suit",
                                      "outfit_color": "#2f3a52", "outfit_accent": "#a02c2c",
                                      "background": "#eef0f4"}},
    {"name": "着物のあやめ", "spec": {"name": "あやめ", "hair_style": "bun", "hair_color": "#3a2a3a",
                                      "hair_accessory": "flower", "eye_shape": "downturned",
                                      "mouth_style": "small", "outfit": "kimono",
                                      "outfit_color": "#5e4a8a", "outfit_accent": "#e8c872",
                                      "background": "#f3eefc"}},
]


def random_spec(seed) -> dict:
    """seed から決定的にランダムなアバターの仕様を作る。必ず validate_spec を通る。"""
    rng = random.Random(seed)
    spec = {
        "format": FORMAT,
        "name": "",
        "face_shape": rng.choice(FACE_SHAPES),
        "skin": rng.choice(SKIN_TONES),
        "hair_style": rng.choice(HAIR_STYLES),
        "hair_color": rng.choice(HAIR_COLORS),
        "eye_shape": rng.choice(EYE_SHAPES),
        "eye_color": rng.choice(EYE_COLORS),
        "brow_style": rng.choice(BROW_STYLES),
        "nose_style": rng.choice(NOSE_STYLES),
        "mouth_style": rng.choice(MOUTH_STYLES),
        "facial_hair": rng.choice(FACIAL_HAIRS),
        "glasses": rng.choice(GLASSES),
        "earrings": rng.choice(EARRINGS),
        "hat": rng.choice(HATS),
        "hair_accessory": rng.choice(HAIR_ACCESSORIES),
        "outfit": rng.choice(OUTFITS),
        "outfit_color": rng.choice(HAIR_COLORS + EYE_COLORS),
        "outfit_accent": rng.choice(("#f5f5f5", "#f5c542", "#e2543e", "#2f3a52", "#ffffff")),
        "bg_style": rng.choice(("solid", "gradient", "pattern")),
        "background": rng.choice(("#eaf2f8", "#fdeef4", "#f2f7e8", "#eef0f7", "#fdf6ec")),
        "background2": rng.choice(("#c9dcee", "#f6c9da", "#d8ecc4", "#d4d8ea", "#f3e2c7")),
        "bg_pattern": rng.choice(("dots", "stripes", "check")),
        "size": 512,
    }
    return validate_spec(spec)
