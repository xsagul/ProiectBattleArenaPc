#pragma once
// A map's navigation grid (.aimesh_ngrid, e.g. assets/maps/navgrid/map11/aipath_srx.aimesh_ngrid): what the game walks
// on. Pathing, walls, brush and the ground height every unit stands at all come from here, not from the visible mesh.
//
// Version 7 layout (checked against Summoner's Rift's file):
//   u8 major (7), u16 minor; Vec3 min bounds, Vec3 max bounds; f32 cell size, u32 cells x, u32 cells z;
//   cells x*z, 48 bytes each (f32 center height at 0, i16 x / i16 z at 20, the rest A* scratch state);
//   u16 vision/pathing flags per cell; 4 bytes of region flags per cell (see `regions`);
//   8 x 132 bytes; height samples: u32 count x, u32 count z, f32 spacing x, f32 spacing z, f32 heights[x*z].

#include <array>
#include <cstdint>
#include <filesystem>
#include <optional>
#include <span>
#include <string>
#include <utility>
#include <vector>

namespace ba {

class PropertyBin;
class Wad;

/** The navigation grid a map geometry's MapContainer names (<geometry>.materials.bin: MapNavGrid NavGridPath),
 *  lower-cased for the wad; empty when it names none. */
std::string navgrid_path(const PropertyBin& materials);

/** Summoner's Rift's navigation grid bytes from a game install: the MapContainer's MapNavGrid (14.x), else the one
 *  map11.bin's MapSkin names (mNavigationMesh, a file in Map11LEVELS.wad under levels/map11/ — 12.x). */
std::optional<std::vector<uint8_t>> read_map_navgrid(const std::filesystem::path& data);
std::optional<std::vector<uint8_t>> read_map_navgrid(const Wad& map_wad, const Wad* levels_wad);

class NavGrid {
 public:
  explicit NavGrid(std::span<const uint8_t> data);

  /** Ground height at a world point: bilinear over the height samples (League space, same units as the map). */
  float height(float x, float z) const;
  /** Vision / pathing flags of the cell under a world point. */
  uint16_t flags(float x, float z) const;

  /** Bit 2 is set on every cell a unit cannot stand on: terrain walls and the structures' footprints (those also carry
   *  4) alike. Bit 1 is brush, 64 a wall vision passes over (river cliffs). */
  static constexpr uint16_t kWall = 2;
  bool walkable(int cx, int cz) const;
  bool walkable_at(float x, float z) const;
  /** Walkable for a unit of pathfinding radius `r`: the cell's centre is at least `r` from every wall cell. */
  bool walkable(int cx, int cz, float r) const;
  bool walkable_at(float x, float z, float r) const;

  /** A path from `from` to `to` over walkable cells: A* on the grid (8 neighbours, no cutting wall corners), then
   *  straightened wherever a line between two waypoints stays on walkable cells. An unreachable or walled target
   *  moves to the nearest walkable cell. Empty when there is no way. Returns the waypoints after `from`. */
  std::vector<std::pair<float, float>> find_path(float from_x, float from_z, float to_x, float to_z, float radius = 0) const;
  /** True when the segment between two points crosses walkable cells only (for a unit of `radius`). */
  bool line_walkable(float ax, float az, float bx, float bz, float radius = 0) const;

  float min_x = 0, min_y = 0, min_z = 0, max_x = 0, max_y = 0, max_z = 0;
  float cell_size = 0;
  uint32_t cells_x = 0, cells_z = 0;
  std::vector<float> center_heights;
  std::vector<uint16_t> cell_flags;
  /** Per cell, 4 bytes: river region; jungle quadrant (low 4 bits) and main region (high: 0 spawn, 1 base, 2-4 top /
   *  mid / bot lane, ...); nearest lane (low: 0-2 Order's top / mid / bot, 3-5 Chaos's, 6-8 the neutral middles) and
   *  point of interest (high); ring (low: 0-4 Order's spawn-nexus, nexus-inhib, inhib-inner, inner-outer,
   *  outer-neutral, 5-9 Chaos's) and SRX flags (high). */
  std::vector<std::array<uint8_t, 4>> regions;
  /** Per cell: distance from its centre to the nearest wall cell (capped at kClearanceCap), for unit radii. */
  std::vector<float> clearance;
  static constexpr float kClearanceCap = 400;
  uint32_t samples_x = 0, samples_z = 0;
  float sample_dx = 0, sample_dz = 0;
  std::vector<float> samples;
};

}  // namespace ba
