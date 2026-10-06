#include <algorithm>
#include "ba/MapObjects.h"

#include <cmath>
#include <map>

#include "ba/Hash.h"

namespace ba {

namespace {

struct Footprint {
  float x = 0, z = 0;
  int cells = 0;
  uint8_t lane = 0, ring = 0, region = 0;  // the commonest value under the footprint
};

std::vector<Footprint> footprints(const NavGrid& nav) {
  const int w = static_cast<int>(nav.cells_x), h = static_cast<int>(nav.cells_z);
  std::vector<uint8_t> seen(static_cast<size_t>(w) * static_cast<size_t>(h), 0);
  auto structure = [&](int i) { return (nav.cell_flags[static_cast<size_t>(i)] & 4) != 0; };
  std::vector<Footprint> out;
  for (int s = 0; s < w * h; ++s) {
    if (seen[static_cast<size_t>(s)] || !structure(s)) continue;
    std::vector<int> stack{s};
    seen[static_cast<size_t>(s)] = 1;
    double sx = 0, sz = 0;
    int n = 0;
    std::map<uint8_t, int> lanes, rings, regions;
    while (!stack.empty()) {
      const int c = stack.back();
      stack.pop_back();
      sx += c % w + 0.5, sz += c / w + 0.5, ++n;
      const auto& r = nav.regions[static_cast<size_t>(c)];
      ++lanes[r[2] & 15], ++rings[r[3] & 15], ++regions[r[1] >> 4];
      const int cx = c % w, cz = c / w;
      const int next[4][2] = {{cx + 1, cz}, {cx - 1, cz}, {cx, cz + 1}, {cx, cz - 1}};
      for (const auto& q : next) {
        if (q[0] < 0 || q[1] < 0 || q[0] >= w || q[1] >= h) continue;
        const int k = q[1] * w + q[0];
        if (!seen[static_cast<size_t>(k)] && structure(k)) seen[static_cast<size_t>(k)] = 1, stack.push_back(k);
      }
    }
    auto commonest = [](const std::map<uint8_t, int>& m) {
      uint8_t best = 0;
      int count = -1;
      for (const auto& [v, c] : m)
        if (c > count) best = v, count = c;
      return best;
    };
    Footprint f;
    f.x = nav.min_x + static_cast<float>(sx / n) * nav.cell_size;
    f.z = nav.min_z + static_cast<float>(sz / n) * nav.cell_size;
    f.cells = n;
    f.lane = commonest(lanes), f.ring = commonest(rings), f.region = commonest(regions);
    out.push_back(f);
  }
  return out;
}

}  // namespace

bool map_spawn_point(const PropertyBin& materials, uint8_t team, SpawnPoint& out) {
  const std::string want = team == 0 ? "__Spawn_T1" : "__Spawn_T2";
  for (const BinEntry& e : materials.entries()) {
    const BinValue* items = e.field("items");
    if (!items) continue;
    for (const auto& [key, item] : items->pairs) {
      if (item.cls != fnv1a("GdsMapObject")) continue;
      const BinValue* name = item.field("name");
      const BinValue* tr = item.field("transform");
      if (!name || !tr || name->str != want) continue;
      // League's matrix: row vectors, translation in the last row; +z of the locator is where it faces
      const auto& M = tr->num;
      out.x = static_cast<float>(M[12]), out.y = static_cast<float>(M[13]), out.z = static_cast<float>(M[14]);
      out.facing = static_cast<float>(std::atan2(M[8], M[10]));
      return true;
    }
  }
  return false;
}

std::vector<MapObject> map_objects(const PropertyBin& materials) {
  // The same object is listed by more than one container, with the same place but not the same rotation. The
  // MapContainer's chunks (the containers of the map as shipped, e.g. 14.1's {c6babea2}) win over the others (the
  // spawn scripts' RequiredLocations container, {2ad5bf8e} in 14.1) [măsurat: the chunk's turret yaws face their lanes
  // (red top outer -115, blue top outer 5) and are what the user recognised as the game's; the other container's
  // (45, -40) are not]
  std::vector<uint32_t> chunks;
  for (const BinEntry& e : materials.entries())
    if (e.cls == fnv1a("MapContainer"))
      if (const BinValue* c = e.field("chunks"))
        for (const auto& [key, v] : c->pairs) chunks.push_back(static_cast<uint32_t>(v.u));
  std::vector<const BinEntry*> order;
  for (const BinEntry& e : materials.entries())
    if (std::find(chunks.begin(), chunks.end(), e.name) != chunks.end()) order.push_back(&e);
  for (const BinEntry& e : materials.entries())
    if (std::find(chunks.begin(), chunks.end(), e.name) == chunks.end()) order.push_back(&e);
  std::vector<MapObject> out;
  std::vector<std::string> seen;
  for (const BinEntry* ep : order) {
    const BinEntry& e = *ep;
    const BinValue* items = e.field("items");
    if (!items) continue;
    for (const auto& [key, item] : items->pairs) {
      if (item.cls != fnv1a("GdsMapObject")) continue;
      const BinValue* name = item.field("name");
      const BinValue* tr = item.field("transform");
      if (!name || !tr) continue;
      if (std::find(seen.begin(), seen.end(), name->str) != seen.end()) continue;
      seen.push_back(name->str);
      MapObject o;
      o.name = name->str;
      if (const BinValue* t = item.field("type")) o.type = static_cast<int>(t->number());
      if (const BinValue* k = item.field(0xad304db5u)) o.skin = k->str;
      const auto& M = tr->num;
      o.x = static_cast<float>(M[12]), o.y = static_cast<float>(M[13]), o.z = static_cast<float>(M[14]);
      o.facing = static_cast<float>(std::atan2(M[8], M[10]));
      for (int k = 0; k < 3; ++k) o.axis_z[k] = static_cast<float>(M[static_cast<size_t>(8 + k)]);
      for (size_t k = 0; k < 16; ++k) o.matrix[k] = static_cast<float>(M[k]);
      if (const BinValue* vf = item.field("mVisibilityFlags")) o.has_visibility_flags = true, o.visibility_flags = static_cast<uint32_t>(vf->number());
      if (const BinValue* b = item.field("boxMin"))
        for (int k = 0; k < 3; ++k) o.box_min[k] = static_cast<float>(b->num[static_cast<size_t>(k)]);
      if (const BinValue* b = item.field("boxMax"))
        for (int k = 0; k < 3; ++k) o.box_max[k] = static_cast<float>(b->num[static_cast<size_t>(k)]);
      out.push_back(std::move(o));
    }
  }
  return out;
}

std::vector<MapStructure> map_structures(const NavGrid& nav) {
  std::vector<MapStructure> out;
  if (nav.regions.empty()) return out;
  for (const Footprint& f : footprints(nav)) {
    MapStructure s;
    s.x = f.x, s.z = f.z, s.cells = f.cells;
    // nearest lane: 0-2 Order's top / mid / bot, 3-5 Chaos's; ring: 0-4 Order's (spawn-nexus, nexus-inhib, inhib-inner,
    // inner-outer, outer-neutral), 5-9 Chaos's
    s.team = f.lane < 3 || (f.lane >= 6 && f.ring < 5) ? 0 : 1;
    static const char* kLanes[3] = {"top", "mid", "bot"};
    s.lane = kLanes[f.lane % 3];
    const int ring = f.ring % 5;
    if (f.cells > 100) {
      s.kind = "nexus", s.lane.clear();
    } else if (f.cells > 30) {
      s.kind = "inhibitor";
    } else if (f.region == 0) {
      s.kind = "fountain", s.lane.clear();  // main region 0: the spawn platform
    } else {
      s.kind = "turret";
      static const char* kTiers[4] = {"nexus", "inhib", "inner", "outer"};
      s.tier = kTiers[std::min(ring, 3)];
      if (ring == 0) s.lane.clear();
    }
    // skins: objectcfg_srx.cfg (the map's object config): Order's turrets / barracks / HQ skinID 0, Chaos's 3
    // (Turret_SR_Order_Blue / Turret_SR_Chaos_Red ...); the fountain turrets are their own characters, skin 0
    if (s.kind == "turret") s.character = "Turret", s.skin = s.team == 0 ? 0 : 3;
    if (s.kind == "inhibitor") s.character = "Inhibitor", s.skin = s.team == 0 ? 0 : 3;
    if (s.kind == "nexus") s.character = "Nexus", s.skin = s.team == 0 ? 0 : 3;
    if (s.kind == "fountain") s.character = s.team == 0 ? "SRUAP_Turret_Order5" : "SRUAP_Turret_Chaos5", s.skin = 0;
    out.push_back(s);
  }
  // which way a structure faces is in no client file: each faces the enemy nexus (our choice, docs/PROVENIENTA.md)
  float nx[2] = {0, 0}, nz[2] = {0, 0};
  for (const MapStructure& s : out)
    if (s.kind == "nexus") nx[s.team] = s.x, nz[s.team] = s.z;
  for (MapStructure& s : out) s.facing = std::atan2(nx[1 - s.team] - s.x, nz[1 - s.team] - s.z);
  return out;
}

}  // namespace ba
