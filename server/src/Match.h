#pragma once
// The state of one match and its rules, advanced one tick at a time. Nothing in here reads a clock or a random source
// of its own: time is the tick count, chance is the match's Random. Given the same orders on the same ticks, a match
// always plays out the same.
//
// Where the rules come from (docs/PROVENIENTA.md):
//   stats, attack slots, cast times, missiles: the characters' own data (CharacterRecord, SpellObjects)
//   attack timer 1 / attack speed, windup percent 0.3 + offset (or cast / total time), the windup modifier, edge-to-edge
//   attack range, physical damage x 100 / (100 + armor), windup cancelled by a new order: documented (LoL Wiki)
//   the map's structures, lanes, minion waves and upgrades: the map's data (ba/MapGame.h)
//   damage ratios between heroes, units and buildings, attack delay limits, the spawn platform's regeneration, inhibitor
//   health: the mode's GameModeConstants (map11.bin)
//   minions' and turrets' choice of target, the order structures can be attacked in, what turrets do to minions and
//   champions and what protects them: documented (LoL Wiki as of patch 14.1, January 2024)
//   rounding times to ticks, how an attack slot is drawn, how often the AI looks around: our reading [de măsurat]

#include <array>
#include <cstdint>
#include <filesystem>
#include <functional>
#include <initializer_list>
#include <map>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

#include "ba/ItemData.h"
#include "ba/CharacterData.h"
#include "ba/Deterministic.h"
#include "ba/MapGame.h"
#include "ba/NavGrid.h"
#include "ba/Protocol.h"
#include "ba/SpellData.h"
#include "ba/Wad.h"

struct lua_State;

