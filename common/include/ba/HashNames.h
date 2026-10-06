#pragma once
// Names behind League's hashes, from CommunityDragon's hash lists (hashes.binfields.txt, hashes.bintypes.txt,
// hashes.binentries.txt / binhashes.txt, hashes.game.txt): "<hex hash> <name>" per line. Only for tools and debugging;
// the game itself works on the hashes.

#include <cstdint>
#include <filesystem>
#include <string>
#include <unordered_map>

namespace ba {

class HashNames {
 public:
  /** Adds every line of a hash list; 8 hex digits are 32-bit (FNV-1a) hashes, 16 are 64-bit (xxh64) path hashes. */
  void load(const std::filesystem::path& file);
  std::string name32(uint32_t h) const;
  std::string name64(uint64_t h) const;

 private:
  std::unordered_map<uint32_t, std::string> h32_;
  std::unordered_map<uint64_t, std::string> h64_;
};

}  // namespace ba
