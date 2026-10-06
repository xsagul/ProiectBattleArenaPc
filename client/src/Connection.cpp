#include "Connection.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>

#include "ba/ByteReader.h"

namespace ba {

double seconds_now() {
  using namespace std::chrono;
  return duration<double>(steady_clock::now().time_since_epoch()).count();
}

void Connection::hello() {
  if (!peer_ || hello_sent_) return;
  net::Writer w;
  w.put(net::Msg::Hello).put(net::kProtocolVersion).str(name_).str(champion_);
  enet_peer_send(peer_, net::kHandshake, enet_packet_create(w.bytes().data(), w.bytes().size(), ENET_PACKET_FLAG_RELIABLE));
  hello_sent_ = true;
}

void Connection::ready() {
  hold_ = false;
  if (connected_) hello();
}

void Connection::pump() {
  ENetEvent ev;
  while (host_ && enet_host_service(host_, &ev, 0) > 0) {
    if (ev.type == ENET_EVENT_TYPE_CONNECT) {
      connected_ = true;
      if (!hold_) hello();
    } else if (ev.type == ENET_EVENT_TYPE_RECEIVE) {
      enet_packet_destroy(ev.packet);  // the server sends nothing before the client has joined
    }
  }
  if (connected_ && peer_) ping_ = static_cast<int>(peer_->roundTripTime);
}

bool Connection::connect(const char* host, uint16_t port, const std::string& name, const std::string& champion, bool hold) {
  hold_ = hold;
  if (enet_initialize() != 0) return false;
  host_ = enet_host_create(nullptr, 1, net::kChannels, 0, 0);
  if (!host_) return false;
  ENetAddress a{};
  enet_address_set_host(&a, host);
  a.port = port;
  peer_ = enet_host_connect(host_, &a, net::kChannels, 0);
  name_ = name;
  champion_ = champion;
  return peer_ != nullptr;
}

Connection::~Connection() {
  if (peer_) enet_peer_disconnect_now(peer_, 0);
  if (host_) enet_host_destroy(host_);
  enet_deinitialize();
}

void Connection::move(float x, float z) {
  if (!peer_) return;
  net::Writer w;
  w.put(net::Msg::MoveOrder).put(x).put(z);
  enet_peer_send(peer_, net::kCommands, enet_packet_create(w.bytes().data(), w.bytes().size(), ENET_PACKET_FLAG_RELIABLE));
}

void Connection::attack(uint32_t target) {
  if (!peer_) return;
  net::Writer w;
  w.put(net::Msg::AttackOrder).put(target);
  enet_peer_send(peer_, net::kCommands, enet_packet_create(w.bytes().data(), w.bytes().size(), ENET_PACKET_FLAG_RELIABLE));
}

void Connection::spawn_dummy(float x, float z) {
  if (!peer_) return;
  net::Writer w;
  w.put(net::Msg::SpawnDummy).put(x).put(z);
  enet_peer_send(peer_, net::kCommands, enet_packet_create(w.bytes().data(), w.bytes().size(), ENET_PACKET_FLAG_RELIABLE));
}

void Connection::cast(uint8_t slot, float x, float z, uint32_t target) {
  if (!peer_) return;
  net::Writer w;
  w.put(net::Msg::CastSpell).put(slot).put(x).put(z).put(target);
  enet_peer_send(peer_, net::kCommands, enet_packet_create(w.bytes().data(), w.bytes().size(), ENET_PACKET_FLAG_RELIABLE));
}

void Connection::buy_item(uint32_t item) {
  if (!peer_) return;
  net::Writer w;
  w.put(net::Msg::BuyItem).put(item);
  enet_peer_send(peer_, net::kCommands, enet_packet_create(w.bytes().data(), w.bytes().size(), ENET_PACKET_FLAG_RELIABLE));
}

void Connection::sell_item(uint8_t slot) {
  if (!peer_) return;
  net::Writer w;
  w.put(net::Msg::SellItem).put(slot);
  enet_peer_send(peer_, net::kCommands, enet_packet_create(w.bytes().data(), w.bytes().size(), ENET_PACKET_FLAG_RELIABLE));
}

void Connection::use_item(uint8_t slot, float x, float z, uint32_t target) {
  if (!peer_) return;
  net::Writer w;
  w.put(net::Msg::UseItem).put(slot).put(x).put(z).put(target);
  enet_peer_send(peer_, net::kCommands, enet_packet_create(w.bytes().data(), w.bytes().size(), ENET_PACKET_FLAG_RELIABLE));
}

void Connection::level_spell(uint8_t slot) {
  if (!peer_) return;
  net::Writer w;
  w.put(net::Msg::LevelSpell).put(slot);
  enet_peer_send(peer_, net::kCommands, enet_packet_create(w.bytes().data(), w.bytes().size(), ENET_PACKET_FLAG_RELIABLE));
}

void Connection::update(double now_tick) {
  ENetEvent ev;
  while (host_ && enet_host_service(host_, &ev, 0) > 0) {
    if (ev.type == ENET_EVENT_TYPE_CONNECT) {
      connected_ = true;
      if (!hold_) hello();
    } else if (ev.type == ENET_EVENT_TYPE_RECEIVE) {
      try {
        receive(ev.packet->data, ev.packet->dataLength, seconds_now());
      } catch (const std::exception& e) {
        std::fprintf(stderr, "bad packet: %s\n", e.what());
      }
      enet_packet_destroy(ev.packet);
    }
  }
  // Walk every unit along its path from where it was at path_tick.
  if (connected_ && peer_) ping_ = static_cast<int>(peer_->roundTripTime);
  for (auto& [id, u] : units) {
    u.moving = false;
    if (u.path.size() < 2) {
      u.dashing = false;
      continue;
    }
    double budget = std::max(0.0, (now_tick - static_cast<double>(u.path_tick) - u.path_frac) * kTickSeconds) * u.speed;
    float x = u.path[0].x;
    float z = u.path[0].z;
    for (size_t i = 1; i < u.path.size(); ++i) {
      const float dx = u.path[i].x - x;
      const float dz = u.path[i].z - z;
      const double d = std::sqrt(dx * dx + dz * dz);
      if (d <= budget) {
        x = u.path[i].x;
        z = u.path[i].z;
        budget -= d;
      } else {
        // on this segment: the unit faces along it
        x += static_cast<float>(dx / d * budget);
        z += static_cast<float>(dz / d * budget);
        u.facing = std::atan2(dx, dz);
        u.moving = true;
        break;
      }
    }
    u.x = x;
    u.z = z;
    if (!u.moving) u.dashing = false;
  }
}

void Connection::receive(const uint8_t* data, size_t size, double now_seconds) {
  ByteReader r({data, size});
  switch (static_cast<net::Msg>(r.read<uint8_t>())) {
    case net::Msg::Welcome:
      my_unit = r.read<uint32_t>();
      server_tick = r.read<int64_t>();
      welcome_tick = server_tick;
      game_start_tick = r.read<int64_t>();
      server_tick_at = now_seconds;
      break;
    case net::Msg::UnitSpawn: {
      ClientUnit u;
      u.id = r.read<uint32_t>();
      u.team = r.read<uint8_t>();
      u.skin = r.string16();
      u.skin_id = r.read<uint8_t>();
      u.x = r.read<float>();
      u.z = r.read<float>();
      u.facing = r.read<float>();
      const int64_t spawned = r.read<int64_t>();
      if (welcome_tick >= 0 && spawned > welcome_tick) u.spawn_time = tick_time(spawned);
      if (!units.count(u.id)) units[u.id] = u;
      break;
    }
    case net::Msg::Waypoints: {
      int64_t start = 0;
      for (net::UnitPath& p : net::read_waypoints(r, start)) {
        auto it = units.find(p.id);
        if (it == units.end()) continue;
        // a path of one point: the unit stands there (it stopped, or other units pushed it)
        if (p.points.size() == 1) it->second.x = p.points[0].x, it->second.z = p.points[0].z;
        it->second.path = std::move(p.points);
        it->second.speed = p.speed;
        it->second.path_tick = start;
        it->second.path_frac = 0;
        it->second.dashing = false;
      }
      if (start > server_tick) {
        server_tick = start;
        server_tick_at = now_seconds;
      }
      break;
    }
    case net::Msg::UnitHealth: {
      const uint32_t id = r.read<uint32_t>();
      const float hp = r.read<float>(), max_hp = r.read<float>();
      const float shield = r.remaining() >= sizeof(float) ? r.read<float>() : 0.0f;
      auto it = units.find(id);
      if (it != units.end()) {
        if (it->second.max_hp > 0 && hp < it->second.hp) ++it->second.hits, it->second.hit_time = now_seconds;
        it->second.hp = hp, it->second.max_hp = max_hp, it->second.shield = shield;
      }
      break;
    }
    case net::Msg::UnitAttack: {
      const int64_t tick = r.read<int64_t>();
      const uint32_t id = r.read<uint32_t>(), target = r.read<uint32_t>();
      ClientUnit::Attack a;
      a.spell = r.string16();
      a.animation = r.string16();
      a.windup = r.read<float>(), a.total = r.read<float>(), a.cast = r.read<float>();
      const float facing = r.read<float>();
      a.target = target;
      auto it = units.find(id);
      if (it == units.end()) break;
      a.serial = it->second.attack.serial + 1;
      a.start = tick_time(tick);
      it->second.attack = a;
      it->second.path.clear();
      it->second.facing = facing;
      break;
    }
    case net::Msg::Missile: {
      Missile m;
      m.start = tick_time(r.read<int64_t>());
      m.from = r.read<uint32_t>(), m.to = r.read<uint32_t>();
      m.speed = r.read<float>();
      m.spell = r.string16();
      missiles.push_back(m);
      break;
    }
    case net::Msg::UnitRemove: {
      units.erase(r.read<uint32_t>());
      break;
    }
    case net::Msg::UnitHit: {
      Hit h;
      h.time = tick_time(r.read<int64_t>());
      h.source = r.read<uint32_t>(), h.target = r.read<uint32_t>();
      h.spell = r.string16();
      hits.push_back(h);
      break;
    }
    case net::Msg::UnitStats: {
      auto it = units.find(r.read<uint32_t>());
      const uint8_t level = r.read<uint8_t>();
      const float xp = r.read<float>(), gold = r.read<float>(), par = r.read<float>(), max_par = r.read<float>();
      const float ad = r.read<float>(), armor = r.read<float>(), mr = r.read<float>(), as = r.read<float>(), ms = r.read<float>();
      if (it == units.end()) break;
      ClientUnit& u = it->second;
      u.level = level, u.xp = xp, u.gold = gold, u.par = par, u.max_par = max_par;
      u.ad = ad, u.armor = armor, u.spell_block = mr, u.attack_speed = as, u.move_speed = ms;
      u.kills = r.read<uint16_t>(), u.deaths = r.read<uint16_t>(), u.assists = r.read<uint16_t>(), u.minions_killed = r.read<uint16_t>();
      u.ap = r.read<float>(), u.ability_haste = r.read<float>(), u.crit = r.read<float>();
      break;
    }
    case net::Msg::UnitItems: {
      auto it = units.find(r.read<uint32_t>());
      int items[7], stacks[7];
      for (int k = 0; k < 7; ++k) items[k] = static_cast<int>(r.read<uint32_t>()), stacks[k] = r.read<uint8_t>();
      if (it == units.end()) break;
      for (int k = 0; k < 7; ++k) it->second.items[k] = items[k], it->second.item_stacks[k] = stacks[k];
      break;
    }
    case net::Msg::UnitSpells: {
      auto it = units.find(r.read<uint32_t>());
      const uint8_t points = r.read<uint8_t>();
      ClientUnit::Spell spells[4];
      for (ClientUnit::Spell& s : spells) {
        s.level = r.read<uint8_t>();
        s.ready_at = now_seconds + r.read<float>();
        s.cooldown_total = r.read<float>();
        s.cost = r.read<float>();
      }
      if (it == units.end()) break;
      it->second.skill_points = points;
      for (int i = 0; i < 4; ++i) it->second.spells[i] = spells[i];
      break;
    }
    case net::Msg::SpellCast: {
      const int64_t tick = r.read<int64_t>();
      auto it = units.find(r.read<uint32_t>());
      r.read<uint8_t>();
      ClientUnit::Cast c;
      c.spell = r.string16();
      c.animation = r.string16();
      c.cast_time = r.read<float>();
      const float x = r.read<float>(), z = r.read<float>();
      r.read<uint32_t>();
      if (it == units.end()) break;
      c.serial = it->second.cast.serial + 1;
      c.start = tick_time(tick);
      it->second.cast = c;
      // a cast with a cast time stops the caster and turns it to where it casts
      if (c.cast_time > 0) {
        it->second.path.clear();
        if (std::hypot(x - it->second.x, z - it->second.z) > 1.f) it->second.facing = std::atan2(x - it->second.x, z - it->second.z);
      }
      break;
    }
    case net::Msg::BuffChange:
      break;  // nothing shows buffs yet: their effects come as Effect messages
    case net::Msg::SkillMissile: {
      SkillMissile m;
      m.start = tick_time(r.read<int64_t>());
      m.id = r.read<uint32_t>(), m.unit = r.read<uint32_t>();
      m.spell = r.string16();
      m.x = r.read<float>(), m.z = r.read<float>(), m.dx = r.read<float>(), m.dz = r.read<float>();
      m.speed = r.read<float>(), m.range = r.read<float>();
      m.effect = r.string16();
      m.accel = r.read<float>(), m.speed_limit = r.read<float>();
      skill_missiles.push_back(m);
      break;
    }
    case net::Msg::SkillMissileEnd:
      skill_missiles_ended.push_back(r.read<uint32_t>());
      break;
    case net::Msg::Dash: {
      const int64_t tick = r.read<int64_t>();
      auto it = units.find(r.read<uint32_t>());
      const float x = r.read<float>(), z = r.read<float>(), speed = r.read<float>();
      if (it == units.end()) break;
      ClientUnit& u = it->second;
      if (speed <= 0) {
        u.x = x, u.z = z, u.path.clear();
      } else {
        if (std::hypot(x - u.x, z - u.z) > 1.f) u.facing = std::atan2(x - u.x, z - u.z);
        u.path = {net::Point{u.x, u.z}, net::Point{x, z}};
        u.speed = speed, u.path_tick = tick, u.path_frac = 0, u.dashing = true;
      }
      break;
    }
    case net::Msg::Effect: {
      EffectChange e;
      e.unit = r.read<uint32_t>();
      e.stop = r.read<uint8_t>() != 0;
      e.key = r.string16();
      e.bone = r.string16();
      e.seconds = r.read<float>();
      e.owner = r.read<uint32_t>();
      effects.push_back(e);
      break;
    }
    case net::Msg::GroundEffect: {
      GroundEffect e;
      e.id = r.read<uint32_t>();
      e.stop = r.read<uint8_t>() != 0;
      e.owner = r.read<uint32_t>();
      e.key = r.string16();
      e.x = r.read<float>(), e.z = r.read<float>();
      e.tx = r.read<float>(), e.tz = r.read<float>();
      e.seconds = r.read<float>();
      e.height = r.read<float>();
      ground_effects.push_back(e);
      break;
    }
    case net::Msg::Animation: {
      const int64_t tick = r.read<int64_t>();
      auto it = units.find(r.read<uint32_t>());
      const std::string clip = r.string16();
      const float seconds = r.read<float>();
      if (it == units.end()) break;
      ClientUnit::Forced& f = it->second.forced;
      ++f.serial;
      f.clip = clip;
      f.start = tick_time(tick);
      f.end = seconds > 0 ? f.start + seconds : -1;
      break;
    }
    case net::Msg::GameEnd:
      winner = r.read<uint8_t>();
      break;
    case net::Msg::UnitRespawn: {
      r.read<int64_t>();
      auto it = units.find(r.read<uint32_t>());
      const float x = r.read<float>(), z = r.read<float>(), facing = r.read<float>();
      if (it == units.end()) break;
      ClientUnit& u = it->second;
      u.dead = false, u.x = x, u.z = z, u.facing = facing;
      u.path.clear(), u.attack = ClientUnit::Attack{}, u.hit_time = -1;
      ++u.respawns;
      u.respawn_time = now_seconds;
      break;
    }
    case net::Msg::UnitDeath: {
      const double when = tick_time(r.read<int64_t>());
      auto it = units.find(r.read<uint32_t>());
      if (it != units.end()) it->second.dead = true, it->second.death_time = when, it->second.path.clear();
      break;
    }
    default:
      break;
  }
}

}  // namespace ba