namespace ba {

enum class UnitType : uint8_t { Champion, Minion, Turret, Inhibitor, Nexus, Fountain, Other };
/** A lane minion's kind, from its record's unit tags (Minion_Lane_Melee / _Ranged / _Siege / _Super). */
enum class MinionKind : uint8_t { None, Melee, Caster, Siege, Super };

/** A unit's numbers as the rules use them: its record's, then whatever changes them (minion upgrades). */
struct UnitStats {
  float max_hp = 0, ad = 0, armor = 0, spell_block = 0, attack_range = 0, attack_speed = 0, move_speed = 0;
  float gameplay_radius = 65, acquisition_range = 750;
  float crit = 0;  // the chance (0..1) that an attack strikes critically
  float crit_damage = 0; // bonus crit damage (Infinity Edge: +0.40f)
  float life_steal = 0;   // e.g. 0.10f
  float omnivamp = 0;     // e.g. 0.10f
  float lethality = 0;
  float armor_pen_pct = 0;
  float magic_pen_flat = 0;
  float magic_pen_pct = 0;
  float ap = 0;              // ability power (items)
  float ability_haste = 0;   // items: a cooldown lasts 100 / (100 + haste) of itself (documented)
  float tenacity = 0;        // crowd control duration reduction
};

enum class DamageType : uint8_t { Physical, Magic, True };

/** Something lasting on a unit (a spell's doing): what it changes while it is there, and its script's hooks. */
struct Buff {
  std::string name;
  uint32_t source = 0;
  int64_t end_tick = -1;        // -1: until removed
  int stacks = 1;
  float move_speed_pct = 0;     // 0.35: 35% faster; negative: a slow
  float move_speed = 0;         // flat move speed bonus
  float attack_speed_pct = 0;   // bonus attack speed, as a share of the base
  float ad = 0, armor = 0, spell_block = 0;        // flat
  float armor_pct = 0, spell_block_pct = 0;        // of the unit's own (negative: a shred)
  float damage_taken_pct = 0;   // -0.3: takes 30% less
  float damage_taken = 0;       // tracked damage accumulated
  float shield = 0;             // takes that much damage in the unit's place
  float crit = 0;               // critical strike chance added
  float tenacity = 0;           // tenacity granted
  float min_hp = 0;             // the unit's health does not go below this (Tryndamere's Undying Rage)
  bool stun = false, root = false, silence = false, disarm = false;
  bool untargetable = false, invulnerable = false;
  int on_attack = 0, on_expire = 0;  // Lua functions (registry references; 0: none)
};

/** One of a champion's four spells. */
struct SpellSlot {
  const SpellData* data = nullptr;
  int level = 0;                // 0: not learned
  int64_t ready_tick = 0;       // the first tick it may be cast again
  float cooldown_total = 0;     // seconds, of the cooldown running (the interface's sweep)
  bool recast = false;          // casting it again is its second cast (the script's OnRecast)
  int64_t recast_tick = 0;      // the first tick the second cast may be used
};

/** A cast under way: walking into range (`pending`), or casting until end_tick. */
struct Cast {
  int slot = -1;
  bool pending = false;
  int64_t end_tick = 0;
  float x = 0, z = 0;
  uint32_t target = 0;
};

/** A unit thrown along a line by a spell, deaf to orders until it arrives. */
struct Dash {
  bool active = false;
  float x = 0, z = 0, speed = 0;
  int on_end = 0;  // Lua function
};

struct Unit {
  uint32_t id = 0;
  uint8_t team = 0;
  std::string skin;  // the character it is drawn as
  int64_t spawn_tick = 0;  // the tick it entered the match
  uint8_t skin_id = 0;
  float x = 0;
  float z = 0;
  float move_speed = 340;           // League units per second
  float facing = 0;                 // radians, 0 = +z
  float pathfinding_radius = 0;     // CharacterRecord pathfindingCollisionRadius: how far it keeps from walls
  std::vector<net::Point> path;     // remaining waypoints
  // what it is
  UnitType kind = UnitType::Other;
  int lane = -1;                    // 0 bot, 1 mid, 2 top (the map data's numbering)
  int position = 0;                 // turrets: 3 outer, 2 inner, 1 inhibitor, 0 nexus
  MinionKind minion = MinionKind::None;
  // combat
  const CharacterRecordData* record = nullptr;  // its data; units without one are scenery
  UnitStats base;    // its record's numbers at its level (minions: with their upgrades)
  UnitStats stats;   // `base` with its buffs: what the rules use
  std::vector<Buff> buffs;
  // spells (champions)
  const std::map<std::string, SpellData>* spell_set = nullptr;  // every spell object of its character
  std::array<SpellSlot, 4> spells;
  int skill_points = 0;
  Cast cast;
  Dash dash;
  int64_t last_hurt_tick = -1;      // when something other than a minion last damaged it
  int64_t last_fight_tick = -1;     // when it last dealt or took damage
  uint32_t owner = 0;               // a spell's creature (Zed's shadow): the champion that made it
  float hp = 0, max_hp = 0;
  float total_shield() const {
    float s = 0;
    for (const Buff& b : buffs) if (b.shield > 0) s += b.shield;
    return s;
  }
  bool dead = false;
  int64_t remove_tick = -1;         // dead minions leave the match then
  bool plating = false;             // an outer turret's plating (PreSeason_Turret_Shield); `owner` is its turret
  int64_t respawn_tick = -1;        // dead champions and inhibitors come back then
  // champions
  int level = 1;
  float xp = 0, gold = 0;
  float par = 0, max_par = 0;       // the ability resource (mana, energy ...)
  uint16_t kills = 0, deaths = 0, assists = 0, minions_killed = 0;
  int upgrades = 0;                 // minions: the upgrades they were born with (siege and super gold grows with them)
  // champions' inventory: six slots and the trinket's (6); an item id per slot (0: empty) and its stack
  std::array<int, 7> items{};
  std::array<uint8_t, 7> item_stacks{};
  std::array<int64_t, 7> item_cooldowns{};
  float base_max_par = 0;           // the resource's maximum from the level alone (items add mana to it)
  uint32_t target = 0;              // the unit it attacks (0: none)
  int64_t attack_start = -1;        // tick the current attack began (-1: none)
  int64_t hit_tick = -1;            // tick its hit lands (melee) or its missile leaves (ranged)
  int64_t next_attack = 0;          // first tick it may start another attack
  int attack_slot = 0;              // which of record->attacks
  bool attack_is_crit = false;      // whether current attack is a critical strike
  float target_x = 0, target_z = 0; // where the target was when the path to it was made
  // the AI's own state (minions, turrets)
  int lane_point = 0;               // the next waypoint of its lane
  int64_t last_attack_tick = -1;    // when it last started an attack (who is "attacking" whom, for aggro)
  float pushed = 0;                 // how far other units have pushed it since its clients last got its position
  int64_t path_sent_tick = -1;      // the last tick its path went out
  // a turret's Warming Up: hits on champions in a row, and the tick of the last
  int champion_hits = 0;
  int64_t last_champion_hit = -1;
  // what the level script decides for structures (SetInvulnerable, SetTargetable, SetNotTargetableToTeam); structures
  // stand invulnerable until the script lets them be hurt [dedus: the script only ever lifts it, AllowDamageOnBuildings]
  bool invulnerable = false;
  bool targetable = true;
  uint8_t hidden_from = 0;          // a bit per team (1 Order, 2 Chaos) that may not target it
  // lane minions: what the level script's MinionInfoTable says they are worth (GoldGiven, ExpGiven, ExperienceRadius)
  float gold_given = 0, exp_given = 0, exp_radius = 0;
  // ---- its AI script (MatchAI.cpp): Riot's own data/scripts/<name>, and what the engine keeps for it
  int ai = -1;                      // which of the match's AI scripts runs it (-1: none)
  int ai_state = 0;                 // AI_IDLE, AI_ATTACKMOVESTATE ... (the script's SetState)
  int acquisition_mode = 0;         // TARGET_ACQUISITION_MODE_DEFAULT / _ASLEEP / _DISTRIBUTE_FIRE
  bool ghosted = false;             // SetGhostedForAllies: its allies walk through it
  bool forward_nav = false;         // SetStateAndMoveToForwardNav: it walks its lane, whatever its target
  bool auto_attack = false;         // TurnOnAutoAttack: it attacks its target whenever its attack timer allows ...
  int64_t auto_attack_tick = 0;     // ... from this tick on
  struct AiTimer {
    std::string name;               // the script function it calls
    int64_t period = 1, due = 0;    // ticks
    bool repeat = false, running = false;
  };
  std::vector<AiTimer> ai_timers;
  struct AiIgnored {
    uint32_t unit;
    int64_t until;
  };
  std::vector<AiIgnored> ai_ignored;  // AddToIgnore: not looked at as targets until then
};

/** A unit entering the match (a player joining, a target dummy), applied at the start of a tick like an order. */
struct SpawnRequest {
  uint8_t team = 0;
  std::string character;
  float x = 0, z = 0, move_speed = 0, pathfinding_radius = 0, facing = 0;
};

/** An order from a player, applied at the start of the tick it is scheduled for. */
struct Order {
  enum class Type : uint8_t { Move = 0, Attack = 1, Cast = 2, LevelSpell = 3, BuyItem = 4, SellItem = 5, UseItem = 6 };
  int64_t tick = 0;
  uint32_t unit = 0;
  float x = 0;
  float z = 0;
  Type type = Type::Move;
  uint32_t target = 0;
  uint8_t slot = 0;  // Cast, LevelSpell: which spell (0 Q .. 3 R); SellItem, UseItem: inventory slot (0..6)
  // BuyItem: `target` is the item id
};

/** What happened during a tick, for the clients. */
struct MatchEvents {
  std::vector<uint32_t> spawned;       // new units: the requests first, in their order, then the barracks' minions
  std::vector<uint32_t> removed;       // units that left the match (dead minions after their death)
  std::vector<uint32_t> path_changed;  // units with a new path
  struct Attack {
    uint32_t unit, target;
    std::string spell, animation;
    float windup, total, spell_cast_time;  // seconds
    float facing;
  };
  std::vector<Attack> attacks;
  struct Missile {
    uint32_t unit, target;
    float speed;
    std::string spell;
  };
  std::vector<Missile> missiles;
  /** An attack landing (a melee hit, or a missile reaching its target): the client plays its hit effect. */
  struct Hit {
    uint32_t source, target;
    std::string spell;
  };
  std::vector<Hit> hits;
  struct Damage {
    uint32_t target;
    float amount, hp, max_hp, shield = 0.f;
  };
  std::vector<Damage> damage;
  std::vector<uint32_t> deaths;
  std::vector<uint32_t> respawned;     // champions back from the dead, at their spawn point; inhibitors standing again
  std::vector<uint32_t> stats_changed; // champions whose level, experience, gold, resource or stats changed
  std::vector<uint32_t> items_changed; // champions whose inventory changed
  std::vector<uint32_t> spells_changed; // champions whose spell levels, cooldowns or skill points changed
  struct SpellCast {
    uint32_t unit;
    uint8_t slot;
    std::string spell, animation;
    float cast_time, x, z;
    uint32_t target;
  };
  std::vector<SpellCast> casts;
  struct BuffChange {
    uint32_t unit;
    std::string name;
    float duration;  // seconds; negative: until removed
    bool added;
  };
  std::vector<BuffChange> buffs;
  struct SkillMissile {
    uint32_t id, unit;
    std::string spell;
    float x, z, dx, dz, speed, range;
    std::string effect;
    float accel, speed_limit;
  };
  std::vector<SkillMissile> skill_missiles;
  std::vector<uint32_t> skill_missiles_ended;
  struct DashMove {
    uint32_t unit;
    float x, z, speed;  // speed 0: it is there at once (a blink)
  };
  std::vector<DashMove> dashes;
  struct Effect {
    uint32_t unit;
    std::string key, bone;
    float seconds;  // 0: it plays out
    bool stop;
    uint32_t owner;  // the unit whose skin has the effect
  };
  std::vector<Effect> effects;
  struct GroundEffect {
    uint32_t id;
    bool stop;
    uint32_t owner;
    std::string key;
    float x, z, tx, tz, seconds, height;
  };
  std::vector<GroundEffect> ground_effects;
  struct Animation {
    uint32_t unit;
    std::string clip;
    float seconds;
  };
  std::vector<Animation> animations;
  int winner = -1;                     // the team whose enemy's nexus fell this tick
};

class Match {
 public:
  /** `records`: every character's data, by champion name and by record path ("Characters/Turret/CharacterRecords/
   *  SR_Outer"). `map`: the map's game (structures, lanes, waves); null for a bare match. */
  Match(uint64_t match_id, const NavGrid* nav = nullptr, const std::map<std::string, CharacterRecordData>* records = nullptr,
        const MapGame* map = nullptr);
  ~Match();
  Match(const Match&) = delete;
  Match& operator=(const Match&) = delete;

