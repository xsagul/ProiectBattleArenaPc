// The units' AI: patch 12.23's own scripts (Scripts.wad, data/scripts/<name>.luabin64), run as Riot shipped them. A
// lane minion runs minion.lua (which loads data/shared/scripts/minions.lua): its states (AI_ATTACKMOVESTATE walking the
// lane, AI_ATTACKMOVE_ATTACKING with a target), its timers (TimerFindEnemies every DELAY_FIND_ENEMIES = 0.25 s,
// TimerMoveForward every frame, TimerAntiKite 4 s), the first wave "asleep" until an enemy is within its wakeUpRange,
// then spreading its fire over the enemy's melee minions. This file is the engine side: the functions the scripts call
// and the moments the engine calls them.
//
// What the scripts do not show is the engine's own; our reading of it, each marked:
//   - one script state per script, shared by its units: the unit a call is about is the engine's ("me"); a unit's
//     state, target, timers and ignore list live in the Unit [dedus: the scripts keep nothing per unit themselves]
//   - a timer runs from InitTimer (the scripts stop the ones they do not want) and fires on the first frame its time
//     is over, then counts again from that frame [măsurat: 13.3 replay, paths re-sent every 8 frames of 33.05 ms while
//     a minion closes on its target = 0.25 s rounded up to frames; the level script's wave timer does the same]
//   - TurnOnAutoAttack: the attack begins 3 frames later [măsurat: first wave of the 13.3 replay, mid lane: the
//     timer frame at which the target stood in range + 3 frames, on three of four pairs; cause in the engine unknown]
//   - TurnOffAutoAttack(STOPREASON_MOVING) while it has a target: its path to the target is made again [măsurat: a
//     path to the target's new place on every timer frame while the target is out of the cancel range]
//   - the cancel range is the attack range + ar_StopAttackRangeModifier (GameModeConstants: 100) [dedus: the name]
//   - ranges (wakeUpRange, firstAcquisitionRange, acquisitionRange) are between centres [măsurat: one minion of the
//     first wave woke at 309 from the nearest enemy and not a timer frame earlier at 481, wakeUpRange 450]
//   - TARGET_ACQUISITION_MODE_DISTRIBUTE_FIRE: the target with the fewest allies already on it, then the nearest
//     [măsurat: first wave, mid lane: every melee minion took an enemy melee of its own, the second one 602 away
//     though the first, already taken, stood 296 away; the casters the same]. The mode's ai_TargetDistanceFactorPer
//     Attacker 0.8, ai_TargetDistanceFactorPerNeightbor 0.6, ai_TargetMaxNumAttackers 5 and ai_TargetRangeFactor 0.7
//     are surely this rule's numbers: how they enter is not known yet.
//   - who a unit prefers otherwise: the documented order (LoL Wiki, "Minion aggression"), as before
//   - the engine's calls not made yet: OnCollisionEnemy / OnCollisionOther, OnPathToTargetBlocked, taunt, fear, flee
//     and charm, OnCanMove / OnCanAttack.

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <set>

#include "Match.h"

extern "C" {
#include "lauxlib.h"
#include "lua.h"
#include "lualib.h"
}

