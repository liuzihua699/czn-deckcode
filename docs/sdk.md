# SDK 基础用法

`czn-deckcode` 提供两个主要函数：`encode()` 将卡组数据变成分享码，`decode()` 将分享码还原成卡组数据。编解码在本机完成，无需账号、API 密钥、游戏客户端或网络连接。

## 1. 安装

要求 **Python 3.10+**。SDK 尚未发布到 PyPI，请从 [v0.1.0a2 Release](https://github.com/liuzihua699/czn-deckcode/releases/tag/v0.1.0a2) 下载 `czn_deckcode-0.1.0a2-py3-none-any.whl`，在下载目录执行：

```bash
python -m pip install --force-reinstall ./czn_deckcode-0.1.0a2-py3-none-any.whl
```

本次修复覆盖原 `0.1.0a2`，版本号未改变；已安装旧版时也应使用 `--force-reinstall`，确保换成修复后的解码器。源码用户可在项目根目录执行 `python -m pip install .`。

SDK 运行时仅使用 Python 标准库，不需要安装 Pillow 或 Tk，也不包含卡图或图形界面。独立演示位于仓库的 `demo/`，使用单独的依赖和 EXE 构建流程。

## 2. 生成卡组码

用 `Card` 表示一条卡牌记录，用 `Deck` 表示某个角色的完整卡组，再传给 `encode()`：

```python
from czn_deckcode import Card, Deck, decode, encode

deck = Deck(
    char_id="30134",  # 角色 ID，使用字符串
    cards=[
        Card("c_30134_uni1"),
        Card("c_30134_uni1", duplicate=True),
        Card("c_30134_srt1", removed=True),
    ],
)

code = encode(deck)
print(code)                       # 可用于分享的码
restored = decode(code)
assert restored == deck
print(restored.to_dict())          # 可交给 JSON 序列化的字典
```

这里使用卡牌 **ID**，不直接填写中文卡名。`duplicate=True` 表示当前这条记录是一张复制牌，不会自动再增加一条记录。每张卡分别占一条记录，输入顺序会被保留。

## 3. 解码游戏中的官方码

以下为可直接运行的官方码示例；在自己的应用中，将 `official_code` 替换为从游戏复制的完整文本即可：

```python
from czn_deckcode import decode

official_code = (
    "v6l8cOjiNqfdzwd5bz8N5Gb2ReyrtB0zwiRbEmZCVx1OgEEpDGY5zpqpqk9i5CmtMFqScYEqyHZqyhHDvQ6_9RTVibh4PasWOU35SC7vwZ1NSb2du64WRU4tCcvgBIpsFKYjNs-5Pu0"
)
deck = decode(official_code)
active_cards = [card for card in deck.cards if not card.removed]

print(deck.char_id)                # 30134
print(len(deck.cards))             # 11 条完整记录
print(len(active_cards))           # 其中 8 张在用卡牌
assert len(deck.cards) == 11
assert len(active_cards) == 8

for card in active_cards:
    print(card.card_id, card.variant_card_id, card.divine_id)
```

`decode()` 返回的记录包括已移除卡。界面只需展示当前卡组时可筛选 `not card.removed`；如果要重新导出，使用完整的 `deck`，保留移除、复制及灵光状态。

## 4. 用字典传入卡组数据

不想构造 `Card` 和 `Deck` 时，可以直接传入 camelCase 字段的字典：

```python
from czn_deckcode import decode, encode

data = {
    "charId": "30134",
    "cards": [
        {
            "cardId": "c_30134_uni1",
            "variantCardId": "c_30134_uni1_rsp2",
            "divineId": "add_r_spark_nihilum_09",
            "duplicate": True,
        },
        {"cardId": "card_ds05_b_c1_4_1"},  # 记忆卡同样使用 ID
    ],
}

code = encode(data)
restored = decode(code)
result = restored.to_dict()
assert result["charId"] == "30134"
assert result["cards"][0]["god"] == "NIHILUM"
assert result["cards"][1]["cardId"] == "card_ds05_b_c1_4_1"
print(result)
```

`to_dict()` 会补齐默认布尔值，省略未设置的可选字段，并执行下文所述的格式归一化。因此，输入字典和输出字典不一定逐项完全相同。

## 5. 读写 JSON 文件

```python
import json
from pathlib import Path
from czn_deckcode import Deck, decode, encode

data = {"charId": "30134", "cards": [{"cardId": "c_30134_uni1"}]}
path = Path("deck.json")
path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

loaded = json.loads(path.read_text(encoding="utf-8-sig"))
deck = Deck.from_dict(loaded)
code = encode(deck)
restored = decode(code)
Path("restored.json").write_text(
    json.dumps(restored.to_dict(), ensure_ascii=False, indent=2),
    encoding="utf-8",
)
assert restored.cards[0].card_id == "c_30134_uni1"
```

输出使用 UTF-8；读取时使用 `utf-8-sig` 也能处理带 BOM 的 UTF-8 文件。

## 6. 字段说明

| Python 字段 | 字典字段 | 含义 |
| --- | --- | --- |
| `Deck.char_id` | `charId` | 必填，角色 ID 字符串，例如 `"30134"` |
| `Deck.cards` | `cards` | 必填，按顺序排列的卡牌记录；Python 模型中是不可变 tuple |
| `Card.card_id` | `cardId` | 必填，卡牌 ID |
| `Card.removed` | `removed` | 是否为已移除记录，默认 `False` |
| `Card.duplicate` | `duplicate` | 这张卡是否为复制牌，默认 `False` |
| `Card.variant_card_id` | `variantCardId` | 可选，独特灵光 `_rspN` 或 `_pot`／`_lbk` 变体 ID |
| `Card.epiphany_id` | `epiphanyId` | 可选，一般灵光 ID，例如 `c03012` |
| `Card.divine_id` | `divineId` | 可选，神闪 ID；需要先有独特灵光 `_rspN` 或一般灵光 |
| `Card.god` | `god` | 神闪 ID 推导出的展示字段，不单独写入卡组码 |

注意以下数据语义：

- `Card` 和 `Deck` 是不可变模型。编辑时创建新的 `Card`／`Deck`，也可以先处理字典再调用 `encode()`。
- `_pot`／`_lbk` 编码为有效卡牌 ID。解码后会进入 `card_id`，`variant_card_id` 留空；`_rspN` 则保留为基础卡 ID 加 `variant_card_id`。
- 同时填写独特灵光 `_rspN` 和一般灵光时，编码优先使用独特灵光。
- `god` 由 `divine_id` 推导为大写，例如 `NIHILUM`。通常不需要手动填写。
- 核心 SDK 返回 ID 和状态，不返回中文卡名、卡图或已计算的伤害。桌面界面使用的本地目录是单独的展示层。
- 同一份卡组可能有多个压缩表示不同的有效码。检查语义应比较解码后的数据，不应只比较码字符串是否相同。

## 7. 异常处理

处理用户粘贴的码时，捕获公共基类 `DeckCodeError`：

```python
from czn_deckcode import DeckCodeError, decode

try:
    deck = decode("invalid-code")  # 替换为用户输入
except DeckCodeError as error:
    print(f"无法导入卡组：{error}")
else:
    print(deck.to_dict())
```

需要区分错误时可使用：

- `InvalidCodeError`：码文本或二进制内容不合法。
- `UnsupportedVersionError`：尚不支持的版本；它继承 `InvalidCodeError`，分别捕获时应放在前面。
- `InvalidDeckError`：传给 `Card`、`Deck` 或 `encode()` 的数据不符合支持的格式。

当前支持 BP4。未知版本或未实现字段会明确报错，编解码不会向外部服务请求回退解析。它不模拟完整游戏规则，仍需在游戏中确认构筑是否合法。
