"""Best-effort recovery reports data loss without guessing record boundaries."""
import base64
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import zlib

from czn_deckcode import Card, Deck, InvalidCodeError, decode, decode_best_effort, encode
from czn_deckcode._obfuscation import transform
from czn_deckcode._serialization import serialize


POSSESSION_CODE = (
    "v6l88OLiNvvFzwd5bz8N7Hb2ZkVEaO1cD_GzNgXLQPTXP3rAgHsRdCQg_OUgKEA0_x52oSNoInQaHZ2bS1XlNfb5OLSWaL5W7ZmtEWtcH5uEnTu9Pq1AAVIGy2JTFi5gBb5GHGlcMKVkqgki-juTiPvIljH4PPvIlu5WPO4cnT42LEGYppiId4w14KZUvZwgYhYlH4BmSg"
)


def code_for(payload):
    compressor = zlib.compressobj(wbits=-15)
    wire = transform(b"BP\x04" + compressor.compress(payload) + compressor.flush())
    return base64.urlsafe_b64encode(wire).decode("ascii").rstrip("=")


class BestEffortTests(unittest.TestCase):
    def test_clean_recorded_exports_match_strict_decode(self):
        samples = Path(__file__).resolve().parents[1] / "research" / "samples"
        official = json.loads((samples / "official_client_codes.json").read_text(encoding="utf-8"))["cases"]
        builder = json.loads((samples / "30134.json").read_text(encoding="utf-8"))["cases"]
        codes = [case["code"] for case in official]
        codes.extend(case["result"]["code"] for case in builder.values())
        for code in codes:
            with self.subTest(code=code):
                expected = decode(code)
                result = decode_best_effort(code)
                self.assertEqual(result.deck, expected)
                self.assertEqual(result.warnings, ())
                self.assertTrue(result.complete)
                self.assertEqual(result.total_cards, len(expected.cards))

    def test_real_seasonal_card_retained_and_later_records_are_read_offline(self):
        with patch("socket.socket", side_effect=AssertionError("Network forbidden")), patch("socket.getaddrinfo", side_effect=AssertionError("DNS forbidden")):
            with self.assertRaisesRegex(InvalidCodeError, "Unsupported card talent list"):
                decode(POSSESSION_CODE)
            result = decode_best_effort(POSSESSION_CODE)
            self.assertEqual(result.deck.char_id, "30115")
            self.assertEqual(result.total_cards, 12)
            self.assertEqual(len(result.deck.cards), 12)
            self.assertTrue(result.complete)
            self.assertEqual(result.skipped_cards, 0)
            self.assertEqual(result.deck.cards[6].card_id, "card_ds04_des_30033")
            self.assertEqual([c.card_id for c in result.deck.cards[-3:]],
                             ["c_30115_srt1", "c_30115_srt3", "c_30115_srt2"])
            self.assertTrue(all(c.removed for c in result.deck.cards[-3:]))
            self.assertEqual(sum(c.duplicate for c in result.deck.cards), 3)
            self.assertEqual(len(result.warnings), 1)
            warning = result.warnings[0]
            self.assertEqual(warning.card_index, 6)
            self.assertEqual(warning.card_id, "card_ds04_des_30033")
            self.assertEqual(warning.field, "talents")
            self.assertEqual(warning.action, "dropped_option")
            self.assertIn("TALENT_POSSESSION", warning.message)
            self.assertEqual(decode(encode(result.deck)), result.deck)
            self.assertEqual(json.loads(json.dumps(result.to_dict()))["total_cards"], 12)

    def test_supported_input_has_no_warnings_and_matches_strict(self):
        deck = Deck("30134", (Card("c_30134_uni1", duplicate=True),))
        result = decode_best_effort(encode(deck))
        self.assertEqual(result.deck, deck)
        self.assertEqual(result.warnings, ())
        self.assertTrue(result.complete)
        self.assertEqual(result.total_cards, 1)

    def test_unsupported_option_between_good_cards_keeps_alignment(self):
        # Ordinary card; card with an unsupported epiphany category; removed card.
        payload = b"\x00\x03\x00\x03p_a\x02\x03p_b\x02\x02c1\x01\x03p_c"
        result = decode_best_effort(code_for(payload))
        self.assertEqual(result.deck, Deck("0", (Card("p_a"), Card("p_b"), Card("p_c", removed=True))))
        self.assertTrue(result.complete)
        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(result.warnings[0].card_index, 1)

    def test_bad_utf8_card_can_be_skipped_without_losing_next_record(self):
        payload = b"\x00\x03\x00\x03p_a\x00\x01\xff\x00\x03p_c"
        result = decode_best_effort(code_for(payload))
        self.assertEqual(result.deck, Deck("0", (Card("p_a"), Card("p_c"))))
        self.assertTrue(result.complete)
        self.assertEqual(result.skipped_cards, 1)
        self.assertEqual(result.warnings[0].action, "skipped_card")

    def test_invalid_rsp_options_and_dependent_divine_are_dropped(self):
        for spark in (b"rsp1_bad", b"rsp1_c_999_srt1", b"rsp1_p_b"):
            with self.subTest(spark=spark):
                divine = b"add_r_spark_nihilum_09"
                payload = (b"\x00\x02\x42\x03p_a\x01" + bytes([len(spark)]) + spark
                           + bytes([len(divine)]) + divine + b"\x00\x03p_c")
                result = decode_best_effort(code_for(payload))
                self.assertEqual(result.deck, Deck("0", (Card("p_a"), Card("p_c"))))
                self.assertEqual(decode(encode(result.deck)), result.deck)
                self.assertTrue(result.complete)
                self.assertEqual([w.field for w in result.warnings], ["epiphany", "divine"])

    def test_known_replication_survives_other_unknown_talents(self):
        payload = b"\x00\x01\x04\x03p_a\x02\x01x\x12TALENT_REPLICATION"
        result = decode_best_effort(code_for(payload))
        self.assertEqual(result.deck.cards, (Card("p_a", duplicate=True),))
        self.assertEqual(len(result.warnings), 1)
        self.assertEqual(decode(encode(result.deck)), result.deck)

    def test_unknown_flags_stop_at_known_prefix_without_scanning_for_next_card(self):
        payload = b"\x00\x03\x00\x03p_a\x08\x03p_b\x00\x03p_c"
        result = decode_best_effort(code_for(payload))
        self.assertEqual(result.deck, Deck("0", (Card("p_a"),)))
        self.assertFalse(result.complete)
        self.assertEqual(result.skipped_cards, 2)
        self.assertEqual(result.warnings[-1].action, "stopped")

    def test_truncated_record_and_impossible_count_preserve_good_prefix(self):
        for payload in (b"\x00\x02\x00\x03p_a\x00\x03p", b"\x00\x7f\x00\x03p_a"):
            with self.subTest(payload=payload):
                result = decode_best_effort(code_for(payload))
                self.assertEqual(result.deck, Deck("0", (Card("p_a"),)))
                self.assertFalse(result.complete)
                self.assertEqual(result.warnings[-1].action, "stopped")

    def test_outer_corruption_and_unreadable_deck_header_still_raise(self):
        for code in ("bad?code", code_for(b"\x80"), code_for(b"")):
            with self.subTest(code=code), self.assertRaises(InvalidCodeError):
                decode_best_effort(code)

    def test_trailing_data_is_reported(self):
        result = decode_best_effort(code_for(serialize(Deck("0", (Card("p_a"),))) + b"\xff"))
        self.assertEqual(result.deck.cards, (Card("p_a"),))
        self.assertFalse(result.complete)
        self.assertEqual(result.warnings[-1].field, "payload")


if __name__ == "__main__":
    unittest.main()
