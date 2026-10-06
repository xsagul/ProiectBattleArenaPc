// bainfo: League files through the game's own parsers.
//
//   bainfo wad <file.wad.client> [hashes.game.txt]                 list the entries (paths when the hash list is given)
//   bainfo bin <file.wad.client> <path of a .bin> [filter] [hash dir] dump the entries of a property bin
//   bainfo path <Map11.wad.client> x0 z0 x1 z1                       a path over base_srx's navigation grid, checked
//   bainfo findhash <file.wad.client> <hex hash> [hashes.game.txt]  the bins that mention a field / class / entry hash
//
// The hash dir holds CommunityDragon's hash lists (hashes.binentries.txt, hashes.binhashes.txt, hashes.bintypes.txt,
// hashes.binfields.txt), e.g. BattleArena/art/lol-data.

#include <cstdio>
#include <chrono>
#include <cstring>
#ifdef _WIN32
#include <d3dcompiler.h>
#endif
#include <filesystem>
#include <optional>
#include <vector>
#include <string>

extern "C" {
#include "lauxlib.h"
#include "lua.h"
#include "lualib.h"
}

#include "ba/HashNames.h"
#include "ba/MapGeometry.h"
#include "ba/MapGame.h"
#include "ba/MapObjects.h"
#include "ba/NavGrid.h"
#include "ba/Model.h"
#include "ba/Texture.h"
#include "ba/PropertyBin.h"
#include "ba/ShaderCache.h"
#include "ba/SpellData.h"
#include "ba/Hash.h"
#include "ba/ItemData.h"
#include "ba/CharacterData.h"
#include "ba/Wad.h"

using namespace ba;

namespace {

HashNames g_names;

void dump(const BinValue& v, int depth);

void indent(int depth) {
  for (int i = 0; i < depth; ++i) std::printf("  ");
}

void dump_fields(const std::vector<BinField>& fields, int depth) {
  for (const BinField& f : fields) {
    indent(depth);
    std::printf("%s: ", g_names.name32(f.name).c_str());
    dump(f.value, depth);
  }
}

void dump(const BinValue& v, int depth) {
  switch (v.type) {
    case BinType::String: std::printf("\"%s\"\n", v.str.c_str()); break;
    case BinType::Hash:
    case BinType::Link: std::printf("%s\n", g_names.name32(static_cast<uint32_t>(v.u)).c_str()); break;
    case BinType::File: std::printf("%s\n", g_names.name64(v.u).c_str()); break;
    case BinType::Vec2: std::printf("[%g, %g]\n", v.num[0], v.num[1]); break;
    case BinType::Vec3: std::printf("[%g, %g, %g]\n", v.num[0], v.num[1], v.num[2]); break;
    case BinType::Vec4:
    case BinType::RGBA: std::printf("[%g, %g, %g, %g]\n", v.num[0], v.num[1], v.num[2], v.num[3]); break;
    case BinType::Mtx4:
      std::printf("[mtx4");
      for (double x : v.num) std::printf(" %g", x);
      std::printf("]\n");
      break;
    case BinType::List:
    case BinType::List2:
    case BinType::Option:
      std::printf("[%zu]\n", v.items.size());
      for (const BinValue& x : v.items) {
        indent(depth + 1);
        dump(x, depth + 1);
      }
      break;
    case BinType::Map:
      std::printf("{%zu}\n", v.pairs.size());
      for (const auto& [k, x] : v.pairs) {
        indent(depth + 1);
        std::printf("key ");
        dump(k, depth + 1);
        indent(depth + 1);
        dump(x, depth + 1);
      }
      break;
    case BinType::Pointer:
    case BinType::Embed:
      if (!v.cls) {
        std::printf("null\n");
        break;
      }
      std::printf("%s\n", g_names.name32(v.cls).c_str());
      dump_fields(v.fields, depth + 1);
      break;
    default: std::printf("%g\n", v.num[0]); break;
  }
}

}  // namespace

