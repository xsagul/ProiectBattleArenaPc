#include "ba/MapGame.h"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdlib>
#include <map>
#include <sstream>

#include "ba/Hash.h"
#include "ba/MapObjects.h"
#include "ba/NavGrid.h"

namespace ba {

namespace {

double num(const BinValue* v, double dflt) { return v ? v->number() : dflt; }

/** "Characters/Turret/Skins/Skin32" -> ("Turret", 32). */
void parse_skin(const std::string& path, std::string& character, int& skin) {
  const size_t a = path.find('/'), b = a == std::string::npos ? a : path.find('/', a + 1);
  if (b == std::string::npos) return;
  character = path.substr(a + 1, b - a - 1);
  const size_t s = path.rfind("Skin");
  skin = s == std::string::npos ? 0 : std::atoi(path.c_str() + s + 4);
}

/** objectcfg_srx.cfg: [section] key=value lines. */
std::map<std::string, std::map<std::string, std::string>> parse_cfg(const std::string& text) {
  std::map<std::string, std::map<std::string, std::string>> out;
  std::istringstream in(text);
  std::string line, section;
  auto trim = [](std::string s) {
    while (!s.empty() && (s.back() == '\r' || s.back() == ' ' || s.back() == '\t')) s.pop_back();
    size_t i = 0;
    while (i < s.size() && (s[i] == ' ' || s[i] == '\t')) ++i;
    return s.substr(i);
  };
  while (std::getline(in, line)) {
    line = trim(line);
    if (line.size() > 2 && line.front() == '[' && line.back() == ']') {
      section = line.substr(1, line.size() - 2);
      continue;
    }
    const size_t eq = line.find('=');
    if (eq == std::string::npos || section.empty()) continue;
    out[section][trim(line.substr(0, eq))] = trim(line.substr(eq + 1));
  }
  return out;
}

int lane_of(char c) { return c == 'L' ? 2 : c == 'C' ? 1 : c == 'R' ? 0 : -1; }

}  // namespace

const MapObject* MapGame::object(std::string_view name) const {
  // names are matched without regard to case, as the game's own hashes are: the jungle script asks for "OrderOwlbear",
  // the map's locator is "OrderOwlBear"
  auto same = [](std::string_view a, std::string_view b) {
    if (a.size() != b.size()) return false;
    for (size_t i = 0; i < a.size(); ++i)
      if (std::tolower(static_cast<unsigned char>(a[i])) != std::tolower(static_cast<unsigned char>(b[i]))) return false;
    return true;
  };
  for (const MapObject& o : objects)
    if (same(o.name, name)) return &o;
  return nullptr;
}

float MapGame::constant(std::string_view name, float dflt) const {
  auto it = constants.find(fnv1a(name));
  return it == constants.end() ? dflt : it->second;
}

float MapGame::death_seconds(int level, double game_seconds) const {
  const auto& d = death_times;
  if (d.per_level.empty()) return 0;
  const float base = d.per_level[static_cast<size_t>(std::clamp(level, 1, static_cast<int>(d.per_level.size())) - 1)];
  // the documented formula (LoL Wiki, Death: base respawn wait x time increase factor) with the data's numbers: from
  // each scaling point's start, its percent is added every increment (15:00 0.425%, 30:00 0.3%, 45:00 1.45% per 30 s),
  // up to the cap (1.5: + 50%). mScalingStartTime / mScalingPercentIncrease (600 s, 0.5%) are not in the documented
  // formula: not applied [de măsurat]
  double factor = 0;
  for (size_t i = 0; i < d.scaling.size(); ++i) {
    const double from = d.scaling[i][0], to = i + 1 < d.scaling.size() ? d.scaling[i + 1][0] : 1e12;
    if (game_seconds <= from) break;
    factor += std::floor((std::min(game_seconds, to) - from) / std::max(1.f, d.increment_secs)) * d.scaling[i][1];
  }
  return base * static_cast<float>(std::min(1.0 + factor, static_cast<double>(std::max(1.f, d.cap))));
}

float MapGame::level_growth(int level) const {
  float sum = 0;
  for (int l = 2; l <= level; ++l) {
    // without the game's table: the documented 0.65 + 0.035 x level
    sum += static_cast<size_t>(l - 1) < level_factors.size() ? level_factors[static_cast<size_t>(l - 1)] : 0.65f + 0.035f * static_cast<float>(l);
  }
  return sum;
}

void read_globals(const PropertyBin& globals, MapGame& out) {
  for (const BinEntry& e : globals.entries())
    if (e.cls == fnv1a("GlobalPerLevelStatsFactor"))
      if (const BinValue* l = e.field("mPerLevelStatsFactor"))
        for (const BinValue& x : l->items) out.level_factors.push_back(static_cast<float>(x.number()));
}

bool read_map_game(const PropertyBin& materials, const PropertyBin& map_bin, const std::string& objectcfg, const NavGrid* nav,
                   MapGame& out) {
  // ---- the mode's constants: GameModeMapData (mModeName CLASSIC) -> mGameModeConstants -> mGroups -> mConstants
  for (const BinEntry& e : map_bin.entries()) {
    if (e.cls != fnv1a("GameModeMapData")) continue;
    const BinValue* mode = e.field("mModeName");
    const BinValue* link = e.field("mGameModeConstants");
    if (!mode || !link || !(mode->str == "CLASSIC" || mode->u == fnv1a("CLASSIC"))) continue;
    if (const BinValue* dl = e.field("mDeathTimes"))
      if (const BinEntry* d = map_bin.entry(static_cast<uint32_t>(dl->u))) {
        if (const BinValue* l = d->field("mTimeDeadPerLevel"))
          for (const BinValue& x : l->items) out.death_times.per_level.push_back(static_cast<float>(x.number()));
        if (const BinValue* l = d->field("mScalingPoints"))
          for (const BinValue& p : l->items)
            out.death_times.scaling.push_back({static_cast<float>(num(p.field("mStartTime"), 0)), static_cast<float>(num(p.field("mPercentIncrease"), 0))});
        out.death_times.increment_secs = static_cast<float>(num(d->field("mScalingIncrementTime"), 30));
        out.death_times.cap = static_cast<float>(num(d->field("mScalingPercentCap"), 1.5));
      }
    if (const BinValue* xl = e.field("mExperienceCurveData"))
      if (const BinEntry* x = map_bin.entry(static_cast<uint32_t>(xl->u)))
        if (const BinValue* l = x->field("mExperienceRequiredPerLevel"))
          for (const BinValue& v : l->items) out.xp_required.push_back(static_cast<float>(v.number()));
    if (const BinValue* xl = e.field("mExperienceModData"))
      if (const BinEntry* x = map_bin.entry(static_cast<uint32_t>(xl->u)))
        if (const BinValue* l = x->field("mPlayerMinionSplitXp"))
          for (const BinValue& v : l->items) out.xp_split.push_back(static_cast<float>(v.number()));
    const BinEntry* c = map_bin.entry(static_cast<uint32_t>(link->u));
    const BinValue* groups = c ? c->field("mGroups") : nullptr;
    if (!groups) continue;
    for (const auto& [gk, group] : groups->pairs)
      if (const BinValue* list = group.field("mConstants"))
        for (const auto& [key, value] : list->pairs)
          if (const BinValue* v = value.field("mValue"); v && v->type != BinType::String && v->items.empty())
            out.constants[static_cast<uint32_t>(key.u)] = static_cast<float>(v->number());
  }
  for (uint8_t t = 0; t < 2; ++t) {
    SpawnPoint sp;
    if (map_spawn_point(materials, t, sp)) out.spawn_point[t] = {sp.x, sp.z}, out.spawn_facing[t] = sp.facing;
  }

  // ---- each structure's lane and tier: the grid footprint nearest to it (ba/MapObjects.h)
  std::vector<MapStructure> footprints;
  if (nav) footprints = map_structures(*nav);
  auto footprint = [&](float x, float z) -> const MapStructure* {
    const MapStructure* best = nullptr;
    float bd = 1e30f;
    for (const MapStructure& f : footprints) {
      const float d = (f.x - x) * (f.x - x) + (f.z - z) * (f.z - z);
      if (d < bd) bd = d, best = &f;
    }
    return best && bd < 400.f * 400.f ? best : nullptr;
  };

  // ---- placements
  const auto cfgs = parse_cfg(objectcfg);
  std::map<int, std::vector<std::pair<int, std::array<float, 2>>>> lane_points;
  out.objects = map_objects(materials);
  // 12.23: the points the level scripts name (the jungle camps' "OrderBlueBuff1", "Baron1", "Dragon" ...) are the
  // MapLocators of map11.bin's MapLocatorArray, not objects of the geometry's bin. Without them the jungle script's
  // camp tables stayed empty and NeutralMinionInit stopped at its first camp.
  for (const BinEntry& e : map_bin.entries()) {
    const BinValue* locators = e.field("locators");
    if (!locators) continue;
    for (const BinValue& item : locators->items) {
      const BinValue* name = item.field("name");
      const BinValue* tr = item.field("transform");
      if (!name || !tr || out.object(name->str)) continue;
      MapObject o;
      o.name = name->str;
      const auto& M = tr->num;
      o.x = static_cast<float>(M[12]), o.y = static_cast<float>(M[13]), o.z = static_cast<float>(M[14]);
      o.facing = static_cast<float>(std::atan2(M[8], M[10]));
      for (int k = 0; k < 3; ++k) o.axis_z[k] = static_cast<float>(M[static_cast<size_t>(8 + k)]);
      for (size_t k = 0; k < 16; ++k) o.matrix[k] = static_cast<float>(M[k]);
      out.objects.push_back(std::move(o));
    }
  }
  for (const MapObject& o : out.objects) {
    const std::string& n = o.name;
    if (n.rfind("__NAV_", 0) == 0 && n.size() > 7) {
      lane_points[lane_of(n[6])].push_back({std::atoi(n.c_str() + 7), {o.x, o.z}});
      continue;
    }
    const std::string order = "__P_Order_Spawn_Barracks__", chaos = "__P_Chaos_Spawn_Barracks__";
    if (n.rfind(order, 0) == 0 || n.rfind(chaos, 0) == 0) {
      const int team = n.rfind(order, 0) == 0 ? 0 : 1, lane = lane_of(n[order.size()]);
      if (lane >= 0) out.minion_spawn[static_cast<size_t>(team)][static_cast<size_t>(lane)] = {o.x, o.z};
      continue;
    }
    StructureSpawn s;
    s.object = n;
    s.x = o.x, s.z = o.z, s.facing = o.facing;
    parse_skin(o.skin, s.character, s.skin);
    if (o.type == 5 && n.rfind("Turret_", 0) == 0) {
      s.kind = "turret";
      s.team = n.find("_T2_") != std::string::npos || n.find("Chaos") != std::string::npos ? 1 : 0;
      const MapStructure* f = footprint(o.x, o.z);
      if (n.find("Shrine") != std::string::npos || (f && f->kind == "fountain")) {
        // the fountain turrets: their own characters (the object's), their record that character's root
        s.kind = "fountain";
        s.record = "Characters/" + s.character + "/CharacterRecords/Root";
      } else if (f) {
        // the tier names the record: Characters/Turret/CharacterRecords/SR_Outer | SR_Inner | SR_Inhibitor | SR_Nexus
        // (the records Turret.bin holds for the Rift) [dedus din nume]
        static const std::map<std::string, std::pair<int, const char*>> kTier = {
            {"outer", {3, "SR_Outer"}}, {"inner", {2, "SR_Inner"}}, {"inhib", {1, "SR_Inhibitor"}}, {"nexus", {5, "SR_Nexus"}}};
        auto t = kTier.find(f->tier);
        if (t == kTier.end()) continue;
        s.position = t->second.first;
        s.record = "Characters/" + s.character + "/CharacterRecords/" + t->second.second;
        s.lane = f->lane == "top" ? 2 : f->lane == "bot" ? 0 : 1;
      } else {
        continue;
      }
    } else if (o.type == 3 && n.rfind("Barracks_", 0) == 0) {
      s.kind = "inhibitor";
      s.team = n.find("_T2_") != std::string::npos ? 1 : 0;
      s.lane = lane_of(n.size() > 12 ? n[12] : ' ');
      s.record = "Characters/" + s.character + "/CharacterRecords/Root";
    } else if (o.type == 4 && n.rfind("HQ_", 0) == 0) {
      s.kind = "nexus";
      s.team = n == "HQ_T2" ? 1 : 0;
      s.record = "Characters/" + s.character + "/CharacterRecords/Root";
    } else {
      continue;
    }
    auto c = cfgs.find(n);
    if (c != cfgs.end()) {
      auto get = [&c](const char* k) { auto it = c->second.find(k); return it == c->second.end() ? std::string() : it->second; };
      if (!get("mMaxHP").empty()) s.max_hp = static_cast<float>(std::atof(get("mMaxHP").c_str()));
      if (!get("mBaseStaticHPRegen").empty()) s.hp_regen = static_cast<float>(std::atof(get("mBaseStaticHPRegen").c_str()));
      if (!get("PathfindingCollisionRadius").empty()) s.collision_radius = static_cast<float>(std::atof(get("PathfindingCollisionRadius").c_str()));
      s.rubble = get("DestroyedTowerSkin");
      if (!get("DestroyedTowerSkinID").empty()) s.rubble_skin = std::atoi(get("DestroyedTowerSkinID").c_str());
      if (!get("SwapModelOnDeathTime").empty()) s.rubble_after = static_cast<float>(std::atof(get("SwapModelOnDeathTime").c_str()));
    }
    out.structures.push_back(std::move(s));
  }
  // the two nexus turrets of a team: HQ_TOWER1 (5) and HQ_TOWER2 (4), in the order of their object names; both
  // stand in the center lane for the level script (GetTurret(team, 1, HQ_TOWER1)) [dedus din script]
  for (uint8_t team = 0; team < 2; ++team) {
    std::vector<StructureSpawn*> hq;
    for (StructureSpawn& s : out.structures)
      if (s.kind == "turret" && s.team == team && s.position == 5) hq.push_back(&s);
    std::sort(hq.begin(), hq.end(), [](const StructureSpawn* a, const StructureSpawn* b) { return a->object < b->object; });
    for (size_t i = 0; i < hq.size(); ++i) hq[i]->position = i == 0 ? 5 : 4, hq[i]->lane = 1;
  }
  for (auto& [lane, pts] : lane_points) {
    if (lane < 0) continue;
    std::sort(pts.begin(), pts.end(), [](const auto& a, const auto& b) { return a.first < b.first; });
    for (const auto& p : pts) out.lanes[static_cast<size_t>(lane)].push_back(p.second);
  }
  return !out.structures.empty();
}

}  // namespace ba
