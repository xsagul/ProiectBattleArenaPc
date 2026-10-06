#pragma once
// What Summoner's Rift's game needs from the map's own data (patch 12.23), read where the game keeps it:
//   materials.bin (the geometry's): GdsMapObject placements: turrets (type 5), barracks = inhibitors (type 3), HQs =
//     nexuses (type 4), each naming the character and skin it stands for; the minions' spawn points
//     (__P_Order_Spawn_Barracks__C01), the lane waypoints (__NAV_L01 .., L = top, C = mid, R = bot).
//   the navigation grid: each structure's lane and tier (its footprint's region bytes, ba/MapObjects.h).
//   map11.bin: the CLASSIC mode's GameModeMapData: GameModeConstants (the server's own numbers), DeathTimes,
//     experience curve and split.
//   levels/map11/scene/cfg/objectcfg_srx.cfg (Map11LEVELS.wad): structures' health, regeneration, collision radius,
//     the turret rubble they turn into.
// In 12.23 the minion waves, upgrades and which structure may be attacked are not data: the server's level script
// decides them (Scripts.wad, levels/map11/scripts/levelscript_srx -> data/shared/scripts/sr_levelscript; see
// server/src/MatchLevel.cpp).

#include <array>
#include <cstdint>
#include <map>
#include <string>
#include <string_view>
#include <vector>

#include "ba/MapObjects.h"
#include "ba/PropertyBin.h"

namespace ba {

class NavGrid;

struct StructureSpawn {
  std::string object;     // the map object: "Turret_T1_C_03"
  std::string kind;       // "turret", "inhibitor", "nexus", "fountain"
  uint8_t team = 0;       // 0 Order, 1 Chaos
  int lane = -1;          // 0 bot, 1 mid, 2 top (the level script's RIGHT / CENTER / LEFT_LANE); -1 none
  // turrets, in the level script's numbering: FRONT_TOWER 3, MIDDLE_TOWER 2, BACK_TOWER 1, HQ_TOWER2 4, HQ_TOWER1 5
  int position = 0;
  std::string record;     // its CharacterRecord: "Characters/Turret/CharacterRecords/SR_Outer"
  std::string character;  // the character and skin it is drawn as (the map object's own)
  int skin = 0;
  float x = 0, z = 0, facing = 0;
  // from objectcfg; 0 when not given
  float max_hp = 0, hp_regen = 0, collision_radius = 0;
  std::string rubble;     // turrets: what they turn into (DestroyedTowerSkin, DestroyedTowerSkinID) ...
  int rubble_skin = 0;
  float rubble_after = 0; // ... SwapModelOnDeathTime seconds after they fall
};

struct MapGame {
  /** Every placed object of the map (the level script finds its turrets, camps and points among them by name). */
  std::vector<MapObject> objects;
  const MapObject* object(std::string_view name) const;
  /** The structures the engine places itself (inhibitors, nexuses), and the turret placements the level script's
   *  CreateChildTurret asks for (turrets: lane, position and record are the script's, left empty here). */
  std::vector<StructureSpawn> structures;
  std::array<std::array<std::array<float, 2>, 3>, 2> minion_spawn{};  // [team][lane] -> x, z
  std::array<std::vector<std::array<float, 2>>, 3> lanes;           // [lane] waypoints, Order's base to Chaos's
  std::array<std::array<float, 2>, 2> spawn_point{};  // [team] -> x, z: the __Spawn_T1 / __Spawn_T2 locators
  std::array<float, 2> spawn_facing{};
  /** The mode's DeathTimes: seconds dead by champion level, growing with the game's length. */
  struct DeathTimes {
    std::vector<float> per_level;                         // mTimeDeadPerLevel
    std::vector<std::array<float, 2>> scaling;            // mScalingPoints: from mStartTime, + mPercentIncrease ...
    float increment_secs = 30, cap = 1.5f;                // ... every mScalingIncrementTime; mScalingPercentCap
  } death_times;
  /** Seconds a champion of `level` stays dead when it dies `game_seconds` into the game. */
  float death_seconds(int level, double game_seconds) const;
  /** The mode's ExperienceCurveData mExperienceRequiredPerLevel: total experience at which level 2, 3 ... begin; and
   *  ExperienceModData mPlayerMinionSplitXp: the share each of 1, 2 ... champions near a dying minion gets. */
  std::vector<float> xp_required, xp_split;
  /** Global.wad `globals`, GlobalPerLevelStatsFactor mPerLevelStatsFactor: what part of a stat's per-level growth each
   *  level adds. */
  std::vector<float> level_factors;
  /** The sum of the factors of levels 2..`level`: how many "per level" amounts a champion of that level has. */
  float level_growth(int level) const;
  /** The CLASSIC mode's GameModeConstants, by the hash of each name ("dr_UnitToHero"). */
  std::map<uint32_t, float> constants;
  float constant(std::string_view name, float dflt) const;
};

/** Reads it all; `objectcfg` is the text of objectcfg_srx.cfg (may be empty), `nav` the map's grid (each structure's
 *  lane and tier; may be null). False when the map has no structures. */
bool read_map_game(const PropertyBin& materials, const PropertyBin& map_bin, const std::string& objectcfg, const NavGrid* nav,
                   MapGame& out);
/** The game-wide numbers of Global.wad's `globals` bin (the per-level stat factors). */
void read_globals(const PropertyBin& globals, MapGame& out);

}  // namespace ba
