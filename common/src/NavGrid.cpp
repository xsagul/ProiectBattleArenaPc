#include "ba/NavGrid.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <queue>
#include <tuple>
#include <stdexcept>
#include <string>

#include "ba/ByteReader.h"
#include "ba/Hash.h"
#include "ba/PropertyBin.h"
#include "ba/Wad.h"

namespace ba {

std::string navgrid_path(const PropertyBin& materials) {
  for (const BinEntry& e : materials.entries()) {
    const BinValue* components = e.field("components");
    if (!components) continue;
    for (const BinValue& c : components->items)
      if (c.cls == fnv1a("MapNavGrid"))
        if (const BinValue* p = c.field("NavGridPath")) {
          std::string s = p->str;
          for (char& ch : s) ch = static_cast<char>(ch >= 'A' && ch <= 'Z' ? ch - 'A' + 'a' : ch);
          return s;
        }
  }
  return {};
}

std::optional<std::vector<uint8_t>> read_map_navgrid(const Wad& map_wad, const Wad* levels) {
  if (auto mats = map_wad.read("data/maps/mapgeometry/map11/base_srx.materials.bin")) {
    const std::string path = navgrid_path(PropertyBin(*mats));
    if (!path.empty())
      if (auto bytes = map_wad.read(path)) return bytes;
  }
  // 12.x: map11.bin's MapSkin names the grid (mNavigationMesh "AIPath_SRX_2.aimesh_ngrid"), kept in Map11LEVELS.wad
  auto map = levels ? map_wad.read("data/maps/shipping/map11/map11.bin") : std::nullopt;
  if (!map) return std::nullopt;
  const PropertyBin bin(*map);
  for (const BinEntry& e : bin.entries())
    if (const BinValue* p = e.field("mNavigationMesh")) {
      std::string s = "levels/map11/" + p->str;
      for (char& ch : s) ch = static_cast<char>(ch >= 'A' && ch <= 'Z' ? ch - 'A' + 'a' : ch);
      if (auto bytes = levels->read(s)) return bytes;
    }
  return std::nullopt;
}

std::optional<std::vector<uint8_t>> read_map_navgrid(const std::filesystem::path& data) {
  const auto dir = data / "DATA" / "FINAL" / "Maps" / "Shipping";
  const Wad map_wad(dir / "Map11.wad.client");
  if (!std::filesystem::exists(dir / "Map11LEVELS.wad.client")) return read_map_navgrid(map_wad, nullptr);
  const Wad levels(dir / "Map11LEVELS.wad.client");
  return read_map_navgrid(map_wad, &levels);
}

NavGrid::NavGrid(std::span<const uint8_t> data) {
  ByteReader r(data);
  const uint8_t major = r.read<uint8_t>();
  r.read<uint16_t>();  // minor
  if (major != 7) throw std::runtime_error("ngrid: version " + std::to_string(major) + " is not supported");
  min_x = r.read<float>(), min_y = r.read<float>(), min_z = r.read<float>();
  max_x = r.read<float>(), max_y = r.read<float>(), max_z = r.read<float>();
  cell_size = r.read<float>();
  cells_x = r.read<uint32_t>();
  cells_z = r.read<uint32_t>();
  const size_t n = static_cast<size_t>(cells_x) * cells_z;
  center_heights.resize(n);
  for (size_t i = 0; i < n; ++i) {
    const size_t at = r.pos();
    center_heights[i] = r.read<float>();
    r.seek(at + 48);
  }
  cell_flags.resize(n);
  for (uint16_t& f : cell_flags) f = r.read<uint16_t>();
  // clearance: the distance from each cell's centre to the nearest point of a wall cell, up to the cap
  clearance.assign(n, kClearanceCap);
  const int w = static_cast<int>(cells_x), h = static_cast<int>(cells_z);
  const int reach = static_cast<int>(std::ceil(kClearanceCap / cell_size));
  for (int wz = 0; wz < h; ++wz)
    for (int wx = 0; wx < w; ++wx) {
      if (!(cell_flags[static_cast<size_t>(wz) * cells_x + static_cast<size_t>(wx)] & kWall)) continue;
      clearance[static_cast<size_t>(wz) * cells_x + static_cast<size_t>(wx)] = 0;
      for (int dz = -reach; dz <= reach; ++dz)
        for (int dx = -reach; dx <= reach; ++dx) {
          const int cx = wx + dx, cz = wz + dz;
          if (cx < 0 || cz < 0 || cx >= w || cz >= h) continue;
          // centre of (cx, cz) to the nearest point of the wall cell's square
          const float gx = std::max(0.f, (static_cast<float>(std::abs(dx)) - 0.5f) * cell_size);
          const float gz = std::max(0.f, (static_cast<float>(std::abs(dz)) - 0.5f) * cell_size);
          float& c = clearance[static_cast<size_t>(cz) * cells_x + static_cast<size_t>(cx)];
          c = std::min(c, std::sqrt(gx * gx + gz * gz));
        }
    }
  regions.resize(n);
  for (auto& reg : regions) r.read_into(reg.data(), 4);
  r.skip(8 * 132);  // unknown blocks
  samples_x = r.read<uint32_t>();
  samples_z = r.read<uint32_t>();
  sample_dx = r.read<float>();
  sample_dz = r.read<float>();
  samples.resize(static_cast<size_t>(samples_x) * samples_z);
  for (float& h : samples) h = r.read<float>();
}

float NavGrid::height(float x, float z) const {
  if (samples.empty() || sample_dx <= 0 || sample_dz <= 0) return 0;
  const float fx = std::clamp((x - min_x) / sample_dx, 0.f, static_cast<float>(samples_x - 1));
  const float fz = std::clamp((z - min_z) / sample_dz, 0.f, static_cast<float>(samples_z - 1));
  const uint32_t x0 = std::min(static_cast<uint32_t>(fx), samples_x - 2), z0 = std::min(static_cast<uint32_t>(fz), samples_z - 2);
  const float u = fx - static_cast<float>(x0), v = fz - static_cast<float>(z0);
  auto at = [&](uint32_t i, uint32_t j) { return samples[static_cast<size_t>(j) * samples_x + i]; };
  const float a = at(x0, z0) + (at(x0 + 1, z0) - at(x0, z0)) * u;
  const float b = at(x0, z0 + 1) + (at(x0 + 1, z0 + 1) - at(x0, z0 + 1)) * u;
  return a + (b - a) * v;
}

bool NavGrid::walkable(int cx, int cz) const {
  if (cx < 0 || cz < 0 || cx >= static_cast<int>(cells_x) || cz >= static_cast<int>(cells_z)) return false;
  return !(cell_flags[static_cast<size_t>(cz) * cells_x + static_cast<size_t>(cx)] & kWall);
}

bool NavGrid::walkable_at(float x, float z) const {
  return walkable(static_cast<int>(std::floor((x - min_x) / cell_size)), static_cast<int>(std::floor((z - min_z) / cell_size)));
}

bool NavGrid::walkable(int cx, int cz, float r) const {
  if (!walkable(cx, cz)) return false;
  return r <= 0 || clearance[static_cast<size_t>(cz) * cells_x + static_cast<size_t>(cx)] >= r;
}

bool NavGrid::walkable_at(float x, float z, float r) const {
  return walkable(static_cast<int>(std::floor((x - min_x) / cell_size)), static_cast<int>(std::floor((z - min_z) / cell_size)), r);
}

bool NavGrid::line_walkable(float ax, float az, float bx, float bz, float radius) const {
  // every cell the segment passes through (sampled at a quarter cell, which cannot skip a cell's corner by more)
  const float dx = bx - ax, dz = bz - az;
  const float len = std::sqrt(dx * dx + dz * dz);
  const int steps = std::max(1, static_cast<int>(std::ceil(len / (cell_size * 0.25f))));
  for (int i = 0; i <= steps; ++i) {
    const float t = static_cast<float>(i) / static_cast<float>(steps);
    if (!walkable_at(ax + dx * t, az + dz * t, radius)) return false;
  }
  return true;
}

std::vector<std::pair<float, float>> NavGrid::find_path(float fx, float fz, float tx, float tz, float radius) const {
  // a unit keeps its pathfinding radius from walls: every test below is for cells it can stand on
  auto walkable = [this, radius](int cx, int cz) { return NavGrid::walkable(cx, cz, radius); };
  const int w = static_cast<int>(cells_x), h = static_cast<int>(cells_z);
  auto cell_of = [&](float x, float z) {
    return std::pair<int, int>{std::clamp(static_cast<int>(std::floor((x - min_x) / cell_size)), 0, w - 1),
                               std::clamp(static_cast<int>(std::floor((z - min_z) / cell_size)), 0, h - 1)};
  };
  auto center = [&](int cx, int cz) {
    return std::pair<float, float>{min_x + (static_cast<float>(cx) + 0.5f) * cell_size, min_z + (static_cast<float>(cz) + 0.5f) * cell_size};
  };
  // the nearest walkable cell to a point (rings outward; ties go to the first found, rows then columns)
  auto nearest = [&](int cx, int cz) -> std::pair<int, int> {
    if (walkable(cx, cz)) return {cx, cz};
    for (int r = 1; r < std::max(w, h); ++r) {
      int best = -1;
      std::pair<int, int> pick{-1, -1};
      for (int dz = -r; dz <= r; ++dz)
        for (int dx = -r; dx <= r; ++dx) {
          if (std::max(std::abs(dx), std::abs(dz)) != r || !walkable(cx + dx, cz + dz)) continue;
          const int d = dx * dx + dz * dz;
          if (best < 0 || d < best) best = d, pick = {cx + dx, cz + dz};
        }
      if (best >= 0) return pick;
    }
    return {-1, -1};
  };

  auto [sx, sz] = nearest(cell_of(fx, fz).first, cell_of(fx, fz).second);
  auto [gx, gz] = cell_of(tx, tz);
  const bool exact = walkable(gx, gz);
  std::tie(gx, gz) = nearest(gx, gz);
  if (sx < 0 || gx < 0) return {};

  // ---- A*: octile distances, diagonal steps only between two open side cells
  const size_t n = static_cast<size_t>(w) * static_cast<size_t>(h);
  std::vector<float> g(n, INFINITY);
  std::vector<int32_t> came(n, -1);
  std::vector<uint8_t> closed(n, 0);
  struct Node {
    float f;
    uint32_t order;  // insertion order breaks ties, so the same query always gives the same path
    int32_t i;
    bool operator>(const Node& o) const { return f != o.f ? f > o.f : order > o.order; }
  };
  std::priority_queue<Node, std::vector<Node>, std::greater<>> open;
  uint32_t order = 0;
  auto heuristic = [&](int cx, int cz) {
    const float dx = static_cast<float>(std::abs(cx - gx)), dz = static_cast<float>(std::abs(cz - gz));
    return (dx + dz) + (1.41421356f - 2.f) * std::min(dx, dz);
  };
  const int32_t start = sz * w + sx, goal = gz * w + gx;
  g[static_cast<size_t>(start)] = 0;
  open.push({heuristic(sx, sz), order++, start});
  bool found = false;
  while (!open.empty()) {
    const Node cur = open.top();
    open.pop();
    const size_t ci = static_cast<size_t>(cur.i);
    if (closed[ci]) continue;
    closed[ci] = 1;
    if (cur.i == goal) {
      found = true;
      break;
    }
    const int cx = cur.i % w, cz = cur.i / w;
    for (int dz = -1; dz <= 1; ++dz)
      for (int dx = -1; dx <= 1; ++dx) {
        if (!dx && !dz) continue;
        const int nx = cx + dx, nz = cz + dz;
        if (!walkable(nx, nz)) continue;
        if (dx && dz && (!walkable(cx + dx, cz) || !walkable(cx, cz + dz))) continue;
        const size_t ni = static_cast<size_t>(nz) * static_cast<size_t>(w) + static_cast<size_t>(nx);
        if (closed[ni]) continue;
        const float cost = g[ci] + ((dx && dz) ? 1.41421356f : 1.f);
        if (cost < g[ni]) {
          g[ni] = cost;
          came[ni] = cur.i;
          open.push({cost + heuristic(nx, nz), order++, static_cast<int32_t>(ni)});
        }
      }
  }
  if (!found) return {};

  // ---- cells back to front, as points: the start, cell centers, the target (exact when it was walkable)
  std::vector<std::pair<float, float>> pts;
  for (int32_t i = goal; i != -1; i = came[static_cast<size_t>(i)]) pts.push_back(center(i % w, i / w));
  std::reverse(pts.begin(), pts.end());
  pts.front() = {fx, fz};
  if (exact) pts.back() = {tx, tz};
  if (pts.size() == 1) pts.push_back(exact ? std::pair<float, float>{tx, tz} : center(gx, gz));

  // ---- straighten: from each kept point, on to the last of the following points it still sees in a straight walkable line
  std::vector<std::pair<float, float>> out;
  size_t at = 0;
  while (at + 1 < pts.size()) {
    size_t next = at + 1;
    for (size_t k = at + 2; k < pts.size() && line_walkable(pts[at].first, pts[at].second, pts[k].first, pts[k].second, radius); ++k)
      next = k;
    out.push_back(pts[next]);
    at = next;
  }
  return out;
}

uint16_t NavGrid::flags(float x, float z) const {
  if (cell_flags.empty()) return 0;
  const int cx = std::clamp(static_cast<int>((x - min_x) / cell_size), 0, static_cast<int>(cells_x) - 1);
  const int cz = std::clamp(static_cast<int>((z - min_z) / cell_size), 0, static_cast<int>(cells_z) - 1);
  return cell_flags[static_cast<size_t>(cz) * cells_x + static_cast<size_t>(cx)];
}

}  // namespace ba
