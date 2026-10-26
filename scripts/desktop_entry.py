"""PyInstaller entry point for the native desktop demo."""

from __future__ import annotations

import json
from pathlib import Path
import sys


def _self_test(output: Path) -> int:
    """Check the bundled codec and Tcl/Tk without leaving a visible window."""
    import tkinter as tk

    from czn_deckcode import __version__, decode, encode
    from czn_deckcode.ui import DeckApplication

    original = "v6l8cOjiNr8NyAd5bz8N5Gb4BacatRLcP_gTJk6Sy-IpI4UudHIDQRTERzqzgUXu"
    root = None
    try:
        deck = decode(original)
        if deck.char_id != "30134" or len(deck.cards) != 8 or decode(encode(deck)) != deck:
            raise RuntimeError("Bundled codec round-trip failed")
        root = tk.Tk()
        root.withdraw()
        DeckApplication(root)
        root.update_idletasks()
        result = {
            "ok": True,
            "version": __version__,
            "frozen": bool(getattr(sys, "frozen", False)),
            "cards": len(deck.cards),
            "tk_version": str(root.tk.call("info", "patchlevel")),
        }
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0
    except Exception as error:
        output.write_text(json.dumps({"ok": False, "error": str(error)}), encoding="utf-8")
        return 1
    finally:
        if root is not None:
            root.destroy()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--self-test":
        raise SystemExit(_self_test(Path(sys.argv[2])))
    from czn_deckcode.ui import main

    main()
