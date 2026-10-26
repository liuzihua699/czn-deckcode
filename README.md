# czn-deckcode

《卡厄思梦境 / Chaos Zero Nightmare》卡组码的离线 Python SDK、命令行和原生桌面工具。

Python 3.10+，运行时零第三方依赖。卡组编解码在本机完成，无须网站接口、账号或网络。当前实现 BP 格式版本 4，外观通常以 `v6l8` 开头。

## 桌面工具

Windows 用户从 [Releases](https://github.com/liuzihua699/czn-deckcode/releases) 下载 `CZNDeckcode-windows-x64.zip`，解压后双击 `CZNDeckcode.exe`。已包含 Python 和 Tcl/Tk，日常使用无须安装环境、启动服务或部署网页。

工具提供卡牌列表和状态编辑、卡组码生成/解码/复制，以及 JSON 导入导出，编解码直接调用本地 SDK。支持 Windows 10/11 x64。

## 从源码启动

在项目目录运行：

```bash
python -m pip install .
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
- 原网站压缩字典还有少量未验证片段；引用这些片段的码会明确报错，避免输出猜测数据。完整范围见 [docs/dictionary.md](docs/dictionary.md)。

算法说明和逆向证据见 [docs/format.md](docs/format.md)。实际网站样本保存在 `research/samples/`，仅供开发验证；SDK 运行不读取样本。

已验证最初两份卡组码、61 份构筑变化、多角色单卡以及特殊字段与长文本样本。本地生成的 8 个新码已通过网站解码器导入验证，记录见 `research/samples/local_export_verification.json`。

## 开发与打包

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e . build
python -m unittest discover -s tests -v
python -m build
```

SDK 的 wheel 和源码包在 `dist/`。项目采用 `src/` 布局，包含 `py.typed`、命令行与桌面入口，可供后续发布到 PyPI；当前版本 `0.1.0a2`，尚未发布 PyPI。

在 Windows 上构建独立桌面程序（PowerShell）：

```powershell
python -m venv .venv-win
.\.venv-win\Scripts\python.exe -m pip install "pyinstaller>=6.11,<7"
.\.venv-win\Scripts\python.exe -m PyInstaller --noconfirm --clean CZNDeckcode.spec
```

产物为 `dist/CZNDeckcode.exe`。也可以执行 `scripts/build_windows.ps1`。PyInstaller 包含 Tcl/Tk，打包后的程序不要求用户安装 Python。GitHub Actions 会测试 SDK，并生成 Windows 桌面程序供下载。

MIT License。本项目为非官方工具，与游戏开发商和网站没有隶属关系。
