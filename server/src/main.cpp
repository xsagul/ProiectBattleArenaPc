// server.exe: runs one match. The simulation lives on this one thread and advances in League's 0.033 s ticks; ENet is
// polled between ticks. Joins and orders that arrive are applied at the start of the next tick and recorded with it.
//
//   server.exe [--port 5119] [--match 12345] [--record match.basr] [--data <folder with DATA/FINAL>]
//   server.exe --replay match.basr [--data ...]   plays a recording back and checks every checkpoint
//   --netlog out.banl (with a match or --simulate): every message the server broadcasts, to compare with Riot's stream

#include <enet/enet.h>
#include <windows.h>

#include <algorithm>

#include <chrono>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <functional>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

#include "Match.h"
#include "Recorder.h"
#include "ba/ByteReader.h"
#include "ba/CharacterData.h"
#include "ba/GameData.h"
#include "ba/MapGame.h"
#include "ba/MapObjects.h"
#include "ba/NavGrid.h"
#include "ba/PropertyBin.h"
#include "ba/Protocol.h"
#include "ba/Wad.h"

using namespace ba;

namespace {

struct Args {
  uint16_t port = net::kDefaultPort;
  uint64_t match = 1;
  std::string record = "match.basr";
  std::string replay;
  bool combat_log = false;  // --combat-log 1 (with --replay): every attack, hit and death
  double simulate = 0;      // --simulate S: a match with one champion run S game seconds as fast as it goes, no network
  float structure_health = 1;  // --structure-health K: structures start with K times their health (checks only)
  int level = 1;               // --level N: champions join at level N (checks only: the Practice Tool's "level up")
  float start_gold = -1;       // --start-gold G: champions join with G gold (checks only: the Practice Tool's gold)
  float start_x = -1, start_z = -1;  // --start-x X --start-z Z: champions join there (checks only: its teleport)
  std::string champion = "Garen";
  std::string mode = "PRACTICETOOL";
  std::string ready_event;  // local launcher notification, after map + scripts are loaded
  std::string data;
  std::string netlog;
};

Args parse(int argc, char** argv) {
  Args a;
  for (int i = 1; i + 1 < argc; i += 2) {
    const std::string k = argv[i];
    if (k == "--port") a.port = static_cast<uint16_t>(std::stoi(argv[i + 1]));
    else if (k == "--match") a.match = std::stoull(argv[i + 1]);
    else if (k == "--record") a.record = argv[i + 1];
    else if (k == "--replay") a.replay = argv[i + 1];
    else if (k == "--combat-log") a.combat_log = std::string(argv[i + 1]) == "1";
    else if (k == "--simulate") a.simulate = std::stod(argv[i + 1]);
    else if (k == "--structure-health") a.structure_health = std::stof(argv[i + 1]);
    else if (k == "--level") a.level = std::stoi(argv[i + 1]);
    else if (k == "--start-gold") a.start_gold = std::stof(argv[i + 1]);
    else if (k == "--start-x") a.start_x = std::stof(argv[i + 1]);
    else if (k == "--start-z") a.start_z = std::stof(argv[i + 1]);
    else if (k == "--champion") a.champion = argv[i + 1];
    else if (k == "--mode") a.mode = argv[i + 1];
    else if (k == "--ready-event") a.ready_event = argv[i + 1];
    else if (k == "--data") a.data = argv[i + 1];
    else if (k == "--netlog") a.netlog = argv[i + 1];
  }
  return a;
}

void send(ENetPeer* peer, net::Channel ch, const std::vector<uint8_t>& bytes, bool reliable = true) {
  ENetPacket* p = enet_packet_create(bytes.data(), bytes.size(), reliable ? ENET_PACKET_FLAG_RELIABLE : 0);
  enet_peer_send(peer, ch, p);
}

/** Every message the server broadcasts, as sent, to compare our stream with Riot's (tools/sponge/netlog_compare.py).
 *  "BANL", u32 version 1; then records: i64 tick, u8 channel, u32 length, the message's bytes. */
class NetLog {
 public:
  explicit NetLog(const std::string& file) {
    if (file.empty()) return;
    f_ = std::fopen(file.c_str(), "wb");
    if (!f_) {
      std::fprintf(stderr, "cannot write %s\n", file.c_str());
      return;
    }
    const uint32_t version = 1;
    std::fwrite("BANL", 1, 4, f_);
    std::fwrite(&version, 4, 1, f_);
  }
  ~NetLog() {
    if (f_) std::fclose(f_);
  }
  NetLog(const NetLog&) = delete;
  NetLog& operator=(const NetLog&) = delete;
  void write(int64_t tick, net::Channel ch, const std::vector<uint8_t>& bytes) {
    if (!f_) return;
    const uint8_t c = ch;
    const uint32_t n = static_cast<uint32_t>(bytes.size());
    std::fwrite(&tick, 8, 1, f_);
    std::fwrite(&c, 1, 1, f_);
    std::fwrite(&n, 4, 1, f_);
    std::fwrite(bytes.data(), 1, bytes.size(), f_);
  }

