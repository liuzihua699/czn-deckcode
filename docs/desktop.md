# 桌面分发

桌面界面使用 Tkinter/ttk 原生窗口，Pillow 加载和缩放项目自带 PNG，直接调用 `czn_deckcode.encode()` / `decode()`。没有浏览器、WebView、HTTP 服务或监听端口。

## 图卡组卡流程

1. 左侧搜索并选择角色；列表按固定顺序排列，选择后只高亮，保留滚动位置。
2. 中间显示当前预设的卡组。01／02／03 切换该角色的预设，＋ 新建；上方可重命名，管理菜单可复制或删除预设。
3. 右侧的小型卡牌库可切换角色／公共／记忆分类、搜索名称或效果，点击 ＋ 添加。
4. 点击中间的卡牌，再使用右侧「新增卡牌」「移除／恢复」「复制」「独特灵光」「神之灵光」「一般灵光」。双击卡牌可查看完整描述，底部可调整顺序。独特灵光显示该牌的 `_rspN` 分支图卡，神闪和一般灵光分别使用对应效果库。
5. 「从卡组码导入」可新建预设或覆盖当前同角色预设；解码成功后自动归入对应角色。不支持的码会明确报错，不覆盖原内容。
6. Ctrl+S 或「保存预设」保存全部角色预设，正常关闭时自动保存。EXE 将配置写入同目录 `user_data/decks.json`，源码运行写入项目内同一路径。
7. 「导出 / 分享」生成和复制卡组码，其 JSON 页提供可选备份工具；日常组卡无需编辑原始 ID。

已补充客户端 BP4 压缩字典，7 条真实游戏导出码可在禁用网络条件下导入、导出和往返，包括记忆卡。未知版本或字段仍会明确报错，避免丢失数据。

卡牌及灵光描述从本地技能／状态表读取固定参数，以基础倍率和数量展示，未计角色、装备和战斗加成；少量实时状态或暂未解析的字段显示「未求值」，原生 X 费用机制仍显示 X。卡片和列表视图均默认隐藏已移除记录，只有用户勾选才显示；隐藏不影响完整导出。

灵光候选按客户端费用、卡牌类型和特性筛选，不等于完整游戏规则验证；神闪需先具有独特灵光或一般灵光。

所有插画、头像及客户端文案已置于 `demo/assets`，不进入 SDK 的 wheel 或源码发行包。`catalog.json` 保存 ID 到图片的关联，`provenance.json` 记录客户端资源名和 PNG 哈希。`NOTICE.txt` 说明素材来源；SDK 的 MIT 许可不覆盖游戏美术和文案。

更新本地图片与数值参数的构建脚本为 `scripts/import_client_art.py`，需要 Pillow、zstandard、texture2ddecoder、lz4 和 opencc-python-reimplemented；输入只读的客户端 SSRA 资源和已提取卡牌表。`client_tables.py` 与 `card_text_values.py` 在构建期读取技能和状态数据，把计算出的展示参数写入项目内的 catalog.json。普通运行和打包不需要这些提取依赖，也不需要安装游戏。

## Windows 成品

解压 `CZNDeckcode-windows-x64.zip`，双击 `CZNDeckcode.exe`。运行时完全离线，已包含所需 Python、Tcl 和 Tk。

## 构建

在 Windows 安装 Python 3.10+，在项目目录执行：

```powershell
python -m venv .venv-win
.\.venv-win\Scripts\python.exe -m pip install . -r demo/requirements.txt "pyinstaller>=6.11,<7"
.\.venv-win\Scripts\python.exe -m PyInstaller --clean --noconfirm CZNDeckcode.spec
```

自测打包文件（无须网络）：

```powershell
Start-Process -FilePath .\dist\CZNDeckcode.exe -ArgumentList '--self-test', 'desktop-check.json', '--official-codes', 'research/samples/official_client_codes.json' -Wait -WindowStyle Hidden
Get-Content desktop-check.json
python scripts/package_windows.py --self-test desktop-check.json
```

自测会在禁止 Python 网络访问的条件下解码官方码、重新编码／解码，并创建桌面窗口组件检查打包的 Tcl/Tk 后销毁窗口；结果写入 JSON。`frozen: true` 表示检查的是打包后的程序。打包脚本校验自测结果后生成 ZIP 和 SHA256 校验文件，不会包含个人 `user_data`。

## CI

`.github/workflows/build.yml` 在 Linux Python 3.10/3.12/3.13 上检查 SDK，并在 Windows 上运行包含 GUI 的测试、构建和成品自测。Windows 成品作为 Actions artifact 上传；正式分发包在仓库 Releases。
