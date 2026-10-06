#pragma once
// The two hashes League's files use to name things:
//   xxh64(lowercase path)  - entries of .wad.client archives, and "file" values inside .bin
//   FNV-1a 32(lowercase)   - .bin entry names, class names and field names

#include <cstdint>
#include <string_view>

namespace ba {

uint64_t wad_hash(std::string_view path);
uint32_t fnv1a(std::string_view name);

}  // namespace ba
