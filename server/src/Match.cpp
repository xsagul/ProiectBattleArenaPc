#include "Match.h"

#include <algorithm>
#include <cmath>
#include <cstring>

namespace ba {

namespace {

/** Seconds as whole ticks, never early [de măsurat: League's rounding]. */
int64_t ticks(double seconds) { return std::max<int64_t>(1, static_cast<int64_t>(std::ceil(seconds / kTickSeconds - 1e-9))); }

float distance(const Unit& a, const Unit& b) { return std::hypot(a.x - b.x, a.z - b.z); }

bool structure(const Unit& u) {
  return u.kind == UnitType::Turret || u.kind == UnitType::Inhibitor || u.kind == UnitType::Nexus || u.kind == UnitType::Fountain;
}

/** How often minions look around for a target and turrets re-check theirs [de măsurat: League's own rate]. */
constexpr int64_t kThinkTicks = 8;
/** How long a dead minion stays before it leaves the match (its death animation) [de măsurat]. */
constexpr double kMinionCorpseSeconds = 3.0;
/** How long an attack counts as "attacking" someone, for the aggro rules [de măsurat]. */
constexpr double kAggroMemorySeconds = 2.0;
/** A lane waypoint counts as reached within this distance [de măsurat]. */
constexpr float kWaypointReach = 150.f;
/** "No enemy minions nearby" for a turret's Reinforced Armor: the documentation gives no distance [alegere proprie, de
 *  măsurat]. */
constexpr float kReinforcedArmorRange = 1000.f;

bool tagged(const Unit& u, const char* tag) { return u.record && u.record->tags.find(tag) != std::string::npos; }

/** The class a unit has in the mode's damage ratios (dr_HeroToUnit ...): champions are heroes, structures buildings,
 *  everything else units. */
const char* damage_class(const Unit& u) { return u.kind == UnitType::Champion ? "Hero" : structure(u) ? "Building" : "Unit"; }

/** A unit pushed further than this from where its clients last saw it is sent to them again [alegere proprie]. */
constexpr float kPushReport = 12.f;
constexpr double kMinionPathResend = 2.0;  // seconds, see the push report below

}  // namespace

Match::Match(uint64_t match_id, const NavGrid* nav, const std::map<std::string, CharacterRecordData>* records, const MapGame* map)
    : random(match_id), nav_(nav), records_(records), map_(map) {
  // room for every unit a match ever has at once: units are named by reference while scripts run, and scripts may make
  // new ones (a vector that grew would move them)
  units.reserve(8192);
}

Unit& Match::spawn(uint8_t team, const std::string& skin, float x, float z) {
  Unit u;
  u.id = next_id_++;
  u.team = team;
  u.skin = skin;
  u.spawn_tick = clock.tick;
  u.x = x;
  u.z = z;
  index_[u.id] = units.size();
  units.push_back(u);
  return units.back();
}

Unit* Match::unit(uint32_t id) {
  auto it = index_.find(id);
  return it == index_.end() ? nullptr : &units[it->second];
}

const Unit* Match::unit(uint32_t id) const {
  auto it = index_.find(id);
  return it == index_.end() ? nullptr : &units[it->second];
}

double Match::game_seconds() const { return start_tick_ < 0 ? -1.0 : static_cast<double>(clock.tick - start_tick_) * kTickSeconds; }

void Match::set_record(Unit& u, const CharacterRecordData* r) {
  u.record = r;
  if (!r) return;
  u.stats.max_hp = r->base_hp;
  u.stats.ad = r->base_damage;
  u.stats.armor = r->base_armor;
  u.stats.spell_block = r->base_spell_block;
  u.stats.attack_range = r->attack_range;
  u.stats.attack_speed = r->attack_speed;
  u.stats.move_speed = r->move_speed;
  u.stats.gameplay_radius = r->gameplay_radius;
  u.stats.acquisition_range = r->acquisition_range;
  u.hp = u.max_hp = u.stats.max_hp;
  u.move_speed = r->move_speed;
  u.pathfinding_radius = r->pathfinding_radius;
  u.base = u.stats;
  u.minion = tagged(u, "Minion_Lane_Melee")    ? MinionKind::Melee
             : tagged(u, "Minion_Lane_Ranged") ? MinionKind::Caster
             : tagged(u, "Minion_Lane_Siege")  ? MinionKind::Siege
             : tagged(u, "Minion_Lane_Super")  ? MinionKind::Super
                                               : MinionKind::None;
}

void Match::place_structures(float health_scale) {
  health_scale_ = health_scale;
  if (!map_) return;
  // the engine's own: inhibitors and nexuses (the turrets are the level script's CreateChildTurret, MatchLevel.cpp)
  for (const StructureSpawn& s : map_->structures) {
    if (s.kind != "inhibitor" && s.kind != "nexus") continue;
    Unit& u = spawn(s.team, s.character, s.x, s.z);
    u.skin_id = static_cast<uint8_t>(s.skin);
    u.facing = s.facing;
    u.kind = s.kind == "turret" ? UnitType::Turret : s.kind == "inhibitor" ? UnitType::Inhibitor : s.kind == "nexus" ? UnitType::Nexus : UnitType::Fountain;
    u.lane = s.lane;
    u.position = s.position;
    set_record(u, record_at(s.record));
    // objectcfg_srx.cfg's health and footprint (inhibitors and nexuses: their records carry none)
    if (s.max_hp > 0) u.stats.max_hp = u.hp = u.max_hp = s.max_hp;
    // the mode's own inhibitor health (GameModeConstants bar_MaxHP: "barracks") goes over the object file's
    if (u.kind == UnitType::Inhibitor && constant("bar_MaxHP", 0) > 0) u.stats.max_hp = u.hp = u.max_hp = constant("bar_MaxHP", 0);
    if (s.collision_radius > 0) u.stats.gameplay_radius = s.collision_radius;  // [dedus: the footprint as the target's edge]
    u.move_speed = u.stats.move_speed = 0;
    if (health_scale != 1.f && u.kind != UnitType::Fountain) u.stats.max_hp = u.hp = u.max_hp = u.max_hp * health_scale;
    u.base = u.stats;
    u.invulnerable = true;  // until the level script lets it be hurt
  }
}

uint64_t Match::checksum() const {
  // FNV-1a 64 over the raw bits: no rounding hides a divergence
  uint64_t h = 0xcbf29ce484222325ull;
  auto mix = [&h](const void* p, size_t n) {
    const auto* b = static_cast<const uint8_t*>(p);
    for (size_t i = 0; i < n; ++i) h = (h ^ b[i]) * 0x100000001b3ull;
  };
  mix(&clock.tick, sizeof clock.tick);
  const uint64_t rnd = random.state();
  mix(&rnd, sizeof rnd);
  for (const Unit& u : units) {
    mix(&u.id, sizeof u.id), mix(&u.team, sizeof u.team), mix(u.skin.data(), u.skin.size());
    mix(&u.x, sizeof u.x), mix(&u.z, sizeof u.z), mix(&u.move_speed, sizeof u.move_speed), mix(&u.facing, sizeof u.facing);
    for (const net::Point& p : u.path) mix(&p.x, sizeof p.x), mix(&p.z, sizeof p.z);
    mix(&u.hp, sizeof u.hp), mix(&u.dead, sizeof u.dead), mix(&u.target, sizeof u.target);
    mix(&u.attack_start, sizeof u.attack_start), mix(&u.next_attack, sizeof u.next_attack), mix(&u.lane_point, sizeof u.lane_point);
    mix(&u.champion_hits, sizeof u.champion_hits), mix(&u.respawn_tick, sizeof u.respawn_tick);
    mix(&u.level, sizeof u.level), mix(&u.xp, sizeof u.xp), mix(&u.gold, sizeof u.gold), mix(&u.par, sizeof u.par);
    for (const SpellSlot& s : u.spells) mix(&s.level, sizeof s.level), mix(&s.ready_tick, sizeof s.ready_tick);
    mix(u.items.data(), sizeof u.items), mix(u.item_stacks.data(), sizeof u.item_stacks);
    for (const Buff& b : u.buffs) mix(b.name.data(), b.name.size()), mix(&b.end_tick, sizeof b.end_tick), mix(&b.shield, sizeof b.shield);
    mix(&u.cast.slot, sizeof u.cast.slot), mix(&u.dash.active, sizeof u.dash.active);
    mix(&u.ai_state, sizeof u.ai_state), mix(&u.auto_attack, sizeof u.auto_attack), mix(&u.acquisition_mode, sizeof u.acquisition_mode);
  }
  for (const Missile& m : missiles_) mix(&m.target, sizeof m.target), mix(&m.x, sizeof m.x), mix(&m.z, sizeof m.z), mix(&m.damage, sizeof m.damage);
  mix(&start_tick_, sizeof start_tick_), mix(&wave_id_, sizeof wave_id_), mix(&next_wave_, sizeof next_wave_),mix(&winner_, sizeof winner_);
  return h;
}

void Match::path_to(Unit& u, float x, float z, MatchEvents& ev) {
  // a path over the navigation grid (a straight line only without one)
  u.path.clear();
  if (nav_) {
    for (const auto& [px, pz] : nav_->find_path(u.x, u.z, x, z, u.pathfinding_radius)) u.path.push_back({px, pz});
  } else {
    u.path = {net::Point{x, z}};
  }
  ev.path_changed.push_back(u.id);
}

float Match::reach(const Unit& u, const Unit& t) const {
  // edge-to-edge range: attack range + both gameplay radii (documented)
  return u.stats.attack_range + u.stats.gameplay_radius + t.stats.gameplay_radius;
}

float Match::attack_damage(const Unit& source, const Unit& target, float extra) const {
  const double t = std::max(0.0, game_seconds());
  float ad = source.stats.ad + extra, armor = target.stats.armor;
  if (source.kind == UnitType::Turret) {
    // a turret's attack damage grows with the game's minutes (documented): outer 182 + 12 a minute from 0:30 (350 at
    // 13:30); inner, inhibitor and nexus turrets + 16 a minute from 3:00 (15 times, until 17:00)
    const bool outer = source.position >= 3;
    const double first = outer ? 30 : 180;
    const int steps = t < first ? 0 : std::min(outer ? 14 : 15, 1 + static_cast<int>((t - first) / 60));
    ad += static_cast<float>(steps) * (outer ? 12.f : 16.f);
    if (target.kind == UnitType::Minion) {
      // turret shots deal a fixed share of a lane minion's maximum health, before its armor (documented): melee 45%,
      // caster 70%, siege 14%, super 5%
      const float share = target.minion == MinionKind::Melee    ? 0.45f
                          : target.minion == MinionKind::Caster ? 0.70f
                          : target.minion == MinionKind::Siege  ? 0.14f
                          : target.minion == MinionKind::Super  ? 0.05f
                                                                : 0.f;
      if (share > 0) ad = share * target.stats.max_hp;
    } else if (target.kind == UnitType::Champion) {
      // Warming Up (documented): + 40% for each hit on a champion in a row, up to + 120%
      ad *= 1.f + 0.4f * static_cast<float>(std::min(3, source.champion_hits));
    }
    if (armor > 0) armor *= 0.7f;  // turrets ignore 30% of armor (documented: Ohmwrecker, the turrets' item)
  }
  if (target.kind == UnitType::Turret && target.position >= 3 && t < 840) {
    // an outer turret's plating, until it falls at 14:00 (documented): + 40 armor for each of its 1000-health plates
    // already broken; once the plating is gone the turret has 40 armor (its record's 15 are the plated turret's)
    armor += 40.f * std::clamp(std::floor((target.max_hp - target.hp) / 1000.f), 0.f, 4.f);
  } else if (target.kind == UnitType::Turret && target.position >= 3) {
    armor += 25.f;
  }
  // physical damage taken = damage x 100 / (100 + armor) (documented)
  float dmg = armor >= 0 ? ad * 100.f / (100.f + armor) : ad * (2.f - 100.f / (100.f - armor));
  // the mode's ratio between the attacker's and the target's class (map11.bin GameModeConstants: dr_UnitToHero ...)
  dmg *= constant((std::string("dr_") + damage_class(source) + "To" + damage_class(target)).c_str(), 1.f);
  if (target.kind == UnitType::Turret) {
    // Fortification (documented): the top and middle outer turrets take half damage for the first five minutes
    if (target.position >= 3 && (target.lane == 1 || target.lane == 2) && t < 300) dmg *= 0.5f;
    // Reinforced Armor (documented): 80% less damage while no enemy minion is near the turret
    bool minions = false;
    for (const Unit& m : units)
      if (!m.dead && m.kind == UnitType::Minion && m.team != target.team && distance(m, target) <= kReinforcedArmorRange) minions = true;
    if (!minions) dmg *= 0.2f;
  }
  return dmg;
}

// ---------------------------------------------------------------- champions: levels, experience, gold

/** The highest level (documented: 18; the mode's curve goes on for other modes). */
constexpr int kMaxLevel = 18;

void Match::level_stats(Unit& u) {
  if (!u.record) return;
  const CharacterRecordData& r = *u.record;
  // stat = base + growth x (the levels' factors summed): Global.wad's mPerLevelStatsFactor
  const float g = map_ ? map_->level_growth(u.level) : 0.f;
  const float old_max = u.max_hp, old_par = u.max_par;
  u.base.max_hp = r.base_hp + r.hp_per_level * g;
  u.base.ad = r.base_damage + r.damage_per_level * g;
  u.base.armor = r.base_armor + r.armor_per_level * g;
  u.base.spell_block = r.base_spell_block + r.spell_block_per_level * g;
  // attack speed: the base plus attackSpeedPerLevel percent of the ratio for each level's factor (documented)
  u.base.attack_speed = r.attack_speed + r.attack_speed_ratio * r.attack_speed_per_level * 0.01f * g;
  // the resource: mana and energy from arBase; one without a base holds arIncrements (Tryndamere's fury: 100) [dedus];
  // refresh_stats adds the items' mana to it and fills what the maximum grew by
  u.base_max_par = r.ar_base > 0 ? r.ar_base + r.ar_per_level * g : r.ar_type != 0 ? r.ar_increments : 0.f;
  refresh_stats(u, nullptr);
  // a level gained adds what the maximum grew by to what the champion has
  u.hp += std::max(0.f, u.max_hp - old_max);
  (void)old_par;  // refresh_stats filled what the resource's maximum grew by
}

float Match::xp_fraction(const Unit& u) const {
  if (!map_ || map_->xp_required.empty() || u.level >= kMaxLevel) return 1.f;
  const auto& req = map_->xp_required;
  const float from = u.level >= 2 ? req[std::min(static_cast<size_t>(u.level - 2), req.size() - 1)] : 0.f;
  const float to = req[std::min(static_cast<size_t>(u.level - 1), req.size() - 1)];
  return to > from ? std::clamp((u.xp - from) / (to - from), 0.f, 1.f) : 1.f;
}

void Match::gain_xp(Unit& u, float amount, MatchEvents& ev) {
  if (amount <= 0 || !map_) return;
  u.xp += amount;
  const auto& req = map_->xp_required;
  while (u.level < kMaxLevel && static_cast<size_t>(u.level - 1) < req.size() && u.xp >= req[static_cast<size_t>(u.level - 1)]) {
    ++u.level;
    ++u.skill_points;  // a point to put into a spell with every level
    ev.spells_changed.push_back(u.id);
    level_stats(u);
    ev.damage.push_back({u.id, 0.f, u.hp, u.max_hp});
  }
  ev.stats_changed.push_back(u.id);
}

void Match::reward(const Unit& dead, const Unit& killer, MatchEvents& ev) {
  if (dead.kind != UnitType::Minion || !map_) return;
  // experience: to the enemy champions within the minion's ExperienceRadius (the level script's spawn info), each its
  // share by how many they are (ExperienceModData mPlayerMinionSplitXp); ExpGiven from its MinionInfoTable
  std::vector<Unit*> near;
  for (Unit& c : units)
    if (c.kind == UnitType::Champion && !c.dead && c.team != dead.team && distance(c, dead) <= dead.exp_radius) near.push_back(&c);
  if (!near.empty() && !map_->xp_split.empty()) {
    const float share = map_->xp_split[std::min(near.size(), map_->xp_split.size()) - 1];
    for (Unit* c : near) gain_xp(*c, dead.exp_given * share, ev);
  }
  // gold: GoldGiven to the champion that landed the last hit (documented)
  if (killer.kind == UnitType::Champion)
    if (Unit* k = unit(killer.id)) k->gold += dead.gold_given, ++k->minions_killed, ev.stats_changed.push_back(k->id);
}

// ---------------------------------------------------------------- the spawn platform heals its team's champions

void Match::regenerate(MatchEvents& ev) {
  if (!map_) return;
  // every sp_RegenTickInterval, sp_HealthRegenPercent of maximum health within sp_RegenRadius of the team's spawn
  // point (GameModeConstants) [de măsurat: the centre of the radius]
  const float radius = constant("sp_RegenRadius", 0), share = constant("sp_HealthRegenPercent", 0);
  const int64_t every = ticks(constant("sp_RegenTickInterval", 0.25f));
  if (!(radius <= 0 || share <= 0 || clock.tick % every != 0))
    for (Unit& u : units) {
      if (u.kind != UnitType::Champion || u.dead) continue;
      const auto& sp = map_->spawn_point[u.team];
      if (std::hypot(u.x - sp[0], u.z - sp[1]) > radius) continue;
      // Refill refillable / corrupting potions in fountain
      for (size_t k = 0; k < u.items.size(); ++k) {
        if (u.items[k] == 2031 && u.item_stacks[k] < 2) {
          u.item_stacks[k] = 2;
          ev.items_changed.push_back(u.id);
        } else if (u.items[k] == 2033 && u.item_stacks[k] < 3) {
          u.item_stacks[k] = 3;
          ev.items_changed.push_back(u.id);
        }
      }
      if (u.hp < u.max_hp) {
        u.hp = std::min(u.max_hp, u.hp + share * u.max_hp);
        ev.damage.push_back({u.id, 0.f, u.hp, u.max_hp});
      }
      if (u.par < u.max_par) {
        u.par = std::min(u.max_par, u.par + constant("sp_ManaRegenPercent", 0) * u.max_par);
        ev.stats_changed.push_back(u.id);
      }
    }
  // ---- a champion's own regeneration: the record's health and resource per second (baseStaticHPRegen, arBaseStaticRegen
  // and their growth), handed out every half second (documented)
  const int64_t half = ticks(0.5);
  if (clock.tick % half == 0)
    for (Unit& u : units) {
      if (u.kind != UnitType::Champion || u.dead || !u.record) continue;
      const float g = map_->level_growth(u.level);
      const float seconds = static_cast<float>(half) * static_cast<float>(kTickSeconds);
      if (u.hp < u.max_hp) {
        u.hp = std::min(u.max_hp, u.hp + (u.record->hp_regen + u.record->hp_regen_per_level * g) * seconds);
        ev.damage.push_back({u.id, 0.f, u.hp, u.max_hp});
      }
      if (u.par < u.max_par) {
        u.par = std::min(u.max_par, u.par + (u.record->ar_regen + u.record->ar_regen_per_level * g) * seconds);
        ev.stats_changed.push_back(u.id);
      }
      // Potions
      if (find_buff(u, "HealthPotion") && u.hp < u.max_hp) {
        u.hp = std::min(u.max_hp, u.hp + 8.f * seconds);
        ev.damage.push_back({u.id, 0.f, u.hp, u.max_hp});
      }
      if (find_buff(u, "RefillablePotion") && u.hp < u.max_hp) {
        u.hp = std::min(u.max_hp, u.hp + (100.f / 12.f) * seconds);
        ev.damage.push_back({u.id, 0.f, u.hp, u.max_hp});
      }
      if (find_buff(u, "CorruptingPotion")) {
        if (u.hp < u.max_hp) {
          u.hp = std::min(u.max_hp, u.hp + (100.f / 12.f) * seconds);
          ev.damage.push_back({u.id, 0.f, u.hp, u.max_hp});
        }
        if (u.par < u.max_par) {
          u.par = std::min(u.max_par, u.par + (75.f / 12.f) * seconds);
          ev.stats_changed.push_back(u.id);
        }
      }
      // Immolate passive (Sunfire Aegis 3068 / Bami's Cinder 3751 / Hollow Radiance 3066)
      bool has_immolate = false;
      for (int it_id : u.items) {
        if (it_id == 3068 || it_id == 3751 || it_id == 3066 || it_id == 6660) { has_immolate = true; break; }
      }
      if (has_immolate && u.last_fight_tick >= 0 && clock.tick - u.last_fight_tick <= ticks(5.0)) {
        const float radius = 325.f;
        const float immolate_dmg = (15.f + 0.0175f * std::max(0.f, u.stats.max_hp - u.base.max_hp)) * seconds;
        for (Unit& target : units) {
          if (target.dead || target.team == u.team || structure(target) || &target == &u) continue;
          if (distance(u, target) <= radius + target.stats.gameplay_radius) {
            spell_damage(u, target, immolate_dmg, DamageType::Magic, "ItemSunfireImmolate", ev);
          }
        }
      }

      // Warmog's Heart (Warmog's Armor 3083): 2.5% max HP per 0.5s if out of combat and >= 1100 bonus HP
      for (int it_id : u.items) {
        if (it_id == 3083) {
          const float bonus_hp = std::max(0.f, u.stats.max_hp - u.base.max_hp);
          if (bonus_hp >= 1100.f && (u.last_fight_tick < 0 || clock.tick - u.last_fight_tick > ticks(6.0))) {
            if (u.hp < u.max_hp) {
              u.hp = std::min(u.max_hp, u.hp + 0.025f * u.max_hp);
              ev.damage.push_back({u.id, 0.f, u.hp, u.max_hp, u.total_shield()});
            }
          }
          break;
        }
      }

      // Magebane (Kaenic Rookern 6701): 18% max HP magic shield if out of combat for 12s
      for (int it_id : u.items) {
        if (it_id == 6701) {
          if (u.last_fight_tick < 0 || clock.tick - u.last_fight_tick > ticks(12.0)) {
            if (!find_buff(u, "KaenicMagebane")) {
              Buff b;
              b.name = "KaenicMagebane";
              b.source = u.id;
              b.shield = 0.18f * u.stats.max_hp;
              u.buffs.push_back(b);
              ev.buffs.push_back({u.id, b.name, -1.f, true});
              ev.damage.push_back({u.id, 0.f, u.hp, u.max_hp, u.total_shield()});
            }
          }
          break;
        }
      }

      // Liandry's Torment periodic burn (2% max HP magic damage per second)
      if (Buff* lb = find_buff(u, "LiandryTorment")) {
        if (Unit* src = unit(lb->source)) {
          const float liandry_dmg = 0.02f * u.stats.max_hp * seconds;
          spell_damage(*src, u, liandry_dmg, DamageType::Magic, "ItemLiandryTorment", ev);
        }
      }

      // Malignance Hatefog periodic burn (60 + 0.05 AP magic damage per second)
      if (Buff* mb = find_buff(u, "MalignanceHatefog")) {
        if (Unit* src = unit(mb->source)) {
          const float hatefog_dmg = (60.f + 0.05f * src->stats.ap) * seconds;
          spell_damage(*src, u, hatefog_dmg, DamageType::Magic, "ItemMalignanceHatefog", ev);
        }
      }
    }
  // ---- ambient gold: ai_AmbientGoldAmount every ai_AmbientGoldInterval seconds from mission_AmbientGoldStartTime
  const double t = game_seconds();
  const float interval = constant("ai_AmbientGoldInterval", 0), amount = constant("ai_AmbientGoldAmount", 0);
  if (interval > 0 && amount > 0 && t >= constant("mission_AmbientGoldStartTime", 0) && (clock.tick - start_tick_) % ticks(interval) == 0)
    for (Unit& u : units)
      if (u.kind == UnitType::Champion) u.gold += amount, ev.stats_changed.push_back(u.id);
}

bool Match::attackable(const Unit& by, const Unit& t) const {
  if (t.dead || !t.record || t.team == by.team || &t == &by) return false;
  if (has_flag(t, &Buff::untargetable)) return false;
  // the level script's say (SetInvulnerable, SetTargetable, SetNotTargetableToTeam)
  if (t.invulnerable || !t.targetable || (t.hidden_from & (1u << by.team))) return false;
  return true;
}

bool Match::attacking(const Unit& a, const Unit& b) const {
  return a.target == b.id && a.last_attack_tick >= 0 && clock.tick - a.last_attack_tick <= ticks(kAggroMemorySeconds);
}

void Match::start_attack(Unit& u, Unit& t, MatchEvents& ev) {
  const CharacterRecordData& r = *u.record;
  if (r.attacks.empty()) return;
  // critical strike check at start of attack so animation and hit are 100% matched
  bool is_crit = (u.stats.crit > 0 && random.unit() < static_cast<double>(u.stats.crit));
  if (u.kind == UnitType::Champion && t.kind == UnitType::Champion) {
    for (int it_id : u.items) {
      if (it_id == 6610 && !find_buff(u, "SunderedSkyCD_" + std::to_string(t.id))) {
        is_crit = true;
        break;
      }
    }
  }
  u.attack_is_crit = is_crit;

  // which attack: basicAttack and extraAttacks by mAttackProbability, drawn from the match's random stream
  float total_p = 0;
  for (const AttackSlot& at : r.attacks) total_p += at.probability;
  double pick = random.unit() * static_cast<double>(total_p);
  u.attack_slot = 0;
  for (size_t i = 0; i < r.attacks.size(); ++i) {
    pick -= r.attacks[i].probability;
    if (pick < 0) {
      u.attack_slot = static_cast<int>(i);
      break;
    }
  }
  const AttackSlot* slot_ptr = &r.attacks[static_cast<size_t>(u.attack_slot)];
  if (is_crit && !r.crits.empty()) {
    slot_ptr = &r.crits[0];
  }
  const AttackSlot& a = *slot_ptr;

  // attack timer = 1 / attack speed; no bonus attack speed yet, so total AS = base AS (documented)
  // the mode's attack delay limits (gcd_AttackMinDelay 0.4 s, gcd_AttackMaxDelay 5 s: attack speed 0.2 .. 2.5)
  const double attack_speed = std::clamp(static_cast<double>(u.stats.attack_speed), 1.0 / constant("gcd_AttackMaxDelay", 5.f),
                                         1.0 / constant("gcd_AttackMinDelay", 0.4f));
  const double attack_time = 1.0 / attack_speed;
  // windup percent: cast / total time when the slot gives them, else 0.3 + the offset (documented); with no bonus
  // attack speed the windup modifier changes nothing: windup = attack time x percent
  const AttackSlot& base = r.attacks[0];
  const AttackSlot& timing = a.has_times || a.has_offset ? a : base;
  const double percent = timing.has_times && timing.total_time > 0 ? timing.cast_time / timing.total_time
                                                                   : constant("gcd_AttackDelayCastPercent", 0.3f) + timing.offset;
  const double windup = attack_time * percent;
  u.attack_start = clock.tick;
  u.last_attack_tick = clock.tick;
  u.hit_tick = clock.tick + ticks(windup);
  u.next_attack = clock.tick + ticks(attack_time);
  if (!u.path.empty()) u.path.clear(), ev.path_changed.push_back(u.id);
  if (!structure(u)) u.facing = std::atan2(t.x - u.x, t.z - u.z);  // a unit turns to its target; a structure stands as built
  std::string anim_name = a.animation;
  if (u.kind == UnitType::Champion) {
    if (find_buff(u, "GarenQ")) {
      anim_name = "Spell1";
    } else if (find_buff(u, "AsheQ")) {
      anim_name = "Spell1";
    }
  }
  ev.attacks.push_back({u.id, t.id, a.name, anim_name, static_cast<float>(windup), static_cast<float>(attack_time), a.spell_cast_time, u.facing});
  // documented (LoL Wiki, "Minion aggression": the call for help): a champion attacking an enemy champion draws the
  // victim's minions near it at once
  if (u.kind == UnitType::Champion && t.kind == UnitType::Champion) ai_call_for_help(t, u);
}

void Match::hit(Unit& source, Unit& target, float damage, const std::string& spell, MatchEvents& ev) {
  if (target.dead) return;
  ev.hits.push_back({source.id, target.id, spell});
  if (source.kind == UnitType::Turret && target.kind == UnitType::Champion) ++source.champion_hits, source.last_champion_hit = clock.tick;

  // Plated Steelcaps (3047): -12% damage from basic attacks
  for (int it_id : target.items) {
    if (it_id == 3047) {
      damage *= 0.88f;
      break;
    }
  }

  // On-hit passives for champion basic attacks
  if (source.kind == UnitType::Champion) {
    // Consume Spellblade buff if present
    for (size_t i = 0; i < source.buffs.size(); ++i) {
      if (source.buffs[i].name == "Spellblade") {
        // Essence Reaver (3508): restores mana
        for (int it_id : source.items) {
          if (it_id == 3508 && source.par < source.max_par) {
            source.par = std::min(source.max_par, source.par + 0.40f * source.buffs[i].ad);
            ev.stats_changed.push_back(source.id);
            break;
          }
        }
        remove_buff(source, i, true, ev);
        break;
      }
    }

    // Blade of the Ruined King (3153): deals current HP damage
    for (int it_id : source.items) {
      if (it_id == 3153) {
        const float pct = source.stats.attack_range > 300.f ? 0.09f : 0.12f;
        float bork_dmg = target.hp * pct;
        if (target.kind == UnitType::Minion) bork_dmg = std::min(bork_dmg, 60.f);
        else bork_dmg = std::max(bork_dmg, 15.f);
        const float armor = target.stats.armor;
        const float mitigated = armor >= 0 ? bork_dmg * 100.f / (100.f + armor) : bork_dmg * (2.f - 100.f / (100.f - armor));
        damage += mitigated;
        break;
      }
    }

    // Nashor's Tooth (3115): 15 + 20% AP magic damage on-hit
    for (int it_id : source.items) {
      if (it_id == 3115) {
        const float raw_magic = 15.f + 0.20f * source.stats.ap;
        const float mr = target.stats.spell_block;
        const float mitigated = mr >= 0 ? raw_magic * 100.f / (100.f + mr) : raw_magic * (2.f - 100.f / (100.f - mr));
        damage += mitigated;
        break;
      }
    }

    // Wit's End (3091): 15-80 magic damage on-hit based on level
    for (int it_id : source.items) {
      if (it_id == 3091) {
        const float raw_magic = 15.f + (65.f / 17.f) * static_cast<float>(std::clamp(source.level - 1, 0, 17));
        const float mr = target.stats.spell_block;
        const float mitigated = mr >= 0 ? raw_magic * 100.f / (100.f + mr) : raw_magic * (2.f - 100.f / (100.f - mr));
        damage += mitigated;
        break;
      }
    }

    // Guinsoo's Rageblade (3124): Wrath on-hit magic damage (30 + 2 * (crit * 100))
    for (int it_id : source.items) {
      if (it_id == 3124) {
        const float raw_magic = 30.f + source.stats.crit * 200.f;
        const float mr = target.stats.spell_block;
        const float mitigated = mr >= 0 ? raw_magic * 100.f / (100.f + mr) : raw_magic * (2.f - 100.f / (100.f - mr));
        damage += mitigated;
        break;
      }
    }

    // Kraken Slayer (6672): Bring It Down (every 3rd basic attack deals 140-310 + 65% AD)
    for (int it_id : source.items) {
      if (it_id == 6672) {
        Buff* b = find_buff(source, "KrakenSlayer");
        int stacks = b ? b->stacks : 0;
        stacks++;
        if (stacks >= 3) {
          if (b) b->stacks = 0;
          const float raw_phys = 140.f + 10.f * static_cast<float>(std::clamp(source.level - 1, 0, 17)) + 0.65f * source.stats.ad;
          const float armor = target.stats.armor;
          const float mitigated = armor >= 0 ? raw_phys * 100.f / (100.f + armor) : raw_phys * (2.f - 100.f / (100.f - armor));
          damage += mitigated;
        } else {
          if (!b) {
            Buff nb;
            nb.name = "KrakenSlayer";
            nb.source = source.id;
            nb.end_tick = clock.tick + ticks(3.0);
            nb.stacks = stacks;
            source.buffs.push_back(nb);
          } else {
            b->stacks = stacks;
            b->end_tick = clock.tick + ticks(3.0);
          }
        }
        break;
      }
    }

    // Sundered Sky (6610): Lightshield Strike (first attack against each champion crits and heals)
    if (target.kind == UnitType::Champion) {
      for (int it_id : source.items) {
        if (it_id == 6610) {
          std::string cd_buff_name = "SunderedSkyCD_" + std::to_string(target.id);
          if (!find_buff(source, cd_buff_name)) {
            Buff cd;
            cd.name = cd_buff_name;
            cd.source = source.id;
            cd.end_tick = clock.tick + ticks(6.0);
            source.buffs.push_back(cd);
            damage += 0.75f * source.stats.ad;
            const float heal = 1.40f * source.base.ad + 0.06f * (source.max_hp - source.hp);
            source.hp = std::min(source.max_hp, source.hp + heal);
            ev.damage.push_back({source.id, 0.f, source.hp, source.max_hp, source.total_shield()});
          }
          break;
        }
      }
    }

    // Voltaic Cyclosword (6696): Energized attack deals 100 bonus physical damage + 99% slow for 0.75s
    if (target.kind == UnitType::Champion) {
      for (int it_id : source.items) {
        if (it_id == 6696) {
          std::string cd_buff_name = "VoltaicCD";
          if (!find_buff(source, cd_buff_name)) {
            Buff cd;
            cd.name = cd_buff_name;
            cd.source = source.id;
            cd.end_tick = clock.tick + ticks(6.0);
            source.buffs.push_back(cd);
            damage += 100.f;
            Buff slow;
            slow.name = "VoltaicSlow";
            slow.source = source.id;
            slow.end_tick = clock.tick + ticks(0.75);
            slow.move_speed_pct = -0.99f;
            target.buffs.push_back(slow);
            ev.buffs.push_back({target.id, slow.name, 0.75f, true});
            ev.effects.push_back({target.id, "Voltaic_tar", "", 0.f, false, source.id});
          }
          break;
        }
      }
    }

    // Opportunity (6694): Preparation (+10 Lethality flat armor pen for 3s after damaging a champion)
    if (target.kind == UnitType::Champion) {
      for (int it_id : source.items) {
        if (it_id == 6694) {
          if (source.last_fight_tick < 0 || clock.tick - source.last_fight_tick >= ticks(8.0)) {
            Buff* b = find_buff(source, "OpportunityPrep");
            if (!b) {
              Buff nb;
              nb.name = "OpportunityPrep";
              nb.source = source.id;
              nb.end_tick = clock.tick + ticks(3.0);
              source.buffs.push_back(nb);
              ev.buffs.push_back({source.id, nb.name, 3.0f, true});
            } else {
              b->end_tick = clock.tick + ticks(3.0);
            }
          }
          break;
        }
      }
    }

    // Heartsteel (3084): Colossal Consumption against enemy champions
    if (target.kind == UnitType::Champion) {
      for (int it_id : source.items) {
        if (it_id == 3084) {
          std::string cd_buff_name = "HeartsteelCD_" + std::to_string(target.id);
          if (!find_buff(source, cd_buff_name)) {
            Buff cd;
            cd.name = cd_buff_name;
            cd.source = source.id;
            cd.end_tick = clock.tick + ticks(30.0);
            source.buffs.push_back(cd);
            const float bonus_phys = 100.f + 0.10f * source.stats.max_hp;
            const float armor = target.stats.armor;
            const float mitigated = armor >= 0 ? bonus_phys * 100.f / (100.f + armor) : bonus_phys * (2.f - 100.f / (100.f - armor));
            damage += mitigated;
            source.base.max_hp += bonus_phys * 0.12f;
            refresh_stats(source, &ev);
          }
          break;
        }
      }
    }

    // Terminus (3302): Juxtaposition (alternating Light and Dark attacks)
    for (int it_id : source.items) {
      if (it_id == 3302) {
        Buff* b = find_buff(source, "TerminusStance");
        bool is_light = b ? (b->stacks == 0) : true;
        if (is_light) {
          Buff* armor_b = find_buff(source, "TerminusLight");
          float current = armor_b ? armor_b->armor : 0.f;
          float add = 6.f + static_cast<float>(source.level / 6);
          if (!armor_b) {
            Buff nb;
            nb.name = "TerminusLight";
            nb.source = source.id;
            nb.end_tick = clock.tick + ticks(5.0);
            nb.armor = add;
            nb.spell_block = add;
            source.buffs.push_back(nb);
          } else {
            armor_b->armor = std::min(add * 3.f, current + add);
            armor_b->spell_block = armor_b->armor;
            armor_b->end_tick = clock.tick + ticks(5.0);
          }
        } else {
          Buff* pen_b = find_buff(source, "TerminusDark");
          float current = pen_b ? pen_b->armor_pct : 0.f;
          float add = 0.06f;
          if (!pen_b) {
            Buff nb;
            nb.name = "TerminusDark";
            nb.source = source.id;
            nb.end_tick = clock.tick + ticks(5.0);
            nb.armor_pct = add;
            source.buffs.push_back(nb);
          } else {
            pen_b->armor_pct = std::min(0.30f, current + add);
            pen_b->end_tick = clock.tick + ticks(5.0);
          }
        }
        if (!b) {
          Buff nb;
          nb.name = "TerminusStance";
          nb.source = source.id;
          nb.stacks = 1;
          nb.end_tick = clock.tick + ticks(5.0);
          source.buffs.push_back(nb);
        } else {
          b->stacks = is_light ? 1 : 0;
          b->end_tick = clock.tick + ticks(5.0);
        }
        refresh_stats(source, &ev);
        break;
      }
    }
  }

  // Thornmail (3075) / Bramble Vest (3076) reflect magic damage to attacker
  if (target.kind == UnitType::Champion && !source.dead) {
    for (int it_id : target.items) {
      if (it_id == 3075 || it_id == 3076) {
        const float bonus_armor = std::max(0.f, target.stats.armor - target.base.armor);
        const float reflect_raw = (it_id == 3075) ? (10.f + 0.25f * bonus_armor) : (6.f + 0.10f * bonus_armor);
        const float mr = source.stats.spell_block;
        const float reflect_dmg = mr >= 0 ? reflect_raw * 100.f / (100.f + mr) : reflect_raw * (2.f - 100.f / (100.f - mr));
        apply_damage(target, source, reflect_dmg, ev);
        break;
      }
    }
  }

  // Statikk Shiv (3087): Electroshock chain lightning
  for (int it_id : source.items) {
    if (it_id == 3087) {
      Buff* b = find_buff(source, "StatikkEnergized");
      int stacks = b ? b->stacks + 35 : 35;
      if (stacks >= 100) {
        if (b) b->stacks = 0;
        int chained = 0;
        for (Unit& o : units) {
          if (o.dead || o.team == source.team || structure(o)) continue;
          if (&o == &target || distance(target, o) <= 500.f) {
            const float shiv_raw = 90.f;
            const float mr = o.stats.spell_block;
            const float shiv_mit = mr >= 0 ? shiv_raw * 100.f / (100.f + mr) : shiv_raw * (2.f - 100.f / (100.f - mr));
            apply_damage(source, o, shiv_mit, ev);
            ev.hits.push_back({source.id, o.id, "ItemStatikkShiv"});
            if (++chained >= 6) break;
          }
        }
      } else {
        if (!b) {
          Buff nb;
          nb.name = "StatikkEnergized";
          nb.source = source.id;
          nb.stacks = stacks;
          source.buffs.push_back(nb);
        } else {
          b->stacks = stacks;
        }
      }
      break;
    }
  }

  // Rapid Firecannon (3094): Sharpshooter (60 bonus magic damage on energized attack)
  for (int it_id : source.items) {
    if (it_id == 3094) {
      Buff* b = find_buff(source, "RFCEnergized");
      int stacks = b ? b->stacks + 35 : 35;
      if (stacks >= 100) {
        if (b) b->stacks = 0;
        const float rfc_raw = 60.f;
        const float mr = target.stats.spell_block;
        const float rfc_mit = mr >= 0 ? rfc_raw * 100.f / (100.f + mr) : rfc_raw * (2.f - 100.f / (100.f - mr));
        damage += rfc_mit;
      } else {
        if (!b) {
          Buff nb;
          nb.name = "RFCEnergized";
          nb.source = source.id;
          nb.stacks = stacks;
          source.buffs.push_back(nb);
        } else {
          b->stacks = stacks;
        }
      }
      break;
    }
  }

  // Dead Man's Plate (3742): Shipwrecker
  for (int it_id : source.items) {
    if (it_id == 3742) {
      Buff* b = find_buff(source, "DeadMansDread");
      if (b && b->stacks > 0) {
        const float bonus_magic = 40.f + 1.0f * source.base.ad;
        const float mr = target.stats.spell_block;
        const float dmp_mit = mr >= 0 ? bonus_magic * 100.f / (100.f + mr) : bonus_magic * (2.f - 100.f / (100.f - mr));
        damage += dmp_mit;
        if (!find_buff(target, "DeadMansSlow")) {
          Buff sb;
          sb.name = "DeadMansSlow";
          sb.source = source.id;
          sb.end_tick = clock.tick + ticks(1.0);
          sb.move_speed_pct = -0.50f;
          target.buffs.push_back(sb);
          ev.buffs.push_back({target.id, sb.name, 1.0f, true});
        }
        b->stacks = 0;
        b->move_speed = 0.f;
        refresh_stats(source, &ev);
      }
      break;
    }
  }

  // Eclipse (6695): Ever Rising Moon (2 separate hits within 1.8s)
  if (target.kind == UnitType::Champion) {
    for (int it_id : source.items) {
      if (it_id == 6695) {
        std::string cd_name = "EclipseCD_" + std::to_string(target.id);
        if (!find_buff(source, cd_name)) {
          Buff* hit_b = find_buff(source, "EclipseHit_" + std::to_string(target.id));
          if (!hit_b) {
            Buff nb;
            nb.name = "EclipseHit_" + std::to_string(target.id);
            nb.source = source.id;
            nb.end_tick = clock.tick + ticks(1.8);
            source.buffs.push_back(nb);
          } else {
            remove_buff(source, static_cast<size_t>(hit_b - source.buffs.data()), true, ev);
            Buff cd;
            cd.name = cd_name;
            cd.source = source.id;
            cd.end_tick = clock.tick + ticks(6.0);
            source.buffs.push_back(cd);

            const bool melee = source.stats.attack_range <= 300.f;
            const float pct = melee ? 0.08f : 0.04f;
            const float bonus_phys = pct * target.stats.max_hp;
            const float armor = target.stats.armor;
            const float mit = armor >= 0 ? bonus_phys * 100.f / (100.f + armor) : bonus_phys * (2.f - 100.f / (100.f - armor));
            damage += mit;

            const float bonus_ad = std::max(0.f, source.stats.ad - source.base.ad);
            const float shield_val = melee ? (160.f + 0.40f * bonus_ad) : (80.f + 0.20f * bonus_ad);
            Buff sh_b;
            sh_b.name = "EclipseShield";
            sh_b.source = source.id;
            sh_b.end_tick = clock.tick + ticks(2.0);
            sh_b.shield = shield_val;
            source.buffs.push_back(sh_b);
            ev.buffs.push_back({source.id, sh_b.name, 2.0f, true});
          }
        }
        break;
      }
    }
  }

  // Lord Dominik's Regards (3036): Giant Slayer
  if (target.kind == UnitType::Champion && target.stats.max_hp > source.stats.max_hp) {
    for (int it_id : source.items) {
      if (it_id == 3036) {
        const float diff = std::clamp(target.stats.max_hp - source.stats.max_hp, 0.f, 2500.f);
        damage *= (1.f + 0.22f * (diff / 2500.f));
        break;
      }
    }
  }

  const float actual_dmg = apply_damage(source, target, damage, ev);

  // Life Steal: heals for a portion of the damage dealt by basic attacks
  if (source.stats.life_steal > 0 && actual_dmg > 0 && source.hp < source.max_hp && !source.dead) {
    const float heal = actual_dmg * source.stats.life_steal;
    source.hp = std::min(source.max_hp, source.hp + heal);
    ev.damage.push_back({source.id, 0.f, source.hp, source.max_hp});
  }
}

float Match::apply_damage(Unit& source, Unit& target, float damage, MatchEvents& ev) {
  if (target.dead) return 0;
  if (target.invulnerable || has_flag(target, &Buff::invulnerable)) return 0;

  // what the target's buffs take off or add (Garen's Courage: 30% less), then its shields, oldest first
  float taken = 0;
  for (const Buff& b : target.buffs) taken += b.damage_taken_pct;
  damage *= std::max(0.f, 1.f + taken);
  for (Buff& b : target.buffs) {
    if (b.shield <= 0 || damage <= 0) continue;
    const float absorbed = std::min(b.shield, damage);
    b.shield -= absorbed, damage -= absorbed;
  }
  if (source.kind != UnitType::Minion) target.last_hurt_tick = clock.tick;
  source.last_fight_tick = target.last_fight_tick = clock.tick;


  // Seraph's Embrace (3040) Lifeline passive:
  if (target.kind == UnitType::Champion && target.hp - damage < target.max_hp * 0.3f && target.hp > 0) {
    for (size_t k = 0; k < target.items.size(); ++k) {
      if (target.items[k] == 3040 && clock.tick >= target.item_cooldowns[k]) {
        target.item_cooldowns[k] = clock.tick + ticks(90.0);
        const float shield_val = 250.f + 0.20f * target.par;
        Buff s_buff;
        s_buff.name = "SeraphLifeline";
        s_buff.source = target.id;
        s_buff.end_tick = clock.tick + ticks(3.0);
        s_buff.shield = shield_val;
        target.buffs.push_back(s_buff);
        ev.buffs.push_back({target.id, s_buff.name, 3.0f, true});
        if (damage > 0) {
          const float absorbed = std::min(target.buffs.back().shield, damage);
          target.buffs.back().shield -= absorbed;
          damage -= absorbed;
        }
        break;
      }
    }
  }

  // Sterak's Gage (3053) Lifeline passive:
  if (target.kind == UnitType::Champion && target.hp - damage < target.max_hp * 0.3f && target.hp > 0) {
    for (size_t k = 0; k < target.items.size(); ++k) {
      if (target.items[k] == 3053 && clock.tick >= target.item_cooldowns[k]) {
        target.item_cooldowns[k] = clock.tick + ticks(60.0);
        const float bonus_hp = std::max(0.f, target.stats.max_hp - target.base.max_hp);
        const float shield_val = 0.80f * bonus_hp;
        Buff s_buff;
        s_buff.name = "SterakLifeline";
        s_buff.source = target.id;
        s_buff.end_tick = clock.tick + ticks(4.5);
        s_buff.shield = shield_val;
        s_buff.tenacity = 0.20f;
        target.buffs.push_back(s_buff);
        ev.buffs.push_back({target.id, s_buff.name, 4.5f, true});
        ev.effects.push_back({target.id, "Steraks_Buff", "", 4.5f, false, target.id});
        if (damage > 0) {
          const float absorbed = std::min(target.buffs.back().shield, damage);
          target.buffs.back().shield -= absorbed;
          damage -= absorbed;
        }
        break;
      }
    }
  }

  // a buff may keep its unit alive (min_hp)
  float floor_hp = 0;
  for (const Buff& b : target.buffs) floor_hp = std::max(floor_hp, b.min_hp);
  target.hp = std::max(std::min(floor_hp, target.hp), target.hp - damage);

  // Omnivamp healing:
  if (source.stats.omnivamp > 0 && damage > 0 && source.hp < source.max_hp && !source.dead) {
    const float heal = damage * source.stats.omnivamp * (target.kind == UnitType::Minion ? 0.33f : 1.0f);
    source.hp = std::min(source.max_hp, source.hp + heal);
    ev.damage.push_back({source.id, 0.f, source.hp, source.max_hp, source.total_shield()});
  }

  ev.damage.push_back({target.id, damage, target.hp, target.max_hp, target.total_shield()});
  if (target.hp <= 0) {
    // Guardian Angel (3026) Rebirth passive:
    if (target.kind == UnitType::Champion) {
      for (size_t k = 0; k < target.items.size(); ++k) {
        if (target.items[k] == 3026 && clock.tick >= target.item_cooldowns[k]) {
          target.item_cooldowns[k] = clock.tick + ticks(300.0);
          target.hp = 1.f;
          Buff ga_buff;
          ga_buff.name = "GuardianAngelStasis";
          ga_buff.source = target.id;
          ga_buff.end_tick = clock.tick + ticks(4.0);
          ga_buff.untargetable = true;
          ga_buff.invulnerable = true;
          ga_buff.stun = true;
          ga_buff.root = true;
          ga_buff.disarm = true;
          ga_buff.silence = true;
          target.buffs.push_back(ga_buff);
          ev.buffs.push_back({target.id, ga_buff.name, 4.0f, true});
          target.target = 0, target.attack_start = -1, target.path.clear();
          ev.path_changed.push_back(target.id);
          return damage;
        }
      }
    }

    target.dead = true;
    target.target = 0, target.attack_start = -1, target.path.clear();
    if (target.kind == UnitType::Minion) target.remove_tick = clock.tick + ticks(kMinionCorpseSeconds);
    reward(target, source, ev);
    if (source.kind == UnitType::Champion) champion_hook(source.id, "OnKill", target.id, target.kind == UnitType::Champion, 0.f);
    // a champion comes back after its level's death time (the mode's DeathTimes)
    if (target.kind == UnitType::Champion && map_) {
      target.respawn_tick = clock.tick + ticks(map_->death_seconds(target.level, std::max(0.0, game_seconds())));
      ++target.deaths;
      if (source.kind == UnitType::Champion) {
        ++source.kills;
        ev.stats_changed.push_back(source.id);

        // Opportunity (6694): Extraction (+150 decaying MS for 1.5s on champion takedown)
        for (int it_id : source.items) {
          if (it_id == 6694) {
            Buff b;
            b.name = "OpportunityExtraction";
            b.source = source.id;
            b.end_tick = clock.tick + ticks(1.5);
            b.move_speed = 150.f;
            source.buffs.push_back(b);
            ev.buffs.push_back({source.id, b.name, 1.5f, true});
            refresh_stats(source, &ev);
            break;
          }
        }

        // Hubris (6699): Eminence (+15 + 2 per kill bonus AD for 60s)
        for (int it_id : source.items) {
          if (it_id == 6699) {
            Buff* b = find_buff(source, "HubrisEminence");
            if (!b) {
              Buff nb;
              nb.name = "HubrisEminence";
              nb.source = source.id;
              nb.end_tick = clock.tick + ticks(60.0);
              nb.ad = 15.f + 2.f * static_cast<float>(source.kills);
              source.buffs.push_back(nb);
              ev.buffs.push_back({source.id, nb.name, 60.0f, true});
            } else {
              b->end_tick = clock.tick + ticks(60.0);
              b->ad = 15.f + 2.f * static_cast<float>(source.kills);
            }
            refresh_stats(source, &ev);
            break;
          }
        }

        // Cryptbloom (3118): Life from Death (healing nova for allies: 50 + 50% AP)
        for (int it_id : source.items) {
          if (it_id == 3118) {
            const float heal_amount = 50.f + 0.50f * source.stats.ap;
            for (Unit& ally : units) {
              if (ally.team == source.team && !ally.dead && distance(ally, target) <= 800.f) {
                ally.hp = std::min(ally.max_hp, ally.hp + heal_amount);
                ev.damage.push_back({ally.id, 0.f, ally.hp, ally.max_hp, ally.total_shield()});
                ev.effects.push_back({ally.id, "Cryptbloom_heal", "", 0.f, false, source.id});
              }
            }
            break;
          }
        }
      }
      ev.stats_changed.push_back(target.id);
    }
    // a structure falls: the level script decides what that exposes (an inhibitor's time down is its SetDisableMinionSpawn)
    if (structure(target)) structure_destroyed(target);
    // the nexus falls: the match is over
    if (target.kind == UnitType::Nexus) winner_ = source.team, ev.winner = winner_;
    ev.deaths.push_back(target.id);
  }
  return damage;
}

// ---------------------------------------------------------------- the AI (documented behaviour, LoL Wiki)

void Match::minion_ai(Unit& u, MatchEvents& ev) {
  const float sight = u.stats.acquisition_range;
  auto in_sight = [&](const Unit& t) { return distance(u, t) <= sight + t.stats.gameplay_radius; };
  // keep the current target while it can be attacked and is in sight
  if (u.target) {
    const Unit* t = unit(u.target);
    if (!t || !attackable(u, *t) || !in_sight(*t)) u.target = 0, u.attack_start = -1;
  }
  // who to attack, by the documented priority (Minion: "Minion aggression"): 1 an enemy champion attacking an allied
  // champion, 2 an enemy minion attacking an allied champion, 3 an enemy minion attacking an allied minion, 4 an enemy
  // turret attacking an allied minion, 5 an enemy champion attacking an allied minion, 6 the closest enemy minion, 7 the
  // closest enemy champion; then structures. A champion attacking an allied champion takes over at once.
  auto priority = [&](const Unit& t) {
    auto attacks_ally = [&](UnitType kind) {
      if (!t.target) return false;
      const Unit* v = unit(t.target);
      return v && v->team == u.team && v->kind == kind && attacking(t, *v);
    };
    if (t.kind == UnitType::Champion && attacks_ally(UnitType::Champion)) return 1;
    if (t.kind == UnitType::Minion && attacks_ally(UnitType::Champion)) return 2;
    if (t.kind == UnitType::Minion && attacks_ally(UnitType::Minion)) return 3;
    if (t.kind == UnitType::Turret && attacks_ally(UnitType::Minion)) return 4;
    if (t.kind == UnitType::Champion && attacks_ally(UnitType::Minion)) return 5;
    if (t.kind == UnitType::Minion) return 6;
    if (t.kind == UnitType::Champion) return 7;
    return 8;
  };
  int best_p = 99;
  float best_d = 1e30f;
  uint32_t best = 0;
  for (const Unit& t : units) {
    if (!attackable(u, t) || !in_sight(t)) continue;
    const int p = priority(t);
    const float d = distance(u, t);
    if (p < best_p || (p == best_p && d < best_d)) best_p = p, best_d = d, best = t.id;
  }
  const Unit* current = u.target ? unit(u.target) : nullptr;
  if (best && (!current || (best_p == 1 && priority(*current) != 1))) {
    if (u.target != best) u.target = best, u.attack_start = -1, u.target_x = 1e9f;
  }
  if (u.target) return;
  lane_walk(u, ev);
}

void Match::lane_walk(Unit& u, MatchEvents& ev) {
  // walk the lane, waypoint by waypoint, then on to the enemy nexus
  if (!map_ || u.lane < 0 || u.lane > 2) return;
  const auto& lane = map_->lanes[static_cast<size_t>(u.lane)];
  const int dir = u.team == 0 ? 1 : -1;
  auto point = [&](int i) { return lane[static_cast<size_t>(i)]; };
  float gx = 0, gz = 0;
  bool have = false;
  while (u.lane_point >= 0 && u.lane_point < static_cast<int>(lane.size())) {
    const auto p = point(u.lane_point);
    const int nxt = u.lane_point + dir;
    // a waypoint behind it (after a chase) or reached: on to the next
    const bool closer_next = nxt >= 0 && nxt < static_cast<int>(lane.size()) &&
                             std::hypot(point(nxt)[0] - u.x, point(nxt)[1] - u.z) < std::hypot(point(nxt)[0] - p[0], point(nxt)[1] - p[1]);
    if (std::hypot(p[0] - u.x, p[1] - u.z) <= kWaypointReach || closer_next) {
      u.lane_point = nxt;
      continue;
    }
    gx = p[0], gz = p[1], have = true;
    break;
  }
  if (!have)
    for (const Unit& t : units)
      if (t.kind == UnitType::Nexus && t.team != u.team) gx = t.x, gz = t.z, have = true;
  if (!have) return;
  const bool going = !u.path.empty() && std::hypot(u.path.back().x - gx, u.path.back().z - gz) < 1.f;
  if (!going) {
    // lanes are open ground: a straight walk unless the grid says otherwise
    if (nav_ && !nav_->line_walkable(u.x, u.z, gx, gz, u.pathfinding_radius)) {
      path_to(u, gx, gz, ev);
    } else {
      u.path = {net::Point{gx, gz}};
      ev.path_changed.push_back(u.id);
    }
  }
}

void Match::turret_ai(Unit& u) {
  auto in_range = [&](const Unit& t) { return distance(u, t) <= reach(u, t); };
  if (u.target) {
    const Unit* t = unit(u.target);
    if (!t || !attackable(u, *t) || structure(*t) || !in_range(*t)) u.target = 0, u.attack_start = -1;
  }
  // documented (Turret): a turret keeps its target until it dies or leaves its range; a new one is the closest of the
  // most prioritized kind in range: siege and super minions, melee minions, caster minions, then champions. An enemy
  // champion that damages an allied champion within 1400 of the turret draws its fire at once.
  auto priority = [](const Unit& t) {
    if (t.minion == MinionKind::Siege || t.minion == MinionKind::Super) return 0;
    if (t.minion == MinionKind::Melee) return 1;
    if (t.minion == MinionKind::Caster) return 2;
    return t.kind == UnitType::Champion ? 4 : 3;
  };
  uint32_t aggro = 0, pick = 0;
  int best_p = 99;
  float best = 1e30f;
  for (const Unit& t : units) {
    if (!attackable(u, t) || structure(t) || !in_range(t)) continue;
    if (t.kind == UnitType::Champion && t.target) {
      const Unit* v = unit(t.target);
      if (v && v->team == u.team && v->kind == UnitType::Champion && attacking(t, *v) && distance(u, *v) <= 1400.f) aggro = t.id;
    }
    const int p = priority(t);
    const float d = distance(u, t);
    if (p < best_p || (p == best_p && d < best)) best_p = p, best = d, pick = t.id;
  }
  const uint32_t want = aggro ? aggro : u.target ? u.target : pick;
  if (want != u.target) u.target = want, u.attack_start = -1;
  // Warming Up ends 3 seconds after the turret's last hit on a champion (documented)
  if (u.champion_hits && clock.tick - u.last_champion_hit > ticks(3.0)) u.champion_hits = 0;
}

// ---------------------------------------------------------------- units do not stand in one another
//
// Units block one another by their pathfinding radius (CharacterRecord pathfindingCollisionRadius) [documented: units
// have collision, minions block]. How League resolves it is in its executable: here two units whose circles overlap
// are pushed apart along the line between them, the walking one giving way to the standing one, never into a wall
// [alegere proprie, de măsurat].

void Match::separate(MatchEvents& ev) {
  std::vector<float> px(units.size(), 0.f), pz(units.size(), 0.f);
  auto solid = [](const Unit& u) { return !u.dead && u.record && u.pathfinding_radius > 0 && !structure(u); };
  bool any = false;
  for (size_t i = 0; i < units.size(); ++i) {
    const Unit& a = units[i];
    if (!solid(a)) continue;
    for (size_t j = i + 1; j < units.size(); ++j) {
      const Unit& b = units[j];
      if (!solid(b)) continue;
      if (a.team == b.team && (a.ghosted || b.ghosted)) continue;  // SetGhostedForAllies (the first wave's minions)
      const float need = a.pathfinding_radius + b.pathfinding_radius;
      float dx = b.x - a.x, dz = b.z - a.z;
      if (std::fabs(dx) >= need || std::fabs(dz) >= need) continue;
      float d = std::sqrt(dx * dx + dz * dz);
      if (d >= need) continue;
      if (d < 1e-3f) {
        // on the same spot: apart along a direction their ids decide (the same in every run)
        const float angle = static_cast<float>((a.id * 7u + b.id * 13u) % 16u) * (6.2831853f / 16.f);
        dx = std::sin(angle), dz = std::cos(angle), d = 1.f;
      }
      const float overlap = need - (d < 1e-3f ? 0.f : std::min(d, need));
      const bool a_walks = !a.path.empty(), b_walks = !b.path.empty();
      const float share_a = a_walks == b_walks ? 0.5f : a_walks ? 1.f : 0.f;
      px[i] -= dx / d * overlap * share_a, pz[i] -= dz / d * overlap * share_a;
      px[j] += dx / d * overlap * (1 - share_a), pz[j] += dz / d * overlap * (1 - share_a);
      any = true;
    }
  }
  if (!any) return;
  for (size_t i = 0; i < units.size(); ++i) {
    if (px[i] == 0 && pz[i] == 0) continue;
    Unit& u = units[i];
    // no further than its own radius a tick, and never into a wall
    const float len = std::hypot(px[i], pz[i]), cap = std::min(len, u.pathfinding_radius);
    const float nx = u.x + px[i] / len * cap, nz = u.z + pz[i] / len * cap;
    if (nav_ && !nav_->walkable_at(nx, nz, u.pathfinding_radius)) continue;
    u.x = nx, u.z = nz;
    u.pushed += cap;
    // a pushed minion's path goes out again at most every ~2 s; between, its clients keep walking the old one
    // [măsurat: 13.3 replay, a walking minion's path re-sent with the same destination 1.8 times before its first
    // attack, 2.01..2.08 s apart; ours went out every 12 units pushed, 15 times as often]
    const bool may_report = u.kind != UnitType::Minion || u.path_sent_tick < 0 || clock.tick - u.path_sent_tick >= ticks(kMinionPathResend);
    if (u.pushed >= kPushReport && may_report) u.pushed = 0, ev.path_changed.push_back(u.id);
  }
}

// ---------------------------------------------------------------- one tick

MatchEvents Match::step(const std::vector<SpawnRequest>& spawns, const std::vector<Order>& orders) {
  MatchEvents ev;
  if (winner_ >= 0) {
    ++clock.tick;  // the match is over: the world stands still
    return ev;
  }
  ev_ = &ev;
  for (const SpawnRequest& s : spawns) {
    Unit& u = spawn(s.team, s.character, s.x, s.z);
    if (records_) {
      auto it = records_->find(s.character);
      if (it != records_->end()) set_record(u, &it->second);
    }
    if (s.move_speed > 0) u.move_speed = u.stats.move_speed = u.base.move_speed = s.move_speed;
    if (s.pathfinding_radius > 0) u.pathfinding_radius = s.pathfinding_radius;
    u.facing = s.facing;
    // the Practice Tool's dummy is not a champion; everything else that is requested is one
    u.kind = s.character == "PracticeTool_TargetDummy" ? UnitType::Other : UnitType::Champion;
    if (u.kind == UnitType::Champion && start_tick_ < 0) start_tick_ = clock.tick;  // the game begins
    if (u.kind == UnitType::Champion) {
      // level 1, the mode's starting gold (ai_StartingGold), a full resource
      u.gold = start_gold_ >= 0 ? start_gold_ : constant("ai_StartingGold", 0);
      u.level = std::clamp(start_level_, 1, 18);
      if (map_ && u.level >= 2 && static_cast<size_t>(u.level - 2) < map_->xp_required.size()) u.xp = map_->xp_required[static_cast<size_t>(u.level - 2)];
      level_stats(u);
      // a full resource, except one that is built up in fights (arType 4: fury)
      u.hp = u.max_hp, u.par = u.record && u.record->ar_type == 4 ? 0.f : u.max_par;
      give_spells(u);
      if (start_x_ >= 0) u.x = start_x_, u.z = start_z_;
      ev.stats_changed.push_back(u.id), ev.spells_changed.push_back(u.id);
    }
    ev.spawned.push_back(u.id);
  }
  // the game began this tick: the level script's server timers start
  if (start_tick_ >= 0 && !level_started_) level_start();

  // ---- champions whose death time is over: back at their team's spawn point, whole
  for (Unit& u : units) {
    if (!u.dead || u.respawn_tick < 0 || u.respawn_tick > clock.tick || !map_) continue;
    u.dead = false, u.respawn_tick = -1;
    u.hp = u.max_hp, u.par = u.record && u.record->ar_type == 4 ? 0.f : u.max_par;
    if (u.kind == UnitType::Champion) u.x = map_->spawn_point[u.team][0], u.z = map_->spawn_point[u.team][1], u.facing = map_->spawn_facing[u.team];
    u.next_attack = clock.tick;
    ev.respawned.push_back(u.id);
  }

  // ---- what the scripts left for now, and the buffs that end
  run_timers(ev);
  update_buffs(ev);

  // ---- orders: a new one replaces whatever the unit was doing (a windup in progress is cancelled: documented)
  for (const Order& o : orders) {
    Unit* u = unit(o.unit);
    // the shop serves the dead too (documented)
    if (u && o.type == Order::Type::BuyItem) {
      buy_item(*u, static_cast<int>(o.target), ev);
      continue;
    }
    if (u && o.type == Order::Type::SellItem) {
      sell_item(*u, o.slot, ev);
      continue;
    }
    if (!u || u->dead) continue;
    if (o.type == Order::Type::LevelSpell) {
      level_spell(*u, o.slot, ev);
      continue;
    }
    if (o.type == Order::Type::Cast) {
      order_cast(*u, o, ev);
      continue;
    }
    if (o.type == Order::Type::UseItem) {
      use_item(*u, o.slot, o.x, o.z, o.target, ev);
      continue;
    }
    if (u->dash.active) continue;                     // thrown by a spell: deaf to orders until it lands
    if (u->cast.slot >= 0 && u->cast.pending) u->cast = Cast{};  // walking into a spell's range: given up
    if (o.type == Order::Type::Attack && o.target == u->target) continue;  // the same target again: nothing changes
    u->attack_start = -1;
    if (o.type == Order::Type::Attack) {
      Unit* t = unit(o.target);
      if (!t || !attackable(*u, *t)) continue;
      u->target = t->id;
      if (!u->path.empty()) u->path.clear(), ev.path_changed.push_back(u->id);
      u->target_x = t->x + 1e9f;  // forces a path on the first tick that needs one
    } else {
      u->target = 0;
      path_to(*u, o.x, o.z, ev);
    }
  }

  update_casts(ev);

  // ---- the barracks and the AI
  barracks(ev);
  ai_update(ev);
  for (Unit& u : units) {
    if (u.dead || !u.record) continue;
    const bool think = (clock.tick + u.id) % kThinkTicks == 0;
    if (u.kind == UnitType::Minion && u.ai < 0 && think) minion_ai(u, ev);
    if (u.kind == UnitType::Turret || u.kind == UnitType::Fountain) turret_ai(u);
  }

  // ---- attackers: walk into range, then attack on their attack timer
  for (size_t ui = 0; ui < units.size(); ++ui) {
    Unit& u = units[ui];
    if (u.dead || !u.record || !u.target) continue;
    Unit* t = unit(u.target);
    if (!t || !attackable(u, *t)) {
      // (a scripted unit keeps the target until its script is told, next tick: OnTargetLost)
      if (u.ai < 0) u.target = 0;
      u.attack_start = -1;
      continue;
    }
    // stunned or disarmed units do not attack; nor does one that is casting or thrown
    if (has_flag(u, &Buff::stun) || has_flag(u, &Buff::disarm) || (u.cast.slot >= 0 && !u.cast.pending) || u.dash.active) {
      u.attack_start = -1;
      continue;
    }
    if (u.attack_start >= 0) {
      if (clock.tick == u.hit_tick) {
        const bool crit = u.attack_is_crit;
        const AttackSlot& a = (crit && !u.record->crits.empty())
                                  ? u.record->crits[0]
                                  : u.record->attacks[static_cast<size_t>(std::clamp(u.attack_slot, 0, static_cast<int>(u.record->attacks.size()) - 1))];
        // the attacker's buffs may add to this attack (Garen's Decisive Strike)
        const float bonus = u.buffs.empty() ? 0.f : attack_bonus(u.id, t->id);
        float dmg = attack_damage(u, *t, bonus);
        // a critical strike: 175% + bonus crit damage (Infinity Edge: +40%)
        // Ashe basic attacks never multiply damage directly (handled via Frost passive damage bonus)
        if (crit && u.skin != "Ashe") dmg *= (1.75f + u.stats.crit_damage);
        if (a.missile) {
          // the missile leaves from the attacker's position and flies at its movement's speed (FixedSpeedMovement
          // mSpeed), following the target (mTracksTarget) [de măsurat: from the unit's centre, to the target's centre]
          missiles_.push_back({u.id, t->id, dmg, u.x, u.z, std::max(1.f, a.missile_speed), &a, crit});
          ev.missiles.push_back({u.id, t->id, a.missile_speed, a.name});
        } else {
          const uint32_t tid = t->id;
          hit(u, *t, dmg, a.name, ev);
          if (u.kind == UnitType::Champion) champion_hook(u.id, "OnAttackHit", tid, crit, dmg);
        }
      }
      if (clock.tick >= u.hit_tick) u.attack_start = -1;  // the windup is over; the rest is the attack timer
      continue;
    }
    if (u.ai >= 0) {
      // its script decides: it walks where the script sent it until TurnOnAutoAttack, then attacks while the target
      // stands in range (out of range, the script's next look turns the attack off and sends it after the target)
      if (!u.auto_attack || u.forward_nav || clock.tick < u.auto_attack_tick || distance(u, *t) > reach(u, *t)) continue;
      if (!u.path.empty()) u.path.clear(), ev.path_changed.push_back(u.id);
      if (clock.tick >= u.next_attack) start_attack(u, *t, ev);
      continue;
    }
    if (distance(u, *t) > reach(u, *t)) {
      if (u.stats.move_speed <= 0) continue;  // structures do not walk
      // champions re-path as their target moves; minions only when they look around (a grid search for each)
      const bool may = u.kind != UnitType::Minion || (clock.tick + u.id) % kThinkTicks == 0 || u.path.empty();
      if (may && (std::hypot(t->x - u.target_x, t->z - u.target_z) > 1.f || u.path.empty())) {
        u.target_x = t->x, u.target_z = t->z;
        if (u.kind == UnitType::Minion && nav_ && nav_->line_walkable(u.x, u.z, t->x, t->z, u.pathfinding_radius)) {
          u.path = {net::Point{t->x, t->z}};
          ev.path_changed.push_back(u.id);
        } else {
          path_to(u, t->x, t->z, ev);
        }
      }
    } else {
      if (!u.path.empty()) u.path.clear(), ev.path_changed.push_back(u.id);
      if (clock.tick >= u.next_attack) start_attack(u, *t, ev);
    }
  }

  // ---- missiles: one tick of flight; one that reaches its target hits it (CastOnMovementComplete) and is gone
  // (DestroyOnMovementComplete)
  for (size_t i = 0; i < missiles_.size();) {
    Missile& m = missiles_[i];
    Unit* t = unit(m.target);
    if (!t || t->dead) {
      missiles_.erase(missiles_.begin() + static_cast<std::ptrdiff_t>(i));
      continue;
    }
    const float dx = t->x - m.x, dz = t->z - m.z;
    const float d = std::sqrt(dx * dx + dz * dz);
    const float step = m.speed * static_cast<float>(kTickSeconds);
    if (d <= step) {
      Unit* s = unit(m.source);
      if (s) {
        const uint32_t sid = s->id, tid = t->id;
        const bool champion = s->kind == UnitType::Champion;
        hit(*s, *t, m.damage, m.slot->name, ev);
        if (champion) champion_hook(sid, "OnAttackHit", tid, m.crit, m.damage);
      }
      missiles_.erase(missiles_.begin() + static_cast<std::ptrdiff_t>(i));
      continue;
    }
    m.x += dx / d * step, m.z += dz / d * step;
    ++i;
  }

  update_skill_missiles(ev);

  // ---- movement; an attacker stops as soon as its target is in range
  const float dt = static_cast<float>(kTickSeconds);
  for (size_t ui = 0; ui < units.size(); ++ui) {
    Unit& u = units[ui];
    if (u.dead) continue;
    if (u.dash.active) {
      // thrown along a line at the dash's speed, whatever lies between
      const float dx = u.dash.x - u.x, dz = u.dash.z - u.z, d = std::sqrt(dx * dx + dz * dz), reach_now = u.dash.speed * dt;
      if (d <= reach_now) {
        u.x = u.dash.x, u.z = u.dash.z;
        const int on_end = u.dash.on_end;
        u.dash = Dash{};
        if (on_end) {
          run_ref(on_end);
        }
      } else {
        u.x += dx / d * reach_now, u.z += dz / d * reach_now;
      }
      continue;
    }
    // stunned and rooted units stand; so does one casting
    if (has_flag(u, &Buff::stun) || has_flag(u, &Buff::root) || (u.cast.slot >= 0 && !u.cast.pending)) continue;
    float budget = u.move_speed * dt;
    const bool engaged = u.ai < 0 || (u.auto_attack && !u.forward_nav && clock.tick >= u.auto_attack_tick);
    const Unit* t = u.target && engaged ? unit(u.target) : nullptr;
    const float r = t && u.record ? reach(u, *t) : 0.f;
    while (budget > 0 && !u.path.empty()) {
      if (t && distance(u, *t) <= r) {
        u.path.clear();
        ev.path_changed.push_back(u.id);
        break;
      }
      const net::Point& p = u.path.front();
      const float dx = p.x - u.x;
      const float dz = p.z - u.z;
      const float d = std::sqrt(dx * dx + dz * dz);
      if (d > 1e-4f) u.facing = std::atan2(dx, dz);
      if (d <= budget) {
        u.x = p.x;
        u.z = p.z;
        budget -= d;
        u.path.erase(u.path.begin());
      } else {
        u.x += dx / d * budget;
        u.z += dz / d * budget;
        budget = 0;
      }
    }
  }

  separate(ev);
  regenerate(ev);
  champion_ticks(ev);

  // ---- an outer turret's plating leaves with its turret, or when the plating falls [măsurat: 845.06 s in a real match]
  for (Unit& u : units)
    if (u.plating && u.remove_tick < 0) {
      const Unit* turret = unit(u.owner);
      if (!turret || turret->dead || game_seconds() >= 845.06) u.remove_tick = clock.tick;
    }

  // ---- dead minions leave
  bool removed = false;
  for (const Unit& u : units)
    if (u.remove_tick >= 0 && u.remove_tick <= clock.tick) ev.removed.push_back(u.id), removed = true;
  if (removed) {
    units.erase(std::remove_if(units.begin(), units.end(), [&](const Unit& u) { return u.remove_tick >= 0 && u.remove_tick <= clock.tick; }), units.end());
    index_.clear();
    for (size_t i = 0; i < units.size(); ++i) index_[units[i].id] = i;
  }
  for (uint32_t id : ev.path_changed)
    if (Unit* u = unit(id)) u->path_sent_tick = clock.tick;
  ++clock.tick;
  ev_ = nullptr;
  return ev;
}

}  // namespace ba