  /** Where a character's spell objects come from (read when a champion of that character joins). */
  using SpellSource = std::function<const std::map<std::string, SpellData>*(const std::string& character)>;
  void set_spells(SpellSource source) { spells_ = std::move(source); }
  /** Loads the spells' scripts (every .lua of the folder). */
  void load_scripts(const std::filesystem::path& dir);
  size_t scripts_loaded() const { return scripts_loaded_; }
  /** The items (Global.wad) and what the mode sells; without them nothing can be bought. */
  void set_items(const ItemTable* items) { items_ = items; }
  const ItemTable* items() const { return items_; }
  /** Whether a champion may buy and sell now: at its team's spawn, or dead (documented, LoL Wiki "Shop" 2023-11). */
  bool in_shop(const Unit& u) const;
  /** Champions join at this level (checks only: the Practice Tool's "level up"). */
  void set_start_level(int level) { start_level_ = level; }
  /** Checks only: champions join with this much gold (negative: the mode's ai_StartingGold). */
  void set_start_gold(float gold) { start_gold_ = gold; }
  /** Checks only: champions join at this place instead of their fountain (the Practice Tool's teleport). */
  void set_start_place(float x, float z) { start_x_ = x, start_z_ = z; }
  /** Seconds until a spell slot may be cast again. */
  float cooldown_left(const Unit& u, int slot) const {
    return std::max(0.f, static_cast<float>(static_cast<double>(u.spells[static_cast<size_t>(slot)].ready_tick - clock.tick) * kTickSeconds));
  }

