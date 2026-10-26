# Client preset dictionary (245 bytes)

The current BP4 dictionary has been extracted from the installed client's
`game/build_preset_codec.js` compiled module. It consists of these ASCII
fragments, in order:

```text
TALENT_REPLICATIONTALENT_CATEGORY_UNIQUECATEGORY_ENCOUNTERCATEGORY_PUBLICCATEGORY_NONE
rsp1_c_rsp2_c_rsp3_c_rsp4_c_rsp5_c_add_r_sparklbk_c_pot_c_assault_
card_c__srt1_srt2_srt3_srt4_uni1_uni2_uni3_uni4_rsp1_rsp2_rsp3_rsp4_rsp5_lbk_pot_eps_col_col2
```

The line breaks are not part of the dictionary. The concatenation is exactly
245 bytes, SHA256 `7cad876fad355e347395665d045572f20867e8830a6d25dd6837a13b1bfc7d9c`.
Fragment offsets in the 22,168-byte module are 909, 1009 and 1093. Module SHA256:
`5e61e139716abd1e335c5542ee5e74a96594cf9114281f8188facee8f70f316f`.
Machine-readable evidence is in `research/samples/client_dictionary.json`.

All previously inferred runs below match this dictionary byte for byte. Seven
real game exports, including memory cards, now decode and re-encode locally
without any network access. Fixtures are in
`research/samples/official_client_codes.json`; one independently checked pair
differs only by the final memory card. The payload contains removed cards as
well as active ones; the UI hides removed records by default without deleting
them from exports.

The earlier 238-byte partial dictionary lacked its leading `TALENT_` and two
internal spans. This caused `invalid distance too far back` on official codes.
The decoder now uses the extracted bytes directly, retaining truncation,
trailing-input and output-size checks. The encoder still emits self-contained
DEFLATE streams. Support is for BP4; this does not promise future versions.

## Earlier chosen-plaintext evidence

The version 4 payload is raw DEFLATE and may use a preset dictionary. Dictionary
positions below are negative offsets relative to the dictionary's end. A copy
at output position `p` with distance `d` refers to dictionary position `p - d`
when that value is negative.

Recovered byte runs:

| Offset | Bytes |
| --- | --- |
| -238 | `REPLICATIONTALENT_` |
| -159 | `rsp1_c_rsp2_c_rsp3_c_rsp4_c_rsp5_c_` |
| -124 | `add_r_spark` |
| -102 | `_assault_` |
| -93 | `card_c__srt1_srt2_srt3_srt4_uni1_uni2_uni3_uni4` |
| -46 | `_rsp1_` |
| -40 | `rsp2_rsp3_rsp4_rsp5_lbk_pot_eps_col_col2` |

The duplicate modifier's raw value is `TALENT_REPLICATION` (18 UTF-8 bytes). In
short exports, its prefix copies the dictionary at -227 and its suffix copies
-238. To recover the actual bytes without guessing, a controlled export placed
160 known 244-byte card IDs before a duplicated card. The output exceeded the
32 KiB LZ77 window, removing the initial dictionary from the history. The final
modifier therefore appeared as literal/output-history data. Its decoded tail
was `04 08 c_0_srt1 01 12 TALENT_REPLICATION`.

Before the client extraction, bytes outside the observed runs were unverified.
The old implementation compared two different fillings and refused outputs
depending on unverified bytes. Those placeholder fillings are no longer used.

Encoding uses raw DEFLATE without dictionary references. A decoder with the
game's preset dictionary also accepts these self-contained streams. Different
DEFLATE compressors may produce different valid codes for identical decks;
byte-for-byte equality with the website's exports is not required for semantic
compatibility.

The formerly unobserved spans within the 238-byte suffix were -220 through
-160 (61 bytes) and -113 through -103 (11 bytes). The client extraction also
recovered the seven-byte prefix. The `_rsp1_` separator bytes were confirmed by
chosen card IDs `c_0_rsp1x` and `c_0_rsp2x`.

The bounded inflater rejects truncated streams, trailing input, over-limit
output, and invalid dictionary distances. Tests include
both fixed and dynamic Huffman blocks, including the 39,553-byte window-flush
sample used to identify the duplication constant.

Reproducible captured evidence is stored in
`research/samples/dictionary_probes.json` and
`research/samples/dictionary_window_flush.json`.
These are research fixtures only; the SDK never contacts the sampling endpoint.
