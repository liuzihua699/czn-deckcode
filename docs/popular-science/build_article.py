"""Build the illustrated article as a standalone offline HTML and sharing ZIP.

Documentation tooling only: Python 3.10+, Markdown, Pillow.
Run from the repository: .venv/bin/python docs/popular-science/build_article.py
"""

from __future__ import annotations

import base64
from html import escape, unescape
import mimetypes
from pathlib import Path
import re
from urllib.parse import unquote
import zipfile

import markdown
from PIL import Image


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
TITLE = "关于卡厄思梦境的卡组码编解码原理，根据大量的卡组码示例反推其编解码算法"
SOURCE = ROOT / f"{TITLE}.md"
OUTPUT = ROOT / "卡组码科普文.html"
BUNDLE = PROJECT / "dist" / "卡组码科普文_图文与GIF.zip"


def data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def embed_image(match: re.Match) -> str:
    attributes = match.group(1)
    source = re.search(r'src="([^"]+)"', attributes)
    if source is None:
        raise ValueError("Image without a source")
    relative = unescape(source.group(1))
    path = (ROOT / unquote(relative)).resolve()
    if ROOT not in path.parents:
        raise ValueError(f"Nonlocal article image: {relative}")
    with Image.open(path) as image:
        width, height = image.size
    attributes = attributes.replace(source.group(0), f'src="{data_uri(path)}"')
    extra = f' width="{width}" height="{height}" loading="lazy" decoding="async"'
    if path.suffix == ".gif":
        extra += f' class="animated" data-still="{data_uri(path.with_suffix(".png"))}"'
    return f"<img{attributes}{extra}>"


CSS = """
:root{color-scheme:light;--ink:#172338;--muted:#64748b;--blue:#2563eb;--line:#dde5ef;--soft:#f4f7fc}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#fff;color:var(--ink);font:18px/1.95 -apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei','Noto Sans CJK SC',sans-serif}
a{color:var(--blue);text-underline-offset:4px;overflow-wrap:anywhere}header,main,footer{max-width:940px;margin:auto;padding:0 36px}
.top{border-bottom:1px solid var(--line);padding:15px 0}.top-inner{max-width:940px;margin:auto;padding:0 36px;display:flex;align-items:center;justify-content:space-between;gap:12px;font-size:13px;color:var(--muted)}
.tag{color:var(--blue);font-weight:700;letter-spacing:.12em}header{padding-top:58px;padding-bottom:26px}.eyebrow{color:var(--muted);font-size:14px}h1{font-size:36px;line-height:1.6;letter-spacing:-.025em;margin:20px 0 24px;font-weight:750}header p{color:var(--muted);font-size:16px;margin:0}.rule{height:4px;width:60px;background:var(--blue);margin-bottom:22px}
main>h1{display:none}main{padding-bottom:64px}h2{font-size:27px;line-height:1.6;margin:64px 0 22px;letter-spacing:-.02em;scroll-margin-top:20px}h3{font-size:22px;margin:38px 0 16px}p{margin:19px 0}strong{font-weight:750;color:#0f2448}
blockquote{border-left:4px solid var(--blue);margin:28px 0;padding:10px 20px;background:var(--soft);color:#41536e;font-size:15px}blockquote p{margin:4px 0}
pre{background:#f3f6fb;border:1px solid var(--line);padding:20px 22px;border-radius:10px;overflow-x:auto;line-height:1.75;font-size:14px}code{font-family:'Cascadia Code',Consolas,'DejaVu Sans Mono',monospace;font-size:.86em;background:#eef2f9;border-radius:4px;padding:2px 4px;overflow-wrap:anywhere}pre code{background:transparent;padding:0;font-size:inherit;overflow-wrap:normal}
img{display:block;width:100%;height:auto;margin:30px auto 8px;border:1px solid var(--line);border-radius:12px;background:#fff}p:has(>em:only-child){font-size:14px;line-height:1.8;color:var(--muted);margin-top:10px}em{font-style:normal}
.table-wrap{overflow-x:auto;margin:28px 0}table{width:100%;border-collapse:collapse;font-size:16px}th{text-align:left;background:#edf3ff}td,th{padding:12px 15px;border:1px solid var(--line)}td:first-child{white-space:nowrap}tr:nth-child(even){background:#f9fbff}
.toc{background:var(--soft);border:1px solid var(--line);border-radius:12px;padding:18px 24px;margin:32px 0 38px;font-size:15px}.toc h2{font-size:16px;margin:0 0 8px}.toc ul{margin:0;padding-left:22px}.toc li{margin:5px 0}.toc a{text-decoration:none}
button{border:1px solid #c7d4e8;border-radius:6px;background:#fff;color:var(--blue);padding:7px 12px;font:inherit;font-size:13px;cursor:pointer}button:hover{background:#eef4ff}footer{font-size:13px;color:var(--muted);border-top:1px solid var(--line);padding-top:24px;padding-bottom:38px}.back{float:right}
@media(max-width:640px){body{font-size:16px;line-height:1.9}header,main,footer,.top-inner{padding-left:20px;padding-right:20px}header{padding-top:32px}h1{font-size:28px;line-height:1.65}h2{font-size:23px;margin-top:44px}pre{font-size:12px;padding:14px}table{font-size:14px}td,th{padding:9px}.eyebrow{font-size:12px}}
@media print{.top,.toc,.back{display:none}header{padding-top:0}h1{font-size:25px}body{font-size:11pt}h2{font-size:17pt;break-after:avoid}img,table,pre{break-inside:avoid}a{color:inherit}header,main,footer{max-width:none;padding-left:0;padding-right:0}main{padding-bottom:0}}
"""

