#pragma once
// A match recording in the spirit of League's Server Network Recordings: the match's seed, then for each tick that had
// any, the spawns and orders applied on it, and every 30 ticks a checkpoint with the match's checksum. Playing it back
// through Match::step must give the same game, tick for tick (server.exe --replay checks it).
//
// "BASR", u32 version 5, u64 match id; then records: u8 1 (events): i64 tick, u32 spawns (u8 team, u16 + character,
// f32 x, z, speed, radius, facing), u32 orders (u32 unit, f32 x, z, u8 type, u32 target, u8 slot); u8 2 (checkpoint): i64 tick,
// u64 checksum.

#include <cstdint>
#include <filesystem>
#include <fstream>
#include <vector>

#include "Match.h"

namespace ba {

class Recorder {
 public:
  Recorder(const std::filesystem::path& file, uint64_t match_id);
  void events(int64_t tick, const std::vector<SpawnRequest>& spawns, const std::vector<Order>& orders);
  void checkpoint(int64_t tick, uint64_t checksum);

 private:
  std::ofstream out_;
};

struct Recording {
  uint64_t match_id = 0;
  struct Events {
    int64_t tick = 0;
    std::vector<SpawnRequest> spawns;
    std::vector<Order> orders;
  };
  std::vector<Events> events;
  std::vector<std::pair<int64_t, uint64_t>> checkpoints;
};

/** Reads a recording; throws on a damaged file. */
Recording read_recording(const std::filesystem::path& file);

}  // namespace ba
