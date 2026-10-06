#pragma once
// A match played from Riot's own server stream: the packets of a 13.3 replay, each already read into its fields by
// Riot's deserializers (tools/sponge/export_replay.py writes them as a .barp file). Every packet kind handled here does
// to the client's world what the Riot client's handler of that kind does; the kinds not handled yet are counted, so
// that "how much of the replay our client understands" is a number (see report()).
//
// Stage 1: fields in clear from the .barp. Stage 2 (not done): the .rofl itself, read by our own wire readers.

#include <cstdint>
#include <cstdio>
#include <functional>
#include <map>
#include <set>
#include <string>
#include <vector>

#include "Connection.h"
#include "ba/CharacterData.h"
#include "ba/MapGame.h"

namespace ba {

class Replay {
 public:
  /** What the handlers need from the client: the map's game objects, the middle of the navigation grid's bounds
   *  (movement packets count 2-unit steps from it), and a character's record (its attack slots). */
  struct World {
    const MapGame* game = nullptr;
    float center_x = 0, center_z = 0;
    std::function<const CharacterRecordData*(const std::string&)> record;
  };
  bool open(const std::string& path, World world);
  bool is_open() const { return file_ != nullptr; }
  /** Applies every packet up to `seconds` of the replay's clock to the connection's world. */
  void feed(Connection& c, double seconds);
  /** Per packet kind: how many were applied by a handler, how many were only counted. */
  void report(const std::string& path) const;
  ~Replay();

 private:
  struct Packet {
    float t = 0;
    uint16_t id = 0;
    uint32_t net = 0;
    std::vector<std::vector<uint8_t>> blocks;
  };
  bool next();
  void seed(Connection& c);
  bool apply(Connection& c, const Packet& p);
  void movement(Connection& c, const uint8_t* buf, size_t size, double t);
  void replication(Connection& c, const std::vector<uint8_t>& buf, double t);

  std::FILE* file_ = nullptr;
  World world_;
  Packet pending_;
  bool has_pending_ = false, seeded_ = false;
  uint32_t left_ = 0;
  std::map<uint16_t, std::pair<uint64_t, uint64_t>> seen_;  // kind -> handled, not handled
  std::map<uint32_t, std::pair<uint8_t, int>> barracks_;    // a barracks' net id -> team, lane
  std::map<uint32_t, uint8_t> hp_group_;                    // a unit's replication group that holds its health
  std::map<uint32_t, double> corpse_until_;                 // dead minions: when the client drops them
  std::set<uint32_t> structures_;                           // turrets, inhibitors, nexuses (they never turn)
  std::set<uint32_t> corpses_;                              // lane minions and monsters: dropped a while after death
  std::map<uint32_t, uint32_t> attack_missile_;             // a unit -> the missile its last attack packet named
};

}  // namespace ba
