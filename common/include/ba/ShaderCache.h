#pragma once
// Riot's compiled DX11 shaders, as the game ships them in ShaderCache.dx11.wad.client:
//   assets/shaders/generated/<shader>.<ps|vs>.dx11       the permutation table (TOC3.0)
//   assets/shaders/generated/<shader>.<ps|vs>.dx11_<n>   compiled permutations n .. n+99, one DXBC blob each
// (patch 14.1 writes ".ps.dx11", later patches ".ps-dx11"; both are tried).
//
// TOC3.0 (read off 14.1's files): u32 6 + "TOC3.0", u32 table size, u32 define count, u32 compiled count, u32 1,
// string "baseDefines", define count x (string name, string value), string "shaders", table size x u64 key, table size
// x u32 permutation index. Strings are u32 length + bytes. A key is XXH64 of the permutation's defines written
// NAME=VALUE, sorted, joined with nothing between them (found by search: research/toc_hash_search.py; every key of
// srx_blend_master decodes and matches its blobs' contents: tools/shader_toc.py).

#include <cstdint>
#include <map>
#include <optional>
#include <span>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

#include "ba/Wad.h"

namespace ba {

using Defines = std::map<std::string, std::string>;  // NAME -> VALUE, kept sorted

struct ShaderToc {
  std::vector<std::pair<std::string, std::string>> defines;  // every NAME=VALUE the permutations are built from
  std::unordered_map<uint64_t, uint32_t> table;               // key -> permutation index
  uint32_t compiled = 0;
};

ShaderToc read_shader_toc(std::span<const uint8_t> data);
/** The key of a set of defines. */
uint64_t permutation_key(const Defines& defines);

class ShaderCache {
 public:
  explicit ShaderCache(const Wad& wad) : wad_(wad) {}
  /** The compiled permutation of `shader` ("shaders/staticmesh/srx_blend_ocean"), stage 'v' or 'p', for `wanted`
   *  defines. Defines the table does not know are dropped (they were not compiled in); empty when the shader or the
   *  combination does not exist. `used` receives the defines actually looked up. */
  std::optional<std::vector<uint8_t>> blob(const std::string& shader, char stage, const Defines& wanted, Defines* used = nullptr);

 private:
  struct Entry {
    std::string base;  // the toc's path without its suffix
    ShaderToc toc;
  };
  const Entry* entry(const std::string& shader, char stage);
  const Wad& wad_;
  std::unordered_map<std::string, std::optional<Entry>> tocs_;
  std::unordered_map<std::string, std::vector<std::vector<uint8_t>>> bundles_;
};

}  // namespace ba
