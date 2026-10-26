"""Build the article's editable SVG figures and 2x PNG exports.

Documentation-only tooling: requires cairosvg and Pillow, not the SDK runtime.
Run from any directory with the project's documentation Python environment.
"""

from __future__ import annotations

from html import escape
from pathlib import Path
import xml.etree.ElementTree as ET

import cairosvg
from PIL import Image, ImageFont


OUT = Path(__file__).resolve().parent / "assets"
FONT = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
BLUE = "#2563eb"
INK = "#111827"
MUTED = "#566176"
PURPLE = "#7c3aed"
TINT = "#eff6ff"
LILAC = "#f5f0ff"
ORANGE = "#b45309"


class Figure:
    def __init__(self, name: str, number: int, title: str, subtitle: str, height: int):
        self.name = name
        self.width = 1200
        self.height = height
        self.lines: list[str] = []
        self.lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}">')
        self.lines.append(f'<title>{escape(title)}</title>')
        self.lines.append(f'<desc>{escape(subtitle)}</desc>')
        self.lines.append('<style>text { font-family: "Noto Sans CJK SC", "Microsoft YaHei", sans-serif; }</style>')
        self.lines.append('<defs><marker id="arrow" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0,10 3.5,0 7" fill="#2563eb"/></marker></defs>')
        self.rect(0, 0, 1200, height, "#ffffff", "none", 0)
        self.text(64, 43, "CZN / BP4 图解", 18, BLUE, weight=700)
        self.text(64, 91, title, 34, weight=700, max_width=1072)
        self.text(64, 132, subtitle, 22, MUTED, max_width=1072)

    def rect(self, x, y, width, height, fill="#ffffff", stroke="#d1d5db", radius=12):
        self.lines.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')

    def text(self, x, y, value, size=24, fill=INK, anchor="start", weight=400, max_width=None):
        value = str(value)
        if FONT.is_file():
            width = ImageFont.truetype(str(FONT), size).getlength(value)
            if max_width is not None and width > max_width:
                raise ValueError(f"{self.name}: text exceeds allotted width: {value} ({width}>{max_width})")
            left = x if anchor == "start" else x - width / 2 if anchor == "middle" else x - width
            if left < 16 or left + width > self.width - 16:
                raise ValueError(f"{self.name}: text outside canvas: {value}")
        self.lines.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{escape(value)}</text>')

    def arrow(self, x1, y1, x2, y2):
        self.lines.append(f'<path d="M {x1} {y1} L {x2} {y2}" fill="none" stroke="{BLUE}" stroke-width="2.5" marker-end="url(#arrow)"/>')

    def note(self, x, y, value, size=21, fill=MUTED):
        if FONT.is_file():
            width = ImageFont.truetype(str(FONT), size).getlength(value)
        else:
            width = len(value) * size
        self.rect(x - 8, y - size - 3, width + 16, size + 12, "#ffffff", "none", 4)
        self.text(x, y, value, size, fill)

    def footer(self, text):
        self.text(64, self.height - 34, text, 20, MUTED, max_width=1072)

    def save(self):
        self.lines.append("</svg>")
        OUT.mkdir(parents=True, exist_ok=True)
        svg = OUT / f"{self.name}.svg"
        png = OUT / f"{self.name}.png"
        svg.write_text("\n".join(self.lines) + "\n", encoding="utf-8")
        ET.parse(svg)
        cairosvg.svg2png(url=str(svg), write_to=str(png), scale=2)
        with Image.open(png) as image:
            assert image.size == (self.width * 2, self.height * 2)
        print(f"OK {self.name}: valid SVG, PNG {self.width * 2}×{self.height * 2}")


