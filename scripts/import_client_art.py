"""Copy client card/portrait textures into the demo as standalone PNG assets.

Build-time only: pip install Pillow texture2ddecoder zstandard lz4 opencc-python-reimplemented
Reads SSRA v4 + SCT2; never modifies the installed client.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

from PIL import Image
import texture2ddecoder
import zstandard
import lz4.block

from client_tables import table as read_table, localized_text
from card_text_values import TextValues


class ClientResources:
    def __init__(self, root: Path):
        self.root = root
        data = (root / "manifest.ssra").read_bytes()
        magic, version, self.build, chunk_count, file_count, _ = struct.unpack_from("<4sIIIII", data)
        if magic != b"SSRA" or version != 4:
            raise ValueError("Expected the client's SSRA v4 resource manifest")
        pool_at, pool_size, chunk_at, file_at = struct.unpack_from("<QQQQ", data, 24)
        pool = data[pool_at:pool_at + pool_size]
        chunk_names = pool.split(b"\0")[:chunk_count]
        self.chunks: dict[int, list[tuple[int, int, Path]]] = {}
        for i, raw in enumerate(chunk_names):
            _, group, _, size, _, _ = struct.unpack_from("<IHHQQQ", data, chunk_at + i * 32)
            group_chunks = self.chunks.setdefault(group, [])
            start = group_chunks[-1][1] if group_chunks else 0
            group_chunks.append((start, start + size, root / "chunks" / raw.decode()))
        self.files = {}
        for i in range(file_count):
            row = struct.unpack_from("<QQIIIIHHI", data, file_at + i * 40)
            at = row[5]
            name = pool[at:pool.find(b"\0", at)].decode()
            self.files[name] = row

    def read(self, name: str) -> bytes:
        _, offset, size, raw_size, _, _, compression, group, _ = self.files[name]
        if max(size, raw_size) > 64 * 1024 * 1024:
            raise ValueError(f"Unexpectedly large image: {name}")
        for start, end, path in self.chunks[group]:
            if start <= offset < end and offset + size <= end:
                with path.open("rb") as stream:
                    stream.seek(offset - start)
                    data = stream.read(size)
                if compression:
                    data = zstandard.ZstdDecompressor().decompress(data, max_output_size=raw_size)
                return data
        raise ValueError(f"Cannot locate resource {name}")


def decode_texture(data: bytes) -> Image.Image:
    if data[:4] != b"SCT2":
        raise ValueError("Expected an SCT2 texture")
    offset = struct.unpack_from("<I", data, 12)[0]
    fmt = struct.unpack_from("<I", data, 20)[0]
    width, height = struct.unpack_from("<HH", data, 24)
    payload = data[offset:]
    expected = ((width + 3) // 4) * ((height + 3) // 4) * 16
    if fmt in (40, 44, 47):
        block = {40: 4, 44: 6, 47: 8}[fmt]
        expected = ((width + block - 1) // block) * ((height + block - 1) // block) * 16
    elif 17 <= fmt <= 26 and fmt != 19:
        expected = width * height * 4
    if len(payload) < expected:
        if len(payload) < 8:
            raise ValueError("Truncated compressed texture")
        raw_size, compressed_size = struct.unpack_from("<II", payload)
        if not expected <= raw_size <= 64 * 1024 * 1024 or compressed_size > len(payload) - 8:
            raise ValueError("Invalid compressed texture sizes")
        payload = lz4.block.decompress(payload[8:8 + compressed_size], uncompressed_size=raw_size)
    payload = payload[:expected]
    if fmt in (40, 44, 47):
        block = {40: 4, 44: 6, 47: 8}[fmt]
        pixels = texture2ddecoder.decode_astc(payload, width, height, block, block)
        return Image.frombytes("RGBA", (width, height), pixels, "raw", "BGRA")
    if fmt == 19:
        pixels = texture2ddecoder.decode_etc2a8(payload, width, height)
        return Image.frombytes("RGBA", (width, height), pixels, "raw", "BGRA")
    if 17 <= fmt <= 26:
        return Image.frombytes("RGBA", (width, height), payload[:width * height * 4])
    raise ValueError(f"Unsupported image pixel format {fmt}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True, help="Previously extracted client card/text table JSON")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "demo/assets")
    args = parser.parse_args()
    source = json.loads(args.catalog.read_text(encoding="utf-8"))
    resources = ClientResources(args.game_root)
    # Complete status chains were not included in the earlier card-only extract.
    tables = source["related_tables"]
    for name in resources.files:
        if name.endswith("@cs.db") or (name.startswith("db/cs(") and name.endswith("@skill_eff.db")):
            rows = read_table(resources.read(name))
            tables[name] = {"source": name, "rows": {key: {"columns": row} for key, row in rows.items()}}
    text_values = TextValues(tables)
    local_text = localized_text(resources.read("text/zht/text.db"))
    from opencc import OpenCC
    simplify = OpenCC("t2s").convert
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    previous_path = output / "provenance.json"
    previous = json.loads(previous_path.read_text(encoding="utf-8")) if previous_path.is_file() else {}
    previous_files = {r["file"]: r["resource"] for r in previous.get("files", [])} if previous.get("build") == resources.build else {}
    cards = source["cards"]
    owners = sorted({m[1] for key in cards if (m := re.fullmatch(r"c_(\d+)_srt1", key))}, key=int)
    assets: dict[str, str] = {}
    provenance = []
    failures = []

    def export(name: str, kind: str, key: str, max_size=(420, 632)) -> str:
        if name in assets:
            return assets[name]
        if name not in resources.files:
            return ""
        relative = f"{kind}/{key}.png"
        try:
            print("IMAGE", name, flush=True)
            target = output / relative
            if target.is_file() and previous_files.get(relative) == name:
                with Image.open(target) as existing:
                    existing.verify()
                assets[name] = relative
                provenance.append({"resource": name, "file": relative, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
                return relative
            raw = resources.read(name)
            image = decode_texture(raw)
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            target.parent.mkdir(parents=True, exist_ok=True)
            image.save(target, optimize=True)
            assets[name] = relative
            provenance.append({"resource": name, "file": relative, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
            return relative
        except Exception as error:
            failures.append({"resource": name, "error": str(error)})
            return ""

    def base_id(key: str) -> str:
        parent = re.sub(r"_(?:rsp\d+|pot|lbk)(?:_.*)?$", "", key)
        return parent if parent in cards else key

    def image_name(key: str) -> str:
        raw = cards[key]["raw_columns"]
        skin = raw.get("card_skin_set", "none")
        if skin in ("none", ""):
            skin = raw.get("sct_name", "none")
        name = f"card_illustration/{skin}.sct"
        if name in resources.files:
            return name
        parent = base_id(key)
        return image_name(parent) if parent != key else ""

    catalog = {}
    for key, row in cards.items():
        raw = row["raw_columns"]
        owner_match = re.match(r"c_(\d+)_", key)
        owner = owner_match[1] if owner_match and owner_match[1] in owners else ""
        sort = raw.get("sort", "")
        group = "character" if owner else "memory" if sort == "SORT_MEMORY" else "neutral"
        art = image_name(key)
        path = export(art, "cards", Path(art).stem) if art else ""
        catalog[key] = {
            "id": key, "base_id": base_id(key), "owner": owner, "group": group,
            "name": row["name_zht"].replace("\u200b", "").strip(),
            "name_s": row["name"].replace("\u200b", "").strip(),
            "text": row["desc_outgame_zht"] or row["desc_zht"],
            "text_s": row["desc_outgame"] or row["desc"],
            "cost": raw.get("cost", "?"), "type": raw.get("card_category", "CARD_SKILL"),
            "rarity": raw.get("rarity", "RARITY_COMMON"), "sort": sort, "art": path,
            "talents": raw.get("talent", "[]"),
            "pickable": bool(path) and (bool(re.fullmatch(r"c_\d+_(srt|uni)[1-4]", key)) or (not owner and sort in ("SORT_NEUTRAL", "SORT_MEMORY", "SORT_DESIRE", "SORT_TABOO", "SORT_ETC"))),
        }
        display = catalog[key]
        display["values"], display["unresolved_values"] = text_values.parameters([display["text"], display["text_s"]], raw.get("link_skill_eff_id", "[]"))
        display["values_s"] = {key: simplify(value) for key, value in display["values"].items()}
    characters = []
    for owner in owners:
        char = source["characters"].get(owner, {})
        candidates = [f"face/character/face_character_popup_{owner}.sct", f"face/character/face_character_{owner}.sct", f"face/character/portrait_character_class_{owner}.sct"]
        art = next((n for n in candidates if n in resources.files), "")
        portrait = export(art, "characters", owner, (480, 320)) if art else ""
        characters.append({"id": owner, "name": char.get("name_zht", owner), "name_s": char.get("name", owner), "art": portrait})
    references = source["localized_references"]
    modifiers = []
    for key, row in source["related_tables"]["db/r_spark@r_spark.db"]["rows"].items():
        raw = row["columns"]
        ref = references.get(raw.get("description", ""), {})
        if not ref.get("zht"):
            continue
        if key.startswith(("add_r_spark_", "assault_r_spark_")):
            group = "divine"
        elif re.fullmatch(r"c\d+|c_\d+_\d+", key):
            group = "epiphany"
        else:
            continue
        modifiers.append({"id": key, "text": ref["zht"], "text_s": ref.get("zh_Hans", ref["zht"]), "group": group, "god": raw.get("god_type", ""),
                          "constraints": {k: raw[k] for k in ("target_card_cost_min", "target_card_cost_max", "target_card_category", "target_card_include_talent", "target_card_exclude_talent", "target_link_base_class_define_id") if k in raw}})
        modifier = modifiers[-1]
        modifier["values"], modifier["unresolved_values"] = text_values.parameters([modifier["text"], modifier["text_s"]], raw.get("add_link_skill_eff_id", "[]"))
        modifier["values_s"] = {key: simplify(value) for key, value in modifier["values"].items()}
    gods = {}
    for key, row in source["related_tables"]["db/r_spark_god_type_define@r_spark_god_type_define.db"]["rows"].items():
        name_key = row["columns"].get("name", "")
        name = local_text.get(name_key, local_text.get(name_key.lower(), key))
        gods[key] = {"name": name, "name_s": simplify(name)}
    display_refs = {}
    for item in [*catalog.values(), *modifiers]:
        for token in re.findall(r"\^([^\^]+)\^", item["text"]):
            if token.startswith("card@"): continue
            text = local_text.get(token) or local_text.get(f"tooltip@box_tooltip_title@{token.lower()}")
            if text: display_refs[token] = {"name": text, "name_s": simplify(text)}
    result = {"schema": 1, "source": "Installed international client (zht)", "build": resources.build,
              "characters": characters, "cards": catalog, "modifiers": modifiers, "gods": gods, "references": display_refs,
              "value_preview": "Client base coefficients; excludes equipment and live battle modifiers"}
    (output / "catalog.json").write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (output / "provenance.json").write_text(json.dumps({"build": resources.build, "files": provenance, "failures": failures}, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "NOTICE.txt").write_text("本目录插画、角色肖像与繁体文案提取自游戏客户端，按客户端资源名与卡牌 ID 对应。游戏美术与文案归原权利人所有，项目代码的 MIT 许可不涵盖这些资源。简体名称和文案为繁转简展示文本。运行 Demo 无需安装游戏或联网。\n", encoding="utf-8")
    print(json.dumps({"characters": len(characters), "cards": len(catalog), "pickable": sum(c["pickable"] for c in catalog.values()), "images": len(provenance), "failures": failures[:8]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
