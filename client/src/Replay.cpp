#include "Replay.h"

#include <algorithm>
#include <cmath>
#include <cstring>

namespace ba {

namespace {

// Riot's 13.3 packet ids (scrambled per patch; named from the client's own handlers and the fields' content, see
// docs/MIGRARE_12.23.md "Tabela id de pachet")
enum : uint16_t {
  kCreateHero = 79,        // keyframe: a champion (net id, name, skin, where it stands)
  kCreateTurret = 565,     // keyframe: a turret (net id, record, the map object's name + "_A")
  kSpawnUnit = 345,        // any other unit by name (turret plating, wards, pets ...)
  kUnitOwner = 355,        // +0x0c unit, +0x10 the unit it belongs to (a turret's plating)
  kBarrackSpawnUnit = 98,  // a lane minion
  kMovementState = 518,    // one unit's movement when it comes into view: standing (place, facing) or a path
  kWaypointGroup = 552,    // paths of several units
  kReplication = 595,      // replicated numbers (health ...)
  kDie = 61,
  kBasicAttackMinion = 286, kBasicAttackTurret = 26, kBasicAttackHero = 592,
  kApplyDamage = 263,
  kAnimationOverrides = 71,
  kPlayAnimation = 65, kPlayAnimation2 = 771,  // one handler in the Riot client for both
  kCreateNeutral = 359,    // a jungle monster
  kMissileLaunched = 779,  // +0x0c the net id of a missile the unit has just fired
};

// seconds a dead minion's body stays [de măsurat: the Riot client removes it itself, the server sends nothing; the
// value is our server's]
constexpr double kCorpseSeconds = 3.0;

template <typename T>
T at(const std::vector<uint8_t>& b, size_t off) {
  T v{};
  if (off + sizeof(T) <= b.size()) std::memcpy(&v, b.data() + off, sizeof(T));  // bytes the decoder left out are zero
  return v;
}

std::string text(const std::vector<uint8_t>& b) {
  std::string s(b.begin(), b.end());
  while (!s.empty() && s.back() == '\0') s.pop_back();
  return s;
}

const std::vector<uint8_t>& block(const std::vector<std::vector<uint8_t>>& blocks, size_t i) {
  static const std::vector<uint8_t> none;
  return i < blocks.size() ? blocks[i] : none;
}

/** The `which`-th string of a packet object. A string field is {pointer, u32 length, u32 capacity}; the decoder
 *  wrote the texts as blocks 1, 2 ... in the order of the fields, and none for an empty string. `fields` are the
 *  offsets of the object's string fields, in order. */
std::string string_field(const std::vector<std::vector<uint8_t>>& blocks, std::initializer_list<size_t> fields, size_t which) {
  size_t index = 1, k = 0;
  for (size_t off : fields) {
    const uint32_t len = at<uint32_t>(block(blocks, 0), off + 4);
    if (k++ == which) return len ? text(block(blocks, index)) : std::string();
    if (len) ++index;
  }
  return {};
}

/** The net id of an object the map itself places (inhibitors "Barracks_T1_L1", nexuses "HQ_T1", the minions' spawn
 *  barracks "__P_Order_Spawn_Barracks__C01"): 0xFF000000 | the low 24 bits of the CRC-32 of its name [read in the 13.3
 *  client, rva 0x2e9090; checked on 36 of the replay's 40 such ids]. */
uint32_t map_object_id(const std::string& name) {
  uint32_t crc = 0xffffffffu;
  for (unsigned char ch : name) {
    crc ^= ch;
    for (int k = 0; k < 8; ++k) crc = (crc >> 1) ^ (0xedb88320u & (0u - (crc & 1u)));
  }
  return 0xff000000u | (~crc & 0x00ffffffu);
}

}  // namespace

/** What the client has before any packet: the objects the map places, under the ids the packets will use. */
void Replay::seed(Connection& c) {
  seeded_ = true;
  if (!world_.game) return;
  for (const StructureSpawn& s : world_.game->structures) {
    if (s.kind != "inhibitor" && s.kind != "nexus") continue;
    ClientUnit u;
    u.id = map_object_id(s.object), u.team = s.team, u.skin = s.character, u.skin_id = static_cast<uint8_t>(s.skin);
    u.x = s.x, u.z = s.z, u.facing = s.facing;
    c.units[u.id] = u;
    hp_group_[u.id] = 5;
    structures_.insert(u.id);
  }
  // lanes as the level script numbers them: 0 bot (R), 1 mid (C), 2 top (L)
  static const char lane_letter[] = {'R', 'C', 'L'};
  for (uint8_t team = 0; team < 2; ++team)
    for (int lane = 0; lane < 3; ++lane)
      barracks_[map_object_id(std::string("__P_") + (team ? "Chaos" : "Order") + "_Spawn_Barracks__" + lane_letter[lane] + "01")] = {team, lane};
}

Replay::~Replay() {
  if (file_) std::fclose(file_);
}

bool Replay::open(const std::string& path, World world) {
  world_ = std::move(world);
  file_ = std::fopen(path.c_str(), "rb");
  if (!file_) return false;
  char magic[4];
  uint32_t version = 0;
  if (std::fread(magic, 1, 4, file_) != 4 || std::memcmp(magic, "BARP", 4) != 0 || std::fread(&version, 4, 1, file_) != 1 ||
      version != 1 || std::fread(&left_, 4, 1, file_) != 1) {
    std::fclose(file_);
    file_ = nullptr;
    return false;
  }
  has_pending_ = next();
  return true;
}

bool Replay::next() {
  if (!file_ || !left_) return false;
#pragma pack(push, 1)
  struct Head {
    float t;
    uint16_t id;
    uint32_t net;
    uint8_t blocks;
  } h;
#pragma pack(pop)
  if (std::fread(&h, sizeof h, 1, file_) != 1) return false;
  pending_.t = h.t, pending_.id = h.id, pending_.net = h.net;
  pending_.blocks.resize(h.blocks);
  for (auto& b : pending_.blocks) {
    uint32_t size = 0;
    if (std::fread(&size, 4, 1, file_) != 1) return false;
    b.resize(size);
    if (size && std::fread(b.data(), 1, size, file_) != size) return false;
  }
  --left_;
  return true;
}

void Replay::feed(Connection& c, double seconds) {
  if (!seeded_) seed(c);
  while (has_pending_ && pending_.t <= seconds) {
    auto& n = seen_[pending_.id];
    (apply(c, pending_) ? n.first : n.second) += 1;
    has_pending_ = next();
  }
  for (auto it = corpse_until_.begin(); it != corpse_until_.end();)
    if (seconds >= it->second) c.units.erase(it->first), it = corpse_until_.erase(it);
    else ++it;
}

/** One unit's path, as the movement packets hold it: u8 2 x points (+1: a teleport id follows), u8 flags, u32 net id,
 *  f32 speed, [u8 teleport id], one bit per coordinate after the first point (1: a signed byte added to the previous
 *  value, 0: an i16 of its own), then the coordinates; a step is 2 world units from the grid's middle. */
void Replay::movement(Connection& c, const uint8_t* buf, size_t size, double t) {
  size_t i = 0;
  auto i16 = [&](size_t p) { int16_t v = 0; if (p + 2 <= size) std::memcpy(&v, buf + p, 2); return v; };
  while (i + 10 <= size) {
    const uint8_t count = buf[i];
    uint32_t net = 0;
    float speed = 0;
    std::memcpy(&net, buf + i + 2, 4), std::memcpy(&speed, buf + i + 6, 4);
    i += 10;
    const int n = count >> 1;
    if (count & 1) ++i;
    if (n < 1) break;
    const size_t nflag = n > 1 ? (2 * static_cast<size_t>(n - 1) + 7) / 8 : 0;
    const size_t flags = i;
    i += nflag;
    int x = i16(i), z = i16(i + 2);
    i += 4;
    std::vector<net::Point> pts;
    auto world = [&](int cx, int cz) { return net::Point{2.f * static_cast<float>(cx) + world_.center_x, 2.f * static_cast<float>(cz) + world_.center_z}; };
    pts.push_back(world(x, z));
    for (int k = 1; k < n; ++k) {
      int v[2];
      for (int j = 0; j < 2; ++j) {
        const size_t bit = 2 * static_cast<size_t>(k - 1) + static_cast<size_t>(j);
        const bool delta = flags + bit / 8 < size && (buf[flags + bit / 8] >> (bit % 8) & 1);
        if (delta) v[j] = (j ? z : x) + (i < size ? static_cast<int8_t>(buf[i]) : 0), i += 1;
        else v[j] = i16(i), i += 2;
      }
      x = v[0], z = v[1];
      pts.push_back(world(x, z));
    }
    auto it = c.units.find(net);
    if (it == c.units.end()) continue;
    ClientUnit& u = it->second;
    if (pts.size() == 1) u.x = pts[0].x, u.z = pts[0].z;
    u.path = std::move(pts);
    u.speed = speed;
    const double tick = t / kTickSeconds;
    u.path_tick = static_cast<int64_t>(std::floor(tick));
    u.path_frac = tick - std::floor(tick);
    u.dashing = false;
  }
}

/** Packet 595: per unit `u8 group mask, u32 net id`, then per group `u32 value mask, u8 size, values`. Health is the
 *  first value (bit 0, a float: 4 bytes, 0xff alone = 0, 0xfe + 4 bytes) of group 5 for champions and turrets, of
 *  group 3 for minions and the other spawned units [measured on the replay]; a champion's bit 1 is its full health. */
void Replay::replication(Connection& c, const std::vector<uint8_t>& buf, double t) {
  size_t i = 0;
  auto value = [&](const uint8_t* d, size_t n, size_t& p, float& out) {
    if (p >= n) return false;
    if (d[p] == 0xff) return out = 0.f, p += 1, true;
    if (d[p] == 0xfe) ++p;
    if (p + 4 > n) return false;
    std::memcpy(&out, d + p, 4);
    return p += 4, true;
  };
  while (i + 5 <= buf.size()) {
    const uint8_t primary = buf[i];
    uint32_t net = 0;
    std::memcpy(&net, buf.data() + i + 1, 4);
    i += 5;
    for (int g = 0; g < 8; ++g) {
      if (!(primary >> g & 1)) continue;
      if (i + 5 > buf.size()) return;
      uint32_t mask = 0;
      std::memcpy(&mask, buf.data() + i, 4);
      const uint8_t size = buf[i + 4];
      i += 5;
      const uint8_t* d = buf.data() + i;
      const size_t n = std::min<size_t>(size, buf.size() - i);
      i += size;
      auto hg = hp_group_.find(net);
      if (hg == hp_group_.end() || hg->second != g || !(mask & 1)) continue;
      auto it = c.units.find(net);
      if (it == c.units.end()) continue;
      ClientUnit& u = it->second;
      size_t p = 0;
      float hp = 0, full = 0;
      if (!value(d, n, p, hp)) continue;
      if (u.max_hp > 0 && hp < u.hp) ++u.hits, u.hit_time = t;
      u.hp = hp;
      if (g == 5 && (mask & 2) && value(d, n, p, full)) u.max_hp = full;
      u.max_hp = std::max(u.max_hp, hp);  // a unit enters at full health
    }
  }
}

bool Replay::apply(Connection& c, const Packet& p) {
  const std::vector<uint8_t>& o = block(p.blocks, 0);
  const MapGame* game = world_.game;
  const double t = p.t;
  switch (p.id) {
    case kCreateHero: {
      ClientUnit u;
      u.id = at<uint32_t>(o, 0x18);
      u.skin = string_field(p.blocks, {0x20, 0x30}, 0);  // +0x20 the champion, +0x30 the player's name
      u.skin_id = static_cast<uint8_t>(at<uint32_t>(o, 0x64));
      // +0x68 is 1 for the five champions that stand at Order's spawn, 0 for Chaos's [measured on this replay]
      u.team = at<uint8_t>(o, 0x68) == 1 ? 0 : 1;
      u.x = at<float>(o, 0x44), u.z = at<float>(o, 0x4c);
      u.facing = std::atan2(at<float>(o, 0x0c), at<float>(o, 0x14));
      c.units[u.id] = u;
      hp_group_[u.id] = 5;
      return true;
    }
    case kCreateTurret: {
      std::string name = string_field(p.blocks, {0x20, 0x40}, 1);  // +0x20 its record ("SR_Outer"), +0x40 its name
      if (name.size() > 2 && name.compare(name.size() - 2, 2, "_A") == 0) name.resize(name.size() - 2);
      if (!game) return false;
      for (const StructureSpawn& s : game->structures) {
        if (s.object != name) continue;
        ClientUnit u;
        u.id = p.net, u.team = s.team, u.skin = s.character, u.skin_id = static_cast<uint8_t>(s.skin);
        u.x = s.x, u.z = s.z, u.facing = s.facing;
        c.units[u.id] = u;
        hp_group_[u.id] = 5;
        structures_.insert(u.id);
        return true;
      }
      return false;
    }
    case kSpawnUnit: {
      ClientUnit u;
      u.id = at<uint32_t>(o, 0x2c);
      u.skin = string_field(p.blocks, {0x3c, 0x5c}, 0);  // +0x3c the character ("TestCubeRender"), +0x5c its name ("AatroxWCenterMinion")
      u.x = at<float>(o, 0x0c), u.z = at<float>(o, 0x14);
      if (t > 0) u.spawn_time = t;
      c.units[u.id] = u;
      hp_group_[u.id] = 3;
      return true;
    }
    case kUnitOwner: {
      // the plating takes its turret's side; its skin is 0 on Order, 2 on Chaos [measured: the plates' texture]
      auto unit = c.units.find(at<uint32_t>(o, 0x0c)), owner = c.units.find(at<uint32_t>(o, 0x10));
      if (unit == c.units.end() || owner == c.units.end()) return false;
      unit->second.team = owner->second.team;
      if (unit->second.skin == "PreSeason_Turret_Shield") unit->second.skin_id = owner->second.team ? 2 : 0;
      return true;
    }
    case kBarrackSpawnUnit: {
      const uint32_t from = at<uint32_t>(o, 0x1c);
      auto b = barracks_.find(from);
      if (b == barracks_.end() || !game) return false;
      static const char* const kinds[] = {"Melee", "Ranged", "Siege", "Super"};  // +0x14: 4, 5, 6, 7
      const int kind = at<uint8_t>(o, 0x14) - 4;
      if (kind < 0 || kind > 3) return false;
      ClientUnit u;
      u.id = at<uint32_t>(o, 0x10);
      u.team = b->second.first;
      u.skin = std::string("SRU_") + (u.team ? "Chaos" : "Order") + "Minion" + kinds[kind];
      u.x = game->minion_spawn[u.team][static_cast<size_t>(b->second.second)][0];
      u.z = game->minion_spawn[u.team][static_cast<size_t>(b->second.second)][1];
      u.spawn_time = t;
      c.units[u.id] = u;
      hp_group_[u.id] = 3;
      corpses_.insert(u.id);
      return true;
    }
    case kCreateNeutral: {
      // +0x14 where it stands, +0x3c the point it faces; strings: +0x24 its name ("SRU_Red4.1.1"), +0x30 the clip
      // it enters with ("spawn"), +0x4c the character ("SRU_Red"), +0x70 the name again; +0x58 = 300, the neutral team
      ClientUnit u;
      u.id = p.net;
      u.team = 2;
      u.skin = string_field(p.blocks, {0x24, 0x30, 0x4c, 0x70}, 2);
      u.x = at<float>(o, 0x14), u.z = at<float>(o, 0x1c);
      const float fx = at<float>(o, 0x3c) - u.x, fz = at<float>(o, 0x44) - u.z;
      if (fx != 0 || fz != 0) u.facing = std::atan2(fx, fz);
      u.spawn_time = t;
      const std::string enter = string_field(p.blocks, {0x24, 0x30, 0x4c, 0x70}, 1);
      if (!enter.empty()) u.forced.clip = enter, u.forced.start = t, u.forced.once = true, u.forced.serial = 1;
      c.units[u.id] = u;
      hp_group_[u.id] = 3;
      corpses_.insert(u.id);
      return true;
    }
    case kPlayAnimation:
    case kPlayAnimation2: {
      // +0x0c the clip's name, +0x1c its speed (1.0 in every packet seen)
      auto it = c.units.find(p.net);
      if (it == c.units.end()) return false;
      ClientUnit::Forced& f = it->second.forced;
      ++f.serial;
      f.clip = string_field(p.blocks, {0x0c}, 0);
      f.start = t, f.end = -1, f.once = true;
      return true;
    }
    case kMissileLaunched: {
      // the missile of the unit's basic attack (the attack packet named it at +0x2c) leaves now; a spell's missile
      // comes with a packet of its own (117), not read yet
      auto it = c.units.find(p.net);
      auto am = attack_missile_.find(p.net);
      if (it == c.units.end() || am == attack_missile_.end() || am->second != at<uint32_t>(o, 0x0c)) return false;
      const CharacterRecordData* rec = world_.record ? world_.record(it->second.skin) : nullptr;
      const AttackSlot* s = rec ? find_attack(*rec, it->second.attack.spell) : nullptr;
      if (!s) return false;
      Connection::Missile m;
      m.from = p.net, m.to = it->second.attack.target, m.speed = s->missile_speed, m.start = t, m.spell = s->name;
      c.missiles.push_back(m);
      return true;
    }
    case kMovementState: {
      // the block: 26 bytes of the unit's state, u8 kind, u32 sync id, then for kind 3 a byte, its place (x, z) and
      // the way it faces (dx, dz); for kind 2 one path as in the group packet; kind 0 or an empty block: nothing
      std::vector<uint8_t> b = block(p.blocks, 1);
      b.resize(std::max<size_t>(b.size(), at<uint32_t>(o, 0x14)));
      if (b.size() < 31) return c.units.count(p.net) || barracks_.count(p.net);  // nothing in it: the unit does not move
      const uint8_t kind = b[26];
      if (kind == 3) {
        const float x = at<float>(b, 32), z = at<float>(b, 36);
        auto it = c.units.find(p.net);
        if (it != c.units.end()) {
          it->second.x = x, it->second.z = z, it->second.path.clear();
          // structures keep the facing of their map object
          if (!structures_.count(p.net)) it->second.facing = std::atan2(at<float>(b, 40), at<float>(b, 44));
          return true;
        }
        return false;
      }
      if (kind == 2) {
        movement(c, b.data() + 31, b.size() - 31, t);
        return true;
      }
      return false;
    }
    case kWaypointGroup: {
      std::vector<uint8_t> b = block(p.blocks, 1);
      b.resize(std::max<size_t>(b.size(), at<uint32_t>(o, 0x14)));
      movement(c, b.data(), b.size(), t);
      return true;
    }
    case kReplication: {
      std::vector<uint8_t> b = block(p.blocks, 1);
      b.resize(std::max<size_t>(b.size(), at<uint32_t>(o, 0x10)));
      replication(c, b, t);
      return true;
    }
    case kDie: {
      auto it = c.units.find(p.net);
      if (it == c.units.end()) return false;
      it->second.dead = true, it->second.death_time = t, it->second.path.clear();
      if (corpses_.count(p.net)) corpse_until_[p.net] = t + kCorpseSeconds;
      return true;
    }
    case kBasicAttackMinion:
    case kBasicAttackTurret:
    case kBasicAttackHero: {
      auto it = c.units.find(p.net);
      if (it == c.units.end()) return false;
      ClientUnit& u = it->second;
      const uint32_t target = at<uint32_t>(o, 0x14);
      // +0x18: the attack slot, 64 = the basic attack, 65.. the extra ones, 73.. the critical ones [documented slot
      // numbering; 64 / 66 / 70 / 72 seen]
      const int slot = at<uint8_t>(o, 0x18) - 64;
      const CharacterRecordData* rec = world_.record ? world_.record(u.skin) : nullptr;
      ClientUnit::Attack a;
      a.serial = u.attack.serial + 1;
      a.start = t;
      a.target = target;
      a.animation = "Attack1";
      const AttackSlot* s = nullptr;
      if (rec && !rec->attacks.empty()) {
        const int n = static_cast<int>(rec->attacks.size());
        s = slot >= 9 && slot - 9 < static_cast<int>(rec->crits.size()) ? &rec->crits[static_cast<size_t>(slot - 9)]
                                                                         : &rec->attacks[static_cast<size_t>(std::clamp(slot, 0, n - 1))];
        const AttackSlot& base = rec->attacks[0];
        const AttackSlot& timing = s->has_times || s->has_offset ? *s : base;
        // the unit's own attack speed is replicated, not read yet: its record's base value [de măsurat]
        const float attack_time = rec->attack_speed > 0 ? 1.f / rec->attack_speed : 1.f;
        const float percent = timing.has_times && timing.total_time > 0 ? timing.cast_time / timing.total_time : 0.3f + timing.offset;
        a.spell = s->name, a.animation = s->animation;
        a.total = attack_time, a.windup = attack_time * percent, a.cast = s->spell_cast_time;
      }
      u.attack = a;
      u.path.clear();
      // a unit turns to its target; a structure stands as built
      auto tg = c.units.find(target);
      if (tg != c.units.end() && !structures_.count(p.net)) u.facing = std::atan2(tg->second.x - u.x, tg->second.z - u.z);
      attack_missile_[p.net] = at<uint32_t>(o, 0x2c);  // the missile this attack will fire (see kMissileLaunched)
      return true;
    }
    case kApplyDamage: {
      Connection::Hit h;
      h.time = t, h.target = p.net, h.source = at<uint32_t>(o, 0x20);
      auto src = c.units.find(h.source);
      if (src != c.units.end()) h.spell = src->second.attack.spell;
      c.hits.push_back(h);
      return true;
    }
    case kAnimationOverrides: {
      auto it = c.units.find(p.net);
      if (it == c.units.end()) return false;
      // the unit's whole list: +0x10 entries of two strings (the clip to play, the clip it stands in for). The
      // decoder gives each entry twice (the vector's old and new storage): pairs are read from the strings
      it->second.anim_overrides.clear();
      for (size_t b = 2; b + 1 < p.blocks.size(); b += 2) {
        std::pair<std::string, std::string> e{text(p.blocks[b]), text(p.blocks[b + 1])};
        if (std::find(it->second.anim_overrides.begin(), it->second.anim_overrides.end(), e) == it->second.anim_overrides.end())
          it->second.anim_overrides.push_back(e);
      }
      return true;
    }
    default:
      return false;
  }
  return false;
}

void Replay::report(const std::string& path) const {
  std::FILE* f = std::fopen(path.c_str(), "w");
  if (!f) return;
  uint64_t kinds_done = 0, done = 0, total = 0;
  for (const auto& [id, n] : seen_) kinds_done += n.first > 0, done += n.first, total += n.first + n.second;
  std::fprintf(f, "replay packets so far: %llu, applied by a handler %llu (%.1f%%); kinds seen %zu, with a handler %llu\n",
               static_cast<unsigned long long>(total), static_cast<unsigned long long>(done), total ? 100.0 * static_cast<double>(done) / static_cast<double>(total) : 0.0,
               seen_.size(), static_cast<unsigned long long>(kinds_done));
  for (const auto& [id, n] : seen_)
    std::fprintf(f, "%4u  applied %8llu  not handled %8llu\n", id, static_cast<unsigned long long>(n.first), static_cast<unsigned long long>(n.second));
  std::fclose(f);
}

}  // namespace ba
