// The level script: patch 12.23's own server script for Summoner's Rift, run as Riot shipped it. Scripts.wad holds
// the compiled Lua 5.1 (.luabin64) of levels/map11/scripts/levelscript_srx (the CLASSIC mode's LevelScriptFile
// mutator), which loads data/shared/scripts/sr_levelscript and globallevelscript. The script decides which structure
// may be hurt (SetInvulnerable / SetTargetable as turrets fall), the minion waves (GetMinionSpawnInfo: which minions,
// how many, with what health, damage, armor, gold and experience) and their upgrades (its timers). This file is the
// engine side: the functions the script calls and the moments the engine calls it.
//
// Engine behaviour the script does not show, our reading [dedus]:
//   - the barracks call GetInitSpawnInfo once and GetMinionSpawnInfo(lane, wave count, 0, team, wave id) before every
//     wave; the first wave comes at the script's INITIAL_TIME_TO_SPAWN, then every WaveSpawnRate ms; a wave's minions
//     come SingleMinionSpawnDelay ms apart, in SpawnOrderMinionNames order (checked on a 12.23 replay: 65.0 s, then
//     0.825 s apart, a wave every 30 s); the next wave is counted from the tick the last one went out [măsurat: the
//     13.3 replay's BarrackSpawnUnit, waves 30.000..30.033 s apart, minions 0.8225..0.8295 s apart];
//   - the third argument of GetMinionSpawnInfo is unused by the script: 0;
//   - timers count game seconds from the game's start; a timer due on a wave's tick runs before the wave;
//   - SetDisableMinionSpawn(barracks, seconds) is the time the lane's inhibitor stays down; when it is over the
//     inhibitor stands again and the engine calls BarrackReactiveEvent(team, lane);
//   - GetTotalTeamMinionsSpawned counts the lane minions alive; GetKeyLocation(0, team) is the team's nexus.
// Functions of the engine the script calls that we do not have yet are logged once (search "level script: missing").

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <set>

#include "Match.h"
#include "ba/Hash.h"

extern "C" {
#include "lstate.h"  // Lua's own call records: where each function of a failed call stood (see level_traceback)
}
#include "ba/PropertyBin.h"
#include "ba/Wad.h"

extern "C" {
#include "lauxlib.h"
#include "lua.h"
#include "lualib.h"
}

namespace ba {

namespace {

int64_t ticks(double seconds) { return std::max<int64_t>(1, static_cast<int64_t>(std::ceil(seconds / kTickSeconds - 1e-9))); }

constexpr int kTeamOrder = 100, kTeamChaos = 200;
int lua_team(uint8_t team) { return team == 0 ? kTeamOrder : kTeamChaos; }
int our_team(lua_Number t) { return static_cast<int>(t) == kTeamChaos ? 1 : static_cast<int>(t) == kTeamOrder ? 0 : -1; }
/** A barracks is not a unit of ours: its handle is this plus team x 3 + lane. */
constexpr uint32_t kBarracksHandle = 0x7f000000u;

std::string lower(std::string s) {
  for (char& c : s) c = static_cast<char>(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
  return s;
}

/** The engine's part of the Lua side: points with arithmetic (Make3DPoint), as the scripts use them. */
const char* kLevelPrelude = R"(
local P = {}
P.__index = P
P.__add = function(a, b) return setmetatable({x = a.x + b.x, y = a.y + b.y, z = a.z + b.z}, P) end
P.__sub = function(a, b) return setmetatable({x = a.x - b.x, y = a.y - b.y, z = a.z - b.z}, P) end
P.__mul = function(a, b)
  if type(a) == "number" then a, b = b, a end
  return setmetatable({x = a.x * b, y = a.y * b, z = a.z * b}, P)
end
function P:lengthSq() return self.x * self.x + self.y * self.y + self.z * self.z end
function P:length() return math.sqrt(self:lengthSq()) end
function Make3DPoint(x, y, z) return setmetatable({x = x or 0, y = y or 0, z = z or 0}, P) end
-- UnitTagIndicies.<tag>: the number the engine knows a unit tag by (HasUnitTag takes a list of them)
UnitTagIndicies = setmetatable({}, {__index = function(t, name)
  local id = UnitTagIndex(name)
  rawset(t, name, id)
  return id
end})
)";

/** Engine functions the 12.23 Summoner's Rift scripts call that we do not provide yet: each logs once when called. */
const char* kNotYet[] = {
    "AddToIgnore", "ApplyPersistentBuff", "ApplyPersistentBuffToAllChampions", "BBSpawnMinion",
    "ClientSide_CameraMoveCameraFromCurrentPositionToPoint", "ClientSide_PlaySoundFile", "CloseShop", "CreateNeutralCamp",
    "DisableHUDForEndOfGame", "EnableNeutralCampSoulStatus", "FadeMinions", "GetModePreloadFlags", "GetSelectedElementalTerrain", "GetUnitSkinName", "HaltAllAI",
    "HasUnitTag", "InitNeutralMinionTimer", "MoveCameraFromCurrentPositionToPoint", "NeutralMinionOverride",
    "NotifyGlobalEvent", "NotifyNeutralCampRewardGiven", "SetGreyscaleEnabledWhenDead", "SetHQCurrentSkin",
    "SetInputLockForAllClients", "SetMinionsNoRender", "SetModePreloadFlags", "SpawnMinion", "SpawnNeutralMinionWithSkin",
    "SpellBuffAdd", "UpdateNeutralCampMinimapIcon", "UpdateNeutralCampNextSpawnType", "SetBuildingHealthRegenEnabled", "GetEoGNexusChangeSkinTime", "GetEoGPanToHQTime",
    "GetEoGUseNexusDeathAnimation", "EndGame", "SetWinningTeam",
};

}  // namespace

/** The functions the level script calls. Units are their ids; barracks kBarracksHandle + team x 3 + lane. */
struct LevelApi {
  static Match& match(lua_State* L) {
    lua_getfield(L, LUA_REGISTRYINDEX, "Match");
    Match* m = static_cast<Match*>(lua_touserdata(L, -1));
    lua_pop(L, 1);
    return *m;
  }
  static Unit* unit(lua_State* L, int arg) {
    if (!lua_isnumber(L, arg)) return nullptr;
    return match(L).unit(static_cast<uint32_t>(lua_tonumber(L, arg)));
  }
  static int push_unit(lua_State* L, const Unit* u) {
    if (u) lua_pushnumber(L, u->id);
    else lua_pushnil(L);
    return 1;
  }
  static int push_point(lua_State* L, float x, float y, float z) {
    lua_getglobal(L, "Make3DPoint");
    lua_pushnumber(L, x), lua_pushnumber(L, y), lua_pushnumber(L, z);
    lua_call(L, 3, 1);
    return 1;
  }
  static Unit* find(lua_State* L, UnitType kind, int team, int lane, int position) {
    for (Unit& u : match(L).units)
      if (u.kind == kind && u.team == team && (lane < 0 || u.lane == lane) && (position < 0 || u.position == position)) return &u;
    return nullptr;
  }

