#!/usr/bin/python3
"""A click-through reading mask for macOS. Run with /usr/bin/python3."""

import ctypes
import objc
import sys
from pathlib import Path
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyRegular,
    NSApplicationDidChangeScreenParametersNotification,
    NSBackingStoreBuffered,
    NSBezierPath,
    NSBundle,
    NSButton,
    NSColor,
    NSControlStateValueOn,
    NSEvenOddWindingRule,
    NSEvent,
    NSFloatingWindowLevel,
    NSGradient,
    NSImage,
    NSLocale,
    NSNotificationCenter,
    NSObject,
    NSPanel,
    NSPopUpButton,
    NSScreen,
    NSSlider,
    NSStatusBar,
    NSSwitchButton,
    NSTabView,
    NSTabViewItem,
    NSTextField,
    NSTimer,
    NSTrackingActiveAlways,
    NSTrackingArea,
    NSTrackingInVisibleRect,
    NSTrackingMouseEnteredAndExited,
    NSVariableStatusItemLength,
    NSView,
    NSWindow,
    NSUserDefaults,
    NSEventMaskKeyDown,
    NSEventModifierFlagCommand,
    NSEventModifierFlagControl,
    NSEventModifierFlagOption,
    NSEventModifierFlagShift,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowCollectionBehaviorStationary,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskNonactivatingPanel,
    NSWindowStyleMaskTitled,
)

DEFAULT_ANCHOR_SIZE = 48
DEFAULT_RESIZE_ANCHOR_SIZE = 24
DEFAULT_ANCHOR_TRANSPARENCY = 0.9
MOVE_ANCHOR_ASPECT = 2.5
MIN_HEIGHT_RATIO = 0.05
FLOATING_OPACITY_WIDTH = 164
FLOATING_OPACITY_HEIGHT = 36
PREFERENCES_DOMAIN = "app.readmask.desktop"
LEGACY_SOURCE_DOMAIN = "com.apple.python3"
PREFERENCE_KEYS = (
    "enabled", "followsMouse", "fixedPoint", "widthRatio", "heightRatio",
    "focusHeight", "opacity", "language", "moveAnchorSize",
    "moveAnchorTransparency", "resizeAnchorSize", "resizeAnchorTransparency",
)
COMMAND = 1 << 8
SHIFT = 1 << 9
OPTION = 1 << 11
CONTROL = 1 << 12
DEFAULT_SHORTCUTS = {
    1: (0x21, CONTROL | OPTION | COMMAND, "["),
    2: (0x1E, CONTROL | OPTION | COMMAND, "]"),
    3: (0x2A, CONTROL | OPTION | COMMAND, "\\"),
}
SHORTCUT_ACTIONS = {1: "enabled", 2: "follow", 3: "move"}

UI_TEXT = {
    "zh": {
        "app_name": "阅读尺",
        "settings_tooltip": "阅读尺设置",
        "enabled": "启用盖板",
        "follow": "跟随鼠标",
        "move": "移到鼠标位置",
        "width": "阅读区宽度",
        "height": "阅读区高度",
        "opacity": "遮罩深度",
        "move_size": "移动锚点大小",
        "move_opacity": "移动锚点透明度",
        "resize_size": "缩放锚点大小",
        "resize_opacity": "缩放锚点透明度",
        "language": "语言",
        "quit": "退出",
        "move_tooltip": "拖动阅读区",
        "resize_tooltip": "拖动调整阅读区大小",
        "started": "阅读尺已启动。",
        "reading_tab": "阅读",
        "handles_tab": "锚点",
        "shortcuts_tab": "快捷键",
        "shortcut_record": "按下快捷键…",
        "shortcut_invalid": "请同时按修饰键和其他按键；Esc 取消，Delete 清除。",
        "shortcut_duplicate": "这个快捷键已用于另一项操作。",
        "shortcut_unavailable": "无法注册：{keys}。请检查是否与其他应用冲突。",
        "shortcut_reset": "恢复默认快捷键",
        "shortcut_none": "未设置",
        "shortcut_record_tooltip": "点击后按下新的快捷键",
    },
    "en": {
        "app_name": "ReadMask",
        "settings_tooltip": "ReadMask settings",
        "enabled": "Enable mask",
        "follow": "Follow pointer",
        "move": "Move to pointer",
        "width": "Focus width",
        "height": "Focus height",
        "opacity": "Mask depth",
        "move_size": "Move handle size",
        "move_opacity": "Move handle transparency",
        "resize_size": "Resize handle size",
        "resize_opacity": "Resize handle transparency",
        "language": "Language",
        "quit": "Quit",
        "move_tooltip": "Drag focus area",
        "resize_tooltip": "Drag to resize focus area",
        "started": "ReadMask is running.",
        "reading_tab": "Reading",
        "handles_tab": "Handles",
        "shortcuts_tab": "Shortcuts",
        "shortcut_record": "Press shortcut…",
        "shortcut_invalid": "Use a modifier and another key. Esc cancels; Delete clears.",
        "shortcut_duplicate": "This shortcut is already assigned to another action.",
        "shortcut_unavailable": "Could not register: {keys}. Check for conflicts with other apps.",
        "shortcut_reset": "Restore default shortcuts",
        "shortcut_none": "None",
        "shortcut_record_tooltip": "Click, then press a new keyboard shortcut",
    },
}


def rect(x, y, width, height):
    return ((x, y), (width, height))


def anchor_dimensions(kind, size):
    return (size * MOVE_ANCHOR_ASPECT, size) if kind == "move" else (size, size)


def preferred_ui_language(languages):
    return "zh" if languages and languages[0].lower().startswith("zh") else "en"


def has_saved_preferences(defaults):
    return (defaults.objectForKey_("hasLaunched") is not None
            or any(defaults.objectForKey_(key) is not None for key in PREFERENCE_KEYS))


def migrate_legacy_preferences(defaults, legacy):
    if has_saved_preferences(defaults):
        return False
    copied = False
    for key in PREFERENCE_KEYS:
        if key in legacy:
            defaults.setObject_forKey_(legacy[key], key)
            copied = True
    if copied:
        defaults.synchronize()
    return copied


def app_preferences():
    if NSBundle.mainBundle().bundleIdentifier() == PREFERENCES_DOMAIN:
        return NSUserDefaults.standardUserDefaults()
    return NSUserDefaults.alloc().initWithSuiteName_(PREFERENCES_DOMAIN)


def shortcut_title(binding):
    if binding is None:
        return None
    _, modifiers, key = binding
    return ("⌃" if modifiers & CONTROL else "") + ("⌥" if modifiers & OPTION else "") + ("⇧" if modifiers & SHIFT else "") + ("⌘" if modifiers & COMMAND else "") + key


def shortcut_from_event(event):
    key_code = event.keyCode()
    if key_code == 53:
        return "cancel"
    if key_code in (51, 117) and not event.modifierFlags() & (
        NSEventModifierFlagCommand | NSEventModifierFlagControl | NSEventModifierFlagOption
    ):
        return None
    modifiers = 0
    for cocoa_flag, carbon_flag in (
        (NSEventModifierFlagCommand, COMMAND),
        (NSEventModifierFlagControl, CONTROL),
        (NSEventModifierFlagOption, OPTION),
        (NSEventModifierFlagShift, SHIFT),
    ):
        if event.modifierFlags() & cocoa_flag:
            modifiers |= carbon_flag
    if not modifiers & (COMMAND | CONTROL | OPTION):
        return "invalid"
    key = event.charactersIgnoringModifiers() or ""
    special = {"\r": "Return", "\t": "Tab", " ": "Space", "\x7f": "Delete",
               "\uf700": "↑", "\uf701": "↓", "\uf702": "←", "\uf703": "→"}
    key = special.get(key, key.upper() if len(key) == 1 and key.isalpha() else key)
    if not key or len(key) > 12:
        return "invalid"
    return (key_code, modifiers, key)


