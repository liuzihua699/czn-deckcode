# CZN Deckcode 0.1.0a2

桌面 demo 使用原生 Tkinter 窗口，直接调用离线 SDK。Windows x64 成品已包含 Python 和 Tcl/Tk，下载 `CZNDeckcode-windows-x64.zip`、解压并双击 `CZNDeckcode.exe` 即可使用。

支持卡牌与移除/复制状态编辑、卡组码生成/解码/复制、JSON 编辑和导入导出。源码、命令行和 SDK 同时提供。

验证：Windows Python 3.10、3.12 各 55 项测试全部通过，其中 7 项使用真实 Tk 窗口和 SDK；独立 `.exe` 自测确认包含 Tcl/Tk，并通过已知原码的解码与编码往返。Linux 无 Tk 环境下 48 项通过、7 项 GUI 测试跳过。

当前支持 BP4。原压缩字典还有少量未确认片段，引用这些片段的码会明确报错，范围见仓库 `docs/dictionary.md`。不同 DEFLATE 表示可能生成与网站不同但等价的字符串。SDK 无外部接口或卡牌数据库依赖。

下载内容：Windows 桌面压缩包、单独 `.exe`、Python wheel、源码包和 SHA256 校验文件。SDK 尚未发布到 PyPI。
