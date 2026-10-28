"""Client asset integrity and real visual picking/editing workflows."""
import copy
from pathlib import Path
import unittest
import tempfile
import json
import base64
import zlib
from unittest.mock import patch

from czn_deckcode import Card, Deck, decode, encode
from czn_deckcode._obfuscation import transform
from demo.library import CardLibrary
from demo.presets import (
    PresetStore, USER_ADDED_FIELD, codec_card_rows, is_user_added_card,
    remove_user_added_card,
)


POSSESSION_CODE = (
    "v6l88OLiNvvFzwd5bz8N7Hb2ZkVEaO1cD_GzNgXLQPTXP3rAgHsRdCQg_OUgKEA0_x52oSNoInQaHZ2bS1XlNfb5OLSWaL5W7ZmtEWtcH5uEnTu9Pq1AAVIGy2JTFi5gBb5GHGlcMKVkqgki-juTiPvIljH4PPvIlu5WPO4cnT42LEGYppiId4w14KZUvZwgYhYlH4BmSg"
)
MEMORY_CARD_CODE = (
    "v6l8wGe1b9OIeyLI25-9XXDFHLIGfrAMevz3PYh69_HWM3fw_K6d4g6xe0wnocB3IES3jmorNuGc0ZZoGxcYMxa1MLSWZf7SOJU5_aHxeeYiG0lTq2Xw9QMyRdOZW0zfnn6IVrIe6GEd5P8nfRPdSm1mxVmP2cODy0ZhGbMupAzHc6hu3nmjdhAIowT_1uEr8yC5fXEXTDw"
)


class LocalCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.library = CardLibrary()

    def test_client_card_ids_resolve_to_their_actual_artwork(self):
        self.assertEqual(self.library.card("c_30134_uni1")["art"], "cards/unique_30134_02.png")
        self.assertEqual(self.library.card("c_1039_srt4")["name"], "水之根源")
        self.assertEqual(self.library.character("30134")["name"], "羅斯薇瑟")

    def test_every_selectable_card_and_character_has_a_local_png(self):
        self.assertGreaterEqual(len(self.library.characters), 39)
        for item in [*self.library.characters, *(c for c in self.library.cards.values() if c["pickable"])]:
            with self.subTest(id=item["id"]):
                path = self.library.root / item["art"]
                self.assertTrue(path.is_file())
                with path.open("rb") as stream:
                    self.assertEqual(stream.read(8), b"\x89PNG\r\n\x1a\n")

    def test_filtering_keeps_roles_separate_and_supports_both_chinese_names(self):
        result = self.library.available("30134", "character")
        self.assertEqual(len(result), 8)
        self.assertTrue(all(c["owner"] == "30134" for c in result))
        self.assertEqual([c["id"] for c in self.library.available("30134", "character", "剑之共鸣")], ["c_30134_uni1"])
        self.assertTrue(all(c["group"] == "memory" for c in self.library.available("1039", "memory")))

    def test_imported_memory_cards_and_duplicate_copies_are_classified_as_added(self):
        deck = decode(MEMORY_CARD_CODE)
        rows = [card.to_dict() for card in deck.cards]
        flags = self.library.user_added_flags(rows, deck.char_id)
        self.assertEqual(flags, [False, False, False, True, True, True, False, False, False, False, False, True, True, True, True])

    def test_unique_general_and_divine_are_distinct_client_libraries(self):
        row = {"cardId": "c_30134_uni1"}
        self.assertEqual([c["id"] for c in self.library.unique_variants(row)], [f"c_30134_uni1_rsp{i}" for i in range(1, 6)])
        for group in ("epiphany", "divine"):
            choices = self.library.modifier_choices(row, group)
            self.assertTrue(choices)
            self.assertTrue(all(m["group"] == group for m in choices))
            for item in choices:
                constraints = item["constraints"]
                self.assertLessEqual(int(constraints["target_card_cost_min"]), 1)
                self.assertGreaterEqual(int(constraints["target_card_cost_max"]), 1)

    def test_client_markup_is_not_exposed_in_card_effects(self):
        text = self.library.effects({"cardId": "c_30134_uni1", "variantCardId": "c_30134_uni1_rsp2"}, "繁體中文")
        for markup in ("[fc]", "[/]", "$", "<br>", "#result_"):
            self.assertNotIn(markup, text)
        self.assertIn("\n", text)

    def test_client_numbers_are_resolved_in_both_chinese_displays(self):
        for language in ("繁體中文", "简体中文"):
            sword = self.library.effects({"cardId": "c_30134_uni1", "variantCardId": "c_30134_uni1_rsp2"}, language)
            self.assertIn("3", sword)
            self.assertIn("1", sword)
            self.assertNotIn("X", sword)
            self.assertNotIn("未求值", sword)
            attack = self.library.description(self.library.card("c_30134_srt4_rsp5"), language)
            self.assertIn("400%", attack)
            self.assertIn("120%", attack)
            self.assertIn("X", attack)  # X cost is an actual game mechanic.
            memory = self.library.description(self.library.card("card_ds05_b_c1_4_1"), language)
            self.assertIn("10%", memory)
            self.assertIn("25%", memory)
            self.assertNotIn("未求值", memory)
            common = self.library.description(self.library.modifier_by_id["c03012"], language)
            self.assertIn("3", common)
            self.assertNotIn("X", common)