def layers():
    f = Figure("01-layers", 1, "把卡组码一层层拆开", "以一张普通卡为例：外面的文字，最终还原为角色、卡牌和状态。", 1000)
    rows = [
        (174, "01  可以复制的文字", "Base64url", "v6l8cOjiNq3Nzwd5bz8N5EYk-E6grJg", TINT),
        (362, "02  撤去文字包装", "经过 XOR 混淆的字节", "bf a9 7c 70 e8 e2 36 ad cd cf 07 79 …", "#f8fafc"),
        (550, "03  撤销 XOR 混淆", "格式头 + 压缩数据", "42 50 04  |  db f6 9a 91 91 81 27 39 …", LILAC),
        (738, "04  解压后的内容", "真正的卡组记录", "角色 30134  ·  1 条记录  ·  c_30134_srt1  ·  普通状态", TINT),
    ]
    for y, label, title, data, fill in rows:
        f.rect(64, y, 1072, 148, fill, "#d5deed")
        f.text(92, y + 38, label, 22, BLUE, weight=700)
        f.text(92, y + 79, title, 28, weight=700)
        f.text(92, y + 119, data, 25, MUTED, max_width=1016)
    for start, label in [(322, "Base64url 解码"), (510, "使用相同掩码 XOR"), (698, "检查头部，解压主体")]:
        f.arrow(600, start + 3, 600, start + 35)
        f.note(650, start + 28, label, 21)
    f.footer("BP4 的头部也参与混淆；仅做 Base64url 解码，还看不到 BP。")
    f.save()


def comparison():
    f = Figure("02-build-comparison", 2, "两份原始构筑，变化发生在哪里？", "卡序、有效卡牌 ID 和移除状态都发生变化，记录总数仍然为 8。", 1120)
    columns = [
        (64, "构筑 1", "64 字符 → 解压后 124 字节", ["srt1_pot", "srt2_pot", "srt3", "srt4", "uni1", "uni2", "uni3", "uni4"]),
        (624, "构筑 2", "64 字符 → 解压后 120 字节", ["srt2_pot", "srt3", "srt4", "uni1", "uni2", "uni3", "uni4", "srt1"]),
    ]
    for col, (x, title, sub, cards) in enumerate(columns):
        f.rect(x, 176, 512, 688, "#fafbfe", "#d1d5db")
        f.text(x + 28, 219, title, 30, BLUE, weight=700)
        f.text(x + 28, 257, sub, 22, MUTED)
        f.text(x + 28, 299, "顺序    有效卡牌 ID", 21, MUTED)
        f.text(x + 482, 299, "flags", 20, MUTED, anchor="end")
        for number, suffix in enumerate(cards, 1):
            y = 320 + (number - 1) * 64
            special = (col == 0 and number == 1) or (col == 1 and number == 8)
            fill = LILAC if special else "#ffffff"
            stroke = "#c4b5fd" if special else "#e5e7eb"
            f.rect(x + 20, y, 472, 54, fill, stroke, 8)
            f.text(x + 35, y + 36, str(number), 23, MUTED)
            f.text(x + 80, y + 36, "c_30134_" + suffix, 23, PURPLE if special else INK)
            f.text(x + 472, y + 36, "01" if col == 1 and number == 8 else "00", 23, PURPLE if special else MUTED, anchor="end", weight=700 if special else 400)
    f.rect(64, 904, 1072, 140, LILAC, "#ddd6fe")
    f.text(92, 946, "被移除的卡，仍有自己的记录", 28, PURPLE, weight=700)
    f.text(92, 988, "srt1_pot → srt1，移至末尾，flags 变为 01。", 25, max_width=1016)
    f.text(92, 1023, "ID 少了“_pot”这 4 个字节，因此原文从 124 变成 120 字节。", 22, MUTED, max_width=1016)
    f.footer("这是这两份输入的具体差异；不能归结为“只改了一个删除位”。")
    f.save()


