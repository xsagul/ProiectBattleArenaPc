#pragma once
// League's property bins (.bin, "PROP" / "PTCH"): every piece of game data (characters, spells, buffs, particle systems,
// materials, the map) is a tree of typed values. Entries, classes and fields are named by FNV-1a hashes of their names.
//
// Header: "PROP" (or "PTCH" + 8 bytes + "PROP"), u32 version (1..3); v2+: u32 link count + 16-bit-length strings;
// u32 entry count, u32 class hash per entry; then per entry: u32 size, u32 entry name hash, u16 field count, fields.
// A field: u32 name hash, u8 type, value. Older files number the container types one lower (List2 did not exist yet).

#include <array>
#include <cstdint>
#include <memory>
#include <span>
#include <string>
#include <vector>

namespace ba {

enum class BinType : uint8_t {
  Empty = 0, Bool = 1, I8 = 2, U8 = 3, I16 = 4, U16 = 5, I32 = 6, U32 = 7, I64 = 8, U64 = 9, F32 = 10,
  Vec2 = 11, Vec3 = 12, Vec4 = 13, Mtx4 = 14, RGBA = 15, String = 16, Hash = 17, File = 18,
  List = 128, List2 = 129, Pointer = 130, Embed = 131, Link = 132, Option = 133, Map = 134, Flag = 135,
};

struct BinField;

/** One value of any type. Numbers live in `num` (vectors and matrices use several), text in `str`. */
struct BinValue {
  BinType type = BinType::Empty;
  std::array<double, 16> num{};          // scalars in num[0]; Vec2/3/4, RGBA, Mtx4 in order
  uint64_t u = 0;                         // Hash, Link (32-bit), File (64-bit), integers as raw bits
  std::string str;                        // String
  BinType elem = BinType::Empty;          // List / List2 / Option element type, Map value type
  BinType key = BinType::Empty;           // Map key type
  std::vector<BinValue> items;            // List / List2 elements, Option (0 or 1 element)
  std::vector<std::pair<BinValue, BinValue>> pairs;  // Map
  uint32_t cls = 0;                       // Pointer / Embed class hash (0 = null pointer)
  std::vector<BinField> fields;           // Pointer / Embed fields

  /** The field of an embedded object whose name hashes to `name_hash`, or null. */
  const BinValue* field(uint32_t name_hash) const;
  const BinValue* field(std::string_view name) const;
  double number() const { return num[0]; }
};

struct BinField {
  uint32_t name = 0;
  BinValue value;
};

struct BinEntry {
  uint32_t name = 0;  // FNV-1a of the entry's path, e.g. "Characters/Garen/Spells/GarenQ"
  uint32_t cls = 0;   // FNV-1a of its class, e.g. "SpellObject"
  std::vector<BinField> fields;
  const BinValue* field(uint32_t name_hash) const;
  const BinValue* field(std::string_view name) const;
};

class PropertyBin {
 public:
  explicit PropertyBin(std::span<const uint8_t> data);

  uint32_t version() const { return version_; }
  const std::vector<std::string>& links() const { return links_; }
  const std::vector<BinEntry>& entries() const { return entries_; }
  const BinEntry* entry(uint32_t name_hash) const;
  const BinEntry* entry(std::string_view name) const;

 private:
  uint32_t version_ = 0;
  std::vector<std::string> links_;
  std::vector<BinEntry> entries_;
};

}  // namespace ba