class PermanentDeleteLogicTests(unittest.TestCase):
    def test_only_a_selected_user_added_record_enables_permanent_delete(self):
        rows = [{"cardId": "built-in"}, {"cardId": "added", USER_ADDED_FIELD: True}]
        self.assertFalse(is_user_added_card(rows, 0))
        self.assertTrue(is_user_added_card(rows, 1))
        self.assertFalse(is_user_added_card(rows, None))

    def test_delete_removes_only_the_selected_added_record(self):
        rows = [
            {"cardId": "first"},
            {"cardId": "added", USER_ADDED_FIELD: True},
            {"cardId": "last"},
        ]
        self.assertEqual(remove_user_added_card(rows, 1), [rows[0], rows[2]])
        self.assertIsNone(remove_user_added_card(rows, 0))
        self.assertEqual(len(rows), 3)

    def test_preset_store_keeps_provenance_but_codec_rows_drop_it(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "decks.json"
            store = PresetStore(path)
            group = store.ensure("30134", [{"cardId": "c_30134_srt1"}])
            group["presets"][0]["cards"].append({"cardId": "c_30134_uni1", USER_ADDED_FIELD: True})
            store.write()

            reopened = PresetStore(path)
            cards = reopened.data["characters"]["30134"]["presets"][0]["cards"]
            self.assertTrue(cards[-1][USER_ADDED_FIELD])
            self.assertEqual(codec_card_rows(cards)[-1], {"cardId": "c_30134_uni1"})


try:
    import tkinter as tk
except ImportError:
    tk = None


@unittest.skipIf(tk is None, "Tkinter is unavailable")
class VisualWorkflowTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(str(error))
        self.root.withdraw()
        from demo.ui import DeckApplication
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.app = DeckApplication(self.root, Path(self.folder.name) / "decks.json")
        self.root.update_idletasks()

    def tearDown(self):
        if hasattr(self, "root"):
            self.root.destroy()

    def test_best_effort_import_preserves_cards_suffix_and_visible_report(self):
        self.app._set_text(self.app.code_text, POSSESSION_CODE)
        with patch("socket.socket", side_effect=AssertionError("Network access forbidden")), patch("socket.getaddrinfo", side_effect=AssertionError("DNS forbidden")):
            deck = self.app.decode_code()
        self.assertIsNotNone(deck)
        self.assertEqual(deck.char_id, "30115")
        self.assertEqual(len(deck.cards), 12)
        self.assertEqual(sum(not c.removed for c in deck.cards), 9)
        self.assertEqual(deck.cards[6].card_id, "card_ds04_des_30033")
        self.assertEqual([c.card_id for c in deck.cards[-3:]], ["c_30115_srt1", "c_30115_srt3", "c_30115_srt2"])
        self.assertTrue(all(c.removed for c in deck.cards[-3:]))
        self.assertEqual(len(self.app.tree.get_children()), 9)
        self.assertIn("未能保留", self.app.status_var.get())
        result = self.app.last_import_result
        self.assertTrue(result.warnings)
        cleaned = self.app._get_text(self.app.code_text)
        self.assertNotEqual(cleaned, POSSESSION_CODE)
        self.assertEqual(decode(cleaned), deck)
        self.assertEqual(decode(self.app.encode_deck()), deck)
        self.app.save_presets()
        self.assertIs(self.app.last_import_result, result)
        self.assertTrue(self.app.import_report_button.instate(["!disabled"]))
        self.assertIn("有丢弃", self.app.import_report_button.cget("text"))
        report = self.app._open_import_report()
        self.root.update_idletasks()
        self.assertTrue(report.winfo_exists())
        def text_widgets(widget):
            yield widget
            for child in widget.winfo_children():
                yield from text_widgets(child)
        report_text = "\n".join(widget.get("1.0", "end-1c") for widget in text_widgets(report) if isinstance(widget, tk.Text))
        self.assertIn("TALENT_POSSESSION", report_text)
        self.assertIn("第 7 条卡牌", report_text)
        report.destroy()
        from demo.presets import PresetStore
        restored = PresetStore(self.app.store.path)
        group = restored.data["characters"]["30115"]
        preset = next(p for p in group["presets"] if p["id"] == group["active"])
        self.assertEqual(Deck.from_dict({"charId": "30115", "cards": preset["cards"]}), deck)

    def test_best_effort_failure_or_empty_recovery_keeps_presets_and_report(self):
        self.app.import_deck_code(POSSESSION_CODE)
        before = copy.deepcopy(self.app.store.data)
        current = self.app._deck_from_editor()
        report = self.app.last_import_result
        compressor = zlib.compressobj(wbits=-15)
        # A valid BP4 envelope whose sole record starts with unsupported flags.
        payload = b"\xa3\xeb\x01\x01\x08\x03p_a"
        empty_recovery_code = base64.urlsafe_b64encode(transform(b"BP\x04" + compressor.compress(payload) + compressor.flush())).decode().rstrip("=")
        for code in ("invalid-code", empty_recovery_code):
            with self.subTest(code=code):
                self.app._set_text(self.app.code_text, code)
                self.assertIsNone(self.app.decode_code())
                self.assertIn("操作失败", self.app.status_var.get())
                self.assertEqual(self.app._deck_from_editor(), current)
                self.assertEqual(self.app.store.data, before)
                self.assertIs(self.app.last_import_result, report)

    def test_choose_role_add_cards_and_export_the_actual_deck(self):
        self.app.select_character("1039")
        self.app._clear_deck()
        self.app.add_library_card("c_1039_srt4")
        self.app.add_library_card("c_1039_srt4")
        self.app.add_library_card("card_ds05_b_c1_1_1")
        restored = decode(self.app.encode_deck())
        self.assertEqual(restored.char_id, "1039")
        self.assertEqual([c.card_id for c in restored.cards], ["c_1039_srt4", "c_1039_srt4", "card_ds05_b_c1_1_1"])
        self.assertTrue(restored.cards[1].duplicate)
        self.assertEqual(self.app.tree.item("0", "values")[0], "水之根源")
        self.assertTrue(self.app.tree.item("0", "image"))

    def test_switching_roles_restores_their_unsaved_drafts(self):
        self.app.add_library_card("c_30134_uni1")
        ross = copy.deepcopy(self.app._cards)
        self.app.select_character("1039")
        self.app._clear_deck()
        self.app.add_library_card("c_1039_uni4")
        self.app.select_character("30134")
        self.assertEqual(self.app._cards, ross)
        self.app.select_character("1039")
        self.assertEqual(self.app._cards[0]["cardId"], "c_1039_uni4")

    def test_variant_removal_order_and_duplication_update_the_same_model(self):
        self.app.show_removed.set(True)
        self.app._select_card(4)
        self.app.set_variant("c_30134_uni1_rsp2")
        self.app._toggle_removed()
        self.app._move_card(-1)
        self.assertEqual(self.app._selected, 3)
        self.app._duplicate_card()
        result = decode(self.app.encode_deck())
        self.assertTrue(result.cards[3].removed)
        self.assertEqual(result.cards[3].variant_card_id, "c_30134_uni1_rsp2")
        self.assertTrue(result.cards[4].duplicate)
        self.assertFalse(result.cards[4].removed)

    def test_foreign_role_card_is_not_added_and_locale_updates_names(self):
        original = copy.deepcopy(self.app._cards)
        self.app.add_library_card("c_1039_srt4")
        self.assertEqual(self.app._cards, original)
        self.app.language_var.set("简体中文")
        self.assertEqual(self.app.tree.item("4", "values")[0], "剑之共鸣")
        self.assertIn("罗斯薇瑟", self.app.character_label.cget("text"))

    def test_card_detail_uses_local_art_and_retains_variant_edits(self):
        self.app._select_card(4)
        self.app._open_card_details()
        window = self.app._detail_window
        self.assertTrue(window.winfo_exists())
        self.app.set_variant("c_30134_uni1_rsp2")
        self.root.update_idletasks()
        self.assertEqual(self.app._cards[4]["variantCardId"], "c_30134_uni1_rsp2")
        window.destroy()
        self.assertIsNone(self.app._detail_window)

    def test_role_selection_keeps_widget_order_and_existing_buttons(self):
        before = [(key, str(button)) for key, button in self.app.character_buttons.items()]
        self.app.select_character("1039")
        self.app.select_character("30134")
        self.assertEqual([(key, str(button)) for key, button in self.app.character_buttons.items()], before)
        self.assertEqual([key for key, _ in before], [c["id"] for c in self.app.library.characters])

    def test_multiple_role_presets_survive_a_new_application(self):
        from demo.ui import DeckApplication
        first = self.app._active_preset
        self.app.rename_preset("明暗一刀")
        self.app._select_card(4)
        self.app.set_variant("c_30134_uni1_rsp2")
        copy_id = self.app.copy_preset()
        self.app.rename_preset("剑穗循环")
        self.app._clear_deck()
        self.app.add_library_card("c_30134_uni1")
        self.app.switch_preset(first)
        self.assertEqual(len(self.app._cards), 8)
        self.app.switch_preset(copy_id)
        self.assertEqual(len(self.app._cards), 1)
        self.app.select_character("1039")
        self.app.rename_preset("补 AP")
        self.app.language_var.set("简体中文")
        path = self.app.save_presets()
        self.assertTrue(path.is_file())
        self.root.destroy()
        self.root = tk.Tk(); self.root.withdraw()
        self.app = DeckApplication(self.root, path)
        self.assertEqual(self.app.char_id_var.get(), "1039")
        self.assertEqual(self.app.language_var.get(), "简体中文")
        self.assertEqual(self.app.preset_name_var.get(), "补 AP")
        self.app.select_character("30134")
        self.assertEqual(self.app._active_preset, copy_id)
        self.assertEqual(self.app.preset_name_var.get(), "剑穗循环")
        self.assertEqual(len(self.app._cards), 1)
        self.app.switch_preset(first)
        self.assertEqual(self.app._cards[4]["variantCardId"], "c_30134_uni1_rsp2")

    def test_code_import_groups_by_owner_and_failure_keeps_all_presets(self):
        before = copy.deepcopy(self.app.store.data)
        rows = copy.deepcopy(self.app._cards)
        with self.assertRaises(Exception): self.app.import_deck_code("invalid-code")
        self.assertEqual(self.app.store.data, before)
        self.assertEqual(self.app._cards, rows)
        code = encode(Deck("1039", (Card("c_1039_srt4"),)))
        with self.assertRaises(ValueError): self.app.import_deck_code(code, replace=True)
        self.assertEqual(self.app.store.data, before)
        self.app.import_deck_code(code, name="水之根源构筑")
        self.assertEqual(self.app.char_id_var.get(), "1039")
        self.assertEqual(self.app.preset_name_var.get(), "水之根源构筑")
        self.assertEqual(len(self.app._group()["presets"]), 4)
        self.app.import_deck_code(code, replace=True)
        self.assertEqual(len(self.app._group()["presets"]), 4)
        self.app.select_character("30134")
        self.assertEqual(self.app._cards, rows)

    def test_general_and_divine_effects_roundtrip_and_clear_without_losing_card(self):
        self.app._select_card(4)
        self.app.set_variant("c_30134_uni1_rsp2")
        divine = "add_r_spark_nihilum_01"
        self.assertTrue(self.app.apply_modifier("divine", divine))
        result = decode(self.app.encode_deck())
        self.assertEqual(result.cards[4].divine_id, divine)
        self.assertEqual(result.cards[4].god, "NIHILUM")
        general = self.app.library.modifier_choices({"cardId": "c_30134_uni1"}, "epiphany")[0]["id"]
        self.app.apply_modifier("epiphany", general)
        result = decode(self.app.encode_deck())
        self.assertIsNone(result.cards[4].variant_card_id)
        self.assertEqual(result.cards[4].epiphany_id, general)
        self.app.apply_modifier("epiphany", None)
        self.assertNotIn("divineId", self.app._cards[4])
        self.assertNotIn("epiphanyId", self.app._cards[4])
        self.assertEqual(self.app._cards[4]["cardId"], "c_30134_uni1")

    def test_unique_divine_general_and_import_dialogs_open_with_real_data(self):
        self.app._select_card(4)
        self.app.set_variant("c_30134_uni1_rsp2")
        for group in ("unique", "divine", "epiphany"):
            window = self.app._open_epiphany(group)
            self.root.update_idletasks()
            self.assertTrue(window.winfo_exists())
            window.destroy()
        window = self.app._open_import_dialog()
        self.assertTrue(window.winfo_exists())
        window.destroy()

    def test_renaming_copying_and_deleting_a_preset_do_not_alias_cards(self):
        first = self.app._active_preset
        self.app.copy_preset()
        self.app._select_card(0)
        self.app.card_vars["removed"].set(True)
        self.app.switch_preset(first)
        self.assertFalse(self.app._cards[0]["removed"])
        self.app.delete_preset()
        self.assertNotIn(first, [p["id"] for p in self.app._group()["presets"]])
        self.app.save_presets()
        self.assertTrue(self.app.store.path.is_file())

    def test_removed_cards_stay_hidden_until_the_user_checks_the_filter(self):
        self.assertFalse(self.app.show_removed.get())
        self.app._select_card(4)
        self.app._toggle_removed()
        self.assertFalse(self.app.show_removed.get())
        self.assertTrue(self.app._cards[4]["removed"])
        self.assertNotIn(4, self.app._deck_frames)
        self.assertNotIn("4", self.app.tree.get_children())
        self.app.show_removed.set(True)
        self.app._removed_filter_changed()
        self.assertIn(4, self.app._deck_frames)
        self.assertIn("4", self.app.tree.get_children())
        self.app._select_card(4)
        self.app._toggle_removed()
        self.assertFalse(self.app._cards[4]["removed"])
        self.assertTrue(self.app.show_removed.get())
        self.app.show_removed.set(False)
        self.app._removed_filter_changed()
        self.assertIn("4", self.app.tree.get_children())

    def test_permanent_delete_is_limited_to_user_added_cards(self):
        self.assertTrue(self.app.delete_card_button.instate(["disabled"]))
        self.app._select_card(0)
        self.assertTrue(self.app.delete_card_button.instate(["disabled"]))

        self.app.add_library_card("c_30134_uni1")
        added_index = len(self.app._cards) - 1
        self.assertTrue(self.app._cards[added_index]["_userAdded"])
        self.assertTrue(self.app.delete_card_button.instate(["!disabled"]))

        self.app.save_presets()
        preset_id = self.app._active_preset
        self.app._activate("30134", preset_id)
        self.app._select_card(added_index)
        self.assertTrue(self.app.delete_card_button.instate(["!disabled"]))

        exported = decode(self.app.encode_deck())
        self.assertEqual(len(exported.cards), len(self.app._cards))
        self.assertNotIn("_userAdded", self.app._get_text(self.app.json_text))

        self.app.delete_user_added_card()
        self.assertEqual(len(self.app._cards), 8)
        self.assertEqual(self.app._selected, added_index - 1)
        self.assertTrue(self.app.delete_card_button.instate(["disabled"]))

    def test_imported_memory_card_can_be_permanently_deleted(self):
        self.app.import_deck_code(MEMORY_CARD_CODE)
        memory_index = next(
            i for i, row in enumerate(self.app._cards)
            if self.app.library.card(row).get("group") == "memory"
        )
        self.app._select_card(memory_index)
        self.assertEqual(self.app.delete_card_button.cget("text"), "删除卡牌")
        self.assertTrue(self.app.delete_card_button.instate(["!disabled"]))

        self.assertTrue(self.app.delete_user_added_card())
        self.assertEqual(len(self.app._cards), 14)
        self.assertEqual(self.app._cards[memory_index]["_userAdded"], True)
        self.assertTrue(self.app.delete_card_button.instate(["!disabled"]))

    def test_imports_all_official_codes_without_network_and_hides_removed_rows(self):
        path = Path(__file__).resolve().parents[1] / "research/samples/official_client_codes.json"
        cases = json.loads(path.read_text(encoding="utf-8"))["cases"]
        with patch("socket.socket", side_effect=AssertionError("Network access forbidden")), patch("socket.getaddrinfo", side_effect=AssertionError("DNS forbidden")):
            for case in cases:
                with self.subTest(name=case["name"]):
                    self.app.import_deck_code(case["code"])
                    expected = case["expected"]
                    active = sum(not c["removed"] for c in expected["cards"])
                    self.assertFalse(self.app.show_removed.get())
                    self.assertEqual(len(self.app.tree.get_children()), active)
                    self.assertEqual(len(self.app._deck_frames), active)
                    self.assertEqual(self.app._deck_from_editor().to_dict(), expected)
                    self.assertEqual(decode(self.app.encode_deck()).to_dict(), expected)
        # Replacing a deck must also delete detached rows, avoiding duplicate Tk IDs.
        for _ in range(3):
            self.app.select_character("30134")
            self.app.select_character("1039")


if __name__ == "__main__":
    unittest.main()
