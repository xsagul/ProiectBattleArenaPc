#pragma once
// The client's link to server.exe over ENet. Units walk their WaypointGroup paths locally, starting from the server tick
// the path was issued on, so movement stays smooth between the server's 30 updates a second.

#include <atomic>
#include <enet/enet.h>

#include <cstdint>
#include <map>
#include <string>
#include <vector>

#include "ba/Deterministic.h"
#include "ba/Protocol.h"

namespace ba {

struct ClientUnit {
  uint32_t id = 0;
  uint8_t team = 0;
  std::string skin;  // the character ("Garen", "Turret") and its skin
  uint8_t skin_id = 0;
  float x = 0;
  float z = 0;
  float speed = 0;
  float facing = 0;  // radians, kept from the last direction it moved in
  bool moving = false;  // still short of the end of its path
  // combat, as the server reports it
  float hp = 0, max_hp = 0, shield = 0;
  float par = 0, max_par = 0;  // the ability resource (mana ...)
  int level = 1;
  float xp = 0;                // the part of the way to the next level
  float gold = 0;
  float ad = 0, armor = 0, spell_block = 0, attack_speed = 0, move_speed = 0;
  uint16_t kills = 0, deaths = 0, assists = 0, minions_killed = 0;
  float ap = 0, ability_haste = 0, crit = 0;
  int items[7] = {};            // the inventory: an item id per slot (0: empty), slot 6 the trinket
  int item_stacks[7] = {};
  bool dead = false;
  double death_time = 0;  // local seconds
  int hits = 0;            // times its health went down (the graph's Hit clip starts over each time)
  double hit_time = -1;    // local seconds of the last one
  double spawn_time = -1;  // local seconds it entered the match, if that happened after the player joined
  int respawns = 0;        // times it came back from the dead (its animation starts afresh)
  double respawn_time = -1;  // local seconds of the last time
  struct Attack {
    int serial = 0;           // changes with every attack (the clip starts over)
    double start = -1;        // local seconds
    std::string spell, animation;
    float windup = 0, total = 0, cast = 0;
    uint32_t target = 0;
  } attack;
  std::vector<net::Point> path;  // from the position at path_tick
  int64_t path_tick = 0;
  double path_frac = 0;  // a replay's paths start between two ticks: the part of a tick after path_tick
  /** The clips the server swapped (Riot's packet 71: the unit's whole list each time): {the clip to play, the clip it
   *  stands in for}, e.g. {"DEATH_CASTER", "DEATH"}, {"STATE2", "IDLE1"}. Names in the server's own letter case. */
  std::vector<std::pair<std::string, std::string>> anim_overrides;
  bool dashing = false;  // its path is a spell's dash, not a walk
  // spells (champions)
  int skill_points = 0;
  struct Spell {
    int level = 0;
    double ready_at = 0;  // local seconds
    float cooldown_total = 0, cost = 0;
  } spells[4];
  struct Cast {
    int serial = 0;       // changes with every cast (the clip starts over)
    double start = -1;    // local seconds
    std::string spell, animation;
    float cast_time = 0;
  } cast;
  /** A clip a spell's script asked for (Garen's spin), for `end - start` seconds (end < 0: until told otherwise). */
  struct Forced {
    int serial = 0;
    std::string clip;
    double start = -1, end = -1;
    bool once = false;  // a replay's "play this clip": for the clip's own length, then back to what the unit was doing
  } forced;
};

class Connection {
 public:
  /** Connects to the server. With `hold` the client only connects (as League's does before it loads) and joins the
   *  match when `ready` is called (its loading done); without it, it joins as soon as it is connected. */
  bool connect(const char* host, uint16_t port, const std::string& name, const std::string& champion, bool hold = false);
  /** The loading is done: joins the match (sends Hello) now, or as soon as the connection is up. */
  void ready();
  /** The round trip to the server in milliseconds (ENet's own measure); -1 while not connected. */
  int ping_ms() const { return ping_; }
  /** Keeps the held connection alive and its round trip measured while the client loads: called from a thread of its
   *  own (nothing else may use the connection meanwhile), since the loading thread is busy for long stretches and a
   *  round trip measured between its pauses would be the pauses' length. */
  void pump();
  /** Handles everything the server sent and walks the units to `now_tick` (fractional server tick). */
  void update(double now_tick);
  void move(float x, float z);
  void attack(uint32_t target);
  /** The Practice Tool's "spawn target dummy" at a point. */
  void spawn_dummy(float x, float z);
  /** Casts a spell (0 Q .. 3 R) at a point of the ground, with the unit under the cursor if any. */
  void cast(uint8_t slot, float x, float z, uint32_t target);
  /** Puts a skill point into a spell. */
  void level_spell(uint8_t slot);
  /** The shop: buys an item (the server checks gold, place and limits) or sells an inventory slot. */
  void buy_item(uint32_t item);
  void sell_item(uint8_t slot);
  void use_item(uint8_t slot, float x, float z, uint32_t target);
  /** Local time (seconds) of a server tick. */
  double tick_time(int64_t tick) const { return server_tick_at + static_cast<double>(tick - server_tick) * kTickSeconds; }
  /** Events for the effects, taken (and cleared) by whoever draws them. */
  struct Missile {
    uint32_t from = 0, to = 0;
    float speed = 0;
    double start = 0;  // local seconds
    std::string spell;
  };
  std::vector<Missile> missiles;
  struct Hit {
    uint32_t source = 0, target = 0;
    double time = 0;  // local seconds
    std::string spell;
  };
  std::vector<Hit> hits;
  /** Spells' missiles (skillshots) that left, and the ids of those that ended. */
  struct SkillMissile {
    uint32_t id = 0, unit = 0;
    std::string spell, effect;
    float x = 0, z = 0, dx = 0, dz = 1, speed = 0, range = 0;
    float accel = 0, speed_limit = 0;
    double start = 0;  // local seconds
  };
  std::vector<SkillMissile> skill_missiles;
  std::vector<uint32_t> skill_missiles_ended;
  /** Effects the spells' scripts start and stop on units. */
  struct EffectChange {
    uint32_t unit = 0, owner = 0;
    bool stop = false;
    std::string key, bone;
    float seconds = 0;
  };
  std::vector<EffectChange> effects;
  /** Effects the scripts start and stop at places. */
  struct GroundEffect {
    uint32_t id = 0, owner = 0;
    bool stop = false;
    std::string key;
    float x = 0, z = 0, tx = 0, tz = 1, seconds = 0, height = 0;
  };
  std::vector<GroundEffect> ground_effects;
  ~Connection();

  uint32_t my_unit = 0;
  int winner = -1;  // the team that won, once the match is over
  int64_t welcome_tick = -1;  // the server tick the player joined on
  int64_t game_start_tick = -1;  // the tick the game's clock started on
  /** The server's tick at the moment of the last packet, and the local time (seconds) it arrived. */
  int64_t server_tick = 0;
  double server_tick_at = 0;
  std::map<uint32_t, ClientUnit> units;

 private:
  void receive(const uint8_t* data, size_t size, double now_seconds);
  ENetHost* host_ = nullptr;
  ENetPeer* peer_ = nullptr;
  std::string name_, champion_;
  bool connected_ = false, hold_ = false, hello_sent_ = false;
  std::atomic<int> ping_{-1};
  void hello();
};

double seconds_now();

}  // namespace ba
