# 阅读尺（ReadMask）发布文案与推广步骤

## 当前阶段

README 已有真实操作 GIF，但仓库目前只提供源码构建，没有可直接下载的预编译 App，也没有 LICENSE 文件。因此对外介绍时应明确“可自行构建试用”，不要写成“一键安装”或“已开源”。

## 仓库简介

- 中文：macOS 阅读尺：突出正在读的区域，支持鼠标跟随、固定阅读区、遮罩调节与多显示器。
- English: A macOS reading overlay with an adjustable focus area, pointer following, and multi-display support.

## 试用帖文案

> 做了阅读尺（ReadMask），一款 macOS 阅读盖板：压暗周围内容，只突出正在读的区域。亮区可以跟随鼠标，也能固定、拖动和缩放；遮罩支持点击穿透与多显示器。README 里有一段真实操作 GIF。目前需要从源码构建，想听听大家在读长文、文档或代码时是否觉得有帮助，以及最希望改进哪里。发帖时附上仓库链接。

> I built ReadMask, a macOS reading overlay that dims the rest of the screen while keeping an adjustable area clear. It can follow the pointer or stay in place, and it works across multiple displays. There's a short demo GIF in the README, and the app can switch between Chinese and English. For now, you need to build it from source. I'd appreciate feedback on where it helps or gets in the way. Add the repository link when posting.

配图使用 `demo/follow-mouse.gif`。只展示已录制的鼠标跟随效果；固定模式与锚点操作可在文字中说明，不把它们描述为 GIF 中已展示的功能。

## 推广顺序

1. **小范围试用：** 先邀请 5–10 位经常阅读长文或文档的 macOS 用户从源码构建，收集“在哪种页面有用”“哪里挡住操作”“设置是否好理解”的反馈。
2. **中文社区：** 根据反馈修订 README 和操作 GIF 后，先发布到 V2EX macOS 节点、少数派等 macOS 或效率工具社区。帖子以真实录屏、具体使用场景和仓库链接为主，明确当前的安装方式。
3. **扩大传播：** 准备可下载的 Release，说明支持的芯片架构与 macOS 版本，并完善签名或安装提示；若计划按开源项目推广，先补充许可证。保持中英文 README 同步后，再考虑海外 macOS 社区。

首轮只观察实际试用和问题反馈，不以浏览量判断产品是否有效。把重复出现的阅读场景和操作障碍整理进 GitHub Issues，优先修复影响首次使用的问题。
