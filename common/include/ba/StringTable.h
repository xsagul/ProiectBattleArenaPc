#pragma once
// League's localised texts (.stringtable, "RST"), e.g. Localized/Global.en_US.wad.client data/menu/main_en_us.stringtable:
// "RST", u8 version; u32 count; count x u64 entries, each the key's hash in the low bits and the text's offset above
// them (version 5: 39 hash bits = xxHash64 of the lowercase key); then the texts, UTF-8, each ending in a zero byte.
// (Read off 14.1's file: "item_3031_name" -> "Infinity Edge".) Versions before 5 have 40 hash bits and a flag byte
// before the texts.

#include <cstdint>
#include <span>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

namespace ba {

class StringTable {
 public:
  StringTable() = default;
  explicit StringTable(std::span<const uint8_t> data);
  /** The text of a key ("Item_3031_Name"), or the key itself when the table has no such text. */
  std::string get(std::string_view key) const;
  bool has(std::string_view key) const;
  size_t size() const { return offsets_.size(); }

 private:
  uint64_t hash(std::string_view key) const;
  int bits_ = 39;
  std::vector<char> texts_;
  std::unordered_map<uint64_t, uint32_t> offsets_;  // key hash -> where its text starts
};

}  // namespace ba