  // ---- loading more of Riot's scripts
  static bool run_file(lua_State* L, const std::vector<std::string>& candidates) {
    Match& m = match(L);
    for (const std::string& c : candidates) {
      // BA_LUA_SRC=<folder of decompiled sources> (checks): the same script as text, so an error names its line
      if (const char* src = std::getenv("BA_LUA_SRC")) {
        const std::string path = std::string(src) + "/" + lower(c) + ".lua";
        // a decompiled file that is not valid Lua (the decompiler's gotos) is skipped: the game's own runs instead
        if (std::filesystem::exists(path) && (luaL_loadfile(L, path.c_str()) == 0 || (lua_pop(L, 1), false))) {
          if (lua_pcall(L, 0, 0, 0) != 0) {
            std::fprintf(stderr, "level script %s: %s\n", c.c_str(), lua_tostring(L, -1));
            lua_pop(L, 1);
          }
          return true;
        }
      }
      auto bytes = m.scripts_wad_ ? m.scripts_wad_->read(lower(c) + ".luabin64") : std::nullopt;
      if (!bytes) continue;
      if (luaL_loadbuffer(L, reinterpret_cast<const char*>(bytes->data()), bytes->size(), c.c_str()) != 0 || lua_pcall(L, 0, 0, 0) != 0) {
        std::fprintf(stderr, "level script %s: %s\n", c.c_str(), lua_tostring(L, -1));
        lua_pop(L, 1);
      }
      return true;
    }
    std::fprintf(stderr, "level script: no %s\n", candidates.empty() ? "?" : candidates.front().c_str());
    return false;
  }
  static int DoLuaShared(lua_State* L) {
    const std::string n = luaL_checkstring(L, 1);
    run_file(L, {"data/shared/scripts/" + n, "data/shared/" + n, "data/buildingblocks/" + n, "data/scripts/" + n});
    return 0;
  }
  static int DoLuaLevel(lua_State* L) {
    const std::string n = luaL_checkstring(L, 1);
    run_file(L, {"levels/map11/scripts/" + n, "data/buildingblocks/" + n, "data/shared/scripts/" + n});
    return 0;
  }
  static int LoadLevelScriptIntoScript(lua_State* L) {
    std::string n = luaL_checkstring(L, 1);
    if (n.size() > 4 && lower(n.substr(n.size() - 4)) == ".lua") n.resize(n.size() - 4);
    run_file(L, {"levels/map11/scripts/" + n, "data/scripts/" + n, "data/shared/scripts/" + n});
    return 0;
  }
  static int Log(lua_State* L) {
    if (std::getenv("BA_LEVEL_LOG")) std::fprintf(stderr, "level script: %s\n", luaL_optstring(L, 1, ""));
    return 0;
  }
  static int NotYet(lua_State* L) {
    static std::set<std::string> told;
    const std::string n = lua_tostring(L, lua_upvalueindex(2));
    if (told.insert(n).second) std::fprintf(stderr, "level script: missing engine function %s\n", n.c_str());
    return 0;
  }