namespace ba {

namespace {

int64_t ticks(double seconds) { return std::max<int64_t>(1, static_cast<int64_t>(std::ceil(seconds / kTickSeconds - 1e-9))); }
float distance(const Unit& a, const Unit& b) { return std::hypot(a.x - b.x, a.z - b.z); }

std::string lower(std::string s) {
  for (char& c : s) c = static_cast<char>(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
  return s;
}

/** The AI states, in the order of the scripts' own DEBUG_MINION_STATE_TABLE (turret.lua). */
const char* kAiStates[] = {
    "AI_IDLE", "AI_SOFTATTACK", "AI_HARDATTACK", "AI_ATTACKMOVESTATE", "AI_STANDING", "AI_MOVE", "AI_GUARD", "AI_ATTACK",
    "AI_RETREAT", "AI_HARDIDLE", "AI_HARDIDLE_ATTACKING", "AI_TAUNTED", "AI_BERSERK", "AI_ATTACKMOVE_ATTACKING", "AI_FEARED",
    "AI_CHARMED", "AI_FLEEING", "AI_ATTACK_GOING_TO_LAST_KNOWN_LOCATION", "AI_HALTED", "AI_SIEGEATTACK", "AI_LAST_NONPET_AI_STATE",
};
constexpr int kAttackMoveAttacking = 13, kTaunted = 11;
enum { kAcquireDefault = 0, kAcquireAsleep = 1, kAcquireDistributeFire = 2 };
enum { kStopImmediately = 0, kStopMoving = 1, kStopTargetLost = 2 };
/** Frames between TurnOnAutoAttack and the attack [măsurat, see the top of the file]. */
constexpr int64_t kAutoAttackLatency = 3;

// Points with arithmetic, the tags' numbers, and the numbers the engine knows its own names by. The areas are the
// navigation grid's main regions (0 the spawn platform, 1 the base, 2..4 the top / mid / bot lane); every other region
// has a number of its own there, none of them one of these five.
const char* kAiPrelude = R"(
local P = {}
P.__index = P
P.__add = function(a, b) return setmetatable({x = a.x + b.x, y = a.y + b.y, z = a.z + b.z}, P) end
P.__sub = function(a, b) return setmetatable({x = a.x - b.x, y = a.y - b.y, z = a.z - b.z}, P) end
function Make3DPoint(x, y, z) return setmetatable({x = x or 0, y = y or 0, z = z or 0}, P) end
UnitTagIndicies = setmetatable({}, {__index = function(t, name)
  local id = UnitTagIndex(name)
  rawset(t, name, id)
  return id
end})
TARGET_ACQUISITION_MODE_DEFAULT, TARGET_ACQUISITION_MODE_ASLEEP, TARGET_ACQUISITION_MODE_DISTRIBUTE_FIRE = 0, 1, 2
STOPREASON_IMMEDIATELY, STOPREASON_MOVING, STOPREASON_TARGET_LOST = 0, 1, 2
GameplayArea = 1
AREA_Platform, AREA_Base, AREA_Lane_Top, AREA_Lane_Mid, AREA_Lane_Bot = 0, 1, 2, 3, 4
)";

}  // namespace

/** The functions the AI scripts call. Units are their ids; "me" is the unit the engine called the script for. */
struct AiApi {
  static Match& match(lua_State* L) { return *static_cast<Match*>(lua_touserdata(L, lua_upvalueindex(1))); }
  static Unit* me(lua_State* L) {
    Match& m = match(L);
    return m.unit(m.ai_me_);
  }
  static Unit* unit(lua_State* L, int arg) { return lua_isnumber(L, arg) ? match(L).unit(static_cast<uint32_t>(lua_tonumber(L, arg))) : nullptr; }
  static int push_unit(lua_State* L, uint32_t id) {
    if (id) lua_pushnumber(L, id);
    else lua_pushnil(L);
    return 1;
  }
  static int push_point(lua_State* L, float x, float z) {
    lua_getglobal(L, "Make3DPoint");
    lua_pushnumber(L, x), lua_pushnumber(L, 0), lua_pushnumber(L, z);
    lua_call(L, 3, 1);
    return 1;
  }
  /** The unit tags a script names by their numbers ({UnitTagIndicies.X, ...}); anything else: none. */
  static std::vector<std::string> tags(lua_State* L, int arg) {
    std::vector<std::string> out;
    const Match& m = match(L);
    if (!lua_istable(L, arg)) return out;
    for (lua_pushnil(L); lua_next(L, arg) != 0; lua_pop(L, 1)) {
      const auto id = static_cast<size_t>(lua_tonumber(L, -1));
      if (id >= 1 && id <= m.unit_tag_names_.size()) out.push_back(m.unit_tag_names_[id - 1]);
    }
    return out;
  }
  static Unit::AiTimer* timer(Unit& u, const std::string& name) {
    for (Unit::AiTimer& t : u.ai_timers)
      if (t.name == name) return &t;
    return nullptr;
  }

