// Spells: what Riot keeps on its servers. The numbers come from each spell's data (ba/SpellData.h); what a spell does
// is a Lua 5.1 script (scripts/*.lua), as Riot's own spells are Lua "building blocks" over a C++ core. This file is
// that core: buffs, casts, cooldowns, skillshot missiles, dashes, timers, and the functions the scripts call.
//
// Our readings, marked [de măsurat] where the game's own rule is in its code:
//   a spell's cooldown and cost start when its cast begins; casts with a cast time stop the caster until they end;
//   spell ranges are measured between centres; a skillshot hits what its line (mLineWidth) touches, by the target's
//   gameplay radius.

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>

#include "Match.h"

extern "C" {
#include "lauxlib.h"
#include "lua.h"
#include "lualib.h"
}

namespace ba {

namespace {

int64_t ticks(double seconds) { return std::max<int64_t>(1, static_cast<int64_t>(std::ceil(seconds / kTickSeconds - 1e-9))); }

bool structure(const Unit& u) {
  return u.kind == UnitType::Turret || u.kind == UnitType::Inhibitor || u.kind == UnitType::Nexus || u.kind == UnitType::Fountain;
}

const char* kPrelude = R"(
Spells = {}
Champions = {}
function Spell(name) return function(t) Spells[name] = t end end
function Champion(name) return function(t) Champions[name] = t end end
)";

}  // namespace

// ---------------------------------------------------------------- stats with buffs

bool Match::has_flag(const Unit& u, bool Buff::*flag) const {
  for (const Buff& b : u.buffs)
    if (b.*flag) return true;
  return false;
}

Buff* Match::find_buff(Unit& u, const std::string& name) {
  for (Buff& b : u.buffs)
    if (b.name == name) return &b;
  return nullptr;
}

void Match::refresh_stats(Unit& u, MatchEvents* ev) {
  const float old_speed = u.move_speed, old_max = u.stats.max_hp;
  UnitStats s = u.base;
  float speed_bonus = 0, slow = 0, as_bonus = 0, armor_pct = 0, mr_pct = 0, speed_flat = 0;
  // the inventory's items: their flat stats add to the base, their percents like a buff's (documented: each stat)
  ItemStats it;
  if (items_)
    for (size_t k = 0; k < u.items.size(); ++k)
      if (const ItemDef* d = u.items[k] ? items_->find(u.items[k]) : nullptr)
        for (int n = 0; n < std::max(1, static_cast<int>(u.item_stacks[k])); ++n) it += d->stats;
  s.max_hp += it.hp, s.ad += it.ad, s.ap += it.ap, s.armor += it.armor, s.spell_block += it.spell_block;
  s.crit += it.crit, s.ability_haste += it.ability_haste, as_bonus += it.attack_speed_pct;
  s.crit_damage = it.crit_damage;
  s.tenacity = it.tenacity;
  s.life_steal = it.life_steal;
  s.omnivamp = it.omnivamp;
  s.armor_pen_pct = it.armor_pen_pct;
  s.magic_pen_flat = it.magic_pen;
  s.magic_pen_pct = it.magic_pen_pct;
  speed_flat += it.move_speed, speed_bonus += it.move_speed_pct;
  // Item unique passive stat calculations (patch 14.1)
  if (items_) {
    for (int item_id : u.items) {
      // Rabadon's Deathcap (3089): Magical Opus (+35% AP)
      if (item_id == 3089) {
        s.ap *= 1.35f;
      }
      // Infinity Edge (3031): Perfection (+40% Critical Strike Damage)
      if (item_id == 3031) {
        s.crit_damage += 0.40f;
      }
      // Sterak's Gage (3053): The Claws That Catch (+50% base AD as bonus AD)
      if (item_id == 3053) {
        s.ad += 0.50f * u.base.ad;
      }
    }
    // Bloodthirster (3072): Engorge (+10..40 AD while above 70% max HP)
    if (u.max_hp > 0 && u.hp / u.max_hp >= 0.70f) {
      for (int item_id : u.items) {
        if (item_id == 3072) {
          s.ad += 10.f + (30.0f / 17.0f) * static_cast<float>(std::clamp(u.level - 1, 0, 17));
          break;
        }
      }
    }
  }
  for (const Buff& b : u.buffs) {
    s.ad += b.ad, s.armor += b.armor, s.spell_block += b.spell_block;
    s.crit += b.crit;
    s.tenacity += b.tenacity;
    speed_flat += b.move_speed;
    armor_pct += b.armor_pct, mr_pct += b.spell_block_pct;
    as_bonus += b.attack_speed_pct;
    // speed bonuses add up; of the slows only the strongest counts (documented: Movement speed)
    if (b.move_speed_pct >= 0) speed_bonus += b.move_speed_pct;
    else slow = std::min(slow, b.move_speed_pct);
  }
  s.armor *= 1.f + armor_pct, s.spell_block *= 1.f + mr_pct;
  s.ad = std::max(0.f, s.ad), s.crit = std::clamp(s.crit, 0.f, 1.f);
  // flat bonuses first, then the percents and the strongest slow (documented: Movement speed)
  s.move_speed = (u.base.move_speed + speed_flat) * (1.f + speed_bonus) * (1.f + slow);
  // bonus attack speed is a share of the record's attackSpeedRatio (documented)
  if (u.record) s.attack_speed += u.record->attack_speed_ratio * as_bonus;
  u.stats = s;
  u.move_speed = s.move_speed;
  u.max_hp = s.max_hp;
  // mana from items goes to mana users only (arType 0) [dedus: the resource the item's stat names]
  const float old_par_max = u.max_par;
  u.max_par = u.base_max_par + (u.record && u.record->ar_type == 0 && u.base_max_par > 0 ? it.mana : 0.f);
  if (u.max_par > old_par_max && old_par_max > 0) u.par += u.max_par - old_par_max;  // a bought mana item fills as it grows
  u.par = std::min(u.par, u.max_par);
  if (old_max > 0 && u.max_hp != old_max) u.hp = std::min(u.hp, u.max_hp);
  if (ev && old_speed != u.move_speed && !u.path.empty()) ev->path_changed.push_back(u.id);
  if (ev && u.kind == UnitType::Champion) ev->stats_changed.push_back(u.id);
}

void Match::remove_buff(Unit& u, size_t index, bool expired, MatchEvents& ev) {
  const Buff b = u.buffs[index];
  const uint32_t id = u.id;
  u.buffs.erase(u.buffs.begin() + static_cast<std::ptrdiff_t>(index));
  refresh_stats(u, &ev);
  ev.buffs.push_back({id, b.name, 0.f, false});
  if (b.name == "GuardianAngelStasis" && expired) {
    u.hp = u.base.max_hp * 0.5f;
    if (u.record && u.record->ar_type == 0) u.par = std::min(u.max_par, u.par + u.max_par * 0.3f);
    ev.damage.push_back({u.id, 0.f, u.hp, u.max_hp});
    ev.stats_changed.push_back(u.id);
  }
  if (b.on_expire && L_) {
    lua_rawgeti(L_, LUA_REGISTRYINDEX, b.on_expire);
    lua_pushboolean(L_, expired);
    call(1, 0, "a buff's on_expire");
  }
  for (int ref : {b.on_attack, b.on_expire})
    if (ref && L_) luaL_unref(L_, LUA_REGISTRYINDEX, ref);
}

void Match::update_buffs(MatchEvents& ev) {
  // (a script's on_expire may add or remove buffs: by index, re-reading the unit each time)
  for (size_t ui = 0; ui < units.size(); ++ui)
    for (size_t i = 0; i < units[ui].buffs.size();) {
      const Buff& b = units[ui].buffs[i];
      if ((b.end_tick >= 0 && b.end_tick <= clock.tick) || units[ui].dead) remove_buff(units[ui], i, !units[ui].dead, ev);
      else ++i;
    }
}

// ---------------------------------------------------------------- damage from spells

