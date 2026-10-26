# czn-deckcode

《卡厄思梦境 / Chaos Zero Nightmare》卡组码的离线 Python SDK。

SDK 只包含编解码 API、数据模型和命令行；不包含卡图、图形界面、游戏客户端资源或网络解析服务。要求 Python 3.10+，运行时零第三方依赖。图卡演示 Demo 单独通过 GitHub Release 的 EXE 提供。

## 安装

发布到 PyPI 后，可安装当前预发布版：

```bash
python -m pip install --pre czn-deckcode
```

项目依赖可固定为 `czn-deckcode==0.1.0a2`。已有环境升级到后续修复版本时使用 `python -m pip install --upgrade --pre czn-deckcode`。

## 基础用法

```python
from czn_deckcode import Card, Deck, decode, encode

deck = Deck("30134", [Card("c_30134_uni1"), Card("c_30134_srt1", removed=True)])
code = encode(deck)
restored = decode(code)
assert restored == deck
print(code)
print(restored.to_dict())
```

已有官方码可以直接传给 `decode(code)`。`encode()` 也接受使用 `charId`、`cards`、`cardId` 等 camelCase 字段的字典。结果保留卡牌顺序、移除和复制状态、独特灵光、一般灵光及神闪字段；只显示在用卡牌时可筛选 `not card.removed`。

## 命令行

```bash
czn-deckcode encode deck.json -o code.txt
czn-deckcode decode - -o restored.json < code.txt
```

不支持的版本或无效输入会抛出 `DeckCodeError` 的子类。当前支持 BP4，编解码不验证完整游戏构筑规则。同一份卡组的有效压缩表示可能不同，应比较解码数据而不是码字符串。

[完整 SDK 用法](https://github.com/liuzihua699/czn-deckcode/blob/main/docs/sdk.md) · [源码和问题反馈](https://github.com/liuzihua699/czn-deckcode) · [独立演示 Demo](https://github.com/liuzihua699/czn-deckcode/releases)
