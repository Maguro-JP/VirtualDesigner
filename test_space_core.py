"""space_core.py のテスト。全選択肢・全家具の配置、色の検証、プリセット、ランダム、エスケープ。"""

import unittest

import item_core
import space_core as sc
from vd_common import VDError


def svg(**overrides):
    spec = dict(sc.DEFAULTS)
    spec.update(overrides)
    return sc.build_svg(spec)


def placement(item, **kw):
    base = {"item": item, "x": 50, "y": 50, "scale": 1.0, "flip": False,
            "main": "#b07a45", "accent": "#7c4a21"}
    base.update(kw)
    return base


class TestValidate(unittest.TestCase):
    def test_defaults(self):
        spec = sc.validate_spec({})
        self.assertEqual(spec["format"], "virtualdesigner.space.v1")
        self.assertEqual(spec["items"], [])

    def test_unknown_choices(self):
        for key, bad in (("wall_pattern", "floral"), ("floor_pattern", "marble"),
                         ("window", "skylight"), ("door", "double"), ("lighting", "candle")):
            with self.subTest(key=key), self.assertRaises(VDError):
                sc.validate_spec({key: bad})
        with self.assertRaises(VDError):
            sc.validate_spec({"format": "x"})
        with self.assertRaises(VDError):
            sc.validate_spec([])

    def test_colors(self):
        self.assertEqual(sc.validate_spec({"wall_color": "#AABBCC"})["wall_color"], "#aabbcc")
        for key in ("wall_color", "floor_color"):
            with self.assertRaises(VDError):
                sc.validate_spec({key: "white"})

    def test_placement_validation(self):
        ok = sc.validate_spec({"items": [placement("chair")]})
        self.assertEqual(ok["items"][0]["width"], item_core.CATALOG["chair"][2])
        for bad in (placement("rocket"),
                    placement("chair", x=101), placement("chair", x=-1),
                    placement("chair", y=101), placement("chair", scale=0.2),
                    placement("chair", scale=3.1), placement("chair", flip="yes"),
                    placement("chair", main="red"), "chair"):
            with self.subTest(bad=bad), self.assertRaises(VDError):
                sc.validate_spec({"items": [bad]})
        with self.assertRaises(VDError):
            sc.validate_spec({"items": "chair"})
        with self.assertRaises(VDError):
            sc.validate_spec({"items": [placement("chair")] * 31})


class TestEveryOptionRenders(unittest.TestCase):
    def check(self, key, options, **base):
        base_svg = svg(**base)
        for option in options:
            with self.subTest(key=key, option=option):
                out = svg(**{**base, key: option})
                self.assertIn("<svg", out)
                if option != base.get(key, sc.DEFAULTS[key]):
                    self.assertNotEqual(out, base_svg)

    def test_wall_patterns(self):
        self.check("wall_pattern", sc.WALL_PATTERNS)

    def test_floor_patterns(self):
        self.check("floor_pattern", sc.FLOOR_PATTERNS)

    def test_windows(self):
        self.check("window", sc.WINDOWS)

    def test_doors(self):
        self.check("door", sc.DOORS)

    def test_lightings(self):
        self.check("lighting", sc.LIGHTINGS)

    def test_wall_floor_colors(self):
        self.assertNotEqual(svg(wall_color="#010203"), svg())
        self.assertNotEqual(svg(floor_color="#010203"), svg())

    def test_every_catalog_item_placeable(self):
        self.assertGreaterEqual(len(item_core.ITEMS), 10)
        empty = svg(items=[])
        for item in item_core.ITEMS:
            with self.subTest(item=item):
                out = svg(items=[placement(item)])
                self.assertIn("<svg", out)
                self.assertNotEqual(out, empty)

    def test_placement_variants_change_svg(self):
        one = svg(items=[placement("sofa")])
        self.assertNotEqual(svg(items=[placement("sofa", x=20)]), one)
        self.assertNotEqual(svg(items=[placement("sofa", y=90)]), one)
        self.assertNotEqual(svg(items=[placement("sofa", scale=1.6)]), one)
        self.assertNotEqual(svg(items=[placement("sofa", flip=True)]), one)
        self.assertNotEqual(svg(items=[placement("sofa", main="#010203")]), one)


class TestPresetsAndRandom(unittest.TestCase):
    def test_presets(self):
        self.assertGreaterEqual(len(sc.PRESETS), 4)
        for preset in sc.PRESETS:
            with self.subTest(preset=preset["name"]):
                spec = sc.validate_spec(preset["spec"])
                self.assertGreaterEqual(len(spec["items"]), 3)
                self.assertIn("<svg", sc.build_svg(spec))

    def test_random(self):
        for seed in (0, 5, 77, 2024):
            spec = sc.random_spec(seed)
            sc.validate_spec(spec)
            self.assertEqual(sc.random_spec(seed), spec)
            self.assertGreaterEqual(len(spec["items"]), 4)
            self.assertIn("<svg", sc.build_svg(spec))


class TestOutputSafety(unittest.TestCase):
    def test_name_escaped(self):
        out = svg(name="<書斎>")
        self.assertIn("&lt;書斎&gt;", out)
        self.assertNotIn("<書斎>", out)

    def test_no_script_and_deterministic(self):
        self.assertNotIn("<script", svg(name="<script>"))
        spec = {"items": [placement("bed"), placement("lamp", x=80)]}
        self.assertEqual(svg(**spec), svg(**spec))


if __name__ == "__main__":
    unittest.main()
