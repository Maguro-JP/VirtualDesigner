"""item_core.py のテスト。全アイテム・全装飾が描けること、色の検証、プリセット、ランダム、エスケープ。"""

import unittest

import item_core as ic
from vd_common import VDError


def svg(**overrides):
    spec = dict(ic.DEFAULTS)
    spec.update(overrides)
    return ic.build_svg(spec)


class TestValidate(unittest.TestCase):
    def test_defaults(self):
        spec = ic.validate_spec({})
        self.assertEqual(spec["format"], "virtualdesigner.item.v1")
        self.assertEqual(spec["item"], "chair")

    def test_unknown_item_and_decoration(self):
        with self.assertRaises(VDError):
            ic.validate_spec({"item": "rocket"})
        with self.assertRaises(VDError):
            ic.validate_spec({"decoration": "lace"})
        with self.assertRaises(VDError):
            ic.validate_spec({"format": "other.v1"})
        with self.assertRaises(VDError):
            ic.validate_spec(None)

    def test_custom_hex(self):
        spec = ic.validate_spec({"main": "#AABBCC", "accent": "#000000"})
        self.assertEqual(spec["main"], "#aabbcc")
        for key in ("main", "accent", "background", "background2"):
            for bad in ("blue", "#1234", "#xyzxyz", 7):
                with self.subTest(key=key, bad=bad), self.assertRaises(VDError):
                    ic.validate_spec({key: bad})


class TestEveryItemRenders(unittest.TestCase):
    def test_catalog_size(self):
        self.assertGreaterEqual(len(ic.ITEMS), 12)
        categories = {ic.CATALOG[i][1] for i in ic.ITEMS}
        self.assertEqual(categories, set(ic.CATEGORIES))

    def test_each_item_renders_and_differs(self):
        base = svg(item="chair")
        seen = set()
        for item in ic.ITEMS:
            with self.subTest(item=item):
                out = svg(item=item)
                self.assertIn("<svg", out)
                self.assertNotIn("<script", out)
                seen.add(out)
                if item != "chair":
                    self.assertNotEqual(out, base)
        self.assertEqual(len(seen), len(ic.ITEMS))

    def test_draw_item_direct(self):
        for item in ic.ITEMS:
            parts = ic.draw_item(item, "#111111", "#eeeeee")
            self.assertTrue(parts)
            self.assertTrue(all(isinstance(p, str) for p in parts))
        with self.assertRaises(VDError):
            ic.draw_item("rocket", "#111111", "#eeeeee")

    def test_decorations_change_svg(self):
        plain = svg(decoration="none")
        for deco in ic.DECORATIONS:
            with self.subTest(decoration=deco):
                out = svg(decoration=deco)
                if deco != "none":
                    self.assertNotEqual(out, plain)

    def test_bg_styles(self):
        base = svg(bg_style="solid")
        self.assertNotEqual(svg(bg_style="gradient"), base)
        self.assertNotEqual(svg(bg_style="pattern"), base)
        for pattern in ("dots", "stripes", "check"):
            self.assertIn("<svg", svg(bg_style="pattern", bg_pattern=pattern))

    def test_colors_change_svg(self):
        self.assertNotEqual(svg(main="#010203"), svg())
        self.assertNotEqual(svg(accent="#010203"), svg())


class TestPresetsAndRandom(unittest.TestCase):
    def test_presets(self):
        self.assertGreaterEqual(len(ic.PRESETS), 6)
        for preset in ic.PRESETS:
            with self.subTest(preset=preset["name"]):
                ic.validate_spec(preset["spec"])
                self.assertIn("<svg", ic.build_svg(preset["spec"]))

    def test_random(self):
        for seed in (0, 3, 17, 12345):
            spec = ic.random_spec(seed)
            ic.validate_spec(spec)
            self.assertEqual(ic.random_spec(seed), spec)
            self.assertIn("<svg", ic.build_svg(spec))


class TestOutputSafety(unittest.TestCase):
    def test_name_escaped(self):
        out = svg(name="<b>剣</b>")
        self.assertIn("&lt;b&gt;", out)
        self.assertNotIn("<b>剣", out)

    def test_deterministic(self):
        self.assertEqual(svg(item="robot"), svg(item="robot"))


if __name__ == "__main__":
    unittest.main()
