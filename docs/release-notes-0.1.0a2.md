# CZN Deckcode v0.1.0a2 · 图卡组卡与官方码导入修复

本次更新覆盖原 `v0.1.0a2`，版本号保持不变。

Windows 用户下载 **CZNDeckcode-windows-x64.zip**，解压后双击 **CZNDeckcode.exe**。包含 Python、Tcl/Tk 及全部插画，无需安装 Python 或游戏。更新时保留原 EXE 旁的 `user_data` 文件夹。

可视化组卡：左侧固定角色列表，中间展示当前卡组，右侧提供编辑操作与可搜索的小型卡牌库。每个角色可管理多个命名预设，支持新增、复制、删除、本地保存和从官方卡组码导入。

编辑功能包括新增卡牌、移除／恢复、复制、独特灵光一闪、神之灵光一闪和一般灵光一闪。独特灵光通过分支图卡选择，神闪与一般灵光使用各自的本地效果库。移除记录默认隐藏，仅用户勾选「显示已移除」后显示；导出仍保留这些记录。

修复官方码导入的 `Invalid DEFLATE stream or unsupported dictionary reference`：从客户端提取 245 字节 BP4 压缩字典，7 条实际官方码（包括记忆卡、复制、移除与神闪）可本地导入并重新导出。

EXE 演示包包含 39 个角色、817 张可选卡牌、855 张本地插画／头像；SDK 不含这些资源。演示中的卡牌与灵光描述从本地技能／状态表读取固定数量和基础倍率，修复大量 X 占位文本。数值未计角色、装备和战斗加成；少量未求值字段会明确标注，游戏本身的 X 费用机制保留。简体文本为客户端繁体文案转换后的展示文本。

导入和导出完全在本机完成，不调用外部编解码 API。76 项测试通过，打包 EXE 在禁止 Python 网络访问的条件下完成 7 条官方码与界面自测，记录网络事件为 0。ZIP 内附离线自测结果和说明。

当前支持 BP4；未来版本、未知字段及完整游戏内构筑限制仍需继续验证。不同压缩表示可能生成不同但语义相同的码。本轮没有增加对未来所有官方码的兼容承诺。

下载内容分为两类：Windows ZIP／EXE 是图卡演示；Python wheel／源码发行包只包含轻量 SDK。原科普资料附件保留。SDK 已发布到 PyPI，安装命令见下方。

## SDK 快速上手

要求 Python 3.10+。下载本 Release 的 `czn_deckcode-0.1.0a2-py3-none-any.whl` 后，在下载目录执行（同版本覆盖升级需要强制重装）：

```bash
python -m pip install --pre --index-url https://pypi.org/simple czn-deckcode
```

```python
from czn_deckcode import Card, Deck, decode, encode

deck = Deck(char_id="30134", cards=[Card("c_30134_uni1")])
code = encode(deck)                   # 卡组数据 → 分享码
restored = decode(code)               # 分享码 → Deck
assert restored == deck
print(restored.to_dict())             # 转为字典；现有官方码同样交给 decode()
```

SDK 无需 Pillow、Tk 或游戏客户端，编解码不调用外部 API。`decode()` 保留已移除记录，仅展示在用卡牌时可筛选 `not card.removed`。完整安装、字段、JSON 文件及异常处理示例见 [SDK 基础用法](https://github.com/liuzihua699/czn-deckcode/blob/main/docs/sdk.md)，也可下载本 Release 的 `SDK-usage.md` 离线阅读。