 private:
  std::FILE* f_ = nullptr;
};

using Out = std::function<void(net::Channel, const std::vector<uint8_t>&)>;

std::vector<uint8_t> spells_message(const Match& match, const Unit& u) {
  net::Writer w;
  w.put(net::Msg::UnitSpells).put(u.id).put(static_cast<uint8_t>(u.skill_points));
  for (int i = 0; i < 4; ++i) {
    const SpellSlot& s = u.spells[static_cast<size_t>(i)];
    w.put(static_cast<uint8_t>(s.level)).put(match.cooldown_left(u, i)).put(s.cooldown_total);
    w.put(s.data ? s.data->mana[static_cast<size_t>(std::clamp(s.level, 1, 6))] : 0.f);
  }
  return w.bytes();
}

std::vector<uint8_t> stats_message(const Match& match, const Unit& u) {
  net::Writer w;
  w.put(net::Msg::UnitStats).put(u.id).put(static_cast<uint8_t>(u.level)).put(match.xp_fraction(u)).put(u.gold).put(u.par).put(u.max_par);
  w.put(u.stats.ad).put(u.stats.armor).put(u.stats.spell_block).put(u.stats.attack_speed).put(u.move_speed);
  w.put(u.kills).put(u.deaths).put(u.assists).put(u.minions_killed);
  w.put(u.stats.ap).put(u.stats.ability_haste).put(u.stats.crit);
  return w.bytes();
}

std::vector<uint8_t> items_message(const Unit& u) {
  net::Writer w;
  w.put(net::Msg::UnitItems).put(u.id);
  for (size_t k = 0; k < u.items.size(); ++k) w.put(static_cast<uint32_t>(u.items[k])).put(u.item_stacks[k]);
  return w.bytes();
}

/** What a client needs to know about a unit it has not seen: it, its health, a champion's numbers, its death. */
void unit_state(const Match& match, const Unit& u, int64_t tick, const Out& out) {
  net::Writer s;
  s.put(net::Msg::UnitSpawn).put(u.id).put(u.team).str(u.skin).put(u.skin_id).put(u.x).put(u.z).put(u.facing).put(u.spawn_tick);
  out(net::kHandshake, s.bytes());
  // the fountain turrets cannot be targeted: no health, no bar
  if (u.record && u.kind != UnitType::Fountain) {
    net::Writer h;
    h.put(net::Msg::UnitHealth).put(u.id).put(u.hp).put(u.max_hp).put(u.total_shield());
    out(net::kStats, h.bytes());
  }
  if (u.kind == UnitType::Champion) out(net::kStats, stats_message(match, u)), out(net::kStats, spells_message(match, u));
  if (u.dead) {
    net::Writer d;
    d.put(net::Msg::UnitDeath).put(tick).put(u.id);
    out(net::kCombat, d.bytes());
  }
}

/** Everything one tick changed, as the messages every client gets. */
void emit_tick(const Match& match, const MatchEvents& events, int64_t start, const Out& broadcast) {
  for (uint32_t id : events.spawned)
    if (const Unit* u = match.unit(id)) unit_state(match, *u, start, broadcast);
  // combat: attacks, missiles, damage, deaths
  for (const MatchEvents::Attack& a : events.attacks) {
    net::Writer w;
    w.put(net::Msg::UnitAttack).put(start).put(a.unit).put(a.target).str(a.spell).str(a.animation).put(a.windup).put(a.total).put(a.spell_cast_time).put(a.facing);
    broadcast(net::kCombat, w.bytes());
  }
  for (const MatchEvents::Missile& m : events.missiles) {
    net::Writer w;
    w.put(net::Msg::Missile).put(start).put(m.unit).put(m.target).put(m.speed).str(m.spell);
    broadcast(net::kCombat, w.bytes());
  }
  for (const MatchEvents::Hit& h : events.hits) {
    net::Writer w;
    w.put(net::Msg::UnitHit).put(start).put(h.source).put(h.target).str(h.spell);
    broadcast(net::kCombat, w.bytes());
  }
  for (const MatchEvents::Damage& d : events.damage) {
    net::Writer w;
    w.put(net::Msg::UnitHealth).put(d.target).put(d.hp).put(d.max_hp).put(d.shield);
    broadcast(net::kStats, w.bytes());
  }
  for (uint32_t id : events.removed) {
    net::Writer w;
    w.put(net::Msg::UnitRemove).put(id);
    broadcast(net::kCombat, w.bytes());
  }
  for (uint32_t id : events.deaths) {
    net::Writer w;
    w.put(net::Msg::UnitDeath).put(start).put(id);
    broadcast(net::kCombat, w.bytes());
  }
  if (events.winner >= 0) {
    net::Writer w;
    w.put(net::Msg::GameEnd).put(static_cast<uint8_t>(events.winner));
    broadcast(net::kHandshake, w.bytes());
  }
  // each champion's numbers once a tick, however many of them changed
  auto each_once = [&match](std::vector<uint32_t> ids, const std::function<void(const Unit&)>& f) {
    std::sort(ids.begin(), ids.end());
    ids.erase(std::unique(ids.begin(), ids.end()), ids.end());
    for (uint32_t id : ids)
      if (const Unit* u = match.unit(id)) f(*u);
  };
  each_once(events.stats_changed, [&](const Unit& u) { broadcast(net::kStats, stats_message(match, u)); });
  each_once(events.items_changed, [&](const Unit& u) { broadcast(net::kStats, items_message(u)); });
  each_once(events.spells_changed, [&](const Unit& u) { broadcast(net::kStats, spells_message(match, u)); });
  for (const MatchEvents::SpellCast& c : events.casts) {
    net::Writer w;
    w.put(net::Msg::SpellCast).put(start).put(c.unit).put(c.slot).str(c.spell).str(c.animation).put(c.cast_time).put(c.x).put(c.z).put(c.target);
    broadcast(net::kCombat, w.bytes());
  }
  for (const MatchEvents::BuffChange& b : events.buffs) {
    net::Writer w;
    w.put(net::Msg::BuffChange).put(b.unit).put(static_cast<uint8_t>(b.added ? 1 : 0)).str(b.name).put(b.duration);
    broadcast(net::kCombat, w.bytes());
  }
  for (const MatchEvents::SkillMissile& m : events.skill_missiles) {
    net::Writer w;
    w.put(net::Msg::SkillMissile).put(start).put(m.id).put(m.unit).str(m.spell).put(m.x).put(m.z).put(m.dx).put(m.dz).put(m.speed).put(m.range).str(m.effect).put(m.accel).put(m.speed_limit);
    broadcast(net::kCombat, w.bytes());
  }
  for (uint32_t id : events.skill_missiles_ended) {
    net::Writer w;
    w.put(net::Msg::SkillMissileEnd).put(id);
    broadcast(net::kCombat, w.bytes());
  }
  for (const MatchEvents::DashMove& d : events.dashes) {
    net::Writer w;
    w.put(net::Msg::Dash).put(start).put(d.unit).put(d.x).put(d.z).put(d.speed);
    broadcast(net::kMovement, w.bytes());
  }
  for (const MatchEvents::Effect& e : events.effects) {
    net::Writer w;
    w.put(net::Msg::Effect).put(e.unit).put(static_cast<uint8_t>(e.stop ? 1 : 0)).str(e.key).str(e.bone).put(e.seconds).put(e.owner);
    broadcast(net::kCombat, w.bytes());
  }
  for (const MatchEvents::GroundEffect& e : events.ground_effects) {
    net::Writer w;
    w.put(net::Msg::GroundEffect).put(e.id).put(static_cast<uint8_t>(e.stop ? 1 : 0)).put(e.owner).str(e.key).put(e.x).put(e.z).put(e.tx).put(e.tz).put(e.seconds).put(e.height);
    broadcast(net::kCombat, w.bytes());
  }
  for (const MatchEvents::Animation& a : events.animations) {
    net::Writer w;
    w.put(net::Msg::Animation).put(start).put(a.unit).str(a.clip).put(a.seconds);
    broadcast(net::kCombat, w.bytes());
  }
  for (uint32_t id : events.respawned) {
    const Unit* u = match.unit(id);
    if (!u) continue;
    net::Writer w;
    w.put(net::Msg::UnitRespawn).put(start).put(id).put(u->x).put(u->z).put(u->facing);
    broadcast(net::kCombat, w.bytes());
    net::Writer h;
    h.put(net::Msg::UnitHealth).put(id).put(u->hp).put(u->max_hp).put(u->total_shield());
    broadcast(net::kStats, h.bytes());
  }
  if (!events.path_changed.empty()) {
    std::vector<net::UnitPath> paths;
    for (uint32_t id : events.path_changed) {
      const Unit* u = match.unit(id);
      if (!u) continue;
      net::UnitPath p;
      p.id = u->id;
      p.speed = u->move_speed;
      p.points.push_back({u->x, u->z});
      for (const net::Point& q : u->path) p.points.push_back(q);
      paths.push_back(std::move(p));
    }
    broadcast(net::kMovement, net::waypoints(start, paths));
  }
}

std::filesystem::path find_data(const std::string& arg) { return find_game_data(arg, std::filesystem::current_path()); }

/** The map's navigation grid (the one the geometry's MapContainer names, base_srx.materials.bin: MapNavGrid) and the
 *  teams' spawn points (its __Spawn_T1 / __Spawn_T2 locators). */
std::unique_ptr<NavGrid> load_navgrid(const std::filesystem::path& data, SpawnPoint spawns[2] = nullptr) {
  try {
    Wad map_wad(data / "DATA" / "FINAL" / "Maps" / "Shipping" / "Map11.wad.client");
    if (auto mats = map_wad.read("data/maps/mapgeometry/map11/base_srx.materials.bin")) {
      const PropertyBin bin(*mats);
      if (spawns)
        for (uint8_t t = 0; t < 2; ++t)
          if (!map_spawn_point(bin, t, spawns[t])) std::fprintf(stderr, "no spawn point for team %u\n", t);
    }
    if (auto bytes = read_map_navgrid(data)) return std::make_unique<NavGrid>(*bytes);
  } catch (const std::exception& e) {
    std::fprintf(stderr, "navigation grid: %s\n", e.what());
  }
  return nullptr;
}

/** The map's game (structures, lanes, minion waves): base_srx.materials.bin, map11.bin and objectcfg_srx.cfg. */
std::unique_ptr<MapGame> load_map_game(const std::filesystem::path& data) {
  try {
    const auto dir = data / "DATA" / "FINAL" / "Maps" / "Shipping";
    Wad map_wad(dir / "Map11.wad.client");
    auto mats = map_wad.read("data/maps/mapgeometry/map11/base_srx.materials.bin");
    auto map = map_wad.read("data/maps/shipping/map11/map11.bin");
    std::string cfg;
    if (std::filesystem::exists(dir / "Map11LEVELS.wad.client"))
      if (auto c = Wad(dir / "Map11LEVELS.wad.client").read("levels/map11/scene/cfg/objectcfg_srx.cfg")) cfg.assign(c->begin(), c->end());
    auto g = std::make_unique<MapGame>();
    if (std::filesystem::exists(data / "DATA" / "FINAL" / "Global.wad.client"))
      if (auto globals = Wad(data / "DATA" / "FINAL" / "Global.wad.client").read("globals")) read_globals(PropertyBin(*globals), *g);
    const auto nav = read_map_navgrid(data);
    const std::unique_ptr<NavGrid> grid = nav ? std::make_unique<NavGrid>(*nav) : nullptr;
    if (mats && map && read_map_game(PropertyBin(*mats), PropertyBin(*map), cfg, grid.get(), *g)) return g;
  } catch (const std::exception& e) {
    std::fprintf(stderr, "map game: %s\n", e.what());
  }
  return nullptr;
}

/** Gives a match its spells: each character's spell objects, read from its wad when first asked for, and the scripts
 *  next to the executable (scripts/*.lua). */
void setup_spells(Match& match, const std::filesystem::path& data, const std::filesystem::path& exe_dir) {
  // the characters the level script names (the lane minions): their records, read from the map's wad when first asked
  static std::map<std::string, std::unique_ptr<CharacterRecordData>> named;
  static std::unique_ptr<Wad> map_wad;
  try {
    map_wad = std::make_unique<Wad>(data / "DATA" / "FINAL" / "Maps" / "Shipping" / "Map11.wad.client");
  } catch (const std::exception& e) {
    std::fprintf(stderr, "map wad: %s\n", e.what());
  }
  match.set_record_source([](const std::string& path) -> const CharacterRecordData* {
    auto it = named.find(path);
    if (it != named.end()) return it->second.get();
    auto r = std::make_unique<CharacterRecordData>();
    if (!map_wad || !read_character_record_at(*map_wad, path, *r)) {
      std::fprintf(stderr, "no record %s\n", path.c_str());
      r.reset();
    }
    return (named[path] = std::move(r)).get();
  });
  // the items (Global.wad) and what the CLASSIC mode sells (map11.bin)
  static ItemTable items;
  static bool items_read = false;
  if (!items_read) {
    items_read = true;
    try {
      const auto final_dir = data / "DATA" / "FINAL";
      if (read_items(Wad(final_dir / "Global.wad.client"), items))
        if (auto m = Wad(final_dir / "Maps" / "Shipping" / "Map11.wad.client").read("data/maps/shipping/map11/map11.bin"))
          read_mode_items(PropertyBin(*m), "CLASSIC", items);
      std::printf("%zu items, %zu sold by the mode\n", items.items.size(), items.mode_items.size());
    } catch (const std::exception& e) {
      std::fprintf(stderr, "items: %s\n", e.what());
    }
  }
  if (!items.items.empty()) match.set_items(&items);
  static std::map<std::string, std::map<std::string, SpellData>> cache;
  match.set_spells([data](const std::string& character) -> const std::map<std::string, SpellData>* {
    auto it = cache.find(character);
    if (it == cache.end()) {
      std::map<std::string, SpellData> spells;
      try {
        const auto wad = data / "DATA" / "FINAL" / "Champions" / (character + ".wad.client");
        if (std::filesystem::exists(wad)) spells = read_spells(Wad(wad), character);
      } catch (const std::exception& e) {
        std::fprintf(stderr, "spells of %s: %s\n", character.c_str(), e.what());
      }
      it = cache.emplace(character, std::move(spells)).first;
    }
    return it->second.empty() ? nullptr : &it->second;
  });
  std::filesystem::path scripts = exe_dir / "scripts";
  if (!std::filesystem::exists(scripts)) scripts = std::filesystem::current_path() / "scripts";
  match.load_scripts(scripts);
}

std::filesystem::path g_exe_dir;

constexpr int64_t kCheckpointTicks = 30;
const std::string kDummy = "PracticeTool_TargetDummy";  // the Practice Tool's target dummy (Map11.wad)

/** Every character's data the match may need: the champions this install has (Champions/<name>.wad.client) and the
 *  Practice Tool's target dummy (in the map's wad). */
std::map<std::string, CharacterRecordData> load_records(const std::filesystem::path& data, const MapGame* game) {
  std::map<std::string, CharacterRecordData> out;
  // the map's units, by record path ("Characters/Turret/CharacterRecords/SR_Outer"), from the map's wad
  if (game) {
    try {
      Wad map_wad(data / "DATA" / "FINAL" / "Maps" / "Shipping" / "Map11.wad.client");
      std::vector<std::string> paths;
      for (const StructureSpawn& s : game->structures) paths.push_back(s.record);
      for (const std::string& p : paths) {
        if (p.empty() || out.count(p)) continue;
        CharacterRecordData r;
        if (read_character_record_at(map_wad, p, r)) out[p] = r;
        else std::fprintf(stderr, "no record %s\n", p.c_str());
      }
    } catch (const std::exception& ex) {
      std::fprintf(stderr, "map records: %s\n", ex.what());
    }
  }
  std::error_code ec;
  for (const auto& e : std::filesystem::directory_iterator(data / "DATA" / "FINAL" / "Champions", ec)) {
    std::string name = e.path().filename().string();
    const std::string ext = ".wad.client";
    if (name.size() <= ext.size() || name.compare(name.size() - ext.size(), ext.size(), ext) != 0) continue;
    name.resize(name.size() - ext.size());
    try {
      CharacterRecordData r;
      if (read_character_record(Wad(e.path()), name, r)) out[name] = r;
    } catch (const std::exception& ex) {
      std::fprintf(stderr, "%s: %s\n", name.c_str(), ex.what());
    }
  }
  try {
    CharacterRecordData r;
    if (read_character_record(Wad(data / "DATA" / "FINAL" / "Maps" / "Shipping" / "Map11.wad.client"), kDummy, r)) out[kDummy] = r;
  } catch (const std::exception& ex) {
    std::fprintf(stderr, "%s: %s\n", kDummy.c_str(), ex.what());
  }
  return out;
}

int replay(const Args& args) {
  const Recording rec = read_recording(args.replay);
  const auto nav = load_navgrid(find_data(args.data));
  const auto game = load_map_game(find_data(args.data));
  const auto records = load_records(find_data(args.data), game.get());
  Match match(rec.match_id, nav.get(), &records, game.get());
  setup_spells(match, find_data(args.data), g_exe_dir);
  // (a match recorded with the checks' options is replayed with the same ones)
  match.set_start_level(args.level);
  match.set_start_gold(args.start_gold);
  if (args.start_x >= 0) match.set_start_place(args.start_x, args.start_z);
  match.place_structures(args.structure_health);
  match.load_level(find_data(args.data));
  size_t next_event = 0, next_check = 0, failures = 0;
  const int64_t end = rec.checkpoints.empty() ? 0 : rec.checkpoints.back().first;
  for (;;) {
    const int64_t tick = match.clock.tick;
    // a checkpoint is the state at the start of its tick, before that tick's events
    while (next_check < rec.checkpoints.size() && rec.checkpoints[next_check].first == tick) {
      const uint64_t mine = match.checksum();
      if (mine != rec.checkpoints[next_check].second && failures++ < 5)
        std::printf("tick %lld: checksum %016llx, recorded %016llx\n", static_cast<long long>(tick), static_cast<unsigned long long>(mine),
                    static_cast<unsigned long long>(rec.checkpoints[next_check].second));
      ++next_check;
    }
    if (tick >= end) break;
    std::vector<SpawnRequest> spawns;
    std::vector<Order> orders;
    if (next_event < rec.events.size() && rec.events[next_event].tick == tick) {
      spawns = rec.events[next_event].spawns;
      orders = rec.events[next_event].orders;
      ++next_event;
    }
    const MatchEvents ev = match.step(spawns, orders);
    if (args.combat_log) {
      const double sec = static_cast<double>(tick) * kTickSeconds;
      for (const auto& a : ev.attacks)
        std::printf("tick %lld (%.3fs): %u attacks %u: %s, windup %.4fs, attack timer %.4fs\n", static_cast<long long>(tick), sec, a.unit, a.target,
                    a.animation.c_str(), a.windup, a.total);
      for (const auto& m : ev.missiles) std::printf("tick %lld (%.3fs): %u fires at %u, speed %.0f\n", static_cast<long long>(tick), sec, m.unit, m.target, m.speed);
      for (const auto& d : ev.damage)
        std::printf("tick %lld (%.3fs): %u takes %.2f, %.2f / %.0f left\n", static_cast<long long>(tick), sec, d.target, d.amount, d.hp, d.max_hp);
      for (uint32_t id : ev.deaths) std::printf("tick %lld (%.3fs): %u dies\n", static_cast<long long>(tick), sec, id);
    }
  }
  std::printf("replayed %lld ticks, %zu events, %zu checkpoints: %s\n", static_cast<long long>(end), rec.events.size(), rec.checkpoints.size(),
              failures ? "DIVERGED" : "identical");
  return failures ? 2 : 0;
}

}  // namespace

