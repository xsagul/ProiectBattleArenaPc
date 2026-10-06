#include "ba/ShaderCache.h"

#include <cstring>
#include <stdexcept>

#include "ba/ByteReader.h"
#include "xxhash.h"

namespace ba {

namespace {

std::string string32(ByteReader& r) { return r.string(r.read<uint32_t>()); }

/** The DXBC containers of a bundle, in order (each starts with "DXBC"; its total size is at byte 24). */
std::vector<std::vector<uint8_t>> split_dxbc(const std::vector<uint8_t>& data) {
  std::vector<std::vector<uint8_t>> out;
  size_t at = 0;
  while (at + 28 <= data.size()) {
    if (std::memcmp(data.data() + at, "DXBC", 4) != 0) {
      ++at;
      continue;
    }
    uint32_t size = 0;
    std::memcpy(&size, data.data() + at + 24, 4);
    if (size <= 32 || at + size > data.size()) {
      at += 4;
      continue;
    }
    out.emplace_back(data.begin() + static_cast<std::ptrdiff_t>(at), data.begin() + static_cast<std::ptrdiff_t>(at + size));
    at += size;
  }
  return out;
}

}  // namespace

ShaderToc read_shader_toc(std::span<const uint8_t> data) {
  ByteReader r(data);
  if (string32(r) != "TOC3.0") throw std::runtime_error("shader toc: not TOC3.0");
  const uint32_t size = r.read<uint32_t>(), ndef = r.read<uint32_t>();
  ShaderToc t;
  t.compiled = r.read<uint32_t>();
  r.skip(4);
  string32(r);  // "baseDefines"
  for (uint32_t i = 0; i < ndef; ++i) {
    std::string n = string32(r);
    t.defines.emplace_back(std::move(n), string32(r));
  }
  string32(r);  // "shaders"
  std::vector<uint64_t> keys(size);
  for (uint64_t& k : keys) k = r.read<uint64_t>();
  for (uint32_t i = 0; i < size; ++i) t.table[keys[i]] = r.read<uint32_t>();
  return t;
}

uint64_t permutation_key(const Defines& defines) {
  std::string s;
  for (const auto& [n, v] : defines) s += n + "=" + v;
  return XXH64(s.data(), s.size(), 0);
}

const ShaderCache::Entry* ShaderCache::entry(const std::string& shader, char stage) {
  const std::string id = shader + (stage == 'v' ? ".vs" : ".ps");
  auto it = tocs_.find(id);
  if (it != tocs_.end()) return it->second ? &*it->second : nullptr;
  std::optional<Entry> e;
  for (const char* sep : {".dx11", "-dx11"}) {
    const std::string base = "assets/shaders/generated/" + id + sep;
    if (auto bytes = wad_.read(base)) {
      e = Entry{base, read_shader_toc(*bytes)};
      break;
    }
  }
  auto& slot = tocs_[id];
  slot = std::move(e);
  return slot ? &*slot : nullptr;
}

std::optional<std::vector<uint8_t>> ShaderCache::blob(const std::string& shader, char stage, const Defines& wanted, Defines* used) {
  const Entry* e = entry(shader, stage);
  if (!e) return std::nullopt;
  Defines keep;
  for (const auto& [n, v] : wanted)
    for (const auto& [tn, tv] : e->toc.defines)
      if (tn == n && tv == v) keep[n] = v;
  if (used) *used = keep;
  auto hit = e->toc.table.find(permutation_key(keep));
  if (hit == e->toc.table.end()) return std::nullopt;
  const uint32_t index = hit->second;
  const std::string bundle = e->base + "_" + std::to_string(index / 100 * 100);
  auto b = bundles_.find(bundle);
  if (b == bundles_.end()) {
    auto bytes = wad_.read(bundle);
    b = bundles_.emplace(bundle, bytes ? split_dxbc(*bytes) : std::vector<std::vector<uint8_t>>{}).first;
  }
  const size_t i = index % 100;
  if (i >= b->second.size()) return std::nullopt;
  return b->second[i];
}

}  // namespace ba
