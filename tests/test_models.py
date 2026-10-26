import json
import unittest
from dataclasses import FrozenInstanceError

from czn_deckcode.errors import (
    DeckCodeError, InvalidCodeError, InvalidDeckError, UnsupportedVersionError,
)
from czn_deckcode.models import Card, Deck


class ModelTests(unittest.TestCase):
    def test_site_json_round_trip_preserves_card_state_and_order(self):
        data = {
            "charId": "30134",
            "cards": [
                {
                    "cardId": "c_30134_srt2", "removed": False, "duplicate": True,
                    "variantCardId": "c_30134_srt2_pot", "epiphanyId": "e:1",
                    "divineId": "d:2", "god": "future-god",
                },
                {"cardId": "c_30134_srt1", "removed": True, "duplicate": False},
            ],
        }
        deck = Deck.from_dict(json.loads(json.dumps(data)))
        self.assertEqual(deck.char_id, "30134")
        self.assertEqual(deck.cards[0].variant_card_id, "c_30134_srt2_pot")
        self.assertTrue(deck.cards[1].removed)
        self.assertEqual(deck.to_dict(), data)
        self.assertEqual(Deck.from_dict(deck.to_dict()), deck)

    def test_optional_empty_identifiers_are_normalized(self):
        card = Card.from_dict({
            "cardId": "opaque", "variantCardId": "", "epiphanyId": None,
            "divineId": "", "god": "",
        })
        self.assertIsNone(card.variant_card_id)
        self.assertIsNone(card.divine_id)
        self.assertEqual(card.god, "")
        self.assertEqual(Card.from_dict(card.to_dict()), card)

    def test_ids_are_opaque_but_must_be_strings(self):
        self.assertEqual(Card("future/card:v2").card_id, "future/card:v2")
        self.assertEqual(Deck("future-character", ()).cards, ())
        for invalid in (None, 123, True, "", "   "):
            with self.subTest(value=invalid), self.assertRaises(InvalidDeckError):
                Card(invalid)
            with self.subTest(character=invalid), self.assertRaises(InvalidDeckError):
                Deck(invalid, ())
        for attribute in ("variant_card_id", "epiphany_id", "divine_id", "god"):
            with self.subTest(attribute=attribute), self.assertRaises(InvalidDeckError):
                Card("card", **{attribute: 42})

    def test_flags_reject_truthy_values_and_null(self):
        for field in ("removed", "duplicate"):
            for invalid in (0, 1, "false", None):
                with self.subTest(field=field, value=invalid):
                    with self.assertRaises(InvalidDeckError):
                        Card.from_dict({"cardId": "card", field: invalid})

    def test_unknown_and_missing_json_fields_are_rejected(self):
        invalid_cards = (
            {}, {"card_id": "card"}, {"cardId": "card", "duplicated": False},
        )
        for data in invalid_cards:
            with self.subTest(card=data), self.assertRaises(InvalidDeckError):
                Card.from_dict(data)
        invalid_decks = (
            {}, {"charId": "character"}, {"charId": "character", "cards": [], "version": 8},
        )
        for data in invalid_decks:
            with self.subTest(deck=data), self.assertRaises(InvalidDeckError):
                Deck.from_dict(data)

    def test_nested_validation_has_card_index(self):
        with self.assertRaisesRegex(InvalidDeckError, r"cards\[1\].*removed"):
            Deck.from_dict({"charId": "character", "cards": [
                {"cardId": "first"}, {"cardId": "second", "removed": 1},
            ]})
        for cards in (None, "card", {}, [None], ["card"]):
            with self.subTest(cards=cards), self.assertRaises(InvalidDeckError):
                Deck.from_dict({"charId": "character", "cards": cards})

    def test_models_cannot_be_invalidated_by_mutating_input(self):
        source = [Card("first")]
        deck = Deck("character", source)
        source.append("invalid card")
        self.assertEqual(deck.cards, (Card("first"),))
        with self.assertRaises(FrozenInstanceError):
            deck.cards[0].removed = "invalid"
        result = deck.to_dict()
        result["cards"][0]["cardId"] = "changed"
        self.assertEqual(deck.cards[0].card_id, "first")

    def test_exception_hierarchy(self):
        self.assertTrue(issubclass(InvalidDeckError, DeckCodeError))
        self.assertTrue(issubclass(InvalidCodeError, DeckCodeError))
        self.assertTrue(issubclass(UnsupportedVersionError, InvalidCodeError))


if __name__ == "__main__":
    unittest.main()
