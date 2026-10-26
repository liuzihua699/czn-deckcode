# BP4 卡组码格式

本实现依据网站的受控请求/响应样本还原。仓库保存了真实样本和额外的数字边界、单字段、长文本对照；没有使用服务端源代码。

## 完整流程

编码：

```text
Deck
  → ULEB128 和 UTF-8 二进制记录
  → raw DEFLATE（网站会引用预置字典；本地编码使用自包含压缩流）
  → 前置明文文件头 42 50 04（ASCII BP + 版本 4）
  → xorshift32 字节掩码异或整个消息
  → Base64url，去掉 = padding
```

解码按相反顺序执行。版本头本身也参与异或。常见的外观前缀 `v6l8` 解成 `bf a9 7c`；异或后才是 `42 50 04`。因此 `v6l8` 是外观特征，版本判断依据解混淆后的头部。

## 异或序列

32 位无符号初始状态为 `0x870fcd0a`。每轮先更新状态：

```python
state ^= (state << 13) & 0xffffffff
state ^= state >> 17
state ^= (state << 5) & 0xffffffff
```

再把该状态按 little endian 输出 4 字节，依次与消息异或。第一轮状态为 `0xab78f9fd`，输出 `fd f9 78 ab`，所以头部 `42 50 04` 经异或变为 `bf a9 7c`。

这是可逆的格式混淆。它没有长度限制，也不需要预先保存长密钥表。多组不重复三元组的字符串和多卡样本恢复的 1645 个连续字节，均与生成器吻合。早期仅观察到压缩主体前 46 字节时，尚不足以确定生成器；长样本的线性递推才最终定位到 xorshift32 与字节对齐。

## 二进制数据

所有整数为 unsigned LEB128：每字节低 7 位为数据，高位 1 表示有后续字节。字符 ID 以 uint32 编码，例如 `30134 → b6 eb 01`。字符串是 `ULEB128(UTF-8 字节数) + UTF-8 字节`。

```text
ULEB128 charId
ULEB128 cardCount
card record × cardCount
```

每条 card record：

```text
u8 flags
string effectiveCardId
[顿悟类别 u8 + string 顿悟资源 ID]  flags & 0x02
[string 神性顿悟资源 ID]            flags & 0x40
[ULEB128 modifierCount + modifiers] flags & 0x04
```

| 位 | 含义 |
| --- | --- |
| `0x01` | removed，卡牌移除 |
| `0x02` | 顿悟资源 |
| `0x04` | 卡牌 modifier 列表，用于复制：数量 1，字符串 `TALENT_REPLICATION` |
| `0x40` | 神性顿悟资源 |

`_pot` / `_lbk` 变体直接写入 effectiveCardId。`c_30134_srt1_rsp2` 则写入基础卡 ID，顿悟类别为 1，资源 ID 为 `rsp2_c_30134_srt1`；公共顿悟类别为 3，资源 ID 类似 `c00001`。神性顿悟随后写入其完整资源 ID。

例如普通单卡 `charId=0, cardId=c_0_srt1`，压缩前是：

```text
00 01 00 08 63 5f 30 5f 73 72 74 31
│  │  │  │  └── c_0_srt1
│  │  │  └───── 字符串长 8
│  │  └──────── flags = 0
│  └─────────── 1 张卡
└────────────── charId = 0
```

## 压缩

网站导出采用 raw DEFLATE，并引用预置字典。字典包括卡牌/顿悟/modifier 的常见 ID 片段。普通无字典的 `zlib.decompress()` 会遇到“距离超过已有输出”等错误；这一错误本身不表示还有未知加密。

压缩参数和匹配选择可能产生不同、但都有效的 DEFLATE 流。SDK 使用 Python 标准库 zlib 生成不引用字典的自包含压缩流；网站的解码器也能接受这种表示。解码器接受标准 raw DEFLATE 的 fixed、dynamic 和 stored block。字典与实现见 `src/czn_deckcode/_compression.py`，恢复范围见 [dictionary.md](dictionary.md)。

## 边界

输入包含 Base64url 字符和可选正确 padding；检查 BP 头、版本、DEFLATE 结束、载荷完全消费、uint32 与字符串长度等。SDK 对无法表示的字段组合或未识别记录结构报错。BP4 没有提供可用于检测所有任意内容更改的密码学校验；改动后仍然构成合法结构的码会被解析为相应卡组。
