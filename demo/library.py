"""Local client-derived display catalog. The codec itself does not use it."""
from __future__ import annotations

from collections import OrderedDict
import json
import os
from pathlib import Path
import re

ASSET_ROOT = Path(__file__).resolve().parent / "assets"
TYPE_NAMES = {"CARD_ATK": "攻擊", "CARD_SKILL": "技能", "CARD_POWER": "強化", "CARD_HEX": "詛咒", "CARD_ABNORMAL": "狀態"}
TYPE_NAMES_S = {"CARD_ATK": "攻击", "CARD_SKILL": "技能", "CARD_POWER": "强化", "CARD_HEX": "诅咒", "CARD_ABNORMAL": "状态"}


class CardLibrary:
    def __init__(self, root: Path = ASSET_ROOT):
        self.root = root
        data = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
        self.characters = data["characters"]
        self.cards = data["cards"]
        self.modifiers = data["modifiers"]
        self.gods = data.get("gods", {})
        self.references = data.get("references", {})
        self.modifier_by_id = {m["id"]: m for m in self.modifiers}
        self.build = data["build"]

    @staticmethod
    def text(item: dict, field: str = "name", language: str = "繁體中文") -> str:
        return item.get(field + "_s", item.get(field, "")) if language == "简体中文" else item.get(field, "")

    def character(self, owner: str) -> dict:
        return next((c for c in self.characters if c["id"] == owner), {"id": owner, "name": "未選擇角色"})

    def card(self, row: dict | str) -> dict:
        key = row if isinstance(row, str) else row.get("variantCardId") or row.get("cardId", "")
        card = self.cards.get(key)
        if card is None and isinstance(row, dict):
            card = self.cards.get(row.get("cardId", ""))
        return card or {"id": key, "base_id": key, "name": "未知卡牌", "name_s": "未知卡牌", "cost": "?", "type": "CARD_SKILL", "art": "", "text": ""}

    def available(self, owner: str, group: str, search: str = "", kind: str = "") -> list[dict]:
        search = search.casefold().strip()
        result = [c for c in self.cards.values() if c["pickable"] and c["group"] == group
                  and (group != "character" or c["owner"] == owner)
                  and (not kind or c["type"] == kind)
                  and (not search or any(search in c.get(key, "").casefold() for key in ("name", "name_s", "id", "text", "text_s")))]
        return sorted(result, key=lambda c: (c["id"].split("_")[-1] if group == "character" else c["name"], c["id"]))

    def variants(self, card: dict) -> list[dict]:
        base = card["base_id"]
        return sorted((c for c in self.cards.values() if c["id"] == base or re.fullmatch(re.escape(base) + r"_(?:rsp\d+|pot|lbk)", c["id"])), key=lambda c: (c["id"] != base, c["id"]))

    def description(self, item: dict, language: str) -> str:
        text = self.text(item, "text", language)
        def reference(match):
            key = match[1]
            if key.startswith("card@"):
                return self.text(self.card(key.split("@")[-1]), language=language)
            if key in self.references:
                return self.text(self.references[key], language=language)
            return key.split("@")[-1] if "@" not in key else ""
        text = re.sub(r"\^([^\^]+)\^", reference, text)
        values = item.get("values_s", item.get("values", {})) if language == "简体中文" else item.get("values", {})
        text = re.sub(r"#([A-Za-z_][A-Za-z0-9_]*)#", lambda m: values.get(m[1], "未求值"), text)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
        text = re.sub(r"\[(?:/?[a-z]*fc|/?cc|/)\]", "", text)
        return re.sub(r"<[^>]+>", "", text).replace("$", "").strip()

    def starter(self, owner: str) -> list[dict]:
        return [{"cardId": f"c_{owner}_{prefix}{i}", "removed": False, "duplicate": False}
                for prefix in ("srt", "uni") for i in range(1, 5) if f"c_{owner}_{prefix}{i}" in self.cards]

    def user_added_flags(self, rows: list[dict], owner: str) -> list[bool]:
        starter_ids = {self.card(row)["base_id"] for row in self.starter(owner)}
        seen = set()
        flags = []
        for row in rows:
            item = self.card(row)
            base_id = item.get("base_id", row.get("cardId", ""))
            group = item.get("group")
            is_added = (
                row.get("_userAdded") is True
                or row.get("duplicate") is True
                or group in {"memory", "neutral"}
                or (group == "character" and base_id not in starter_ids)
                or base_id in seen
            )
            flags.append(is_added)
            seen.add(base_id)
        return flags

    def unique_variants(self, row: dict) -> list[dict]:
        return [c for c in self.variants(self.card(row)) if re.search(r"_rsp\d+$", c["id"])]

    def effects(self, row: dict, language: str) -> str:
        parts = [self.description(self.card(row), language)]
        for field in ("epiphanyId", "divineId"):
            key = row.get(field)
            if key:
                item = self.modifier_by_id.get(key)
                parts.append(self.description(item, language) if item else "未收录的灵光效果")
        return "\n".join(p for p in parts if p)

    def modifier_choices(self, row: dict, group: str) -> list[dict]:
        """Use the client's cost, category and talent constraints for display filtering.

        Class/event/unlock restrictions are not a complete game rules simulation.
        """
        item = self.card(row)
        try:
            cost = int(item.get("cost", "0"))
        except (TypeError, ValueError):
            return []
        def values(raw):
            return {v for v in raw.strip("[]").split(",") if v}
        talents = values(item.get("talents", "[]"))
        result = []
        for modifier in self.modifiers:
            if modifier["group"] != group:
                continue
            c = modifier.get("constraints", {})
            if not int(c.get("target_card_cost_min", -1)) <= cost <= int(c.get("target_card_cost_max", 99)):
                continue
            categories = values(c.get("target_card_category", "[]"))
            included = values(c.get("target_card_include_talent", "[]"))
            excluded = values(c.get("target_card_exclude_talent", "[]"))
            if categories and item["type"] not in categories:
                continue
            if included and not talents.intersection(included) or talents.intersection(excluded):
                continue
            result.append(modifier)
        return result