float Match::spell_damage(Unit& source, Unit& target, float raw, DamageType type, const std::string& spell, MatchEvents& ev) {
  if (target.dead || raw <= 0) return 0;

  // Shadowflame (4645): Cinderbloom crits for 120% magic damage if target < 35% HP
  if (type == DamageType::Magic && target.kind == UnitType::Champion && target.max_hp > 0 && target.hp / target.max_hp < 0.35f) {
    for (int it_id : source.items) {
      if (it_id == 4645) {
        raw *= 1.20f;
        break;
      }
    }
  }

  // Lord Dominik's Regards (3036): Giant Slayer up to +22% physical damage
  if (type == DamageType::Physical && target.kind == UnitType::Champion && target.stats.max_hp > source.stats.max_hp) {
    for (int it_id : source.items) {
      if (it_id == 3036) {
        const float diff = std::clamp(target.stats.max_hp - source.stats.max_hp, 0.f, 2500.f);
        raw *= 1.f + 0.22f * (diff / 2500.f);
        break;
      }
    }
  }

  // Armor or Magic Resist with penetration (documented: League 14.1 formulas)
  float resist = 0.f;
  if (type == DamageType::Physical) {
    resist = target.stats.armor;
    if (source.kind == UnitType::Champion && source.stats.armor_pen_pct > 0) {
      resist *= (1.f - source.stats.armor_pen_pct);
    }
  } else if (type == DamageType::Magic) {
    resist = target.stats.spell_block;
    if (source.kind == UnitType::Champion) {
      if (source.stats.magic_pen_pct > 0) resist *= (1.f - source.stats.magic_pen_pct);
      if (source.stats.magic_pen_flat > 0) resist = std::max(0.f, resist - source.stats.magic_pen_flat);
    }
  }

  float dmg = resist >= 0 ? raw * 100.f / (100.f + resist) : raw * (2.f - 100.f / (100.f - resist));
  // the mode's ratio between the classes (dr_HeroToUnit ...)
  auto cls = [](const Unit& u) { return u.kind == UnitType::Champion ? "Hero" : structure(u) ? "Building" : "Unit"; };
  dmg *= constant((std::string("dr_") + cls(source) + "To" + cls(target)).c_str(), 1.f);
  ev.hits.push_back({source.id, target.id, spell});

  // Rylai's Crystal Scepter (3116): Rimefrost 30% slow for 1s on ability damage
  if (source.kind == UnitType::Champion && (target.kind == UnitType::Champion || target.kind == UnitType::Minion) && !target.dead) {
    for (int it_id : source.items) {
      if (it_id == 3116) {
        if (!find_buff(target, "RylaiSlow")) {
          Buff b;
          b.name = "RylaiSlow";
          b.source = source.id;
          b.end_tick = clock.tick + ticks(1.0);
          b.move_speed_pct = -0.30f;
          target.buffs.push_back(b);
          ev.buffs.push_back({target.id, b.name, 1.0f, true});
        }
        break;
      }
    }
  }

  // Liandry's Torment (3151): Torment 2% max HP magic damage per second for 3s
  if (source.kind == UnitType::Champion && target.kind == UnitType::Champion && !target.dead) {
    for (int it_id : source.items) {
      if (it_id == 3151) {
        Buff* b = find_buff(target, "LiandryTorment");
        if (!b) {
          Buff nb;
          nb.name = "LiandryTorment";
          nb.source = source.id;
          nb.end_tick = clock.tick + ticks(3.0);
          target.buffs.push_back(nb);
          ev.buffs.push_back({target.id, nb.name, 3.0f, true});
        } else {
          b->end_tick = clock.tick + ticks(3.0);
        }
        break;
      }
    }
  }

  // Stormsurge (6657): Squall on dealing >= 35% max HP in 2.5s
  if (source.kind == UnitType::Champion && target.kind == UnitType::Champion && !target.dead) {
    for (int it_id : source.items) {
      if (it_id == 6657) {
        Buff* b = find_buff(target, "StormsurgeCharge");
        if (!b) {
          Buff nb;
          nb.name = "StormsurgeCharge";
          nb.source = source.id;
          nb.end_tick = clock.tick + ticks(2.5);
          nb.damage_taken = dmg;
          target.buffs.push_back(nb);
        } else {
          b->damage_taken += dmg;
          if (b->damage_taken >= 0.35f * target.max_hp) {
            remove_buff(target, static_cast<size_t>(b - target.buffs.data()), true, ev);
            const float squall_raw = 140.f + 0.20f * source.stats.ap;
            const float mr = target.stats.spell_block;
            const float squall_mitigated = mr >= 0 ? squall_raw * 100.f / (100.f + mr) : squall_raw * (2.f - 100.f / (100.f - mr));
            apply_damage(source, target, squall_mitigated, ev);
            Buff ms_b;
            ms_b.name = "StormsurgeHaste";
            ms_b.source = source.id;
            ms_b.end_tick = clock.tick + ticks(2.0);
            ms_b.move_speed_pct = 0.25f;
            source.buffs.push_back(ms_b);
            ev.buffs.push_back({source.id, ms_b.name, 2.0f, true});
          }
        }
        break;
      }
    }
  }

  // Malignance (6697): Hatefog ground zone on ultimate damage
  if (source.kind == UnitType::Champion && target.kind == UnitType::Champion && !target.dead) {
    if (spell == "LuxR" || spell == "GarenR" || spell == "EnchantedCrystalArrow" || spell == "ZedR") {
      for (int it_id : source.items) {
        if (it_id == 6697) {
          Buff* b = find_buff(target, "MalignanceHatefog");
          if (!b) {
            Buff nb;
            nb.name = "MalignanceHatefog";
            nb.source = source.id;
            nb.end_tick = clock.tick + ticks(3.0);
            nb.spell_block = -10.f;
            target.buffs.push_back(nb);
            ev.buffs.push_back({target.id, nb.name, 3.0f, true});
          } else {
            b->end_tick = clock.tick + ticks(3.0);
          }
          break;
        }
      }
    }
  }

  return apply_damage(source, target, dmg, ev);
}

// ---------------------------------------------------------------- spell slots, levels, casts

void Match::give_spells(Unit& u) {
  if (!spells_ || !u.record) return;
  const std::map<std::string, SpellData>* all = spells_(u.skin);
  if (!all) return;
  u.spell_set = all;
  for (size_t i = 0; i < 4; ++i) {
    const std::string& path = u.record->spells[i];
    auto it = all->find(path.substr(path.rfind('/') + 1));
    u.spells[i].data = it == all->end() ? nullptr : &it->second;
  }
  u.skill_points = u.level;
}

void Match::level_spell(Unit& u, int slot, MatchEvents& ev) {
  if (slot < 0 || slot > 3 || u.skill_points <= 0 || !u.spells[static_cast<size_t>(slot)].data || u.dead) return;
  SpellSlot& s = u.spells[static_cast<size_t>(slot)];
  // documented (Champion ability): the ultimate takes points at levels 6, 11 and 16, three in all; a basic ability up
  // to five, never more than half the champion's level rounded up
  const int cap = slot == 3 ? (u.level >= 16 ? 3 : u.level >= 11 ? 2 : u.level >= 6 ? 1 : 0) : std::min(5, (u.level + 1) / 2);
  if (s.level >= cap) return;
  ++s.level, --u.skill_points;
  ev.spells_changed.push_back(u.id);
}

SpellCaster Match::caster_of(const Unit& u) const {
  SpellCaster c;
  c.level = u.level;
  c.ability_haste = u.stats.ability_haste;
  const UnitStats stats = u.stats, base = u.base;
  const float hp = u.hp, max_hp = u.max_hp;
  c.stat = [stats, base, hp, max_hp](int stat, int formula) {
    auto pick = [formula](float total, float b) { return formula == kFormulaBase ? b : formula == kFormulaBonus ? total - b : total; };
    switch (stat) {
      case kStatAbilityPower: return pick(stats.ap, base.ap);
      case kStatAbilityHaste: return pick(stats.ability_haste, base.ability_haste);
      case kStatCritChance: return pick(stats.crit, base.crit);
      case kStatArmor: return pick(stats.armor, base.armor);
      case kStatAttackDamage: return pick(stats.ad, base.ad);
      case kStatAttackSpeed: return pick(stats.attack_speed, base.attack_speed);
      case kStatMagicResist: return pick(stats.spell_block, base.spell_block);
      case kStatMoveSpeed: return pick(stats.move_speed, base.move_speed);
      case kStatMaxHealth: return pick(max_hp, base.max_hp);
      case kStatCurrentHealth: return hp;
      case kStatMissingHealthPercent: return max_hp > 0 ? 1.f - hp / max_hp : 0.f;
      default: return 0.f;
    }
  };
  return c;
}

