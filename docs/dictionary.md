# Preset dictionary evidence

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

Dictionary bytes outside the observed runs remain unverified. The SDK compares
two inflations which fill these positions differently. It returns a payload
only when both results agree, and reports an explicit error for a code which
requires an unverified byte. This avoids silently substituting guessed text.

Encoding uses raw DEFLATE without dictionary references. A decoder with the
game's preset dictionary also accepts these self-contained streams. Different
DEFLATE compressors may produce different valid codes for identical decks;
byte-for-byte equality with the website's exports is not required for semantic
compatibility.

The remaining unobserved spans within the 238-byte suffix are -220 through
-160 (61 bytes) and -113 through -103 (11 bytes). The full dictionary may also
have an earlier prefix. The `_rsp1_` separator bytes were directly confirmed by
chosen card IDs `c_0_rsp1x` and `c_0_rsp2x`.

The bounded inflater rejects truncated streams, trailing input, over-limit
output, and streams that reference those unverified positions. Tests include
both fixed and dynamic Huffman blocks, including the 39,553-byte window-flush
sample used to identify the duplication constant.

Reproducible captured evidence is stored in
`research/samples/dictionary_probes.json` and
`research/samples/dictionary_window_flush.json`.
These are research fixtures only; the SDK never contacts the sampling endpoint.
