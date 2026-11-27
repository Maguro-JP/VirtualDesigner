"""AtelIer 拡張の試験。拡張の形、ダイアログの各タブで作れること、本体の置き場読み込みで登録できること"""
import json
import os
import shutil
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "atelier_extension"))

try:
    from PySide6.QtWidgets import QApplication, QMainWindow
    HAS_QT = True
except ImportError:
    HAS_QT = False

CORE_FILES = ("vd_common.py", "avatar_core.py", "item_core.py", "space_core.py")


def _app():
    return QApplication.instance() or QApplication([])


@unittest.skipUnless(HAS_QT, "PySide6 が無い環境では拡張の試験をしない")
class ExtensionShapeTest(unittest.TestCase):
    def test_manifest_and_object(self):
        spec = json.loads((ROOT / "atelier_extension" / "extension.json").read_text(encoding="utf-8"))
        self.assertEqual(spec["module"], "virtual_designer.extension")
        self.assertEqual(spec["attr"], "EXTENSION")
        from virtual_designer.extension import EXTENSION
        self.assertEqual(EXTENSION.name, "virtual-designer")
        self.assertTrue(callable(EXTENSION.attach))

    def test_attach_adds_menu(self):
        _app()
        from virtual_designer.extension import EXTENSION
        win = QMainWindow()
        EXTENSION.attach(win)
        titles = [a.text() for a in win.menuBar().actions()]
        self.assertIn("バーチャルデザイン", titles)


@unittest.skipUnless(HAS_QT, "PySide6 が無い環境では拡張の試験をしない")
class DialogTest(unittest.TestCase):
    def setUp(self):
        _app()
        from virtual_designer.extension import VirtualDesignerDialog
        self.dlg = VirtualDesignerDialog()

    def test_has_three_tabs(self):
        self.assertEqual(self.dlg.tabs.count(), 3)
        labels = [self.dlg.tabs.tabText(i) for i in range(3)]
        self.assertEqual(labels, ["アバター", "空間", "道具"])

    def test_each_tab_builds_svg(self):
        for tab in (self.dlg.avatar_tab, self.dlg.space_tab, self.dlg.item_tab):
            with self.subTest(tab=type(tab).__name__):
                svg = tab.current_svg()
                self.assertIn("<svg", svg)
                self.assertNotIn("<script", svg)

    def test_avatar_tab_options_change_svg(self):
        tab = self.dlg.avatar_tab
        base = tab.current_svg()
        tab.hair_style.setCurrentIndex(tab.hair_style.findData("twintails"))
        self.assertNotEqual(tab.current_svg(), base)

    def test_item_tab_options_change_svg(self):
        tab = self.dlg.item_tab
        base = tab.current_svg()
        tab.item.setCurrentIndex(tab.item.findData("sword"))
        self.assertNotEqual(tab.current_svg(), base)

    def test_space_tab_placements(self):
        tab = self.dlg.space_tab
        self.assertGreaterEqual(len(tab.placements), 1)
        before = tab.current_svg()
        tab._add()
        self.assertNotEqual(tab.current_svg(), before)
        tab._remove()
        self.assertEqual(tab.current_svg(), before)

    def test_invalid_color_is_an_error(self):
        tab = self.dlg.avatar_tab
        tab.skin.setText("red")
        # core は拡張がファイルの場所から読むため、例外のクラスは import した物と別物になる。ValueError として見る
        with self.assertRaises(ValueError):
            tab.current_svg()
        self.assertNotEqual(tab.status.text(), "")


class DropInLoadTest(unittest.TestCase):
    """本体（AtelIer）の load_dropins で、インストールした形のフォルダが登録できること"""

    def test_loads_through_atelier(self):
        atelier_home = os.environ.get("ATELIER_HOME", str(ROOT.parent / "AtelIer-work"))
        if not (Path(atelier_home) / "atelier" / "extensions.py").is_file():
            self.skipTest("AtelIer のソースが近くに無い")
        sys.path.insert(0, atelier_home)
        from atelier import extensions
        with TemporaryDirectory() as d:
            dst = Path(d) / "VirtualDesigner"
            shutil.copytree(ROOT / "atelier_extension", dst)
            for name in CORE_FILES:
                shutil.copy2(ROOT / name, dst / name)
            names = extensions.load_dropins(Path(d))
            self.assertIn("virtual-designer", names)
            self.assertIn("virtual-designer", [e.name for e in extensions.registered()])


if __name__ == "__main__":
    unittest.main()
