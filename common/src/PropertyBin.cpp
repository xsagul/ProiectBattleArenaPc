#include "ba/PropertyBin.h"

#include <stdexcept>
#include <string>

#include "ba/ByteReader.h"
#include "ba/Hash.h"

namespace ba {

namespace {

struct BadType : std::runtime_error {
  using std::runtime_error::runtime_error;
};

class Parser {
 public:
  Parser(ByteReader& r, bool legacy) : r_(r), legacy_(legacy) {}

  BinType type() {
    uint8_t t = r_.read<uint8_t>();
    // Before List2 existed, the container types were numbered one lower.
    if (legacy_ && t >= 129) ++t;
    if (!(t <= 18 || (t >= 128 && t <= 135))) throw BadType("bin: unknown type " + std::to_string(t));
    return static_cast<BinType>(t);
  }

  BinField field() {
    BinField f;
    f.name = r_.read<uint32_t>();
    f.value = value(type());
    return f;
  }

  BinValue value(BinType t) {
    BinValue v;
    v.type = t;
    switch (t) {
      case BinType::Empty: r_.skip(6); break;  // as pyRitoFile reads it: three u16
      case BinType::Bool:
      case BinType::Flag:
      case BinType::U8: v.num[0] = r_.read<uint8_t>(); v.u = static_cast<uint64_t>(v.num[0]); break;
      case BinType::I8: v.num[0] = r_.read<int8_t>(); break;
      case BinType::I16: v.num[0] = r_.read<int16_t>(); break;
      case BinType::U16: v.num[0] = r_.read<uint16_t>(); break;
      case BinType::I32: v.num[0] = r_.read<int32_t>(); break;
      case BinType::U32: v.u = r_.read<uint32_t>(); v.num[0] = static_cast<double>(v.u); break;
      case BinType::I64: v.num[0] = static_cast<double>(r_.read<int64_t>()); break;
      case BinType::U64: v.u = r_.read<uint64_t>(); v.num[0] = static_cast<double>(v.u); break;
      case BinType::F32: v.num[0] = r_.read<float>(); break;
      case BinType::Vec2: floats(v, 2); break;
      case BinType::Vec3: floats(v, 3); break;
      case BinType::Vec4: floats(v, 4); break;
      case BinType::Mtx4: floats(v, 16); break;
      case BinType::RGBA:
        for (int i = 0; i < 4; ++i) v.num[i] = r_.read<uint8_t>();
        break;
      case BinType::String: v.str = r_.string16(); break;
      case BinType::Hash:
      case BinType::Link: v.u = r_.read<uint32_t>(); break;
      case BinType::File: v.u = r_.read<uint64_t>(); break;
      case BinType::List:
      case BinType::List2: {
        v.elem = type();
        r_.skip(4);  // byte size
        const uint32_t n = r_.read<uint32_t>();
        v.items.reserve(n);
        for (uint32_t i = 0; i < n; ++i) v.items.push_back(value(v.elem));
        break;
      }
      case BinType::Pointer:
      case BinType::Embed: {
        v.cls = r_.read<uint32_t>();
        if (v.cls != 0) {
          r_.skip(4);  // byte size
          const uint16_t n = r_.read<uint16_t>();
          v.fields.reserve(n);
          for (uint16_t i = 0; i < n; ++i) v.fields.push_back(field());
        }
        break;
      }
      case BinType::Option: {
        v.elem = type();
        if (r_.read<uint8_t>() != 0) v.items.push_back(value(v.elem));
        break;
      }
      case BinType::Map: {
        v.key = type();
        v.elem = type();
        r_.skip(4);  // byte size
        const uint32_t n = r_.read<uint32_t>();
        v.pairs.reserve(n);
        for (uint32_t i = 0; i < n; ++i) {
          BinValue k = value(v.key);
          BinValue x = value(v.elem);
          v.pairs.emplace_back(std::move(k), std::move(x));
        }
        break;
      }
    }
    return v;
  }

 private:
  void floats(BinValue& v, int n) {
    for (int i = 0; i < n; ++i) v.num[static_cast<size_t>(i)] = r_.read<float>();
  }

  ByteReader& r_;
  bool legacy_;
};

const BinValue* find(const std::vector<BinField>& fields, uint32_t h) {
  for (const BinField& f : fields)
    if (f.name == h) return &f.value;
  return nullptr;
}

}  // namespace

const BinValue* BinValue::field(uint32_t h) const { return find(fields, h); }
const BinValue* BinValue::field(std::string_view name) const { return find(fields, fnv1a(name)); }
const BinValue* BinEntry::field(uint32_t h) const { return find(fields, h); }
const BinValue* BinEntry::field(std::string_view name) const { return find(fields, fnv1a(name)); }

PropertyBin::PropertyBin(std::span<const uint8_t> data) {
  ByteReader r(data);
  std::string magic = r.string(4);
  if (magic == "PTCH") {
    r.skip(8);
    magic = r.string(4);
  }
  if (magic != "PROP") throw std::runtime_error("bin: bad signature");
  version_ = r.read<uint32_t>();
  if (version_ < 1 || version_ > 3) throw std::runtime_error("bin: unsupported version " + std::to_string(version_));
  if (version_ >= 2) {
    const uint32_t n = r.read<uint32_t>();
    for (uint32_t i = 0; i < n; ++i) links_.push_back(r.string16());
  }
  const uint32_t count = r.read<uint32_t>();
  std::vector<uint32_t> classes(count);
  for (uint32_t& c : classes) c = r.read<uint32_t>();
  const size_t start = r.pos();

  // New numbering first; files from before List2 existed fail on a type byte and are read again the old way.
  for (bool legacy : {false, true}) {
    try {
      r.seek(start);
      Parser p(r, legacy);
      entries_.clear();
      entries_.reserve(count);
      for (uint32_t i = 0; i < count; ++i) {
        BinEntry e;
        e.cls = classes[i];
        r.skip(4);  // byte size
        e.name = r.read<uint32_t>();
        const uint16_t n = r.read<uint16_t>();
        e.fields.reserve(n);
        for (uint16_t k = 0; k < n; ++k) e.fields.push_back(p.field());
        entries_.push_back(std::move(e));
      }
      return;
    } catch (const BadType&) {
      if (legacy) throw;
    }
  }
}

const BinEntry* PropertyBin::entry(uint32_t h) const {
  for (const BinEntry& e : entries_)
    if (e.name == h) return &e;
  return nullptr;
}

const BinEntry* PropertyBin::entry(std::string_view name) const { return entry(fnv1a(name)); }

}  // namespace ba