def smoke_stage(name):
    if "--smoke" in sys.argv:
        Path("/private/tmp/readmask-smoke-result.txt").write_text(
            name + "\n", encoding="utf-8"
        )


def focus_rectangle(screen, cursor, width_ratio, height_ratio):
    """Return a screen-local focus rectangle or None if cursor is elsewhere."""
    sx, sy, sw, sh = screen
    px, py = cursor
    if not (sx <= px < sx + sw and sy <= py < sy + sh):
        return None
    width = min(sw, max(112, sw * width_ratio))
    height = sh * height_ratio
    x = min(max(px - sx - width / 2, 0), sw - width)
    y = min(max(py - sy - height / 2, 0), sh - height)
    return (x, y, width, height)


def nearest_display_point(point, frames):
    """Keep a dragged focus center on the nearest connected display."""
    if not frames:
        return point
    px, py = point
    candidates = []
    for sx, sy, sw, sh in frames:
        x = min(max(px, sx), sx + sw - 1)
        y = min(max(py, sy), sy + sh - 1)
        candidates.append((x, y))
    return min(candidates, key=lambda p: (p[0] - px) ** 2 + (p[1] - py) ** 2)


def fourcc(value):
    return int.from_bytes(value.encode("ascii"), "big")


class EventTypeSpec(ctypes.Structure):
    _fields_ = [("event_class", ctypes.c_uint32), ("event_kind", ctypes.c_uint32)]


class EventHotKeyID(ctypes.Structure):
    _fields_ = [("signature", ctypes.c_uint32), ("identifier", ctypes.c_uint32)]


class GlobalHotKeys:
    SIGNATURE = fourcc("RMSK")

    def __init__(self, on_press, shortcuts):
        self.on_press = on_press
        self.carbon = ctypes.CDLL(
            "/System/Library/Frameworks/Carbon.framework/Frameworks/HIToolbox.framework/HIToolbox"
        )
        callback_type = ctypes.CFUNCTYPE(
            ctypes.c_int32, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
        )
        self.callback = callback_type(self._handle_event)
        self.handler_ref = ctypes.c_void_p()
        self.hotkey_refs = []
        self.failed_identifiers = []

        self.carbon.GetApplicationEventTarget.restype = ctypes.c_void_p
        self.carbon.InstallEventHandler.argtypes = [
            ctypes.c_void_p, callback_type, ctypes.c_uint32,
            ctypes.POINTER(EventTypeSpec), ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        self.carbon.InstallEventHandler.restype = ctypes.c_int32
        self.carbon.RegisterEventHotKey.argtypes = [
            ctypes.c_uint32, ctypes.c_uint32, EventHotKeyID,
            ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p),
        ]
        self.carbon.RegisterEventHotKey.restype = ctypes.c_int32
        self.carbon.GetEventParameter.argtypes = [
            ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32,
            ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_void_p,
        ]
        self.carbon.GetEventParameter.restype = ctypes.c_int32
        self.carbon.UnregisterEventHotKey.argtypes = [ctypes.c_void_p]
        self.carbon.RemoveEventHandler.argtypes = [ctypes.c_void_p]

        target = self.carbon.GetApplicationEventTarget()
        event_type = EventTypeSpec(fourcc("keyb"), 5)
        status = self.carbon.InstallEventHandler(
            target, self.callback, 1, ctypes.byref(event_type),
            None, ctypes.byref(self.handler_ref),
        )
        if status != 0:
            raise RuntimeError("Cannot install hotkey handler: %d" % status)

        for identifier, binding in shortcuts.items():
            if binding is None:
                continue
            key_code, modifiers, _ = binding
            hotkey_ref = ctypes.c_void_p()
            status = self.carbon.RegisterEventHotKey(
                key_code, modifiers,
                EventHotKeyID(self.SIGNATURE, identifier),
                target, 1, ctypes.byref(hotkey_ref),
            )
            if status != 0:
                self.failed_identifiers.append(identifier)
            else:
                self.hotkey_refs.append(hotkey_ref)

    def _handle_event(self, next_handler, event, user_data):
        hotkey = EventHotKeyID()
        status = self.carbon.GetEventParameter(
            event, fourcc("----"), fourcc("hkid"), None,
            ctypes.sizeof(hotkey), None, ctypes.byref(hotkey),
        )
        if status != 0 or hotkey.signature != self.SIGNATURE:
            return -9874  # eventNotHandledErr
        try:
            self.on_press(hotkey.identifier)
        except Exception as error:
            print("快捷键执行失败: %s" % error, file=sys.stderr, flush=True)
            return -9874
        return 0

    def close(self):
        for hotkey_ref in self.hotkey_refs:
            self.carbon.UnregisterEventHotKey(hotkey_ref)
        self.hotkey_refs.clear()
        if self.handler_ref.value:
            self.carbon.RemoveEventHandler(self.handler_ref)
            self.handler_ref = ctypes.c_void_p()


class MaskView(NSView):
    focus = objc.ivar()
    opacity = objc.ivar()

    def isOpaque(self):
        return False

    def drawRect_(self, dirty_rect):
        path = NSBezierPath.bezierPathWithRect_(self.bounds())
        if self.focus is not None:
            path.appendBezierPathWithRect_(rect(*self.focus))
            path.setWindingRule_(NSEvenOddWindingRule)
        NSColor.blackColor().colorWithAlphaComponent_(self.opacity).setFill()
        path.fill()
        if self.focus is not None:
            NSColor.whiteColor().colorWithAlphaComponent_(0.35).setStroke()
            outline = NSBezierPath.bezierPathWithRect_(rect(*self.focus))
            outline.setLineWidth_(1)
            outline.stroke()


class SliderBackgroundView(NSView):
    owner = objc.ivar()
    hovered = objc.ivar()

    def isOpaque(self):
        return False

    def mouseEntered_(self, event):
        self.hovered = True
        self.window().setAlphaValue_(1.0)

    def mouseExited_(self, event):
        self.hovered = False
        self.window().setAlphaValue_(
            1.0 - self.owner.anchor_transparencies["move"]
        )

    def drawRect_(self, dirty_rect):
        background = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            self.bounds(), 8, 8
        )
        NSColor.colorWithCalibratedRed_green_blue_alpha_(0.11, 0.16, 0.18, 0.94).setFill()
        background.fill()
        NSColor.colorWithCalibratedRed_green_blue_alpha_(0.75, 0.88, 0.84, 0.72).setStroke()
        background.setLineWidth_(1)
        background.stroke()


class FloatingOpacitySlider(NSView):
    owner = objc.ivar()
    value = objc.ivar()

    def isOpaque(self):
        return False

    def doubleValue(self):
        return self.value

    def setDoubleValue_(self, value):
        self.value = min(1.0, max(0.0, value))
        self.setNeedsDisplay_(True)

    def drawRect_(self, dirty_rect):
        bounds = self.bounds()
        track = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            rect(12, 8, bounds[1][0] - 24, 10), 5, 5
        )
        gradient = NSGradient.alloc().initWithStartingColor_endingColor_(
            NSColor.colorWithCalibratedWhite_alpha_(0.89, 1.0),
            NSColor.colorWithCalibratedWhite_alpha_(0.18, 1.0),
        )
        gradient.drawInBezierPath_angle_(track, 0)
        NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.7).setStroke()
        track.setLineWidth_(1)
        track.stroke()
        progress = self.value
        center_x = 12 + progress * (bounds[1][0] - 24)
        thumb = NSBezierPath.bezierPathWithOvalInRect_(
            rect(center_x - 7, 6, 14, 14)
        )
        NSColor.colorWithCalibratedWhite_alpha_(1.0, 1.0).setFill()
        thumb.fill()
        NSColor.colorWithCalibratedWhite_alpha_(0.12, 0.85).setStroke()
        thumb.setLineWidth_(1)
        thumb.stroke()

    def mouseDown_(self, event):
        self._set_value_from_event(event)

    def mouseDragged_(self, event):
        self._set_value_from_event(event)

    @objc.python_method
    def _set_value_from_event(self, event):
        x = self.convertPoint_fromView_(event.locationInWindow(), None)[0]
        progress = min(1.0, max(0.0, (x - 12) / (self.bounds()[1][0] - 24)))
        self.setDoubleValue_(progress)
        self.owner.opacityChanged_(self)


