"""Read client PLPcK tables at build time; no runtime dependency on the game.

Container layout also documented by NineS11942/ChaosZero-Toolkit (unpack_data.py).
The static resource key is unrelated to accounts or deck-code obfuscation.
"""
from __future__ import annotations

import struct

_KEY = bytes.fromhex(
    "91ae4ed4644f585162ec1bd5ef24addbaf838242aef51e97804b134ffd8ce5bb4f6e3"
    "e6451147cdf56c318e5e964c999c0d95cc860822e6b418be465d79a036dbf67ab3d"
    "a72ab1023a4561f444e5ce858d23ea10feb4899151ad7e43ff3e2419a97b4dd3af4"
    "ef5c829e5af4ace9436f6b6b6382e9dfd26642099011a4899089c9d4b9f80bbb00"
    "a4cc73255ce1f78646e91c9c12313f5d840dc51457010d37d19615bb69888b42b19"
    "e749f993c00337e9332f89b320c173a5653848788798a771739e72dbc84c79465971"
    "49bddae4e3bd1a17856c85a555cfa24f6352d005933b50042be0ba4c708de8ebb52"
    "059b2059c9bfe90d8923df74b43911bbc00bb6bfa"
)


def entries(blob: bytes):
    if not blob.startswith(b"PLPcK"):
        phases = [p for p in range(256) if bytes(blob[i] ^ _KEY[(i + p) % 256] for i in range(5)) == b"PLPcK"]
        if len(phases) != 1:
            raise ValueError("Unrecognized client table")
        phase = phases[0]
        blob = bytes(v ^ _KEY[(i + phase) % 256] for i, v in enumerate(blob))
    count = struct.unpack_from("<I", blob, 21)[0]
    if 43 + count * 5 > len(blob):
        raise ValueError("Invalid table bucket count")
    seen = set()
    for bucket in range(count):
        pos = 43 + bucket * 5
        address = (blob[pos] << 32) | struct.unpack_from("<I", blob, pos + 1)[0]
        while address:
            if address in seen: break
            if address + 15 > len(blob): raise ValueError("Invalid table node")
            seen.add(address)
            key_length = blob[address + 5]
            value_length = struct.unpack_from("<I", blob, address + 6)[0]
            following = (blob[address + 10] << 32) | struct.unpack_from("<I", blob, address + 11)[0]
            start = address + 15
            if start + key_length + value_length > len(blob): raise ValueError("Truncated table value")
            yield blob[start:start + key_length], blob[start + key_length:start + key_length + value_length]
            address = following


def table(blob: bytes) -> dict[str, dict[str, str]]:
    items = list(entries(blob))
    columns = {int(k[1:]): v.decode("utf-8") for k, v in items if k.startswith(b"\t") and k[1:].isdigit()}
    result = {}
    for key, value in items:
        if key.startswith(b"\t"): continue
        values = value.decode("utf-8").rstrip("\0").split("\0")
        result[key.decode("utf-8")] = {name: values[i] for i, name in columns.items() if i < len(values)}
    return result


def localized_text(blob: bytes) -> dict[str, str]:
    result = {}
    for key, value in entries(blob):
        if key.startswith(b"\t"): continue
        values = value.decode("utf-8").split("\0")
        if len(values) > 1: result[key.decode("utf-8")] = values[1]
    return result
