# ReadMask

[简体中文](README.md)

**Keep the part you're reading in focus.** ReadMask is a reading overlay for macOS. It dims the rest of your screen and leaves a clear area you can adjust. That area can follow your pointer or stay in place. The overlay lets clicks through and works across multiple displays.

## Demo

In follow-pointer mode, the clear area moves with your reading position:

![Screen recording of the ReadMask clear area following the pointer](docs/demo/follow-mouse.gif)

## Get started

This repository currently provides source builds, not a prebuilt app. Building requires macOS, Python 3.9 or newer, and Xcode Command Line Tools for `clang`. On Apple Silicon, use an arm64 Python and PyInstaller to build a native arm64 app.

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt pyinstaller
./build.sh
```

The app will be at `dist/ReadMask.app` on your Mac. Open it from Finder; no terminal window will appear. Settings opens on first launch. After that, click the Dock or menu bar icon to open it again. Source and app builds share the same settings.

## Reading modes

- **Follow pointer:** The clear area moves with your pointer as you read.
- **Stay in place:** Turn off following, then drag the handle below the clear area to move it or drag the bottom-right handle to resize it.
- **Adjust the view:** Change the clear area's size, mask depth, and each handle's size and transparency in settings. In fixed mode, the slider below the clear area also adjusts mask depth.

Settings has Reading, Handles, and Shortcuts tabs. The initial language follows macOS; use the language menu at the bottom to switch between Chinese and English. Your choice and other changes are saved automatically. Closing the settings window does not quit ReadMask; use its Quit button to exit.

## Keyboard shortcuts

Hold the first three keys, then press the last one:

| Keys | Action |
| --- | --- |
| <kbd>Control ⌃</kbd> + <kbd>Option ⌥</kbd> + <kbd>Command ⌘</kbd> + <kbd>[</kbd> | Toggle the mask |
| <kbd>Control ⌃</kbd> + <kbd>Option ⌥</kbd> + <kbd>Command ⌘</kbd> + <kbd>]</kbd> | Toggle pointer following |
| <kbd>Control ⌃</kbd> + <kbd>Option ⌥</kbd> + <kbd>Command ⌘</kbd> + <kbd>&#92;</kbd> | Move the clear area to the pointer |

In the Shortcuts tab, click a shortcut button and press a new combination to change it. Esc cancels, Delete clears it, and the reset button restores all defaults. If a shortcut cannot be registered, that item is marked in settings while the rest of the app remains usable.

## Run from source

If your Python installation already has PyObjC (AppKit), run:

```sh
python3 readmask.py
```

You can also use the virtual environment created above. If the macOS system Python includes PyObjC, `/usr/bin/python3 readmask.py` works as well.

The local `build.sh` app is ad hoc signed for local use. Distribution requires Developer ID signing and Apple notarization; see the [release guide](docs/releasing.md).

## Development check

Run `python3 readmask.py --smoke` in a macOS graphical session to check the mask, handles, and shortcuts. The app exits automatically when the check finishes.