  // ---- more of Riot's scripts
  static int DoLuaShared(lua_State* L) {
    Match& m = match(L);
    const std::string n = lower(luaL_checkstring(L, 1));
    for (const std::string& path : {"data/shared/scripts/" + n, "data/scripts/" + n, "data/shared/" + n}) {
      auto bytes = m.scripts_wad_ ? m.scripts_wad_->read(path + ".luabin64") : std::nullopt;
      if (!bytes) continue;
      if (luaL_loadbuffer(L, reinterpret_cast<const char*>(bytes->data()), bytes->size(), n.c_str()) != 0 || lua_pcall(L, 0, 0, 0) != 0) {
        std::fprintf(stderr, "ai script %s: %s\n", n.c_str(), lua_tostring(L, -1));
        lua_pop(L, 1);
      }
      return 0;
    }
    // "ObjectTags" is not among the client's scripts: what it would define (UnitTagIndicies) is the engine's here
    if (n != "objecttags") std::fprintf(stderr, "ai script: no %s\n", n.c_str());
    return 0;
  }
  static int UnitTagIndex(lua_State* L) {
    auto& names = match(L).unit_tag_names_;
    const std::string name = luaL_checkstring(L, 1);
    auto it = std::find(names.begin(), names.end(), name);
    if (it == names.end()) names.push_back(name), it = names.end() - 1;
    return lua_pushnumber(L, static_cast<lua_Number>(it - names.begin()) + 1), 1;
  }

  // ---- time and timers
  static int GetMissionTime(lua_State* L) { return lua_pushnumber(L, std::max(0.0, match(L).game_seconds())), 1; }
  static int InitTimer(lua_State* L) {
    Match& m = match(L);
    Unit* u = me(L);
    if (!u) return 0;
    const std::string name = luaL_checkstring(L, 1);
    const double secs = luaL_checknumber(L, 2);
    Unit::AiTimer* t = timer(*u, name);
    if (!t) u->ai_timers.push_back({}), t = &u->ai_timers.back();
    t->name = name, t->period = secs > 0 ? ticks(secs) : 1, t->repeat = lua_toboolean(L, 3) != 0, t->running = true;
    t->due = m.clock.tick + t->period;
    return 0;
  }
  static int StopTimer(lua_State* L) {
    Unit* u = me(L);
    if (Unit::AiTimer* t = u ? timer(*u, luaL_checkstring(L, 1)) : nullptr) t->running = false;
    return 0;
  }
  static int ResetAndStartTimer(lua_State* L) {
    Unit* u = me(L);
    if (Unit::AiTimer* t = u ? timer(*u, luaL_checkstring(L, 1)) : nullptr) t->running = true, t->due = match(L).clock.tick + t->period;
    return 0;
  }

  // ---- the unit's state
  static int GetState(lua_State* L) {
    const Unit* u = me(L);
    return lua_pushnumber(L, u ? u->ai_state : 0), 1;
  }
  static int SetState(lua_State* L) {
    if (Unit* u = me(L)) u->ai_state = static_cast<int>(luaL_checknumber(L, 1));
    return 0;
  }
  static int SetTargetAcquisitionMode(lua_State* L) {
    if (Unit* u = me(L)) u->acquisition_mode = static_cast<int>(luaL_checknumber(L, 1));
    return 0;
  }
  static int GetTargetAcquisitionMode(lua_State* L) {
    const Unit* u = me(L);
    return lua_pushnumber(L, u ? u->acquisition_mode : 0), 1;
  }
  static int SetGhostedForAllies(lua_State* L) {
    if (Unit* u = me(L)) u->ghosted = lua_toboolean(L, 1) != 0;
    return 0;
  }
  static int GetMinionLane(lua_State* L) {
    const Unit* u = me(L);
    return lua_pushnumber(L, u ? u->lane : -1), 1;
  }
  static int IsMoving(lua_State* L) {
    const Unit* u = me(L);
    return lua_pushboolean(L, u && !u->path.empty()), 1;
  }
  static int Nil(lua_State* L) { return lua_pushnil(L), 1; }

