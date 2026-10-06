#include "ba/Hash.h"

#include <string>

#include "xxhash.h"

namespace ba {

static char lower(char c) { return (c >= 'A' && c <= 'Z') ? static_cast<char>(c - 'A' + 'a') : c; }

uint64_t wad_hash(std::string_view path) {
  std::string s(path);
  for (char& c : s) c = lower(c);
  return XXH64(s.data(), s.size(), 0);
}

uint32_t fnv1a(std::string_view name) {
  uint32_t h = 0x811C9DC5u;
  for (char c : name) {
    h ^= static_cast<uint8_t>(lower(c));
    h *= 0x01000193u;
  }
  return h;
}

}  // namespace ba