class AnchorView(NSView):
    owner = objc.ivar()
    kind = objc.ivar()

    def isOpaque(self):
        return False

    def acceptsFirstMouse_(self, event):
        return True

    def drawRect_(self, dirty_rect):
        scale = self.bounds()[1][1] / 48
        width = self.bounds()[1][0]
        height = self.bounds()[1][1]
        glyph_center_x = 60 if self.kind == "move" else 24

        def glyph_point(x, y):
            return ((glyph_center_x + (x - glyph_center_x) * 0.7) * scale,
                    (24 + (y - 24) * 0.7) * scale)

        background = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            rect(1.5 * scale, 1.5 * scale,
                 width - 3 * scale, height - 3 * scale),
            height / 2 - 1.5 * scale, height / 2 - 1.5 * scale,
        )
        NSColor.colorWithCalibratedRed_green_blue_alpha_(0.11, 0.16, 0.18, 0.94).setFill()
        background.fill()
        NSColor.colorWithCalibratedRed_green_blue_alpha_(0.75, 0.88, 0.84, 0.72).setStroke()
        background.setLineWidth_(1.3 * scale)
        background.stroke()

        def stroke_segments(segments, color, line_width):
            path = NSBezierPath.bezierPath()
            for start, end in segments:
                path.moveToPoint_(glyph_point(*start))
                path.lineToPoint_(glyph_point(*end))
            path.setLineCapStyle_(1)
            path.setLineJoinStyle_(1)
            path.setLineWidth_(line_width * scale * 0.8)
            color.setStroke()
            path.stroke()

        accent = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.53, 0.88, 0.75, 1)
        white = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.96, 0.98, 0.97, 1)
        if self.kind == "move":
            pointer = NSBezierPath.bezierPath()
            pointer.moveToPoint_(glyph_point(31, 38))
            for x, y in ((31, 12), (38, 19), (43, 11),
                         (48, 14), (43, 22), (53, 22)):
                pointer.lineToPoint_(glyph_point(x, y))
            pointer.closePath()
            white.setFill()
            pointer.fill()
            stroke_segments((
                ((76, 13), (76, 35)), ((65, 24), (87, 24)),
                ((76, 35), (72, 31)), ((76, 35), (80, 31)),
                ((76, 13), (72, 17)), ((76, 13), (80, 17)),
                ((65, 24), (69, 28)), ((65, 24), (69, 20)),
                ((87, 24), (83, 28)), ((87, 24), (83, 20)),
            ), accent, 2.1)
        else:
            stroke_segments((
                ((14, 14), (34, 34)),
                ((14, 14), (14, 22)), ((14, 14), (22, 14)),
                ((34, 34), (26, 34)), ((34, 34), (34, 26)),
            ), white, 2.3)

    def mouseEntered_(self, event):
        self.window().setAlphaValue_(1.0)

    def mouseExited_(self, event):
        if self.owner.drag_kind != self.kind:
            self.window().setAlphaValue_(
                1.0 - self.owner.anchor_transparencies[self.kind]
            )

    def mouseDown_(self, event):
        self.window().setAlphaValue_(1.0)
        self.owner.begin_anchor_drag(self.kind)

    def mouseDragged_(self, event):
        self.owner.update_anchor_drag(NSEvent.mouseLocation())

    def mouseUp_(self, event):
        self.owner.end_anchor_drag()
        frame = self.window().frame()
        mouse = NSEvent.mouseLocation()
        inside = (frame[0][0] <= mouse[0] < frame[0][0] + frame[1][0]
                  and frame[0][1] <= mouse[1] < frame[0][1] + frame[1][1])
        self.window().setAlphaValue_(
            1.0 if inside else 1.0 - self.owner.anchor_transparencies[self.kind]
        )


