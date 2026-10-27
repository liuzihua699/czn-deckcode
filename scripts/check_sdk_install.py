"""Verify a separately installed SDK wheel, without source or demo imports."""
from __future__ import annotations

import argparse
import contextlib
import importlib.metadata
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
network_events = []


def offline(event, _args):
    if event.startswith("socket."):
        network_events.append(event)
        raise RuntimeError("SDK attempted network access")


sys.addaudithook(offline)
import czn_deckcode
from czn_deckcode import Card, Deck, InvalidCodeError, decode, decode_best_effort, encode
from czn_deckcode import cli

POSSESSION_CODE = (
    "v6l88OLiNvvFzwd5bz8N7Hb2ZkVEaO1cD_GzNgXLQPTXP3rAgHsRdCQg_OUgKEA0_x52oSNoInQaHZ2bS1XlNfb5OLSWaL5W7ZmtEWtcH5uEnTu9Pq1AAVIGy2JTFi5gBb5GHGlcMKVkqgki-juTiPvIljH4PPvIlu5WPO4cnT42LEGYppiId4w14KZUvZwgYhYlH4BmSg"
)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--fixtures", type=Path, default=ROOT / "research/samples/official_client_codes.json")
args = parser.parse_args()
package = Path(czn_deckcode.__file__).resolve().parent
assert not package.is_relative_to(ROOT / "src"), "Run with -I against an installed wheel"
assert not (importlib.metadata.requires("czn-deckcode") or []), "SDK must have zero runtime dependencies"
assert importlib.metadata.version("czn-deckcode") == czn_deckcode.__version__
allowed = {"__init__.py", "__main__.py", "_compression.py", "_obfuscation.py", "_serialization.py", "cli.py", "codec.py", "errors.py", "models.py", "py.typed", "__pycache__"}
assert {p.name for p in package.iterdir()} <= allowed, "Unexpected non-SDK files installed"
cases = json.loads(args.fixtures.read_text(encoding="utf-8"))["cases"]
for case in cases:
    deck = decode(case["code"])
    assert deck.to_dict() == case["expected"]
    assert decode(encode(deck)) == deck
sample = Deck("30134", [Card("c_30134_uni1")])
assert decode(encode(sample)) == sample
try:
    decode(POSSESSION_CODE)
except InvalidCodeError as error:
    assert "Unsupported card talent list" in str(error)
else:
    raise AssertionError("Strict decode must reject unsupported talents")
recovered = decode_best_effort(POSSESSION_CODE)
assert recovered.deck.char_id == "30115"
assert recovered.total_cards == len(recovered.deck.cards) == 12
assert sum(not card.removed for card in recovered.deck.cards) == 9
assert recovered.complete and recovered.skipped_cards == 0
assert recovered.deck.cards[6].card_id == "card_ds04_des_30033"
assert len(recovered.warnings) == 1
warning = recovered.warnings[0]
assert (warning.card_index, warning.card_id, warning.field, warning.action) == (
    6, "card_ds04_des_30033", "talents", "dropped_option")
assert "TALENT_POSSESSION" in warning.message
assert decode(encode(recovered.deck)) == recovered.deck
stdout = io.StringIO()
with contextlib.redirect_stdout(stdout):
    assert cli.main(["--help"]) == 0
assert "{encode,decode}" in stdout.getvalue()
assert not any(name.startswith(("demo", "PIL", "tkinter")) for name in sys.modules)
assert not network_events
print(json.dumps({"ok": True, "version": czn_deckcode.__version__, "official_codes": len(cases), "best_effort_import": True, "runtime_dependencies": [], "demo_included": False, "network_events": network_events}))