void Match::order_cast(Unit& u, const Order& o, MatchEvents& ev) {
  if (o.slot > 3 || u.dead) return;
  SpellSlot& s = u.spells[o.slot];
  if (s.data && s.level > 0 && s.recast) {
    // the spell's second cast (Zed changing places with his shadow, Lux bursting her singularity): free, at once, and
    // whatever its cooldown; the script's OnRecast does it
    if (clock.tick < s.recast_tick || has_flag(u, &Buff::stun)) return;
    Cast c;
    c.slot = o.slot, c.x = o.x, c.z = o.z, c.target = o.target;
    if (spell_hook(u, c, "OnRecast")) lua_pop(L_, 1);
    return;
  }
  if (!s.data || s.level <= 0 || clock.tick < s.ready_tick) return;
  if (u.par < s.data->mana[static_cast<size_t>(s.level)]) return;
  if (has_flag(u, &Buff::stun) || has_flag(u, &Buff::silence)) return;
  if (u.cast.slot >= 0 && !u.cast.pending) return;  // already casting
  const std::string& kind = s.data->targeting_name;
  Cast c;
  c.slot = o.slot, c.x = o.x, c.z = o.z, c.target = 0;
  const float range = s.data->range[static_cast<size_t>(s.level)];
  if (kind == "Self" || kind == "SelfAoe") {
    c.x = u.x, c.z = u.z;
  } else if (kind == "Target") {
    Unit* t = unit(o.target);
    if (!t || t->dead || t->team == u.team || structure(*t)) return;  // an enemy unit under the cursor [the scripts' spells so far]
    c.target = t->id, c.x = t->x, c.z = t->z;
    c.pending = std::hypot(t->x - u.x, t->z - u.z) > range;
  } else if (kind == "Area" || kind == "AreaClamped") {
    // a place within castRange: the caster walks into range first (documented: targeted casts out of range)
    c.pending = std::hypot(o.x - u.x, o.z - u.z) > range;
  }
  // the script may refuse (Ashe's Ranger's Focus without its four stacks): Spells[name].CanCast(cast) -> false
  if (spell_hook(u, c, "CanCast")) {
    const bool refused = lua_isboolean(L_, -1) && !lua_toboolean(L_, -1);
    lua_pop(L_, 1);
    if (refused) return;
  }
  u.cast = c;
  if (c.pending) {
    u.target = 0, u.attack_start = -1;
    path_to(u, c.x, c.z, ev);
  } else {
    begin_cast(u, ev);
  }
}

void Match::begin_cast(Unit& u, MatchEvents& ev) {
  SpellSlot& s = u.spells[static_cast<size_t>(u.cast.slot)];
  const SpellData& d = *s.data;
  const size_t rank = static_cast<size_t>(s.level);
  u.cast.pending = false;
  u.par -= d.mana[rank];
  // ability haste: the cooldown lasts 100 / (100 + haste) of itself (documented)
  s.cooldown_total = d.cooldown[rank] * 100.f / (100.f + std::max(0.f, u.stats.ability_haste));
  s.ready_tick = clock.tick + ticks(s.cooldown_total);
  ev.spells_changed.push_back(u.id), ev.stats_changed.push_back(u.id);
  ev.casts.push_back({u.id, static_cast<uint8_t>(u.cast.slot), d.name, d.animation, d.cast_time, u.cast.x, u.cast.z, u.cast.target});
  // Spellblade proc on ability cast
  if (u.kind == UnitType::Champion) {
    for (int it_id : u.items) {
      if (it_id == 3057 || it_id == 3078 || it_id == 3100 || it_id == 3508) {
        if (!find_buff(u, "Spellblade") && !find_buff(u, "SpellbladeCD")) {
          float bonus_ad = (it_id == 3078) ? 2.0f * u.base.ad : (it_id == 3508) ? 1.3f * u.base.ad + 0.2f * (u.stats.ad - u.base.ad) : (it_id == 3100) ? u.base.ad + 0.5f * u.stats.ap : u.base.ad;
          Buff b;
          b.name = "Spellblade";
          b.source = u.id;
          b.end_tick = clock.tick + ticks(10.0);
          b.ad = bonus_ad;
          u.buffs.push_back(b);
          Buff cd;
          cd.name = "SpellbladeCD";
          cd.source = u.id;
          cd.end_tick = clock.tick + ticks(1.5);
          u.buffs.push_back(cd);
          ev.buffs.push_back({u.id, "Spellblade", 10.f, true});
          ev.effects.push_back({u.id, "Sheen_buff", "BUFFBONE_WEAPON_1", 10.f, false, u.id});
          break;
        }
      }
    }
  }
  // what the script does as the cast begins (Lux's Final Spark fires a second into its cast)
  if (spell_hook(u, u.cast, "OnStart")) lua_pop(L_, 1);
  if (d.cast_time > 0) {
    // the caster stops and turns to where it casts; its attack's windup is lost
    if (!u.path.empty()) u.path.clear(), ev.path_changed.push_back(u.id);
    u.attack_start = -1;
    if (std::hypot(u.cast.x - u.x, u.cast.z - u.z) > 1.f) u.facing = std::atan2(u.cast.x - u.x, u.cast.z - u.z);
    u.cast.end_tick = clock.tick + ticks(d.cast_time);
  } else {
    finish_cast(u.id, ev);
  }
}

bool Match::spell_hook(const Unit& u, const Cast& c, const char* hook) {
  if (!L_ || c.slot < 0) return false;
  const SpellSlot& s = u.spells[static_cast<size_t>(c.slot)];
  if (!s.data) return false;
  // Spells[name].<hook>{caster, slot, rank, spell, x, z, target}
  lua_getglobal(L_, "Spells");
  lua_getfield(L_, -1, s.data->name.c_str());
  if (!lua_istable(L_, -1)) {
    lua_pop(L_, 2);
    return false;
  }
  lua_getfield(L_, -1, hook);
  if (!lua_isfunction(L_, -1)) {
    lua_pop(L_, 3);
    return false;
  }
  lua_newtable(L_);
  lua_pushnumber(L_, u.id), lua_setfield(L_, -2, "caster");
  lua_pushnumber(L_, c.slot), lua_setfield(L_, -2, "slot");
  lua_pushnumber(L_, s.level), lua_setfield(L_, -2, "rank");
  lua_pushstring(L_, s.data->name.c_str()), lua_setfield(L_, -2, "spell");
  lua_pushnumber(L_, c.x), lua_setfield(L_, -2, "x");
  lua_pushnumber(L_, c.z), lua_setfield(L_, -2, "z");
  if (c.target) lua_pushnumber(L_, c.target), lua_setfield(L_, -2, "target");
  const std::string what = s.data->name + "." + hook;
  if (!call(1, 1, what.c_str())) lua_pushnil(L_);
  // the result under the two tables: they go, it stays
  lua_remove(L_, -2);
  lua_remove(L_, -2);
  return true;
}

void Match::finish_cast(uint32_t id, MatchEvents& ev) {
  Unit* u = unit(id);
  if (!u || u->cast.slot < 0) return;
  const Cast c = u->cast;
  const Unit copy = *u;
  u->cast = Cast{};
  if (spell_hook(copy, c, "OnCast")) lua_pop(L_, 1);
  (void)ev;
}

void Match::update_casts(MatchEvents& ev) {
  for (size_t i = 0; i < units.size(); ++i) {
    Unit& u = units[i];
    if (u.cast.slot < 0) continue;
    if (u.dead || has_flag(u, &Buff::stun) || (!u.cast.pending && has_flag(u, &Buff::silence))) {
      u.cast = Cast{};  // a cast in progress is lost [de măsurat: which casts survive what]
      continue;
    }
    if (u.cast.pending) {
      const SpellSlot& s = u.spells[static_cast<size_t>(u.cast.slot)];
      const float range = s.data->range[static_cast<size_t>(s.level)];
      if (u.cast.target) {
        const Unit* t = unit(u.cast.target);
        if (!t || t->dead) {
          u.cast = Cast{};
          continue;
        }
        if (std::hypot(t->x - u.cast.x, t->z - u.cast.z) > 1.f || u.path.empty()) {
          u.cast.x = t->x, u.cast.z = t->z;
          if (std::hypot(t->x - u.x, t->z - u.z) > range) path_to(u, t->x, t->z, ev);
        }
      }
      if (std::hypot(u.cast.x - u.x, u.cast.z - u.z) <= range) begin_cast(u, ev);
      continue;
    }
    if (clock.tick >= u.cast.end_tick) finish_cast(u.id, ev);
  }
}

// ---------------------------------------------------------------- skillshots, dashes, timers

/** A champion to the spells that ask for one: a champion, or the Practice Tool's dummy (a unit of no other kind that has
 *  a record; a spell's own creatures have none). */
static bool champion_like(const Unit& u) { return u.kind == UnitType::Champion || (u.kind == UnitType::Other && u.record); }