// ---------------------------------------------------------------- the shop (LoL Wiki "Shop", revision 2023-11-25)

namespace ba {

bool Match::in_shop(const Unit& u) const {
  if (u.kind != UnitType::Champion || !map_) return false;
  if (u.dead) return true;
  // "in proximity of the shop": the team's fountain [de măsurat: the distance; the fountain's sp_RegenRadius here]
  const float dx = u.x - map_->spawn_point[u.team][0], dz = u.z - map_->spawn_point[u.team][1];
  const float r = map_->constant("sp_RegenRadius", 1100);
  return dx * dx + dz * dz <= r * r;
}

void Match::buy_item(Unit& u, int id, MatchEvents& ev) {
  if (!items_ || !in_shop(u)) return;
  const ItemDef* d = items_->find(id);
  if (!d || !d->in_store) return;
  if (!items_->mode_items.empty() && !items_->mode_items.count(id)) return;
  if (!d->required_champion.empty() && d->required_champion != u.skin) return;
  // the recipe: components the champion owns are used up (each owned item at most once, the deepest first) and cost
  // nothing more; the rest is bought along (documented: Shop, "purchasing an item is equivalent to ...")
  std::array<int, 7> inv = u.items;
  std::array<uint8_t, 7> stacks = u.item_stacks;
  std::function<int(int)> cost_of = [&](int item) -> int {
    for (size_t k = 0; k < inv.size(); ++k)
      if (inv[k] == item && item != id) {
        if (stacks[k] > 1) --stacks[k];
        else inv[k] = 0, stacks[k] = 0;
        return 0;
      }
    const ItemDef* x = items_->find(item);
    if (!x) return 0;
    int c = x->price;
    for (int comp : x->components) c += cost_of(comp);
    return c;
  };
  const int cost = cost_of(id);
  if (static_cast<float>(cost) > u.gold) return;
  // the slot: a stack of the same item with room, else the first free slot of its groups' range (trinkets: 6)
  int lo = 0, hi = 5;
  for (uint32_t g : d->groups) {
    auto gd = items_->groups.find(g);
    if (gd != items_->groups.end() && (gd->second.slot_min != 0 || gd->second.slot_max != 5)) lo = gd->second.slot_min, hi = gd->second.slot_max;
  }
  int slot = -1;
  for (int k = lo; k <= hi && k < 7 && slot < 0; ++k)
    if (inv[static_cast<size_t>(k)] == id && stacks[static_cast<size_t>(k)] < std::max(1, d->max_stack)) slot = k;
  for (int k = lo; k <= hi && k < 7 && slot < 0; ++k)
    if (inv[static_cast<size_t>(k)] == 0) slot = k;
  if (slot < 0) return;
  const bool stacking = inv[static_cast<size_t>(slot)] == id;
  // ownership limits: each of its groups' mMaxGroupOwnable (boots: one; potions: one kind, stacked up to maxStack),
  // counted after the components are used up; a stack that grows takes no new place
  if (!stacking)
    for (uint32_t g : d->groups) {
      auto gd = items_->groups.find(g);
      if (gd == items_->groups.end() || gd->second.max_ownable < 0) continue;
      int owned = 0;
      for (int item : inv)
        if (const ItemDef* x = item ? items_->find(item) : nullptr)
          if (std::find(x->groups.begin(), x->groups.end(), g) != x->groups.end()) ++owned;
      if (owned >= gd->second.max_ownable) return;
    }
  inv[static_cast<size_t>(slot)] = id, stacks[static_cast<size_t>(slot)] = static_cast<uint8_t>(stacks[static_cast<size_t>(slot)] + 1);
  u.items = inv, u.item_stacks = stacks;
  u.gold -= static_cast<float>(cost);
  refresh_stats(u, &ev);
  ev.items_changed.push_back(u.id), ev.stats_changed.push_back(u.id);
}

void Match::sell_item(Unit& u, int slot, MatchEvents& ev) {
  if (!items_ || slot < 0 || slot > 6 || !in_shop(u)) return;
  const size_t k = static_cast<size_t>(slot);
  const ItemDef* d = u.items[k] ? items_->find(u.items[k]) : nullptr;
  if (!d || !d->can_be_sold) return;
  // the item's whole worth times its sellBackModifier [meta default 0.7], rounded down [de măsurat: the rounding]
  u.gold += std::floor(static_cast<float>(items_->total_cost(d->id)) * d->sell_back);
  if (u.item_stacks[k] > 1) --u.item_stacks[k];
  else u.items[k] = 0, u.item_stacks[k] = 0;
  refresh_stats(u, &ev);
  ev.items_changed.push_back(u.id), ev.stats_changed.push_back(u.id);
}

void Match::use_item(Unit& u, int slot, float x, float z, uint32_t target, MatchEvents& ev) {
  (void)x; (void)z; (void)target;
  if (u.dead || slot < 0 || slot >= static_cast<int>(u.items.size())) return;
  const int item_id = u.items[static_cast<size_t>(slot)];
  if (item_id == 0) return;
  if (clock.tick < u.item_cooldowns[static_cast<size_t>(slot)]) return;
  if (has_flag(u, &Buff::stun) || has_flag(u, &Buff::silence)) return;

  // Health Potion (2003)
  if (item_id == 2003) {
    if (find_buff(u, "HealthPotion")) return;
    Buff b;
    b.name = "HealthPotion";
    b.source = u.id;
    b.end_tick = clock.tick + ticks(15.0);
    u.buffs.push_back(b);
    ev.buffs.push_back({u.id, b.name, 15.0f, true});
    u.item_cooldowns[static_cast<size_t>(slot)] = clock.tick + ticks(0.5);
    if (u.item_stacks[static_cast<size_t>(slot)] > 1) {
      --u.item_stacks[static_cast<size_t>(slot)];
    } else {
      u.items[static_cast<size_t>(slot)] = 0;
      u.item_stacks[static_cast<size_t>(slot)] = 0;
    }
    refresh_stats(u, &ev);
    ev.items_changed.push_back(u.id);
    return;
  }

  // Refillable Potion (2031)
  if (item_id == 2031) {
    if (u.item_stacks[static_cast<size_t>(slot)] == 0 || find_buff(u, "RefillablePotion")) return;
    Buff b;
    b.name = "RefillablePotion";
    b.source = u.id;
    b.end_tick = clock.tick + ticks(12.0);
    u.buffs.push_back(b);
    ev.buffs.push_back({u.id, b.name, 12.0f, true});
    --u.item_stacks[static_cast<size_t>(slot)];
    u.item_cooldowns[static_cast<size_t>(slot)] = clock.tick + ticks(0.5);
    ev.items_changed.push_back(u.id);
    return;
  }

  // Corrupting Potion (2033)
  if (item_id == 2033) {
    if (u.item_stacks[static_cast<size_t>(slot)] == 0 || find_buff(u, "CorruptingPotion")) return;
    Buff b;
    b.name = "CorruptingPotion";
    b.source = u.id;
    b.end_tick = clock.tick + ticks(12.0);
    u.buffs.push_back(b);
    ev.buffs.push_back({u.id, b.name, 12.0f, true});
    --u.item_stacks[static_cast<size_t>(slot)];
    u.item_cooldowns[static_cast<size_t>(slot)] = clock.tick + ticks(0.5);
    ev.items_changed.push_back(u.id);
    return;
  }

  // Zhonya's Hourglass (3157)
  if (item_id == 3157) {
    Buff b;
    b.name = "ZhonyaHourglass";
    b.source = u.id;
    b.end_tick = clock.tick + ticks(2.5);
    b.untargetable = true;
    b.invulnerable = true;
    b.stun = true;
    b.root = true;
    b.disarm = true;
    b.silence = true;
    u.buffs.push_back(b);
    ev.buffs.push_back({u.id, b.name, 2.5f, true});
    u.target = 0;
    u.attack_start = -1;
    u.path.clear();
    ev.path_changed.push_back(u.id);
    u.item_cooldowns[static_cast<size_t>(slot)] = clock.tick + ticks(120.0);
    ev.spells_changed.push_back(u.id);
    return;
  }

  // Youmuu's Ghostblade (3142)
  if (item_id == 3142) {
    Buff b;
    b.name = "YoumuuGhostblade";
    b.source = u.id;
    b.end_tick = clock.tick + ticks(6.0);
    b.move_speed_pct = 0.25f;
    u.buffs.push_back(b);
    refresh_stats(u, &ev);
    ev.buffs.push_back({u.id, b.name, 6.0f, true});
    u.item_cooldowns[static_cast<size_t>(slot)] = clock.tick + ticks(45.0);
    ev.spells_changed.push_back(u.id);
    return;
  }

  // Ravenous Hydra (3074) / Profane Hydra (6698) / Titanic Hydra (3748) / Tiamat (3077)
  if (item_id == 3074 || item_id == 6698 || item_id == 3748 || item_id == 3077) {
    const float radius = 450.f;
    for (Unit& target_unit : units) {
      if (target_unit.dead || target_unit.team == u.team || structure(target_unit) || &target_unit == &u) continue;
      if (distance(u, target_unit) <= radius + target_unit.stats.gameplay_radius) {
        float raw_ad = (item_id == 3074) ? 1.0f * u.stats.ad : (item_id == 6698) ? (target_unit.hp < target_unit.max_hp * 0.5f ? 1.2f * u.stats.ad : 0.8f * u.stats.ad) : 0.8f * u.stats.ad;
        spell_damage(u, target_unit, raw_ad, DamageType::Physical, "ItemHydraCrescent", ev);
      }
    }
    u.item_cooldowns[static_cast<size_t>(slot)] = clock.tick + ticks(10.0);
    ev.spells_changed.push_back(u.id);
    return;
  }

  // Randuin's Omen (3143)
  if (item_id == 3143) {
    const float radius = 550.f;
    for (Unit& target_unit : units) {
      if (target_unit.dead || target_unit.team == u.team || structure(target_unit) || &target_unit == &u) continue;
      if (distance(u, target_unit) <= radius + target_unit.stats.gameplay_radius) {
        Buff slow_b;
        slow_b.name = "RanduinsSlow";
        slow_b.source = u.id;
        slow_b.end_tick = clock.tick + ticks(1.5);
        slow_b.move_speed_pct = -0.70f;
        target_unit.buffs.push_back(slow_b);
        refresh_stats(target_unit, &ev);
        ev.buffs.push_back({target_unit.id, slow_b.name, 1.5f, true});
      }
    }
    u.item_cooldowns[static_cast<size_t>(slot)] = clock.tick + ticks(90.0);
    ev.spells_changed.push_back(u.id);
    return;
  }

  // Locket of the Iron Solari (3190)
  if (item_id == 3190) {
    const float radius = 850.f;
    for (Unit& ally : units) {
      if (ally.dead || ally.team != u.team || ally.kind != UnitType::Champion) continue;
      if (distance(u, ally) <= radius) {
        Buff shield_b;
        shield_b.name = "LocketShield";
        shield_b.source = u.id;
        shield_b.end_tick = clock.tick + ticks(2.5);
        shield_b.shield = 200.f + 10.f * static_cast<float>(ally.level);
        ally.buffs.push_back(shield_b);
        ev.buffs.push_back({ally.id, shield_b.name, 2.5f, true});
      }
    }
    u.item_cooldowns[static_cast<size_t>(slot)] = clock.tick + ticks(90.0);
    ev.spells_changed.push_back(u.id);
    return;
  }

  // Shurelya's Battlesong (2065)
  if (item_id == 2065) {
    const float radius = 1000.f;
    for (Unit& ally : units) {
      if (ally.dead || ally.team != u.team || ally.kind != UnitType::Champion) continue;
      if (distance(u, ally) <= radius) {
        Buff speed_b;
        speed_b.name = "ShurelyasInspire";
        speed_b.source = u.id;
        speed_b.end_tick = clock.tick + ticks(4.0);
        speed_b.move_speed_pct = 0.30f;
        ally.buffs.push_back(speed_b);
        refresh_stats(ally, &ev);
        ev.buffs.push_back({ally.id, speed_b.name, 4.0f, true});
      }
    }
    u.item_cooldowns[static_cast<size_t>(slot)] = clock.tick + ticks(75.0);
    ev.spells_changed.push_back(u.id);
    return;
  }

  // Hextech Rocketbelt (3152)
  if (item_id == 3152) {
    float dx = x - u.x, dz = z - u.z;
    float len = std::hypot(dx, dz);
    if (len < 1e-3f) {
      dx = std::sin(u.facing);
      dz = std::cos(u.facing);
      len = 1.0f;
    }
    dx /= len;
    dz /= len;
    const float dash_dist = 275.f;
    const float target_x = u.x + dx * dash_dist, target_z = u.z + dz * dash_dist;
    u.dash.active = true;
    u.dash.x = target_x;
    u.dash.z = target_z;
    u.dash.speed = 1200.f;
    ev.dashes.push_back({u.id, target_x, target_z, 1200.f});
    // Fire rockets in front
    const float dmg = 125.f + 0.15f * u.stats.ap;
    for (Unit& target_unit : units) {
      if (target_unit.dead || target_unit.team == u.team || structure(target_unit) || &target_unit == &u) continue;
      if (distance(u, target_unit) <= 650.f) {
        float tx = target_unit.x - u.x, tz = target_unit.z - u.z;
        float dot = (tx * dx + tz * dz) / std::max(1.f, std::hypot(tx, tz));
        if (dot > 0.5f) { // in front ~60 degree cone
          spell_damage(u, target_unit, dmg, DamageType::Magic, "ItemRocketbeltRockets", ev);
        }
      }
    }
    // 30% MS for 1.5s
    Buff speed_b;
    speed_b.name = "RocketbeltHaste";
    speed_b.source = u.id;
    speed_b.end_tick = clock.tick + ticks(1.5);
    speed_b.move_speed_pct = 0.30f;
    u.buffs.push_back(speed_b);
    refresh_stats(u, &ev);
    ev.buffs.push_back({u.id, speed_b.name, 1.5f, true});

    u.item_cooldowns[static_cast<size_t>(slot)] = clock.tick + ticks(40.0);
    ev.spells_changed.push_back(u.id);
    return;
  }

  // Redemption (3107)
  if (item_id == 3107) {
    const float rad = 550.f;
    for (Unit& target_unit : units) {
      if (target_unit.dead || &target_unit == &u) continue;
      if (std::hypot(target_unit.x - x, target_unit.z - z) <= rad) {
        if (target_unit.team == u.team && target_unit.kind == UnitType::Champion) {
          const float heal = 200.f + 11.f * static_cast<float>(target_unit.level);
          target_unit.hp = std::min(target_unit.max_hp, target_unit.hp + heal);
          ev.damage.push_back({target_unit.id, 0.f, target_unit.hp, target_unit.max_hp, target_unit.total_shield()});
        } else if (target_unit.team != u.team && target_unit.kind == UnitType::Champion) {
          const float true_dmg = 0.10f * target_unit.max_hp;
          spell_damage(u, target_unit, true_dmg, DamageType::True, "ItemRedemptionBurn", ev);
        }
      }
    }
    u.item_cooldowns[static_cast<size_t>(slot)] = clock.tick + ticks(90.0);
    ev.spells_changed.push_back(u.id);
    return;
  }

  // Mikael's Blessing (3222)
  if (item_id == 3222) {
    Unit* target_unit = unit(target);
    if (!target_unit || target_unit->team != u.team || target_unit->kind != UnitType::Champion) target_unit = &u;
    if (target_unit && !target_unit->dead) {
      // Cleanse crowd control
      for (auto it = target_unit->buffs.begin(); it != target_unit->buffs.end();) {
        if (it->stun || it->root || it->silence || it->disarm) {
          it = target_unit->buffs.erase(it);
        } else {
          ++it;
        }
      }
      refresh_stats(*target_unit, &ev);
      const float heal = 100.f + 5.f * static_cast<float>(target_unit->level);
      target_unit->hp = std::min(target_unit->max_hp, target_unit->hp + heal);
      ev.damage.push_back({target_unit->id, 0.f, target_unit->hp, target_unit->max_hp, target_unit->total_shield()});
    }
    u.item_cooldowns[static_cast<size_t>(slot)] = clock.tick + ticks(120.0);
    ev.spells_changed.push_back(u.id);
    return;
  }

  // Quicksilver Sash (3140) / Mercurial Scimitar (3139)
  if (item_id == 3140 || item_id == 3139) {
    for (auto it = u.buffs.begin(); it != u.buffs.end();) {
      if (it->stun || it->root || it->silence || it->disarm || it->move_speed_pct < 0) {
        it = u.buffs.erase(it);
      } else {
        ++it;
      }
    }
    if (item_id == 3139) {
      Buff b;
      b.name = "MercurialQuicksilver";
      b.source = u.id;
      b.end_tick = clock.tick + ticks(1.5);
      b.move_speed_pct = 0.50f;
      u.buffs.push_back(b);
      ev.buffs.push_back({u.id, b.name, 1.5f, true});
    }
    refresh_stats(u, &ev);
    u.item_cooldowns[static_cast<size_t>(slot)] = clock.tick + ticks(90.0);
    ev.spells_changed.push_back(u.id);
    return;
  }
}

}  // namespace ba
