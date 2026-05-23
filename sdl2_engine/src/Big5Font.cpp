#include "Big5Font.h"
#include <fstream>
#include <cstring>
#include <iostream>

namespace pe {

bool Big5Font::load(const std::string &path) {
    std::ifstream f(path, std::ios::binary);
    if (!f) {
        std::cerr << "Big5Font: cannot open " << path << "\n";
        return false;
    }
    char magic[2];
    f.read(magic, 2);
    if (magic[0] != 'B' || magic[1] != 'F') {
        std::cerr << "Big5Font: bad magic\n";
        return false;
    }
    uint16_t n;
    f.read(reinterpret_cast<char *>(&n), 2);
    for (uint16_t i = 0; i < n; i++) {
        uint16_t code;
        std::array<uint8_t, 18> data;
        f.read(reinterpret_cast<char *>(&code), 2);
        f.read(reinterpret_cast<char *>(data.data()), 18);
        if (!f) return false;
        glyphs_[code] = data;
    }
    return true;
}

const uint8_t *Big5Font::findGlyph(uint16_t big5_code) const {
    auto it = glyphs_.find(big5_code);
    if (it == glyphs_.end()) return nullptr;
    return it->second.data();
}

int Big5Font::drawText(uint8_t *pixels, int pitch, int buf_w, int buf_h,
                        int x, int y, std::span<const uint8_t> big5_bytes,
                        uint8_t fg_color) const {
    int cur_x = x;
    size_t i = 0;
    while (i < big5_bytes.size()) {
        uint8_t b = big5_bytes[i];

        /* Detect Big5 lead byte: 0xA1..0xFE */
        if (b >= 0xA1 && b <= 0xFE && i + 1 < big5_bytes.size()) {
            uint8_t trail = big5_bytes[i + 1];
            if ((trail >= 0x40 && trail <= 0x7E) || (trail >= 0xA1 && trail <= 0xFE)) {
                /* Big5 wide char */
                uint16_t code = (static_cast<uint16_t>(b) << 8) | trail;
                const uint8_t *g = findGlyph(code);
                if (g) {
                    for (int row = 0; row < H; row++) {
                        int py = y + row;
                        if (py < 0 || py >= buf_h) continue;
                        for (int col = 0; col < W; col++) {
                            int px = cur_x + col;
                            if (px < 0 || px >= buf_w) continue;
                            if (testBit(g, col, row)) {
                                pixels[py * pitch + px] = fg_color;
                            }
                        }
                    }
                }
                cur_x += W;  /* advance by 12 px */
                i += 2;
                continue;
            }
        }

        /* ASCII fallback: half-width 6 px advance (caller will likely use
         * a separate ASCII font; for now we just draw small block) */
        if (b >= 0x20 && b < 0x7F) {
            uint16_t code = b;  /* ASCII as low-byte big5 */
            const uint8_t *g = findGlyph(code);
            if (g) {
                /* draw glyph at half-width slot */
                for (int row = 0; row < H; row++) {
                    int py = y + row;
                    if (py < 0 || py >= buf_h) continue;
                    for (int col = 0; col < 6; col++) {
                        int px = cur_x + col;
                        if (px < 0 || px >= buf_w) continue;
                        if (testBit(g, col, row)) {
                            pixels[py * pitch + px] = fg_color;
                        }
                    }
                }
            }
            cur_x += 6;
        } else if (b == '\n') {
            cur_x = x;
            y += H + 2;
        } else {
            /* skip unknown */
        }
        i += 1;
    }
    return cur_x;
}

} // namespace pe
