# czn-deckcode

《卡厄思梦境 / Chaos Zero Nightmare》的离线卡组码工具。

项目分为两个部分：

- **SDK**：负责卡组码编码和解码，纯 Python、零运行时依赖，不包含卡图和 GUI。
- **Demo**：独立的 Windows 图形工具，用于查看角色、卡牌、灵光和管理预设卡组。

编解码完全在本地完成，不需要游戏客户端、账号或外部 API。

## SDK 最小用法

当前 SDK wheel 可以从 [v0.1.0a2 Release](https://github.com/liuzihua699/czn-deckcode/releases/tag/v0.1.0a2) 下载：

```bash
python -m pip install --force-reinstall ./czn_deckcode-0.1.0a2-py3-none-any.whl
```

代码示例：

```python
from czn_deckcode import decode, encode

code = "粘贴游戏中的卡组码"
deck = decode(code)
print(deck.to_dict())

new_code = encode({
    "charId": "30134",
    "cards": [{"cardId": "c_30134_uni1"}],
})
print(new_code)
```

PyPI 发布配置已经准备好，首次发布完成后即可使用：

```bash
pip install --pre czn-deckcode
```

完整 SDK 文档见 [docs/sdk.md](docs/sdk.md)，发布步骤见 [docs/publishing.md](docs/publishing.md)。

## Demo 功能

Windows 用户可以从 [Releases](https://github.com/liuzihua699/czn-deckcode/releases) 下载 Demo：

- 按角色管理多个预设卡组；
- 从官方卡组码导入；
- 搜索和添加角色卡、公共卡、记忆卡；
- 新增、复制、移除和恢复卡牌；
- 选择独特灵光、一般灵光和神之灵光；
- 使用本地卡图和繁简中文展示；
- 配置保存在 EXE 旁的 `user_data/decks.json`。

Demo 的源码和卡图位于 `demo/`，不进入 SDK 发行包。

## 开发

```bash
python -m pip install -e .
python -m pip install -r demo/requirements.txt
python -m unittest discover -s tests -v
python scripts/desktop_entry.py
```

项目采用 MIT License。游戏卡图和客户端文案属于原权利人，不包含在代码许可范围内。
