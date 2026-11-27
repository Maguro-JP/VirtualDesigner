"""avatar_core.py のテスト。全パーツの全選択肢が描けて SVG が変わること、色の検証、プリセット、ランダム、エスケープ。"""

import unittest

import avatar_core as ac
from vd_common import VDError


def svg(**overrides):
    spec = dict(ac.DEFAULTS)
    spec.update(overrides)
    return ac.build_svg(spec)


class TestValidate(unittest.TestCase):
    def test_defaults(self):
        spec = ac.validate_spec({})
        self.assertEqual(spec["format"], "virtualdesigner.avatar.v1")
        self.assertEqual(spec["face_shape"], "round")
        self.assertEqual(spec["size"], 512)

    def test_non_dict_and_bad_format(self):
        with self.assertRaises(VDError):
            ac.validate_spec("x")
        with self.assertRaises(VDError):
            ac.validate_spec({"format": "other.v1"})

    def test_unknown_choices(self):
        for key, bad in (("face_shape", "hexagon"), ("hair_style", "afro"),
                         ("eye_shape", "star"), ("brow_style", "thick"),
                         ("nose_style", "big"), ("mouth_style", "cat"),
                         ("facial_hair", "goatee"), ("glasses", "monocle"),
                         ("earrings", "chain"), ("hat", "crown"),
                         ("hair_accessory", "band"), ("outfit", "armor"),
                         ("bg_style", "photo"), ("bg_pattern", "wave")):
            with self.subTest(key=key), self.assertRaises(VDError):
                ac.validate_spec({key: bad})

    def test_custom_hex_accepted_and_normalised(self):
        spec = ac.validate_spec({"skin": "#A1B2C3", "hair_color": "#000000",
                                 "eye_color": "#FF00AA", "outfit_color": "#123abc"})
        self.assertEqual(spec["skin"], "#a1b2c3")
        self.assertEqual(spec["eye_color"], "#ff00aa")

    def test_custom_hex_rejected(self):
        for key in ("skin", "hair_color", "eye_color", "outfit_color",
                    "outfit_accent", "background", "background2"):
            for bad in ("red", "#12345", "#1234567", "#GGGGGG", "123456", 42, None):
                with self.subTest(key=key, bad=bad), self.assertRaises(VDError):
                    ac.validate_spec({key: bad})

    def test_name_rules(self):
        with self.assertRaises(VDError):
            ac.validate_spec({"name": "x" * 31})
        with self.assertRaises(VDError):
            ac.validate_spec({"name": "a\x01b"})
        self.assertEqual(ac.validate_spec({"name": "  たろう  "})["name"], "たろう")

    def test_size_bounds(self):
        for bad in (127, 2049, 512.0, "512", True):
            with self.subTest(bad=bad), self.assertRaises(VDError):
                ac.validate_spec({"size": bad})


class TestEveryOptionRenders(unittest.TestCase):
    """各カテゴリの全選択肢が、既定と違う SVG をエラーなく描くこと。"""

    def check(self, key, options, **base):
        base_svg = svg(**base)
        for option in options:
            with self.subTest(key=key, option=option):
                out = svg(**{**base, key: option})
                self.assertIn("<svg", out)
                if option != base.get(key, ac.DEFAULTS[key]):
                    self.assertNotEqual(out, base_svg)

    def test_face_shapes(self):
        self.check("face_shape", ac.FACE_SHAPES)

    def test_hair_styles(self):
        self.check("hair_style", ac.HAIR_STYLES)

    def test_eye_shapes(self):
        self.check("eye_shape", ac.EYE_SHAPES)

    def test_brow_styles(self):
        self.check("brow_style", ac.BROW_STYLES)

    def test_nose_styles(self):
        self.check("nose_style", ac.NOSE_STYLES)

    def test_mouth_styles(self):
        self.check("mouth_style", ac.MOUTH_STYLES)

    def test_facial_hairs(self):
        self.check("facial_hair", ac.FACIAL_HAIRS)

    def test_glasses(self):
        self.check("glasses", ac.GLASSES)

    def test_earrings(self):
        self.check("earrings", ac.EARRINGS)

    def test_hats(self):
        self.check("hat", ac.HATS, hair_style="short")

    def test_hair_accessories(self):
        self.check("hair_accessory", ac.HAIR_ACCESSORIES, hair_style="long")

    def test_outfits(self):
        self.check("outfit", ac.OUTFITS)

    def test_bg_styles_and_patterns(self):
        self.check("bg_style", ("solid", "gradient", "pattern"))
        self.check("bg_pattern", ("dots", "stripes", "check"), bg_style="pattern")

    def test_colors_change_svg(self):
        for key in ("skin", "hair_color", "eye_color", "outfit_color", "outfit_accent"):
            with self.subTest(key=key):
                self.assertNotEqual(svg(**{key: "#010203"}), svg())
        # 閉じた目では瞳の色は出ないので、目の色は丸目で確認済み（既定が丸目）


class TestPresetsAndRandom(unittest.TestCase):
    def test_presets_valid_and_render(self):
        self.assertGreaterEqual(len(ac.PRESETS), 6)
        for preset in ac.PRESETS:
            with self.subTest(preset=preset["name"]):
                spec = ac.validate_spec(preset["spec"])
                self.assertIn("<svg", ac.build_svg(spec))

    def test_random_valid_deterministic(self):
        for seed in (0, 1, 2, 42, 999, "abc"):
            with self.subTest(seed=seed):
                spec = ac.random_spec(seed)
                ac.validate_spec(spec)
                self.assertEqual(ac.random_spec(seed), spec)
                self.assertIn("<svg", ac.build_svg(spec))


class TestOutputSafety(unittest.TestCase):
    def test_name_escaped(self):
        out = svg(name='A<B & "C"')
        self.assertIn("A&lt;B &amp;", out)
        self.assertNotIn("A<B", out)

    def test_no_script_anywhere(self):
        for hair in ac.HAIR_STYLES:
            self.assertNotIn("<script", svg(hair_style=hair, name="<script>"))
        self.assertNotIn("onload", svg(name="x"))

    def test_deterministic(self):
        self.assertEqual(svg(), svg())
        self.assertEqual(svg(hair_style="twintails", outfit="kimono"),
                         svg(hair_style="twintails", outfit="kimono"))


if __name__ == "__main__":
    unittest.main()
