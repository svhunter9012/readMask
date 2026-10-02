import unittest
from unittest.mock import patch
from uuid import uuid4

from AppKit import (NSApplication, NSEventModifierFlagCommand,
                    NSEventModifierFlagControl, NSScreen, NSUserDefaults)

from readmask import (COMMAND, CONTROL, DEFAULT_SHORTCUTS, GlobalHotKeys,
                      ReadMaskApp, UI_TEXT, focus_rectangle,
                      has_saved_preferences, migrate_legacy_preferences,
                      preferred_ui_language, shortcut_from_event, shortcut_title)


class KeyEvent:
    def __init__(self, key_code, flags, characters):
        self.key_code = key_code
        self.flags = flags
        self.characters = characters

    def keyCode(self):
        return self.key_code

    def modifierFlags(self):
        return self.flags

    def charactersIgnoringModifiers(self):
        return self.characters


class CarbonFunction:
    def __init__(self, result):
        self.result = result

    def __call__(self, *args):
        return self.result(*args) if callable(self.result) else self.result


class FakeCarbon:
    def __init__(self):
        self.GetApplicationEventTarget = CarbonFunction(1)
        self.InstallEventHandler = CarbonFunction(0)
        self.RegisterEventHotKey = CarbonFunction(
            lambda key_code, modifiers, hotkey_id, target, options, ref:
            -1 if hotkey_id.identifier == 2 else 0
        )
        self.GetEventParameter = CarbonFunction(0)
        self.UnregisterEventHotKey = CarbonFunction(0)
        self.RemoveEventHandler = CarbonFunction(0)


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
            first.shortcuts[1] = (15, CONTROL | COMMAND, "R")
            first.shortcuts[2] = None
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
            self.assertEqual(second.shortcuts[1], (15, CONTROL | COMMAND, "R"))
            self.assertIsNone(second.shortcuts[2])
            self.assertEqual(second.anchor_sizes, {"move": 60, "resize": 36})
            self.assertEqual(second.anchor_transparencies, {"move": 0.7, "resize": 0.3})
            self.assertEqual(second.fixed_point, (123.5, 456.5))
        finally:
            defaults.removePersistentDomainForName_(suite)

    def test_languages_have_the_same_ui_strings(self):
        self.assertEqual(set(UI_TEXT["zh"]), set(UI_TEXT["en"]))

    def test_first_launch_uses_system_language_and_existing_settings(self):
        self.assertEqual(preferred_ui_language(["zh-Hans-CN", "en-US"]), "zh")
        self.assertEqual(preferred_ui_language(["en-US", "zh-Hans-CN"]), "en")
        self.assertEqual(preferred_ui_language(["fr-FR"]), "en")
        suite = "app.readmask.test." + uuid4().hex
        defaults = NSUserDefaults.alloc().initWithSuiteName_(suite)
        try:
            self.assertFalse(has_saved_preferences(defaults))
            self.assertTrue(migrate_legacy_preferences(
                defaults, {"enabled": False, "language": "en", "unrelated": 1}
            ))
            self.assertTrue(has_saved_preferences(defaults))
            self.assertFalse(defaults.boolForKey_("enabled"))
            self.assertEqual(defaults.stringForKey_("language"), "en")
            self.assertIsNone(defaults.objectForKey_("unrelated"))
            self.assertFalse(migrate_legacy_preferences(defaults, {"enabled": True}))
        finally:
            defaults.removePersistentDomainForName_(suite)

    def test_shortcut_capture_and_conflict_are_independent(self):
        flags = NSEventModifierFlagControl | NSEventModifierFlagCommand
        binding = shortcut_from_event(KeyEvent(15, flags, "r"))
        self.assertEqual(binding, (15, CONTROL | COMMAND, "R"))
        self.assertEqual(shortcut_title(binding), "⌃⌘R")
        self.assertEqual(shortcut_from_event(KeyEvent(53, 0, "")), "cancel")
        self.assertIsNone(shortcut_from_event(KeyEvent(51, 0, "")))
        self.assertEqual(shortcut_from_event(KeyEvent(15, 0, "r")), "invalid")
        with patch("readmask.ctypes.CDLL", return_value=FakeCarbon()):
            hotkeys = GlobalHotKeys(lambda identifier: None, DEFAULT_SHORTCUTS)
            try:
                self.assertEqual(hotkeys.failed_identifiers, [2])
                self.assertEqual(len(hotkeys.hotkey_refs), 2)
            finally:
                hotkeys.close()

    def test_settings_controls_fit_in_each_tab(self):
        NSApplication.sharedApplication()
        app = ReadMaskApp.alloc().init()
        app._make_status_item()
        app._make_settings_window()
        tabs = app.controls["tabs"]
        for tab in app.tab_items.values():
            tabs.selectTabViewItem_(tab)
            view = tab.view()
            width, height = view.bounds()[1]
            for child in view.subviews():
                (x, y), (child_width, child_height) = child.frame()
                self.assertGreaterEqual(x, 0)
                self.assertGreaterEqual(y, 0)
                self.assertLessEqual(x + child_width, width)
                self.assertLessEqual(y + child_height, height)


if __name__ == "__main__":
    unittest.main()
