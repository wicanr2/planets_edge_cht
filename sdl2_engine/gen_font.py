"""Generate 12x12 Big5 font blob from unifont 16x16 source.

Strategy:
  1. Parse /usr/share/unifont/unifont.hex — Unicode codepoint → 16x16 1bpp glyph
  2. For each Big5 codepoint we care about, look up its Unicode value, fetch unifont glyph
  3. Downsample 16x16 → 12x12 via nearest-neighbor (with edge-aware tweaks)
  4. Pack into binary blob:
     [u16 magic = 'BF']
     [u16 num_glyphs]
     [num_glyphs × (u16 big5_code, 18 bytes glyph_data)]
     Each glyph = 12 rows × 12 bits = 144 bits packed MSB-first = 18 bytes

Demo charset: 天際寒星 繁體中文版本 任務 完成 New World Computing 字幕
"""
import os, sys, struct

UNIFONT_HEX = "/usr/share/unifont/unifont.hex"
OUT_BLOB = "/mnt/d/03_tools/poc/sdl2_spike/big5_font_12.bin"

# Demo strings — every char appearing in these will be in the font blob
DEMO_STRINGS = [
    "天際寒星",
    "繁體中文化版",
    "新世界電腦",
    "按任意鍵繼續",
    "司令官波克",
    "搜尋元件",
    "拯救地球",
    "敬請期待",
    "本譯版由社群製作",
    "中文化測試版本",
]

