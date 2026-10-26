"""Bounded raw DEFLATE compression used by version 4 preset codes.

Encoders are free to choose different DEFLATE matches.  Our encoder does not
reference the game's preset dictionary, so it never depends on an inferred
byte.  The decoder checks both fillings of the unobserved dictionary positions
and refuses streams whose output would depend on one of those positions.
"""
from __future__ import annotations

import zlib

from .errors import InvalidCodeError

# Negative offsets are relative to the end of the game's preset dictionary.
# These runs are supported by chosen-plaintext LZ77 copy observations.
_KNOWN_RUNS = {
    -238: b"REPLICATIONTALENT_",
    -159: b"rsp1_c_rsp2_c_rsp3_c_rsp4_c_rsp5_c_",
    -124: b"add_r_spark",
    -102: b"_assault_",
    -93: b"card_c__srt1_srt2_srt3_srt4_uni1_uni2_uni3_uni4",
    -46: b"_rsp1_",
    -40: b"rsp2_rsp3_rsp4_rsp5_lbk_pot_eps_col_col2",
}


def _dictionary(fill: int) -> bytes:
    result = bytearray([fill]) * 238
    for offset, run in _KNOWN_RUNS.items():
        at = len(result) + offset
        result[at : at + len(run)] = run
    return bytes(result)


_DICTIONARY = _dictionary(0)
_ALTERNATE_DICTIONARY = _dictionary(255)


def compress(payload: bytes) -> bytes:
    """Return a valid raw DEFLATE stream without external dictionary matches."""
    compressor = zlib.compressobj(level=9, wbits=-15)
    return compressor.compress(payload) + compressor.flush()


def _inflate(data: bytes, dictionary: bytes, limit: int) -> bytes:
    decompressor = zlib.decompressobj(wbits=-15, zdict=dictionary)
    try:
        result = decompressor.decompress(data, limit + 1)
    except zlib.error as exc:
        raise InvalidCodeError("Invalid DEFLATE stream or unsupported dictionary reference") from exc
    if len(result) > limit or decompressor.unconsumed_tail:
        raise InvalidCodeError("Decoded deck exceeds the configured size limit")
    if not decompressor.eof:
        raise InvalidCodeError("Truncated DEFLATE stream")
    if decompressor.unused_data:
        raise InvalidCodeError("Unexpected bytes after the DEFLATE stream")
    return result


def decompress(data: bytes, *, max_output: int = 1_048_576) -> bytes:
    """Inflate a single complete stream, rejecting unverified dictionary bytes."""
    if not isinstance(max_output, int) or isinstance(max_output, bool) or max_output < 0:
        raise ValueError("max_output must be a non-negative integer")
    result = _inflate(data, _DICTIONARY, max_output)
    alternate = _inflate(data, _ALTERNATE_DICTIONARY, max_output)
    if result != alternate:
        raise InvalidCodeError("This code references an unverified preset dictionary entry")
    return result