void Match::update_skill_missiles(MatchEvents& ev) {
  const float dt = static_cast<float>(kTickSeconds);
  for (size_t i = 0; i < skill_missiles_.size();) {
    SkillMissile m = skill_missiles_[i];  // a copy: its script may launch more
    const float step = std::min(m.speed * dt, m.left);
    const float nx = m.x + m.dx * step, nz = m.z + m.dz * step;
    bool stop = false;
    // every enemy the segment walked this tick touches, nearest first
    std::vector<std::pair<float, uint32_t>> touched;
    for (const Unit& t : units) {
      if (t.dead || !t.record || t.team == m.team || structure(t)) continue;
      if (m.champions && !champion_like(t)) continue;
      if (std::find(m.hit.begin(), m.hit.end(), t.id) != m.hit.end()) continue;
      const float px = t.x - m.x, pz = t.z - m.z;
      const float along = std::clamp(px * m.dx + pz * m.dz, 0.f, step);
      const float cx = m.x + m.dx * along, cz = m.z + m.dz * along;
      if (std::hypot(t.x - cx, t.z - cz) <= m.width * 0.5f + t.stats.gameplay_radius) touched.emplace_back(along, t.id);
    }
    std::sort(touched.begin(), touched.end());
    for (const auto& [along, id] : touched) {
      m.hit.push_back(id);
      if (m.on_hit && L_) {
        lua_rawgeti(L_, LUA_REGISTRYINDEX, m.on_hit);
        lua_pushnumber(L_, id);
        if (call(1, 1, "a missile's on_hit")) {
          stop = lua_toboolean(L_, -1) != 0;
          lua_pop(L_, 1);
        }
      }
      if (stop) {
        m.x += m.dx * along, m.z += m.dz * along;
        break;
      }
    }
    if (!stop) m.x = nx, m.z = nz, m.left -= step;
    if (m.accel > 0) m.speed = std::min(m.speed_limit, m.speed + m.accel * dt);
    if (m.accel < 0) m.speed = std::max(m.speed_limit, m.speed + m.accel * dt);
    // (the script may have added missiles: this one is found again by its id)
    auto it = std::find_if(skill_missiles_.begin(), skill_missiles_.end(), [&](const SkillMissile& x) { return x.id == m.id; });
    if (it == skill_missiles_.end()) continue;
    if (stop || m.left <= 0) {
      ev.skill_missiles_ended.push_back(m.id);
      const int on_end = m.on_end, on_hit = m.on_hit;
      const float ex = m.x, ez = m.z;
      skill_missiles_.erase(it);
      if (on_end && L_) {
        lua_rawgeti(L_, LUA_REGISTRYINDEX, on_end);
        lua_pushnumber(L_, ex), lua_pushnumber(L_, ez);
        call(2, 0, "a missile's on_end");
      }
      for (int ref : {on_hit, on_end})
        if (ref && L_) luaL_unref(L_, LUA_REGISTRYINDEX, ref);
      continue;  // the next missile slid into place
    }
    *it = m;
    i = static_cast<size_t>(it - skill_missiles_.begin()) + 1;
  }
}

void Match::run_timers(MatchEvents& ev) {
  (void)ev;
  // those due, in the order they were set (a timer may set more: they wait for the next pass)
  for (;;) {
    size_t best = timers_.size();
    for (size_t i = 0; i < timers_.size(); ++i)
      if (timers_[i].tick <= clock.tick && (best == timers_.size() || timers_[i].seq < timers_[best].seq)) best = i;
    if (best == timers_.size()) break;
    const int ref = timers_[best].ref;
    timers_.erase(timers_.begin() + static_cast<std::ptrdiff_t>(best));
    if (!L_) continue;
    lua_rawgeti(L_, LUA_REGISTRYINDEX, ref);
    call(0, 0, "a timer");
    luaL_unref(L_, LUA_REGISTRYINDEX, ref);
  }
}

void Match::champion_ticks(MatchEvents& ev) {
  (void)ev;
  if (!L_ || clock.tick % ticks(0.25) != 0) return;
  // Champions[name].OnTick(unit) four times a second (passives)
  std::vector<std::pair<uint32_t, std::string>> champions;
  for (const Unit& u : units)
    if (u.kind == UnitType::Champion && !u.dead) champions.emplace_back(u.id, u.skin);
  for (const auto& [id, name] : champions) {
    lua_getglobal(L_, "Champions");
    lua_getfield(L_, -1, name.c_str());
    if (lua_istable(L_, -1)) {
      lua_getfield(L_, -1, "OnTick");
      if (lua_isfunction(L_, -1)) {
        lua_pushnumber(L_, id);
        call(1, 0, "OnTick");
      } else {
        lua_pop(L_, 1);
      }
    }
    lua_pop(L_, 2);
  }
}

void Match::champion_hook(uint32_t id, const char* hook, uint32_t other, bool flag, float amount) {
  const Unit* u = unit(id);
  if (!L_ || !u) return;
  lua_getglobal(L_, "Champions");
  lua_getfield(L_, -1, u->skin.c_str());
  if (lua_istable(L_, -1)) {
    lua_getfield(L_, -1, hook);
    if (lua_isfunction(L_, -1)) {
      lua_pushnumber(L_, id), lua_pushnumber(L_, other), lua_pushboolean(L_, flag), lua_pushnumber(L_, amount);
      call(4, 0, hook);
    } else {
      lua_pop(L_, 1);
    }
  }
  lua_pop(L_, 2);
}

float Match::attack_bonus(uint32_t attacker, uint32_t target) {
  // each buff with an on_attack hook: on_attack(target) -> bonus physical damage for this attack, and whether the buff
  // was used up
  float bonus = 0;
  if (!L_) return 0;
  for (size_t i = 0;;) {
    Unit* u = unit(attacker);
    if (!u || i >= u->buffs.size()) break;
    const Buff b = u->buffs[i];
    if (!b.on_attack) {
      ++i;
      continue;
    }
    lua_rawgeti(L_, LUA_REGISTRYINDEX, b.on_attack);
    lua_pushnumber(L_, target);
    bool used = false;
    if (call(1, 2, "a buff's on_attack")) {
      bonus += static_cast<float>(lua_tonumber(L_, -2));
      used = lua_toboolean(L_, -1) != 0;
      lua_pop(L_, 2);
    }
    u = unit(attacker);
    if (!u) break;
    // (the hook may have changed the buffs: this one is found again by its name)
    size_t at = u->buffs.size();
    for (size_t k = 0; k < u->buffs.size(); ++k)
      if (u->buffs[k].name == b.name && u->buffs[k].on_attack == b.on_attack) at = k;
    if (used && at < u->buffs.size() && ev_) {
      remove_buff(*u, at, false, *ev_);
      i = at;
    } else {
      i = at < u->buffs.size() ? at + 1 : i + 1;
    }
  }
  return bonus;
}

// ---------------------------------------------------------------- Lua

bool Match::call(int args, int results, const char* what) {
  if (lua_pcall(L_, args, results, 0) == 0) return true;
  std::fprintf(stderr, "script error in %s: %s\n", what, lua_tostring(L_, -1));
  lua_pop(L_, 1);
  return false;
}

void Match::run_ref(int ref) {
  if (!L_ || !ref) return;
  lua_rawgeti(L_, LUA_REGISTRYINDEX, ref);
  call(0, 0, "a dash's end");
  luaL_unref(L_, LUA_REGISTRYINDEX, ref);
}

/** The functions the scripts call. Units are their ids. */
struct LuaApi {
  static Match& match(lua_State* L) { return *static_cast<Match*>(lua_touserdata(L, lua_upvalueindex(1))); }
  static Unit* unit(lua_State* L, int arg) { return match(L).unit(static_cast<uint32_t>(lua_tonumber(L, arg))); }
  static float num(lua_State* L, int table, const char* field, float dflt = 0) {
    lua_getfield(L, table, field);
    const float v = lua_isnumber(L, -1) ? static_cast<float>(lua_tonumber(L, -1)) : dflt;
    lua_pop(L, 1);
    return v;
  }
  static bool flag(lua_State* L, int table, const char* field) {
    lua_getfield(L, table, field);
    const bool v = lua_toboolean(L, -1) != 0;
    lua_pop(L, 1);
    return v;
  }
  static int ref(lua_State* L, int table, const char* field) {
    lua_getfield(L, table, field);
    if (lua_isfunction(L, -1)) return luaL_ref(L, LUA_REGISTRYINDEX);
    lua_pop(L, 1);
    return 0;
  }

