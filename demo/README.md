# 图卡演示 Demo

本目录为 SDK 的独立图形演示，包含窗口代码、本地图卡与展示用文案。它不属于 PyPI 的 SDK wheel 或源码发行包。

在仓库根目录运行：

```bash
python -m pip install -e .
python -m pip install -r demo/requirements.txt
python scripts/desktop_entry.py
```

Windows EXE 仍使用根目录 `CZNDeckcode.spec` 构建；素材来源说明位于 `assets/NOTICE.txt`。预设配置路径保持为 EXE 旁的 `user_data/decks.json`，源码运行使用仓库内的 `user_data/decks.json`。

从卡组码导入时默认尽量保留可识别的内容：跳过不支持的选项或卡牌，并通过“查看导入报告”显示丢弃明细。遇到无法确定后续记录边界的损坏时只恢复此前记录；底层格式错误或没有恢复任何卡牌时保留当前预设。有丢弃内容的导入会生成恢复后的卡组码，重新导出不包含被丢弃的数据。