  // ---- the mode, timers, world variables, chance
  static int GetMutatorParameterString(lua_State* L) {
    auto& mu = match(L).mutators_;
    auto it = mu.find(luaL_checkstring(L, 1));
    if (it == mu.end()) return lua_pushnil(L), 1;
    return lua_pushstring(L, it->second.c_str()), 1;
  }
  static int GetMutatorParameterBool(lua_State* L) {
    auto& mu = match(L).mutators_;
    auto it = mu.find(luaL_checkstring(L, 1));
    return lua_pushboolean(L, it != mu.end() && it->second != "0" && it->second != "false"), 1;
  }
  static int GetMutatorParameterInt(lua_State* L) {
    auto& mu = match(L).mutators_;
    auto it = mu.find(luaL_checkstring(L, 1));
    return lua_pushnumber(L, it == mu.end() ? 0 : std::atoi(it->second.c_str())), 1;
  }
  static int IsMutatorEnabled(lua_State* L) { return lua_pushboolean(L, match(L).mutators_.count(luaL_checkstring(L, 1)) != 0), 1; }
  static int InitTimer(lua_State* L) {
    Match& m = match(L);
    const std::string name = luaL_checkstring(L, 1);
    const double secs = luaL_checknumber(L, 2);
    const bool repeat = lua_toboolean(L, 3) != 0;
    const double now = std::max(0.0, m.game_seconds());
    auto it = std::find_if(m.level_timers_.begin(), m.level_timers_.end(), [&](const Match::LevelTimer& t) { return t.name == name; });
    if (it != m.level_timers_.end()) m.level_timers_.erase(it);
    m.level_timers_.push_back({name, now + secs, repeat ? secs : 0.0});
    return 0;
  }
  static int SetWorldVar(lua_State* L) {
    lua_getfield(L, LUA_REGISTRYINDEX, "WorldVars");
    lua_pushvalue(L, 1), lua_pushvalue(L, 2);
    lua_settable(L, -3);
    return lua_pop(L, 1), 0;
  }
  static int GetWorldVar(lua_State* L) {
    lua_getfield(L, LUA_REGISTRYINDEX, "WorldVars");
    lua_pushvalue(L, 1);
    lua_gettable(L, -2);
    return 1;
  }
  static int GetRandomIntLua(lua_State* L) {
    // the match's own random source, so that a recording replays the same [dedus: a value in 0 .. n - 1]
    const auto n = static_cast<uint32_t>(std::max<lua_Number>(1, luaL_optnumber(L, 1, 1)));
    return lua_pushnumber(L, match(L).random.next() % n), 1;
  }
  static int GetRandomIntInRangeLua(lua_State* L) {
    const int a = static_cast<int>(luaL_checknumber(L, 1)), b = static_cast<int>(luaL_checknumber(L, 2));
    const int lo = std::min(a, b), hi = std::max(a, b);
    return lua_pushnumber(L, lo + static_cast<int>(match(L).random.next() % static_cast<uint32_t>(hi - lo + 1))), 1;
  }

  // ---- the jungle script's helpers (sr_neutralminionspawn). Argument orders are the script's own calls.
  // SetBit(bit, flags) -> flags with the bit set; IsBitSet(bit, flags). [dedus: the bit's number is its position]
  static int IsBitSet(lua_State* L) {
    const auto bit = static_cast<uint32_t>(luaL_checknumber(L, 1)), flags = static_cast<uint32_t>(luaL_checknumber(L, 2));
    return lua_pushboolean(L, bit < 32 && ((flags >> bit) & 1u) != 0), 1;
  }
  static int SetBit(lua_State* L) {
    const auto bit = static_cast<uint32_t>(luaL_checknumber(L, 1)), flags = static_cast<uint32_t>(luaL_checknumber(L, 2));
    return lua_pushnumber(L, bit < 32 ? (flags | (1u << bit)) : flags), 1;
  }
  static int GetModePreloadFlags(lua_State* L) { return lua_pushnumber(L, match(L).preload_flags_), 1; }
  static int SetModePreloadFlags(lua_State* L) {
    match(L).preload_flags_ = static_cast<uint32_t>(luaL_checknumber(L, 1));
    return 0;
  }
  // no elemental terrain is chosen when a match starts [dedus: 0 stands for "none"; the engine's own value is not in
  // the data]
  static int GetSelectedElementalTerrain(lua_State* L) { return lua_pushnumber(L, 0), 1; }
  static int GetUnitSkinName(lua_State* L) {
    const Unit* u = unit(L, 1);
    return lua_pushstring(L, u ? u->skin.c_str() : ""), 1;
  }
  static int UnitTagIndex(lua_State* L) {
    auto& names = match(L).unit_tag_names_;
    const std::string name = luaL_checkstring(L, 1);
    auto it = std::find(names.begin(), names.end(), name);
    if (it == names.end()) names.push_back(name), it = names.end() - 1;
    return lua_pushnumber(L, static_cast<lua_Number>(it - names.begin()) + 1), 1;
  }
  // HasUnitTag(unit, {tag indices}): whether the unit's record carries any of the tags (unitTagsString: "A | B | C")
  static int HasUnitTag(lua_State* L) {
    const Match& m = match(L);
    const Unit* u = unit(L, 1);
    if (!u || !u->record || !lua_istable(L, 2)) return lua_pushboolean(L, 0), 1;
    const std::string tags = " | " + u->record->tags + " | ";
    bool has = false;
    for (lua_pushnil(L); !has && lua_next(L, 2) != 0; lua_pop(L, 1)) {
      const auto id = static_cast<size_t>(lua_tonumber(L, -1));
      if (id >= 1 && id <= m.unit_tag_names_.size()) has = tags.find(" | " + m.unit_tag_names_[id - 1] + " | ") != std::string::npos;
      if (has) lua_pop(L, 2);
    }
    return lua_pushboolean(L, has), 1;
  }
  // CreateNeutralCamp(camp table, camp number): the camp exists for the players (its minimap place)
  static int CreateNeutralCamp(lua_State* L) {
    Match::NeutralCamp c;
    c.index = static_cast<int>(luaL_optnumber(L, 2, 0));
    if (lua_istable(L, 1)) {
      lua_getfield(L, 1, "MinimapPosition");
      if (lua_istable(L, -1)) {
        lua_getfield(L, -1, "x"), c.x = static_cast<float>(lua_tonumber(L, -1)), lua_pop(L, 1);
        lua_getfield(L, -1, "z"), c.z = static_cast<float>(lua_tonumber(L, -1)), lua_pop(L, 1);
      }
      lua_pop(L, 1);
    }
    match(L).neutral_camps_.push_back(c);
    return 0;
  }

