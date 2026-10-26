"""Render the article's two local BP4 codec animations with Pillow.

Run from any directory with Python 3 and Pillow. No network or SDK dependency.
All bytes below are a recorded one-card example verified against czn_deckcode.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "assets"
W, H = 1200, 1000
BLUE = "#2563eb"
PURPLE = "#7c3aed"
INK = "#111827"
MUTED = "#64748b"
LINE = "#d1d5db"
SOFT = "#f8fafc"
TINT = "#eff6ff"
DONE = "#e0e7ff"
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

PAYLOAD = "b6 eb 01 01 00 0c 63 5f 33 30 31 33 34 5f 73 72 74 31"
COMPRESSED = "db f6 9a 91 91 81 27 39 de d8 c0 d0 d8 24 be b8 a8 c4 10 00"
MESSAGE = "42 50 04 " + COMPRESSED
WIRE = "bf a9 7c 70 e8 e2 36 ad cd cf 07 79 6f 3f 0d e4 46 24 f8 4e a0 ac 98"
CODE = "v6l8cOjiNq3Nzwd5bz8N5EYk-E6grJg"


def font(size: int, bold: bool = False, mono: bool = False):
    return ImageFont.truetype(MONO if mono else BOLD if bold else FONT, size)


def wrapped(draw: ImageDraw.ImageDraw, text: str, width: int, fnt):
    lines = []
    line = ""
    for char in text:
        if char == "\n":
            lines.append(line)
            line = ""
        elif line and draw.textlength(line + char, font=fnt) > width:
            lines.append(line)
            line = char
        else:
            line += char
    if line:
        lines.append(line)
    return lines


def para(draw, text, xy, width, size=26, fill=INK, bold=False, gap=13):
    fnt = font(size, bold)
    x, y = xy
    for line in wrapped(draw, text, width, fnt):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += size + gap
    return y


def hex_rows(value: str, count=9):
    values = value.split()
    return [" ".join(values[i:i + count]) for i in range(0, len(values), count)]


@dataclass(frozen=True)
class Stage:
    label: str
    badge: str
    title: str
    input: str
    output_label: str
    output: tuple[str, ...]
    note: str
    kind: str = "hex"


ENCODING = [
    Stage("准备构筑", "角色、卡牌、状态", "先把这份构筑说清楚", "输入：角色 30134，只带一张普通卡。", "卡组内容", ("角色：30134", "卡牌：c_30134_srt1", "数量：1 张", "移除：否　复制：否"), "图片与中文名称另行映射；这里保存角色、卡牌 ID 和状态。", "text"),
    Stage("写成二进制", "18 字节", "按约定顺序写入字段", "角色 → 卡牌数量 → 状态 → ID 长度 → ID。", "二进制卡组记录 · 18 字节", tuple(hex_rows(PAYLOAD)), "b6 eb 01 是角色 30134；01 是一张卡；00 是状态；0c 是 ID 长度 12。"),
    Stage("DEFLATE 压缩", "20 字节", "压缩刚才的卡组记录", "输入：18 字节二进制记录。", "raw DEFLATE 结果 · 20 字节", tuple(hex_rows(COMPRESSED)), "这个样例太短，压缩开销使结果稍长；完整卡组的重复内容更容易压缩。"),
    Stage("添加格式头", "23 字节", "在压缩结果前面加上 BP4", "42 50 是 BP；04 表示格式版本 4。", "格式头 + 压缩结果 · 23 字节", tuple(hex_rows(MESSAGE)), "格式头在 XOR 之前加入；接下来会与压缩数据一起参与混淆。"),
    Stage("XOR 混淆", "23 字节", "用固定规则逐字节变换", "掩码起始 fd f9 78；42 50 04 变为 bf a9 7c。", "XOR 后 · 23 字节", tuple(hex_rows(WIRE)), "掩码由 xorshift32 生成。长度不变，再 XOR 同一掩码即可还原。"),
    Stage("转 Base64url", "31 个字符", "把二进制换成可复制的文字", "输入：混淆后的 23 字节；去掉末尾补位等号。", "最终卡组码 · 31 个字符", (CODE,), "前三字节 bf a9 7c 转为 v6l8。这个固定前缀来自格式头和固定掩码。", "code"),
]

DECODING = [
    Stage("拿到卡组码", "31 个字符", "从这一串分享码开始", "同一个例子：角色 30134，只有一张普通卡。", "待解码的卡组码", (CODE,), "下面逐层恢复字节和字段；全过程在本机完成。", "code"),
    Stage("解 Base64url", "23 字节", "先把文字还原成二进制", "按长度补回 =，再做 Base64url 解码。", "恢复的混淆数据 · 23 字节", tuple(hex_rows(WIRE)), "此时还没有撤销 XOR，开头是 bf a9 7c，还读不到 BP 格式头。"),
    Stage("撤销 XOR", "23 字节", "重新生成同一串掩码", "bf a9 7c XOR fd f9 78，恢复 42 50 04。", "恢复的完整消息 · 23 字节", tuple(hex_rows(MESSAGE)), "XOR 两次同一掩码会恢复原数据；前三字节现在能读出 BP 和版本 4。"),
    Stage("检查格式头", "取出 20 字节", "确认 BP4，再取出压缩部分", "检查 42 50 04，移除这 3 字节头部。", "等待解压的数据 · 20 字节", tuple(hex_rows(COMPRESSED)), "格式头负责说明读取规则；不支持的版本会明确报错。"),
    Stage("DEFLATE 解压", "18 字节", "还原原始卡组记录", "对这 20 字节执行 raw DEFLATE 解压。", "解压后的卡组记录 · 18 字节", tuple(hex_rows(PAYLOAD)), "本地新码使用自包含压缩流；原站码可能引用预置字典，未知引用会报错。"),
    Stage("读取字段", "恢复构筑", "按字段顺序读回角色和卡牌", "读出角色、数量、状态、ID 长度和卡牌 ID。", "还原成功", ("角色：30134", "卡牌：c_30134_srt1", "数量：1 张", "移除：否　复制：否"), "这正是编码前的单卡构筑。读取结束还要确认没有多余或缺失的数据。", "text"),
]


def rail(draw, stages, current, move=None):
    x, y, width, height, step = 48, 188, 318, 78, 111
    cx = x + 30
    for index in range(5):
        sy = y + index * step + height
        ey = y + (index + 1) * step
        color = BLUE if index < current else LINE
        draw.line((cx, sy + 3, cx, ey - 7), fill=color, width=4)
        draw.polygon(((cx - 6, ey - 12), (cx + 6, ey - 12), (cx, ey - 4)), fill=color)
    if move:
        source, fraction = move
        sy = y + source * step + height + 3
        ey = y + (source + 1) * step - 7
        cy = sy + (ey - sy) * fraction
        draw.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), fill=PURPLE)
    for index, stage in enumerate(stages):
        yy = y + index * step
        active = index == current
        fill = TINT if active else DONE if index < current else "#ffffff"
        edge = BLUE if active else "#c7d2fe" if index < current else LINE
        draw.rounded_rectangle((x, yy, x + width, yy + height), 12, fill=fill, outline=edge, width=3 if active else 2)
        draw.ellipse((x + 15, yy + 22, x + 45, yy + 52), fill=BLUE if index <= current else "#94a3b8")
        draw.text((x + 24, yy + 20), str(index + 1), fill="#ffffff", font=font(22, True))
        draw.text((x + 61, yy + 7), stage.label, fill=BLUE if active else INK, font=font(28, active))
        draw.text((x + 61, yy + 43), stage.badge, fill=MUTED, font=font(24))


def render(stages, current, decoding=False, move=None):
    image = Image.new("RGB", (W, H), "#ffffff")
    draw = ImageDraw.Draw(image)
    direction = "解码" if decoding else "编码"
    draw.rounded_rectangle((48, 35, 154, 75), 8, fill=TINT)
    draw.text((67, 38), "BP4 示例", fill=BLUE, font=font(24, True))
    draw.text((48, 91), f"{'从卡组码还原构筑' if decoding else '从一张卡生成卡组码'}", fill=INK, font=font(42, True))
    draw.text((870, 107), f"{direction} · {current + 1} / 6", fill=MUTED, font=font(27))
    draw.line((48, 159, W - 48, 159), fill=LINE, width=2)
    rail(draw, stages, current, move)
    stage = stages[current]
    x, y, pw, ph = 410, 188, 742, 633
    draw.rounded_rectangle((x, y, x + pw, y + ph), 14, fill=SOFT, outline=LINE, width=2)
    para(draw, stage.title, (x + 28, y + 23), pw - 56, size=31, bold=True)
    para(draw, stage.input, (x + 28, y + 88), pw - 56, size=25, fill=MUTED)
    draw.line((x + 28, y + 183, x + pw - 28, y + 183), fill=LINE, width=2)
    draw.text((x + 28, y + 207), stage.output_label, fill=BLUE, font=font(27, True))
    cy = y + 265
    for index, row in enumerate(stage.output):
        if stage.kind == "text":
            draw.text((x + 30, cy), row, fill=INK, font=font(29))
            cy += 57
        elif stage.kind == "code":
            draw.rounded_rectangle((x + 24, cy - 12, x + pw - 24, cy + 60), 9, fill="#ffffff", outline="#bfdbfe", width=2)
            draw.text((x + 38, cy + 5), row, fill=PURPLE, font=font(29, mono=True))
            cy += 90
        else:
            draw.text((x + 30, cy), row, fill=PURPLE if current in (3, 4) else INK, font=font(28, mono=True))
            cy += 51
    note_top = y + 487
    draw.line((x + 28, note_top - 9, x + pw - 28, note_top - 9), fill=LINE, width=2)
    para(draw, stage.note, (x + 28, note_top + 10), pw - 56, size=24, fill=MUTED, gap=10)
    # A progressively extending track reinforces that each stage consumes the previous result.
    track_x, track_y, track_width = 410, 859, 742
    draw.rounded_rectangle((track_x, track_y, track_x + track_width, track_y + 8), 4, fill="#e2e8f0")
    draw.rounded_rectangle((track_x, track_y, track_x + track_width * (current + 1) / 6, track_y + 8), 4, fill=BLUE)
    draw.text((48, 915), "同一份真实单卡数据，逐步展示每一层的输入与输出。", fill=MUTED, font=font(25))
    draw.text((48, 955), "十六进制每两个字符代表一个字节；动画会循环播放。", fill=MUTED, font=font(24))
    return image


def save_animation(name, stages, decoding=False):
    frames = []
    durations = []
    for current in range(len(stages)):
        frames.append(render(stages, current, decoding))
        durations.append(2400 if current in (0, len(stages) - 1) else 1800)
        if current < len(stages) - 1:
            for fraction in (0.2, 0.4, 0.6, 0.8):
                frames.append(render(stages, current, decoding, (current, fraction)))
                durations.append(90)
    # Use one palette for every frame so fixed text and pale backgrounds remain stable.
    palette = frames[-1].quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    path = OUT / f"{name}.gif"
    indexed[0].save(path, save_all=True, append_images=indexed[1:], duration=durations, loop=0, disposal=2, optimize=True)
    frames[-1].save(OUT / f"{name}.png")
    with Image.open(path) as image:
        total = 0
        for index in range(image.n_frames):
            image.seek(index)
            total += image.info["duration"]
        assert image.size == (W, H)
        assert image.info.get("loop") == 0
        assert 10_000 <= total <= 18_000
        assert path.stat().st_size < 5_000_000
        print(f"{path.name}: {image.n_frames} frames; {total / 1000:.2f}s; {image.size}; {path.stat().st_size} bytes; infinite loop")


def check_constants():
    import base64
    import zlib
    assert len(bytes.fromhex(PAYLOAD)) == 18
    assert len(bytes.fromhex(COMPRESSED)) == 20
    assert len(bytes.fromhex(MESSAGE)) == 23
    assert len(bytes.fromhex(WIRE)) == 23
    assert len(CODE) == 31
    assert zlib.decompress(bytes.fromhex(COMPRESSED), wbits=-15) == bytes.fromhex(PAYLOAD)
    assert base64.urlsafe_b64encode(bytes.fromhex(WIRE)).decode().rstrip("=") == CODE
    state = 0x870FCD0A
    original = bytearray(bytes.fromhex(WIRE))
    for offset in range(0, len(original), 4):
        state ^= (state << 13) & 0xFFFFFFFF
        state ^= state >> 17
        state ^= (state << 5) & 0xFFFFFFFF
        for index, value in enumerate(state.to_bytes(4, "little")[:len(original) - offset]):
            original[offset + index] ^= value
    assert original == bytes.fromhex(MESSAGE)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    check_constants()
    save_animation("07-encoding", ENCODING)
    save_animation("08-decoding", DECODING, decoding=True)