def record():
    f = Figure("03-binary-record", 3, "一张普通卡，怎样写成 18 字节？", "按固定顺序存储字段，省去 JSON 中反复出现的字段名。", 890)
    cells = [
        (64, 240, "角色编号", "b6 eb 01", "3 字节", "30134", TINT),
        (304, 160, "记录数量", "01", "1 字节", "1 条", "#f8fafc"),
        (464, 160, "状态标记", "00", "1 字节", "无特殊状态", LILAC),
        (624, 160, "ID 长度", "0c", "1 字节", "12 字节", "#f8fafc"),
        (784, 352, "卡牌 ID 内容", None, "12 字节", "c_30134_srt1", TINT),
    ]
    for x, width, label, data, length, decoded, fill in cells:
        f.rect(x, 196, width, 254, fill, "#cbd5e1", 0)
        f.text(x + width / 2, 238, label, 23, weight=700, anchor="middle")
        if data:
            f.text(x + width / 2, 301, data, 30, BLUE, anchor="middle")
        else:
            f.text(x + width / 2, 286, "63 5f 33 30 31 33", 23, BLUE, anchor="middle")
            f.text(x + width / 2, 325, "34 5f 73 72 74 31", 23, BLUE, anchor="middle")
        f.text(x + width / 2, 370, length, 21, MUTED, anchor="middle")
        f.text(x + width / 2, 421, decoded, 22, anchor="middle")
    f.rect(64, 498, 1072, 178, "#fafbfe", "#d5deed")
    f.text(92, 542, "数字使用可变长度整数，字符串先写长度、再写内容。", 26, weight=700, max_width=1016)
    f.text(92, 589, "b6 eb 01 → 54 + 107 × 128 + 1 × 16384 = 30134", 25, BLUE)
    f.text(92, 637, "0c 是十六进制的 12，随后正好读取 12 字节 ID。", 24, MUTED)
    f.text(64, 745, "完整二进制记录", 25, weight=700)
    f.rect(64, 768, 1072, 58, TINT, "#dbeafe", 8)
    f.text(84, 806, "b6 eb 01 01 00 0c 63 5f 33 30 31 33 34 5f 73 72 74 31", 23, BLUE, max_width=1032)
    f.footer("每两个十六进制字符表示一个字节；图中区块宽度不按字节数缩放。")
    f.save()


def prefix():
    f = Figure("04-header-prefix", 4, "为什么这些码都以 v6l8 开头？", "BP4 的固定头与固定掩码，先产生相同的三个字节。", 1030)
    centers = [420, 660, 900]
    for row, (label, values, fill) in enumerate([
        ("BP4 格式头", ["42", "50", "04"], TINT),
        ("掩码前三字节", ["fd", "f9", "78"], "#f8fafc"),
        ("逐字节 XOR", ["bf", "a9", "7c"], LILAC),
    ]):
        y = 187 + row * 133
        f.text(64, y + 61, label, 26, BLUE if row == 2 else INK, weight=700)
        for x, value in zip(centers, values):
            f.rect(x - 90, y, 180, 94, fill, "#d5deed")
            f.text(x, y + 62, value, 40, PURPLE if row == 2 else BLUE, anchor="middle", weight=700)
    f.arrow(660, 557, 660, 618)
    f.note(710, 600, "重新按 6 位分组", 22)
    f.text(64, 660, "24 位二进制 → 四组 6 位 → 四个 Base64url 字符", 26, weight=700)
    for x, bits, number, letter in [(64, "101111", "47", "v"), (344, "111010", "58", "6"), (624, "100101", "37", "l"), (904, "111100", "60", "8")]:
        f.rect(x, 700, 232, 170, TINT, "#bfdbfe")
        f.text(x + 116, 743, bits, 29, BLUE, anchor="middle")
        f.text(x + 116, 783, "字符表序号 " + number, 21, MUTED, anchor="middle")
        f.text(x + 116, 842, letter, 42, PURPLE, anchor="middle", weight=700)
    f.rect(64, 908, 1072, 62, LILAC, "#ddd6fe")
    f.text(600, 950, "v6l8 表明共同的格式开头；角色编号要到解压后才出现。", 24, anchor="middle")
    f.footer("Base64url 是把二进制换成文字的表示方式，本身不压缩数据。")
    f.save()