/** A match without players' input: one champion standing at its fountain while the waves play out; the state every
 *  30 game seconds (checks of the map's game: waves, lanes, fights, structures; and the simulation's cost). */
int simulate(const Args& args) {
  const auto data = find_data(args.data);
  SpawnPoint spawn_points[2];
  const auto nav = load_navgrid(data, spawn_points);
  const auto game = load_map_game(data);
  const auto records = load_records(data, game.get());
  Match match(args.match, nav.get(), &records, game.get());
  setup_spells(match, data, g_exe_dir);
  match.set_start_level(args.level);
  match.set_start_gold(args.start_gold);
  if (args.start_x >= 0) match.set_start_place(args.start_x, args.start_z);
  match.place_structures(args.structure_health);
  match.load_level(find_data(args.data));
  if (game)
    std::printf("%zu mode constants: unit to building %.3f, unit to hero %.3f, inhibitor health %.0f, attack delay %.1f .. %.1f s\n", game->constants.size(),
                game->constant("dr_UnitToBuilding", -1), game->constant("dr_UnitToHero", -1), game->constant("bar_MaxHP", -1),
                game->constant("gcd_AttackMinDelay", -1), game->constant("gcd_AttackMaxDelay", -1));
  std::vector<SpawnRequest> first{{0, args.champion, spawn_points[0].x, spawn_points[0].z, 0, 0, spawn_points[0].facing}};
  const int64_t end = static_cast<int64_t>(args.simulate / kTickSeconds);
  NetLog netlog(args.netlog);
  size_t attacks = 0, deaths = 0, spawned = 0, missiles = 0;
  const auto t0 = std::chrono::steady_clock::now();
  double worst = 0;
  for (int64_t i = 0; i <= end; ++i) {
    const auto a = std::chrono::steady_clock::now();
    const MatchEvents ev = match.step(i == 0 ? first : std::vector<SpawnRequest>{}, {});
    emit_tick(match, ev, i, [&netlog, i](net::Channel ch, const std::vector<uint8_t>& bytes) { netlog.write(i, ch, bytes); });
    worst = std::max(worst, std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - a).count());
    attacks += ev.attacks.size(), deaths += ev.deaths.size(), spawned += ev.spawned.size(), missiles += ev.missiles.size();
    if (i % static_cast<int64_t>(30 / kTickSeconds) == 0 || i == end || ev.winner >= 0) {
      int minions[2][3] = {};
      float lead[2][3] = {};  // how far along its lane the most advanced minion is (0 own base .. 1 enemy base)
      for (const Unit& u : match.units) {
        if (u.kind != UnitType::Minion || u.dead || u.lane < 0) continue;
        ++minions[u.team][u.lane];
        const auto& lane = game->lanes[static_cast<size_t>(u.lane)];
        float best = 1e30f;
        size_t at = 0;
        for (size_t k = 0; k < lane.size(); ++k) {
          const float d = std::hypot(lane[k][0] - u.x, lane[k][1] - u.z);
          if (d < best) best = d, at = k;
        }
        const float f = lane.size() > 1 ? static_cast<float>(at) / static_cast<float>(lane.size() - 1) : 0.f;
        lead[u.team][u.lane] = std::max(lead[u.team][u.lane], u.team == 0 ? f : 1 - f);
      }
      int standing[2] = {};
      std::string fallen;
      for (const Unit& u : match.units)
        if (u.kind == UnitType::Turret || u.kind == UnitType::Inhibitor || u.kind == UnitType::Nexus) {
          if (!u.dead) ++standing[u.team];
          else fallen += " " + std::to_string(u.team) + ":" + u.skin + "(lane " + std::to_string(u.lane) + " pos " + std::to_string(u.position) + ")";
        }
      std::printf("t %6.1f s  minions order bot/mid/top %2d %2d %2d chaos %2d %2d %2d  lead order %.2f %.2f %.2f chaos %.2f %.2f %.2f  structures %d/%d  attacks %zu missiles %zu deaths %zu spawned %zu%s\n",
                  match.game_seconds(), minions[0][0], minions[0][1], minions[0][2], minions[1][0], minions[1][1], minions[1][2], lead[0][0], lead[0][1],
                  lead[0][2], lead[1][0], lead[1][1], lead[1][2], standing[0], standing[1], attacks, missiles, deaths, spawned, fallen.c_str());
    }
    if (ev.winner >= 0) {
      std::printf("the nexus of team %d fell at %.1f s: team %d wins\n", 1 - ev.winner, match.game_seconds(), ev.winner);
      break;
    }
  }
  const double ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
  std::printf("%lld ticks in %.0f ms: %.3f ms a tick, worst %.2f ms (a tick lasts %.1f ms)\n", static_cast<long long>(match.clock.tick), ms, ms / static_cast<double>(std::max<int64_t>(1, match.clock.tick)), worst,
              kTickSeconds * 1000);
  return 0;
}

