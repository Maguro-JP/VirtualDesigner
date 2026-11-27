"""VirtualDesigner を AtelIer の拡張として付ける（atelier/extensions.py の口）。

本体はこのパッケージを読まない。拡張の置き場（ProgramData\\AtelIer\\extensions\\VirtualDesigner\\）に
extension.json と一緒に置かれ、本体の窓に「バーチャルデザイン」のメニューと、
アバター・空間・道具の 3 つのタブを持つダイアログを足す。
生成は VirtualDesigner 本体の各 core（検証と SVG 生成、標準ライブラリのみ）を使う。
このファイルは AtelIer の中で動くので、画面には AtelIer と同じ PySide6 を使う。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget, QMenu,
                               QMessageBox, QPushButton, QSpinBox, QDoubleSpinBox,
                               QTabWidget, QVBoxLayout, QWidget)

MENU = "バーチャルデザイン"

FACE_LABELS = (("round", "丸"), ("oval", "卵"), ("square", "四角"), ("sharp", "シャープ"))
HAIR_LABELS = (("none", "無し"), ("buzz", "坊主"), ("short", "ショート"), ("bob", "ボブ"),
               ("long", "ロング"), ("twintails", "ツインテール"), ("ponytail", "ポニーテール"),
               ("bun", "お団子"), ("mohawk", "モヒカン"), ("wavy", "ウェーブ"),
               ("curly", "カーリー"), ("sidepart", "サイドパート"))
EYE_LABELS = (("round", "丸目"), ("almond", "アーモンド"), ("upturned", "つり目"),
              ("downturned", "たれ目"), ("closed", "閉じ目"))
BROW_LABELS = (("straight", "まっすぐ"), ("arch", "アーチ"), ("angled", "キリッ"), ("gentle", "やさしい"))
NOSE_LABELS = (("dot", "点"), ("line", "線"), ("shadow", "影"), ("none", "無し"))
MOUTH_LABELS = (("smile", "笑顔"), ("grin", "にっこり"), ("open", "開いた口"), ("flat", "まっすぐ"),
                ("small", "小さい口"), ("surprised", "おどろき"))
FACIAL_HAIR_LABELS = (("none", "無し"), ("stubble", "無精髭"), ("mustache", "口髭"),
                      ("beard", "顎髭"), ("full", "フル（口髭＋顎髭）"))
GLASSES_LABELS = (("none", "無し"), ("round", "丸眼鏡"), ("square", "四角眼鏡"), ("sunglasses", "サングラス"))
EARRING_LABELS = (("none", "無し"), ("stud", "スタッド"), ("hoop", "フープ"), ("drop", "ドロップ"))
HAT_LABELS = (("none", "無し"), ("cap", "キャップ"), ("beret", "ベレー帽"), ("beanie", "ニット帽"), ("straw", "麦わら帽子"))
ACCESSORY_LABELS = (("none", "無し"), ("ribbon", "リボン"), ("hairpin", "ヘアピン"), ("flower", "花"))
OUTFIT_LABELS = (("tshirt", "Tシャツ"), ("shirt", "シャツ"), ("hoodie", "パーカー"),
                 ("suit", "スーツ"), ("dress", "ドレス"), ("kimono", "着物"))
DECORATION_LABELS = (("none", "無し"), ("dots", "ドット"), ("stripes", "ストライプ"), ("stars", "星"))
BG_STYLE_LABELS = (("solid", "単色"), ("gradient", "グラデーション"), ("pattern", "柄"))
BG_PATTERN_LABELS = (("dots", "ドット"), ("stripes", "ストライプ"), ("check", "チェック"))
WALL_PATTERN_LABELS = (("none", "無し"), ("dots", "ドット"), ("stripes", "ストライプ"),
                       ("check", "チェック"), ("wainscot", "腰壁"))
FLOOR_PATTERN_LABELS = (("plain", "無地"), ("wood", "木目"), ("tile", "タイル"), ("carpet", "カーペット"))
WINDOW_LABELS = (("none", "無し"), ("left", "左"), ("center", "中央"), ("right", "右"))
DOOR_LABELS = (("none", "無し"), ("left", "左"), ("right", "右"))
LIGHTING_LABELS = (("bright", "明るい"), ("warm", "暖かい"), ("dim", "薄暗い"), ("night", "夜"))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_cores():
    """各 core を探して読む。置き場に一緒に入れた物（インストール時）を先に、
    無ければこのリポジトリの根の物（開発時）を使う。
    core 同士が名前で読み合う（space_core → item_core → vd_common）ため、
    依存順に sys.modules へ登録してから読み込む。"""
    here = Path(__file__).resolve()
    candidates = [here.parents[1],          # 拡張の置き場 / atelier_extension の直下
                  here.parents[2]]          # リポジトリの根
    for root in candidates:
        if (root / "avatar_core.py").is_file():
            _load_module("vd_common", root / "vd_common.py")
            item = _load_module("item_core", root / "item_core.py")
            avatar = _load_module("avatar_core", root / "avatar_core.py")
            space = _load_module("space_core", root / "space_core.py")
            return avatar, space, item
    raise ImportError("avatar_core.py が見つかりません")


def _combo(labels):
    box = QComboBox()
    for key, label in labels:
        box.addItem(label, key)
    return box


def _render_preview(label: QLabel, svg: str, width: int, height: int) -> None:
    renderer = QSvgRenderer(svg.encode("utf-8"))
    pix = QPixmap(width, height)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    renderer.render(painter)
    painter.end()
    label.setPixmap(pix)


class _BaseTab(QWidget):
    """プレビューと保存を持つタブの共通部分。"""

    core = None
    filename = "virtual.svg"
    preview_size = (320, 320)

    def _build_tail(self, layout: QVBoxLayout) -> None:
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(*self.preview_size)
        self.status = QLabel("")
        save_svg = QPushButton("SVGで保存…")
        save_png = QPushButton("PNGで保存…")
        save_svg.clicked.connect(self._save_svg)
        save_png.clicked.connect(self._save_png)
        row = QHBoxLayout()
        row.addWidget(save_svg)
        row.addWidget(save_png)
        row.addStretch(1)
        layout.addWidget(self.preview)
        layout.addWidget(self.status)
        layout.addLayout(row)

    def _watch(self, *widgets) -> None:
        for w in widgets:
            if isinstance(w, QLineEdit):
                w.textChanged.connect(self._refresh)
            elif isinstance(w, (QSpinBox, QDoubleSpinBox)):
                w.valueChanged.connect(self._refresh)
            elif isinstance(w, QCheckBox):
                w.stateChanged.connect(self._refresh)
            else:
                w.currentIndexChanged.connect(self._refresh)

    def spec(self) -> dict:
        raise NotImplementedError

    def png_size(self) -> tuple[int, int]:
        size = self.core.validate_spec(self.spec())["size"]
        return size, size

    def current_svg(self) -> str:
        """今の入力で SVG を作る。入力が不正なら core のエラーをそのまま上げる"""
        return self.core.build_svg(self.core.validate_spec(self.spec()))

    def _refresh(self):
        try:
            svg = self.current_svg()
        except Exception as e:   # noqa: BLE001  入力の誤りはプレビューの代わりに理由を出す
            self.status.setText(str(e))
            self.preview.setPixmap(QPixmap())
            return
        self.status.setText("")
        _render_preview(self.preview, svg, *self.preview_size)

    def _save_svg(self):
        try:
            svg = self.current_svg()
        except Exception as e:   # noqa: BLE001
            QMessageBox.warning(self, "作れません", str(e))
            return
        path, _ = QFileDialog.getSaveFileName(self, "SVGで保存", self.filename, "SVG (*.svg)")
        if path:
            Path(path).write_text(svg, encoding="utf-8")

    def _save_png(self):
        try:
            svg = self.current_svg()
            width, height = self.png_size()
        except Exception as e:   # noqa: BLE001
            QMessageBox.warning(self, "作れません", str(e))
            return
        path, _ = QFileDialog.getSaveFileName(self, "PNGで保存",
                                              self.filename.replace(".svg", ".png"), "PNG (*.png)")
        if path:
            renderer = QSvgRenderer(svg.encode("utf-8"))
            img = QImage(width, height, QImage.Format_ARGB32)
            img.fill(Qt.transparent)
            painter = QPainter(img)
            renderer.render(painter)
            painter.end()
            img.save(path, "PNG")


class AvatarTab(_BaseTab):
    filename = "avatar.svg"

    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.name = QLineEdit("")
        self.face_shape = _combo(FACE_LABELS)
        self.skin = QLineEdit("#ffd7ae")
        self.hair_style = _combo(HAIR_LABELS)
        self.hair_color = QLineEdit("#6b4423")
        self.eye_shape = _combo(EYE_LABELS)
        self.eye_color = QLineEdit("#5b3a1e")
        self.brow_style = _combo(BROW_LABELS)
        self.nose_style = _combo(NOSE_LABELS)
        self.mouth_style = _combo(MOUTH_LABELS)
        self.facial_hair = _combo(FACIAL_HAIR_LABELS)
        self.glasses = _combo(GLASSES_LABELS)
        self.earrings = _combo(EARRING_LABELS)
        self.hat = _combo(HAT_LABELS)
        self.hair_accessory = _combo(ACCESSORY_LABELS)
        self.outfit = _combo(OUTFIT_LABELS)
        self.outfit_color = QLineEdit("#4a6fd4")
        self.outfit_accent = QLineEdit("#f5f5f5")
        self.bg_style = _combo(BG_STYLE_LABELS)
        self.background = QLineEdit("#eaf2f8")
        self.background2 = QLineEdit("#c9dcee")
        self.bg_pattern = _combo(BG_PATTERN_LABELS)
        self.size = QSpinBox()
        self.size.setRange(128, 2048)
        self.size.setValue(512)
        form = QFormLayout()
        form.addRow("名前", self.name)
        form.addRow("顔の形", self.face_shape)
        form.addRow("肌の色 (#RRGGBB)", self.skin)
        form.addRow("髪型", self.hair_style)
        form.addRow("髪の色", self.hair_color)
        form.addRow("目の形", self.eye_shape)
        form.addRow("瞳の色", self.eye_color)
        form.addRow("眉", self.brow_style)
        form.addRow("鼻", self.nose_style)
        form.addRow("口", self.mouth_style)
        form.addRow("髭", self.facial_hair)
        form.addRow("眼鏡", self.glasses)
        form.addRow("耳飾り", self.earrings)
        form.addRow("帽子", self.hat)
        form.addRow("髪飾り", self.hair_accessory)
        form.addRow("服", self.outfit)
        form.addRow("服の色", self.outfit_color)
        form.addRow("服の差し色", self.outfit_accent)
        form.addRow("背景の種類", self.bg_style)
        form.addRow("背景色", self.background)
        form.addRow("背景色2", self.background2)
        form.addRow("背景の柄", self.bg_pattern)
        form.addRow("大きさ", self.size)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        self._build_tail(layout)
        self._watch(self.name, self.face_shape, self.skin, self.hair_style, self.hair_color,
                    self.eye_shape, self.eye_color, self.brow_style, self.nose_style,
                    self.mouth_style, self.facial_hair, self.glasses, self.earrings,
                    self.hat, self.hair_accessory, self.outfit, self.outfit_color,
                    self.outfit_accent, self.bg_style, self.background, self.background2,
                    self.bg_pattern, self.size)
        self._refresh()

    def spec(self) -> dict:
        return {"name": self.name.text(), "face_shape": self.face_shape.currentData(),
                "skin": self.skin.text(), "hair_style": self.hair_style.currentData(),
                "hair_color": self.hair_color.text(), "eye_shape": self.eye_shape.currentData(),
                "eye_color": self.eye_color.text(), "brow_style": self.brow_style.currentData(),
                "nose_style": self.nose_style.currentData(), "mouth_style": self.mouth_style.currentData(),
                "facial_hair": self.facial_hair.currentData(), "glasses": self.glasses.currentData(),
                "earrings": self.earrings.currentData(), "hat": self.hat.currentData(),
                "hair_accessory": self.hair_accessory.currentData(), "outfit": self.outfit.currentData(),
                "outfit_color": self.outfit_color.text(), "outfit_accent": self.outfit_accent.text(),
                "bg_style": self.bg_style.currentData(), "background": self.background.text(),
                "background2": self.background2.text(), "bg_pattern": self.bg_pattern.currentData(),
                "size": self.size.value()}


class ItemTab(_BaseTab):
    filename = "item.svg"

    def __init__(self, core, parent=None):
        super().__init__(parent)
        self.core = core
        self.item = _combo(tuple((key, core.ITEM_LABELS[key]) for key in core.ITEMS))
        self.name = QLineEdit("")
        self.main = QLineEdit("#b07a45")
        self.accent = QLineEdit("#7c4a21")
        self.decoration = _combo(DECORATION_LABELS)
        self.bg_style = _combo(BG_STYLE_LABELS)
        self.background = QLineEdit("#fdf6ec")
        self.background2 = QLineEdit("#f3e2c7")
        self.bg_pattern = _combo(BG_PATTERN_LABELS)
        self.size = QSpinBox()
        self.size.setRange(128, 2048)
        self.size.setValue(512)
        form = QFormLayout()
        form.addRow("道具", self.item)
        form.addRow("名前", self.name)
        form.addRow("メイン色 (#RRGGBB)", self.main)
        form.addRow("差し色", self.accent)
        form.addRow("模様", self.decoration)
        form.addRow("背景の種類", self.bg_style)
        form.addRow("背景色", self.background)
        form.addRow("背景色2", self.background2)
        form.addRow("背景の柄", self.bg_pattern)
        form.addRow("大きさ", self.size)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        self._build_tail(layout)
        self._watch(self.item, self.name, self.main, self.accent, self.decoration,
                    self.bg_style, self.background, self.background2, self.bg_pattern, self.size)
        self._refresh()

    def spec(self) -> dict:
        return {"item": self.item.currentData(), "name": self.name.text(),
                "main": self.main.text(), "accent": self.accent.text(),
                "decoration": self.decoration.currentData(),
                "bg_style": self.bg_style.currentData(), "background": self.background.text(),
                "background2": self.background2.text(), "bg_pattern": self.bg_pattern.currentData(),
                "size": self.size.value()}


class SpaceTab(_BaseTab):
    filename = "space.svg"
    preview_size = (360, 270)

    def __init__(self, space_core, item_core, parent=None):
        super().__init__(parent)
        self.core = space_core
        self.item_core = item_core
        self.placements: list[dict] = [
            {"item": "sofa", "x": 62, "y": 58, "scale": 1.0, "flip": False,
             "main": "#c96f4a", "accent": "#f0d9b5"},
            {"item": "lamp", "x": 88, "y": 40, "scale": 1.0, "flip": False,
             "main": "#8a6d3b", "accent": "#d9a441"},
        ]
        self.name = QLineEdit("")
        self.wall_color = QLineEdit("#f3e9d7")
        self.wall_pattern = _combo(WALL_PATTERN_LABELS)
        self.floor_color = QLineEdit("#b07a45")
        self.floor_pattern = _combo(FLOOR_PATTERN_LABELS)
        self.window = _combo(WINDOW_LABELS)
        self.door = _combo(DOOR_LABELS)
        self.lighting = _combo(LIGHTING_LABELS)
        self.size = QSpinBox()
        self.size.setRange(128, 2048)
        self.size.setValue(512)
        form = QFormLayout()
        form.addRow("部屋の名前", self.name)
        form.addRow("壁の色 (#RRGGBB)", self.wall_color)
        form.addRow("壁の柄", self.wall_pattern)
        form.addRow("床の色", self.floor_color)
        form.addRow("床の柄", self.floor_pattern)
        form.addRow("窓", self.window)
        form.addRow("ドア", self.door)
        form.addRow("照明", self.lighting)
        form.addRow("幅", self.size)

        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._load_editor)
        self.p_item = _combo(tuple((key, item_core.ITEM_LABELS[key]) for key in item_core.ITEMS))
        self.p_x = QSpinBox(); self.p_x.setRange(0, 100); self.p_x.setValue(50)
        self.p_y = QSpinBox(); self.p_y.setRange(0, 100); self.p_y.setValue(50)
        self.p_scale = QDoubleSpinBox(); self.p_scale.setRange(0.3, 3.0)
        self.p_scale.setSingleStep(0.1); self.p_scale.setValue(1.0)
        self.p_flip = QCheckBox("左右反転")
        self.p_main = QLineEdit("#b07a45")
        self.p_accent = QLineEdit("#7c4a21")
        pform = QFormLayout()
        pform.addRow("置く物", self.p_item)
        pform.addRow("x（横 %）", self.p_x)
        pform.addRow("y（奥行き %）", self.p_y)
        pform.addRow("大きさ", self.p_scale)
        pform.addRow("", self.p_flip)
        pform.addRow("メイン色", self.p_main)
        pform.addRow("差し色", self.p_accent)
        add = QPushButton("追加")
        remove = QPushButton("削除")
        add.clicked.connect(self._add)
        remove.clicked.connect(self._remove)
        prow = QHBoxLayout()
        prow.addWidget(add)
        prow.addWidget(remove)
        prow.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(QLabel("配置した物"))
        layout.addWidget(self.list)
        layout.addLayout(pform)
        layout.addLayout(prow)
        self._build_tail(layout)
        self._watch(self.name, self.wall_color, self.wall_pattern, self.floor_color,
                    self.floor_pattern, self.window, self.door, self.lighting, self.size)
        self._watch(self.p_item, self.p_x, self.p_y, self.p_scale, self.p_flip,
                    self.p_main, self.p_accent)
        self._syncing = False
        self._rebuild_list()
        self._refresh()

    # -- 配置リストの管理 --
    def _rebuild_list(self):
        self._syncing = True
        self.list.clear()
        for p in self.placements:
            label = self.item_core.ITEM_LABELS[p["item"]]
            self.list.addItem(f'{label}（x={p["x"]}, y={p["y"]}, ×{p["scale"]}）')
        if self.placements:
            self.list.setCurrentRow(0)
        self._syncing = False
        self._load_editor(self.list.currentRow())

    def _load_editor(self, row: int):
        if self._syncing or row < 0 or row >= len(self.placements):
            return
        p = self.placements[row]
        self._syncing = True
        self.p_item.setCurrentIndex(self.p_item.findData(p["item"]))
        self.p_x.setValue(int(p["x"]))
        self.p_y.setValue(int(p["y"]))
        self.p_scale.setValue(float(p["scale"]))
        self.p_flip.setChecked(bool(p["flip"]))
        self.p_main.setText(p["main"])
        self.p_accent.setText(p["accent"])
        self._syncing = False

    def _apply_editor(self):
        row = self.list.currentRow()
        if self._syncing or row < 0 or row >= len(self.placements):
            return
        self.placements[row] = {"item": self.p_item.currentData(), "x": self.p_x.value(),
                                "y": self.p_y.value(), "scale": self.p_scale.value(),
                                "flip": self.p_flip.isChecked(), "main": self.p_main.text(),
                                "accent": self.p_accent.text()}
        label = self.item_core.ITEM_LABELS[self.placements[row]["item"]]
        p = self.placements[row]
        self.list.item(row).setText(f'{label}（x={p["x"]}, y={p["y"]}, ×{p["scale"]}）')

    def _add(self):
        self.placements.append({"item": "chair", "x": 50, "y": 60, "scale": 1.0,
                                "flip": False, "main": "#b07a45", "accent": "#7c4a21"})
        self._rebuild_list()
        self.list.setCurrentRow(len(self.placements) - 1)
        self._refresh()

    def _remove(self):
        row = self.list.currentRow()
        if 0 <= row < len(self.placements):
            del self.placements[row]
            self._rebuild_list()
            self._refresh()

    def _refresh(self):
        self._apply_editor()
        super()._refresh()

    def spec(self) -> dict:
        return {"name": self.name.text(), "wall_color": self.wall_color.text(),
                "wall_pattern": self.wall_pattern.currentData(),
                "floor_color": self.floor_color.text(),
                "floor_pattern": self.floor_pattern.currentData(),
                "window": self.window.currentData(), "door": self.door.currentData(),
                "lighting": self.lighting.currentData(),
                "items": [dict(p) for p in self.placements],
                "size": self.size.value()}

    def png_size(self) -> tuple[int, int]:
        size = self.core.validate_spec(self.spec())["size"]
        return size, round(size * 0.75)


class VirtualDesignerDialog(QDialog):
    """アバター・空間・道具の 3 タブで作り、プレビューを見て SVG / PNG で保存するダイアログ"""

    def __init__(self, parent=None):
        super().__init__(parent)
        avatar_core, space_core, item_core = load_cores()
        self.setWindowTitle("バーチャルデザイン")
        self.tabs = QTabWidget()
        self.avatar_tab = AvatarTab(avatar_core)
        self.space_tab = SpaceTab(space_core, item_core)
        self.item_tab = ItemTab(item_core)
        self.tabs.addTab(self.avatar_tab, "アバター")
        self.tabs.addTab(self.space_tab, "空間")
        self.tabs.addTab(self.item_tab, "道具")
        close = QPushButton("閉じる")
        close.clicked.connect(self.accept)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addWidget(close)


class VirtualDesignerExtension:
    name = "virtual-designer"

    def attach(self, window) -> None:
        menu = QMenu(MENU, window)
        act = QAction("アバター・空間・道具を作る…", window)
        act.setToolTip("アバターの見た目、部屋、道具をパーツと色で作り、SVG / PNG で保存します")
        act.triggered.connect(lambda _=False: VirtualDesignerDialog(window).exec())
        menu.addAction(act)
        window.menuBar().addMenu(menu)
        window.virtual_designer_menu = menu   # 窓に参照を持たせる（メニューが消えないように）


EXTENSION = VirtualDesignerExtension()
