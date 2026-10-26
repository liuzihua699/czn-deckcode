"""Native Tkinter desktop workbench for the offline deck-code SDK."""

from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, font as tkfont, scrolledtext, ttk
from typing import Callable, TypeVar

from czn_deckcode import Card, Deck, decode, encode
from .visual_ui import VisualWorkbench, BG, PANEL, INPUT, TEXT, MUTED, ACCENT
from .presets import PresetStore


EXAMPLE_CODE = "v6l8cOjiNr8NyAd5bz8N5Gb4BacatRLcP_gTJk6Sy-IpI4UudHIDQRTERzqzgUXu"
_OPTIONAL_FIELDS = ("variantCardId", "epiphanyId", "divineId", "god")
_T = TypeVar("_T")
_BG, _PANEL, _INPUT, _TEXT, _MUTED, _ACCENT = BG, PANEL, INPUT, TEXT, MUTED, ACCENT


def example_deck() -> Deck:
    cards = []
    for name in ("srt1", "srt2", "srt3", "srt4", "uni1", "uni2", "uni3", "uni4"):
        card_id = f"c_30134_{name}"
        cards.append(Card(card_id, variant_card_id=f"{card_id}_pot" if name in ("srt1", "srt2") else None))
    return Deck("30134", tuple(cards))


