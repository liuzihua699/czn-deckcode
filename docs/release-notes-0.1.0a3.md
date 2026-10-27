# CZN Deckcode v0.1.0a3 · 尽力导入与丢弃报告

当卡组码包含尚不支持的天赋或卡牌选项时，现在可以尽量保留可读取的卡牌，并查看具体丢弃了哪些内容。

## 本次更新

- SDK 新增 `decode_best_effort()`，返回恢复后的 `deck`、丢弃明细 `warnings`、原始记录数及解析是否完整结束。原 `decode()` 继续严格检查，不会自动丢弃数据。
- 能确定字段边界时，跳过不支持的选项或卡牌并继续读取后面的记录；遇到未知状态位、截断等无法确定后续记录边界的问题时，只保留此前已恢复的内容。Base64、版本、BP 头和压缩流错误仍然报错。
- 命令行新增 `decode --best-effort`，卡组 JSON 输出到标准输出，丢弃明细输出到标准错误。
- Windows Demo 默认尽力导入，提供持续可查看的“导入报告”。有丢弃时自动生成恢复后的卡组码；无法恢复任何卡牌或底层解析失败时保留原预设。
- SDK 安装说明统一使用 PyPI，无需先下载 GitHub Release 中的 wheel。

所有编解码与导入操作均在本机完成，不调用外部编解码接口。重新导出的卡组码只包含已恢复内容，无法还原被丢弃的数据；`complete=True` 也不代表没有丢失信息，仍需检查 `warnings`。

## SDK 安装与使用

要求 Python 3.10+。从 PyPI 安装或升级预发布版：

```bash
python -m pip install --upgrade --pre --index-url https://pypi.org/simple czn-deckcode
```

需要固定版本时使用 `czn-deckcode==0.1.0a3`。

```python
from czn_deckcode import decode_best_effort, encode

result = decode_best_effort("粘贴你的卡组码")
print(result.deck.to_dict())
for warning in result.warnings:
    print(warning.card_id, warning.field, warning.message)

recovered_code = encode(result.deck)
```

完整 API 和严格编解码示例见 [SDK 基础用法](https://github.com/liuzihua699/czn-deckcode/blob/v0.1.0a3/docs/sdk.md)，发布流程见 [PyPI 发布步骤](https://github.com/liuzihua699/czn-deckcode/blob/v0.1.0a3/docs/publishing.md)。SDK 运行时零第三方依赖，不包含 GUI、卡图或游戏客户端资源。

## Windows Demo

下载 **CZNDeckcode-windows-x64.zip**，解压后双击 **CZNDeckcode.exe**，无需安装 Python 或游戏。更新时保留原 EXE 旁的 `user_data` 文件夹。Windows ZIP／EXE 是独立图形演示，SDK 的 wheel／源码发行包只包含轻量 SDK。

88 项自动化测试通过，覆盖实际含不支持天赋的卡组码、后续记录恢复、未知状态位、截断、命令行和桌面端导入报告。当前支持 BP4，不验证完整游戏构筑规则，也不保证恢复后的卡组能被游戏或第三方网站接受。
