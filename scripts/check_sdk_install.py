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
from czn_deckcode import Card, Deck, decode, encode
from czn_deckcode import cli

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
stdout = io.StringIO()
with contextlib.redirect_stdout(stdout):
    assert cli.main(["--help"]) == 0
assert "{encode,decode}" in stdout.getvalue()
assert not any(name.startswith(("demo", "PIL", "tkinter")) for name in sys.modules)
assert not network_events
print(json.dumps({"ok": True, "version": czn_deckcode.__version__, "official_codes": len(cases), "runtime_dependencies": [], "demo_included": False, "network_events": network_events}))
