#include "CcArchive.h"
#include "Lzw.h"
#include <fstream>
#include <stdexcept>
#include <cstring>

namespace pe {

bool CcArchive::looksCompressed(const std::vector<uint8_t> &blob, uint32_t &orig) {
    if (blob.size() < 8) return false;
    orig = static_cast<uint32_t>(blob[0]) |
           (static_cast<uint32_t>(blob[1]) << 8) |
           (static_cast<uint32_t>(blob[2]) << 16) |
           (static_cast<uint32_t>(blob[3]) << 24);
    return blob.size() < orig && orig < 0x100000;
}

CcArchive::CcArchive(const std::string &path) {
    std::ifstream f(path, std::ios::binary);
    if (!f) throw std::runtime_error("cc: cannot open " + path);
    f.seekg(0, std::ios::end);
    size_t sz = static_cast<size_t>(f.tellg());
    f.seekg(0);
    file_data_.resize(sz);
    f.read(reinterpret_cast<char *>(file_data_.data()), sz);

    if (sz < 2) throw std::runtime_error("cc: file too small");
    uint16_t count = static_cast<uint16_t>(file_data_[0]) | (static_cast<uint16_t>(file_data_[1]) << 8);
    size_t p = 2;
    for (uint16_t i = 0; i < count; i++) {
        if (p + 8 > sz) throw std::runtime_error("cc: truncated entry table");
        uint16_t id = static_cast<uint16_t>(file_data_[p]) | (static_cast<uint16_t>(file_data_[p+1]) << 8);
        uint32_t off = file_data_[p+2] | (static_cast<uint32_t>(file_data_[p+3]) << 8) |
                       (static_cast<uint32_t>(file_data_[p+4]) << 16);
        uint32_t esz = file_data_[p+5] | (static_cast<uint32_t>(file_data_[p+6]) << 8) |
                       (static_cast<uint32_t>(file_data_[p+7]) << 16);
        entries_[id] = {off, esz};
        p += 8;
    }
}

std::optional<std::vector<uint8_t>> CcArchive::getEntry(uint16_t id) const {
    auto it = entries_.find(id);
    if (it == entries_.end()) return std::nullopt;
    const auto &hdr = it->second;
    if (hdr.file_off + hdr.size > file_data_.size()) return std::nullopt;
    std::vector<uint8_t> blob(
        file_data_.begin() + hdr.file_off,
        file_data_.begin() + hdr.file_off + hdr.size);

    uint32_t orig = 0;
    if (looksCompressed(blob, orig)) {
        std::span<const uint8_t> bitstream(blob.data() + 4, blob.size() - 4);
        return lzwDecompress(bitstream, orig);
    }
    return blob;
}

std::vector<uint16_t> CcArchive::ids() const {
    std::vector<uint16_t> out;
    out.reserve(entries_.size());
    for (auto &p : entries_) out.push_back(p.first);
    return out;
}

} // namespace pe
