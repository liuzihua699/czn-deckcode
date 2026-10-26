# 验证资料

这些文件是开发样本，SDK 和 UI 运行时不会读取它们。运行全部离线回归：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

`samples/30134.json` 是最初 61 个受控构筑变化，包括用户最初的两个码。`matrix.json`、`probes.json`、`charprobe.json` 是跨角色、卡序、变体和数量的早期样本。错误字符串或失败请求保留为历史证据，不代表有效卡组码。

`numeric.json` 包含数字边界和 ID 形式实验；网站会把超 uint32 数字截断，SDK 明确拒绝此类输入。`fields.json` 包含单字段和组合字段实验；失败的输入没有参与有效码验证。

`stream_short.json`、`stream_medium.json`、`stream_long.json` 用小写字母数字构造受控、无重复三元组的长 ID。已知序列化原文压缩后与网站码比较，可以恢复掩码；最终通过四字节对齐识别 xorshift32，而非在 SDK 中保存样本密钥表。最长样本独立验证了 1645 个压缩主体掩码字节。

`local_export_verification.json` 记录 SDK 生成的新码和网站导入响应，共 8 个成功案例。它们证明本地自包含 raw DEFLATE 流与网站使用的格式兼容；运行时不需要重复调用网站。

原始网站使用的预置字典尚未完全恢复。当前实现对未知位置使用两种不同填充值解压，只有结果一致才返回数据。所有已保存的有效样本均通过这一检查；未知引用不会被悄悄替换。详见 `docs/dictionary.md`。

样本只用于格式兼容性分析，不代表对所有游戏版本、卡牌机制或未知扩展的覆盖。
