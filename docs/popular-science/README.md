# 科普文与配图

正文标题：**《关于卡厄思梦境的卡组码编解码原理，根据大量的卡组码示例反推其编解码算法》**。

- `关于卡厄思梦境的卡组码编解码原理，根据大量的卡组码示例反推其编解码算法.md`：可编辑、可转载的 Markdown 正文。
- `卡组码科普文.html`：可双击阅读的离线版本，内嵌所有正文图片和两段 GIF；顶部按钮可暂停、播放动画。
- `assets/01` 至 `06`：六张静态图，PNG 为 2 倍尺寸，SVG 可编辑。
- `assets/07-encoding.gif`、`08-decoding.gif`：编码、解码动画，分别约 14 秒循环；同名 PNG 为静态备用。
- 项目 `dist/卡组码科普文_图文与GIF.zip`：完整分享包，包含原稿、图像、离线 HTML 和相关技术资料。

文章用于科普已采样的 BP4 格式，具体已知、未知边界见正文。SDK 的运行依赖未改变；下面的依赖仅供重建文档。

重建（Linux，需中文字体与 Cairo）：

```bash
python -m pip install cairosvg Pillow Markdown
python docs/popular-science/build_figures.py
python docs/popular-science/build_animations.py
python docs/popular-science/build_article.py
```

图像脚本默认使用系统 Noto Sans CJK 字体。变更正文或图像后，重新运行 `build_article.py` 即可更新离线 HTML 和分享包。
