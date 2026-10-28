"""Portable, atomic local preset storage, independent of Tk and the codec."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
from uuid import uuid4

from czn_deckcode.models import Deck

USER_ADDED_FIELD = "_userAdded"


def codec_card_rows(cards: list[dict]) -> list[dict]:
    return [
        {key: value for key, value in card.items() if key != USER_ADDED_FIELD}
        if isinstance(card, dict) else card
        for card in cards
    ]


def is_user_added_card(cards: list[dict], index: int | None) -> bool:
    return (
        index is not None
        and 0 <= index < len(cards)
        and cards[index].get(USER_ADDED_FIELD) is True
    )


def remove_user_added_card(cards: list[dict], index: int | None) -> list[dict] | None:
    if not is_user_added_card(cards, index):
        return None
    result = copy.deepcopy(cards)
    del result[index]
    return result


def default_store_path() -> Path:
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
    return base / "user_data" / "decks.json"


class PresetStore:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else default_store_path()
        self.data = {"schema": 1, "selected_character": "30134", "language": "繁體中文", "characters": {}}
        if self.path.is_file():
            value = json.loads(self.path.read_text(encoding="utf-8"))
            if value.get("schema") != 1 or not isinstance(value.get("characters"), dict):
                raise ValueError("不支持的预设文件格式")
            for owner, group in value["characters"].items():
                ids = set()
                if not isinstance(group.get("presets"), list) or not group["presets"]:
                    raise ValueError("预设列表为空")
                for preset in group["presets"]:
                    if preset["id"] in ids or not isinstance(preset["name"], str):
                        raise ValueError("预设标识重复或名称有误")
                    ids.add(preset["id"])
                    for card in preset["cards"]:
                        if isinstance(card, dict) and USER_ADDED_FIELD in card and type(card[USER_ADDED_FIELD]) is not bool:
                            raise ValueError("用户新增卡牌标记有误")
                    Deck.from_dict({"charId": owner, "cards": codec_card_rows(preset["cards"])})
                if group["active"] not in ids:
                    raise ValueError("当前预设不存在")
            self.data = value

    def ensure(self, owner: str, starter: list[dict]) -> dict:
        groups = self.data["characters"]
        if owner not in groups:
            presets = [self.make(f"{i}号预设", starter) for i in range(1, 4)]
            groups[owner] = {"active": presets[0]["id"], "presets": presets}
        return groups[owner]

    @staticmethod
    def make(name: str, cards: list[dict]) -> dict:
        return {"id": uuid4().hex, "name": name, "cards": copy.deepcopy(cards)}

    def write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.path)