  // ---- the structures
  static int GetTurret(lua_State* L) {
    const int team = our_team(luaL_checknumber(L, 1));
    const int lane = static_cast<int>(luaL_checknumber(L, 2)), position = static_cast<int>(luaL_checknumber(L, 3));
    Unit* u = find(L, UnitType::Turret, team, position >= 4 ? -1 : lane, position);
    return push_unit(L, u && !u->dead ? u : nullptr);
  }
  static int GetDampener(lua_State* L) {
    return push_unit(L, find(L, UnitType::Inhibitor, our_team(luaL_checknumber(L, 1)), static_cast<int>(luaL_checknumber(L, 2)), -1));
  }
  static int GetHQ(lua_State* L) { return push_unit(L, find(L, UnitType::Nexus, our_team(luaL_checknumber(L, 1)), -1, -1)); }
  static int GetBarracks(lua_State* L) {
    const int team = our_team(luaL_checknumber(L, 1)), lane = static_cast<int>(luaL_checknumber(L, 2));
    return lua_pushnumber(L, kBarracksHandle + static_cast<uint32_t>(team * 3 + lane)), 1;
  }
  static int GetLinkedBarrack(lua_State* L) {
    const Unit* u = unit(L, 1);
    if (!u || u->kind != UnitType::Inhibitor) return lua_pushnil(L), 1;
    return lua_pushnumber(L, kBarracksHandle + static_cast<uint32_t>(u->team * 3 + u->lane)), 1;
  }
  static int GetTeamID(lua_State* L) {
    const auto h = static_cast<uint32_t>(luaL_optnumber(L, 1, 0));
    if (h >= kBarracksHandle && h < kBarracksHandle + 6) return lua_pushnumber(L, lua_team(static_cast<uint8_t>((h - kBarracksHandle) / 3))), 1;
    const Unit* u = unit(L, 1);
    return lua_pushnumber(L, u ? lua_team(u->team) : 0), 1;
  }
  static int GetLane(lua_State* L) {
    const Unit* u = unit(L, 1);
    return lua_pushnumber(L, u ? u->lane : -1), 1;
  }
  static int GetTurretPosition(lua_State* L) {
    const Unit* u = unit(L, 1);
    return lua_pushnumber(L, u ? u->position : -1), 1;
  }
  static int IsTurretAI(lua_State* L) {
    const Unit* u = unit(L, 1);
    return lua_pushboolean(L, u && u->kind == UnitType::Turret), 1;
  }
  static int IsDampener(lua_State* L) {
    const Unit* u = unit(L, 1);
    return lua_pushboolean(L, u && u->kind == UnitType::Inhibitor), 1;
  }
  static int GetDampenerType(lua_State* L) {
    // the script reads it back as team + lane (Order 100 + lane, Chaos 200 + lane); -1 when not an inhibitor
    const Unit* u = unit(L, 1);
    return lua_pushnumber(L, u && u->kind == UnitType::Inhibitor ? lua_team(u->team) + u->lane : -1), 1;
  }
  static int GetHQType(lua_State* L) {
    // ORDER_HQ 1, CHAOS_HQ 2 (the script's defines)
    const Unit* u = unit(L, 1);
    return lua_pushnumber(L, u && u->kind == UnitType::Nexus ? u->team + 1 : 0), 1;
  }
  static int GetUnitRef(lua_State* L) { return lua_pushvalue(L, 1), 1; }
  static int GetPosition(lua_State* L) {
    const Unit* u = unit(L, 1);
    return u ? push_point(L, u->x, 0.f, u->z) : (lua_pushnil(L), 1);
  }
  static int GetKeyLocation(lua_State* L) {
    const Unit* hq = find(L, UnitType::Nexus, our_team(luaL_checknumber(L, 2)), -1, -1);
    return hq ? push_point(L, hq->x, 0.f, hq->z) : (lua_pushnil(L), 1);
  }
  static int SetInvulnerable(lua_State* L) {
    if (Unit* u = unit(L, 1)) u->invulnerable = lua_toboolean(L, 2) != 0;
    return 0;
  }
  static int SetTargetable(lua_State* L) {
    if (Unit* u = unit(L, 1)) {
      u->targetable = lua_toboolean(L, 2) != 0;
      if (u->targetable) u->hidden_from = 0;
    }
    return 0;
  }
  static int SetNotTargetableToTeam(lua_State* L) {
    Unit* u = unit(L, 1);
    const int team = our_team(luaL_checknumber(L, 3));
    if (!u || team < 0) return 0;
    const auto bit = static_cast<uint8_t>(1u << team);
    u->hidden_from = lua_toboolean(L, 2) ? static_cast<uint8_t>(u->hidden_from | bit) : static_cast<uint8_t>(u->hidden_from & ~bit);
    return 0;
  }
  static int SetDisableMinionSpawn(lua_State* L) {
    Match& m = match(L);
    const auto h = static_cast<uint32_t>(luaL_checknumber(L, 1));
    if (h < kBarracksHandle || h >= kBarracksHandle + 6) return 0;
    for (Match::Barracks& b : m.barracks_)
      if (static_cast<uint32_t>(b.team * 3 + b.lane) == h - kBarracksHandle)
        b.disabled_until = std::max(0.0, m.game_seconds()) + luaL_checknumber(L, 2);
    return 0;
  }
  static int Nothing(lua_State*) { return 0; }
  /** CreateChildTurret(map object, character, record, team, position, lane): a turret of the level script's at the
   *  map object's place, its record Characters/<character>/CharacterRecords/<record> (Root when empty); skin and
   *  rubble from objectcfg. */
  static int CreateChildTurret(lua_State* L) {
    Match& m = match(L);
    const std::string object = luaL_checkstring(L, 1), character = luaL_checkstring(L, 2), record = luaL_optstring(L, 3, "");
    const int team = our_team(luaL_checknumber(L, 4));
    const int position = static_cast<int>(luaL_optnumber(L, 5, 0)), lane = static_cast<int>(luaL_optnumber(L, 6, -1));
    const StructureSpawn* where = nullptr;
    if (m.map_)
      for (const StructureSpawn& s : m.map_->structures)
        if (s.object == object) where = &s;
    if (!where || team < 0) return lua_pushnil(L), 1;
    for (const Unit& u : m.units)
      if (u.kind == UnitType::Turret || u.kind == UnitType::Fountain)
        if (std::hypot(u.x - where->x, u.z - where->z) < 1.f) return lua_pushnumber(L, u.id), 1;  // already standing
    Unit& u = m.spawn(static_cast<uint8_t>(team), character, where->x, where->z);
    // the skin: the map object's, when it stands for this character (the fountains' are not: the script's
    // SRUAP_MageCrystal stands where the object names SRUAP_Turret_Chaos5) [dedus]
    u.skin_id = static_cast<uint8_t>(where->character == character ? where->skin : 0);
    u.facing = where->facing;
    u.kind = position == 0 ? UnitType::Fountain : UnitType::Turret;
    u.lane = lane, u.position = position;
    m.set_record(u, m.record_at("Characters/" + character + "/CharacterRecords/" + (record.empty() ? std::string("Root") : record)));
    if (where->collision_radius > 0) u.stats.gameplay_radius = where->collision_radius;
    u.move_speed = u.stats.move_speed = 0;
    if (m.health_scale_ != 1.f && u.kind != UnitType::Fountain) u.stats.max_hp = u.hp = u.max_hp = u.max_hp * m.health_scale_;
    u.base = u.stats;
    u.invulnerable = true;  // until the script lets it be hurt (AllowDamageOnBuildings)
    if (m.ev_) m.ev_->spawned.push_back(u.id);
    return lua_pushnumber(L, u.id), 1;
  }
  static int FNVHash(lua_State* L) { return lua_pushnumber(L, fnv1a(luaL_checkstring(L, 1))), 1; }
  /** A placed point of the map by name (GdsMapObject): its position; FacingPosition: position + its +z axis. */
  static int Get3DPointPosition(lua_State* L) {
    const Match& m = match(L);
    const MapObject* o = m.map_ ? m.map_->object(luaL_checkstring(L, 1)) : nullptr;
    if (!o) {
      // a point the script names and the map does not have: said once (the script goes on with nil)
      static std::set<std::string> told;
      if (told.insert(lua_tostring(L, 1)).second) std::fprintf(stderr, "level script: no map point %s%c", lua_tostring(L, 1), 10);
    }
    return o ? push_point(L, o->x, o->y, o->z) : (lua_pushnil(L), 1);
  }
  static int Get3DPointFacingPosition(lua_State* L) {
    const Match& m = match(L);
    const MapObject* o = m.map_ ? m.map_->object(luaL_checkstring(L, 1)) : nullptr;
    return o ? push_point(L, o->x + o->axis_z[0], o->y + o->axis_z[1], o->z + o->axis_z[2]) : (lua_pushnil(L), 1);
  }

