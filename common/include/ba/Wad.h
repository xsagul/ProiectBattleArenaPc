#pragma once
// League's .wad.client archives (version 3), read straight from disk like the game does.
//
// Layout: "RW", major, minor; v3 then has a 256-byte signature, a u64 checksum and the entry count (at byte 268), and the
// table of contents from byte 272: 32 bytes per entry
//   u64 path hash (xxh64 of the lowercase path) | u32 offset | u32 compressed size | u32 uncompressed size |
//   u8 type (low 4 bits: 0 raw, 1 gzip, 2 link, 3 zstd, 4 zstd with sub-chunks; high 4 bits: sub-chunk count) |
//   u8 duplicate | u16 first sub-chunk index | u64 checksum

#include <cstdint>
#include <filesystem>
#include <fstream>
#include <optional>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace ba {

struct WadEntry {
  uint64_t hash = 0;
  uint32_t offset = 0;
  uint32_t compressed = 0;
  uint32_t size = 0;
  uint8_t type = 0;
};

class Wad {
 public:
  explicit Wad(const std::filesystem::path& file);

  const std::filesystem::path& file() const { return file_; }
  const std::unordered_map<uint64_t, WadEntry>& entries() const { return entries_; }
  bool has(std::string_view path) const;

  /** The decompressed bytes of an entry, or nothing when the archive does not hold it. */
  std::optional<std::vector<uint8_t>> read(std::string_view path) const;
  std::optional<std::vector<uint8_t>> read_hash(uint64_t hash) const;

 private:
  std::filesystem::path file_;
  mutable std::ifstream in_;
  uint8_t major_ = 0;
  std::unordered_map<uint64_t, WadEntry> entries_;
};

}  // namespace ba