  // ---- what a unit is, where, how strong
  static int Exists(lua_State* L) { return lua_pushboolean(L, unit(L, 1) != nullptr), 1; }
  static int Team(lua_State* L) {
    const Unit* u = unit(L, 1);
    return lua_pushnumber(L, u ? u->team : -1), 1;
  }
  static int IsChampion(lua_State* L) {
    const Unit* u = unit(L, 1);
    return lua_pushboolean(L, u && champion_like(*u)), 1;
  }
  static int IsMinion(lua_State* L) {
    const Unit* u = unit(L, 1);
    return lua_pushboolean(L, u && u->kind == UnitType::Minion), 1;
  }
  static int IsDead(lua_State* L) {
    const Unit* u = unit(L, 1);
    return lua_pushboolean(L, !u || u->dead), 1;
  }
  static int Pos(lua_State* L) {
    const Unit* u = unit(L, 1);
    lua_pushnumber(L, u ? u->x : 0), lua_pushnumber(L, u ? u->z : 0);
    return 2;
  }
  static int Facing(lua_State* L) {
    const Unit* u = unit(L, 1);
    return lua_pushnumber(L, u ? u->facing : 0), 1;
  }
  static int Distance(lua_State* L) {
    const Unit* a = unit(L, 1);
    const Unit* b = unit(L, 2);
    return lua_pushnumber(L, a && b ? std::hypot(a->x - b->x, a->z - b->z) : 1e9), 1;
  }
  static int Level(lua_State* L) {
    const Unit* u = unit(L, 1);
    return lua_pushnumber(L, u ? u->level : 0), 1;
  }
  static int Rank(lua_State* L) {
    const Unit* u = unit(L, 1);
    const int slot = static_cast<int>(lua_tonumber(L, 2));
    return lua_pushnumber(L, u && slot >= 0 && slot < 4 ? u->spells[static_cast<size_t>(slot)].level : 0), 1;
  }
  static int HP(lua_State* L) {
    const Unit* u = unit(L, 1);
    return lua_pushnumber(L, u ? u->hp : 0), 1;
  }
  static int MaxHP(lua_State* L) {
    const Unit* u = unit(L, 1);
    return lua_pushnumber(L, u ? u->max_hp : 0), 1;
  }
  static int Stat(lua_State* L) {
    const Unit* u = unit(L, 1);
    const std::string n = luaL_checkstring(L, 2);
    float v = 0;
    if (u) {
      const UnitStats& s = u->stats;
      const UnitStats& b = u->base;
      v = n == "ad" ? s.ad : n == "bonus_ad" ? s.ad - b.ad : n == "base_ad" ? b.ad : n == "armor" ? s.armor : n == "bonus_armor" ? s.armor - b.armor
          : n == "mr" ? s.spell_block : n == "bonus_mr" ? s.spell_block - b.spell_block : n == "as" ? s.attack_speed
          : n == "bonus_as" ? (u->record && u->record->attack_speed_ratio > 0 ? (s.attack_speed - u->record->attack_speed) / u->record->attack_speed_ratio : 0.f)
          : n == "ms" ? s.move_speed : n == "range" ? s.attack_range : n == "radius" ? s.gameplay_radius : n == "crit" ? s.crit : 0.f;
    }
    return lua_pushnumber(L, v), 1;
  }
  static int SinceHurt(lua_State* L) {
    const Unit* u = unit(L, 1);
    const Match& m = match(L);
    return lua_pushnumber(L, u && u->last_hurt_tick >= 0 ? static_cast<double>(m.clock.tick - u->last_hurt_tick) * kTickSeconds : 1e9), 1;
  }
  static int Now(lua_State* L) { return lua_pushnumber(L, match(L).game_seconds()), 1; }
  static int Random(lua_State* L) { return lua_pushnumber(L, match(L).random.unit()), 1; }

  // ---- a spell's numbers: Value(unit, spell, name [, rank]), Calc(unit, spell, name [, rank])
  static const SpellData* spell(lua_State* L, const Unit* u, int& rank) {
    if (!u || !u->spell_set) return nullptr;
    auto it = u->spell_set->find(luaL_checkstring(L, 2));
    if (it == u->spell_set->end()) return nullptr;
    rank = lua_isnumber(L, 4) ? static_cast<int>(lua_tonumber(L, 4)) : 1;
    if (!lua_isnumber(L, 4))
      for (const SpellSlot& s : u->spells)
        if (s.data == &it->second) rank = std::max(1, s.level);
    return &it->second;
  }
  static int Value(lua_State* L) {
    const Unit* u = unit(L, 1);
    int rank = 1;
    const SpellData* s = spell(L, u, rank);
    bool known = false;
    const float v = s ? spell_value(*s, spell_name_hash(luaL_checkstring(L, 3)), rank, &known) : 0.f;
    if (!s) std::fprintf(stderr, "script: no spell %s\n", lua_tostring(L, 2));
    else if (!known) std::fprintf(stderr, "script: %s has no value %s\n", s->name.c_str(), lua_tostring(L, 3));
    return lua_pushnumber(L, v), 1;
  }
  /** EffectValue(unit, spell, index [, rank]): the spell's mEffectAmount of that index (from 1) at its rank. */
  static int EffectValue(lua_State* L) {
    const Unit* u = unit(L, 1);
    int rank = 1;
    const SpellData* s = spell(L, u, rank);
    const int i = static_cast<int>(luaL_checknumber(L, 3));
    if (lua_isnumber(L, 5)) rank = static_cast<int>(lua_tonumber(L, 5));
    if (!s || i < 1 || static_cast<size_t>(i) > s->effects.size()) {
      std::fprintf(stderr, "script: %s has no effect amount %d\n", lua_tostring(L, 2), i);
      return lua_pushnumber(L, 0), 1;
    }
    return lua_pushnumber(L, s->effects[static_cast<size_t>(i - 1)][static_cast<size_t>(std::clamp(rank, 0, 6))]), 1;
  }
  static int Calc(lua_State* L) {
    const Unit* u = unit(L, 1);
    int rank = 1;
    const SpellData* s = spell(L, u, rank);
    bool known = false;
    const float v = s ? spell_calc(*s, luaL_checkstring(L, 3), rank, match(L).caster_of(*u), &known) : 0.f;
    if (s && !known) std::fprintf(stderr, "script: %s has no calculation %s\n", s->name.c_str(), lua_tostring(L, 3));
    return lua_pushnumber(L, v), 1;
  }
  /** SpellInfo(unit, spell, what): "range", "radius", "speed", "accel", "speed_limit", "width" (the whole width: twice
   *  the files' number), "cone", "cooldown", "cast" (its cast time) from the spell's data. */
  static int SpellInfo(lua_State* L) {
    const Unit* u = unit(L, 1);
    int rank = 1;
    const SpellData* s = spell(L, u, rank);
    const std::string what = luaL_checkstring(L, 3);
    const size_t r = static_cast<size_t>(std::clamp(rank, 0, 6));
    return lua_pushnumber(L, !s ? 0 : what == "range" ? s->range[r] : what == "radius" ? s->radius[r] : what == "speed" ? s->missile_speed
                                : what == "width" ? s->line_width * 2 : what == "cone" ? s->cone_angle : what == "cooldown" ? s->cooldown[r]
                                : what == "accel" ? s->missile_accel : what == "speed_limit" ? s->missile_speed_limit : what == "cast" ? s->cast_time : 0), 1;
  }

  // ---- Damage(source, target, amount, "physical" | "magic" | "true" [, spell]) -> what it took
  static int Damage(lua_State* L) {
    Match& m = match(L);
    Unit* s = unit(L, 1);
    Unit* t = unit(L, 2);
    if (!s || !t || !m.ev_) return lua_pushnumber(L, 0), 1;
    const std::string kind = luaL_optstring(L, 4, "physical");
    const DamageType type = kind == "magic" ? DamageType::Magic : kind == "true" ? DamageType::True : DamageType::Physical;
    return lua_pushnumber(L, m.spell_damage(*s, *t, static_cast<float>(lua_tonumber(L, 3)), type, luaL_optstring(L, 5, ""), *m.ev_)), 1;
  }
  static int Heal(lua_State* L) {
    Match& m = match(L);
    Unit* u = unit(L, 1);
    if (!u || u->dead || !m.ev_) return 0;
    u->hp = std::min(u->max_hp, u->hp + static_cast<float>(lua_tonumber(L, 2)));
    m.ev_->damage.push_back({u->id, 0.f, u->hp, u->max_hp});
    return 0;
  }

