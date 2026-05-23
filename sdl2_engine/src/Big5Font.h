/* Big5Font.h — 12x12 Big5 bitmap font loader + blitter */
#pragma once
#include <cstdint>
#include <span>
#include <string>
#include <unordered_map>
#include <vector>
#include <array>

namespace pe {

class Big5Font {
public:
    static constexpr int W = 12;
    static constexpr int H = 12;

    /** Load font blob produced by gen_font.py
     *  Format:
     *    [u16 'BF'][u16 num_glyphs][num_glyphs × (u16 big5_code, 18 bytes glyph)]
     *  Glyph: 12 rows × 12 bits, packed MSB-first in 144 bits (18 bytes total)
     */
    bool load(const std::string &path);

    /** Returns pointer to 18-byte glyph data for given big5 codepoint, or null. */
    const uint8_t *findGlyph(uint16_t big5_code) const;

    /** Blit string (Big5 / cp950 encoded) into an indexed pixel buffer
     *  at (x, y). Sets foreground pixels to `color`, leaves others.
     *  Returns x advanced. ASCII bytes use half-width (6 wide). */
    int drawText(uint8_t *pixels, int pitch, int buf_w, int buf_h,
                 int x, int y, std::span<const uint8_t> big5_bytes,
                 uint8_t fg_color = 15) const;

    /** Number of loaded glyphs */
    size_t glyphCount() const { return glyphs_.size(); }

private:
    /* glyph storage: 18-byte glyphs keyed by Big5 code */
    std::unordered_map<uint16_t, std::array<uint8_t, 18>> glyphs_;

    /** Test if bit (col, row) is set in the 18-byte glyph. */
    static bool testBit(const uint8_t *g, int col, int row) {
        int bit = row * 12 + col;
        int byte_idx = bit / 8;
        int bit_idx = 7 - (bit % 8);
        return (g[byte_idx] >> bit_idx) & 1;
    }
};

} // namespace pe