class ReadMaskApp(NSObject):
    def init(self):
        self = objc.super(ReadMaskApp, self).init()
        if self is not None:
            self.enabled = True
            self.follows_mouse = True
            self.width_ratio = 0.75
            self.height_ratio = 0.15
            self.opacity = 0.5
            self.language = preferred_ui_language(NSLocale.preferredLanguages())
            self.shortcuts = dict(DEFAULT_SHORTCUTS)
            self.anchor_sizes = {"move": DEFAULT_ANCHOR_SIZE,
                                 "resize": DEFAULT_RESIZE_ANCHOR_SIZE}
            self.anchor_transparencies = {"move": DEFAULT_ANCHOR_TRANSPARENCY,
                                          "resize": DEFAULT_ANCHOR_TRANSPARENCY}
            self.fixed_point = None
            self.last_point = None
            self.overlays = []
            self.anchor_panels = {}
            self.opacity_panel = None
            self.controls = {}
            self.hotkeys = None
            self.hotkey_errors = []
            self.shortcut_monitor = None
            self.recording_shortcut = None
            self.shortcut_feedback = None
            self.drag_kind = None
            self.drag_focus_point = None
            self.preferences = app_preferences()
            if "--smoke" not in sys.argv:
                self._migrate_legacy_preferences()
                self.first_launch = not has_saved_preferences(self.preferences)
                self._load_preferences()
            else:
                self.first_launch = False
        return self

    @objc.python_method
    def _text(self, key):
        return UI_TEXT[self.language][key]

    @objc.python_method
    def _migrate_legacy_preferences(self):
        legacy = (NSUserDefaults.standardUserDefaults()
                  .persistentDomainForName_(LEGACY_SOURCE_DOMAIN) or {})
        migrate_legacy_preferences(self.preferences, legacy)

    @objc.python_method
    def _load_preferences(self):
        defaults = self.preferences
        language = defaults.stringForKey_("language")
        if language in UI_TEXT:
            self.language = language
        for key, attribute in (("enabled", "enabled"),
                               ("followsMouse", "follows_mouse")):
            if defaults.objectForKey_(key) is not None:
                setattr(self, attribute, bool(defaults.boolForKey_(key)))
        saved_point = defaults.arrayForKey_("fixedPoint")
        if saved_point is not None and len(saved_point) == 2:
            self.fixed_point = (float(saved_point[0]), float(saved_point[1]))
        for key, attribute, low, high in (
            ("widthRatio", "width_ratio", 0.2, 1.0),
            ("heightRatio", "height_ratio", MIN_HEIGHT_RATIO, 1.0),
            ("opacity", "opacity", 0.0, 1.0),
        ):
            if defaults.objectForKey_(key) is not None:
                setattr(self, attribute, min(high, max(low, defaults.doubleForKey_(key))))
        if (defaults.objectForKey_("heightRatio") is None
                and defaults.objectForKey_("focusHeight") is not None):
            point = (self.fixed_point if not self.follows_mouse and self.fixed_point
                     else tuple(NSEvent.mouseLocation()))
            screen = next((screen for screen in NSScreen.screens()
                           if focus_rectangle(
                               (screen.frame()[0][0], screen.frame()[0][1],
                                screen.frame()[1][0], screen.frame()[1][1]),
                               point, self.width_ratio, self.height_ratio,
                           ) is not None), NSScreen.mainScreen())
            if screen is not None:
                screen_height = screen.frame()[1][1]
                self.height_ratio = min(1.0, max(
                    MIN_HEIGHT_RATIO,
                    defaults.doubleForKey_("focusHeight") / screen_height,
                ))
                defaults.setDouble_forKey_(self.height_ratio, "heightRatio")
                defaults.synchronize()
        for kind in ("move", "resize"):
            size_key = kind + "AnchorSize"
            transparency_key = kind + "AnchorTransparency"
            if defaults.objectForKey_(size_key) is not None:
                self.anchor_sizes[kind] = round(min(96, max(24, defaults.doubleForKey_(size_key))))
            if defaults.objectForKey_(transparency_key) is not None:
                self.anchor_transparencies[kind] = min(
                    0.9, max(0.0, defaults.doubleForKey_(transparency_key))
                )
        for identifier in DEFAULT_SHORTCUTS:
            prefix = "shortcut.%d." % identifier
            if defaults.objectForKey_(prefix + "enabled") is None:
                continue
            if not defaults.boolForKey_(prefix + "enabled"):
                self.shortcuts[identifier] = None
            elif defaults.objectForKey_(prefix + "keyCode") is not None:
                self.shortcuts[identifier] = (
                    defaults.integerForKey_(prefix + "keyCode"),
                    defaults.integerForKey_(prefix + "modifiers"),
                    defaults.stringForKey_(prefix + "keyLabel") or
                    DEFAULT_SHORTCUTS[identifier][2],
                )

    @objc.python_method
    def _save_preferences(self):
        if "--smoke" in sys.argv:
            return
        defaults = self.preferences
        defaults.setBool_forKey_(self.enabled, "enabled")
        defaults.setBool_forKey_(self.follows_mouse, "followsMouse")
        defaults.setDouble_forKey_(self.width_ratio, "widthRatio")
        defaults.setDouble_forKey_(self.height_ratio, "heightRatio")
        defaults.setDouble_forKey_(self.opacity, "opacity")
        defaults.setObject_forKey_(self.language, "language")
        defaults.setBool_forKey_(True, "hasLaunched")
        for kind in ("move", "resize"):
            defaults.setDouble_forKey_(self.anchor_sizes[kind], kind + "AnchorSize")
            defaults.setDouble_forKey_(
                self.anchor_transparencies[kind], kind + "AnchorTransparency"
            )
        if self.fixed_point is not None:
            defaults.setObject_forKey_(list(self.fixed_point), "fixedPoint")
        for identifier, binding in self.shortcuts.items():
            prefix = "shortcut.%d." % identifier
            defaults.setBool_forKey_(binding is not None, prefix + "enabled")
            if binding is not None:
                key_code, modifiers, key_label = binding
                defaults.setInteger_forKey_(key_code, prefix + "keyCode")
                defaults.setInteger_forKey_(modifiers, prefix + "modifiers")
                defaults.setObject_forKey_(key_label, prefix + "keyLabel")
        defaults.synchronize()

    def applicationDidFinishLaunching_(self, notification):
        NSApplication.sharedApplication().setActivationPolicy_(
            NSApplicationActivationPolicyRegular
        )
        self._make_status_item()
        self._make_settings_window()
        self._make_anchors()
        self._make_opacity_control()
        self._rebuild_overlays()
        self._register_hotkeys()
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
            self, "screensChanged:", NSApplicationDidChangeScreenParametersNotification, None
        )
        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1 / 30, self, "tick:", None, True
        )
        if "--smoke" in sys.argv:
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                0.2, self, "smokeTest:", None, False
            )
        else:
            if self.hotkey_errors:
                self.controls["tabs"].selectTabViewItem_(self.tab_items["shortcuts"])
            if self.first_launch or self.hotkey_errors:
                self.showSettings_(None)
            self.preferences.setBool_forKey_(True, "hasLaunched")
            self.preferences.synchronize()

    @objc.python_method
    def _register_hotkeys(self):
        if self.hotkeys is not None:
            self.hotkeys.close()
            self.hotkeys = None
        try:
            self.hotkeys = GlobalHotKeys(self._perform_hotkey, self.shortcuts)
            self.hotkey_errors = self.hotkeys.failed_identifiers
        except RuntimeError:
            self.hotkey_errors = [identifier for identifier, binding in self.shortcuts.items()
                                  if binding is not None]
        if "shortcut_warning" in self.controls:
            self._refresh_shortcut_display()

    @objc.python_method
    def _make_status_item(self):
        self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSVariableStatusItemLength
        )
        button = self.status_item.button()
        icon = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
            "text.viewfinder", self._text("app_name")
        )
        if icon is not None:
            button.setImage_(icon)
        else:
            button.setTitle_("▣")
        button.setToolTip_(self._text("settings_tooltip"))
        button.setTarget_(self)
        button.setAction_("showSettings:")

    @objc.python_method
    def _make_settings_window(self):
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect(0, 0, 420, 450),
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_(self._text("app_name"))
        self.window.setLevel_(NSFloatingWindowLevel + 1)
        self.window.center()
        self.window.setReleasedWhenClosed_(False)
        self.window.setDelegate_(self)
        content = self.window.contentView()

        tabs = NSTabView.alloc().initWithFrame_(rect(10, 48, 400, 390))
        content.addSubview_(tabs)
        self.controls["tabs"] = tabs
        self.tab_items = {}
        tab_views = {}
        for key in ("reading", "handles", "shortcuts"):
            item = NSTabViewItem.alloc().initWithIdentifier_(key)
            item.setLabel_(self._text(key + "_tab"))
            view = NSView.alloc().initWithFrame_(rect(0, 0, 392, 350))
            item.setView_(view)
            tabs.addTabViewItem_(item)
            self.tab_items[key] = item
            tab_views[key] = view
        tabs.selectTabViewItem_(self.tab_items["reading"])
        tabs.setDelegate_(self)
        reading = tab_views["reading"]
        handles = tab_views["handles"]
        shortcuts = tab_views["shortcuts"]

        self.controls["enabled"] = self._checkbox(
            reading, "enabled", 300, self.enabled, "toggleEnabled:"
        )
        self.controls["follow"] = self._checkbox(
            reading, "follow", 268, self.follows_mouse, "toggleFollow:"
        )
        move = NSButton.alloc().initWithFrame_(rect(18, 229, 210, 26))
        move.setTitle_(self._text("move"))
        move.setTarget_(self)
        move.setAction_("moveToMouse:")
        reading.addSubview_(move)
        self.controls["move"] = move

        self.controls["width"] = self._slider(
            reading, "width", 165, 0.2, 1.0, self.width_ratio, "widthChanged:"
        )
        self.controls["height"] = self._slider(
            reading, "height", 105, MIN_HEIGHT_RATIO, 1.0,
            self.height_ratio, "heightChanged:"
        )
        self.controls["opacity"] = self._slider(
            reading, "opacity", 45, 0.0, 1.0, self.opacity, "opacityChanged:"
        )
        self.controls["move_size"] = self._slider(
            handles, "move_size", 265, 24, 96,
            self.anchor_sizes["move"], "moveSizeChanged:"
        )
        self.controls["move_opacity"] = self._slider(
            handles, "move_opacity", 195, 0.0, 0.9,
            self.anchor_transparencies["move"], "moveOpacityChanged:"
        )
        self.controls["resize_size"] = self._slider(
            handles, "resize_size", 125, 24, 96,
            self.anchor_sizes["resize"], "resizeSizeChanged:"
        )
        self.controls["resize_opacity"] = self._slider(
            handles, "resize_opacity", 55, 0.0, 0.9,
            self.anchor_transparencies["resize"], "resizeOpacityChanged:"
        )
        for identifier, y in ((1, 265), (2, 195), (3, 125)):
            action = SHORTCUT_ACTIONS[identifier]
            label = NSTextField.labelWithString_(self._text(action))
            label.setFrame_(rect(18, y + 3, 180, 22))
            shortcuts.addSubview_(label)
            self.controls["shortcut_%d_title" % identifier] = label
            button = NSButton.alloc().initWithFrame_(rect(205, y, 172, 28))
            button.setTitle_(shortcut_title(self.shortcuts[identifier]) or self._text("shortcut_none"))
            button.setToolTip_(self._text("shortcut_record_tooltip"))
            button.setTag_(identifier)
            button.setTarget_(self)
            button.setAction_("recordShortcut:")
            shortcuts.addSubview_(button)
            self.controls["shortcut_%d" % identifier] = button
        warning = NSTextField.labelWithString_("")
        warning.setFrame_(rect(18, 55, 360, 52))
        warning.setTextColor_(NSColor.systemRedColor())
        warning.setUsesSingleLineMode_(False)
        warning.cell().setWraps_(True)
        shortcuts.addSubview_(warning)
        self.controls["shortcut_warning"] = warning
        reset = NSButton.alloc().initWithFrame_(rect(18, 15, 190, 28))
        reset.setTitle_(self._text("shortcut_reset"))
        reset.setTarget_(self)
        reset.setAction_("resetShortcuts:")
        shortcuts.addSubview_(reset)
        self.controls["shortcut_reset"] = reset
        language_label = NSTextField.labelWithString_(self._text("language"))
        language_label.setFrame_(rect(18, 15, 82, 20))
        content.addSubview_(language_label)
        self.controls["language_label"] = language_label
        language = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            rect(108, 10, 152, 26), False
        )
        language.addItemsWithTitles_(["中文", "English"])
        language.selectItemAtIndex_(0 if self.language == "zh" else 1)
        language.setTarget_(self)
        language.setAction_("languageChanged:")
        content.addSubview_(language)
        self.controls["language"] = language
        quit_button = NSButton.alloc().initWithFrame_(rect(330, 12, 70, 26))
        quit_button.setTitle_(self._text("quit"))
        quit_button.setTarget_(self)
        quit_button.setAction_("quit:")
        content.addSubview_(quit_button)
        self.controls["quit"] = quit_button
        self._sync_labels()
        self._refresh_shortcut_display()

    @objc.python_method
    def _checkbox(self, content, key, y, checked, action):
        button = NSButton.alloc().initWithFrame_(rect(18, y, 220, 24))
        button.setButtonType_(NSSwitchButton)
        button.setTitle_(self._text(key))
        button.setState_(NSControlStateValueOn if checked else 0)
        button.setTarget_(self)
        button.setAction_(action)
        content.addSubview_(button)
        return button

    @objc.python_method
    def _slider(self, content, key, y, minimum, maximum, value, action):
        label = NSTextField.labelWithString_(self._text(key))
        label.setFrame_(rect(18, y + 25, 240, 20))
        content.addSubview_(label)
        self.controls[key + "_title"] = label
        value_label = NSTextField.labelWithString_("")
        value_label.setFrame_(rect(280, y + 25, 100, 20))
        value_label.setAlignment_(2)
        content.addSubview_(value_label)
        slider = NSSlider.alloc().initWithFrame_(rect(18, y, 362, 24))
        slider.setMinValue_(minimum)
        slider.setMaxValue_(maximum)
        slider.setDoubleValue_(value)
        slider.setContinuous_(True)
        slider.setTarget_(self)
        slider.setAction_(action)
        content.addSubview_(slider)
        self.controls[key + "_label"] = value_label
        return slider

    @objc.python_method
    def _sync_labels(self):
        self.controls["width_label"].setStringValue_(
            "%d%%" % round(self.width_ratio * 100)
        )
        self.controls["height_label"].setStringValue_(
            "%d%%" % round(self.height_ratio * 100)
        )
        self.controls["opacity_label"].setStringValue_(
            "%d%%" % round(self.opacity * 100)
        )
        for kind in ("move", "resize"):
            self.controls[kind + "_size_label"].setStringValue_(
                "%d×%d pt" % anchor_dimensions(kind, self.anchor_sizes[kind])
            )
            self.controls[kind + "_opacity_label"].setStringValue_(
                "%d%%" % round(self.anchor_transparencies[kind] * 100)
            )
        self.controls["move"].setEnabled_(not self.follows_mouse)

    @objc.python_method
    def _apply_language(self):
        self.window.setTitle_(self._text("app_name"))
        button = self.status_item.button()
        button.setToolTip_(self._text("settings_tooltip"))
        icon = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
            "text.viewfinder", self._text("app_name")
        )
        if icon is not None:
            button.setImage_(icon)
        for key in ("enabled", "follow", "move", "quit"):
            self.controls[key].setTitle_(self._text(key))
        for key, item in self.tab_items.items():
            item.setLabel_(self._text(key + "_tab"))
        self.controls["language_label"].setStringValue_(self._text("language"))
        for key in ("width", "height", "opacity", "move_size", "move_opacity",
                    "resize_size", "resize_opacity"):
            self.controls[key + "_title"].setStringValue_(self._text(key))
        for identifier, action in SHORTCUT_ACTIONS.items():
            self.controls["shortcut_%d_title" % identifier].setStringValue_(self._text(action))
            self.controls["shortcut_%d" % identifier].setToolTip_(self._text("shortcut_record_tooltip"))
        self.controls["shortcut_reset"].setTitle_(self._text("shortcut_reset"))
        self._refresh_shortcut_display()
        for kind, panel in self.anchor_panels.items():
            panel.contentView().setToolTip_(self._text(kind + "_tooltip"))
        self.controls["floating_opacity"].setToolTip_(self._text("opacity"))

    @objc.python_method
    def _refresh_shortcut_display(self):
        for identifier, binding in self.shortcuts.items():
            title = (self._text("shortcut_record") if self.recording_shortcut == identifier
                     else shortcut_title(binding) or self._text("shortcut_none"))
            self.controls["shortcut_%d" % identifier].setTitle_(title)
        if self.shortcut_feedback:
            message = self._text(self.shortcut_feedback)
        elif self.recording_shortcut is not None:
            message = self._text("shortcut_invalid")
        elif self.hotkey_errors:
            keys = ", ".join(shortcut_title(self.shortcuts[identifier])
                             for identifier in self.hotkey_errors)
            message = self._text("shortcut_unavailable").format(keys=keys)
        else:
            message = ""
        self.controls["shortcut_warning"].setStringValue_(message)

    @objc.python_method
    def _make_anchors(self):
        for kind in ("move", "resize"):
            panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
                rect(0, 0, *anchor_dimensions(kind, self.anchor_sizes[kind])),
                NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
                NSBackingStoreBuffered,
                False,
            )
            panel.setLevel_(NSFloatingWindowLevel + 1)
            panel.setCollectionBehavior_(
                NSWindowCollectionBehaviorCanJoinAllSpaces
                | NSWindowCollectionBehaviorFullScreenAuxiliary
                | NSWindowCollectionBehaviorStationary
            )
            panel.setOpaque_(False)
            panel.setBackgroundColor_(NSColor.clearColor())
            panel.setHasShadow_(False)
            panel.setAlphaValue_(1.0 - self.anchor_transparencies[kind])
            view = AnchorView.new()
            view.setFrame_(rect(0, 0, *anchor_dimensions(kind, self.anchor_sizes[kind])))
            view.owner = self
            view.kind = kind
            view.setToolTip_(self._text(kind + "_tooltip"))
            tracking = NSTrackingArea.alloc().initWithRect_options_owner_userInfo_(
                view.bounds(),
                NSTrackingMouseEnteredAndExited
                | NSTrackingActiveAlways
                | NSTrackingInVisibleRect,
                view,
                None,
            )
            view.addTrackingArea_(tracking)
            panel.setContentView_(view)
            self.anchor_panels[kind] = panel

    @objc.python_method
    def _make_opacity_control(self):
        panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            rect(0, 0, FLOATING_OPACITY_WIDTH, FLOATING_OPACITY_HEIGHT),
            NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
            NSBackingStoreBuffered,
            False,
        )
        panel.setLevel_(NSFloatingWindowLevel + 1)
        panel.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorFullScreenAuxiliary
            | NSWindowCollectionBehaviorStationary
        )
        panel.setOpaque_(False)
        panel.setBackgroundColor_(NSColor.clearColor())
        panel.setHasShadow_(False)
        panel.setAlphaValue_(1.0 - self.anchor_transparencies["move"])
        background = SliderBackgroundView.new()
        background.setFrame_(rect(0, 0, FLOATING_OPACITY_WIDTH, FLOATING_OPACITY_HEIGHT))
        background.owner = self
        background.hovered = False
        tracking = NSTrackingArea.alloc().initWithRect_options_owner_userInfo_(
            background.bounds(),
            NSTrackingMouseEnteredAndExited
            | NSTrackingActiveAlways
            | NSTrackingInVisibleRect,
            background,
            None,
        )
        background.addTrackingArea_(tracking)
        slider = FloatingOpacitySlider.alloc().initWithFrame_(
            rect(10, 5, FLOATING_OPACITY_WIDTH - 20, 26)
        )
        slider.owner = self
        slider.setDoubleValue_(self.opacity)
        slider.setToolTip_(self._text("opacity"))
        background.addSubview_(slider)
        panel.setContentView_(background)
        self.opacity_panel = panel
        self.controls["floating_opacity"] = slider

    @objc.python_method
    def _rebuild_overlays(self):
        for panel, _ in self.overlays:
            panel.close()
        self.overlays = []
        for screen in NSScreen.screens():
            frame = screen.frame()
            panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
                frame,
                NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
                NSBackingStoreBuffered,
                False,
            )
            panel.setLevel_(NSFloatingWindowLevel)
            panel.setCollectionBehavior_(
                NSWindowCollectionBehaviorCanJoinAllSpaces
                | NSWindowCollectionBehaviorFullScreenAuxiliary
                | NSWindowCollectionBehaviorStationary
            )
            panel.setIgnoresMouseEvents_(True)
            panel.setOpaque_(False)
            panel.setBackgroundColor_(NSColor.clearColor())
            panel.setHasShadow_(False)
            view = MaskView.new()
            view.setFrame_(rect(0, 0, frame[1][0], frame[1][1]))
            view.focus = None
            view.opacity = self.opacity
            panel.setContentView_(view)
            self.overlays.append((panel, screen))
            if self.enabled:
                panel.orderFrontRegardless()
        if self.fixed_point is not None:
            frames = [
                (frame[0][0], frame[0][1], frame[1][0], frame[1][1])
                for _, screen in self.overlays for frame in (screen.frame(),)
            ]
            self.fixed_point = nearest_display_point(self.fixed_point, frames)
        self._redraw()

    @objc.python_method
    def _redraw(self):
        mouse = NSEvent.mouseLocation()
        point = self.drag_focus_point
        if point is None:
            point = mouse if self.follows_mouse or self.fixed_point is None else self.fixed_point
        active = None
        for panel, screen in self.overlays:
            frame = screen.frame()
            view = panel.contentView()
            view.focus = focus_rectangle(
                (frame[0][0], frame[0][1], frame[1][0], frame[1][1]),
                point,
                self.width_ratio,
                self.height_ratio,
            )
            view.opacity = self.opacity
            view.setNeedsDisplay_(True)
            if view.focus is not None:
                active = (screen, view.focus)
        self._position_anchors(active)

    @objc.python_method
    def _position_anchors(self, active):
        if not self.enabled or active is None:
            for panel in self.anchor_panels.values():
                panel.orderOut_(None)
            self.opacity_panel.orderOut_(None)
            return
        screen, focus = active
        origin = screen.frame()[0]
        x, y, width, height = focus
        move_size = self.anchor_sizes["move"]
        resize_size = self.anchor_sizes["resize"]
        move_width, _ = anchor_dimensions("move", move_size)
        move_x = min(max(x + width * 0.6 - move_width / 2, 0),
                     screen.frame()[1][0] - move_width)
        positions = {
            "move": (origin[0] + move_x,
                     origin[1] + max(y - move_size, 0)),
            "resize": (origin[0] + x + width - resize_size - 5,
                       origin[1] + y + 5),
        }
        for kind, panel in self.anchor_panels.items():
            if self.follows_mouse:
                panel.orderOut_(None)
                continue
            px, py = positions[kind]
            anchor_width, anchor_height = anchor_dimensions(
                kind, self.anchor_sizes[kind]
            )
            panel.contentView().setFrame_(rect(0, 0, anchor_width, anchor_height))
            panel.setFrame_display_(
                rect(px, py, anchor_width, anchor_height), True
            )
            if not panel.isVisible():
                panel.orderFrontRegardless()
        if self.follows_mouse:
            self.opacity_panel.orderOut_(None)
        else:
            available_left = move_x - 8
            available_right = screen.frame()[1][0] - move_x - move_width - 8
            if available_left >= FLOATING_OPACITY_WIDTH or available_left >= available_right:
                slider_width = min(FLOATING_OPACITY_WIDTH, available_left)
                slider_x = move_x - slider_width - 8
            else:
                slider_width = min(FLOATING_OPACITY_WIDTH, available_right)
                slider_x = move_x + move_width + 8
            slider_width = max(60, slider_width)
            slider_y = max(y - move_size, 0) + (move_size - FLOATING_OPACITY_HEIGHT) / 2
            self.opacity_panel.contentView().setFrame_(
                rect(0, 0, slider_width, FLOATING_OPACITY_HEIGHT)
            )
            self.controls["floating_opacity"].setFrame_(
                rect(10, 5, slider_width - 20, 26)
            )
            self.controls["floating_opacity"].setNeedsDisplay_(True)
            self.opacity_panel.setFrame_display_(
                rect(origin[0] + slider_x, origin[1] + slider_y,
                     slider_width, FLOATING_OPACITY_HEIGHT), True
            )
            if not self.opacity_panel.isVisible():
                self.opacity_panel.orderFrontRegardless()

    @objc.python_method
    def begin_anchor_drag(self, kind):
        if not self.enabled or (kind == "move" and self.follows_mouse):
            return
        self.drag_kind = kind
        self.drag_start_mouse = tuple(NSEvent.mouseLocation())
        self.drag_focus_point = (
            self.drag_start_mouse if self.follows_mouse or self.fixed_point is None
            else tuple(self.fixed_point)
        )
        self.drag_start_focus = self.drag_focus_point
        self.drag_start_width = self.width_ratio
        self.drag_start_height = self.height_ratio
        self.drag_screen = next(
            (screen for _, screen in self.overlays if
             focus_rectangle(
                 (screen.frame()[0][0], screen.frame()[0][1],
                  screen.frame()[1][0], screen.frame()[1][1]),
                 self.drag_focus_point, self.width_ratio, self.height_ratio,
             ) is not None),
            None,
        )

    @objc.python_method
    def update_anchor_drag(self, mouse):
        if self.drag_kind is None:
            return
        dx = mouse[0] - self.drag_start_mouse[0]
        dy = mouse[1] - self.drag_start_mouse[1]
        if self.drag_kind == "move":
            frames = [
                (frame[0][0], frame[0][1], frame[1][0], frame[1][1])
                for _, screen in self.overlays for frame in (screen.frame(),)
            ]
            self.fixed_point = nearest_display_point(
                (self.drag_start_focus[0] + dx, self.drag_start_focus[1] + dy),
                frames,
            )
            self.drag_focus_point = self.fixed_point
        else:
            if self.drag_screen is None:
                return
            screen_width = self.drag_screen.frame()[1][0]
            screen_height = self.drag_screen.frame()[1][1]
            width = screen_width * self.drag_start_width + 2 * dx
            self.width_ratio = min(1.0, max(0.2, width / screen_width))
            self.height_ratio = min(1.0, max(
                MIN_HEIGHT_RATIO, self.drag_start_height - 2 * dy / screen_height
            ))
            self.controls["width"].setDoubleValue_(self.width_ratio)
            self.controls["height"].setDoubleValue_(self.height_ratio)
            self._sync_labels()
        self._redraw()

    @objc.python_method
    def end_anchor_drag(self):
        self.drag_kind = None
        self.drag_focus_point = None
        self._redraw()
        self._save_preferences()

    def showSettings_(self, sender):
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        self.window.makeKeyAndOrderFront_(None)

    def windowWillClose_(self, notification):
        if self.recording_shortcut is not None:
            self._stop_recording_shortcut()
            self._register_hotkeys()

    def windowDidResignKey_(self, notification):
        if self.recording_shortcut is not None:
            self._stop_recording_shortcut()
            self._register_hotkeys()

    def tabView_didSelectTabViewItem_(self, tab_view, item):
        if self.recording_shortcut is not None and item != self.tab_items["shortcuts"]:
            self._stop_recording_shortcut()
            self._register_hotkeys()

    def recordShortcut_(self, sender):
        self._stop_recording_shortcut()
        if self.hotkeys is not None:
            self.hotkeys.close()
            self.hotkeys = None
        self.recording_shortcut = sender.tag()
        self.shortcut_feedback = None

        def capture(event):
            self._record_shortcut_event(event)
            return None

        self.shortcut_monitor = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
            NSEventMaskKeyDown, capture
        )
        self._refresh_shortcut_display()
        self.window.makeKeyAndOrderFront_(None)

    @objc.python_method
    def _record_shortcut_event(self, event):
        binding = shortcut_from_event(event)
        if binding == "cancel":
            self._stop_recording_shortcut()
            self._register_hotkeys()
            return
        if binding == "invalid":
            self.shortcut_feedback = "shortcut_invalid"
            self._refresh_shortcut_display()
            return
        if binding is not None and any(
            other != self.recording_shortcut and saved is not None
            and saved[:2] == binding[:2]
            for other, saved in self.shortcuts.items()
        ):
            self.shortcut_feedback = "shortcut_duplicate"
            self._refresh_shortcut_display()
            return
        self.shortcuts[self.recording_shortcut] = binding
        self._stop_recording_shortcut()
        self._register_hotkeys()
        self._save_preferences()

    @objc.python_method
    def _stop_recording_shortcut(self):
        if self.shortcut_monitor is not None:
            NSEvent.removeMonitor_(self.shortcut_monitor)
            self.shortcut_monitor = None
        self.recording_shortcut = None
        self.shortcut_feedback = None
        if "shortcut_warning" in self.controls:
            self._refresh_shortcut_display()

    def resetShortcuts_(self, sender):
        self._stop_recording_shortcut()
        self.shortcuts = dict(DEFAULT_SHORTCUTS)
        self._register_hotkeys()
        self._save_preferences()

    def applicationShouldHandleReopen_hasVisibleWindows_(self, application, has_visible_windows):
        self.showSettings_(None)
        return True

    def screensChanged_(self, notification):
        self._rebuild_overlays()

    def tick_(self, timer):
        if not self.enabled or not self.follows_mouse or self.drag_kind is not None:
            return
        mouse = NSEvent.mouseLocation()
        point = tuple(mouse)
        if point != self.last_point:
            self.last_point = point
            self._redraw()

    def toggleEnabled_(self, sender):
        self._set_enabled(sender.state() == NSControlStateValueOn)

    @objc.python_method
    def _set_enabled(self, enabled):
        self.enabled = enabled
        self.controls["enabled"].setState_(NSControlStateValueOn if enabled else 0)
        for panel, _ in self.overlays:
            if self.enabled:
                panel.orderFrontRegardless()
            else:
                panel.orderOut_(None)
        self._redraw()
        self._save_preferences()

    def toggleFollow_(self, sender):
        self._set_following(sender.state() == NSControlStateValueOn)

    @objc.python_method
    def _set_following(self, following):
        if self.follows_mouse and not following:
            self.fixed_point = NSEvent.mouseLocation()
        self.follows_mouse = following
        self.controls["follow"].setState_(NSControlStateValueOn if following else 0)
        self._sync_labels()
        self._redraw()
        self._save_preferences()

    def moveToMouse_(self, sender):
        self._move_to_mouse()

    def languageChanged_(self, sender):
        self.language = ("zh", "en")[sender.indexOfSelectedItem()]
        self._apply_language()
        self._save_preferences()

    @objc.python_method
    def _move_to_mouse(self):
        self.fixed_point = NSEvent.mouseLocation()
        self._redraw()
        self._save_preferences()

    @objc.python_method
    def _perform_hotkey(self, identifier):
        if identifier == 1:
            self._set_enabled(not self.enabled)
        elif identifier == 2:
            self._set_following(not self.follows_mouse)
        elif identifier == 3:
            self._move_to_mouse()

    def widthChanged_(self, sender):
        self.width_ratio = sender.doubleValue()
        self._sync_labels()
        self._redraw()
        self._save_preferences()

    def heightChanged_(self, sender):
        self.height_ratio = sender.doubleValue()
        self._sync_labels()
        self._redraw()
        self._save_preferences()

    def opacityChanged_(self, sender):
        self.opacity = sender.doubleValue()
        for key in ("opacity", "floating_opacity"):
            if self.controls[key] is not sender:
                self.controls[key].setDoubleValue_(self.opacity)
        self._sync_labels()
        self._redraw()
        self._save_preferences()

    def moveSizeChanged_(self, sender):
        self._set_anchor_size("move", sender.doubleValue())

    def resizeSizeChanged_(self, sender):
        self._set_anchor_size("resize", sender.doubleValue())

    @objc.python_method
    def _set_anchor_size(self, kind, size):
        self.anchor_sizes[kind] = round(size)
        self._sync_labels()
        self._redraw()
        self._save_preferences()

    def moveOpacityChanged_(self, sender):
        self._set_anchor_transparency("move", sender.doubleValue())

    def resizeOpacityChanged_(self, sender):
        self._set_anchor_transparency("resize", sender.doubleValue())

    @objc.python_method
    def _set_anchor_transparency(self, kind, transparency):
        self.anchor_transparencies[kind] = transparency
        if self.drag_kind != kind:
            self.anchor_panels[kind].setAlphaValue_(1.0 - transparency)
        if kind == "move" and not self.opacity_panel.contentView().hovered:
            self.opacity_panel.setAlphaValue_(1.0 - transparency)
        self._sync_labels()
        self._save_preferences()

    def quit_(self, sender):
        NSApplication.sharedApplication().terminate_(None)

    def applicationWillTerminate_(self, notification):
        self._stop_recording_shortcut()
        if self.hotkeys is not None:
            self.hotkeys.close()

    def smokeTest_(self, timer):
        assert NSApplication.sharedApplication().activationPolicy() == NSApplicationActivationPolicyRegular
        assert self.controls["tabs"].numberOfTabViewItems() == 3
        assert self.controls["tabs"].selectedTabViewItem() == self.tab_items["reading"]
        self.controls["tabs"].selectTabViewItem_(self.tab_items["shortcuts"])
        self.recordShortcut_(self.controls["shortcut_1"])
        assert self.recording_shortcut == 1 and self.shortcut_monitor is not None

        class RecordedKey:
            def keyCode(self):
                return 15

            def modifierFlags(self):
                return (NSEventModifierFlagControl | NSEventModifierFlagOption
                        | NSEventModifierFlagCommand)

            def charactersIgnoringModifiers(self):
                return "r"

        self._record_shortcut_event(RecordedKey())
        assert self.shortcuts[1] == (15, CONTROL | OPTION | COMMAND, "R")
        assert self.recording_shortcut is None and self.shortcut_monitor is None
        self.resetShortcuts_(None)
        assert self.shortcuts == DEFAULT_SHORTCUTS
        self.controls["language"].selectItemAtIndex_(1)
        self.languageChanged_(self.controls["language"])
        assert self.window.title() == "ReadMask"
        assert self.tab_items["shortcuts"].label() == "Shortcuts"
        assert self.controls["resize_opacity_title"].stringValue() == "Resize handle transparency"
        assert self.anchor_panels["move"].contentView().toolTip() == "Drag focus area"
        self.controls["language"].selectItemAtIndex_(0)
        self.languageChanged_(self.controls["language"])
        assert self.window.title() == "阅读尺"
        assert self.overlays
        assert self.hotkeys is not None and len(self.hotkeys.hotkey_refs) == 3
        assert all(panel.isVisible() for panel, _ in self.overlays)
        assert all(panel.ignoresMouseEvents() for panel, _ in self.overlays)
        assert not self.anchor_panels["resize"].isVisible()
        assert not self.anchor_panels["move"].isVisible()
        assert not self.opacity_panel.isVisible()
        assert any(panel.contentView().focus is not None for panel, _ in self.overlays)
        self.controls["width"].setDoubleValue_(0.55)
        self.widthChanged_(self.controls["width"])
        assert self.width_ratio == 0.55
        self.controls["follow"].setState_(0)
        self.toggleFollow_(self.controls["follow"])
        assert not self.follows_mouse
        assert self.anchor_panels["move"].isVisible()
        assert self.anchor_panels["resize"].isVisible()
        assert self.opacity_panel.isVisible()
        assert abs(self.opacity_panel.alphaValue() - 0.1) < 0.001
        slider_background = self.opacity_panel.contentView()
        slider_background.mouseEntered_(None)
        assert self.opacity_panel.alphaValue() == 1.0
        slider_background.mouseExited_(None)
        assert abs(self.opacity_panel.alphaValue() - 0.1) < 0.001
        self.controls["floating_opacity"].setDoubleValue_(0.0)
        self.opacityChanged_(self.controls["floating_opacity"])
        assert self.opacity == 0.0
        assert self.controls["opacity"].doubleValue() == 0.0
        self.controls["opacity"].setDoubleValue_(1.0)
        self.opacityChanged_(self.controls["opacity"])
        assert self.opacity == 1.0
        assert self.controls["floating_opacity"].doubleValue() == 1.0
        self.controls["floating_opacity"].setDoubleValue_(0.6)
        self.opacityChanged_(self.controls["floating_opacity"])
        assert abs(self.opacity - 0.6) < 0.001
        assert abs(self.controls["opacity"].doubleValue() - 0.6) < 0.001
        assert self.anchor_panels["move"].frame()[1] == anchor_dimensions(
            "move", DEFAULT_ANCHOR_SIZE
        )
        assert self.anchor_panels["resize"].frame()[1] == anchor_dimensions(
            "resize", DEFAULT_RESIZE_ANCHOR_SIZE
        )
        assert all(abs(panel.alphaValue() - 0.1) < 0.001
                   for panel in self.anchor_panels.values())
        active = next((screen, panel.contentView().focus)
                      for panel, screen in self.overlays
                      if panel.contentView().focus is not None)
        screen, focus = active
        origin = screen.frame()[0]
        move_frame = self.anchor_panels["move"].frame()
        assert abs(move_frame[0][0] + move_frame[1][0] / 2
                   - (origin[0] + focus[0] + focus[2] * 0.6)) < 1
        assert (abs(move_frame[0][1] + move_frame[1][1]
                    - (origin[1] + focus[1])) < 1
                or focus[1] < DEFAULT_ANCHOR_SIZE)
        for kind, size, transparency in (("move", 64, 0.6), ("resize", 32, 0.4)):
            self.controls[kind + "_size"].setDoubleValue_(size)
            self._set_anchor_size(kind, size)
            self.controls[kind + "_opacity"].setDoubleValue_(transparency)
            self._set_anchor_transparency(kind, transparency)
            assert self.anchor_panels[kind].frame()[1] == anchor_dimensions(kind, size)
            assert abs(self.anchor_panels[kind].alphaValue()
                       - (1 - transparency)) < 0.001
        assert abs(self.opacity_panel.alphaValue() - 0.4) < 0.001
        anchor = self.anchor_panels["move"].contentView()
        anchor.mouseEntered_(None)
        assert self.anchor_panels["move"].alphaValue() == 1.0
        anchor.mouseExited_(None)
        assert abs(self.anchor_panels["move"].alphaValue() - 0.4) < 0.001
        mouse = tuple(NSEvent.mouseLocation())
        self.begin_anchor_drag("move")
        self.update_anchor_drag((mouse[0] + 10, mouse[1] + 10))
        self.end_anchor_drag()
        self.begin_anchor_drag("resize")
        self.update_anchor_drag((mouse[0] + 10, mouse[1] - 10))
        self.end_anchor_drag()
        assert self.width_ratio > 0.55 and self.height_ratio > 0.15
        if len(self.overlays) > 1:
            target = next(screen.frame() for _, screen in self.overlays
                          if screen is not self.drag_screen)
            destination = (target[0][0] + target[1][0] / 2,
                           target[0][1] + target[1][1] / 2)
            self.begin_anchor_drag("move")
            drag_mouse = (self.drag_start_mouse[0] + destination[0] - self.drag_start_focus[0],
                          self.drag_start_mouse[1] + destination[1] - self.drag_start_focus[1])
            self.update_anchor_drag(drag_mouse)
            self.end_anchor_drag()
            assert tuple(self.fixed_point) == destination
        self.controls["enabled"].setState_(0)
        self.toggleEnabled_(self.controls["enabled"])
        assert all(not panel.isVisible() for panel, _ in self.overlays)
        self._perform_hotkey(1)
        assert self.enabled and all(panel.isVisible() for panel, _ in self.overlays)
        self._perform_hotkey(2)
        assert self.follows_mouse
        assert not self.anchor_panels["resize"].isVisible()
        assert not self.anchor_panels["move"].isVisible()
        assert not self.opacity_panel.isVisible()
        self._perform_hotkey(3)
        assert tuple(self.fixed_point) == tuple(NSEvent.mouseLocation())
        smoke_stage("passed: %d display(s)" % len(self.overlays))
        print("GUI smoke test passed: %d display(s)" % len(self.overlays), flush=True)
        NSApplication.sharedApplication().terminate_(None)


if __name__ == "__main__":
    smoke_stage("started")
    app = NSApplication.sharedApplication()
    delegate = ReadMaskApp.alloc().init()
    app.setDelegate_(delegate)
    print(delegate._text("started"), flush=True)
    app.run()
