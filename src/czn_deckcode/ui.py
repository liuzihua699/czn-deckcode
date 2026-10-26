"""Native Tkinter desktop workbench for the offline deck-code SDK."""

from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, font as tkfont, scrolledtext, ttk
from typing import Callable, TypeVar

from czn_deckcode import Card, Deck, decode, encode


EXAMPLE_CODE = "v6l8cOjiNr8NyAd5bz8N5Gb4BacatRLcP_gTJk6Sy-IpI4UudHIDQRTERzqzgUXu"
_OPTIONAL_FIELDS = ("variantCardId", "epiphanyId", "divineId", "god")
_T = TypeVar("_T")
_BG = "#10131b"
_PANEL = "#181d29"
_INPUT = "#101520"
_TEXT = "#e6e9f2"
_MUTED = "#8e9ab0"
_ACCENT = "#9e8af4"


def example_deck() -> Deck:
    cards = []
    for name in ("srt1", "srt2", "srt3", "srt4", "uni1", "uni2", "uni3", "uni4"):
        card_id = f"c_30134_{name}"
        cards.append(Card(card_id, variant_card_id=f"{card_id}_pot" if name in ("srt1", "srt2") else None))
    return Deck("30134", tuple(cards))


class DeckApplication:
    """Desktop view and editable deck state, backed directly by the SDK."""

    def __init__(self, root: tk.Tk):
        self.root = root
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
        self.load_example()

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
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background=_PANEL, foreground=_TEXT, bordercolor="#343c50", lightcolor="#343c50", darkcolor="#343c50", troughcolor=_INPUT)
        style.configure("App.TFrame", background=_BG)
        style.configure("App.TLabel", background=_BG)
        style.configure("Title.TLabel", font=(family, 18, "bold"), background=_BG)
        style.configure("Muted.TLabel", foreground=_MUTED)
        style.configure("AppMuted.TLabel", background=_BG, foreground=_MUTED)
        style.configure("TLabelframe", borderwidth=1, relief="solid")
        style.configure("TLabelframe.Label", foreground="#c8c2e6", font=(family, 10, "bold"))
        style.configure("TEntry", fieldbackground=_INPUT, foreground=_TEXT, padding=(6, 5), insertcolor=_TEXT)
        style.map("TEntry", fieldbackground=[("disabled", "#151a25")], foreground=[("disabled", "#667188")])
        style.configure("TButton", background="#272e40", foreground=_TEXT, borderwidth=1, padding=(10, 6))
        style.map("TButton", background=[("active", "#37415a"), ("pressed", "#414c68")])
        style.configure("Accent.TButton", background="#816ee0", foreground="#ffffff")
        style.map("Accent.TButton", background=[("active", "#9480f1"), ("pressed", "#6e5dcc")])
        style.configure("TCheckbutton", padding=(0, 3), indicatorcolor=_INPUT)
        style.map("TCheckbutton", background=[("active", _PANEL)], indicatorcolor=[("selected", _ACCENT)])
        style.configure("Treeview", background=_INPUT, fieldbackground=_INPUT, foreground=_TEXT, rowheight=27, borderwidth=0)
        style.configure("Treeview.Heading", background="#242c3c", foreground="#aebad0", padding=(7, 6), relief="flat")
        style.map("Treeview", background=[("selected", "#3d355f")], foreground=[("selected", "#ffffff")])
        style.configure("TNotebook", background=_PANEL, borderwidth=0)
        style.configure("TNotebook.Tab", background="#22293a", foreground=_MUTED, padding=(17, 8))
        style.map("TNotebook.Tab", background=[("selected", _PANEL)], foreground=[("selected", _TEXT)])
        style.configure("TPanedwindow", background=_BG)
        style.configure("TScrollbar", background="#303a50", arrowcolor=_MUTED, borderwidth=0)

    def _build(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        heading = ttk.Frame(self.root, style="App.TFrame", padding=(18, 16, 18, 12))
        heading.grid(row=0, column=0, sticky="ew")
        heading.columnconfigure(0, weight=1)
        ttk.Label(heading, text="CZN / 卡组工作台", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(heading, text="编辑构筑、生成分享码，所有操作均在本机完成。", style="AppMuted.TLabel").grid(row=1, column=0, sticky="w", pady=(5, 0))
        ttk.Button(heading, text="载入示例", command=self.load_example).grid(row=0, column=1, rowspan=2, padx=(12, 0))
        self.panes = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        self.panes.grid(row=1, column=0, sticky="nsew", padx=18)
        left = ttk.LabelFrame(self.panes, text=" 01  卡组构筑 ", padding=12)
        right = ttk.LabelFrame(self.panes, text=" 02  卡组码与 JSON ", padding=12)
        self.panes.add(left, weight=1)
        self.panes.add(right, weight=1)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        character = ttk.Frame(left)
        character.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        character.columnconfigure(1, weight=1)
        ttk.Label(character, text="角色 ID").grid(row=0, column=0, padx=(0, 9))
        self.char_entry = ttk.Entry(character, textvariable=self.char_id_var, width=15)
        self.char_entry.grid(row=0, column=1, sticky="ew")
        ttk.Label(character, textvariable=self.count_var, style="Muted.TLabel").grid(row=0, column=2, padx=(10, 0))
        tree_frame = ttk.Frame(left)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(tree_frame, columns=("card", "state"), show="headings", selectmode="browse", height=5)
        self.tree.heading("card", text="卡牌 ID")
        self.tree.heading("state", text="状态")
        self.tree.column("card", width=255, minwidth=140, stretch=True)
        self.tree.column("state", width=95, minwidth=80, stretch=False)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<<TreeviewSelect>>", self._on_selection)
        row_buttons = ttk.Frame(left)
        row_buttons.grid(row=2, column=0, sticky="ew", pady=(8, 10))
        ttk.Button(row_buttons, text="＋ 添加卡牌", command=self.add_card).pack(side=tk.LEFT)
        ttk.Button(row_buttons, text="删除选中", command=self.remove_card).pack(side=tk.LEFT, padx=(8, 0))
        editor = ttk.LabelFrame(left, text=" 选中卡牌 ", padding=(9, 7))
        editor.grid(row=3, column=0, sticky="ew")
        editor.columnconfigure(1, weight=1)
        self.editor_controls: list[ttk.Widget] = []
        fields = ((0, "cardId", "卡牌 ID"), (2, "variantCardId", "变体 ID"), (3, "epiphanyId", "顿悟 ID"), (4, "divineId", "神格 ID"), (5, "god", "神明"))
        for row, key, text in fields:
            ttk.Label(editor, text=text, width=8).grid(row=row, column=0, sticky="w", pady=3)
            entry = ttk.Entry(editor, textvariable=self.card_vars[key])
            entry.grid(row=row, column=1, sticky="ew", pady=3)
            self.editor_controls.append(entry)
            if key == "cardId":
                self.card_id_entry = entry
        checks = ttk.Frame(editor)
        checks.grid(row=1, column=1, sticky="w", pady=(1, 3))
        for key, text in (("removed", "已移除"), ("duplicate", "重复卡")):
            control = ttk.Checkbutton(checks, text=text, variable=self.card_vars[key])
            control.pack(side=tk.LEFT, padx=(0, 19))
            self.editor_controls.append(control)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        self.notebook = ttk.Notebook(right)
        self.notebook.grid(row=0, column=0, sticky="nsew")
        code_page = ttk.Frame(self.notebook, padding=(9, 12, 9, 9))
        json_page = ttk.Frame(self.notebook, padding=(9, 12, 9, 9))
        self.notebook.add(code_page, text="卡组码")
        self.notebook.add(json_page, text="JSON 编辑")
        for page in (code_page, json_page):
            page.columnconfigure(0, weight=1)
            page.rowconfigure(1, weight=1)
        ttk.Label(code_page, text="粘贴已有卡组码，或由左侧构筑生成。", style="Muted.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 9))
        self.code_text = self._text(code_page)
        self.code_text.grid(row=1, column=0, sticky="nsew")
        code_actions = ttk.Frame(code_page)
        code_actions.grid(row=2, column=0, sticky="ew", pady=(11, 0))
        for column in range(3):
            code_actions.columnconfigure(column, weight=1)
        ttk.Button(code_actions, text="生成卡组码", style="Accent.TButton", command=self.encode_deck).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(code_actions, text="解码到卡组", command=self.decode_code).grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Button(code_actions, text="复制", command=self.copy_code).grid(row=0, column=2, sticky="ew", padx=(5, 0))
        ttk.Label(code_page, text="解码会替换左侧内容；复制后可直接分享。", style="Muted.TLabel", wraplength=340).grid(row=3, column=0, sticky="w", pady=(10, 0))
        ttk.Label(json_page, text="可直接编辑，再点击「应用到卡组」。", style="Muted.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 9))
        self.json_text = self._text(json_page)
        self.json_text.grid(row=1, column=0, sticky="nsew")
        json_actions = ttk.Frame(json_page)
        json_actions.grid(row=2, column=0, sticky="ew", pady=(11, 0))
        ttk.Button(json_actions, text="应用到卡组", style="Accent.TButton", command=self.apply_json).pack(side=tk.LEFT)
        ttk.Button(json_actions, text="复制 JSON", command=self.copy_json).pack(side=tk.LEFT, padx=(8, 0))
        file_actions = ttk.Frame(right)
        file_actions.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        ttk.Button(file_actions, text="导入 JSON", command=self.import_json).pack(side=tk.LEFT)
        ttk.Button(file_actions, text="导出 JSON", command=self.export_json).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(file_actions, text="纯离线", style="Muted.TLabel").pack(side=tk.RIGHT)
        self.status_label = ttk.Label(self.root, textvariable=self.status_var, style="AppMuted.TLabel", padding=(18, 10), wraplength=860)
        self.status_label.grid(row=2, column=0, sticky="ew")
        self.root.bind("<Configure>", self._resize_status, add=True)

    @staticmethod
    def _text(parent: ttk.Frame) -> scrolledtext.ScrolledText:
        return scrolledtext.ScrolledText(parent, width=1, height=8, wrap=tk.WORD, undo=True, background=_INPUT, foreground="#d0c9f7", insertbackground=_TEXT, selectbackground="#51466f", relief=tk.FLAT, borderwidth=0, padx=11, pady=10, font=("Consolas", 10), highlightthickness=1, highlightbackground="#343c50", highlightcolor=_ACCENT)

    def _resize_status(self, event: tk.Event) -> None:
        if event.widget is self.root:
            self.status_label.configure(wraplength=max(100, event.width - 36))

    def _status(self, message: str, error: bool = False) -> None:
        self.status_var.set(message)
        self.status_label.configure(foreground="#f2a9b8" if error else "#a8c9b8")

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

    def _deck_from_editor(self) -> Deck:
        return Deck.from_dict({"charId": self.char_id_var.get().strip(), "cards": self._cards})

    @staticmethod
    def _card_state(card: dict) -> str:
        flags = [label for key, label in (("removed", "已移除"), ("duplicate", "重复")) if card.get(key)]
        return " · ".join(flags) if flags else "启用"

    def _populate(self, deck: Deck) -> None:
        self._changing = True
        self.char_id_var.set(deck.char_id)
        self._cards = [card.to_dict() for card in deck.cards]
        self.tree.delete(*self.tree.get_children())
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
        for control in self.editor_controls:
            control.configure(state=tk.NORMAL if index is not None else tk.DISABLED)
        if index is not None:
            self.tree.selection_set(str(index))
            self.tree.focus(str(index))
            self.tree.see(str(index))
        self._changing = False

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
        self.tree.item(str(self._selected), values=(card["cardId"] or "（未填写卡牌 ID）", self._card_state(card)))
        self._sync_json()

    def load_example(self) -> None:
        self._populate(example_deck())
        self._set_text(self.code_text, EXAMPLE_CODE)
        self._status("已载入角色 30134 的示例构筑。可直接编辑或解码。")

    def add_card(self) -> None:
        self._cards.append({"cardId": "", "removed": False, "duplicate": False})
        index = len(self._cards) - 1
        self.tree.insert("", tk.END, iid=str(index), values=("（未填写卡牌 ID）", "启用"))
        self.count_var.set(f"{len(self._cards)} 张卡牌")
        self._select_card(index)
        self._sync_json()
        self.card_id_entry.focus_set()
        self._status("已添加卡牌，请填写卡牌 ID。")

    def remove_card(self) -> None:
        if self._selected is None:
            self._status("请先选择要删除的卡牌。", True)
            return
        index = self._selected
        self._cards.pop(index)
        self.tree.delete(*self.tree.get_children())
        for number, card in enumerate(self._cards):
            self.tree.insert("", tk.END, iid=str(number), values=(card["cardId"], self._card_state(card)))
        self.count_var.set(f"{len(self._cards)} 张卡牌")
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
            deck = decode(code)
            self._populate(deck)
            return deck
        return self._execute(action, "解码完成，卡组已载入编辑器。")

    def apply_json(self) -> Deck | None:
        def action() -> Deck:
            value = json.loads(self._get_text(self.json_text))
            deck = Deck.from_dict(value)
            self._populate(deck)
            return deck
        return self._execute(action, "JSON 已应用到卡组。")

    def import_json(self, path: str | Path | None = None) -> Deck | None:
        if path is None:
            path = filedialog.askopenfilename(parent=self.root, title="导入卡组 JSON", filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")])
        if not path:
            return None
        def action() -> Deck:
            deck = Deck.from_dict(json.loads(Path(path).read_text(encoding="utf-8-sig")))
            self._populate(deck)
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
    DeckApplication(root)
    root.mainloop()


def main() -> None:
    run()


if __name__ == "__main__":
    main()
