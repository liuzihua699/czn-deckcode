import base64
import json
from pathlib import Path
import random
import unittest
from unittest.mock import patch
import zlib

from czn_deckcode import (
    Card, Deck, InvalidCodeError, InvalidDeckError, UnsupportedVersionError, decode, encode,
)
from czn_deckcode._obfuscation import transform


SAMPLES = Path(__file__).resolve().parents[1] / "research" / "samples"
BUILD1_CODE = "v6l8cOjiNr8NyAd5bz8N5Gb4BacatRLcP_gTJk6Sy-IpI4UudHIDQRTERzqzgUXu"
BUILD2_CODE = "v6l8cOjiNr8NyAd5bz8N5Gb4OqcatZtbvCimK8hSEmQXL6ecqhDgm1Wc7cJpLBLu"


def normalized_request(value):
    """Independently express BP's builder normalization for fixture comparisons."""
    cards = []
    for row in value["cards"]:
        row = dict(row)
        variant = row.get("variantCardId")
        if variant and variant.endswith(("_pot", "_lbk")):
            row["cardId"] = row.pop("variantCardId")
        if variant and "_rsp" in variant:
            row.pop("epiphanyId", None)
        divine = row.get("divineId")
        if divine:
            row["god"] = divine.split("_spark_", 1)[1].rsplit("_", 1)[0].upper()
        else:
            row.pop("god", None)
        cards.append(Card.from_dict(row))
    return Deck(str(int(value["charId"])), cards)


def wire_code(message):
    return base64.urlsafe_b64encode(transform(message)).decode().rstrip("=")


