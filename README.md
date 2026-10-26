# czn-deckcode

《卡厄思梦境 / Chaos Zero Nightmare》卡组码的离线 Python SDK、命令行和原生桌面工具。

Python 3.10+，SDK 运行时零第三方依赖，图形界面使用 Pillow 显示本地插画。卡组编解码在本机完成，无须网站接口、账号或网络。当前实现 BP 格式版本 4，外观通常以 `v6l8` 开头。

## 桌面工具

Windows 用户从 [Releases](https://github.com/liuzihua699/czn-deckcode/releases) 下载 `CZNDeckcode-windows-x64.zip`，解压后双击 `CZNDeckcode.exe`。已包含 Python 和 Tcl/Tk，日常使用无须安装环境、启动服务或部署网页。

工具采用预设构筑布局：左侧固定角色列表，中间展示当前卡组大图，右侧提供编辑操作与可搜索的小型卡牌库。每个角色可以管理多个命名预设，支持新增、复制、删除、保存及从卡组码导入。选择卡牌后可移除／恢复、复制、排序，独特灵光以分支图卡展示，神闪与一般灵光分别从本地效果库选择。支持 Windows 10/11 x64。

预设保存在程序旁的 `user_data/decks.json`，点击「保存预设」或按 Ctrl+S 保存，正常关闭时也会保存。原来的高级 ID 编辑入口已移除，JSON 备份工具位于「导出 / 分享」窗口。卡组码导入可新建预设或覆盖同角色当前预设；不支持的码会报错并保留原卡组。

已带入客户端对应的 39 个角色、817 张可选卡牌及 855 张本地插画／头像。素材位于 `src/czn_deckcode/assets`，以客户端卡牌 ID 和资源名对应，随应用一起打包；运行时无需访问游戏目录或图片网站。默认显示客户端繁体文案，简体选项为繁转简展示文本。卡牌和灵光的固定参数来自本地技能／状态表，显示基础倍率与数量，未计角色、装备及战斗加成；少数依赖实时状态或暂未解析的字段标为「未求值」。游戏本身的 X 费用机制仍显示 X。效果筛选尚未复现全部游戏内规则。

移除卡牌不会自动勾选「显示已移除」。只有用户勾选后，卡片与列表视图才显示这些记录；隐藏不会删除移除状态，导出仍保留完整数据。

当前运行代码不调用任何外部编解码 API，详见 [离线验证说明](docs/offline.md)。

## 从源码启动

在项目目录运行：

```bash
python -m pip install ".[desktop]"
czn-deckcode ui
```

运行后直接打开 Tkinter 桌面窗口。也可以运行 `czn-deckcode-desktop`（Windows 下不显示命令行窗口）。

也可以不用安装，直接从源码启动：

```bash
PYTHONPATH=src python3 -m czn_deckcode ui
```

Linux 桌面环境也可以运行 `./run-ui.sh`；Windows 安装 Python 3.10+ 后可双击 `启动卡组工具.cmd`。Linux 从源码运行 GUI 需要系统的 `python3-tk` 包与图形环境；SDK/命令行编解码无需 Tk。

## SDK

```python
from czn_deckcode import Card, Deck, encode, decode

deck = Deck(
    char_id="30134",
    cards=[
        Card("c_30134_srt1", variant_card_id="c_30134_srt1_pot"),
        Card("c_30134_srt2", removed=True),
    ],
)
code = encode(deck)
restored = decode(code)
assert restored.cards[0].card_id == "c_30134_srt1_pot"
print(code)
print(restored.to_dict())
```

也接受与网站相同的 camelCase JSON 对象：

```python
deck_json = {
    "charId": "30134",
    "cards": [{"cardId": "c_30134_srt1", "duplicate": False}],
}
code = encode(deck_json)
deck_json = decode(code).to_dict()
```

`Card` 字段：`card_id`、`removed`、`duplicate`、`variant_card_id`、`epiphany_id`、`divine_id`、`god`。JSON 对应 `cardId`、`removed`、`duplicate`、`variantCardId`、`epiphanyId`、`divineId`、`god`。`Deck.cards` 是不可变 tuple，保留输入顺序。

`encode()` 返回无 padding 的 Base64url 字符串；`decode()` 返回 `Deck`。格式错误抛出 `InvalidCodeError`，不支持的版本抛出 `UnsupportedVersionError`，无效卡组抛出 `InvalidDeckError`，统一继承 `DeckCodeError(ValueError)`。

## 命令行

```bash
czn-deckcode encode examples/build1.json
czn-deckcode encode examples/build1.json -o code.txt
czn-deckcode decode "v6l8cOjiNr8NyAd5bz8N5Gb4BacatRLcP_gTJk6Sy-IpI4UudHIDQRTERzqzgUXu"
czn-deckcode decode - -o restored.json < code.txt
```

也可以通过 `python -m czn_deckcode` 调用。失败时错误写入 stderr，返回状态码 2。

## 兼容性与数据语义

- 支持普通卡、移除、复制、`_pot` / `_lbk` 变体、`_rspN` 角色顿悟、公共顿悟和神性顿悟。
- `_pot` / `_lbk` 直接存储为有效卡牌 ID，解码放入 `card_id`，`variant_card_id` 留空；`_rspN` 解码为基础卡 ID 加 `variant_card_id`。
- `god` 是由神性顿悟 ID 推导的展示字段，不单独存储，解码为大写（例如 `VITOR`）。原格式没有表达的信息无法保留。
- SDK 不含卡牌数据库，负责格式转换，不检查游戏内是否存在某张卡或构筑是否合法。
- 同一份数据可以有多种有效 DEFLATE 表示。本地编码后的字符串可能与网站导出不同，但解压后的卡组数据相同；不能用字符串是否完全相同判断兼容性。
- 未识别的版本或字段结构会明确报错。当前解码上限为 1 MiB 卡组数据，输入码上限为 2 MiB 字符。
- 已从客户端模块提取 245 字节 BP4 压缩字典，修复真实官方码的解压错误；新增 7 条游戏导出码回归，包括记忆卡、移除、复制、一般灵光和神闪。证据见 [docs/dictionary.md](docs/dictionary.md)。

面向普通读者的图文稿见 [卡组码科普文](docs/popular-science/关于卡厄思梦境的卡组码编解码原理，根据大量的卡组码示例反推其编解码算法.md)，配有 PNG、SVG 和编码/解码 GIF，附离线 HTML 阅读版。

从结构到完整实例的中文说明见 [卡组码结构与编解码报告](docs/卡组码结构与编解码报告.md)，包括逐层字节、原始两码的对照及本地实现。简要格式说明见 [docs/format.md](docs/format.md)。实际网站样本保存在 `research/samples/`，仅供开发验证；SDK 运行不读取样本。

已验证最初两份卡组码、61 份构筑变化、多角色单卡以及特殊字段与长文本样本。本地生成的 8 个新码已通过网站解码器导入验证，记录见 `research/samples/local_export_verification.json`。

## 开发与打包

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[desktop]" build
python -m unittest discover -s tests -v
python -m build
```

SDK 的 wheel 和源码包在 `dist/`。项目采用 `src/` 布局，包含 `py.typed`、命令行与桌面入口，可供后续发布到 PyPI；当前版本 `0.1.0a2`，尚未发布 PyPI。

在 Windows 上构建独立桌面程序（PowerShell）：

```powershell
python -m venv .venv-win
.\.venv-win\Scripts\python.exe -m pip install ".[desktop]" "pyinstaller>=6.11,<7"
.\.venv-win\Scripts\python.exe -m PyInstaller --noconfirm --clean CZNDeckcode.spec
```

产物为 `dist/CZNDeckcode.exe`。也可以执行 `scripts/build_windows.ps1`。PyInstaller 包含 Tcl/Tk，打包后的程序不要求用户安装 Python。GitHub Actions 会测试 SDK，并生成 Windows 桌面程序供下载。

MIT License。本项目为非官方工具，与游戏开发商和网站没有隶属关系。
