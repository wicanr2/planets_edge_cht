/* CcArchive.h — Planet's Edge .cc archive reader (LZW-decoded entries) */
#pragma once
#include <cstdint>
#include <map>
#include <string>
#include <vector>
#include <optional>

namespace pe {

class CcArchive {
public:
    /** Parse .cc archive header + entry table. Does NOT decompress payloads. */
    explicit CcArchive(const std::string &path);

    /** Decompress (or copy raw) entry by id. Returns empty optional if id not found. */
    std::optional<std::vector<uint8_t>> getEntry(uint16_t id) const;

    /** List of entry ids in the archive. */
    std::vector<uint16_t> ids() const;

    bool hasEntry(uint16_t id) const { return entries_.count(id) > 0; }

private:
    struct EntryHeader {
        uint32_t file_off;
        uint32_t size;
    };

    std::vector<uint8_t>            file_data_;
    std::map<uint16_t, EntryHeader> entries_;

    static bool looksCompressed(const std::vector<uint8_t> &blob, uint32_t &orig_size_out);
};

} // namespace pe
