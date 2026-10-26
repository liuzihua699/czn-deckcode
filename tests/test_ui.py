"""Real Tk widget tests. Run under a desktop session or Xvfb on Linux."""

import json
from pathlib import Path
import tempfile
import unittest

try:
    import tkinter as tk
except ImportError:
    tk = None

from czn_deckcode import decode

if tk is not None:
    from czn_deckcode.ui import DeckApplication, EXAMPLE_CODE


@unittest.skipIf(tk is None, "Tkinter is not installed")
class NativeUITests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(f"A graphical display or Xvfb is required: {error}")
        self.root.withdraw()
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.app = DeckApplication(self.root, Path(self.folder.name) / "decks.json")
        self.root.update_idletasks()
        try:
            self.previous_clipboard = self.root.clipboard_get()
        except tk.TclError:
            self.previous_clipboard = None

    def tearDown(self):
        if hasattr(self, "root"):
            if self.previous_clipboard is not None:
                self.root.clipboard_clear()
                self.root.clipboard_append(self.previous_clipboard)
            self.root.destroy()

    def test_user_code_decodes_into_eight_real_cards(self):
        self.app._set_text(self.app.code_text, EXAMPLE_CODE)
        deck = self.app.decode_code()
        self.assertIsNotNone(deck)
        self.assertEqual(deck.char_id, "30134")
        self.assertEqual(len(self.app.tree.get_children()), 8)
        self.assertEqual(self.app._cards[0]["cardId"], "c_30134_srt1_pot")
        self.assertEqual(self.app._cards[1]["cardId"], "c_30134_srt2_pot")

    def test_selected_card_edits_survive_real_encode_and_decode(self):
        self.app._select_card(0)
        self.app.card_vars["removed"].set(True)
        self.app._select_card(1)
        self.app.card_vars["duplicate"].set(True)
        code = self.app.encode_deck()
        self.assertIsNotNone(code)
        actual = decode(code)
        self.assertTrue(actual.cards[0].removed)
        self.assertTrue(actual.cards[1].duplicate)
        self.app.decode_code()
        self.assertTrue(self.app._cards[0]["removed"])
        self.assertTrue(self.app._cards[1]["duplicate"])

    def test_optional_fields_and_json_follow_selected_card(self):
        self.app._select_card(0)
        values = {"variantCardId": "c_30134_srt1_rsp1", "epiphanyId": "c123", "divineId": "add_r_spark_hera_1", "god": "HERA"}
        for key, value in values.items():
            self.app.card_vars[key].set(value)
        self.app._select_card(1)
        self.app._select_card(0)
        for key, value in values.items():
            self.assertEqual(self.app.card_vars[key].get(), value)
        data = json.loads(self.app._get_text(self.app.json_text))
        for key, value in values.items():
            self.assertEqual(data["cards"][0][key], value)

    def test_json_edit_apply_and_import_export(self):
        value = {"charId": "30134", "cards": [{"cardId": "c_30134_uni1", "removed": True}]}
        self.app._set_text(self.app.json_text, json.dumps(value))
        self.assertIsNotNone(self.app.apply_json())
        self.assertEqual(len(self.app.tree.get_children()), 0)  # Removed cards are hidden by default.
        self.assertEqual(self.app._cards[0]["cardId"], "c_30134_uni1")
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "构筑.json"
            self.assertEqual(self.app.export_json(target), target)
            expected = json.loads(target.read_text(encoding="utf-8"))
            self.assertTrue(expected["cards"][0]["removed"])
            self.app.load_example()
            self.assertIsNotNone(self.app.import_json(target))
            self.assertEqual(self.app._deck_from_editor().to_dict(), expected)

    def test_add_remove_and_empty_selection(self):
        self.app.add_card()
        self.app.card_vars["cardId"].set("c_30134_uni2")
        self.assertEqual(len(self.app._cards), 9)
        self.assertEqual(self.app._cards[-1]["cardId"], "c_30134_uni2")
        self.app.remove_card()
        self.assertEqual(len(self.app._cards), 8)
        for _ in range(8):
            self.app.remove_card()
        self.assertEqual(self.app.tree.get_children(), ())
        self.assertIsNone(self.app._selected)
        self.assertEqual(self.app._deck_frames, {})
        self.app.remove_card()
        self.assertIn("请先选择", self.app.status_var.get())

    def test_errors_are_visible_and_do_not_replace_existing_cards(self):
        before = self.app._deck_from_editor()
        self.app._set_text(self.app.code_text, "invalid-code")
        self.assertIsNone(self.app.decode_code())
        self.assertIn("操作失败", self.app.status_var.get())
        self.assertEqual(self.app._deck_from_editor(), before)
        self.app._set_text(self.app.json_text, "{broken")
        self.assertIsNone(self.app.apply_json())
        self.assertIn("JSON 格式有误", self.app.status_var.get())
        self.app.char_id_var.set("")
        self.assertIsNone(self.app.encode_deck())
        self.assertIn("操作失败", self.app.status_var.get())

    def test_copy_and_900_by_650_resizable_layout(self):
        self.assertEqual(self.app.copy_code(), EXAMPLE_CODE)
        self.assertEqual(self.root.clipboard_get(), EXAMPLE_CODE)
        self.root.geometry("900x650")
        self.root.update_idletasks()
        self.assertEqual(self.root.minsize(), (900, 650))
        self.assertEqual(self.root.resizable(), (1, 1))
        self.assertGreater(self.app.panes.winfo_reqwidth(), 0)
        self.assertIsNotNone(self.app.notebook)


if __name__ == "__main__":
    unittest.main()