  // ---- AddBuff(unit, {name =, source =, duration =, move_speed =, attack_speed =, ad =, armor =, mr =, armor_pct =,
  //      mr_pct =, damage_taken =, shield =, stun =, root =, silence =, disarm =, on_attack = fn, on_expire = fn})
  //      a buff of the same name is replaced
  static int AddBuff(lua_State* L) {
    Match& m = match(L);
    const uint32_t id = static_cast<uint32_t>(lua_tonumber(L, 1));
    luaL_checktype(L, 2, LUA_TTABLE);
    Unit* u = m.unit(id);
    if (!u || u->dead || !m.ev_) return 0;
    Buff b;
    lua_getfield(L, 2, "name");
    b.name = luaL_optstring(L, -1, "buff");
    lua_pop(L, 1);
    b.source = static_cast<uint32_t>(num(L, 2, "source"));
    float duration = num(L, 2, "duration", -1);
    b.stacks = static_cast<int>(num(L, 2, "stacks", 1));
    b.move_speed_pct = num(L, 2, "move_speed"), b.attack_speed_pct = num(L, 2, "attack_speed");
    b.ad = num(L, 2, "ad"), b.armor = num(L, 2, "armor"), b.spell_block = num(L, 2, "mr");
    b.armor_pct = num(L, 2, "armor_pct"), b.spell_block_pct = num(L, 2, "mr_pct");
    b.damage_taken_pct = num(L, 2, "damage_taken");
    if (b.damage_taken_pct == 0) b.damage_taken_pct = num(L, 2, "damage_taken_pct");
    b.shield = num(L, 2, "shield");
    b.crit = num(L, 2, "crit"), b.min_hp = num(L, 2, "min_hp");
    b.tenacity = num(L, 2, "tenacity");
    b.stun = flag(L, 2, "stun"), b.root = flag(L, 2, "root"), b.silence = flag(L, 2, "silence"), b.disarm = flag(L, 2, "disarm");
    b.untargetable = flag(L, 2, "untargetable"), b.invulnerable = flag(L, 2, "invulnerable");
    b.on_attack = ref(L, 2, "on_attack"), b.on_expire = ref(L, 2, "on_expire");

    // Crowd control duration reduced by target tenacity
    if (duration > 0 && (b.stun || b.root || b.silence || b.move_speed_pct < 0)) {
      const float ten = std::clamp(u->stats.tenacity, 0.f, 0.90f);
      if (ten > 0) duration *= (1.f - ten);
    }
    b.end_tick = duration >= 0 ? m.clock.tick + ticks(duration) : -1;
    for (size_t i = 0; i < u->buffs.size(); ++i)
      if (u->buffs[i].name == b.name) {
        // replaced without its on_expire: it goes on
        const Buff old = u->buffs[i];
        u->buffs.erase(u->buffs.begin() + static_cast<std::ptrdiff_t>(i));
        for (int r : {old.on_attack, old.on_expire})
          if (r) luaL_unref(L, LUA_REGISTRYINDEX, r);
        break;
      }
    u->buffs.push_back(b);
    if (b.stun || b.root) {
      if (!u->path.empty()) u->path.clear(), m.ev_->path_changed.push_back(id);
    }
    if (b.stun) u->attack_start = -1;
    m.refresh_stats(*u, m.ev_);
    m.ev_->buffs.push_back({id, b.name, duration, true});
    return 0;
  }
  static int HasBuff(lua_State* L) {
    Unit* u = unit(L, 1);
    return lua_pushboolean(L, u && match(L).find_buff(*u, luaL_checkstring(L, 2)) != nullptr), 1;
  }
  static int BuffStacks(lua_State* L) {
    Unit* u = unit(L, 1);
    const Buff* b = u ? match(L).find_buff(*u, luaL_checkstring(L, 2)) : nullptr;
    return lua_pushnumber(L, b ? b->stacks : 0), 1;
  }
  static int BuffTime(lua_State* L) {
    Unit* u = unit(L, 1);
    Match& m = match(L);
    const Buff* b = u ? m.find_buff(*u, luaL_checkstring(L, 2)) : nullptr;
    return lua_pushnumber(L, b && b->end_tick >= 0 ? static_cast<double>(b->end_tick - m.clock.tick) * kTickSeconds : 0), 1;
  }
  static int RemoveBuff(lua_State* L) {
    Match& m = match(L);
    Unit* u = unit(L, 1);
    if (!u || !m.ev_) return 0;
    const std::string name = luaL_checkstring(L, 2);
    for (size_t i = 0; i < u->buffs.size(); ++i)
      if (u->buffs[i].name == name) {
        m.remove_buff(*u, i, false, *m.ev_);
        break;
      }
    return 0;
  }
  /** RemoveSlows(unit): Garen's Decisive Strike and the like. */
  static int RemoveSlows(lua_State* L) {
    Match& m = match(L);
    const uint32_t id = static_cast<uint32_t>(lua_tonumber(L, 1));
    for (size_t i = 0;;) {
      Unit* u = m.unit(id);
      if (!u || i >= u->buffs.size() || !m.ev_) break;
      if (u->buffs[i].move_speed_pct < 0) m.remove_buff(*u, i, false, *m.ev_);
      else ++i;
    }
    return 0;
  }

  // ---- Enemies(unit, x, z, radius [, champions_only]) -> the living enemy units (not structures) whose edge is within
  //      the radius, nearest first
  static int Enemies(lua_State* L) {
    Match& m = match(L);
    const Unit* u = unit(L, 1);
    const float x = static_cast<float>(lua_tonumber(L, 2)), z = static_cast<float>(lua_tonumber(L, 3)), r = static_cast<float>(lua_tonumber(L, 4));
    const bool champions = lua_toboolean(L, 5) != 0;
    std::vector<std::pair<float, uint32_t>> found;
    if (u)
      for (const Unit& t : m.units) {
        if (t.dead || !t.record || t.team == u->team || structure(t)) continue;
        if (champions && !champion_like(t)) continue;
        const float d = std::hypot(t.x - x, t.z - z);
        if (d <= r + t.stats.gameplay_radius) found.emplace_back(d, t.id);
      }
    std::sort(found.begin(), found.end());
    lua_newtable(L);
    for (size_t i = 0; i < found.size(); ++i) lua_pushnumber(L, found[i].second), lua_rawseti(L, -2, static_cast<int>(i + 1));
    return 1;
  }

  // ---- EnemiesInLine(unit, x0, z0, x1, z1, width [, champions_only]) -> the living enemy units a line of that width
  //      touches, nearest to its start first
  static int EnemiesInLine(lua_State* L) {
    Match& m = match(L);
    const Unit* u = unit(L, 1);
    const float x0 = static_cast<float>(lua_tonumber(L, 2)), z0 = static_cast<float>(lua_tonumber(L, 3));
    const float x1 = static_cast<float>(lua_tonumber(L, 4)), z1 = static_cast<float>(lua_tonumber(L, 5)), width = static_cast<float>(lua_tonumber(L, 6));
    const bool champions = lua_toboolean(L, 7) != 0;
    const float len = std::hypot(x1 - x0, z1 - z0), dx = len > 0 ? (x1 - x0) / len : 0, dz = len > 0 ? (z1 - z0) / len : 1;
    std::vector<std::pair<float, uint32_t>> found;
    if (u)
      for (const Unit& t : m.units) {
        if (t.dead || !t.record || t.team == u->team || structure(t)) continue;
        if (champions && !champion_like(t)) continue;
        const float along = std::clamp((t.x - x0) * dx + (t.z - z0) * dz, 0.f, len);
        if (std::hypot(t.x - (x0 + dx * along), t.z - (z0 + dz * along)) <= width * 0.5f + t.stats.gameplay_radius) found.emplace_back(along, t.id);
      }
    std::sort(found.begin(), found.end());
    lua_newtable(L);
    for (size_t i = 0; i < found.size(); ++i) lua_pushnumber(L, found[i].second), lua_rawseti(L, -2, static_cast<int>(i + 1));
    return 1;
  }

  static int Allies(lua_State* L) {
    Match& m = match(L);
    const Unit* u = unit(L, 1);
    const float x = static_cast<float>(lua_tonumber(L, 2)), z = static_cast<float>(lua_tonumber(L, 3)), r = static_cast<float>(lua_tonumber(L, 4));
    const bool champions = lua_isboolean(L, 5) ? (lua_toboolean(L, 5) != 0) : true;
    std::vector<std::pair<float, uint32_t>> found;
    if (u)
      for (const Unit& t : m.units) {
        if (t.dead || !t.record || t.team != u->team || structure(t)) continue;
        if (champions && !champion_like(t)) continue;
        const float d = std::hypot(t.x - x, t.z - z);
        if (d <= r + t.stats.gameplay_radius) found.emplace_back(d, t.id);
      }
    std::sort(found.begin(), found.end());
    lua_newtable(L);
    for (size_t i = 0; i < found.size(); ++i) lua_pushnumber(L, found[i].second), lua_rawseti(L, -2, static_cast<int>(i + 1));
    return 1;
  }

  static int AlliesInLine(lua_State* L) {
    Match& m = match(L);
    const Unit* u = unit(L, 1);
    const float x0 = static_cast<float>(lua_tonumber(L, 2)), z0 = static_cast<float>(lua_tonumber(L, 3));
    const float x1 = static_cast<float>(lua_tonumber(L, 4)), z1 = static_cast<float>(lua_tonumber(L, 5)), width = static_cast<float>(lua_tonumber(L, 6));
    const bool champions = lua_isboolean(L, 7) ? (lua_toboolean(L, 7) != 0) : true;
    const float len = std::hypot(x1 - x0, z1 - z0), dx = len > 0 ? (x1 - x0) / len : 0, dz = len > 0 ? (z1 - z0) / len : 1;
    std::vector<std::pair<float, uint32_t>> found;
    if (u)
      for (const Unit& t : m.units) {
        if (t.dead || !t.record || t.team != u->team || structure(t)) continue;
        if (champions && !champion_like(t)) continue;
        const float along = std::clamp((t.x - x0) * dx + (t.z - z0) * dz, 0.f, len);
        if (std::hypot(t.x - (x0 + dx * along), t.z - (z0 + dz * along)) <= width * 0.5f + t.stats.gameplay_radius) found.emplace_back(along, t.id);
      }
    std::sort(found.begin(), found.end());
    lua_newtable(L);
    for (size_t i = 0; i < found.size(); ++i) lua_pushnumber(L, found[i].second), lua_rawseti(L, -2, static_cast<int>(i + 1));
    return 1;
  }