int main(int argc, char** argv) {
  const Args args = parse(argc, argv);
  if (args.mode != "PRACTICETOOL") {
    std::fprintf(stderr, "unsupported game mode: %s\n", args.mode.c_str());
    return 1;
  }
  {
    std::error_code ec;
    g_exe_dir = std::filesystem::absolute(argv[0], ec).parent_path();
  }
  std::setvbuf(stdout, nullptr, _IONBF, 0);  // the log shows up as it happens
  if (args.simulate > 0) return simulate(args);
  if (!args.replay.empty()) {
    try {
      return replay(args);
    } catch (const std::exception& e) {
      std::fprintf(stderr, "replay: %s\n", e.what());
      return 1;
    }
  }
  if (enet_initialize() != 0) {
    std::fprintf(stderr, "ENet failed to start\n");
    return 1;
  }
  ENetAddress address{};
  enet_address_set_host(&address, "127.0.0.1");
  address.port = args.port;
  ENetHost* host = enet_host_create(&address, 10, net::kChannels, 0, 0);
  if (!host) {
    std::fprintf(stderr, "cannot listen on port %u\n", args.port);
    return 1;
  }
  std::printf("BattleArena match server: match %llu on 127.0.0.1:%u, %.1f ticks/s\n", static_cast<unsigned long long>(args.match),
              args.port, 1.0 / kTickSeconds);

  const std::filesystem::path data = find_data(args.data);
  SpawnPoint spawn_points[2];
  const auto nav = load_navgrid(data, spawn_points);
  std::printf(nav ? "navigation grid: %ux%u cells\n" : "no navigation grid: units walk in straight lines\n", nav ? nav->cells_x : 0u, nav ? nav->cells_z : 0u);
  const auto game = load_map_game(data);
  if (game)
    std::printf("the map's game: %zu structures, lanes of %zu / %zu / %zu waypoints\n", game->structures.size(), game->lanes[0].size(),
                game->lanes[1].size(), game->lanes[2].size());
  const auto records = load_records(data, game.get());
  std::printf("%zu characters' data loaded\n", records.size());
  Match match(args.match, nav.get(), &records, game.get());
  setup_spells(match, data, g_exe_dir);
  match.set_start_level(args.level);
  match.set_start_gold(args.start_gold);
  if (args.start_x >= 0) match.set_start_place(args.start_x, args.start_z);
  match.place_structures(args.structure_health);
  match.load_level(find_data(args.data));
  std::printf("%zu structures placed, %zu spell scripts\n", match.units.size(), match.scripts_loaded());

  Recorder recorder(args.record, args.match);
  NetLog netlog(args.netlog);
  if (!args.ready_event.empty()) {
    HANDLE ready = OpenEventA(EVENT_MODIFY_STATE, FALSE, args.ready_event.c_str());
    if (!ready || !SetEvent(ready)) {
      if (ready) CloseHandle(ready);
      std::fprintf(stderr, "cannot signal launcher readiness\n");
      enet_host_destroy(host);
      enet_deinitialize();
      return 1;
    }
    CloseHandle(ready);
  }
  std::unordered_map<ENetPeer*, uint32_t> players;  // peer -> the unit it controls
  struct Joining {
    ENetPeer* peer;
    std::string name;
    SpawnRequest spawn;
  };
  std::vector<Joining> joining;
  std::vector<SpawnRequest> dummies;
  std::vector<Order> pending;

  using clock = std::chrono::steady_clock;  // QueryPerformanceCounter underneath on Windows
  const auto tick_len = std::chrono::microseconds(kTickMicros);
  auto next = clock::now();

  for (;;) {
    // ---- network, until the next tick is due
    ENetEvent ev;
    while (enet_host_service(host, &ev, 0) > 0) {
      if (ev.type == ENET_EVENT_TYPE_RECEIVE) {
        try {
          ByteReader r({ev.packet->data, ev.packet->dataLength});
          const auto msg = static_cast<net::Msg>(r.read<uint8_t>());
          if (msg == net::Msg::Hello && !players.count(ev.peer)) {
            const uint32_t version = r.read<uint32_t>();
            const std::string name = r.string16();
            const std::string champion = version == net::kProtocolVersion ? r.string16() : std::string();
            if (version != net::kProtocolVersion || !records.count(champion) || champion == kDummy) {
              enet_peer_disconnect(ev.peer, 0);  // an old client, or a champion this install does not have
            } else {
              // Order's side for now (one player); at its fountain's spawn locator; its stats from its record
              const SpawnPoint& sp = spawn_points[0];
              joining.push_back({ev.peer, name, {0, champion, sp.x, sp.z, 0, 0, sp.facing}});
            }
          } else if (msg == net::Msg::MoveOrder && players.count(ev.peer)) {
            Order o;
            o.unit = players[ev.peer];
            o.x = r.read<float>();
            o.z = r.read<float>();
            pending.push_back(o);
          } else if (msg == net::Msg::AttackOrder && players.count(ev.peer)) {
            Order o;
            o.unit = players[ev.peer];
            o.type = Order::Type::Attack;
            o.target = r.read<uint32_t>();
            pending.push_back(o);
          } else if (msg == net::Msg::CastSpell && players.count(ev.peer)) {
            Order o;
            o.unit = players[ev.peer];
            o.type = Order::Type::Cast;
            o.slot = r.read<uint8_t>();
            o.x = r.read<float>();
            o.z = r.read<float>();
            o.target = r.read<uint32_t>();
            pending.push_back(o);
          } else if (msg == net::Msg::BuyItem && players.count(ev.peer)) {
            Order o;
            o.unit = players[ev.peer];
            o.type = Order::Type::BuyItem;
            o.target = r.read<uint32_t>();
            pending.push_back(o);
          } else if (msg == net::Msg::SellItem && players.count(ev.peer)) {
            Order o;
            o.unit = players[ev.peer];
            o.type = Order::Type::SellItem;
            o.slot = r.read<uint8_t>();
            pending.push_back(o);
          } else if (msg == net::Msg::UseItem && players.count(ev.peer)) {
            Order o;
            o.unit = players[ev.peer];
            o.type = Order::Type::UseItem;
            o.slot = r.read<uint8_t>();
            o.x = r.read<float>();
            o.z = r.read<float>();
            o.target = r.read<uint32_t>();
            pending.push_back(o);
          } else if (msg == net::Msg::LevelSpell && players.count(ev.peer)) {
            Order o;
            o.unit = players[ev.peer];
            o.type = Order::Type::LevelSpell;
            o.slot = r.read<uint8_t>();
            pending.push_back(o);
          } else if (msg == net::Msg::SpawnDummy && players.count(ev.peer) && records.count(kDummy)) {
            // the Practice Tool's "spawn target dummy": on the enemy team, where the player points
            SpawnRequest d;
            d.team = 1;
            d.character = kDummy;
            d.x = r.read<float>();
            d.z = r.read<float>();
            dummies.push_back(d);
          }
        } catch (const std::exception& e) {
          std::fprintf(stderr, "bad packet: %s\n", e.what());
        }
        enet_packet_destroy(ev.packet);
      } else if (ev.type == ENET_EVENT_TYPE_DISCONNECT) {
        players.erase(ev.peer);
      }
    }

    // ---- simulation: as many ticks as are due (catches up after a hitch instead of slowing the game down)
    const auto now = clock::now();
    while (now >= next) {
      const int64_t start = match.clock.tick;
      if (start % kCheckpointTicks == 0) recorder.checkpoint(start, match.checksum());
      std::vector<SpawnRequest> spawns;
      for (const Joining& j : joining) spawns.push_back(j.spawn);
      spawns.insert(spawns.end(), dummies.begin(), dummies.end());
      for (Order& o : pending) o.tick = start;
      recorder.events(start, spawns, pending);
      const MatchEvents events = match.step(spawns, pending);
      const std::vector<uint32_t>& spawned = events.spawned;
      pending.clear();
      dummies.clear();
      auto broadcast = [&players, &netlog, start](net::Channel ch, const std::vector<uint8_t>& bytes) {
        netlog.write(start, ch, bytes);
        for (auto& [peer, _] : players) send(peer, ch, bytes);
      };
      // the new players: who they are, and every unit already on the map (the new units reach everyone below)
      std::vector<ENetPeer*> fresh;
      for (size_t i = 0; i < joining.size() && i < spawned.size(); ++i) {
        fresh.push_back(joining[i].peer);
        ENetPeer* peer = joining[i].peer;
        players[peer] = spawned[i];
        std::printf("%s joined as %s (unit %u)\n", joining[i].name.c_str(), joining[i].spawn.character.c_str(), spawned[i]);
        net::Writer w;
        w.put(net::Msg::Welcome).put(spawned[i]).put(match.clock.tick).put(match.start_tick());
        send(peer, net::kHandshake, w.bytes());
      }
      if (!fresh.empty())
        for (const Unit& u : match.units) {
          if (std::find(spawned.begin(), spawned.end(), u.id) != spawned.end()) continue;
          unit_state(match, u, start, [&fresh](net::Channel ch, const std::vector<uint8_t>& bytes) {
            for (ENetPeer* p : fresh) send(p, ch, bytes);
          });
        }
      joining.clear();
      if (events.winner >= 0) std::printf("the match is over: team %d wins\n", events.winner);
      emit_tick(match, events, start, broadcast);
      next += tick_len;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
  }
}
