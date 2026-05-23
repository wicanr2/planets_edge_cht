/* Lzw.h — Planet's Edge LZW 9-12 bit decoder (Unix compress style) */
#pragma once
#include <cstdint>
#include <span>
#include <vector>

namespace pe {

/** Decompress packed bytes (LSB-first variable-width 9..12 bit LZW,
 *  clear=0x100, end=0x101) producing at most `orig_size` output bytes. */
std::vector<uint8_t> lzwDecompress(std::span<const uint8_t> packed, uint32_t orig_size);

} // namespace pe
