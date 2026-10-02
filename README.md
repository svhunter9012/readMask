# 阅读尺 ReadMask

[English](README.en.md)

**让注意力留在正在读的内容上。** 阅读尺（ReadMask）是一款 macOS 阅读盖板：压暗屏幕其他区域，留出一块可调整的清晰阅读区。读长文、文档或代码时，阅读区可以跟随鼠标，也可以固定在屏幕上。遮罩支持点击穿透和多显示器。

## 效果演示

鼠标跟随模式下，清晰区域会随阅读位置移动：

![阅读尺的阅读区跟随鼠标移动](docs/demo/follow-mouse.gif)

## 开始使用

目前仓库提供源码构建，尚未发布预编译的 App。构建需要 macOS、Python 3.9 或更新版本，以及包含 `clang` 的 Xcode Command Line Tools。在 Apple Silicon Mac 上，请使用 arm64 版本的 Python 和 PyInstaller，才能构建原生 arm64 应用。

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt pyinstaller
./build.sh
```

生成的应用位于本地 `dist/ReadMask.app`。通过 Finder 双击即可启动，不会打开终端窗口。首次启动会打开设置；之后点击程序坞或菜单栏图标即可再次打开。源码版和 App 版共用设置。

## 阅读方式

- **跟随鼠标：** 清晰区域随鼠标移动，适合连续阅读。
- **固定位置：** 关闭跟随后，拖动阅读区下方的锚点移动亮区，拖动右下角的锚点调整大小。
- **自由调整：** 阅读区尺寸、遮罩深度，以及锚点的大小和透明度均可在设置中调整。固定模式下也能直接拖动阅读区下方的滑块调整遮罩深度。

设置分为“阅读”“锚点”“快捷键”三个标签页。首次使用时界面语言跟随 macOS；窗口底部可在中文和 English 之间切换，选择会自动保存。关闭设置窗口不会退出应用；点击窗口中的“退出”可结束运行。

## 快捷键

按住前三个键，再按最后一个键：

| 具体按键 | 功能 |
| --- | --- |
| <kbd>Control ⌃</kbd> + <kbd>Option ⌥</kbd> + <kbd>Command ⌘</kbd> + <kbd>[</kbd> | 开关盖板 |
| <kbd>Control ⌃</kbd> + <kbd>Option ⌥</kbd> + <kbd>Command ⌘</kbd> + <kbd>]</kbd> | 切换跟随鼠标 |
| <kbd>Control ⌃</kbd> + <kbd>Option ⌥</kbd> + <kbd>Command ⌘</kbd> + <kbd>&#92;</kbd> | 将阅读区移到鼠标位置 |

在“快捷键”标签页点击对应按钮，再按新组合键即可修改；按 Esc 取消，按 Delete 清除，也可恢复全部默认快捷键。如果组合键注册失败，设置页会标出对应项，其他功能仍可使用。

## 从源码运行

已安装 PyObjC（AppKit）的 Python 可以直接运行：

```sh
python3 readmask.py
```

也可以用上面创建的虚拟环境运行；本机的 macOS 系统 Python 若已包含 PyObjC，可使用 `/usr/bin/python3 readmask.py`。

本地 `build.sh` 生成的应用使用临时签名，适合本机试用。对外分发需要 Developer ID 签名和 Apple 公证；步骤见[发布说明](docs/releasing.md)。

## 开发检查

在 macOS 图形会话中运行 `python3 readmask.py --smoke`，程序会检查遮罩、锚点和快捷键的基本状态，然后自动退出。
