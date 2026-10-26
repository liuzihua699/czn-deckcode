"""Client-style deck workspace using local artwork and local presets."""
from __future__ import annotations

import copy
import re
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox

from .library import CardImages, CardLibrary, TYPE_NAMES, TYPE_NAMES_S
from czn_deckcode.models import Deck

BG, PANEL, INPUT, TEXT, MUTED, ACCENT = "#e6e8eb", "#f8f9fa", "#ffffff", "#30353b", "#79818b", "#e98534"


class ScrollPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, background=PANEL, highlightthickness=0, width=120)
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scroll.set)
        self.inner = ttk.Frame(self.canvas)
        self.window = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.inner.bind("<Configure>", lambda _: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.window, width=e.width))

    def wheel(self, event):
        units = -int(event.delta / 120) if abs(event.delta) >= 120 else (-1 if event.delta > 0 else 1)
        self.canvas.yview_scroll(units, "units")
        return "break"

    def bind_wheel(self, widget):
        widget.bind("<MouseWheel>", self.wheel)


class VisualWorkbench:
    def _build(self):
        self.library = CardLibrary()
        self.images = CardImages(self.root, self.library)
        self.language_var = tk.StringVar(self.root, self.store.data.get("language", "繁體中文"))
        self.character_search = tk.StringVar(self.root)
        self.card_search = tk.StringVar(self.root)
        self.group_var = tk.StringVar(self.root, "character")
        self.show_removed = tk.BooleanVar(self.root, False)
        self._active_preset = self._loaded_owner = None
        self._detail_window = self._choice_window = self._import_window = None
        self._grid_after = self._deck_signature = None
        self._deck_width = self._library_page = 0
        self._pending_action = None
        self.root.geometry("1480x930")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        header = ttk.Frame(self.root, style="App.TFrame", padding=(18, 12))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text="预设构筑", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="选择角色  /  管理卡组  /  编辑灵光", style="AppMuted.TLabel").grid(row=0, column=1, sticky="w", padx=20)
        ttk.Combobox(header, textvariable=self.language_var, values=("繁體中文", "简体中文"), state="readonly", width=10).grid(row=0, column=2, padx=6)
        ttk.Button(header, text="从卡组码导入", command=self._open_import_dialog).grid(row=0, column=3, padx=6)
        ttk.Button(header, text="导出 / 分享", command=self._encode_and_show).grid(row=0, column=4, padx=6)
        self.panes = ttk.Panedwindow(self.root, orient="horizontal")
        self.panes.grid(row=1, column=0, sticky="nsew", padx=14)
        roles = ttk.Frame(self.panes, width=170, padding=10)
        center = ttk.Frame(self.panes, width=950, padding=(10, 12))
        sidebar = ttk.Frame(self.panes, width=294, padding=12)
        roles.pack_propagate(False)
        sidebar.pack_propagate(False)
        self.panes.add(roles, weight=0)
        self.panes.add(center, weight=5)
        self.panes.add(sidebar, weight=0)
        ttk.Label(roles, text="角色", font=(self.font_family, 12, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Entry(roles, textvariable=self.character_search, width=14).pack(fill="x", pady=(0, 8))
        self.character_panel = ScrollPanel(roles)
        self.character_panel.pack(fill="both", expand=True)
        self.character_buttons = {}
        self._render_characters()
        self.character_search.trace_add("write", lambda *_: self._render_characters())
        self.language_var.trace_add("write", lambda *_: self._language_changed())
        center.columnconfigure(1, weight=1)
        center.rowconfigure(1, weight=1)
        title = ttk.Frame(center)
        title.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        title.columnconfigure(0, weight=1)
        self.character_label = ttk.Label(title, font=(self.font_family, 16, "bold"))
        self.character_label.grid(row=0, column=0, sticky="w")
        self.preset_name_var = tk.StringVar(self.root)
        ttk.Label(title, textvariable=self.preset_name_var, foreground=MUTED).grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Button(title, text="重命名", command=self._rename_preset).grid(row=0, column=1, padx=3)
        menu_button = ttk.Menubutton(title, text="管理 ▾")
        menu = tk.Menu(menu_button, tearoff=False)
        menu.add_command(label="新建预设", command=self.new_preset)
        menu.add_command(label="复制当前预设", command=self.copy_preset)
        menu.add_command(label="删除当前预设", command=self._confirm_delete_preset)
        menu_button["menu"] = menu
        menu_button.grid(row=0, column=2, padx=3)
        self.preset_panel = ScrollPanel(center)
        self.preset_panel.grid(row=1, column=0, sticky="ns", padx=(0, 10))
        self.preset_panel.canvas.configure(width=54)
        self.deck_views = ttk.Notebook(center)
        self.deck_views.grid(row=1, column=1, sticky="nsew")
        self.deck_panel = ScrollPanel(self.deck_views)
        table = ttk.Frame(self.deck_views)
        self.deck_views.add(self.deck_panel, text="卡片视图")
        self.deck_views.add(table, text="列表视图")
        self.tree = ttk.Treeview(table, columns=("name", "state"), show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="卡面"); self.tree.column("#0", width=54, stretch=False)
        self.tree.heading("name", text="卡牌"); self.tree.column("name", width=200)
        self.tree.heading("state", text="状态"); self.tree.column("state", width=160)
        bar = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=bar.set)
        self.tree.pack(side="left", fill="both", expand=True); bar.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_selection)
        self.tree.bind("<Double-1>", lambda _: self._open_card_details())
        self.deck_panel.canvas.bind("<Configure>", self._deck_resized, add=True)
        self.deck_panel.bind_wheel(self.deck_panel.canvas)
        bottom = ttk.Frame(center)
        bottom.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Checkbutton(bottom, text="显示已移除", variable=self.show_removed, command=self._removed_filter_changed).pack(side="left")
        ttk.Button(bottom, text="← 前移", command=lambda: self._move_card(-1)).pack(side="left", padx=4)
        ttk.Button(bottom, text="后移 →", command=lambda: self._move_card(1)).pack(side="left")
        ttk.Button(bottom, text="保存预设", style="Accent.TButton", command=self.save_presets).pack(side="right")
        self._stats = [tk.StringVar(self.root) for _ in range(4)]
        stats = ttk.Frame(sidebar); stats.pack(fill="x", pady=(0, 12))
        for i, variable in enumerate(self._stats):
            tk.Label(stats, textvariable=variable, bg="#eef0f2", fg=TEXT, font=(self.font_family, 10), padx=8, pady=9).grid(row=i // 2, column=i % 2, sticky="ew", padx=1, pady=1)
            stats.columnconfigure(i % 2, weight=1)
        ttk.Label(sidebar, text="编辑功能", foreground=MUTED).pack(anchor="w", pady=(0, 5))
        self.action_buttons = {}
        actions = (("add", "＋  新增卡牌", self._focus_library), ("remove", "－  移除 / 恢复卡牌", self._toggle_removed),
                   ("duplicate", "▣  复制卡牌", self._duplicate_card), ("unique", "✧  独特灵光一闪", lambda: self._open_epiphany("unique")),
                   ("divine", "✦  神之灵光一闪", lambda: self._open_epiphany("divine")), ("epiphany", "✧  一般灵光一闪", lambda: self._open_epiphany("epiphany")))
        for key, label, callback in actions:
            button = ttk.Button(sidebar, text=label, command=callback)
            button.pack(fill="x", pady=3); self.action_buttons[key] = button
        ttk.Separator(sidebar).pack(fill="x", pady=12)
        ttk.Label(sidebar, text="卡牌库", font=(self.font_family, 12, "bold")).pack(anchor="w")
        groups = ttk.Frame(sidebar); groups.pack(fill="x", pady=5)
        for label, value in (("角色", "character"), ("公共", "neutral"), ("记忆", "memory")):
            ttk.Radiobutton(groups, text=label, variable=self.group_var, value=value).pack(side="left", padx=(0, 9))
        self.library_search_entry = ttk.Entry(sidebar, textvariable=self.card_search)
        self.library_search_entry.pack(fill="x", pady=(0, 6))
        self.card_panel = ScrollPanel(sidebar); self.card_panel.canvas.configure(height=40)
        self.library_summary = tk.StringVar(self.root)
        pager = ttk.Frame(sidebar); pager.pack(side="bottom", fill="x", pady=(6, 0))
        ttk.Button(pager, text="‹", width=3, command=lambda: self._change_library_page(-1)).pack(side="left")
        ttk.Label(pager, textvariable=self.library_summary, foreground=MUTED).pack(side="left", expand=True)
        ttk.Button(pager, text="›", width=3, command=lambda: self._change_library_page(1)).pack(side="right")
        self.card_panel.pack(fill="both", expand=True)
        for variable in (self.card_search, self.group_var): variable.trace_add("write", lambda *_: self._reset_library())
        self.status_label = ttk.Label(self.root, textvariable=self.status_var, style="AppMuted.TLabel", padding=(18, 9))
        self.status_label.grid(row=2, column=0, sticky="ew")
        self.root.bind("<Configure>", self._resize_status, add=True)
        self.root.bind("<Escape>", lambda _: self._cancel_action())
        self.root.bind("<Control-s>", lambda _: self.save_presets())
        self.root.protocol("WM_DELETE_WINDOW", self._close_app)
        self.root.bind("<Destroy>", self._cancel_render, add=True)
        self._build_share_window()

    def _build_share_window(self):
        self.share_window = tk.Toplevel(self.root); self.share_window.withdraw()
        self.share_window.title("导出与数据工具"); self.share_window.geometry("760x570")
        self.share_window.protocol("WM_DELETE_WINDOW", self.share_window.withdraw)
        self.notebook = ttk.Notebook(self.share_window); self.notebook.pack(fill="both", expand=True, padx=14, pady=14)
        code_page = ttk.Frame(self.notebook, padding=10); json_page = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(code_page, text="卡组码"); self.notebook.add(json_page, text="JSON 数据工具")
        for page in (code_page, json_page): page.rowconfigure(1, weight=1); page.columnconfigure(0, weight=1)
        ttk.Label(code_page, text="生成后可复制分享；导入请使用主界面的「从卡组码导入」。", wraplength=650).grid(row=0, column=0, sticky="w", pady=(0, 12))
        self.code_text = self._text(code_page); self.code_text.grid(row=1, column=0, sticky="nsew")
        ttk.Button(code_page, text="复制卡组码", command=self.copy_code).grid(row=2, column=0, sticky="e", pady=10)
        ttk.Label(json_page, text="可选的数据备份工具；日常组卡无需填写任何 ID。", wraplength=650).grid(row=0, column=0, sticky="w", pady=(0, 12))
        self.json_text = self._text(json_page); self.json_text.grid(row=1, column=0, sticky="nsew")
        buttons = ttk.Frame(json_page); buttons.grid(row=2, column=0, sticky="ew", pady=10)
        for label, command in (("导入文件", self.import_json), ("导出文件", self.export_json), ("应用 JSON", self.apply_json), ("复制 JSON", self.copy_json)):
            ttk.Button(buttons, text=label, command=command).pack(side="left", padx=3)

    def _render_characters(self):
        position = self.character_panel.canvas.yview()[0]
        for child in self.character_panel.inner.winfo_children(): child.destroy()
        self.character_buttons.clear(); query = self.character_search.get().strip().casefold(); self._portraits = []
        for char in self.library.characters:
            if query and not any(query in char.get(k, "").casefold() for k in ("name", "name_s")): continue
            image = self.images.portrait(char, (42, 40)); self._portraits.append(image)
            button = tk.Button(self.character_panel.inner, text="  " + self.library.text(char, language=self.language_var.get()), image=image, compound="left", anchor="w", font=(self.font_family, 10), relief="flat", borderwidth=0, padx=5, pady=5, command=lambda owner=char["id"]: self.select_character(owner))
            button.pack(fill="x", pady=2); self.character_panel.bind_wheel(button); self.character_buttons[char["id"]] = button
        self._highlight_character(); self.character_panel.inner.update_idletasks(); self.character_panel.canvas.yview_moveto(position)

    def _highlight_character(self):
        for owner, button in self.character_buttons.items():
            active = owner == self.char_id_var.get()
            button.configure(bg="#fff0e2" if active else PANEL, fg="#c76b27" if active else TEXT, activebackground="#f9e0c9")

    def _language_changed(self):
        self._render_characters(); self._reset_library(); self._visual_state_changed()
        self.store.data["language"] = self.language_var.get()

    def _group(self):
        return self.store.ensure(self.char_id_var.get(), self.library.starter(self.char_id_var.get()))

    def _capture_preset(self):
        if not self._active_preset or not self._loaded_owner: return
        Deck.from_dict({"charId": self._loaded_owner, "cards": self._cards})
        group = self.store.data["characters"][self._loaded_owner]
        preset = next(p for p in group["presets"] if p["id"] == self._active_preset)
        preset["cards"] = copy.deepcopy(self._cards)

    def select_character(self, owner):
        if owner == self._loaded_owner: return
        self._capture_preset()
        group = self.store.ensure(owner, self.library.starter(owner))
        self._activate(owner, group["active"])

    def _activate(self, owner, preset_id):
        self._pending_action = None
        group = self.store.data["characters"][owner]
        preset = next(p for p in group["presets"] if p["id"] == preset_id)
        self._loaded_owner, self._active_preset = owner, preset_id
        group["active"] = preset_id; self.store.data["selected_character"] = owner
        self._populate(Deck.from_dict({"charId": owner, "cards": preset["cards"]}))
        self._set_text(self.code_text, ""); self._render_presets(); self._reset_library()

    def _render_presets(self):
        for child in self.preset_panel.inner.winfo_children(): child.destroy()
        group = self._group()
        for i, preset in enumerate(group["presets"], 1):
            active = preset["id"] == self._active_preset
            button = tk.Button(self.preset_panel.inner, text=f"{i:02}", bg="#fff0e2" if active else "#5e6268", fg=ACCENT if active else "white", font=(self.font_family, 18, "bold"), relief="flat", borderwidth=0, pady=15, command=lambda key=preset["id"]: self.switch_preset(key))
            button.pack(fill="x", pady=(0, 9)); self.preset_panel.bind_wheel(button)
            if active: self.preset_name_var.set(preset["name"])
        ttk.Button(self.preset_panel.inner, text="＋", width=3, command=self.new_preset).pack(fill="x", pady=5)

    def switch_preset(self, key):
        if key == self._active_preset: return
        self._capture_preset(); self._activate(self.char_id_var.get(), key)

    def new_preset(self, name=None):
        self._capture_preset(); group = self._group()
        preset = self.store.make(name or f"{len(group['presets']) + 1}号预设", self.library.starter(self.char_id_var.get()))
        group["presets"].append(preset); self._activate(self.char_id_var.get(), preset["id"])
        self._status("已新建预设，可在右侧添加卡牌。")
        return preset["id"]

    def copy_preset(self):
        self._capture_preset(); group = self._group()
        current = next(p for p in group["presets"] if p["id"] == self._active_preset)
        preset = self.store.make(current["name"] + " 副本", self._cards)
        group["presets"].append(preset); self._activate(self.char_id_var.get(), preset["id"])
        self._status("已复制为独立预设。")
        return preset["id"]

    def _rename_preset(self):
        name = simpledialog.askstring("重命名预设", "卡组名称", initialvalue=self.preset_name_var.get(), parent=self.root)
        if name and name.strip(): self.rename_preset(name)

    def rename_preset(self, name):
        if not name.strip(): return
        preset = next(p for p in self._group()["presets"] if p["id"] == self._active_preset)
        preset["name"] = name.strip()[:80]; self._render_presets()

    def _confirm_delete_preset(self):
        if messagebox.askyesno("删除预设", f"删除「{self.preset_name_var.get()}」？", parent=self.root): self.delete_preset()

    def delete_preset(self):
        group = self._group(); group["presets"] = [p for p in group["presets"] if p["id"] != self._active_preset]
        if not group["presets"]: group["presets"] = [self.store.make("1号预设", self.library.starter(self.char_id_var.get()))]
        self._activate(self.char_id_var.get(), group["presets"][0]["id"])

    def save_presets(self):
        def action():
            self._capture_preset(); self.store.data["language"] = self.language_var.get(); self.store.write()
            return self.store.path
        return self._execute(action, "全部角色的预设已保存。")

    def _close_app(self):
        if self.save_presets() is not None: self.root.destroy()
        else: messagebox.showerror("保存失败", self.status_var.get() + "\n请检查目录权限后重试，或导出 JSON 备份。", parent=self.root)

    def _visual_state_changed(self):
        language = self.language_var.get()
        self.character_label.configure(text=self.library.text(self.library.character(self.char_id_var.get()), language=language))
        self._highlight_character(); self._tree_photos = []
        for i, row in enumerate(self._cards):
            photo = self.images.card(row, (38, 56), language); self._tree_photos.append(photo)
            self.tree.item(str(i), image=photo, values=(self.library.text(self.library.card(row), language=language), self._card_state(row)))
        self._filter_removed_rows()
        active = sum(not r.get("removed") for r in self._cards); removed = len(self._cards) - active
        duplicates = sum(bool(r.get("duplicate")) and not r.get("removed") for r in self._cards)
        flashed = sum(bool(re.search(r"_rsp\d+$", r.get("variantCardId", "")) or r.get("epiphanyId") or r.get("divineId")) and not r.get("removed") for r in self._cards)
        for var, text in zip(self._stats, (f"卡牌  {active}", f"灵光  {flashed}", f"复制  {duplicates}", f"已移除  {removed}")): var.set(text)
        self.count_var.set(f"{active} 张卡牌"); self._render_deck(); self._visual_refresh_selection()

    def _deck_resized(self, event):
        dimensions = (event.width, event.height)
        if dimensions == self._deck_width: return
        self._deck_width = dimensions
        if self._grid_after is not None: self.root.after_cancel(self._grid_after)
        self._grid_after = self.root.after(100, self._render_deck)

    def _cancel_render(self, event):
        if event.widget is self.root and self._grid_after is not None:
            self.root.after_cancel(self._grid_after); self._grid_after = None

    def _render_deck(self):
        if self._grid_after is not None: self.root.after_cancel(self._grid_after); self._grid_after = None
        width = self.deck_panel.canvas.winfo_width()
        if width < 100: width = 820
        columns = 4 if width >= 700 else 3 if width >= 500 else 2
        card_width = max(115, min(245, (width - 16 * columns - 12) // columns))
        height = self.deck_panel.canvas.winfo_height()
        if height > 300:
            card_width = min(card_width, max(115, int((height - 36) / 2.98)))
        signature = (repr(self._cards), self.language_var.get(), self.show_removed.get(), columns, card_width)
        if signature == self._deck_signature: self._visual_refresh_selection(); return
        self._deck_signature = signature; self._deck_frames = {}; self._deck_photos = []
        for child in self.deck_panel.inner.winfo_children(): child.destroy()
        visible = [(i, r) for i, r in enumerate(self._cards) if self.show_removed.get() or not r.get("removed")]
        for column in range(6): self.deck_panel.inner.columnconfigure(column, weight=1 if column < columns else 0)
        for n, (i, row) in enumerate(visible):
            frame = tk.Frame(self.deck_panel.inner, bg=PANEL, highlightthickness=3, highlightbackground=PANEL, padx=2, pady=2)
            frame.grid(row=n // columns, column=n % columns, sticky="n", padx=4, pady=6)
            photo = self.images.card(row, (card_width, round(card_width * 1.49)), self.language_var.get(), full=True)
            self._deck_photos.append(photo)
            label = tk.Label(frame, image=photo, borderwidth=0, bg=PANEL, cursor="hand2"); label.pack()
            label.bind("<Button-1>", lambda _, index=i: self._card_clicked(index))
            label.bind("<Double-1>", lambda _, index=i: self._card_double_clicked(index))
            self.deck_panel.bind_wheel(label); self._deck_frames[i] = frame
        if not visible: ttk.Label(self.deck_panel.inner, text="当前预设还没有卡牌\n从右侧卡牌库点击 ＋ 添加", foreground=MUTED, justify="center", padding=35).grid(row=0, column=0, columnspan=columns)
        self._visual_refresh_selection()

    def _visual_refresh_selection(self):
        for i, frame in getattr(self, "_deck_frames", {}).items(): frame.configure(highlightbackground=ACCENT if i == self._selected else PANEL)

    def _filter_removed_rows(self):
        for i, row in enumerate(self._cards):
            if row.get("removed") and not self.show_removed.get(): self.tree.detach(str(i))
            else: self.tree.move(str(i), "", "end")
        if self._selected is not None and self._cards[self._selected].get("removed") and not self.show_removed.get():
            self._select_card(next((i for i, row in enumerate(self._cards) if not row.get("removed")), None))

    def _removed_filter_changed(self):
        self._filter_removed_rows()
        self._render_deck()

    def _card_clicked(self, index):
        self._select_card(index)
        if self._pending_action:
            action, self._pending_action = self._pending_action, None
            if action in ("unique", "divine", "epiphany"): self._open_epiphany(action)
            elif action == "remove": self._toggle_removed()
            elif action == "duplicate": self._duplicate_card()

    def _card_double_clicked(self, index):
        self._select_card(index); self._open_card_details()

    def _require_card(self, action):
        if self._selected is not None: return True
        self._pending_action = action; self._status("请点击中间卡组中的一张卡牌；按 Esc 取消。")
        return False

    def _cancel_action(self):
        self._pending_action = None; self._status("已取消选择。")

    def _reset_library(self):
        self._library_page = 0; self._render_library()

    def _change_library_page(self, delta):
        self._library_page = max(0, self._library_page + delta); self._render_library()

    def _render_library(self):
        for child in self.card_panel.inner.winfo_children(): child.destroy()
        cards = self.library.available(self.char_id_var.get(), self.group_var.get(), self.card_search.get())
        pages = max(1, (len(cards) + 17) // 18); self._library_page = min(self._library_page, pages - 1)
        self.library_summary.set(f"{len(cards)} 张 · {self._library_page + 1}/{pages}"); self._library_photos = []
        types = TYPE_NAMES_S if self.language_var.get() == "简体中文" else TYPE_NAMES
        for item in cards[self._library_page * 18:(self._library_page + 1) * 18]:
            frame = ttk.Frame(self.card_panel.inner, padding=(2, 3)); frame.pack(fill="x")
            photo = self.images.card(item["id"], (38, 56), self.language_var.get()); self._library_photos.append(photo)
            label = ttk.Label(frame, image=photo); label.pack(side="left", padx=(0, 7))
            text = ttk.Frame(frame); text.pack(side="left", fill="x", expand=True)
            name = ttk.Label(text, text=self.library.text(item, language=self.language_var.get()), wraplength=143); name.pack(anchor="w")
            kind = ttk.Label(text, text=f"{types.get(item['type'], '特殊')}  ·  {item['cost']} AP", foreground=MUTED, font=(self.font_family, 9)); kind.pack(anchor="w", pady=(2, 0))
            button = ttk.Button(frame, text="＋", width=3, command=lambda key=item["id"]: self.add_library_card(key)); button.pack(side="right", padx=(3, 0))
            for widget in (frame, text, label, name, kind, button): self.card_panel.bind_wheel(widget)
        self.card_panel.canvas.yview_moveto(0)

    def _focus_library(self):
        self.library_search_entry.focus_set(); self.library_search_entry.selection_range(0, "end")
        self._status("在右侧搜索卡牌，点击 ＋ 加入当前预设。")

    def add_library_card(self, key):
        item = self.library.card(key)
        if item.get("owner") and item["owner"] != self.char_id_var.get():
            self._status("不能加入其他角色的专属卡牌，请先切换角色。", True); return
        if key not in self.library.cards: self._status("未收录此卡牌。", True); return
        base = item["base_id"]
        duplicate = any(self.library.card(r)["base_id"] == base and not r.get("removed") for r in self._cards)
        rows = copy.deepcopy(self._cards) + [{"cardId": base, "removed": False, "duplicate": duplicate}]
        self._populate(Deck.from_dict({"charId": self.char_id_var.get(), "cards": rows})); self._select_card(len(rows) - 1)
        self._status("卡牌已加入当前预设。")

    def _duplicate_card(self):
        if not self._require_card("duplicate"): return
        index = self._selected; rows = copy.deepcopy(self._cards)
        row = copy.deepcopy(rows[index]); row.update(duplicate=True, removed=False); rows.insert(index + 1, row)
        self._populate(Deck.from_dict({"charId": self.char_id_var.get(), "cards": rows})); self._select_card(index + 1)
        self._status("已复制卡牌及其灵光效果。")

    def _toggle_removed(self):
        if not self._require_card("remove"): return
        self.card_vars["removed"].set(not self.card_vars["removed"].get())
        self._status("已更新移除状态；勾选「显示已移除」后可选择移除的卡牌并恢复。")

    def _move_card(self, delta):
        i = self._selected
        if i is None or not 0 <= i + delta < len(self._cards): return
        rows = copy.deepcopy(self._cards); rows[i], rows[i + delta] = rows[i + delta], rows[i]
        self._populate(Deck.from_dict({"charId": self.char_id_var.get(), "cards": rows})); self._select_card(i + delta)

    def _clear_deck(self):
        self._populate(Deck(self.char_id_var.get(), ()))

    def set_variant(self, key):
        if self._selected is None: return
        row = copy.deepcopy(self._cards[self._selected]); item = self.library.card(key)
        row["cardId"] = item["base_id"]; row.pop("variantCardId", None); row.pop("epiphanyId", None)
        if key != item["base_id"]: row["variantCardId"] = key
        if not re.search(r"_rsp\d+$", key): row.pop("divineId", None); row.pop("god", None)
        self._replace_selected(row)

    def _replace_selected(self, row):
        index = self._selected
        if index is None: return
        rows = copy.deepcopy(self._cards); rows[index] = row
        self._populate(Deck.from_dict({"charId": self.char_id_var.get(), "cards": rows})); self._select_card(index)

    def apply_modifier(self, group, key):
        if self._selected is None: return False
        row = copy.deepcopy(self._cards[self._selected]); field = "divineId" if group == "divine" else "epiphanyId"
        if key:
            item = self.library.modifier_by_id[key]
            if item["group"] != group: raise ValueError("灵光分类不匹配")
            if group == "divine" and not (re.search(r"_rsp\d+$", row.get("variantCardId", "")) or row.get("epiphanyId")):
                self._status("请先选择独特灵光或一般灵光，再添加神闪。", True); return False
            if group == "epiphany": row["cardId"] = self.library.card(row)["base_id"]; row.pop("variantCardId", None)
            row[field] = key
            if group == "divine": row["god"] = item["god"]
        else:
            row.pop(field, None)
            if group == "divine": row.pop("god", None)
            elif not re.search(r"_rsp\d+$", row.get("variantCardId", "")): row.pop("divineId", None); row.pop("god", None)
        self._replace_selected(row)
        return True

    def _dialog(self, title, geometry):
        window = tk.Toplevel(self.root); window.title(title); window.geometry(geometry); window.transient(self.root); window.configure(bg=PANEL)
        if self.root.winfo_viewable(): window.grab_set()
        return window

    def _open_epiphany(self, group):
        if not self._require_card(group): return
        if self._choice_window and self._choice_window.winfo_exists(): self._choice_window.destroy()
        row = copy.deepcopy(self._cards[self._selected])
        if group == "divine" and not (re.search(r"_rsp\d+$", row.get("variantCardId", "")) or row.get("epiphanyId")):
            self._status("请先选择独特灵光或一般灵光，再添加神闪。", True); return
        if group == "unique": return self._open_unique_choices(row)
        title = "神之灵光一闪" if group == "divine" else "一般灵光一闪"
        window = self._dialog(title, "960x690"); self._choice_window = window
        body = ttk.Frame(window, padding=20); body.pack(fill="both", expand=True)
        ttk.Label(body, text=title, font=(self.font_family, 20, "bold")).pack(anchor="w")
        ttk.Label(body, text="按卡牌费用、类型与特性筛选；未校验全部游戏内条件。选择效果后预览。", foreground=MUTED).pack(anchor="w", pady=(7, 12))
        search = tk.StringVar(window); god_var = tk.StringVar(window, "全部神祇")
        filter_bar = ttk.Frame(body); filter_bar.pack(fill="x", pady=(0, 12))
        ttk.Label(filter_bar, text="搜索效果").pack(side="left", padx=(0, 10))
        entry = ttk.Entry(filter_bar, textvariable=search); entry.pack(side="left", fill="x", expand=True)
        choices = self.library.modifier_choices(row, group)
        gods = sorted({m["god"] for m in choices})
        god_labels = {self.library.text(self.library.gods.get(g, {"name": g}), language=self.language_var.get()): g for g in gods}
        if group == "divine": ttk.Combobox(filter_bar, textvariable=god_var, values=["全部神祇", *god_labels], state="readonly", width=14).pack(side="right", padx=(10, 0))
        content = ttk.Frame(body); content.pack(fill="both", expand=True)
        result_panel = ScrollPanel(content); result_panel.pack(side="left", fill="both", expand=True, padx=(0, 18))
        preview = ttk.Frame(content, width=260); preview.pack(side="right", fill="y")
        image_label = ttk.Label(preview); image_label.pack()
        description = ttk.Label(preview, wraplength=250, foreground=TEXT); description.pack(fill="x", pady=10)
        selection = {"key": row.get("divineId" if group == "divine" else "epiphanyId")}; buttons = []
        field = "divineId" if group == "divine" else "epiphanyId"
        def choose(key):
            selection["key"] = key; value = copy.deepcopy(row)
            if key:
                value[field] = key
                if group == "epiphany": value.pop("variantCardId", None)
            else: value.pop(field, None)
            photo = self.images.card(value, (240, 358), self.language_var.get(), full=True)
            image_label.configure(image=photo); image_label.image = photo
            description.configure(text=self.library.effects(value, self.language_var.get()))
            for option, button in buttons: button.configure(bg="#ffe5cc" if option == key else "#edf0f2")
        def render(*_):
            for child in result_panel.inner.winfo_children(): child.destroy()
            buttons.clear(); query = search.get().strip().casefold()
            for item in choices:
                if query and not any(query in item.get(k, "").casefold() for k in ("text", "text_s")): continue
                if god_var.get() != "全部神祇" and item["god"] != god_labels.get(god_var.get()): continue
                text = self.library.description(item, self.language_var.get())
                label = self.library.text(self.library.gods.get(item["god"], {"name": item["god"]}), language=self.language_var.get()) if group == "divine" else "一般灵光"
                frame = ttk.Frame(result_panel.inner, padding=(0, 3)); frame.pack(fill="x")
                button = tk.Button(frame, text=f"{label}\n{text}", wraplength=460, justify="left", anchor="w", relief="flat", bg="#edf0f2", fg=TEXT, activebackground="#ffe9d5", padx=12, pady=10, font=(self.font_family, 10), command=lambda key=item["id"]: choose(key))
                button.pack(fill="x"); result_panel.bind_wheel(button); buttons.append((item["id"], button))
            if not buttons: ttk.Label(result_panel.inner, text="没有匹配的灵光效果", padding=20).pack()
            result_panel.canvas.yview_moveto(0); choose(selection["key"])
        render(); search.trace_add("write", render); god_var.trace_add("write", render)
        bottom = ttk.Frame(body); bottom.pack(fill="x", pady=(14, 0))
        ttk.Button(bottom, text="清除此类灵光", command=lambda: choose(None)).pack(side="left")
        ttk.Button(bottom, text="取消", command=window.destroy).pack(side="right", padx=5)
        def apply():
            if self.apply_modifier(group, selection["key"]): window.destroy(); self._status(f"已更新{title}。")
        ttk.Button(bottom, text="应用效果", style="Accent.TButton", command=apply).pack(side="right", padx=5)
        entry.focus_set()
        return window

    def _open_unique_choices(self, row):
        variants = self.library.unique_variants(row)
        if not variants: self._status("这张卡没有收录独特灵光分支，可选择一般灵光。", True); return
        window = self._dialog("独特灵光一闪", "1240x650"); self._choice_window = window; window.configure(bg="#353a42")
        tk.Label(window, text="灵光一闪", font=(self.font_family, 24), bg="#353a42", fg="white").pack(pady=(25, 12))
        tk.Label(window, text="选择这张卡的独特灵光分支，点击卡面后应用。", font=(self.font_family, 12), bg="#353a42", fg="#ccd2d9").pack(pady=(0, 15))
        strip = tk.Canvas(window, bg="#353a42", highlightthickness=0, height=400); strip.pack(fill="both", expand=True, padx=18)
        horizontal = ttk.Scrollbar(window, orient="horizontal", command=strip.xview); horizontal.pack(fill="x", padx=18); strip.configure(xscrollcommand=horizontal.set)
        inner = tk.Frame(strip, bg="#353a42"); strip.create_window(0, 0, window=inner, anchor="nw")
        selection = tk.StringVar(window, row.get("variantCardId", "")); frames = {}; photos = []
        for i, item in enumerate(variants):
            value = copy.deepcopy(row); value["variantCardId"] = item["id"]; value.pop("epiphanyId", None)
            frame = tk.Frame(inner, bg="#353a42", highlightthickness=3, highlightbackground="#353a42", padx=3, pady=3); frame.grid(row=0, column=i, padx=7, pady=8)
            photo = self.images.card(value, (210, 314), self.language_var.get(), full=True); photos.append(photo)
            label = tk.Label(frame, image=photo, bg="#353a42", cursor="hand2"); label.pack()
            tk.Label(frame, text="当前灵光" if row.get("variantCardId") == item["id"] else f"分支 {i + 1}", bg="#353a42", fg="#e5e8ec", pady=10).pack(fill="x")
            label.bind("<Button-1>", lambda _, key=item["id"]: selection.set(key)); frames[item["id"]] = frame
        window._photos = photos
        def highlight(*_):
            for key, frame in frames.items(): frame.configure(highlightbackground=ACCENT if selection.get() == key else "#353a42")
        selection.trace_add("write", highlight); highlight(); inner.update_idletasks(); strip.configure(scrollregion=strip.bbox("all"))
        bottom = tk.Frame(window, bg="#353a42"); bottom.pack(fill="x", padx=25, pady=18)
        ttk.Button(bottom, text="还原基础卡牌", command=lambda: (self.set_variant(self.library.card(row)["base_id"]), window.destroy())).pack(side="left")
        ttk.Button(bottom, text="取消", command=window.destroy).pack(side="right", padx=6)
        def apply():
            if selection.get() in frames: self.set_variant(selection.get()); window.destroy(); self._status("已应用独特灵光分支。")
        ttk.Button(bottom, text="应用灵光", style="Accent.TButton", command=apply).pack(side="right", padx=6)
        return window

    def _open_card_details(self):
        if self._selected is None: return
        if self._detail_window and self._detail_window.winfo_exists(): self._detail_window.destroy()
        row = self._cards[self._selected]; window = self._dialog("卡牌详情", "650x580"); self._detail_window = window
        body = ttk.Frame(window, padding=24); body.pack(fill="both", expand=True)
        photo = self.images.card(row, (250, 373), self.language_var.get(), full=True)
        label = ttk.Label(body, image=photo); label.image = photo; label.pack(side="left", padx=(0, 22))
        side = ttk.Frame(body); side.pack(side="left", fill="both", expand=True)
        ttk.Label(side, text=self.library.text(self.library.card(row), language=self.language_var.get()), font=(self.font_family, 14, "bold"), wraplength=270).pack(anchor="w", pady=(0, 12))
        ttk.Label(side, text=self.library.effects(row, self.language_var.get()), wraplength=270).pack(anchor="w", pady=(0, 20))
        ttk.Label(side, text="数值为客户端基础参数，未计角色、装备和战斗加成。少量字段尚未求值。", wraplength=270, foreground=MUTED).pack(anchor="w", pady=(0, 14))
        for group, title in (("unique", "独特灵光一闪"), ("divine", "神之灵光一闪"), ("epiphany", "一般灵光一闪")):
            ttk.Button(side, text=title, command=lambda g=group: (window.destroy(), self._open_epiphany(g))).pack(fill="x", pady=4)
        def destroyed(event):
            if event.widget is window: self._detail_window = None
        window.bind("<Destroy>", destroyed)

    def import_deck_code(self, code, replace=False, name=None):
        from czn_deckcode import decode
        # Decode fully before mutating the current deck or any preset.
        deck = decode(code.strip())
        self.load_external_deck(deck, replace, name)
        self._set_text(self.code_text, code.strip())
        return deck

    def load_external_deck(self, deck, replace=False, name=None):
        if replace and deck.char_id != self.char_id_var.get(): raise ValueError("角色不同，请选择「导入为新预设」。")
        self._capture_preset(); group = self.store.ensure(deck.char_id, self.library.starter(deck.char_id))
        if replace:
            preset = next(p for p in group["presets"] if p["id"] == self._active_preset); preset["cards"] = [c.to_dict() for c in deck.cards]
        else:
            preset = self.store.make(name.strip() if name and name.strip() else "导入的卡组", [c.to_dict() for c in deck.cards]); group["presets"].append(preset)
        self._activate(deck.char_id, preset["id"])
        self._status("卡组已导入并归入对应角色，点击「保存预设」保存到本地。")
        return deck

    def _open_import_dialog(self):
        window = self._dialog("从卡组码导入", "710x455"); self._import_window = window
        body = ttk.Frame(window, padding=20); body.pack(fill="both", expand=True)
        ttk.Label(body, text="从卡组码导入", font=(self.font_family, 18, "bold")).pack(anchor="w")
        ttk.Label(body, text="粘贴官方卡组码，成功后自动归入对应角色。编解码完全在本机完成，无需联网。", wraplength=650, foreground=MUTED).pack(anchor="w", pady=(10, 12))
        editor = self._text(body); editor.configure(height=7); editor.pack(fill="both", expand=True)
        bar = ttk.Frame(body); bar.pack(fill="x", pady=12); mode = tk.StringVar(window, "new")
        ttk.Radiobutton(bar, text="导入为新预设", variable=mode, value="new").pack(side="left", padx=(0, 18))
        ttk.Radiobutton(bar, text="覆盖当前预设（相同角色）", variable=mode, value="replace").pack(side="left")
        error_var = tk.StringVar(window); ttk.Label(body, textvariable=error_var, foreground="#b13939", wraplength=650).pack(anchor="w", pady=(0, 8))
        footer = ttk.Frame(body); footer.pack(fill="x"); ttk.Button(footer, text="取消", command=window.destroy).pack(side="right", padx=5)
        def apply():
            try: self.import_deck_code(self._get_text(editor), mode.get() == "replace")
            except Exception as error: error_var.set(f"导入失败，原卡组保留：{error}"); return
            window.destroy()
        ttk.Button(footer, text="导入卡组", style="Accent.TButton", command=apply).pack(side="right", padx=5); editor.focus_set()
        return window

    def _encode_and_show(self):
        if self.encode_deck() is not None: self.share_window.deiconify(); self.share_window.lift(); self.notebook.select(0)
