# 编解码离线边界与验证

SDK 的 `encode()` 和 `decode()`、CLI 和桌面导入／导出均在本机运行，不调用 CZNMetaDecks 或其他外部编解码 API，没有联网回退路径。

调用链：

```text
桌面 import_deck_code / encode_deck
  → czn_deckcode.decode / encode
  → Base64URL + 本地混淆变换
  → Python 标准库 zlib + 内置 BP4 字典
  → 本地二进制字段读写
```

图片、中文文案、基础数值及灵光效果库均包含在项目资源目录和 EXE 中。运行时不读取游戏目录，不向服务器发送卡组码。源码中的历史网站验证样本是开发证据，运行时不读取它们；构建时安装 Python 依赖与运行时编解码是不同环节。

验证方法：

- `tests/test_codec.py` 与 `tests/test_visual_builder.py` 禁止创建 socket 和 DNS 查询，再实际导入 7 条游戏导出码、执行图形界面导入和重新导出，检查所有卡牌字段及顺序。
- 桌面 `--self-test` 在导入 SDK、创建 UI 之前安装 Python 审计钩子；遇到任何 `socket.*` 事件即失败，结果记录事件清单。
- 可额外提供官方码回归文件验证已打包的程序，文件仅在测试时读取，不是运行时查询库或解码查表。

```powershell
Start-Process -FilePath .\dist\import-fix\CZNDeckcode.exe -ArgumentList '--self-test', 'offline-check.json', '--official-codes', 'research/samples/official_client_codes.json' -Wait -WindowStyle Hidden
Get-Content offline-check.json
```

`network_blocked: true`、`network_events: []` 和 `official_codes: 7` 表示在禁止 Python 网络访问的情况下完成全部官方码和桌面流程检查。这一保证针对当前项目的运行代码；压缩字典修复不代表未来游戏版本和未知字段也已支持。
