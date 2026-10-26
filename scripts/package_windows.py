"""Package a verified EXE as a portable ZIP; never includes user configurations."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_NAME = "CZNDeckcode-windows-x64.zip"
PREFIX = "CZNDeckcode/"
INSTRUCTIONS = """CZN 卡组工作台 0.1.0a2

解压整个文件夹后双击 CZNDeckcode.exe，无需安装 Python 或游戏。
编解码、图片与数值表均在本地使用，不调用外部编解码 API。
首次启动会解压内嵌运行库和插画，请稍候。

1. 左侧选择角色；中间展示当前卡组，右侧提供编辑功能与可搜索卡牌库。
2. 01/02/03 切换同角色预设，＋ 新建；可重命名、复制、删除预设。
3. 在右侧搜索卡牌，点击 ＋ 加入。选择中间卡牌后可移除、恢复、复制及设置灵光。
4. 独特灵光展示分支图卡；神闪与一般灵光分别使用对应本地效果库。
5. 已移除记录默认隐藏，只有手动勾选「显示已移除」后才显示。
   隐藏不会删除记录，导出仍保留移除和复制状态。
6. 「从卡组码导入」支持新建预设或覆盖当前同角色预设。
   已验证 7 条实际官方码，含记忆卡；未知版本或字段会报错，不会联网回退。
7. 「保存预设」或 Ctrl+S 保存，正常关闭时也会保存。
   配置位于程序旁 user_data/decks.json；更新时保留原 user_data 文件夹。
8. 「导出 / 分享」生成卡组码，JSON 页提供可选备份工具。

已包含 39 个角色、817 张可选卡牌和 855 张本地插画／头像。
繁体文案来自客户端；简体是转换展示文本。
固定数量和基础倍率来自本地技能／状态表，未计角色、装备和战斗加成。
少量尚未求值的字段会明确标注；游戏本身的 X 费用机制仍显示 X。
构筑限制与未来游戏版本的兼容性仍需后续完善。

附「离线自测结果.json」「离线说明.md」「素材来源说明.txt」及许可证。
"""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package(exe: Path, report_path: Path, output: Path, additional: list[Path]) -> dict:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not (report.get("ok") and report.get("frozen") and report.get("network_blocked")
            and report.get("official_codes") == 7 and report.get("network_events") == []):
        raise ValueError("EXE 必须先通过禁用网络条件下的 7 条官方码自测")
    output.mkdir(parents=True, exist_ok=True)
    target = output / "CZNDeckcode.exe"
    if exe.resolve() != target.resolve(): shutil.copy2(exe, target)
    digest = sha256(target)
    archive = output / ARCHIVE_NAME
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        bundle.write(target, PREFIX + target.name, compress_type=zipfile.ZIP_STORED)
        bundle.writestr(PREFIX + "使用说明.txt", INSTRUCTIONS.encode("utf-8-sig"))
        bundle.writestr(PREFIX + "SHA256SUMS.txt", f"{digest}  {target.name}\n")
        bundle.write(report_path, PREFIX + "离线自测结果.json")
        bundle.write(ROOT / "docs/offline.md", PREFIX + "离线说明.md")
        bundle.write(ROOT / "src/czn_deckcode/assets/NOTICE.txt", PREFIX + "素材来源说明.txt")
        bundle.write(ROOT / "LICENSE", PREFIX + "licenses/MIT.txt")
        for license_path in (ROOT / "licenses").glob("*.txt"):
            bundle.write(license_path, PREFIX + "licenses/" + license_path.name)
        pillow = importlib.metadata.distribution("Pillow")
        for entry in pillow.files or []:
            if str(entry).replace("\\", "/").endswith("licenses/LICENSE"):
                bundle.write(pillow.locate_file(entry), PREFIX + "licenses/Pillow.txt")
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None: raise ValueError("ZIP 完整性校验失败")
        if any("user_data" in name or name.endswith(".py") for name in bundle.namelist()):
            raise ValueError("ZIP 不应包含个人配置或开发源码")
        if hashlib.sha256(bundle.read(PREFIX + target.name)).hexdigest() != digest:
            raise ValueError("ZIP 内的 EXE 校验失败")
    files = [target, archive]
    for path in additional:
        destination = output / path.name
        if path.resolve() != destination.resolve(): shutil.copy2(path, destination)
        files.append(destination)
    lines = [f"{sha256(path)}  {path.name}" for path in files]
    (output / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="ascii")
    return {"exe": str(target), "zip": str(archive), "files": [p.name for p in files]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, default=ROOT / "dist/CZNDeckcode.exe")
    parser.add_argument("--self-test", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--additional", type=Path, action="append", default=[])
    args = parser.parse_args()
    print(json.dumps(package(args.exe, args.self_test, args.output_dir, args.additional), ensure_ascii=False))