  GameClock clock;
  Random random;
  std::vector<Unit> units;  // ordered by id: iteration order never depends on memory addresses

  Unit& spawn(uint8_t team, const std::string& skin, float x, float z);
  Unit* unit(uint32_t id);
  const Unit* unit(uint32_t id) const;
  /** The map's structures, standing when the match begins. `health_scale` other than 1 is for checks only (matches
   *  whose structures fall quickly). */
  void place_structures(float health_scale = 1.f);
  /** Runs the map's level script, patch 12.23's own (Scripts.wad: LevelScript_SRX -> SR_LevelScript): it decides
   *  which structure may be hurt, the minion waves and their upgrades (MatchLevel.cpp). After place_structures. */
  void load_level(const std::filesystem::path& data);
  /** Where records the match did not get come from (the lane minions the level script names). */
  using RecordSource = std::function<const CharacterRecordData*(const std::string& path)>;
  void set_record_source(RecordSource source) { record_source_ = std::move(source); }
  /** The team that won (its enemy's nexus fell), -1 while the match goes on. A finished match stands still. */
  int winner() const { return winner_; }

  /** Applies the spawns and orders of this tick and advances the world by one tick. */
  MatchEvents step(const std::vector<SpawnRequest>& spawns, const std::vector<Order>& orders);
  /** A checksum of everything that decides the game (tick, random state, every unit's exact numbers): two runs of the
   *  same recording must agree on it tick for tick. */
  uint64_t checksum() const;
  /** Seconds since the game began (the first champion came in); negative before. */
  double game_seconds() const;
  /** The tick the game began on, -1 before. */
  int64_t start_tick() const { return start_tick_; }