def parse_unifont():
    """Parse unifont.hex → dict[codepoint] = 64 hex chars (16x16 1bpp).

    File format: each line "CCCC:HHHH...HHHH" where:
      - 16x16 full-width glyph: 64 hex chars (16 rows × 4 hex chars/row)
      - 8x16 half-width glyph: 32 hex chars (16 rows × 2 hex chars/row)
    """
    glyphs = {}
    n_full = 0
    n_half = 0
    with open(UNIFONT_HEX, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or ':' not in line: continue
            cp_hex, glyph_hex = line.split(':', 1)
            cp = int(cp_hex, 16)
            if len(glyph_hex) == 64:
                glyphs[cp] = glyph_hex
                n_full += 1
            elif len(glyph_hex) == 32:
                # 8x16 half-width — pad each 8-bit row to 16-bit (left-justified)
                padded = ''
                for r in range(16):
                    row_byte = glyph_hex[r*2:r*2+2]
                    padded += row_byte + '00'  # left half = glyph, right half = 0
                glyphs[cp] = padded
                n_half += 1
    print(f"  full-width: {n_full}, half-width: {n_half}")
    return glyphs

def hex_to_bits_16x16(hex_str):
    """64 hex chars → 16 rows of 16 bits each."""
    rows = []
    for r in range(16):
        row_byte_hi = int(hex_str[r*4:r*4+2], 16)
        row_byte_lo = int(hex_str[r*4+2:r*4+4], 16)
        bits = (row_byte_hi << 8) | row_byte_lo
        rows.append(bits)
    return rows

def downsample_16x16_to_12x12(rows16):
    """Naive nearest-neighbor downsample. Keep rows/cols at indices 0,1,3,4,5,7,8,9,11,12,13,15.
    These 12 indices give an even-ish sampling of 16."""
    keep_idx = [0, 1, 3, 4, 6, 7, 8, 9, 11, 12, 14, 15]
    # Actually use simple: take cols 1..14 (drop edges 0,15) but spread evenly
    # Better strategy: bilinear-ish OR-down (use OR of neighbors for stroke preservation)
    rows12 = []
    # For each output row i (0..11), input row = (i * 16) // 12 = something
    # Use nearest with OR:
    for oy in range(12):
        # Map output row 0..11 to input rows 0..15
        # Use bracket: rows that map to this output row
        iy_start = (oy * 16) // 12
        iy_end = ((oy + 1) * 16) // 12
        if iy_end <= iy_start: iy_end = iy_start + 1
        in_rows = rows16[iy_start:iy_end]
        merged_row = 0
        for r in in_rows: merged_row |= r
        # Now downsample columns: 16 → 12
        out_row = 0
        for ox in range(12):
            ix_start = (ox * 16) // 12
            ix_end = ((ox + 1) * 16) // 12
            if ix_end <= ix_start: ix_end = ix_start + 1
            # OR of those input bits (MSB-first: bit 15 = leftmost)
            bit_set = 0
            for ix in range(ix_start, ix_end):
                if merged_row & (1 << (15 - ix)):
                    bit_set = 1
                    break
            if bit_set:
                out_row |= (1 << (11 - ox))
        rows12.append(out_row)
    return rows12

def rows12_to_bytes(rows12):
    """12 rows × 12 bits = 144 bits → pack as 18 bytes MSB-first."""
    bits = 0
    for row in rows12:
        bits = (bits << 12) | (row & 0xFFF)
    # bits is 144 bits long
    out = bytearray(18)
    for i in range(18):
        # MSB-first: byte i = bits[(17-i)*8 : (17-i)*8+8] from top
        shift = (17 - i) * 8
        out[i] = (bits >> shift) & 0xFF
    return bytes(out)

def collect_demo_chars():
    chars = set()
    for s in DEMO_STRINGS:
        for ch in s:
            chars.add(ch)
    return sorted(chars)

def main():
    if not os.path.exists(UNIFONT_HEX):
        print(f"ERROR: {UNIFONT_HEX} not found. Run via WSL.")
        sys.exit(2)
    print(f"Reading unifont.hex...")
    unifont = parse_unifont()
    print(f"  {len(unifont)} glyphs loaded")

    demo_chars = collect_demo_chars()
    print(f"  demo charset: {len(demo_chars)} unique chars")
    print(f"  chars: {''.join(demo_chars)}")

    glyphs_out = []  # list of (big5_code, glyph_bytes)
    missing = []
    for ch in demo_chars:
        cp = ord(ch)
        if cp not in unifont:
            print(f"  WARN: U+{cp:04X} '{ch}' not in unifont")
            missing.append(ch)
            continue
        # Encode to Big5 (cp950)
        try:
            big5_bytes = ch.encode('cp950')
            if len(big5_bytes) != 2:
                # Skip single-byte chars (ASCII fits but we handle separately)
                if len(big5_bytes) == 1:
                    big5_code = big5_bytes[0]  # ASCII
                else:
                    print(f"  SKIP: '{ch}' encodes to {big5_bytes.hex()}")
                    continue
            else:
                big5_code = (big5_bytes[0] << 8) | big5_bytes[1]
        except UnicodeEncodeError:
            print(f"  SKIP: '{ch}' not in Big5/cp950")
            missing.append(ch)
            continue

        rows16 = hex_to_bits_16x16(unifont[cp])
        rows12 = downsample_16x16_to_12x12(rows16)
        glyph_bytes = rows12_to_bytes(rows12)
        glyphs_out.append((big5_code, ch, glyph_bytes))

    print(f"\n  encoded {len(glyphs_out)} glyphs, {len(missing)} missing")

    # Sort by big5_code so we can binary-search at runtime
    glyphs_out.sort(key=lambda x: x[0])

    # Write blob:
    #   [u16 magic 'BF']
    #   [u16 num_glyphs]
    #   [num_glyphs × (u16 big5_code, 18 bytes glyph)]
    with open(OUT_BLOB, 'wb') as f:
        f.write(b'BF')
        f.write(struct.pack('<H', len(glyphs_out)))
        for big5_code, ch, gbytes in glyphs_out:
            f.write(struct.pack('<H', big5_code))
            f.write(gbytes)
    print(f"\nWrote {OUT_BLOB} ({4 + len(glyphs_out)*20} bytes)")

    # Print a sample (first 5 glyphs as ASCII art)
    print(f"\n=== Sample (first 5 glyphs as ASCII art) ===")
    for big5_code, ch, gbytes in glyphs_out[:5]:
        rows12_back = []
        # unpack 18 bytes → 144 bits → 12 rows × 12 bits
        bits_int = int.from_bytes(gbytes, 'big')
        for r in range(12):
            shift = (11 - r) * 12
            rows12_back.append((bits_int >> shift) & 0xFFF)
        print(f"  '{ch}' = 0x{big5_code:04X}:")
        for r in rows12_back:
            line = ''
            for b in range(12):
                line += '##' if (r & (1 << (11 - b))) else '..'
            print(f"    {line}")
        print()

if __name__ == '__main__':
    main()