class CardImages:
    """Root-owned image cache; all artwork is loaded from bundled local PNGs."""
    def __init__(self, root, library: CardLibrary):
        from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageTk
        self.Image, self.Draw, self.Font, self.Ops, self.ImageTk = Image, ImageDraw, ImageFont, ImageOps, ImageTk
        self.root, self.library = root, library
        self.cache = OrderedDict()
        self.font_path = next((str(p) for p in [Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/msyh.ttc", Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")] if p.is_file()), "")

    def font(self, size):
        return self.Font.truetype(self.font_path, size) if self.font_path else self.Font.load_default(size=size)

    def _photo(self, key, create):
        if key not in self.cache:
            self.cache[key] = self.ImageTk.PhotoImage(create(), master=self.root)
            if len(self.cache) > 180:
                self.cache.popitem(last=False)
        self.cache.move_to_end(key)
        return self.cache[key]

    def portrait(self, character: dict, size=(60, 48)):
        def create():
            path = self.library.root / character.get("art", "")
            image = self.Image.open(path).convert("RGBA") if path.is_file() else self.Image.new("RGBA", size, "#2c3349")
            return self.Ops.fit(image, size, centering=(.5, .30))
        return self._photo(("portrait", character["id"], size), create)

    def card(self, row: dict | str, size=(146, 218), language="繁體中文", full=False):
        item = self.library.card(row)
        removed = isinstance(row, dict) and row.get("removed", False)
        duplicate = isinstance(row, dict) and row.get("duplicate", False)
        def create():
            width, height = size
            path = self.library.root / item.get("art", "")
            image = self.Image.open(path).convert("RGBA") if path.is_file() else self.Image.new("RGBA", size, "#252c40")
            image = self.Ops.fit(image, size, centering=(.5, .43))
            overlay = self.Image.new("RGBA", size)
            draw = self.Draw.Draw(overlay)
            for y in range(height):
                alpha = int(225 * max(0, (y / height - .43) / .57))
                draw.line((0, y, width, y), fill=(8, 13, 27, alpha))
            draw.rectangle((0, 0, width, int(height * .19)), fill=(8, 13, 27, 105))
            image = self.Image.alpha_composite(image, overlay)
            draw = self.Draw.Draw(image)
            scale = width / 146
            border = "#cba66e" if "RARE" in item.get("rarity", "") else "#87a6d6"
            draw.rounded_rectangle((1, 1, width - 2, height - 2), radius=int(8 * scale), outline=border, width=max(1, round(2 * scale)))
            cost = str(item.get("cost", "?"))
            if cost == "-1": cost = "X"
            draw.rounded_rectangle((5 * scale, 5 * scale, 31 * scale, 34 * scale), radius=6 * scale, fill="#193d66")
            draw.text((18 * scale, 17 * scale), cost, font=self.font(round(19 * scale)), fill="#9ce5ff", anchor="mm")
            types = TYPE_NAMES_S if language == "简体中文" else TYPE_NAMES
            draw.text((38 * scale, 10 * scale), types.get(item["type"], "特殊"), font=self.font(round(10 * scale)), fill="white")
            name = self.library.text(item, language=language)
            font_size = round(15 * scale)
            while self.Draw.Draw(image).textlength(name, font=self.font(font_size)) > width - 15 * scale and font_size > 9 * scale:
                font_size -= 1
            if full:
                # Match the client's card face: title at top, effects on the art.
                top_font = self.font(max(11, round(12 * scale)))
                while draw.textlength(name, font=top_font) > width - 42 * scale and top_font.size > 9:
                    top_font = self.font(top_font.size - 1)
                draw.text((36 * scale, 28 * scale), name, font=top_font, fill="#d9f6ff", stroke_width=1, stroke_fill="#15334e")
                row_value = row if isinstance(row, dict) else {"cardId": row}
                effect = self.library.effects(row_value, language)
                def wrap(text, font):
                    lines = []
                    for paragraph in text.splitlines():
                        line = ""
                        for char in paragraph:
                            if line and draw.textlength(line + char, font=font) > width - 16 * scale:
                                lines.append(line); line = ""
                            line += char
                        lines.append(line)
                    return lines
                available_height = height * .51
                for points in range(max(11, round(11 * scale)), 8, -1):
                    font = self.font(points)
                    lines = wrap(effect, font)
                    line_height = points + max(3, round(2 * scale))
                    if len(lines) * line_height <= available_height:
                        break
                top = max(height * .39, height - 14 * scale - len(lines) * line_height)
                draw.rounded_rectangle((4 * scale, top - 6, width - 4 * scale, height - 7 * scale), radius=5, fill=(8, 15, 24, 150))
                for i, line in enumerate(lines):
                    draw.text((width / 2, top + i * line_height), line, font=font, anchor="mt", fill="#fffde6", stroke_width=1, stroke_fill="#20282d")
                badges = [label for flag, label in ((duplicate, "已复制"), (row_value.get("divineId"), "神闪"), (row_value.get("epiphanyId"), "一般灵光")) if flag]
                if badges:
                    draw.text((width / 2, 50 * scale), " / ".join(badges), anchor="mt", font=self.font(round(10 * scale)), fill="#ffd98d", stroke_width=1, stroke_fill="#29251d")
            else:
                draw.text((8 * scale, height - 37 * scale), name, font=self.font(font_size), fill="#fff6c8")
                draw.text((8 * scale, height - 17 * scale), "已移除" if removed else "複製" if duplicate else "", font=self.font(round(10 * scale)), fill="#e1d8ff")
            if removed:
                shade = self.Image.new("RGBA", size, (20, 24, 35, 130))
                image = self.Image.alpha_composite(image, shade)
            return image
        modifiers = tuple(row.get(k, "") for k in ("epiphanyId", "divineId", "god")) if isinstance(row, dict) else ()
        return self._photo(("card", item["id"], size, language, removed, duplicate, full, modifiers), create)