 private:
  struct Missile {
    uint32_t source, target;
    float damage;
    float x, z, speed;
    const AttackSlot* slot;
    bool crit = false;
  };
  /** A lane minion the barracks will put out at `tick`, with what the level script's MinionInfoTable gave it. */
  struct PendingMinion {
    int64_t tick;
    uint8_t team;
    int lane;
    std::string character;  // MinionName: "SRU_OrderMinionMelee"
    float hp_bonus, damage_bonus, armor, spell_block, move_speed_bonus, gold, exp, exp_radius;
  };
  void path_to(Unit& u, float x, float z, MatchEvents& ev);
  void start_attack(Unit& u, Unit& t, MatchEvents& ev);
  void hit(Unit& source, Unit& target, float damage, const std::string& spell, MatchEvents& ev);
  /** `extra`: attack damage added for this attack (a spell's empowered attack). */
  float attack_damage(const Unit& source, const Unit& target, float extra = 0) const;
  /** Takes `damage` (already past armor) off the target: its damage reductions and shields first; death and rewards. */
  float apply_damage(Unit& source, Unit& target, float damage, MatchEvents& ev);
  // ---- spells (MatchSpells.cpp)
  friend struct LuaApi;
  struct SkillMissile {
    uint32_t id = 0, source = 0;
    uint8_t team = 0;
    float x = 0, z = 0, dx = 0, dz = 1, speed = 0, left = 0, width = 0;
    float accel = 0, speed_limit = 0;  // AcceleratingMovement: the speed changes by accel a second up (or down) to the limit
    int on_hit = 0, on_end = 0;
    bool champions = false;  // only champions stop it or are hit by it
    std::vector<uint32_t> hit;
  };
  struct Timer {
    int64_t tick;
    uint64_t seq;
    int ref;
  };
  bool has_flag(const Unit& u, bool Buff::*flag) const;
  Buff* find_buff(Unit& u, const std::string& name);
  /** `stats` from `base` and the unit's buffs. */
  void refresh_stats(Unit& u, MatchEvents* ev);
  void remove_buff(Unit& u, size_t index, bool expired, MatchEvents& ev);
  void update_buffs(MatchEvents& ev);
  float spell_damage(Unit& source, Unit& target, float raw, DamageType type, const std::string& spell, MatchEvents& ev);
  void give_spells(Unit& u);
  void level_spell(Unit& u, int slot, MatchEvents& ev);
  void buy_item(Unit& u, int id, MatchEvents& ev);
  void sell_item(Unit& u, int slot, MatchEvents& ev);
  void use_item(Unit& u, int slot, float x, float z, uint32_t target, MatchEvents& ev);
  SpellCaster caster_of(const Unit& u) const;
  void order_cast(Unit& u, const Order& o, MatchEvents& ev);
  void begin_cast(Unit& u, MatchEvents& ev);
  void finish_cast(uint32_t id, MatchEvents& ev);
  /** Spells[spell].<hook>(the cast's table): pushes the call's one result (nil when the script has no such hook). */
  bool spell_hook(const Unit& u, const Cast& c, const char* hook);
  void update_casts(MatchEvents& ev);
  void update_skill_missiles(MatchEvents& ev);
  void run_timers(MatchEvents& ev);
  void champion_ticks(MatchEvents& ev);
  /** The bonus damage the attacker's buffs add to an attack that lands (their on_attack hooks). */
  float attack_bonus(uint32_t attacker, uint32_t target);
  /** Champions[name].<hook>(unit, other, flag, amount), when the champion's script has it. */
  void champion_hook(uint32_t id, const char* hook, uint32_t other, bool flag, float amount);
  /** Calls the Lua function on the stack; false (and the error logged) when it fails. */
  bool call(int args, int results, const char* what);
  /** Calls a script function kept by reference (no arguments), and lets go of it. */
  void run_ref(int ref);
  /** A mode constant (GameModeConstants), or `dflt` without the map's data. */
  float constant(const char* name, float dflt) const { return map_ ? map_->constant(name, dflt) : dflt; }
  void regenerate(MatchEvents& ev);
  /** A champion's stats at its level: the record's base and per-level growth. */
  void level_stats(Unit& u);
  /** Experience and gold for a death: to the champions near it and to the one that landed the last hit. */
  void reward(const Unit& dead, const Unit& killer, MatchEvents& ev);
  void gain_xp(Unit& u, float amount, MatchEvents& ev);
  /** The part of the way from the champion's level to the next (1 at the last level). */
 public:
  float xp_fraction(const Unit& u) const;
 private:
  void set_record(Unit& u, const CharacterRecordData* r);
  float reach(const Unit& u, const Unit& t) const;
  /** Whether `t` may be attacked by `by` (alive, an enemy, and a structure only once the ones before it fell). */
  bool attackable(const Unit& by, const Unit& t) const;
  // ---- the level script (MatchLevel.cpp)
  friend struct LevelApi;
  const CharacterRecordData* record_at(const std::string& path);
  /** Calls the level script's function on the stack (lua_pcall); false (and the error logged) when it fails. */
  bool level_call(int args, int results, const char* what);
  /** Calls a global function of the level script by name, without arguments, when it has one. */
  void level_run(const char* name);
  /** Stands a PreSeason_Turret_Shield unit on each outer turret (see the definition). */
  void spawn_turret_plating();
  /** The game begins (the first champion came in): the server's timers start (OnLevelInitServer, OnGameStartup). */
  void level_start();
  /** The level script's timers and the barracks' waves, every tick. */
  void barracks(MatchEvents& ev);
  void spawn_minion(const PendingMinion& p, MatchEvents& ev);
  /** A structure fell: the level script's HandleDestroyedObject decides what is exposed next. */
  void structure_destroyed(Unit& u);
  void minion_ai(Unit& u, MatchEvents& ev);
  /** Walks a lane minion on along its lane: the next waypoint, then the enemy nexus. */
  void lane_walk(Unit& u, MatchEvents& ev);
  // ---- the units' AI scripts (MatchAI.cpp)
  friend struct AiApi;
  /** The script `name` of data/scripts (loaded on first use): its index, -1 when the game has none. */
  int ai_script(const std::string& name);
  /** Gives the unit its AI script and runs the script's OnInit for it. */
  void ai_init(Unit& u, const std::string& script);
  /** Calls a function of the unit's script for it (the script's "me"); false when the script has none or it failed. */
  bool ai_call(Unit& u, const char* fn, std::initializer_list<uint32_t> args = {});
  /** Every tick: targets that are gone (OnTargetLost) and the scripts' timers that are due. */
  void ai_update(MatchEvents& ev);
  /** The engine's choice of a target for `u` within `range` (between centres) among the units carrying one of the
   *  `include` tags (any when empty) and none of the `exclude` tags; 0: none. */
  uint32_t ai_find_target(const Unit& u, float range, const std::vector<std::string>& include, const std::vector<std::string>& exclude) const;
  void ai_set_target(Unit& u, uint32_t target);
  /** Sends the unit towards its target's place. */
  void ai_close(Unit& u, const Unit& t, MatchEvents& ev);
  /** `attacker` attacks `victim`: the victim's allies near enough are told (their scripts' OnCallForHelp). */
  void ai_call_for_help(const Unit& victim, const Unit& attacker);
  void ai_close_scripts();
  void turret_ai(Unit& u);
  /** Pushes apart units that stand in one another. */
  void separate(MatchEvents& ev);
  /** Whether `a` has attacked `b` lately (the AI's notion of "attacking"). */
  bool attacking(const Unit& a, const Unit& b) const;

