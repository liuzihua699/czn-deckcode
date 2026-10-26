"""PyInstaller entry point for the native desktop demo."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile


def _self_test(output: Path, official_codes: Path | None = None) -> int:
    """Check the bundled codec and Tcl/Tk without leaving a visible window."""
    network_events = []
    def forbid_network(event, _args):
        if event.startswith("socket."):
            network_events.append(event)
            raise RuntimeError("Network access forbidden during offline self-test")
    sys.addaudithook(forbid_network)
    import tkinter as tk

    from czn_deckcode import __version__, Deck, decode, encode
    from czn_deckcode.ui import DeckApplication

    original = "v6l8cOjiNr8NyAd5bz8N5Gb4BacatRLcP_gTJk6Sy-IpI4UudHIDQRTERzqzgUXu"
    root = None
    try:
        deck = decode(original)
        if deck.char_id != "30134" or len(deck.cards) != 8 or decode(encode(deck)) != deck:
            raise RuntimeError("Bundled codec round-trip failed")
        root = tk.Tk()
        root.withdraw()
        temporary = tempfile.TemporaryDirectory()
        app = DeckApplication(root, Path(temporary.name) / "decks.json")
        root.update_idletasks()
        if len(app.library.characters) < 30:
            raise RuntimeError("Bundled character catalog is missing")
        art = app.library.card("c_30134_uni1")
        if not (app.library.root / art["art"]).is_file():
            raise RuntimeError("Bundled card illustration is missing")
        app.select_character("1039")
        app._clear_deck()
        app.add_library_card("c_1039_srt4")
        generated = app.encode_deck()
        if not generated or decode(generated).cards[0].card_id != "c_1039_srt4":
            raise RuntimeError("Visual card picking did not produce a valid deck")
        image = app.images.card("c_30134_uni1")
        if image.width() != 146:
            raise RuntimeError("Bundled card image rendering failed")
        count = 0
        if official_codes is not None:
            for case in json.loads(official_codes.read_text(encoding="utf-8"))["cases"]:
                expected = Deck.from_dict(case["expected"])
                if decode(case["code"]) != expected or decode(encode(expected)) != expected:
                    raise RuntimeError(f"Official codec fixture failed: {case['name']}")
                app.import_deck_code(case["code"])
                active = sum(not card.removed for card in expected.cards)
                if app.show_removed.get() or len(app.tree.get_children()) != active or len(app._deck_frames) != active:
                    raise RuntimeError("Removed-card visibility regression")
                count += 1
        preview = app.library.description(app.library.card("c_30134_uni1_rsp2"), "繁體中文")
        if "生成3" not in preview or "卡牌1" not in preview:
            raise RuntimeError("Client numeric descriptions missing")
        result = {
            "ok": True,
            "version": __version__,
            "frozen": bool(getattr(sys, "frozen", False)),
            "cards": len(deck.cards),
            "tk_version": str(root.tk.call("info", "patchlevel")),
            "characters": len(app.library.characters),
            "catalog_cards": len(app.library.cards),
            "local_card_art": True,
            "visual_builder_roundtrip": True,
            "client_style_ui": True,
            "network_blocked": True,
            "network_events": network_events,
            "official_codes": count,
            "numeric_descriptions": True,
        }
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0
    except Exception as error:
        output.write_text(json.dumps({"ok": False, "error": str(error)}), encoding="utf-8")
        return 1
    finally:
        if root is not None:
            root.destroy()
        if "temporary" in locals():
            temporary.cleanup()


if __name__ == "__main__":
    if len(sys.argv) in (3, 5) and sys.argv[1] == "--self-test":
        fixture = Path(sys.argv[4]) if len(sys.argv) == 5 and sys.argv[3] == "--official-codes" else None
        raise SystemExit(_self_test(Path(sys.argv[2]), fixture))
    from czn_deckcode.ui import main

    main()
