# 图卡演示 Demo

本目录为 SDK 的独立图形演示，包含窗口代码、本地图卡与展示用文案。它不属于 PyPI 的 SDK wheel 或源码发行包。

在仓库根目录运行：

```bash
python -m pip install -e .
python -m pip install -r demo/requirements.txt
python scripts/desktop_entry.py
```

Windows EXE 仍使用根目录 `CZNDeckcode.spec` 构建；素材来源说明位于 `assets/NOTICE.txt`。预设配置路径保持为 EXE 旁的 `user_data/decks.json`，源码运行使用仓库内的 `user_data/decks.json`。