  static int IsRooted(lua_State* L) {
    const Unit* u = unit(L, 1);
    return lua_pushboolean(L, u && match(L).has_flag(*u, &Buff::root)), 1;
  }
  static int IsStunned(lua_State* L) {
    const Unit* u = unit(L, 1);
    return lua_pushboolean(L, u && match(L).has_flag(*u, &Buff::stun)), 1;
  }
  static int IsSilenced(lua_State* L) {
    const Unit* u = unit(L, 1);
    return lua_pushboolean(L, u && match(L).has_flag(*u, &Buff::silence)), 1;
  }

  // ---- the ability resource: Resource(unit), MaxResource(unit), AddResource(unit, amount)
  static int Resource(lua_State* L) {
    const Unit* u = unit(L, 1);
    return lua_pushnumber(L, u ? u->par : 0), 1;
  }
  static int MaxResource(lua_State* L) {
    const Unit* u = unit(L, 1);
    return lua_pushnumber(L, u ? u->max_par : 0), 1;
  }
  static int AddResource(lua_State* L) {
    Match& m = match(L);
    Unit* u = unit(L, 1);
    if (!u || !m.ev_) return 0;
    u->par = std::clamp(u->par + static_cast<float>(lua_tonumber(L, 2)), 0.f, u->max_par);
    m.ev_->stats_changed.push_back(u->id);
    return 0;
  }
  /** SinceFight(unit): seconds since it last dealt or took damage. */
  static int SinceFight(lua_State* L) {
    const Unit* u = unit(L, 1);
    const Match& m = match(L);
    return lua_pushnumber(L, u && u->last_fight_tick >= 0 ? static_cast<double>(m.clock.tick - u->last_fight_tick) * kTickSeconds : 1e9), 1;
  }

  // ---- SpawnUnit(owner, character, x, z [, seconds]) -> the id of a creature of the owner's (Zed's shadow): it
  //      stands where it is put, cannot be attacked, and leaves after `seconds`; RemoveUnit(id); Owner(id)
  static int SpawnUnit(lua_State* L) {
    Match& m = match(L);
    const Unit* o = unit(L, 1);
    if (!o || !m.ev_) return lua_pushnumber(L, 0), 1;
    const uint8_t team = o->team;
    const uint32_t owner = o->id;
    const float facing = o->facing;
    Unit& u = m.spawn(team, luaL_checkstring(L, 2), static_cast<float>(lua_tonumber(L, 3)), static_cast<float>(lua_tonumber(L, 4)));
    u.kind = UnitType::Other, u.owner = owner, u.facing = facing;
    if (lua_isnumber(L, 5)) u.remove_tick = m.clock.tick + ticks(lua_tonumber(L, 5));
    m.ev_->spawned.push_back(u.id);
    return lua_pushnumber(L, u.id), 1;
  }
  static int RemoveUnit(lua_State* L) {
    Unit* u = unit(L, 1);
    if (u && u->kind == UnitType::Other) u->remove_tick = match(L).clock.tick;
    return 0;
  }
  static int SetFacing(lua_State* L) {
    Unit* u = unit(L, 1);
    if (u) u->facing = std::atan2(static_cast<float>(lua_tonumber(L, 2)) - u->x, static_cast<float>(lua_tonumber(L, 3)) - u->z);
    return 0;
  }

  // ---- After(seconds, fn)
  static int After(lua_State* L) {
    Match& m = match(L);
    luaL_checktype(L, 2, LUA_TFUNCTION);
    lua_pushvalue(L, 2);
    m.timers_.push_back({m.clock.tick + ticks(lua_tonumber(L, 1)), m.timer_seq_++, luaL_ref(L, LUA_REGISTRYINDEX)});
    return 0;
  }

  // ---- Missile{source =, spell =, x =, z = (start; the source's place by default), tx =, tz = (toward), speed =,
  //      range =, width = (the whole width), accel =, speed_limit =, champions = (only they meet it), effect = (a key
  //      of the source's skin), on_hit = fn(target) -> true to stop, on_end = fn(x, z)} -> its id
  static int Missile(lua_State* L) {
    Match& m = match(L);
    luaL_checktype(L, 1, LUA_TTABLE);
    const Unit* s = m.unit(static_cast<uint32_t>(num(L, 1, "source")));
    if (!s || !m.ev_) return lua_pushnumber(L, 0), 1;
    Match::SkillMissile k;
    k.id = m.next_missile_id_++;
    k.source = s->id, k.team = s->team;
    k.x = num(L, 1, "x", s->x), k.z = num(L, 1, "z", s->z);
    const float tx = num(L, 1, "tx", k.x), tz = num(L, 1, "tz", k.z + 1);
    const float len = std::hypot(tx - k.x, tz - k.z);
    k.dx = len > 1e-3f ? (tx - k.x) / len : std::sin(s->facing), k.dz = len > 1e-3f ? (tz - k.z) / len : std::cos(s->facing);
    k.speed = std::max(1.f, num(L, 1, "speed", 1000)), k.left = num(L, 1, "range", 1000), k.width = num(L, 1, "width", 0);
    k.accel = num(L, 1, "accel"), k.speed_limit = std::max(1.f, num(L, 1, "speed_limit", k.speed));
    k.on_hit = ref(L, 1, "on_hit"), k.on_end = ref(L, 1, "on_end");
    k.champions = flag(L, 1, "champions");
    lua_getfield(L, 1, "spell");
    const std::string spell = luaL_optstring(L, -1, "");
    lua_pop(L, 1);
    lua_getfield(L, 1, "effect");
    const std::string effect = luaL_optstring(L, -1, "");
    lua_pop(L, 1);
    m.skill_missiles_.push_back(k);
    m.ev_->skill_missiles.push_back({k.id, k.source, spell, k.x, k.z, k.dx, k.dz, k.speed, k.left, effect, k.accel, k.speed_limit});
    return lua_pushnumber(L, k.id), 1;
  }

  // ---- Dash(unit, x, z, speed [, fn at the end]); Blink(unit, x, z)
  static int Dash(lua_State* L) {
    Match& m = match(L);
    Unit* u = unit(L, 1);
    if (!u || !m.ev_) return 0;
    if (u->dash.on_end) luaL_unref(L, LUA_REGISTRYINDEX, u->dash.on_end);
    u->dash = {};
    u->dash.active = true;
    u->dash.x = static_cast<float>(lua_tonumber(L, 2)), u->dash.z = static_cast<float>(lua_tonumber(L, 3));
    u->dash.speed = std::max(1.f, static_cast<float>(lua_tonumber(L, 4)));
    if (lua_isfunction(L, 5)) lua_pushvalue(L, 5), u->dash.on_end = luaL_ref(L, LUA_REGISTRYINDEX);
    u->path.clear();
    u->attack_start = -1;
    if (std::hypot(u->dash.x - u->x, u->dash.z - u->z) > 1.f) u->facing = std::atan2(u->dash.x - u->x, u->dash.z - u->z);
    m.ev_->dashes.push_back({u->id, u->dash.x, u->dash.z, u->dash.speed});
    return 0;
  }
  static int Blink(lua_State* L) {
    Match& m = match(L);
    Unit* u = unit(L, 1);
    if (!u || !m.ev_) return 0;
    u->x = static_cast<float>(lua_tonumber(L, 2)), u->z = static_cast<float>(lua_tonumber(L, 3));
    u->path.clear();
    m.ev_->dashes.push_back({u->id, u->x, u->z, 0.f});
    return 0;
  }
  /** A walkable point at most `range` from the unit toward (x, z): where a dash may end. */
  static int ClampWalkable(lua_State* L) {
    Match& m = match(L);
    const Unit* u = unit(L, 1);
    float x = static_cast<float>(lua_tonumber(L, 2)), z = static_cast<float>(lua_tonumber(L, 3));
    const float range = static_cast<float>(lua_tonumber(L, 4));
    if (u) {
      const float d = std::hypot(x - u->x, z - u->z);
      if (d > range && d > 0) x = u->x + (x - u->x) / d * range, z = u->z + (z - u->z) / d * range;
      // back along the line until the ground can be stood on
      if (m.nav_)
        for (int i = 0; i < 40 && !m.nav_->walkable_at(x, z, u->pathfinding_radius); ++i) x += (u->x - x) * 0.1f, z += (u->z - z) * 0.1f;
    }
    lua_pushnumber(L, x), lua_pushnumber(L, z);
    return 2;
  }