  // ---- targets
  static int find(lua_State* L, int which) {
    Match& m = match(L);
    const Unit* u = me(L);
    if (!u || !u->record) return lua_pushnil(L), 1;
    const float range = which == 1 ? u->record->wake_up_range : which == 2 ? u->record->first_acquisition_range : u->stats.acquisition_range;
    return push_unit(L, m.ai_find_target(*u, range, tags(L, 1), tags(L, 2)));
  }
  static int FindTargetInAcR(lua_State* L) { return find(L, 0); }
  static int FindTargetInWakeUpRange(lua_State* L) { return find(L, 1); }
  static int FindTargetInFirstAcquisitionRange(lua_State* L) { return find(L, 2); }
  static int GetTarget(lua_State* L) {
    const Unit* u = me(L);
    return push_unit(L, u ? u->target : 0);
  }
  static int SetTarget(lua_State* L) {
    Unit* u = me(L);
    const Unit* t = unit(L, 1);
    if (u) match(L).ai_set_target(*u, t ? t->id : 0);
    return 0;
  }
  static int AddToIgnore(lua_State* L) {
    Match& m = match(L);
    Unit* u = me(L);
    if (u && u->target) u->ai_ignored.push_back({u->target, m.clock.tick + ticks(luaL_checknumber(L, 1))});
    return 0;
  }
  static int IsHeroAI(lua_State* L) {
    const Unit* t = unit(L, 1);
    return lua_pushboolean(L, t && t->kind == UnitType::Champion), 1;
  }
  static int IsDead(lua_State* L) {
    const Unit* t = unit(L, 1);
    return lua_pushboolean(L, !t || t->dead), 1;
  }
  static int DistanceBetweenMeAndObject(lua_State* L) {
    const Unit* u = me(L);
    const Unit* t = unit(L, 1);
    return lua_pushnumber(L, u && t ? distance(*u, *t) : 1e9), 1;
  }
  static int in_range(lua_State* L, bool cancel) {
    const Match& m = match(L);
    const Unit* u = me(L);
    const Unit* t = u && u->target ? m.unit(u->target) : nullptr;
    if (!t) return lua_pushboolean(L, 0), 1;
    return lua_pushboolean(L, distance(*u, *t) <= m.reach(*u, *t) + (cancel ? m.constant("ar_StopAttackRangeModifier", 100) : 0.f)), 1;
  }
  static int TargetInAttackRange(lua_State* L) { return in_range(L, false); }
  static int TargetInCancelAttackRange(lua_State* L) { return in_range(L, true); }
  static int region(lua_State* L, const Unit* u) {
    const Match& m = match(L);
    if (!u || !m.nav_ || m.nav_->regions.empty() || m.nav_->cell_size <= 0) return lua_pushnumber(L, 2), 1;  // no grid: a lane
    const int cx = std::clamp(static_cast<int>((u->x - m.nav_->min_x) / m.nav_->cell_size), 0, static_cast<int>(m.nav_->cells_x) - 1);
    const int cz = std::clamp(static_cast<int>((u->z - m.nav_->min_z) / m.nav_->cell_size), 0, static_cast<int>(m.nav_->cells_z) - 1);
    return lua_pushnumber(L, m.nav_->regions[static_cast<size_t>(cz) * m.nav_->cells_x + static_cast<size_t>(cx)][1] >> 4), 1;
  }
  static int GetRegionTag(lua_State* L) { return region(L, unit(L, 1)); }
  static int GetMyRegionTag(lua_State* L) { return region(L, me(L)); }

