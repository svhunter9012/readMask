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
    NSButton,
    NSColor,
    NSControlStateValueOn,
    NSEvenOddWindingRule,
    NSEvent,
    NSFloatingWindowLevel,
    NSGradient,
    NSImage,
    NSNotificationCenter,
    NSObject,
    NSPanel,
    NSScreen,
    NSSlider,
    NSStatusBar,
    NSSwitchButton,
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


def rect(x, y, width, height):
    return ((x, y), (width, height))


def anchor_dimensions(kind, size):
    return (size * MOVE_ANCHOR_ASPECT, size) if kind == "move" else (size, size)


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
    MODIFIERS = (1 << 8) | (1 << 11) | (1 << 12)  # Command, Option, Control.
    KEY_CODES = {1: 0x21, 2: 0x1E, 3: 0x2A}  # [, ], backslash.

    def __init__(self, on_press):
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

        for identifier, key_code in self.KEY_CODES.items():
            hotkey_ref = ctypes.c_void_p()
            status = self.carbon.RegisterEventHotKey(
                key_code, self.MODIFIERS,
                EventHotKeyID(self.SIGNATURE, identifier),
                target, 1, ctypes.byref(hotkey_ref),
            )
            if status != 0:
                self.close()
                raise RuntimeError("Cannot register hotkey %d: %d" % (identifier, status))
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
            self.drag_kind = None
            self.drag_focus_point = None
            self.preferences = NSUserDefaults.standardUserDefaults()
            if "--smoke" not in sys.argv:
                self._load_preferences()
        return self

    @objc.python_method
    def _load_preferences(self):
        defaults = self.preferences
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
        for kind in ("move", "resize"):
            defaults.setDouble_forKey_(self.anchor_sizes[kind], kind + "AnchorSize")
            defaults.setDouble_forKey_(
                self.anchor_transparencies[kind], kind + "AnchorTransparency"
            )
        if self.fixed_point is not None:
            defaults.setObject_forKey_(list(self.fixed_point), "fixedPoint")
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
        self.hotkeys = GlobalHotKeys(self._perform_hotkey)
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

    @objc.python_method
    def _make_status_item(self):
        self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSVariableStatusItemLength
        )
        button = self.status_item.button()
        icon = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
            "text.viewfinder", "阅读盖板"
        )
        if icon is not None:
            button.setImage_(icon)
        else:
            button.setTitle_("▣")
        button.setToolTip_("阅读盖板设置")
        button.setTarget_(self)
        button.setAction_("showSettings:")

    @objc.python_method
    def _make_settings_window(self):
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect(0, 0, 340, 600),
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_("阅读盖板")
        self.window.setLevel_(NSFloatingWindowLevel + 1)
        self.window.center()
        self.window.setReleasedWhenClosed_(False)
        content = self.window.contentView()

        self.controls["enabled"] = self._checkbox(
            content, "启用盖板", 560, self.enabled, "toggleEnabled:"
        )
        self._shortcut_label(content, "⌃⌥⌘[", 560)
        self.controls["follow"] = self._checkbox(
            content, "跟随鼠标", 530, self.follows_mouse, "toggleFollow:"
        )
        self._shortcut_label(content, "⌃⌥⌘]", 530)
        move = NSButton.alloc().initWithFrame_(rect(18, 497, 160, 26))
        move.setTitle_("移到鼠标位置")
        move.setTarget_(self)
        move.setAction_("moveToMouse:")
        content.addSubview_(move)
        self.controls["move"] = move
        self._shortcut_label(content, "⌃⌥⌘\\", 500)

        self.controls["width"] = self._slider(
            content, "阅读区宽度", 445, 0.2, 1.0, self.width_ratio, "widthChanged:"
        )
        self.controls["height"] = self._slider(
            content, "阅读区高度", 380, MIN_HEIGHT_RATIO, 1.0,
            self.height_ratio, "heightChanged:"
        )
        self.controls["opacity"] = self._slider(
            content, "遮罩深度", 315, 0.0, 1.0, self.opacity, "opacityChanged:"
        )
        self.controls["move_size"] = self._slider(
            content, "移动锚点大小", 250, 24, 96,
            self.anchor_sizes["move"], "moveSizeChanged:"
        )
        self.controls["move_opacity"] = self._slider(
            content, "移动锚点透明度", 185, 0.0, 0.9,
            self.anchor_transparencies["move"], "moveOpacityChanged:"
        )
        self.controls["resize_size"] = self._slider(
            content, "缩放锚点大小", 120, 24, 96,
            self.anchor_sizes["resize"], "resizeSizeChanged:"
        )
        self.controls["resize_opacity"] = self._slider(
            content, "缩放锚点透明度", 55, 0.0, 0.9,
            self.anchor_transparencies["resize"], "resizeOpacityChanged:"
        )
        quit_button = NSButton.alloc().initWithFrame_(rect(250, 12, 70, 26))
        quit_button.setTitle_("退出")
        quit_button.setTarget_(self)
        quit_button.setAction_("quit:")
        content.addSubview_(quit_button)
        self._sync_labels()

    @objc.python_method
    def _checkbox(self, content, title, y, checked, action):
        button = NSButton.alloc().initWithFrame_(rect(18, y, 180, 24))
        button.setButtonType_(NSSwitchButton)
        button.setTitle_(title)
        button.setState_(NSControlStateValueOn if checked else 0)
        button.setTarget_(self)
        button.setAction_(action)
        content.addSubview_(button)
        return button

    @objc.python_method
    def _shortcut_label(self, content, title, y):
        label = NSTextField.labelWithString_(title)
        label.setFrame_(rect(220, y + 2, 100, 20))
        label.setAlignment_(2)
        content.addSubview_(label)

    @objc.python_method
    def _slider(self, content, title, y, minimum, maximum, value, action):
        label = NSTextField.labelWithString_(title)
        label.setFrame_(rect(18, y + 25, 170, 20))
        content.addSubview_(label)
        value_label = NSTextField.labelWithString_("")
        value_label.setFrame_(rect(225, y + 25, 95, 20))
        value_label.setAlignment_(2)
        content.addSubview_(value_label)
        slider = NSSlider.alloc().initWithFrame_(rect(18, y, 302, 24))
        slider.setMinValue_(minimum)
        slider.setMaxValue_(maximum)
        slider.setDoubleValue_(value)
        slider.setContinuous_(True)
        slider.setTarget_(self)
        slider.setAction_(action)
        content.addSubview_(slider)
        self.controls[title + "_label"] = value_label
        return slider

    @objc.python_method
    def _sync_labels(self):
        self.controls["阅读区宽度_label"].setStringValue_(
            "%d%%" % round(self.width_ratio * 100)
        )
        self.controls["阅读区高度_label"].setStringValue_(
            "%d%%" % round(self.height_ratio * 100)
        )
        self.controls["遮罩深度_label"].setStringValue_(
            "%d%%" % round(self.opacity * 100)
        )
        for kind, title in (("move", "移动"), ("resize", "缩放")):
            self.controls[title + "锚点大小_label"].setStringValue_(
                "%d×%d pt" % anchor_dimensions(kind, self.anchor_sizes[kind])
            )
            self.controls[title + "锚点透明度_label"].setStringValue_(
                "%d%%" % round(self.anchor_transparencies[kind] * 100)
            )
        self.controls["move"].setEnabled_(not self.follows_mouse)

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
            view.setToolTip_("拖动阅读区" if kind == "move" else "拖动调整阅读区大小")
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
        slider.setToolTip_("遮罩深度")
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
        if self.hotkeys is not None:
            self.hotkeys.close()

    def smokeTest_(self, timer):
        assert NSApplication.sharedApplication().activationPolicy() == NSApplicationActivationPolicyRegular
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
    print("阅读盖板已启动，点击菜单栏图标打开设置。", flush=True)
    app.run()
