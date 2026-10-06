#include "ba/StringTable.h"

#include <cctype>
#include <cstring>
#include <stdexcept>

#include <xxhash.h>

namespace ba {

StringTable::StringTable(std::span<const uint8_t> data) {
  if (data.size() < 8 || std::memcmp(data.data(), "RST", 3) != 0) throw std::runtime_error("stringtable: not an RST file");
  const uint8_t version = data[3];
  bits_ = version >= 5 ? 39 : 40;
  size_t o = 4;
  uint32_t count = 0;
  std::memcpy(&count, data.data() + o, 4), o += 4;
  if (o + static_cast<size_t>(count) * 8 > data.size()) throw std::runtime_error("stringtable: cut short");
  std::vector<uint64_t> entries(count);
  std::memcpy(entries.data(), data.data() + o, static_cast<size_t>(count) * 8), o += static_cast<size_t>(count) * 8;
  if (version < 5) ++o;  // a flag byte
  texts_.assign(reinterpret_cast<const char*>(data.data()) + o, reinterpret_cast<const char*>(data.data()) + data.size());
  texts_.push_back('\0');
  const uint64_t mask = (uint64_t{1} << bits_) - 1;
  offsets_.reserve(count);
  for (uint64_t e : entries) offsets_[e & mask] = static_cast<uint32_t>(e >> bits_);
}

uint64_t StringTable::hash(std::string_view key) const {
  std::string lower(key);
  for (char& c : lower) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
  return XXH64(lower.data(), lower.size(), 0) & ((uint64_t{1} << bits_) - 1);
}

bool StringTable::has(std::string_view key) const { return offsets_.count(hash(key)) != 0; }

std::string StringTable::get(std::string_view key) const {
  auto it = offsets_.find(hash(key));
  if (it == offsets_.end() || it->second >= texts_.size()) return std::string(key);
  return std::string(texts_.data() + it->second);
}

}  // namespace ba