class CodecTests(unittest.TestCase):
    def test_official_client_exports_include_memory_and_removed_cards_offline(self):
        cases = json.loads((SAMPLES / "official_client_codes.json").read_text(encoding="utf-8"))["cases"]
        self.assertEqual(len(cases), 7)
        with patch("socket.socket", side_effect=AssertionError("Network access forbidden")), patch("socket.getaddrinfo", side_effect=AssertionError("DNS forbidden")):
            for case in cases:
                with self.subTest(name=case["name"]):
                    expected = Deck.from_dict(case["expected"])
                    actual = decode(case["code"])
                    self.assertEqual(actual, expected)
                    self.assertEqual(decode(encode(actual)), expected)
        original = decode(cases[0]["code"])
        self.assertEqual(original.cards[-1].card_id, "card_ds05_b_c1_4_1")
        self.assertEqual(sum(c.removed for c in original.cards), 3)
        self.assertEqual(sum(c.duplicate for c in original.cards), 3)
        without_memory = next(c for c in cases if c["name"] == "ross_without_memory")
        self.assertEqual(original.cards[:-1], decode(without_memory["code"]).cards)

    def test_locally_generated_codes_previously_imported_by_website(self):
        record = json.loads((SAMPLES / "local_export_verification.json").read_text(encoding="utf-8"))
        self.assertEqual(len(record["cases"]), 8)
        for sample in record["cases"]:
            with self.subTest(name=sample["name"]):
                self.assertTrue(sample["matches"])
                self.assertEqual(sample["http_status"], 200)
                restored = decode(sample["local_code"])
                self.assertEqual(restored, Deck.from_dict(sample["local_decoded"]))
                self.assertEqual(decode(encode(sample["input"])), restored)

    def test_both_original_user_codes(self):
        first = decode(BUILD1_CODE)
        self.assertEqual(first.char_id, "30134")
        self.assertEqual(len(first.cards), 8)
        self.assertEqual([card.card_id for card in first.cards[:2]], ["c_30134_srt1_pot", "c_30134_srt2_pot"])
        self.assertFalse(any(card.removed for card in first.cards))
        second = decode(BUILD2_CODE)
        self.assertEqual(second.cards[0].card_id, "c_30134_srt2_pot")
        self.assertEqual(second.cards[-1], Card("c_30134_srt1", removed=True))
        self.assertEqual(len(second.cards), 8)

    def test_all_61_builder_samples(self):
        cases = json.loads((SAMPLES / "30134.json").read_text(encoding="utf-8"))["cases"]
        self.assertEqual(len(cases), 61)
        for name, sample in cases.items():
            with self.subTest(name=name):
                expected = normalized_request(sample["request"])
                restored = decode(sample["result"]["code"])
                self.assertEqual(restored, expected)
                self.assertEqual(decode(encode(sample["request"])), expected)
                self.assertEqual(decode(encode(restored)), expected)

    def test_long_independent_samples_verify_entire_mask_and_dynamic_deflate(self):
        for name in ("stream_short", "stream_medium", "stream_long"):
            for sample in json.loads((SAMPLES / (name + ".json")).read_text(encoding="utf-8")):
                code = sample.get("result", {}).get("code")
                if not code:
                    continue
                with self.subTest(name=name, cards=len(sample["request"]["cards"])):
                    expected = Deck.from_dict(sample["request"])
                    self.assertEqual(decode(code), expected)
                    self.assertEqual(decode(encode(expected)), expected)
        longest = json.loads((SAMPLES / "stream_long.json").read_text())[2]
        self.assertGreater(len(base64.urlsafe_b64decode(longest["result"]["code"] + "===")), 1600)

    def test_multi_character_single_card_matrix(self):
        cases = json.loads((SAMPLES / "matrix.json").read_text(encoding="utf-8"))
        count = 0
        for name, code in cases.items():
            if not code.startswith("v6l8") or name.endswith("|FULL"):
                continue
            owner, suffix = name.split("|")
            with self.subTest(name=name):
                expected = Deck(owner, [Card(f"c_{owner}_{suffix}")])
                self.assertEqual(decode(code), expected)
                self.assertEqual(decode(encode(expected)), expected)
            count += 1
        self.assertEqual(count, 73)

    def test_all_successful_field_samples_have_identical_binary_payloads(self):
        from czn_deckcode._compression import decompress
        from czn_deckcode._serialization import serialize
        count = 0
        for sample in json.loads((SAMPLES / "fields.json").read_text(encoding="utf-8")):
            code = (sample.get("result") or {}).get("code")
            if not code:
                continue
            with self.subTest(name=sample["name"]):
                wire = base64.urlsafe_b64decode(code + "=" * (-len(code) % 4))
                self.assertEqual(decompress(transform(wire)[3:]), serialize(Deck.from_dict(sample["request"])))
                restored = decode(code)
                self.assertEqual(decode(encode(sample["request"])), restored)
            count += 1
        self.assertGreaterEqual(count, 20)

    def test_padded_and_surrounding_whitespace(self):
        code = encode(Deck("30134", [Card("c_30134_srt1")]))
        self.assertEqual(decode(code), decode(" \n" + code + "=" * (-len(code) % 4) + "\t"))

    def test_no_network_is_needed(self):
        deck = Deck("30134", [Card("c_30134_srt1", duplicate=True)])
        with patch("socket.socket", side_effect=AssertionError("Network access forbidden")):
            self.assertEqual(decode(encode(deck)), deck)
            self.assertEqual(decode(BUILD1_CODE).char_id, "30134")

    def test_varied_new_decks_are_not_sample_lookup(self):
        rng = random.Random(21431)
        for _ in range(80):
            owner = str(rng.choice([0, 1003, 1055, 30134, 4294967295]))
            cards = [
                Card(f"c_{owner}_srt{rng.randint(1, 4)}", removed=bool(rng.getrandbits(1)), duplicate=bool(rng.getrandbits(1)))
                for _ in range(rng.randint(0, 35))
            ]
            deck = Deck(owner, cards)
            self.assertEqual(decode(encode(deck)), deck)

    def test_malformed_base64_and_headers(self):
        for code in (None, 1, "", " ", "A", "A===", "a+b/", "v6l8=", "v6l8\nAAAA", "AB"):
            with self.subTest(code=code):
                with self.assertRaises(InvalidCodeError):
                    decode(code)
        with self.assertRaises(InvalidCodeError):
            decode(wire_code(b"XX\x04\x00"))
        with self.assertRaises(UnsupportedVersionError):
            decode(wire_code(b"BP\x05\x00"))

    def test_invalid_compression_and_payload(self):
        with self.assertRaises(InvalidCodeError):
            decode(wire_code(b"BP\x04not deflate"))
        for data in (b"", b"\x80", b"\x00\x01", b"\x00\x00\x01"):
            compressor = zlib.compressobj(wbits=-15)
            compressed = compressor.compress(data) + compressor.flush()
            with self.subTest(payload=data), self.assertRaises(InvalidCodeError):
                decode(wire_code(b"BP\x04" + compressed))

    def test_card_order_changes_code(self):
        cards = [Card("c_30134_srt1"), Card("c_30134_uni4")]
        self.assertNotEqual(encode(Deck("30134", cards)), encode(Deck("30134", cards[::-1])))


if __name__ == "__main__":
    unittest.main()