  // ---- cooldowns and attacks
  static int SetCooldown(lua_State* L) {
    Match& m = match(L);
    Unit* u = unit(L, 1);
    const int slot = static_cast<int>(lua_tonumber(L, 2));
    if (!u || slot < 0 || slot > 3 || !m.ev_) return 0;
    const double seconds = std::max(0.0, lua_tonumber(L, 3));
    SpellSlot& s = u->spells[static_cast<size_t>(slot)];
    s.ready_tick = seconds > 0 ? m.clock.tick + ticks(seconds) : m.clock.tick;
    s.cooldown_total = std::max(s.cooldown_total, static_cast<float>(seconds));
    m.ev_->spells_changed.push_back(u->id);
    return 0;
  }
  /** SetRecast(unit, slot, on [, seconds until it may be used]): while on, casting the spell again calls its OnRecast
   *  (no cost, no cast time, whatever its cooldown). */
  static int SetRecast(lua_State* L) {
    Match& m = match(L);
    Unit* u = unit(L, 1);
    const int slot = static_cast<int>(lua_tonumber(L, 2));
    if (!u || slot < 0 || slot > 3) return 0;
    SpellSlot& s = u->spells[static_cast<size_t>(slot)];
    s.recast = lua_toboolean(L, 3) != 0;
    s.recast_tick = m.clock.tick + ticks(luaL_optnumber(L, 4, 0));
    return 0;
  }
  static int Cooldown(lua_State* L) {
    const Unit* u = unit(L, 1);
    const int slot = static_cast<int>(lua_tonumber(L, 2));
    const Match& m = match(L);
    return lua_pushnumber(L, u && slot >= 0 && slot < 4 ? std::max<double>(0, static_cast<double>(u->spells[static_cast<size_t>(slot)].ready_tick - m.clock.tick) * kTickSeconds) : 0), 1;
  }
  static int ResetAttack(lua_State* L) {
    Unit* u = unit(L, 1);
    if (u) u->next_attack = match(L).clock.tick, u->attack_start = -1;
    return 0;
  }
  /** AttackOrder(unit, target): the unit goes for the target with its attacks. */
  static int AttackOrder(lua_State* L) {
    Unit* u = unit(L, 1);
    const Unit* t = unit(L, 2);
    if (u && t) u->target = t->id, u->target_x = t->x + 1e9f;
    return 0;
  }

  // ---- what the clients show: Effect(unit, key [, bone [, seconds [, owner]]]) starts an effect on the unit, of
  //      the owner's skin (the unit's own by default; a hit effect is the caster's); seconds: it is stopped after
  //      that long (none: it plays out); StopEffect(unit, key); Animate(unit, clip [, seconds]) plays a clip of the
  //      unit's graph
  static int Effect(lua_State* L) {
    Match& m = match(L);
    const Unit* u = unit(L, 1);
    if (u && m.ev_)
      m.ev_->effects.push_back({u->id, luaL_checkstring(L, 2), luaL_optstring(L, 3, ""), static_cast<float>(luaL_optnumber(L, 4, 0)), false,
                                lua_isnumber(L, 5) ? static_cast<uint32_t>(lua_tonumber(L, 5)) : u->id});
    return 0;
  }
  static int StopEffect(lua_State* L) {
    Match& m = match(L);
    const Unit* u = unit(L, 1);
    if (u && m.ev_) m.ev_->effects.push_back({u->id, luaL_checkstring(L, 2), "", 0.f, true, u->id});
    return 0;
  }
  /** EffectAt(owner, key, x, z [, seconds [, toward x, toward z [, height]]]) -> its id: an effect of the owner's skin
   *  at a place, that high over the ground, facing the place it is turned toward (the owner's way unless told; its
   *  beams reach that place); StopEffectAt(id). */
  static int EffectAt(lua_State* L) {
    Match& m = match(L);
    const Unit* u = unit(L, 1);
    if (!u || !m.ev_) return lua_pushnumber(L, 0), 1;
    const float x = static_cast<float>(luaL_checknumber(L, 3)), z = static_cast<float>(luaL_checknumber(L, 4));
    float tx = x + std::sin(u->facing), tz = z + std::cos(u->facing);
    if (lua_isnumber(L, 6) && lua_isnumber(L, 7)) tx = static_cast<float>(lua_tonumber(L, 6)), tz = static_cast<float>(lua_tonumber(L, 7));
    const uint32_t id = m.next_ground_effect_++;
    m.ev_->ground_effects.push_back({id, false, u->id, luaL_checkstring(L, 2), x, z, tx, tz, static_cast<float>(luaL_optnumber(L, 5, 0)),
                                     static_cast<float>(luaL_optnumber(L, 8, 0))});
    return lua_pushnumber(L, id), 1;
  }
  static int StopEffectAt(lua_State* L) {
    Match& m = match(L);
    if (m.ev_) m.ev_->ground_effects.push_back({static_cast<uint32_t>(luaL_checknumber(L, 1)), true, 0, "", 0, 0, 0, 1, 0, 0});
    return 0;
  }
  static int Animate(lua_State* L) {
    Match& m = match(L);
    const Unit* u = unit(L, 1);
    if (u && m.ev_) m.ev_->animations.push_back({u->id, luaL_checkstring(L, 2), static_cast<float>(luaL_optnumber(L, 3, 0))});
    return 0;
  }
};

void Match::load_scripts(const std::filesystem::path& dir) {
  L_ = luaL_newstate();
  luaL_openlibs(L_);
  if (luaL_dostring(L_, kPrelude) != 0) std::fprintf(stderr, "script prelude: %s\n", lua_tostring(L_, -1));
  static const luaL_Reg api[] = {
      {"Exists", LuaApi::Exists}, {"Team", LuaApi::Team}, {"IsChampion", LuaApi::IsChampion}, {"IsMinion", LuaApi::IsMinion}, {"IsDead", LuaApi::IsDead},
      {"Pos", LuaApi::Pos}, {"Facing", LuaApi::Facing}, {"Distance", LuaApi::Distance}, {"Level", LuaApi::Level}, {"Rank", LuaApi::Rank},
      {"HP", LuaApi::HP}, {"MaxHP", LuaApi::MaxHP}, {"Stat", LuaApi::Stat}, {"SinceHurt", LuaApi::SinceHurt}, {"Now", LuaApi::Now},
      {"Random", LuaApi::Random}, {"Value", LuaApi::Value}, {"Calc", LuaApi::Calc}, {"SpellInfo", LuaApi::SpellInfo}, {"Damage", LuaApi::Damage},
      {"Heal", LuaApi::Heal}, {"AddBuff", LuaApi::AddBuff}, {"HasBuff", LuaApi::HasBuff}, {"BuffStacks", LuaApi::BuffStacks}, {"BuffTime", LuaApi::BuffTime},
      {"RemoveBuff", LuaApi::RemoveBuff}, {"RemoveSlows", LuaApi::RemoveSlows}, {"Enemies", LuaApi::Enemies}, {"After", LuaApi::After},
      {"Missile", LuaApi::Missile}, {"Dash", LuaApi::Dash}, {"Blink", LuaApi::Blink}, {"ClampWalkable", LuaApi::ClampWalkable},
      {"SetCooldown", LuaApi::SetCooldown}, {"Cooldown", LuaApi::Cooldown}, {"ResetAttack", LuaApi::ResetAttack}, {"AttackOrder", LuaApi::AttackOrder},
      {"Effect", LuaApi::Effect}, {"StopEffect", LuaApi::StopEffect}, {"EffectAt", LuaApi::EffectAt}, {"StopEffectAt", LuaApi::StopEffectAt},
      {"EffectValue", LuaApi::EffectValue}, {"SetRecast", LuaApi::SetRecast}, {"Animate", LuaApi::Animate},
      {"EnemiesInLine", LuaApi::EnemiesInLine}, {"Resource", LuaApi::Resource}, {"MaxResource", LuaApi::MaxResource},
      {"AddResource", LuaApi::AddResource}, {"SinceFight", LuaApi::SinceFight}, {"SpawnUnit", LuaApi::SpawnUnit},
      {"RemoveUnit", LuaApi::RemoveUnit}, {"SetFacing", LuaApi::SetFacing},
      {"Allies", LuaApi::Allies}, {"AlliesInLine", LuaApi::AlliesInLine},
      {"IsRooted", LuaApi::IsRooted}, {"IsStunned", LuaApi::IsStunned}, {"IsSilenced", LuaApi::IsSilenced},
  };
  for (const luaL_Reg& f : api) {
    lua_pushlightuserdata(L_, this);
    lua_pushcclosure(L_, f.func, 1);
    lua_setglobal(L_, f.name);
  }
  // every script of the folder, in name order (the same in every run)
  std::vector<std::filesystem::path> files;
  std::error_code ec;
  for (const auto& e : std::filesystem::directory_iterator(dir, ec))
    if (e.path().extension() == ".lua") files.push_back(e.path());
  std::sort(files.begin(), files.end());
  for (const auto& f : files)
    if (luaL_dofile(L_, f.string().c_str()) != 0) {
      std::fprintf(stderr, "script %s: %s\n", f.filename().string().c_str(), lua_tostring(L_, -1));
      lua_pop(L_, 1);
    }
  scripts_loaded_ = files.size();
}

Match::~Match() {
  if (L_) lua_close(L_);
  if (LL_) lua_close(LL_);
  ai_close_scripts();
}

}  // namespace ba
