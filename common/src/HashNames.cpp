#include "ba/HashNames.h"

#include <cstdio>
#include <fstream>

namespace ba {

void HashNames::load(const std::filesystem::path& file) {
  std::ifstream in(file);
  std::string line;
  while (std::getline(in, line)) {
    const size_t sp = line.find(' ');
    if (sp == std::string::npos) continue;
    const std::string hex = line.substr(0, sp);
    std::string name = line.substr(sp + 1);
    if (!name.empty() && name.back() == '\r') name.pop_back();
    if (hex.size() == 8)
      h32_[static_cast<uint32_t>(std::stoul(hex, nullptr, 16))] = std::move(name);
    else if (hex.size() == 16)
      h64_[std::stoull(hex, nullptr, 16)] = std::move(name);
  }
}

std::string HashNames::name32(uint32_t h) const {
  auto it = h32_.find(h);
  if (it != h32_.end()) return it->second;
  char buf[16];
  std::snprintf(buf, sizeof buf, "{%08x}", h);
  return buf;
}

std::string HashNames::name64(uint64_t h) const {
  auto it = h64_.find(h);
  if (it != h64_.end()) return it->second;
  char buf[24];
  std::snprintf(buf, sizeof buf, "{%016llx}", static_cast<unsigned long long>(h));
  return buf;
}

}  // namespace ba
