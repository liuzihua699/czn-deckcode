"""Offline Chaos Zero Nightmare deck codes. No network or runtime dependencies."""

from .codec import FORMAT_VERSION, decode, encode
from .errors import DeckCodeError, InvalidCodeError, InvalidDeckError, UnsupportedVersionError
from .models import Card, Deck

__version__ = "0.1.0a2"

__all__ = [
    "Card", "Deck", "encode", "decode", "FORMAT_VERSION",
    "DeckCodeError", "InvalidCodeError", "InvalidDeckError", "UnsupportedVersionError",
    "__version__",
]