  uint32_t next_id_ = 1;
  const NavGrid* nav_ = nullptr;  // the map's .aimesh_ngrid: paths go around its walls
  const std::map<std::string, CharacterRecordData>* records_ = nullptr;
  const MapGame* map_ = nullptr;
  const ItemTable* items_ = nullptr;
  std::vector<Missile> missiles_;
  std::unordered_map<uint32_t, size_t> index_;  // id -> position in units
  int64_t start_tick_ = -1;   // the tick the first champion came in
  int winner_ = -1;
  lua_State* L_ = nullptr;
  MatchEvents* ev_ = nullptr;  // the tick's events, while it is stepped (the scripts' functions add to them)
  SpellSource spells_;
  std::vector<SkillMissile> skill_missiles_;
  uint32_t next_missile_id_ = 1;
  uint32_t next_ground_effect_ = 1;
  std::vector<Timer> timers_;
  uint64_t timer_seq_ = 0;
  size_t scripts_loaded_ = 0;
  int start_level_ = 1;
  float start_gold_ = -1;
  float start_x_ = -1, start_z_ = -1;
  std::vector<PendingMinion> pending_minions_;
  // the level script
  struct LevelTimer {
    std::string name;   // the global function it calls
    double at, every;   // game seconds; every <= 0: once
  };
  struct Barracks {
    uint8_t team = 0;
    int lane = 0;
    int waves = 0;              // waves put out so far
    double disabled_until = -1; // SetDisableMinionSpawn: its inhibitor lies fallen until then (game seconds)
  };
  lua_State* LL_ = nullptr;
  struct AiScript {
    std::string name;
    lua_State* L = nullptr;   // null: the game has no such script
  };
  std::vector<AiScript> ai_scripts_;
  uint32_t ai_me_ = 0;        // the unit an AI script is being called for
  std::unique_ptr<Wad> scripts_wad_;
  std::map<std::string, std::string> mutators_;   // the mode's mutator parameters: "LevelScriptFile" -> "LevelScript_SRX.lua"
  std::vector<LevelTimer> level_timers_;
  // ---- the jungle script's state the engine keeps (sr_neutralminionspawn)
  uint32_t preload_flags_ = 0;                 // Get / SetModePreloadFlags: which dragons the script asked to preload
  std::vector<std::string> unit_tag_names_;    // UnitTagIndicies: the index the scripts know each unit tag by
  struct NeutralCamp {
    int index = 0;        // the script's camp number
    float x = 0, z = 0;   // its MinimapPosition
  };
  std::vector<NeutralCamp> neutral_camps_;     // CreateNeutralCamp
  std::vector<Barracks> barracks_;
  double first_wave_ = 0, wave_rate_ = 30, minion_delay_ = 0.8;  // seconds (the script's INITIAL_TIME_TO_SPAWN, ms tables)
  int wave_id_ = 0;
  // the next wave, game seconds; armed again from the moment a wave actually went out [măsurat: 13.3 replay, waves
  // 30.000..30.033 s apart, drifting +0.88 s over 60 waves]
  double next_wave_ = -1;
  bool level_started_ = false;
  float health_scale_ = 1.f;  // checks only: structures' health times this (place_structures)
  RecordSource record_source_;
};

}  // namespace ba
