#pragma once
// The match protocol between server.exe and client.exe: ENet (reliable UDP) with 7 channels like League's, compact
// little-endian binary messages. Movement travels as paths (League's WaypointGroup), not as positions every tick: the
// client walks a unit along its path on its own until the server sends a new one.

#include <cstdint>
#include <cstring>
#include <span>
#include <string>
#include <vector>

#include "ba/ByteReader.h"

namespace ba::net {

constexpr uint16_t kDefaultPort = 5119;  // inside League's 5000-5500 game range
constexpr uint32_t kProtocolVersion = 16;
constexpr size_t kChannels = 7;

enum Channel : uint8_t {
  kHandshake = 0,  // connect, welcome, match settings
  kCommands = 1,   // player orders (reliable, ordered)
  kMovement = 2,   // WaypointGroup paths
  kCombat = 3,     // casts, damage, buffs, effects (reliable)
  kStats = 4,      // replicated stats (deltas, latest wins)
  kChat = 5,       // chat and announcements
  kReserved = 6,
};

enum class Msg : uint8_t {
  // client -> server
  Hello = 1,       // u32 version, string name, string champion (e.g. "Garen")
  MoveOrder = 2,   // f32 x, f32 z (League units)
  AttackOrder = 3, // u32 target unit
  SpawnDummy = 4,  // f32 x, f32 z: a practice target dummy there (League's Practice Tool)
  CastSpell = 5,   // u8 slot (0 Q .. 3 R), f32 x, f32 z (the cursor on the ground), u32 the unit under the cursor (0: none)
  LevelSpell = 6,  // u8 slot: a skill point into that spell
  BuyItem = 7,     // u32 item id (the shop: at the fountain or dead)
  SellItem = 8,    // u8 inventory slot (0..5, 6 the trinket)
  UseItem = 9,     // u8 slot, f32 x, f32 z, u32 target
  // server -> client
  Welcome = 64,    // u32 your unit id, i64 server tick, i64 the tick the game began on (its clock's zero)
  UnitSpawn = 65,  // u32 id, u8 team, string character (e.g. "Garen", "Turret"), u8 skin, f32 x, f32 z, f32 facing, i64 the tick it entered the match
  Waypoints = 66,  // i64 start tick, u16 count, then per unit: u32 id, f32 speed, u16 n, n x (f32 x, f32 z)
  UnitHealth = 67, // u32 id, f32 hp, f32 max hp, f32 shield
  UnitAttack = 68, // i64 start tick, u32 id, u32 target, string spell, string animation, f32 windup, f32 attack time,
                   // f32 spell cast time, f32 the unit's facing (it turns to its target; structures do not)
  Missile = 69,    // i64 tick, u32 from, u32 to, f32 speed, string spell
  UnitDeath = 70,  // i64 tick, u32 id
  UnitRemove = 72, // u32 id: the unit left the match (a dead minion after its death)
  UnitHit = 71,    // i64 tick, u32 source, u32 target, string spell: an attack lands (melee hit or missile arrival)
  UnitRespawn = 73, // i64 tick, u32 id, f32 x, f32 z, f32 facing: a dead champion is back at its team's spawn point, or
                    // an inhibitor stands again
  GameEnd = 74,     // u8 the winning team: the other team's nexus fell
  UnitStats = 75,   // u32 id, u8 level, f32 the part of the way to the next level, f32 gold, f32 ability resource, f32 its
                    // maximum, f32 attack damage, f32 armor, f32 magic resist, f32 attack speed, f32 move speed, u16 kills,
                    // u16 deaths, u16 assists, u16 minions killed, f32 ability power, f32 ability haste, f32 crit chance:
                    // a champion's numbers, whenever one of them changes
  UnitSpells = 76,  // u32 id, u8 skill points, then for each of the 4 spells: u8 level, f32 cooldown left, f32 the whole
                    // cooldown, f32 cost
  SpellCast = 77,   // i64 tick, u32 id, u8 slot, string spell, string animation, f32 cast time, f32 x, f32 z, u32 target
  BuffChange = 78,  // u32 id, u8 1 added / 0 gone, string name, f32 seconds (negative: until removed)
  SkillMissile = 79, // i64 tick, u32 missile id, u32 caster, string spell, f32 x, f32 z, f32 dx, f32 dz, f32 speed, f32 range,
                     // string effect (a key of the caster's skin; empty: the spell's mMissileEffectKey), f32 acceleration,
                     // f32 the speed it stops changing at
  SkillMissileEnd = 80, // u32 missile id
  Dash = 81,        // i64 tick, u32 id, f32 x, f32 z, f32 speed (0: there at once)
  Effect = 82,      // u32 id, u8 1 stop / 0 start, string key, string bone, f32 seconds, u32 the unit whose skin's
                    // ResourceResolver has the key (a spell's hit effect plays on the target, but is the caster's)
  Animation = 83,   // i64 tick, u32 id, string clip, f32 seconds: the unit plays a clip of its graph
  GroundEffect = 84, // u32 effect id, u8 1 stop / 0 start, u32 the unit whose skin has the key, string key, f32 x, f32 z,
                     // f32 tx, f32 tz (the place it faces, and its beams reach), f32 seconds (0: it plays out), f32 height
                     // over the ground: an effect at a place
  UnitItems = 85,    // u32 id, 7 x (u32 item id, u8 stack): a champion's inventory (slot 6: the trinket)
};

/** Appends little-endian values to a packet. */
class Writer {
 public:
  template <typename T>
  Writer& put(T v) {
    const auto* p = reinterpret_cast<const uint8_t*>(&v);
    buf_.insert(buf_.end(), p, p + sizeof(T));
    return *this;
  }
  Writer& str(const std::string& s) {
    put<uint16_t>(static_cast<uint16_t>(s.size()));
    buf_.insert(buf_.end(), s.begin(), s.end());
    return *this;
  }
  const std::vector<uint8_t>& bytes() const { return buf_; }

 private:
  std::vector<uint8_t> buf_;
};

struct Point {
  float x = 0;
  float z = 0;
};

struct UnitPath {
  uint32_t id = 0;
  float speed = 0;  // League units per second
  std::vector<Point> points;
};

inline std::vector<uint8_t> waypoints(int64_t start_tick, const std::vector<UnitPath>& paths) {
  Writer w;
  w.put(Msg::Waypoints).put(start_tick).put<uint16_t>(static_cast<uint16_t>(paths.size()));
  for (const UnitPath& p : paths) {
    w.put(p.id).put(p.speed).put<uint16_t>(static_cast<uint16_t>(p.points.size()));
    for (const Point& q : p.points) w.put(q.x).put(q.z);
  }
  return w.bytes();
}

inline std::vector<UnitPath> read_waypoints(ByteReader& r, int64_t& start_tick) {
  start_tick = r.read<int64_t>();
  const uint16_t n = r.read<uint16_t>();
  std::vector<UnitPath> out(n);
  for (UnitPath& p : out) {
    p.id = r.read<uint32_t>();
    p.speed = r.read<float>();
    const uint16_t k = r.read<uint16_t>();
    p.points.resize(k);
    for (Point& q : p.points) {
      q.x = r.read<float>();
      q.z = r.read<float>();
    }
  }
  return out;
}

}  // namespace ba::net
