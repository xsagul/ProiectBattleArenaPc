#pragma once
// Summoner's Rift's structures. Their placements are not in any client file (the game server holds them), but the
// navigation grid marks every structure's footprint (cells flagged 4, StructureWall): each structure stands at the
// centre of its footprint. The grid's region bytes under the footprint name it: nearest lane (team and lane), ring
// (outer / inner / inhibitor / nexus tier), main region (the spawn platform: the fountain turret); its size tells a
// nexus (~158 cells) from an inhibitor (44-61) from a turret (18-21).

#include <cstdint>
#include <string>
#include <vector>

#include "ba/NavGrid.h"
#include "ba/PropertyBin.h"

namespace ba {

struct MapStructure {
  uint8_t team = 0;        // 0 blue (Order, bottom left), 1 red (Chaos, top right)
  std::string kind;        // "turret", "inhibitor", "nexus", "fountain"
  std::string lane;        // "top", "mid", "bot" or ""
  std::string tier;        // turrets: "outer", "inner", "inhib", "nexus"
  float x = 0, z = 0;      // footprint centre (League units)
  int cells = 0;           // footprint size in grid cells
  std::string character;   // the character it is drawn as
  int skin = 0;            // and the skin (the Rift's: Turret 32 / 35, Inhibitor and Nexus 0 / 3)
  float facing = 0;        // radians, 0 = +z
};

/** Every structure of the map, from the grid's footprints (empty when the grid has none). */
std::vector<MapStructure> map_structures(const NavGrid& nav);

/** Where a team's champions appear: the map's "__Spawn_T1" (Order) / "__Spawn_T2" (Chaos) locators (GdsMapObject in
 *  the geometry's materials.bin). False when the map has none. */
struct SpawnPoint {
  float x = 0, y = 0, z = 0, facing = 0;
};
bool map_spawn_point(const PropertyBin& materials, uint8_t team, SpawnPoint& out);

/** A placed object of the map (GdsMapObject in the geometry's materials.bin): turrets (type 5), barracks
 *  (inhibitors, type 3), the minions' spawn points ("__P_Order_Spawn_Barracks__C01"), locators, props. */
struct MapObject {
  std::string name;
  int type = 0;
  std::string skin;  // the character and skin it stands for ({ad304db5}): "Characters/Turret/Skins/Skin3"; empty for locators
  float x = 0, y = 0, z = 0, facing = 0;  // the transform's translation; facing: atan2 of its +z axis
  float axis_z[3] = {0, 0, 1};             // the transform's +z axis (its third row), as it is (scale included)
  float box_min[3] = {0, 0, 0}, box_max[3] = {0, 0, 0};
  // mVisibilityFlags: which Rifts show it (bit 0 the plain one, the others the elemental ones); absent = all of them
  bool has_visibility_flags = false;
  uint32_t visibility_flags = 0;
  // the transform as the file has it: row vectors, rotation and scale in the first three rows, translation in the last
  float matrix[16] = {1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1};
  bool on_plain_rift() const { return !has_visibility_flags || (visibility_flags & 1u) != 0; }
};
std::vector<MapObject> map_objects(const PropertyBin& materials);

}  // namespace ba
