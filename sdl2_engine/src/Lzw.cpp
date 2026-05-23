#include "Lzw.h"
#include <array>

namespace pe {

std::vector<uint8_t> lzwDecompress(std::span<const uint8_t> packed, uint32_t orig_size) {
    constexpr uint16_t CLEAR = 0x100;
    constexpr uint16_t END = 0x101;
    constexpr int MAX_WIDTH = 12;
    constexpr int DICT_CAP = 4096;

    std::vector<uint8_t> out;
    out.reserve(orig_size);

    int bit_pos = 0;
    auto get_code = [&](int width) -> uint16_t {
        int bp = bit_pos;
        bit_pos += width;
        size_t byte = static_cast<size_t>(bp >> 3);
        int shift = bp & 7;
        uint8_t b0 = byte     < packed.size() ? packed[byte]     : 0;
        uint8_t b1 = byte + 1 < packed.size() ? packed[byte + 1] : 0;
        uint8_t b2 = byte + 2 < packed.size() ? packed[byte + 2] : 0;
        uint32_t v = static_cast<uint32_t>(b0) |
                     (static_cast<uint32_t>(b1) << 8) |
                     (static_cast<uint32_t>(b2) << 16);
        return static_cast<uint16_t>((v >> shift) & ((1u << width) - 1));
    };

    int width = 9;
    int next_cd = 0x102;
    int next_max = 1 << width;
    std::array<uint16_t, DICT_CAP> parent{};
    std::array<uint8_t,  DICT_CAP> suffix{};

    uint16_t code = get_code(width);
    if (code == END) return out;
    if (code == CLEAR) {
        code = get_code(width);
        if (code == END) return out;
    }
    out.push_back(static_cast<uint8_t>(code));
    uint16_t prev = code;
    uint8_t first = static_cast<uint8_t>(code);

    while (out.size() < orig_size) {
        code = get_code(width);
        if (code == END) break;
        if (code == CLEAR) {
            width = 9; next_cd = 0x102; next_max = 1 << width;
            code = get_code(width);
            if (code == END) break;
            out.push_back(static_cast<uint8_t>(code));
            prev = code;
            first = static_cast<uint8_t>(code);
            continue;
        }
        uint16_t cur = code;
        std::vector<uint8_t> stack;
        stack.reserve(32);
        if (code >= next_cd) {
            stack.push_back(first);
            cur = prev;
        }
        while (cur > 0xFF) {
            stack.push_back(suffix[cur]);
            cur = parent[cur];
        }
        first = static_cast<uint8_t>(cur);
        out.push_back(first);
        while (!stack.empty()) {
            out.push_back(stack.back());
            stack.pop_back();
        }
        if (next_cd < DICT_CAP) {
            parent[next_cd] = prev;
            suffix[next_cd] = first;
            next_cd++;
            if (next_cd >= next_max && width < MAX_WIDTH) {
                width++;
                next_max <<= 1;
            }
        }
        prev = code;
    }
    if (out.size() > orig_size) out.resize(orig_size);
    return out;
}

} // namespace pe
