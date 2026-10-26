import unittest
import zlib
import hashlib
import json
from pathlib import Path

from czn_deckcode._compression import compress, decompress
from czn_deckcode.errors import InvalidCodeError


class CompressionTests(unittest.TestCase):
    def test_dictionary_matches_extracted_client_fragments(self):
        from czn_deckcode._compression import _DICTIONARY
        record = json.loads((Path(__file__).resolve().parents[1] / "research/samples/client_dictionary.json").read_text())
        self.assertEqual(len(_DICTIONARY), 245)
        self.assertEqual(_DICTIONARY, "".join(f["text"] for f in record["fragments"]).encode())
        self.assertEqual(hashlib.sha256(_DICTIONARY).hexdigest(), record["dictionary_sha256"])

    def test_previously_unknown_dictionary_bytes_come_from_the_client(self):
        # A complete fixed-Huffman stream: COPY length 3, distance 220, END.
        # This position was unknown before extracting the client's dictionary.
        self.assertEqual(decompress(bytes.fromhex("03fa0d00")), b"CAT")

    def test_output_limit_including_zero_and_exact_boundary(self):
        wire = compress(b"a" * 10000)
        self.assertEqual(decompress(wire, max_output=10000), b"a" * 10000)
        for limit in (0, 9999):
            with self.subTest(limit=limit), self.assertRaises(InvalidCodeError):
                decompress(wire, max_output=limit)
        self.assertEqual(decompress(compress(b""), max_output=0), b"")

    def test_extra_and_concatenated_streams_and_truncations_are_rejected(self):
        wire = compress(b"sample")
        for invalid in (wire + b"\0", wire + wire, wire[:-1], b"", b"\xff"):
            with self.subTest(data=invalid), self.assertRaises(InvalidCodeError):
                decompress(invalid)

    def test_stored_and_fixed_blocks(self):
        payload = bytes(range(256)) * 5
        for level, strategy in ((0, zlib.Z_DEFAULT_STRATEGY), (6, zlib.Z_FIXED)):
            compressor = zlib.compressobj(level, zlib.DEFLATED, -15, 8, strategy)
            wire = compressor.compress(payload) + compressor.flush()
            self.assertEqual(decompress(wire), payload)


if __name__ == "__main__":
    unittest.main()