  // ---- units and champions
  static int GetTotalTeamMinionsSpawned(lua_State* L) {
    int n = 0;
    for (const Unit& u : match(L).units) n += u.kind == UnitType::Minion && !u.dead;
    return lua_pushnumber(L, n), 1;
  }
  static int LuaForEachChampion(lua_State* L) {
    Match& m = match(L);
    const int team = our_team(luaL_checknumber(L, 1));
    const std::string fn = luaL_checkstring(L, 2);
    std::vector<uint32_t> ids;
    for (const Unit& u : m.units)
      if (u.kind == UnitType::Champion && (team < 0 || u.team == team)) ids.push_back(u.id);
    for (uint32_t id : ids) {
      lua_getglobal(L, fn.c_str());
      if (!lua_isfunction(L, -1)) {
        lua_pop(L, 1);
        break;
      }
      lua_pushnumber(L, id);
      m.level_call(1, 0, fn.c_str());
    }
    return 0;
  }
  static int PreloadCharacter(lua_State* L) {
    // the record is read now, as the game reads the character before the match
    match(L).record_at("Characters/" + std::string(luaL_checkstring(L, 1)) + "/CharacterRecords/Root");
    return 0;
  }
};

const CharacterRecordData* Match::record_at(const std::string& path) {
  if (path.empty()) return nullptr;
  if (records_) {
    auto it = records_->find(path);
    if (it != records_->end()) return &it->second;
  }
  return record_source_ ? record_source_(path) : nullptr;
}

// The message handler of level-script calls. The game's scripts are stripped of line numbers, so each Lua function on
// the stack is given by its name, the line it was defined at (kept) and the index of the instruction it stood at: the
// place in a `luac -l` listing of the script.
static int level_traceback(lua_State* L) {
  std::string out = lua_tostring(L, 1) ? lua_tostring(L, 1) : "?";
  lua_Debug ar;
  for (int level = 1; lua_getstack(L, level, &ar); ++level) {
    lua_getinfo(L, "Sn", &ar);
    int pc = -1;
    const CallInfo* ci = L->base_ci + ar.i_ci;
    if (ttisfunction(ci->func) && !clvalue(ci->func)->c.isC) pc = static_cast<int>(ci->savedpc - clvalue(ci->func)->l.p->code) - 1;
    char line[256];
    std::snprintf(line, sizeof line, "\n\t%s function '%s' defined at line %d, instruction %d", ar.what, ar.name ? ar.name : "?", ar.linedefined, pc);
    out += line;
  }
  lua_pushstring(L, out.c_str());
  return 1;
}

bool Match::level_call(int args, int results, const char* what) {
  const int base = lua_gettop(LL_) - args;
  lua_pushcfunction(LL_, level_traceback);
  lua_insert(LL_, base);
  const int r = lua_pcall(LL_, args, results, base);
  lua_remove(LL_, base);
  if (r == 0) return true;
  std::fprintf(stderr, "level script %s: %s\n", what, lua_tostring(LL_, -1));
  lua_pop(LL_, 1);
  return false;
}

// The outer turrets' plating is a unit of its own. [măsurat: the packets of a real 12.23 match (research/replays1223,
// match 0): at time 0 the server spawns one minion named PreSeason_Turret_Shield at each of the six outer turrets'
// positions, not targetable, facing its team's spawn point (position2 - position1 is the unit vector towards
// __Spawn_T1 / __Spawn_T2 on all six); the two still standing die at 845.06 s. No script of the client's data creates
// it: the server's own code does.] Its skins [măsurat: the texture the 13.3 replay client binds on each side's
// turret]: 0 on Order's (Order_Blue, blue gems), 2 on Chaos's (named "Choas_Blue", its texture the red-gemmed
// ..._Skin02_Chaos_Red). Skins 1 and 3 are the other colour of each: what a Chaos player sees (not done yet).
void Match::spawn_turret_plating() {
  struct At {
    uint32_t turret;
    uint8_t team;
    float x, z;
  };
  std::vector<At> outer;
  for (const Unit& u : units)
    if (u.kind == UnitType::Turret && u.position == 3) outer.push_back({u.id, u.team, u.x, u.z});
  for (const At& a : outer) {
    Unit& p = spawn(a.team, "PreSeason_Turret_Shield", a.x, a.z);
    p.kind = UnitType::Other;
    p.plating = true;
    p.owner = a.turret;
    p.skin_id = a.team == 0 ? 0 : 2;
    p.targetable = false;
    p.invulnerable = true;
    p.move_speed = p.stats.move_speed = 0;
    if (map_) p.facing = std::atan2(map_->spawn_point[a.team][0] - a.x, map_->spawn_point[a.team][1] - a.z);
    if (ev_) ev_->spawned.push_back(p.id);
  }
}

void Match::level_run(const char* name) {
  if (!LL_) return;
  lua_getglobal(LL_, name);
  if (!lua_isfunction(LL_, -1)) return lua_pop(LL_, 1);
  level_call(0, 0, name);
}

void Match::load_level(const std::filesystem::path& data) {
  const auto final_dir = data / "DATA" / "FINAL";
  if (!std::filesystem::exists(final_dir / "Scripts.wad.client")) return;
  scripts_wad_ = std::make_unique<Wad>(final_dir / "Scripts.wad.client");

  // ---- the mode's mutator parameters: Global.wad's GameMutatorExpansions, "Default" then the mode's ("CLASSIC"), each
  // "Name(value)", "MapID(11)?Name(value)" only on map 11. The bin's path is not known by name: its entry hash.
  try {
    Wad global(final_dir / "Global.wad.client");
    if (auto bytes = global.read_hash(0xd109e1824a0373d3ull)) {
      const PropertyBin bin(*bytes);
      for (const char* mode : {"Default", "CLASSIC"})
        for (const BinEntry& e : bin.entries()) {
          const BinValue* name = e.field("mExpandedMutator");
          const BinValue* list = e.field("mMutators");
          if (!name || name->str != mode || !list) continue;
          for (const BinValue& v : list->items) {
            std::string s = v.str;
            const std::string map_prefix = "MapID(";
            if (s.rfind(map_prefix, 0) == 0) {
              const size_t q = s.find(")?");
              if (q == std::string::npos || s.substr(map_prefix.size(), q - map_prefix.size()) != "11") continue;
              s = s.substr(q + 2);
            }
            const size_t open = s.find('('), close = s.rfind(')');
            if (open == std::string::npos || close == std::string::npos || close < open) mutators_[s] = "1";
            else mutators_[s.substr(0, open)] = s.substr(open + 1, close - open - 1);
          }
        }
    }
  } catch (const std::exception& e) {
    std::fprintf(stderr, "mutators: %s\n", e.what());
  }

  LL_ = luaL_newstate();
  luaL_openlibs(LL_);
  lua_newtable(LL_);
  lua_setfield(LL_, LUA_REGISTRYINDEX, "WorldVars");
  lua_pushlightuserdata(LL_, this);
  lua_setfield(LL_, LUA_REGISTRYINDEX, "Match");
  if (luaL_dostring(LL_, kLevelPrelude) != 0) std::fprintf(stderr, "level prelude: %s\n", lua_tostring(LL_, -1));
  for (const char* n : kNotYet) {
    lua_pushlightuserdata(LL_, this);
    lua_pushstring(LL_, n);
    lua_pushcclosure(LL_, LevelApi::NotYet, 2);
    lua_setglobal(LL_, n);
  }
  static const luaL_Reg api[] = {
      {"DoLuaShared", LevelApi::DoLuaShared}, {"DoLuaLevel", LevelApi::DoLuaLevel},
      {"LoadLevelScriptIntoScript", LevelApi::LoadLevelScriptIntoScript}, {"Log", LevelApi::Log},
      {"GetMutatorParameterString", LevelApi::GetMutatorParameterString}, {"GetMutatorParameterBool", LevelApi::GetMutatorParameterBool},
      {"GetMutatorParameterInt", LevelApi::GetMutatorParameterInt}, {"IsMutatorEnabled", LevelApi::IsMutatorEnabled},
      {"InitTimer", LevelApi::InitTimer}, {"SetWorldVar", LevelApi::SetWorldVar}, {"GetWorldVar", LevelApi::GetWorldVar},
      {"IsBitSet", LevelApi::IsBitSet}, {"SetBit", LevelApi::SetBit}, {"GetModePreloadFlags", LevelApi::GetModePreloadFlags},
      {"SetModePreloadFlags", LevelApi::SetModePreloadFlags}, {"GetSelectedElementalTerrain", LevelApi::GetSelectedElementalTerrain},
      {"GetUnitSkinName", LevelApi::GetUnitSkinName}, {"UnitTagIndex", LevelApi::UnitTagIndex}, {"HasUnitTag", LevelApi::HasUnitTag},
      {"CreateNeutralCamp", LevelApi::CreateNeutralCamp},
      {"GetRandomIntLua", LevelApi::GetRandomIntLua}, {"GetRandomIntInRangeLua", LevelApi::GetRandomIntInRangeLua},
      {"GetTurret", LevelApi::GetTurret}, {"GetDampener", LevelApi::GetDampener}, {"GetHQ", LevelApi::GetHQ},
      {"GetBarracks", LevelApi::GetBarracks}, {"GetLinkedBarrack", LevelApi::GetLinkedBarrack}, {"GetTeamID", LevelApi::GetTeamID},
      {"GetLane", LevelApi::GetLane}, {"GetObjectLaneId", LevelApi::GetLane}, {"GetTurretPosition", LevelApi::GetTurretPosition},
      {"IsTurretAI", LevelApi::IsTurretAI}, {"IsDampener", LevelApi::IsDampener}, {"GetDampenerType", LevelApi::GetDampenerType},
      {"GetHQType", LevelApi::GetHQType}, {"GetUnitRef", LevelApi::GetUnitRef}, {"GetPosition", LevelApi::GetPosition},
      {"GetKeyLocation", LevelApi::GetKeyLocation}, {"SetInvulnerable", LevelApi::SetInvulnerable},
      {"SetTargetable", LevelApi::SetTargetable}, {"SetNotTargetableToTeam", LevelApi::SetNotTargetableToTeam},
      {"SetDisableMinionSpawn", LevelApi::SetDisableMinionSpawn}, {"SetDampenerRespawnAnimationDuration", LevelApi::Nothing},
      {"SetDampenerState", LevelApi::Nothing}, {"SetBarracksSpawnEnabled", LevelApi::Nothing},
      {"GetTotalTeamMinionsSpawned", LevelApi::GetTotalTeamMinionsSpawned}, {"LuaForEachChampion", LevelApi::LuaForEachChampion},
      {"PreloadCharacter", LevelApi::PreloadCharacter}, {"PreloadCharacterWithCFGSkin", LevelApi::PreloadCharacter},
      {"PreloadCharacterWithSkinID", LevelApi::PreloadCharacter}, {"CreateChildTurret", LevelApi::CreateChildTurret},
      {"FNVHash", LevelApi::FNVHash}, {"GetHashedGameObjName", LevelApi::FNVHash},
      {"Get3DPointPosition", LevelApi::Get3DPointPosition}, {"Get3DPointFacingPosition", LevelApi::Get3DPointFacingPosition},
  };
  for (const luaL_Reg& f : api) {
    lua_pushlightuserdata(LL_, this);
    lua_pushcclosure(LL_, f.func, 1);
    lua_setglobal(LL_, f.name);
  }

  // ---- the level's script (its main chunk calls Init), then the engine's load-time calls
  std::string file = mutators_.count("LevelScriptFile") ? mutators_["LevelScriptFile"] : "LevelScript.lua";
  if (file.size() > 4) file.resize(file.size() - 4);
  if (!LevelApi::run_file(LL_, {"levels/map11/scripts/" + file})) return;
  level_run("OnLevelInit");
  level_run("OnPostLevelLoad");
  spawn_turret_plating();

  lua_getglobal(LL_, "INITIAL_TIME_TO_SPAWN");
  first_wave_ = lua_tonumber(LL_, -1);
  lua_pop(LL_, 1);
  for (uint8_t team = 0; team < 2; ++team)
    for (int lane = 0; lane < 3; ++lane) {
      Barracks b;
      b.team = team, b.lane = lane;
      barracks_.push_back(b);
      lua_getglobal(LL_, "GetInitSpawnInfo");
      lua_pushnumber(LL_, lane), lua_pushnumber(LL_, lua_team(team));
      if (!level_call(2, 1, "GetInitSpawnInfo")) continue;
      if (lua_istable(LL_, -1)) {
        lua_getfield(LL_, -1, "WaveSpawnRate");
        if (lua_isnumber(LL_, -1)) wave_rate_ = lua_tonumber(LL_, -1) / 1000.0;
        lua_getfield(LL_, -2, "SingleMinionSpawnDelay");
        if (lua_isnumber(LL_, -1)) minion_delay_ = lua_tonumber(LL_, -1) / 1000.0;
        lua_pop(LL_, 2);
      }
      lua_pop(LL_, 1);
    }
}

void Match::level_start() {
  level_started_ = true;
  level_run("OnLevelInitServer");
  level_run("OnGameStartup");
}

void Match::barracks(MatchEvents& ev) {
  if (LL_ && start_tick_ >= 0) {
    const int64_t now = clock.tick;
    auto due = [&](double secs) { return start_tick_ + ticks(secs) <= now; };
    // ---- timers due, oldest first; each calls the global function of its name
    for (;;) {
      auto it = std::min_element(level_timers_.begin(), level_timers_.end(), [](const LevelTimer& a, const LevelTimer& b) { return a.at < b.at; });
      if (it == level_timers_.end() || !due(it->at)) break;
      const std::string name = it->name;
      if (it->every > 0) it->at += it->every;
      else level_timers_.erase(it);
      level_run(name.c_str());
    }
    // ---- inhibitors whose time down is over stand again: BarrackReactiveEvent(team, lane)
    for (Barracks& b : barracks_) {
      if (b.disabled_until < 0 || !due(b.disabled_until)) continue;
      b.disabled_until = -1;
      for (Unit& u : units)
        if (u.kind == UnitType::Inhibitor && u.team == b.team && u.lane == b.lane && u.dead) {
          u.dead = false, u.hp = u.max_hp, u.respawn_tick = -1;
          ev.respawned.push_back(u.id);
        }
      lua_getglobal(LL_, "BarrackReactiveEvent");
      lua_pushnumber(LL_, lua_team(b.team)), lua_pushnumber(LL_, b.lane);
      level_call(2, 0, "BarrackReactiveEvent");
    }
    // ---- a wave: every barracks asks the script what to put out
    if (first_wave_ > 0 && next_wave_ < 0) next_wave_ = first_wave_;
    if (first_wave_ > 0 && due(next_wave_)) {
      ++wave_id_;
      next_wave_ = static_cast<double>(now - start_tick_) * kTickSeconds + wave_rate_;
      for (Barracks& b : barracks_) {
        ++b.waves;
        lua_getglobal(LL_, "GetMinionSpawnInfo");
        lua_pushnumber(LL_, b.lane), lua_pushnumber(LL_, b.waves), lua_pushnumber(LL_, 0), lua_pushnumber(LL_, lua_team(b.team)),
            lua_pushnumber(LL_, wave_id_);
        if (!level_call(5, 1, "GetMinionSpawnInfo")) continue;
        const int info = lua_gettop(LL_);
        auto field = [&](int table, const char* name, float dflt) {
          lua_getfield(LL_, table, name);
          const float v = lua_isnumber(LL_, -1) ? static_cast<float>(lua_tonumber(LL_, -1)) : dflt;
          lua_pop(LL_, 1);
          return v;
        };
        const float exp_radius = field(info, "ExperienceRadius", 0);
        lua_getfield(LL_, info, "SpawnOrderMinionNames");
        lua_getfield(LL_, info, "MinionInfoTable");
        const int names = info + 1, table = info + 2;
        int order = 0;
        for (int i = 1; lua_istable(LL_, names) && lua_istable(LL_, table); ++i) {
          lua_rawgeti(LL_, names, i);
          if (!lua_isstring(LL_, -1)) {
            lua_pop(LL_, 1);
            break;
          }
          lua_gettable(LL_, table);  // MinionInfoTable[name]
          const int entry = lua_gettop(LL_);
          if (lua_istable(LL_, entry)) {
            lua_getfield(LL_, entry, "MinionName");
            const std::string character = lua_isstring(LL_, -1) ? lua_tostring(LL_, -1) : "";
            lua_pop(LL_, 1);
            const int count = static_cast<int>(field(entry, "NumPerWave", 0));
            for (int k = 0; k < count && !character.empty(); ++k)
              pending_minions_.push_back({now + (order++ == 0 ? 0 : ticks(minion_delay_ * (order - 1))), b.team, b.lane, character,
                                          field(entry, "HPBonus", 0), field(entry, "DamageBonus", 0), field(entry, "Armor", 0),
                                          field(entry, "MagicResistance", 0), field(entry, "MoveSpeedBaseIncrease", 0),
                                          field(entry, "GoldGiven", 0), field(entry, "ExpGiven", 0), exp_radius});
          }
          lua_pop(LL_, 1);
        }
        lua_settop(LL_, info - 1);
      }
    }
  }
  for (size_t i = 0; i < pending_minions_.size();) {
    if (pending_minions_[i].tick <= clock.tick) {
      spawn_minion(pending_minions_[i], ev);
      pending_minions_.erase(pending_minions_.begin() + static_cast<std::ptrdiff_t>(i));
    } else {
      ++i;
    }
  }
}

void Match::spawn_minion(const PendingMinion& p, MatchEvents& ev) {
  const CharacterRecordData* r = record_at("Characters/" + p.character + "/CharacterRecords/Root");
  if (!r || !map_) return;
  const auto& at = map_->minion_spawn[p.team][static_cast<size_t>(p.lane)];
  Unit& u = spawn(p.team, p.character, at[0], at[1]);
  u.kind = UnitType::Minion;
  u.lane = p.lane;
  set_record(u, r);
  // the level script's MinionInfoTable: its bonuses over the record, and what the minion is worth
  u.stats.max_hp += p.hp_bonus, u.stats.ad += p.damage_bonus, u.stats.armor += p.armor, u.stats.spell_block += p.spell_block;
  u.stats.move_speed += p.move_speed_bonus;
  u.hp = u.max_hp = u.stats.max_hp;
  u.move_speed = u.stats.move_speed;
  u.base = u.stats;
  u.gold_given = p.gold, u.exp_given = p.exp, u.exp_radius = p.exp_radius;
  // its lane's waypoints, walked from its own base (Order's from the start, Chaos's from the end)
  const auto& lane = map_->lanes[static_cast<size_t>(p.lane)];
  u.lane_point = p.team == 0 ? 0 : static_cast<int>(lane.size()) - 1;
  u.facing = lane.empty() ? 0.f : std::atan2(lane[static_cast<size_t>(u.lane_point)][0] - u.x, lane[static_cast<size_t>(u.lane_point)][1] - u.z);
  ev.spawned.push_back(u.id);
  // its AI: the game's lane minion script [dedus: the level script names none for the barracks' minions; minion.lua is
  // the lane minions' among data/scripts]. BA_OLD_MINION_AI (checks): our own earlier reading instead.
  if (!std::getenv("BA_OLD_MINION_AI")) ai_init(u, "Minion");
}

void Match::structure_destroyed(Unit& u) {
  if (!LL_) return;
  lua_getglobal(LL_, "HandleDestroyedObject");
  if (!lua_isfunction(LL_, -1)) return lua_pop(LL_, 1);
  lua_pushnumber(LL_, u.id);
  level_call(1, 0, "HandleDestroyedObject");
}

}  // namespace ba
