# 阅读尺 ReadMask

[English](README.en.md)

**让注意力留在正在读的内容上。** 阅读尺（ReadMask）是一款 macOS 阅读盖板：压暗屏幕其他区域，留出一块可调整的清晰阅读区。读长文、文档或代码时，阅读区可以跟随鼠标，也可以固定在屏幕上。遮罩支持点击穿透和多显示器。

## 效果演示

鼠标跟随模式下，清晰区域会随阅读位置移动：

![阅读尺的阅读区跟随鼠标移动](docs/demo/follow-mouse.gif)

## 开始使用

目前仓库提供源码构建，尚未发布预编译的 App。构建需要 macOS、Python 3.9 或更新版本，以及包含 `clang` 的 Xcode Command Line Tools。

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt pyinstaller
./build.sh
```

生成的应用位于本地 `dist/ReadMask.app`。通过 Finder 双击即可启动，不会打开终端窗口。阅读尺会出现在程序坞和菜单栏；点击任一图标可打开设置。

## 阅读方式

- **跟随鼠标：** 清晰区域随鼠标移动，适合连续阅读。
- **固定位置：** 关闭跟随后，拖动阅读区下方的锚点移动亮区，拖动右下角的锚点调整大小。
- **自由调整：** 阅读区尺寸、遮罩深度，以及锚点的大小和透明度均可在设置中调整。固定模式下也能直接拖动阅读区下方的滑块调整遮罩深度。

设置窗口底部可在中文和 English 之间切换，选择会自动保存。关闭设置窗口不会退出应用；点击窗口中的“退出”可结束运行。

## 快捷键

按住前三个键，再按最后一个键：

| 具体按键 | 功能 |
| --- | --- |
| <kbd>Control ⌃</kbd> + <kbd>Option ⌥</kbd> + <kbd>Command ⌘</kbd> + <kbd>[</kbd> | 开关盖板 |
| <kbd>Control ⌃</kbd> + <kbd>Option ⌥</kbd> + <kbd>Command ⌘</kbd> + <kbd>]</kbd> | 切换跟随鼠标 |
| <kbd>Control ⌃</kbd> + <kbd>Option ⌥</kbd> + <kbd>Command ⌘</kbd> + <kbd>&#92;</kbd> | 将阅读区移到鼠标位置 |

这些快捷键也显示在设置窗口中。如果组合键已被其他应用占用，阅读尺可能无法注册快捷键并启动。

## 从源码运行

已安装 PyObjC（AppKit）的 Python 可以直接运行：

```sh
python3 readmask.py
```

也可以用上面创建的虚拟环境运行；本机的 macOS 系统 Python 若已包含 PyObjC，可使用 `/usr/bin/python3 readmask.py`。

## 开发检查

在 macOS 图形会话中运行 `python3 readmask.py --smoke`，程序会检查遮罩、锚点和快捷键的基本状态，然后自动退出。