class DeckApplication(VisualWorkbench):
    """Desktop view and editable deck state, backed directly by the SDK."""

    def __init__(self, root: tk.Tk, store_path: Path | None = None):
        self.root = root
        self.store = PresetStore(store_path)
        self._cards: list[dict] = []
        self._selected: int | None = None
        self._changing = False
        self.char_id_var = tk.StringVar(root)
        self.status_var = tk.StringVar(root)
        self.count_var = tk.StringVar(root)
        self.card_vars: dict[str, tk.Variable] = {
            "cardId": tk.StringVar(root),
            "removed": tk.BooleanVar(root),
            "duplicate": tk.BooleanVar(root),
            **{field: tk.StringVar(root) for field in _OPTIONAL_FIELDS},
        }
        self._style()
        self._build()
        self.char_id_var.trace_add("write", lambda *_: self._sync_json())
        for variable in self.card_vars.values():
            variable.trace_add("write", lambda *_: self._update_selected())
        owner = self.store.data.get("selected_character", "30134")
        first_use = not self.store.data["characters"]
        group = self.store.ensure(owner, self.library.starter(owner))
        if first_use and owner == "30134":
            group["presets"][0]["cards"] = [c.to_dict() for c in example_deck().cards]
        self._activate(owner, group["active"])
        if first_use:
            self._set_text(self.code_text, EXAMPLE_CODE)
        self._status("选择中间的卡牌，再用右侧编辑功能；Ctrl+S 保存，关闭时自动保存。")

    def _style(self) -> None:
        self.root.title("CZN · 卡组工作台")
        self.root.geometry("1040x740")
        self.root.minsize(900, 650)
        self.root.configure(background=_BG)
        self.root.resizable(True, True)
        families = set(tkfont.families(self.root))
        family = next((name for name in ("Microsoft YaHei UI", "Microsoft YaHei", "Noto Sans CJK SC") if name in families), "TkDefaultFont")
        if family != "TkDefaultFont":
            tkfont.nametofont("TkDefaultFont").configure(family=family, size=10)
        self.font_family = family
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background=_PANEL, foreground=_TEXT, bordercolor="#d5d9de", lightcolor="#ffffff", darkcolor="#d5d9de", troughcolor="#e8ebee")
        style.configure("App.TFrame", background=_BG)
        style.configure("App.TLabel", background=_BG)
        style.configure("Title.TLabel", font=(family, 18, "bold"), background=_BG)
        style.configure("Muted.TLabel", foreground=_MUTED)
        style.configure("AppMuted.TLabel", background=_BG, foreground=_MUTED)
        style.configure("TLabelframe", borderwidth=1, relief="solid")
        style.configure("TLabelframe.Label", foreground=_TEXT, font=(family, 10, "bold"))
        style.configure("TEntry", fieldbackground=_INPUT, foreground=_TEXT, padding=(6, 5), insertcolor=_TEXT)
        style.configure("TCombobox", fieldbackground=_INPUT, background="#edf0f2", foreground=_TEXT, arrowcolor=_MUTED)
        style.map("TCombobox", fieldbackground=[("readonly", _INPUT)], foreground=[("readonly", _TEXT)], selectbackground=[("readonly", _INPUT)], selectforeground=[("readonly", _TEXT)])
        style.configure("TRadiobutton", background=_PANEL, foreground=_TEXT, indicatorcolor=_INPUT)
        style.map("TRadiobutton", indicatorcolor=[("selected", _ACCENT), ("!selected", _INPUT)])
        style.map("TEntry", fieldbackground=[("disabled", "#edf0f2")], foreground=[("disabled", "#9097a0")])
        style.configure("TButton", background="#eff1f3", foreground=_TEXT, borderwidth=1, padding=(10, 7))
        style.map("TButton", background=[("active", "#fff0e2"), ("pressed", "#ffe1c5")])
        style.configure("Accent.TButton", background=_ACCENT, foreground="#ffffff")
        style.map("Accent.TButton", background=[("active", "#ed9854"), ("pressed", "#ce7128")])
        style.configure("TCheckbutton", padding=(0, 3), indicatorcolor=_INPUT)
        style.map("TCheckbutton", background=[("active", _PANEL)], indicatorcolor=[("selected", _ACCENT)])
        style.configure("Treeview", background=_INPUT, fieldbackground=_INPUT, foreground=_TEXT, rowheight=64, borderwidth=0)
        style.configure("Treeview.Heading", background="#e9ecef", foreground=_MUTED, padding=(7, 6), relief="flat")
        style.map("Treeview", background=[("selected", "#ffe5cd")], foreground=[("selected", _TEXT)])
        style.configure("TNotebook", background=_PANEL, borderwidth=0)
        style.configure("TNotebook.Tab", background="#e8ebee", foreground=_MUTED, padding=(17, 8))
        style.map("TNotebook.Tab", background=[("selected", _PANEL)], foreground=[("selected", _TEXT)])
        style.configure("TPanedwindow", background=_BG)
        style.configure("TScrollbar", background="#d4d9de", arrowcolor=_MUTED, borderwidth=0, arrowsize=12)

    @staticmethod
    def _text(parent: ttk.Frame) -> scrolledtext.ScrolledText:
        return scrolledtext.ScrolledText(parent, width=1, height=8, wrap=tk.WORD, undo=True, background=_INPUT, foreground=_TEXT, insertbackground=_TEXT, selectbackground="#ffe0c4", relief=tk.FLAT, borderwidth=0, padx=11, pady=10, font=("Consolas", 10), highlightthickness=1, highlightbackground="#d5d9de", highlightcolor=_ACCENT)

    def _resize_status(self, event: tk.Event) -> None:
        if event.widget is self.root:
            self.status_label.configure(wraplength=max(100, event.width - 36))

    def _status(self, message: str, error: bool = False) -> None:
        self.status_var.set(message)
        self.status_label.configure(foreground="#b13939" if error else "#527264")

    def _execute(self, callback: Callable[[], _T], success: str) -> _T | None:
        try:
            result = callback()
        except json.JSONDecodeError as error:
            self._status(f"JSON 格式有误：第 {error.lineno} 行，第 {error.colno} 列。", True)
            return None
        except Exception as error:
            self._status(f"操作失败：{error}", True)
            return None
        self._status(success)
        return result

    @staticmethod
    def _get_text(widget: tk.Text) -> str:
        return widget.get("1.0", "end-1c")

    @staticmethod
    def _set_text(widget: tk.Text, value: str) -> None:
        widget.delete("1.0", tk.END)
        widget.insert("1.0", value)
        widget.edit_reset()

    def _sync_json(self) -> None:
        if self._changing:
            return
        value = {"charId": self.char_id_var.get().strip(), "cards": self._cards}
        self._set_text(self.json_text, json.dumps(value, ensure_ascii=False, indent=2))
        self._visual_state_changed()

    def _deck_from_editor(self) -> Deck:
        return Deck.from_dict({"charId": self.char_id_var.get().strip(), "cards": self._cards})

    @staticmethod
    def _card_state(card: dict) -> str:
        flags = [label for key, label in (("removed", "已移除"), ("duplicate", "重复")) if card.get(key)]
        return " · ".join(flags) if flags else "启用"

    def _populate(self, deck: Deck) -> None:
        self._changing = True
        for index in range(len(self._cards)):
            if self.tree.exists(str(index)):
                self.tree.delete(str(index))
        self.char_id_var.set(deck.char_id)
        self._cards = [card.to_dict() for card in deck.cards]
        for index, card in enumerate(self._cards):
            self.tree.insert("", tk.END, iid=str(index), values=(card["cardId"], self._card_state(card)))
        self._changing = False

        self.count_var.set(f"{len(self._cards)} 张卡牌")
        self._select_card(0 if self._cards else None)
        self._sync_json()

    def _select_card(self, index: int | None) -> None:
        self._selected = index
        self._changing = True
        card = self._cards[index] if index is not None else {}
        for key, variable in self.card_vars.items():
            variable.set(bool(card.get(key, False)) if key in ("removed", "duplicate") else card.get(key) or "")
        if index is not None:
            self.tree.selection_set(str(index))
            self.tree.focus(str(index))
            self.tree.see(str(index))
        self._changing = False
        self._visual_refresh_selection()

    def _on_selection(self, _event: tk.Event | None = None) -> None:
        if self._changing:
            return
        selection = self.tree.selection()
        index = int(selection[0]) if selection else None
        if index != self._selected:
            self._select_card(index)

    def _update_selected(self) -> None:
        if self._changing or self._selected is None:
            return
        card = {"cardId": str(self.card_vars["cardId"].get()).strip(), "removed": bool(self.card_vars["removed"].get()), "duplicate": bool(self.card_vars["duplicate"].get())}
        for key in _OPTIONAL_FIELDS:
            value = str(self.card_vars[key].get()).strip()
            if value:
                card[key] = value
        self._cards[self._selected] = card
        self._set_text(self.code_text, "")
        self.tree.item(str(self._selected), values=(card["cardId"] or "（未填写卡牌 ID）", self._card_state(card)))
        self._sync_json()

    def load_example(self) -> None:
        self.select_character("30134")
        self._populate(example_deck())
        self._set_text(self.code_text, EXAMPLE_CODE)
        self._status("已载入「羅斯薇瑟」示例构筑。选择卡牌后可在右侧编辑灵光。")

    def add_card(self) -> None:
        self._cards.append({"cardId": "", "removed": False, "duplicate": False})
        index = len(self._cards) - 1
        self.tree.insert("", tk.END, iid=str(index), values=("（未填写卡牌 ID）", "启用"))
        self.count_var.set(f"{len(self._cards)} 张卡牌")
        self._select_card(index)
        self._sync_json()

    def remove_card(self) -> None:
        if self._selected is None:
            self._status("请先选择要删除的卡牌。", True)
            return
        index = self._selected
        rows = self._cards[:index] + self._cards[index + 1:]
        self._populate(Deck.from_dict({"charId": self.char_id_var.get(), "cards": rows}))
        self._select_card(min(index, len(self._cards) - 1) if self._cards else None)
        self._sync_json()
        self._status("已删除选中卡牌。")

    def encode_deck(self) -> str | None:
        def action() -> str:
            code = encode(self._deck_from_editor())
            self._set_text(self.code_text, code)
            self.notebook.select(0)
            return code
        return self._execute(action, "卡组码已生成，可复制后分享。")

    def decode_code(self) -> Deck | None:
        def action() -> Deck:
            code = self._get_text(self.code_text).strip()
            if not code:
                raise ValueError("请先输入卡组码。")
            return self.import_deck_code(code)
        return self._execute(action, "解码完成，卡组已载入编辑器。")

    def apply_json(self) -> Deck | None:
        def action() -> Deck:
            value = json.loads(self._get_text(self.json_text))
            deck = Deck.from_dict(value)
            self.load_external_deck(deck, replace=deck.char_id == self.char_id_var.get())
            return deck
        return self._execute(action, "JSON 已应用到卡组。")

    def import_json(self, path: str | Path | None = None) -> Deck | None:
        if path is None:
            path = filedialog.askopenfilename(parent=self.root, title="导入卡组 JSON", filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")])
        if not path:
            return None
        def action() -> Deck:
            deck = Deck.from_dict(json.loads(Path(path).read_text(encoding="utf-8-sig")))
            self.load_external_deck(deck, name=Path(path).stem)
            return deck
        return self._execute(action, "卡组 JSON 已导入。")

    def export_json(self, path: str | Path | None = None) -> Path | None:
        deck = self._execute(self._deck_from_editor, "")
        if deck is None:
            return None
        if path is None:
            path = filedialog.asksaveasfilename(parent=self.root, title="导出卡组 JSON", initialfile=f"czn-deck-{deck.char_id}.json", defaultextension=".json", filetypes=[("JSON 文件", "*.json")])
        if not path:
            return None
        def action() -> Path:
            target = Path(path)
            with target.open("w", encoding="utf-8", newline="\n") as output:
                output.write(json.dumps(deck.to_dict(), ensure_ascii=False, indent=2) + "\n")
            return target
        return self._execute(action, "卡组 JSON 已导出。")

    def _copy(self, text: str, label: str) -> str | None:
        def action() -> str:
            if not text.strip():
                raise ValueError(f"暂无可复制的{label}。")
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            return text
        return self._execute(action, f"{label}已复制。")

    def copy_code(self) -> str | None:
        return self._copy(self._get_text(self.code_text).strip(), "卡组码")

    def copy_json(self) -> str | None:
        return self._copy(self._get_text(self.json_text), "JSON")


def run() -> None:
    """Open the native desktop application and run its event loop."""
    root = tk.Tk()
    try:
        DeckApplication(root)
    except Exception as error:
        from tkinter import messagebox
        messagebox.showerror("工作台启动失败", str(error), parent=root)
        root.destroy()
        return
    root.mainloop()


def main() -> None:
    run()


if __name__ == "__main__":
    main()
