#pragma once
// Where the game's files are (the folder that holds DATA/FINAL). The project plays one patch's data: the target is
// patch 14.1 (the user's choice), named in `data-path.txt` at the project root; `game-data/` is the fallback.

#include <filesystem>
#include <string>

namespace ba {

/** `arg` when given; else, walking up from `start`: the folder named in a data-path.txt (its first line), or a
 *  game-data folder, whichever comes first with a DATA/FINAL inside. */
std::filesystem::path find_game_data(const std::string& arg, const std::filesystem::path& start);

}  // namespace ba