  // ---- what it does
  static int SetStateAndCloseToTarget(lua_State* L) {
    Match& m = match(L);
    Unit* u = me(L);
    const Unit* t = unit(L, 2);
    if (!u) return 0;
    u->ai_state = static_cast<int>(luaL_checknumber(L, 1));
    u->forward_nav = false;
    m.ai_set_target(*u, t ? t->id : 0);
    if (t && m.ev_) m.ai_close(*u, *t, *m.ev_);
    return 0;
  }
  static int SetStateAndMoveToForwardNav(lua_State* L) {
    Match& m = match(L);
    Unit* u = me(L);
    if (!u) return 0;
    u->ai_state = static_cast<int>(luaL_checknumber(L, 1));
    u->forward_nav = true;
    if (m.ev_ && u->attack_start < 0) m.lane_walk(*u, *m.ev_);
    return 0;
  }
  static int SetStateAndMove(lua_State* L) {
    Match& m = match(L);
    Unit* u = me(L);
    if (!u) return 0;
    u->ai_state = static_cast<int>(luaL_checknumber(L, 1));
    u->forward_nav = false;
    if (lua_istable(L, 2) && m.ev_) {
      lua_getfield(L, 2, "x"), lua_getfield(L, 2, "z");
      m.path_to(*u, static_cast<float>(lua_tonumber(L, -2)), static_cast<float>(lua_tonumber(L, -1)), *m.ev_);
      lua_pop(L, 2);
    }
    return 0;
  }
  static int TurnOnAutoAttack(lua_State* L) {
    Match& m = match(L);
    Unit* u = me(L);
    const Unit* t = unit(L, 1);
    if (!u || !t) return 0;
    m.ai_set_target(*u, t->id);
    if (!u->auto_attack) u->auto_attack = true, u->auto_attack_tick = m.clock.tick + kAutoAttackLatency;
    return 0;
  }
  static int TurnOffAutoAttack(lua_State* L) {
    Match& m = match(L);
    Unit* u = me(L);
    if (!u) return 0;
    const int reason = static_cast<int>(luaL_optnumber(L, 1, kStopMoving));
    u->auto_attack = false;
    if (reason == kStopImmediately) u->attack_start = -1;
    const Unit* t = u->target ? m.unit(u->target) : nullptr;
    const bool closing = u->ai_state == kAttackMoveAttacking || u->ai_state == kTaunted;
    if (reason == kStopMoving && t && closing && !u->forward_nav && u->attack_start < 0 && m.ev_) m.ai_close(*u, *t, *m.ev_);
    return 0;
  }
  static int LastAutoAttackFinished(lua_State* L) {
    const Unit* u = me(L);
    return lua_pushboolean(L, !u || u->attack_start < 0), 1;
  }
  static int GetPos(lua_State* L) {
    const Unit* t = unit(L, 1);
    return t ? push_point(L, t->x, t->z) : (lua_pushnil(L), 1);
  }
  static int MyPoint(lua_State* L) {
    const Unit* u = me(L);
    return u ? push_point(L, u->x, u->z) : (lua_pushnil(L), 1);
  }
};

uint32_t Match::ai_find_target(const Unit& u, float range, const std::vector<std::string>& include, const std::vector<std::string>& exclude) const {
  auto has = [](const Unit& t, const std::vector<std::string>& tags) {
    if (!t.record) return false;
    const std::string all = " | " + t.record->tags + " | ";
    for (const std::string& tag : tags)
      if (all.find(" | " + tag + " | ") != std::string::npos) return true;
    return false;
  };
  // the documented order (LoL Wiki, "Minion aggression"): 1 an enemy champion attacking an allied champion, 2 an enemy
  // minion attacking an allied champion, 3 an enemy minion attacking an allied minion, 4 an enemy turret attacking an
  // allied minion, 5 an enemy champion attacking an allied minion, 6 the closest enemy minion, 7 the closest enemy
  // champion; then structures
  auto priority = [&](const Unit& t) {
    auto attacks_ally = [&](UnitType kind) {
      if (!t.target) return false;
      const Unit* v = unit(t.target);
      return v && v->team == u.team && v->kind == kind && attacking(t, *v);
    };
    if (t.kind == UnitType::Champion && attacks_ally(UnitType::Champion)) return 1;
    if (t.kind == UnitType::Minion && attacks_ally(UnitType::Champion)) return 2;
    if (t.kind == UnitType::Minion && attacks_ally(UnitType::Minion)) return 3;
    if (t.kind == UnitType::Turret && attacks_ally(UnitType::Minion)) return 4;
    if (t.kind == UnitType::Champion && attacks_ally(UnitType::Minion)) return 5;
    if (t.kind == UnitType::Minion) return 6;
    if (t.kind == UnitType::Champion) return 7;
    return 8;
  };
  const bool spread = u.acquisition_mode == kAcquireDistributeFire;
  int best_n = 1 << 30, best_p = 99;
  float best_d = 1e30f;
  uint32_t best = 0;
  for (const Unit& t : units) {
    if (!attackable(u, t)) continue;
    const float d = distance(u, t);
    if (d > range) continue;
    if (std::any_of(u.ai_ignored.begin(), u.ai_ignored.end(), [&](const Unit::AiIgnored& i) { return i.unit == t.id && i.until > clock.tick; })) continue;
    if (has(t, exclude) || (!include.empty() && !has(t, include))) continue;
    int n = 0;
    if (spread)
      for (const Unit& a : units) n += !a.dead && a.team == u.team && a.id != u.id && a.target == t.id;
    const int p = priority(t);
    if (n < best_n || (n == best_n && (p < best_p || (p == best_p && d < best_d)))) best_n = n, best_p = p, best_d = d, best = t.id;
  }
  return best;
}

void Match::ai_set_target(Unit& u, uint32_t target) {
  if (u.target == target) return;
  u.target = target;
  u.attack_start = -1;   // a new target: the windup under way is given up
  u.auto_attack = false;
}

void Match::ai_close(Unit& u, const Unit& t, MatchEvents& ev) {
  u.target_x = t.x, u.target_z = t.z;
  if (u.stats.move_speed <= 0) return;
  if (!nav_ || nav_->line_walkable(u.x, u.z, t.x, t.z, u.pathfinding_radius)) {
    u.path = {net::Point{t.x, t.z}};
    ev.path_changed.push_back(u.id);
  } else {
    path_to(u, t.x, t.z, ev);
  }
}

int Match::ai_script(const std::string& name) {
  for (size_t i = 0; i < ai_scripts_.size(); ++i)
    if (ai_scripts_[i].name == name) return ai_scripts_[i].L ? static_cast<int>(i) : -1;
  ai_scripts_.push_back({name, nullptr});
  auto bytes = scripts_wad_ ? scripts_wad_->read("data/scripts/" + lower(name) + ".luabin64") : std::nullopt;
  if (!bytes) {
    std::fprintf(stderr, "ai script: no %s\n", name.c_str());
    return -1;
  }
  lua_State* L = luaL_newstate();
  luaL_openlibs(L);
  static const luaL_Reg api[] = {
      {"DoLuaShared", AiApi::DoLuaShared}, {"UnitTagIndex", AiApi::UnitTagIndex}, {"GetMissionTime", AiApi::GetMissionTime},
      {"InitTimer", AiApi::InitTimer}, {"StopTimer", AiApi::StopTimer}, {"ResetAndStartTimer", AiApi::ResetAndStartTimer},
      {"GetState", AiApi::GetState}, {"SetState", AiApi::SetState}, {"NetSetState", AiApi::SetState},
      {"SetTargetAcquisitionMode", AiApi::SetTargetAcquisitionMode}, {"GetTargetAcquisitionMode", AiApi::GetTargetAcquisitionMode},
      {"SetGhostedForAllies", AiApi::SetGhostedForAllies}, {"GetMinionLane", AiApi::GetMinionLane}, {"IsMoving", AiApi::IsMoving},
      {"GetTauntTarget", AiApi::Nil}, {"GetCharmTarget", AiApi::Nil},
      {"FindTargetInAcR", AiApi::FindTargetInAcR}, {"FindTargetInAcRWithFilter", AiApi::FindTargetInAcR},
      {"FindTargetInWakeUpRangeWithFilter", AiApi::FindTargetInWakeUpRange},
      {"FindTargetInFirstAcquisitionRangeWithFilter", AiApi::FindTargetInFirstAcquisitionRange},
      {"GetTarget", AiApi::GetTarget}, {"SetTarget", AiApi::SetTarget}, {"AddToIgnore", AiApi::AddToIgnore},
      {"IsHeroAI", AiApi::IsHeroAI}, {"IsDead", AiApi::IsDead}, {"DistanceBetweenMeAndObject", AiApi::DistanceBetweenMeAndObject},
      {"TargetInAttackRange", AiApi::TargetInAttackRange}, {"TargetInCancelAttackRange", AiApi::TargetInCancelAttackRange},
      {"GetRegionTag", AiApi::GetRegionTag}, {"GetMyRegionTag", AiApi::GetMyRegionTag},
      {"SetStateAndCloseToTarget", AiApi::SetStateAndCloseToTarget}, {"SetStateAndMoveToForwardNav", AiApi::SetStateAndMoveToForwardNav},
      {"SetStateAndMove", AiApi::SetStateAndMove}, {"TurnOnAutoAttack", AiApi::TurnOnAutoAttack},
      {"TurnOffAutoAttack", AiApi::TurnOffAutoAttack}, {"LastAutoAttackFinished", AiApi::LastAutoAttackFinished},
      {"GetPos", AiApi::GetPos}, {"GetFearLeashPoint", AiApi::MyPoint}, {"MakeFleePoint", AiApi::MyPoint}, {"MakeWanderPoint", AiApi::MyPoint},
  };
  for (const luaL_Reg& f : api) {
    lua_pushlightuserdata(L, this);
    lua_pushcclosure(L, f.func, 1);
    lua_setglobal(L, f.name);
  }
  for (size_t i = 0; i < sizeof kAiStates / sizeof *kAiStates; ++i) lua_pushnumber(L, static_cast<lua_Number>(i)), lua_setglobal(L, kAiStates[i]);
  if (luaL_dostring(L, kAiPrelude) != 0) std::fprintf(stderr, "ai prelude: %s\n", lua_tostring(L, -1));
  if (luaL_loadbuffer(L, reinterpret_cast<const char*>(bytes->data()), bytes->size(), name.c_str()) != 0 || lua_pcall(L, 0, 0, 0) != 0) {
    std::fprintf(stderr, "ai script %s: %s\n", name.c_str(), lua_tostring(L, -1));
    lua_close(L);
    return -1;
  }
  ai_scripts_.back().L = L;
  return static_cast<int>(ai_scripts_.size()) - 1;
}

bool Match::ai_call(Unit& u, const char* fn, std::initializer_list<uint32_t> args) {
  if (u.ai < 0) return false;
  lua_State* L = ai_scripts_[static_cast<size_t>(u.ai)].L;
  lua_getglobal(L, fn);
  if (!lua_isfunction(L, -1)) return lua_pop(L, 1), false;
  const uint32_t before = ai_me_;
  ai_me_ = u.id;
  lua_pushnumber(L, u.id), lua_setglobal(L, "me");
  for (uint32_t a : args) AiApi::push_unit(L, a);
  const bool ok = lua_pcall(L, static_cast<int>(args.size()), 0, 0) == 0;
  if (!ok) {
    // each failure once: a missing engine function would otherwise be told for every minion on every frame
    static std::set<std::string> told;
    const std::string what = std::string(fn) + ": " + (lua_tostring(L, -1) ? lua_tostring(L, -1) : "?");
    if (told.insert(what).second) std::fprintf(stderr, "ai script %s %s\n", ai_scripts_[static_cast<size_t>(u.ai)].name.c_str(), what.c_str());
    lua_pop(L, 1);
  }
  ai_me_ = before;
  return ok;
}

void Match::ai_init(Unit& u, const std::string& script) {
  u.ai = ai_script(script);
  if (u.ai >= 0) ai_call(u, "OnInit");
}

void Match::ai_update(MatchEvents&) {
  for (size_t i = 0; i < units.size(); ++i) {
    Unit& u = units[i];
    if (u.ai < 0 || u.dead) continue;
    std::erase_if(u.ai_ignored, [&](const Unit::AiIgnored& x) { return x.until <= clock.tick; });
    // its target is gone (dead, or may no longer be attacked)
    if (u.target) {
      const Unit* t = unit(u.target);
      if (!t || !attackable(u, *t)) {
        u.target = 0, u.attack_start = -1, u.auto_attack = false;
        ai_call(u, "OnTargetLost");
      }
    }
    // its timers that are due, in the order the script made them
    for (size_t k = 0; k < u.ai_timers.size(); ++k) {
      Unit::AiTimer& t = u.ai_timers[k];
      if (!t.running || t.due > clock.tick) continue;
      const std::string name = t.name;
      if (t.repeat) t.due = clock.tick + t.period;
      else t.running = false;
      ai_call(u, name.c_str());
    }
  }
}

void Match::ai_call_for_help(const Unit& victim, const Unit& attacker) {
  for (size_t i = 0; i < units.size(); ++i) {
    Unit& u = units[i];
    if (u.ai < 0 || u.dead || u.team != victim.team || u.id == victim.id || u.target == attacker.id) continue;
    if (distance(u, attacker) > u.stats.acquisition_range || !attackable(u, attacker)) continue;
    ai_call(u, "OnCallForHelp", {victim.id, attacker.id});
  }
}

void Match::ai_close_scripts() {
  for (AiScript& s : ai_scripts_)
    if (s.L) lua_close(s.L);
  ai_scripts_.clear();
}

}  // namespace ba
