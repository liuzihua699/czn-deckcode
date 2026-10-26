"""Build display parameters from client skill/status tables, without battle state.

Only numeric source fields are rendered as numbers. Runtime-only values receive
an explicit label; the resolver never invents a combat result or evaluates code.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re

TOKEN = re.compile(r"#([A-Za-z_][A-Za-z0-9_]*)#")


def ids(value: str) -> list[str]:
    return [v for v in value.strip("[]").split(",") if v and v != "none"]


class TextValues:
    def __init__(self, tables: dict):
        self.skills = {}
        self.statuses = {}
        for table in tables.values():
            if table["source"].endswith("@skill_eff.db"):
                self.skills.update({k: r["columns"] for k, r in table["rows"].items()})
            elif table["source"].endswith("@cs.db"):
                self.statuses.update({k: r["columns"] for k, r in table["rows"].items()})

    @staticmethod
    def number(value: str | None) -> str | None:
        if value is None: return None
        try:
            number = Decimal(value)
            if not number.is_finite(): return None
            return format(number.normalize(), "f")
        except InvalidOperation:
            return None

    def skill(self, links: list[str], index: str | int) -> dict:
        position = int(index)
        return self.skills.get(links[position], {}) if position < len(links) else {}

    def cs_links(self, skill: dict) -> list[str]:
        links = ids(skill.get("link_cs_id", "[]"))
        status = self.statuses.get(links[0], {}) if links else {}
        return ids(status.get("link_skill_eff_id", "[]"))

    def resolve(self, token: str, links: list[str]) -> str | None:
        # Optional live multiplier suffixes are absent in an out-of-battle preview.
        if token.startswith(("n_result_vt_mul_", "n_result_vt_ecv_mul_")): return ""
        token = re.sub(r"^(?:(?:n_|nrd_|basic_|final_))+", "", token)
        match = re.fullmatch(r"cs_tv_max_(.+)", token)
        if match:
            return self.number(self.statuses.get(match[1], {}).get("overlay_value_max"))
        match = re.fullmatch(r"dmg_attr_leech_(shield|hp)_(\d+)", token)
        if match:
            attributes = self.skill(links, match[2]).get("eff_attr", "[]")
            amount = re.search(r"DMG_ATTR_LEECH_" + match[1].upper() + r"_PCT_(\d+)", attributes)
            return amount[1] if amount else None
        if re.fullmatch(r"dmg_attr_class_\d+", token): return "職業效果："
        match = re.fullmatch(r"result_coeff_ecdv([01])_(\d+)", token)
        if match:
            value = self.number(self.skill(links, match[2]).get(f"eff_condition_value_{match[1]}"))
            return value + "%" if value is not None else None
        match = re.fullmatch(r"cs_(.+)_(\d+)_(\d+)", token)
        if match:
            field, root, child = match.groups()
            return self.resolve(f"{field}_{child}", self.cs_links(self.skill(links, root)))
        match = re.fullmatch(r"during_(.+)_(\d+)_(\d+)", token)
        if match:
            field, root, branch = match.groups()
            parent = self.skill(links, root)
            following = parent.get(f"during_eff_{branch}_link_skill_eff_id", "none")
            return self.resolve("cs_ev_0_0" if field == "cs_ev" else f"{field}_0", ids(following))
        match = re.fullmatch(r"skill_eff_ev_(.+)", token)
        if match:
            return self.number(self.skills.get(match[1], {}).get("eff_value"))
        match = re.fullmatch(r"(?:result_)?(coeff_pct_off_ev|coeff_ev|damage_pct_off|damage_noecv|damage|ev|ecv|ectc|value|run_pct|ecdv[01]|ecdcv[01])_(\d+)", token)
        if match:
            field, index = match.groups()
            skill = self.skill(links, index)
            if not skill: return None
            column = {"ecv": "eff_count_value", "ectc": "eff_card_target_count", "run_pct": "run_pct",
                      "ecdv0": "eff_condition_value_0", "ecdv1": "eff_condition_value_1",
                      "ecdcv0": "eff_condition_count_value_0", "ecdcv1": "eff_condition_count_value_1"}.get(field, "eff_value")
            number = self.number(skill.get(column))
            if number is None: return None
            if field == "ectc" and number == "-1": return "全部"
            if field in ("damage", "damage_noecv", "coeff_ev"): return number + "%"
            return number
        match = re.fullmatch(r"condition_(count_)?value_stack_(\d+)_(\d+)", token)
        if match:
            field = "eff_condition_count_value_" if match[1] else "eff_condition_value_"
            return self.number(self.skill(links, match[2]).get(field + match[3]))
        return None

    def parameters(self, texts: list[str], links: str) -> tuple[dict, list]:
        values, unresolved = {}, []
        linked = ids(links)
        tokens = sorted({m[1] for text in texts for m in TOKEN.finditer(text)})
        for token in tokens:
            value = self.resolve(token, linked)
            if value is None:
                unresolved.append(token)
            else:
                values[token] = value
        return values, unresolved
