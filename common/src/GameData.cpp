#include "ba/GameData.h"

#include <fstream>

namespace ba {

std::filesystem::path find_game_data(const std::string& arg, const std::filesystem::path& start) {
  namespace fs = std::filesystem;
  if (!arg.empty()) return fs::absolute(arg);
  std::error_code ec;
  for (fs::path p = fs::absolute(start, ec); !p.empty(); p = p.parent_path()) {
    std::ifstream f(p / "data-path.txt");
    std::string line;
    if (f && std::getline(f, line)) {
      while (!line.empty() && (line.back() == '\r' || line.back() == ' ')) line.pop_back();
      if (fs::exists(fs::path(line) / "DATA" / "FINAL", ec)) return line;
    }
    if (fs::exists(p / "game-data" / "DATA" / "FINAL", ec)) return p / "game-data";
    if (p == p.parent_path()) break;
  }
  return fs::absolute(start, ec) / "game-data";
}

}  // namespace ba