SCRIPT = """
const pictures=[...document.querySelectorAll('img.animated')];
pictures.forEach(p=>p.dataset.animation=p.src);
let paused=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const button=document.getElementById('motion');
function apply(){pictures.forEach(p=>p.src=paused?p.dataset.still:p.dataset.animation);button.textContent=paused?'播放 GIF 动画':'暂停 GIF 动画';button.setAttribute('aria-pressed',String(paused));}
button.addEventListener('click',()=>{paused=!paused;apply();});apply();
window.addEventListener('beforeprint',()=>{pictures.forEach(p=>p.src=p.dataset.still)});
window.addEventListener('afterprint',apply);
"""


def main() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    converter = markdown.Markdown(extensions=["fenced_code", "tables", "toc", "sane_lists"])
    body = converter.convert(text)
    body = re.sub(r"<img([^>]+?)/?>", embed_image, body)
    body = re.sub(r"<table>(.*?)</table>", r'<div class="table-wrap"><table>\1</table></div>', body, flags=re.S)
    # Embed the printable flowchart link too, so this HTML needs no image folder.
    for destination in re.findall(r'href="(assets/[^"]+)"', body):
        body = body.replace(f'href="{destination}"', f'href="{data_uri(ROOT / unescape(destination))}" target="_blank"')
    assert len(re.findall('class="animated"', body)) == 2
    assert not re.search(r'<img[^>]+src="(?!data:)', body)
    toc_items = []
    for anchor, title in re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', body):
        toc_items.append(f'<li><a href="#{anchor}">{title}</a></li>')
    toc = '<nav class="toc" aria-label="文章目录"><h2>阅读目录</h2><ul>' + ''.join(toc_items) + '</ul></nav>'
    # Place the directory after the opening scope note, before the first section.
    first_section = body.find('<h2 id=')
    body = body[:first_section] + toc + body[first_section:]
    html = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{escape(TITLE)}</title><style>{CSS}</style></head>
<body id="top"><div class="top"><div class="top-inner"><span class="tag">CZN · 卡组码研究</span><button id="motion" type="button">暂停 GIF 动画</button></div></div>
<header><div class="rule"></div><div class="eyebrow">技术科普 · 真实样例 · 图解与动画</div><h1>{escape(TITLE)}</h1><p>从一串分享码出发，逐层看清角色、卡牌和状态怎样被装进去。</p></header>
<main>{body}</main><footer><a class="back" href="#top">回到顶部 ↑</a>文中图像与 GIF 已嵌入本文件，可断网阅读。参考资料随分享包提供。</footer><script>{SCRIPT}</script></body></html>'''
    OUTPUT.write_text(html, encoding="utf-8")
    BUNDLE.parent.mkdir(exist_ok=True)
    # Preserve repository paths so links between the article and evidence work.
    included = {SOURCE, OUTPUT, ROOT / "README.md", PROJECT / "README.md", PROJECT / "LICENSE"}
    included.update(ROOT.glob("build_*.py"))
    included.update((ROOT / "assets").glob("*"))
    included.update((PROJECT / "docs").glob("*.md"))
    included.update((PROJECT / "src" / "czn_deckcode").glob("*.py"))
    included.add(PROJECT / "src" / "czn_deckcode" / "py.typed")
    included.update((PROJECT / "research").rglob("*.json"))
    included.add(PROJECT / "research" / "README.md")
    included.update((PROJECT / "tests").glob("*.py"))
    included.update((PROJECT / "examples").glob("*"))
    included.update((PROJECT / "licenses").glob("*.txt"))
    included.update((PROJECT / "scripts").glob("*.py"))
    included.update((PROJECT / "scripts").glob("*.ps1"))
    included.update(PROJECT / name for name in (
        "CZNDeckcode.spec", "MANIFEST.in", "run-ui.sh", "启动卡组工具.cmd",
    ))
    root_readme = (
        "卡组码科普文分享包\n\n"
        "双击“打开科普文.html”阅读，图像和两段 GIF 已内嵌，无需联网。\n"
        "可编辑正文、PNG、SVG、GIF 位于 docs/popular-science/。\n"
        "同包附技术报告、SDK源码和采样证据，保留目录结构以便跳转。\n"
        "静态图与GIF均为本文制作，可与文章一起使用。\n"
    )
    with zipfile.ZipFile(BUNDLE, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(included):
            if not path.is_file():
                raise FileNotFoundError(path)
            archive.write(path, path.relative_to(PROJECT).as_posix())
        archive.writestr("阅读说明.txt", root_readme)
        root_html = html.replace('href="../../', 'href="').replace('href="../', 'href="docs/')
        archive.writestr("打开科普文.html", root_html)
        archive.writestr("pyproject.toml", (PROJECT / "pyproject.toml").read_text(encoding="utf-8"))
    with zipfile.ZipFile(BUNDLE) as archive:
        assert archive.testzip() is None
    print("HTML:", OUTPUT, OUTPUT.stat().st_size)
    print("ZIP:", BUNDLE, BUNDLE.stat().st_size)


if __name__ == "__main__":
    main()