def pipeline():
    f = Figure("05-codec-pipeline", 5, "完整编码流程：从清单到分享码", "一张卡的实测结果；解码时按相反顺序逐层还原。", 1240)
    rows = [
        ("构筑清单", "角色 30134，卡牌 c_30134_srt1", "输入", "#fafbfe"),
        ("写成二进制", "角色、数量、状态、ID 长度、ID 内容", "18 字节", TINT),
        ("raw DEFLATE 压缩", "生成不引用原网站字典的自包含压缩流", "20 字节", "#fafbfe"),
        ("加入 BP4 头部", "在压缩数据前加入 42 50 04", "23 字节", LILAC),
        ("整体 XOR 混淆", "格式头和压缩数据一起处理", "23 字节", "#fafbfe"),
        ("Base64url 转成文字", "去掉末尾用于补位的等号", "31 字符", TINT),
    ]
    for index, (title, detail, length, fill) in enumerate(rows):
        y = 178 + index * 144
        f.rect(136, y, 872, 112, fill, "#d5deed")
        f.text(94, y + 66, str(index + 1).zfill(2), 26, BLUE, anchor="middle", weight=700)
        f.text(164, y + 44, title, 28, weight=700)
        f.text(164, y + 86, detail, 22, MUTED, max_width=646)
        f.text(980, y + 45, length, 26, BLUE, anchor="end", weight=700)
        if index < 5:
            f.arrow(572, y + 115, 572, y + 140)
    f.arrow(1088, 1008, 1088, 218)
    f.note(1048, 598, "解码", 22)
    f.rect(64, 1100, 1072, 70, LILAC, "#ddd6fe")
    f.text(600, 1146, "v6l8cOjiNq3Nzwd5bz8N5EYk-E6grJg", 30, PURPLE, anchor="middle", weight=700)
    f.footer("短数据可能越压越大；此例 18 → 20 字节正常。XOR 不改变数据长度。")
    f.save()


def dictionary():
    f = Figure("06-dictionary", 6, "字典恢复到了哪一步？", "当前确认的是末尾 238 字节的一段后缀，完整字典还可能有更早的前缀。", 1000)
    x0, total_width = 64, 1072
    spans = [(18, True), (61, False), (46, True), (11, False), (102, True)]
    x = x0
    for count, known in spans:
        width = total_width * count / 238
        f.rect(round(x, 2), 218, round(width, 2), 96, "#dbeafe" if known else "#ffedd5", "#ffffff", 0)
        if width > 40:
            f.text(x + width / 2, 277, str(count), 24 if width < 66 else 28, BLUE if known else ORANGE, anchor="middle", weight=700)
        x += width
    f.text(64, 194, "更早前缀：尚不能确定", 21, MUTED)
    f.text(64, 351, "-238", 21, MUTED)
    f.text(1136, 351, "-1（字典末尾）", 21, MUTED, anchor="end")
    f.rect(64, 390, 1072, 104, "#fafbfe", "#d5deed")
    f.rect(88, 420, 30, 30, "#dbeafe", "#bfdbfe", 4)
    f.text(136, 446, "166 字节已确认", 27, BLUE, weight=700)
    f.rect(580, 420, 30, 30, "#ffedd5", "#fed7aa", 4)
    f.text(628, 446, "72 字节未确认", 27, ORANGE, weight=700)
    f.text(64, 557, "未确认的两段", 27, weight=700)
    f.text(64, 604, "-220 至 -160：61 字节；-113 至 -103：11 字节。", 25, MUTED)
    f.rect(64, 650, 1072, 112, TINT, "#bfdbfe")
    f.text(92, 692, "本地编码", 27, BLUE, weight=700)
    f.text(92, 735, "生成自包含的压缩流，不依赖原网站字典。", 25)
    f.rect(64, 790, 1072, 112, LILAC, "#ddd6fe")
    f.text(92, 832, "解码原网站的码", 27, PURPLE, weight=700)
    f.text(92, 875, "若引用未知字典内容，会明确报错，避免输出猜测数据。", 25)
    f.footer("条带按字节数等比例绘制：蓝色为已确认，橙色为未确认。")
    f.save()


if __name__ == "__main__":
    for build in (layers, comparison, record, prefix, pipeline, dictionary):
        build()
