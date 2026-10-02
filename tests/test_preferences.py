import unittest
from uuid import uuid4

from AppKit import NSScreen, NSUserDefaults

from readmask import ReadMaskApp, UI_TEXT, focus_rectangle


class PreferencesTest(unittest.TestCase):
    def test_height_tracks_each_screen(self):
        first = focus_rectangle((0, 0, 1000, 1000), (500, 500), 0.5, 0.2)
        second = focus_rectangle((1000, 0, 1000, 600), (1500, 300), 0.5, 0.2)
        self.assertEqual(first[3], 200)
        self.assertEqual(second[3], 120)

    def test_legacy_point_height_migrates_once(self):
        suite = "app.readmask.test." + uuid4().hex
        defaults = NSUserDefaults.alloc().initWithSuiteName_(suite)
        try:
            screen = NSScreen.mainScreen()
            frame = screen.frame()
            center = (frame[0][0] + frame[1][0] / 2,
                      frame[0][1] + frame[1][1] / 2)
            defaults.setBool_forKey_(False, "followsMouse")
            defaults.setObject_forKey_(center, "fixedPoint")
            defaults.setDouble_forKey_(frame[1][1] * 0.2, "focusHeight")

            app = ReadMaskApp.alloc().init()
            app.preferences = defaults
            app._load_preferences()
            self.assertAlmostEqual(app.height_ratio, 0.2)
            self.assertAlmostEqual(defaults.doubleForKey_("heightRatio"), 0.2)
        finally:
            defaults.removePersistentDomainForName_(suite)

    def test_settings_survive_a_new_app_instance(self):
        suite = "app.readmask.test." + uuid4().hex
        defaults = NSUserDefaults.alloc().initWithSuiteName_(suite)
        try:
            first = ReadMaskApp.alloc().init()
            first.preferences = defaults
            first.enabled = False
            first.follows_mouse = False
            first.width_ratio = 0.42
            first.height_ratio = 0.23
            first.opacity = 0.64
            first.language = "en"
            first.anchor_sizes = {"move": 60, "resize": 36}
            first.anchor_transparencies = {"move": 0.7, "resize": 0.3}
            first.fixed_point = (123.5, 456.5)
            first._save_preferences()

            second = ReadMaskApp.alloc().init()
            second.preferences = defaults
            second._load_preferences()
            self.assertFalse(second.enabled)
            self.assertFalse(second.follows_mouse)
            self.assertAlmostEqual(second.width_ratio, 0.42)
            self.assertAlmostEqual(second.height_ratio, 0.23)
            self.assertAlmostEqual(second.opacity, 0.64)
            self.assertEqual(second.language, "en")
            self.assertEqual(second.anchor_sizes, {"move": 60, "resize": 36})
            self.assertEqual(second.anchor_transparencies, {"move": 0.7, "resize": 0.3})
            self.assertEqual(second.fixed_point, (123.5, 456.5))
        finally:
            defaults.removePersistentDomainForName_(suite)

    def test_languages_have_the_same_ui_strings(self):
        self.assertEqual(set(UI_TEXT["zh"]), set(UI_TEXT["en"]))


if __name__ == "__main__":
    unittest.main()