int main(int argc, char** argv) {
  if (argc < 3) {
    std::fprintf(stderr, "usage: bainfo wad <file> [hashes.game.txt] | bainfo bin <file> <bin path> [filter] [hash dir]\n");
    return 2;
  }
  try {
    const std::string cmd = argv[1];
    Wad wad(argv[2]);
    if (cmd == "wad") {
      if (argc > 3) g_names.load(argv[3]);
      for (const auto& [h, e] : wad.entries()) std::printf("%s %u\n", g_names.name64(h).c_str(), e.size);
      std::printf("%zu entries\n", wad.entries().size());
      return 0;
    }
    if ((cmd == "tex" || cmd == "skn" || cmd == "skl" || cmd == "anm" || cmd == "mapgeo") && argc > 3) {
      auto bytes = wad.read(argv[3]);
      if (!bytes) {
        std::fprintf(stderr, "not in the archive: %s\n", argv[3]);
        return 1;
      }
      if (cmd == "tex") {
        Texture t = read_texture(*bytes);
        std::printf("%ux%u format %d, %zu mips, mip0 %zu bytes\n", t.width, t.height, static_cast<int>(t.format), t.mips.size(), t.mips[0].size());
        if (argc > 4) {  // bainfo tex <wad> <path> out.png: mip 0 as a PNG
          const std::string bytes_png = encode_png(t.width, t.height, texture_rgba(t));
          FILE* f = std::fopen(argv[4], "wb");
          if (!f) return 1;
          std::fwrite(bytes_png.data(), 1, bytes_png.size(), f);
          std::fclose(f);
        }
      } else if (cmd == "skn") {
        SkinMesh m = read_skn(*bytes);
        std::printf("%zu vertices, %zu indices\n", m.vertices.size(), m.indices.size());
        for (const SkinRange& s : m.ranges) std::printf("  %s: vertices %u+%u, indices %u+%u\n", s.material.c_str(), s.vertex_start, s.vertex_count, s.index_start, s.index_count);
        if (argc > 4) {  // bainfo skn <wad> <path> out.txt: per vertex "x y z  b0 b1 b2 b3  w0 w1 w2 w3"
          FILE* f = std::fopen(argv[4], "w");
          if (!f) return 1;
          for (const auto& v : m.vertices)
            std::fprintf(f, "%.3f %.3f %.3f  %d %d %d %d  %.3f %.3f %.3f %.3f\n", v.position[0], v.position[1], v.position[2], v.bones[0], v.bones[1], v.bones[2],
                         v.bones[3], v.weights[0], v.weights[1], v.weights[2], v.weights[3]);
          std::fclose(f);
        }
      } else if (cmd == "skl") {
        Skeleton s = read_skl(*bytes);
        std::printf("%zu joints, %zu influences\n", s.joints.size(), s.influences.size());
        for (size_t i = 0; i < s.joints.size() && i < 8; ++i)
          std::printf("  %s parent %d t(%.2f %.2f %.2f) r(%.3f %.3f %.3f %.3f)\n", s.joints[i].name.c_str(), s.joints[i].parent, s.joints[i].translate[0],
                      s.joints[i].translate[1], s.joints[i].translate[2], s.joints[i].rotate[0], s.joints[i].rotate[1], s.joints[i].rotate[2], s.joints[i].rotate[3]);
      } else if (cmd == "anm") {
        Animation a = read_anm(*bytes);
        size_t keys = 0;
        for (const Track& t : a.tracks) keys += t.translate.size() + t.rotate.size() + t.scale.size();
        std::printf("%s, %.1f fps, %.2f frames (%.3f s), %zu tracks, %zu keys\n", a.compressed ? "compressed" : "uncompressed", a.fps, a.frames, a.seconds(), a.tracks.size(), keys);
      } else {
        MapGeometry g = read_mapgeo(*bytes);
        size_t base = 0, subs = 0;
        for (const GeoModel& m : g.models) {
          if (m.layers & 1) ++base;
          subs += m.submeshes.size();
        }
        std::printf("version %u, %zu layouts, %zu vertex buffers, %zu index buffers, %zu models (%zu on layer 1), %zu submeshes\n", g.version,
                    g.layouts.size(), g.vertex_buffers.size(), g.index_buffers.size(), g.models.size(), base, subs);
        if (!g.models.empty()) std::printf("model 0: %s, %u vertices, %u indices\n", g.models[0].submeshes.empty() ? "-" : g.models[0].submeshes[0].material.c_str(), g.models[0].vertex_count, g.models[0].index_count);
      }
      return 0;
    }
    if (cmd == "spells" && argc > 3) {
      // bainfo spells <champion wad> <Champion> [all]: the four spells and the passive as the reader sees them (every
      // spell object with `all`), with each calculation worked out for a champion with 100 attack damage (50 of it
      // bonus) and 100 ability power, at level 1 / rank 1 and level 18 / top rank
      const std::string character = argv[3];
      const bool all = argc > 4;
      CharacterRecordData rec;
      read_character_record(wad, character, rec);
      const auto spells = read_spells(wad, character);
      std::vector<std::string> names;
      for (const std::string& s : rec.spells) names.push_back(s.substr(s.rfind('/') + 1));
      if (all) {
        names.clear();
        for (const auto& [n, s] : spells) names.push_back(n);
      }
      SpellCaster low, high;
      low.level = 1, high.level = 18;
      low.stat = high.stat = [](int stat, int formula) {
        if (stat == kStatAttackDamage) return formula == kFormulaBonus ? 50.f : formula == kFormulaBase ? 50.f : 100.f;
        if (stat == kStatAbilityPower) return 100.f;
        if (stat == kStatMaxHealth) return 2000.f;
        return 0.f;
      };
      for (const std::string& n : names) {
        auto it = spells.find(n);
        if (it == spells.end()) {
          std::printf("%s: not found\n", n.c_str());
          continue;
        }
        const SpellData& s = it->second;
        if (!s.has_spell) {
          std::printf("%s: no spell data\n", n.c_str());
          continue;
        }
        const int top = n == rec.spells[3].substr(rec.spells[3].rfind('/') + 1) ? 3 : 5;
        std::printf("%s: %s, animation %s, cast time %.3f s, missile speed %.0f width %.0f\n", n.c_str(), s.targeting_name.c_str(), s.animation.c_str(),
                    s.cast_time, s.missile_speed, s.line_width);
        std::printf("  cooldown %g..%g, mana %g..%g, range %g, radius %g\n", s.cooldown[1], s.cooldown[static_cast<size_t>(top)], s.mana[1],
                    s.mana[static_cast<size_t>(top)], s.range[1], s.radius[1]);
        std::printf("  ranks cooldown");
        for (int r = 1; r <= top; ++r) std::printf(" %g", s.cooldown[static_cast<size_t>(r)]);
        std::printf(" mana");
        for (int r = 1; r <= top; ++r) std::printf(" %g", s.mana[static_cast<size_t>(r)]);
        std::printf("\n");
        for (const std::string& v : s.value_names) {
          const auto& a = s.values.at(fnv1a(v));
          std::printf("  %-28s", v.c_str());
          for (int r = 1; r <= top; ++r) std::printf(" %g", a[static_cast<size_t>(r)]);
          std::printf("\n");
        }
        for (size_t i = 0; i < s.effects.size(); ++i) {
          bool any = false;
          for (float x : s.effects[i]) any |= x != 0;
          if (!any) continue;
          std::printf("  effect %zu                    ", i + 1);
          for (int r = 1; r <= top; ++r) std::printf(" %g", s.effects[i][static_cast<size_t>(r)]);
          std::printf("\n");
        }
        for (const auto& [key, calc] : s.calcs) {
          std::printf("  = %-26s %g .. %g", g_names.name32(key).c_str(), spell_calc(s, key, 1, low), spell_calc(s, key, top, high));
          std::function<void(const CalcPart&)> unknown = [&](const CalcPart& p) {
            if (p.kind == CalcPart::Kind::Unknown) std::printf("  [part %s not read]", g_names.name32(p.cls).c_str());
            for (const CalcPart& x : p.parts) unknown(x);
          };
          for (const CalcPart& p : calc.parts) unknown(p);
          if (calc.has_multiplier) unknown(calc.multiplier);
          std::printf("\n");
        }
      }
      std::printf("passive icon %s\n", rec.passive_icon.c_str());
      return 0;
    }
    if (cmd == "items" && argc > 3) {
      // bainfo items <Global.wad> <Map11.wad>: every item the CLASSIC mode sells, with its total cost and stats
      ItemTable t;
      if (!read_items(wad, t)) {
        std::fprintf(stderr, "no items\n");
        return 1;
      }
      Wad map(argv[3]);
      if (auto m = map.read("data/maps/shipping/map11/map11.bin")) read_mode_items(PropertyBin(*m), "CLASSIC", t);
      std::printf("%zu items, %zu groups, %zu sold by CLASSIC\n", t.items.size(), t.groups.size(), t.mode_items.size());
      for (int id : t.mode_items) {
        const ItemDef& d = t.items.at(id);
        std::printf("%6d %-28s total %5d (price %4d) store %d sell %.2f groups %zu comps", id, d.name_key.c_str(), t.total_cost(id), d.price, d.in_store,
                    d.sell_back, d.groups.size());
        for (int c : d.components) std::printf(" %d", c);
        std::printf(" | hp %.0f ad %.0f ap %.0f ar %.0f mr %.0f as %.2f crit %.2f ms %.0f/%.2f mana %.0f ah %.0f\n", d.stats.hp, d.stats.ad, d.stats.ap,
                    d.stats.armor, d.stats.spell_block, d.stats.attack_speed_pct, d.stats.crit, d.stats.move_speed, d.stats.move_speed_pct, d.stats.mana,
                    d.stats.ability_haste);
      }
      return 0;
    }
    if (cmd == "mapgame" && argc > 3) {
      // bainfo mapgame <Map11.wad> <Map11LEVELS.wad>: the game the map's data sets up
      auto mats = wad.read("data/maps/mapgeometry/map11/base_srx.materials.bin");
      auto map = wad.read("data/maps/shipping/map11/map11.bin");
      std::string cfg;
      Wad levels(argv[3]);
      if (auto c = levels.read("levels/map11/scene/cfg/objectcfg_srx.cfg")) cfg.assign(c->begin(), c->end());
      if (!mats || !map) return 1;
      MapGame g;
      Wad levels_wad(argv[3]);
      const auto nav_bytes = read_map_navgrid(wad, &levels_wad);
      const std::unique_ptr<NavGrid> nav = nav_bytes ? std::make_unique<NavGrid>(*nav_bytes) : nullptr;
      if (!read_map_game(PropertyBin(*mats), PropertyBin(*map), cfg, nav.get(), g)) {
        std::fprintf(stderr, "no structures\n");
        return 1;
      }
      for (const StructureSpawn& s : g.structures)
        std::printf("%-26s %-9s team %d lane %2d pos %d at %7.0f %7.0f  %s as %s skin %d  hp %.0f regen %.0f r %.0f  rubble %s %d after %.1f\n",
                    s.object.c_str(), s.kind.c_str(), s.team, s.lane, s.position, s.x, s.z, s.record.c_str(), s.character.c_str(), s.skin, s.max_hp,
                    s.hp_regen, s.collision_radius, s.rubble.c_str(), s.rubble_skin, s.rubble_after);
      for (int t = 0; t < 2; ++t)
        for (int l = 0; l < 3; ++l) std::printf("minions team %d lane %d spawn at %.0f %.0f\n", t, l, g.minion_spawn[t][l][0], g.minion_spawn[t][l][1]);
      for (int l = 0; l < 3; ++l) {
        std::printf("lane %d: %zu waypoints:", l, g.lanes[l].size());
        for (const auto& p : g.lanes[l]) std::printf(" (%.0f %.0f)", p[0], p[1]);
        std::printf("\n");
      }
      return 0;
    }
    if (cmd == "objects" && argc > 3) {
      // bainfo objects <map wad> <materials.bin path> [type]: the map's placed objects
      auto bytes = wad.read(argv[3]);
      if (!bytes) return 1;
      const int only = argc > 4 ? std::stoi(argv[4]) : -1;
      for (const MapObject& o : map_objects(PropertyBin(*bytes)))
        if (only < 0 || o.type == only)
          std::printf("%-40s type %2d at %8.1f %7.1f %8.1f facing %6.3f box %.0f..%.0f %.0f..%.0f\n", o.name.c_str(), o.type, o.x, o.y, o.z, o.facing,
                      o.box_min[0], o.box_max[0], o.box_min[2], o.box_max[2]);
      return 0;
    }
    if (cmd == "permutation" && argc > 4) {
      // bainfo permutation <ShaderCache wad> <shaders/staticmesh/name> <v|p> [NAME=VALUE ...] [out.dxbc]
      Defines want;
      std::string out;
      for (int i = 5; i < argc; ++i) {
        const std::string a = argv[i];
        const size_t eq = a.find('=');
        if (eq == std::string::npos) out = a;
        else want[a.substr(0, eq)] = a.substr(eq + 1);
      }
      ShaderCache cache(wad);
      Defines used;
      auto blob = cache.blob(argv[3], argv[4][0], want, &used);
      std::string list;
      for (const auto& [n, v] : used) list += n + "=" + v + " ";
      if (!blob) {
        std::fprintf(stderr, "no permutation for: %s\n", list.c_str());
        return 1;
      }
      std::printf("%zu bytes for: %s\n", blob->size(), list.c_str());
      if (!out.empty()) {
        FILE* f = std::fopen(out.c_str(), "wb");
        if (!f) return 1;
        std::fwrite(blob->data(), 1, blob->size(), f);
        std::fclose(f);
      }
      return 0;
    }
    if ((cmd == "raw" || cmd == "disasm") && argc > 3) {
      // raw: writes an entry as it is; disasm: prints a compiled DX11 shader (DXBC) as assembly, with D3DDisassemble.
      // The entry is a path, or {16 hex digits} for one whose name is unknown.
      const std::string entry = argv[3];
      auto bytes = entry.size() == 18 && entry.front() == '{' ? wad.read_hash(std::stoull(entry.substr(1, 16), nullptr, 16)) : wad.read(entry);
      if (!bytes) {
        std::fprintf(stderr, "not in the archive: %s\n", argv[3]);
        return 1;
      }
      if (cmd == "raw") {
        FILE* f = std::fopen(argc > 4 ? argv[4] : "entry.bin", "wb");
        if (!f) return 1;
        std::fwrite(bytes->data(), 1, bytes->size(), f);
        std::fclose(f);
        std::printf("%zu bytes\n", bytes->size());
        return 0;
      }
#ifdef _WIN32
      // the DXBC container may sit behind a header of Riot's: find its "DXBC" magic
      size_t at = 0;
      while (at + 4 <= bytes->size() && std::memcmp(bytes->data() + at, "DXBC", 4) != 0) ++at;
      if (at + 4 > bytes->size()) {
        std::fprintf(stderr, "no DXBC in this entry\n");
        return 1;
      }
      ID3DBlob* text = nullptr;
      if (FAILED(D3DDisassemble(bytes->data() + at, bytes->size() - at, 0, nullptr, &text)) || !text) {
        std::fprintf(stderr, "D3DDisassemble failed (header %zu bytes)\n", at);
        return 1;
      }
      std::printf("// header: %zu bytes before DXBC\n%s\n", at, static_cast<const char*>(text->GetBufferPointer()));
      text->Release();
      return 0;
#else
      return 1;
#endif
    }
    if (cmd == "navcell" && argc > 4) {  // bainfo navcell <Map11.wad> x z [x z ...]: the navgrid cell under each point
      auto mats = wad.read("data/maps/mapgeometry/map11/base_srx.materials.bin");
      auto bytes = mats ? wad.read(navgrid_path(PropertyBin(*mats))) : std::nullopt;
      if (!bytes) return 1;
      const NavGrid nav(*bytes);
      std::printf("grid %u x %u cells of %.1f from (%.1f, %.1f)\n", nav.cells_x, nav.cells_z, nav.cell_size, nav.min_x, nav.min_z);
      for (int i = 3; i + 1 < argc; i += 2) {
        const float x = std::stof(argv[i]), z = std::stof(argv[i + 1]);
        const int cx = static_cast<int>(std::floor((x - nav.min_x) / nav.cell_size)), cz = static_cast<int>(std::floor((z - nav.min_z) / nav.cell_size));
        const size_t at = static_cast<size_t>(cz) * nav.cells_x + static_cast<size_t>(cx);
        std::printf("%.0f %.0f: cell %d %d flags %u regions %u %u %u %u walkable %d\n", x, z, cx, cz, nav.cell_flags[at], nav.regions[at][0],
                    nav.regions[at][1], nav.regions[at][2], nav.regions[at][3], nav.walkable(cx, cz) ? 1 : 0);
      }
      return 0;
    }
    if (cmd == "path" && argc > 6) {
      auto mats = wad.read("data/maps/mapgeometry/map11/base_srx.materials.bin");
      auto bytes = mats ? wad.read(navgrid_path(PropertyBin(*mats))) : std::nullopt;
      if (!bytes) return 1;
      const NavGrid nav(*bytes);
      const float x0 = std::stof(argv[3]), z0 = std::stof(argv[4]), x1 = std::stof(argv[5]), z1 = std::stof(argv[6]);
      const auto t0 = std::chrono::steady_clock::now();
      const float radius = argc > 7 ? std::stof(argv[7]) : 0.f;
      const auto path = nav.find_path(x0, z0, x1, z1, radius);
      const double ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
      float px = x0, pz = z0, length = 0;
      int blocked = 0;
      float min_clear = NavGrid::kClearanceCap;
      for (const auto& [x, z] : path) {
        if (!nav.line_walkable(px, pz, x, z, radius)) ++blocked;
        for (int k = 0; k <= 100; ++k) {
          const float sx = px + (x - px) * static_cast<float>(k) / 100, sz = pz + (z - pz) * static_cast<float>(k) / 100;
          const int cx = static_cast<int>((sx - nav.min_x) / nav.cell_size), cz = static_cast<int>((sz - nav.min_z) / nav.cell_size);
          if (cx >= 0 && cz >= 0 && cx < static_cast<int>(nav.cells_x) && cz < static_cast<int>(nav.cells_z))
            min_clear = std::min(min_clear, nav.clearance[static_cast<size_t>(cz) * nav.cells_x + static_cast<size_t>(cx)]);
        }
        length += std::hypot(x - px, z - pz);
        std::printf("  -> %.0f %.0f\n", x, z);
        px = x, pz = z;
      }
      std::printf("%zu waypoints, %.0f units long (straight line %.0f), %d segments through walls, %.2f ms\n", path.size(), length,
                  std::hypot(x1 - x0, z1 - z0), blocked, ms);
      std::printf("closest the path comes to a wall cell: %.0f units\n", min_clear);
      return 0;
    }
    if (cmd == "lua" && argc > 3) {
      // runs one of the client's compiled scripts (Scripts.wad: Lua 5.1 bytecode) and prints the globals it sets
      auto bytes = wad.read(argv[3]);
      if (!bytes) return 1;
      lua_State* L = luaL_newstate();
      if (luaL_loadbuffer(L, reinterpret_cast<const char*>(bytes->data()), bytes->size(), argv[3]) != 0 || lua_pcall(L, 0, 0, 0) != 0) {
        std::fprintf(stderr, "lua: %s\n", lua_tostring(L, -1));
        lua_close(L);
        return 1;
      }
      lua_pushnil(L);
      while (lua_next(L, LUA_GLOBALSINDEX) != 0) {
        const char* key = lua_tostring(L, -2);
        if (lua_isnumber(L, -1)) std::printf("%s = %g\n", key, lua_tonumber(L, -1));
        else if (lua_isstring(L, -1)) std::printf("%s = \"%s\"\n", key, lua_tostring(L, -1));
        else if (lua_isboolean(L, -1)) std::printf("%s = %s\n", key, lua_toboolean(L, -1) ? "true" : "false");
        else std::printf("%s = <%s>\n", key, luaL_typename(L, -1));
        lua_pop(L, 1);
      }
      lua_close(L);
      return 0;
    }
    if (cmd == "structures") {
      // the structures as the navigation grid names them (MapObjects.cpp)
      auto mats = wad.read("data/maps/mapgeometry/map11/base_srx.materials.bin");
      auto bytes = mats ? wad.read(navgrid_path(PropertyBin(*mats))) : std::nullopt;
      if (!bytes) return 1;
      const NavGrid nav(*bytes);
      for (const MapStructure& s : map_structures(nav))
        std::printf("%s %-9s %-3s %-5s at %6.0f %6.0f, %3d cells -> %s skin %d, facing %4.0f deg\n", s.team ? "red " : "blue", s.kind.c_str(),
                    s.lane.c_str(), s.tier.c_str(), s.x, s.z, s.cells, s.character.c_str(), s.skin, s.facing * 57.2958f);
      return 0;
    }
    if (cmd == "findtext" && argc > 3) {
      // every property bin of the archive whose bytes hold a text (any case), e.g. the bin that defines a particle by
      // its name: bainfo findtext <wad> <text> [hashes.game.txt]
      std::string want = argv[3];
      for (char& c : want) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
      if (argc > 4) g_names.load(argv[4]);
      for (const auto& [h, e] : wad.entries()) {
        std::optional<std::vector<uint8_t>> bytes;
        try {
          bytes = wad.read_hash(h);
        } catch (const std::exception&) {
          continue;
        }
        if (!bytes || bytes->size() < 8) continue;
        if (std::memcmp(bytes->data(), "PROP", 4) != 0 && std::memcmp(bytes->data(), "PTCH", 4) != 0) continue;
        std::string text(bytes->begin(), bytes->end());
        for (char& c : text) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
        if (text.find(want) != std::string::npos) std::printf("%s\n", g_names.name64(h).c_str());
      }
      return 0;
    }
    if (cmd == "findhash" && argc > 3) {
      // every property bin of the archive whose bytes hold a 32-bit hash (a field, class or entry name), e.g. to see
      // where a field like mBlendTime is ever set: bainfo findhash <wad> <hex hash> [hashes.game.txt]
      const uint32_t want = static_cast<uint32_t>(std::stoul(argv[3], nullptr, 16));
      if (argc > 4) g_names.load(argv[4]);
      uint8_t pat[4];
      std::memcpy(pat, &want, 4);
      size_t bins = 0;
      for (const auto& [h, e] : wad.entries()) {
        std::optional<std::vector<uint8_t>> bytes;
        try {
          bytes = wad.read_hash(h);
        } catch (const std::exception&) {
          continue;
        }
        if (!bytes || bytes->size() < 8) continue;
        if (std::memcmp(bytes->data(), "PROP", 4) != 0 && std::memcmp(bytes->data(), "PTCH", 4) != 0) continue;
        ++bins;
        size_t hits = 0;
        for (size_t i = 0; i + 4 <= bytes->size(); ++i)
          if (std::memcmp(bytes->data() + i, pat, 4) == 0) ++hits;
        if (hits) std::printf("%s %zu\n", g_names.name64(h).c_str(), hits);
      }
      std::printf("%zu bins searched\n", bins);
      return 0;
    }
    if (cmd == "bin" && argc > 3) {
      const std::string filter = argc > 4 ? argv[4] : "";
      if (argc > 5) {
        const std::filesystem::path dir = argv[5];
        for (const char* f : {"hashes.binentries.txt", "hashes.binhashes.txt", "hashes.bintypes.txt", "hashes.binfields.txt"})
          if (std::filesystem::exists(dir / f)) g_names.load(dir / f);
      }
      // a path, or "{<16 hex digits>}" for an entry whose path is unknown
      const std::string want = argv[3];
      auto bytes = want.size() == 18 && want.front() == '{' ? wad.read_hash(std::stoull(want.substr(1, 16), nullptr, 16)) : wad.read(want);
      if (!bytes) {
        std::fprintf(stderr, "not in the archive: %s\n", argv[3]);
        return 1;
      }
      PropertyBin bin(*bytes);
      std::printf("version %u, %zu entries, %zu links\n", bin.version(), bin.entries().size(), bin.links().size());
      for (const std::string& l : bin.links()) std::printf("  link %s\n", l.c_str());
      for (const BinEntry& e : bin.entries()) {
        const std::string name = g_names.name32(e.name);
        if (!filter.empty() && name.find(filter) == std::string::npos) continue;
        std::printf("%s (%s)\n", name.c_str(), g_names.name32(e.cls).c_str());
        dump_fields(e.fields, 1);
      }
      return 0;
    }
  } catch (const std::exception& e) {
    std::fprintf(stderr, "error: %s\n", e.what());
    return 1;
  }
  return 2;
}
