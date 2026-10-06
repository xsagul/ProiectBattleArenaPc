// client.exe: the match client. Connects to server.exe, sends the player's orders (right click: move, or attack the
// enemy under the cursor; T: the Practice Tool's target dummy at the cursor) and draws the match from League's own
// files. It holds no game rules: everything it shows comes from the server.
//
//   client.exe [--host 127.0.0.1] [--port 5119] [--name Sorin] [--data <folder with DATA/FINAL>]

#include <windows.h>
#include <windowsx.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <map>
#include <memory>
#include <set>
#include <string>
#include <thread>
#include <tuple>

#include "Character.h"
#include "Connection.h"
#include "Gpu.h"
#include "Hud.h"
#include "LoadingScreen.h"
#include "MapView.h"
#include "Vfx.h"
#include "Math.h"
#include "ba/CharacterData.h"
#include "ba/GameData.h"
#include "ba/Hash.h"
#include "ba/ItemData.h"
#include "ba/MapGame.h"
#include "Replay.h"
#include "ba/StringTable.h"
#include "ba/MapObjects.h"
#include "ba/SpellData.h"
#include "ba/Wad.h"

using namespace ba;

namespace {

// League's camera: looks north, tilted 56 degrees down, 40 degree vertical field of view.
constexpr float kPitch = 56.f * 3.14159265f / 180.f;
constexpr float kFov = 40.f * 3.14159265f / 180.f;

struct Camera {
  float x = 1200, z = 1200;  // the point looked at (League units)
  // zoom limits: CameraConfig (Global.wad globals bin) mZoomMinDistance 1000 [meta default] and mZoomMaxDistance 2250
  // [two of its four entries + meta default; the others say 2600 and 3000; de măsurat: which entry CLASSIC uses]
  static constexpr float kZoomMin = 1000, kZoomMax = 2250;
  static constexpr float kNear = 50, kFar = 20000;  // our depth range [alegere proprie]
  float distance = kZoomMax;  // [de măsurat: the zoom a match starts at]
  float target = kZoomMax;    // where the wheel sends the zoom; mZoomEaseTime 0.2 s eases toward it [meta default]
  float4x4 view, proj;
  float3 eye;
  // --eye x,y,z (checks): the eye held at a point, as the replay client's free camera is, looking down at the pitch
  bool fixed = false;
  float3 fixed_eye;

  void update(float aspect, float ground) {
    float3 at{x, ground, z};
    eye = {x, ground + std::sin(kPitch) * distance, z - std::cos(kPitch) * distance};
    if (fixed) eye = fixed_eye, at = {eye.x, eye.y - std::sin(kPitch) * 1000.f, eye.z + std::cos(kPitch) * 1000.f};
    view = look_at_lh(eye, at, {0, 1, 0});
    proj = perspective_lh(kFov, aspect, kNear, kFar);
  }

  /** The direction from the eye through a screen pixel. */
  float3 ray(int px, int py, int w, int h) const {
    const float nx = (2.f * static_cast<float>(px) / static_cast<float>(w) - 1.f) / proj.m[0][0];
    const float ny = (1.f - 2.f * static_cast<float>(py) / static_cast<float>(h)) / proj.m[1][1];
    // camera basis from the view matrix (columns are the camera axes in world space)
    const float3 right{view.m[0][0], view.m[1][0], view.m[2][0]};
    const float3 up{view.m[0][1], view.m[1][1], view.m[2][1]};
    const float3 fwd{view.m[0][2], view.m[1][2], view.m[2][2]};
    return normalize(fwd + right * nx + up * ny);
  }

  /** The point of the plane y = `ground` under a screen pixel. */
  bool pick(int px, int py, int w, int h, float ground, float& wx, float& wz) const {
    const float3 dir = ray(px, py, w, h);
    if (std::fabs(dir.y) < 1e-5f) return false;
    const float t = (ground - eye.y) / dir.y;
    if (t <= 0) return false;
    wx = eye.x + dir.x * t;
    wz = eye.z + dir.z * t;
    return true;
  }
};

Gpu g_gpu;
bool g_structure_yaw_test = false;
// the shop: the items (Global.wad), the mode's list (map11.bin), the texts (Localized/Global.en_US.wad)
ItemTable g_items;
StringTable g_strings;
std::unique_ptr<Wad> g_global_wad;
bool g_shop_open = false;    // P (League's default key)
int g_shop_selected = 0;     // the item picked in the shop
int g_inv_selected = -1;     // the inventory slot picked while the shop is open

/** What buying `id` costs the player now: the items it builds from that the player owns are used up (as the server
 *  does it). */
int cost_now(int id, const int (&owned)[7]) {
  int inv[7];
  for (int k = 0; k < 7; ++k) inv[k] = owned[k];
  std::function<int(int)> cost_of = [&](int item) -> int {
    for (int& slot : inv)
      if (slot == item && item != id) {
        slot = 0;
        return 0;
      }
    const ItemDef* d = g_items.find(item);
    if (!d) return 0;
    int c = d->price;
    for (int comp : d->components) c += cost_of(comp);
    return c;
  };
  return cost_of(id);
}
std::string g_turret_clip_test;  // --turret-clip <clip>: every turret stands in this clip (test only)
float g_structure_yaw[2] = {1, 0};
Connection g_conn;
MapView g_map;
CharacterModel g_garen;
std::filesystem::path g_data;          // DATA/FINAL
const Wad* g_map_wad = nullptr;

/** The model of a character skin, loaded once: from its champion wad when it has one, else from the map's wad
 *  (structures, monsters). */
/** The wad that holds a character: its champion wad when it has one, else the map's. */
const Wad* wad_of(const std::string& character) {
  static std::map<std::string, std::unique_ptr<Wad>> wads;
  static std::map<std::string, const Wad*> found;
  if (auto it = found.find(character); it != found.end()) return it->second;
  const auto open = [&](const std::string& name) -> const Wad* {
    const std::filesystem::path champ = g_data / "Champions" / (name + ".wad.client");
    if (!std::filesystem::exists(champ)) return nullptr;
    auto& w = wads[name];
    if (!w) w = std::make_unique<Wad>(champ);
    return w.get();
  };
  const Wad* wad = open(character);
  if (!wad) {
    // a champion's creature lives in the champion's archive (ZedShadow in Zed's): the archive named by the longest
    // beginning of the character's name that holds the character's files
    std::string lower = character;
    for (char& c : lower) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    const std::string bin = "data/characters/" + lower + "/" + lower + ".bin";
    for (size_t n = character.size() - 1; n >= 2 && !wad; --n)
      if (const Wad* w = open(character.substr(0, n)); w && w->has(bin)) wad = w;
  }
  if (!wad) wad = g_map_wad;
  found[character] = wad;
  return wad;
}

CharacterModel* model_of(const std::string& character, int skin) {
  static std::map<std::string, std::unique_ptr<CharacterModel>> models;
  const std::string key = character + "/" + std::to_string(skin);
  auto it = models.find(key);
  if (it != models.end()) return it->second.get();
  auto m = std::make_unique<CharacterModel>();
  const Wad* wad = wad_of(character);
  CharacterModel* out = wad && m->load(g_gpu, *wad, character, skin) ? m.get() : nullptr;
  models[key] = out ? std::move(m) : nullptr;
  return out;
}
/** A character's CharacterRecord (selection cylinder for picking), read once from the wad its model comes from. */
const CharacterRecordData* record_of(const std::string& character) {
  static std::map<std::string, std::unique_ptr<CharacterRecordData>> records;
  auto it = records.find(character);
  if (it != records.end()) return it->second.get();
  auto r = std::make_unique<CharacterRecordData>();
  bool ok = false;
  try {
    const Wad* wad = wad_of(character);
    ok = wad && read_character_record(*wad, character, *r);
  } catch (const std::exception&) {
  }
  auto& slot = records[character];
  slot = ok ? std::move(r) : nullptr;
  return slot.get();
}
/** An interface picture of a character (its portrait, a spell's icon), from the wad that holds the character; cached. */
ID3D11ShaderResourceView* icon_of(const std::string& character, const std::string& path) {
  static std::map<std::string, ComPtr<ID3D11ShaderResourceView>> icons;
  if (path.empty()) return nullptr;
  std::string key = path;
  for (char& c : key) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
  auto it = icons.find(key);
  if (it != icons.end()) return it->second.Get();
  ComPtr<ID3D11ShaderResourceView> srv;
  try {
    const Wad* wad = wad_of(character);
    if (auto bytes = wad ? wad->read(key) : std::nullopt) srv = g_gpu.texture(read_texture(*bytes));
  } catch (const std::exception&) {
  }
  icons[key] = srv;
  return srv.Get();
}
/** A character's spell objects (for the effects its spells name), read once from the wad that holds it. */
const std::map<std::string, SpellData>& spells_of(const std::string& character) {
  static std::map<std::string, std::map<std::string, SpellData>> cache;
  auto it = cache.find(character);
  if (it != cache.end()) return it->second;
  std::map<std::string, SpellData> spells;
  try {
    if (const Wad* wad = wad_of(character)) spells = read_spells(*wad, character);
  } catch (const std::exception&) {
  }
  return cache.emplace(character, std::move(spells)).first->second;
}
CharacterRenderer g_chars;
Vfx g_vfx;
Hud g_hud;
bool g_hud_on = false;
// the loading screen (the "LoadingScreen" client state): shown from the window's first frame until the server has put
// the player into the match
LoadingScreen g_loading;
bool g_loading_on = false;
// the outer turrets (MapGame position 3): their health is five plates of 1000 until 14:00, and their bar shows them
// ("Plates are segments of the turret's health", LoL Wiki, Turret, revision of 2024-01-13)
std::vector<std::array<float, 2>> g_outer_turrets;
MapGame g_map_game;   // the map's game objects (a replay's packets name them)
Replay g_replay;      // --replay <file.barp>: the match comes from Riot's packets, not from our server
constexpr double kPlatingEndsSeconds = 14 * 60;
// the minimap's picture and the world square it covers: the map skin's mMinimapBackgroundConfig (mDefaultTextureName,
// and that texture's mSize among mCustomMinimapBackgrounds) [dedus: the square starts at the world's origin]
std::string g_minimap_texture;
float g_minimap_size[2] = {14850, 14850};
int g_fps = 0;

/** Every unit's joints in the world, as drawn last frame (effects start from and stick to bones). */
struct UnitPose {
  const CharacterModel* model = nullptr;
  std::vector<float4x4> joints;
};
std::map<uint32_t, UnitPose> g_poses;
std::map<uint32_t, std::string> g_unit_clips;  // the clip each unit was drawn with last frame (the shot's report)

/** Where a unit's bone is; bone names in spell data differ in case from the skeleton's ("R_hand" / "R_Hand"). */
bool bone_world(uint32_t unit, const std::string& bone, float3& out) {
  auto it = g_poses.find(unit);
  if (it == g_poses.end() || !it->second.model || bone.empty()) return false;
  const auto& joints = it->second.model->skeleton.joints;
  for (size_t i = 0; i < joints.size() && i < it->second.joints.size(); ++i) {
    const std::string& n = joints[i].name;
    if (n.size() != bone.size()) continue;
    bool same = true;
    for (size_t k = 0; k < n.size() && same; ++k) same = std::tolower(static_cast<unsigned char>(n[k])) == std::tolower(static_cast<unsigned char>(bone[k]));
    if (!same) continue;
    const float4x4& m = it->second.joints[i];
    out = {m.m[3][0], m.m[3][1], m.m[3][2]};
    return true;
  }
  return false;
}

std::set<uint32_t> g_unresolved_effects;  // effect keys nothing resolved (the shot's report lists them)

/** An effect key resolved through the caster's skin (its ResourceResolver), then through the game's
 *  GlobalResourceResolver (the turrets' break effects are there), or null. */
const VfxSystemDef* effect_of(const ClientUnit& caster, uint32_t key) {
  if (!key) return nullptr;
  const Wad* wad = wad_of(caster.skin);
  if (!wad) return nullptr;
  const auto& resolver = g_vfx.skin_effects(*wad, caster.skin, caster.skin_id, g_map_wad);
  auto it = resolver.find(key);
  const VfxSystemDef* sys = it == resolver.end() ? g_vfx.global_effect(key) : g_vfx.system(it->second);
  if (!sys) g_unresolved_effects.insert(key);
  return sys;
}

/** An effect frame at `p` whose local +z points along `forward` (+y stays as close to up as it can). */
VfxFrame frame_at(float3 p, float3 forward) {
  VfxFrame f;
  f.x = p.x, f.y = p.y, f.z = p.z;
  float3 z = forward;
  const float len = std::sqrt(z.x * z.x + z.y * z.y + z.z * z.z);
  if (len < 1e-5f) return f;
  z = {z.x / len, z.y / len, z.z / len};
  float3 x{z.z, 0, -z.x};  // up x forward
  const float lx = std::sqrt(x.x * x.x + x.z * x.z);
  if (lx < 1e-5f) return f;
  x = {x.x / lx, 0, x.z / lx};
  const float3 y{z.y * x.z - z.z * x.y, z.z * x.x - z.x * x.z, z.x * x.y - z.y * x.x};  // forward x right
  const float3 axes[3] = {x, y, z};
  for (int c = 0; c < 3; ++c) f.m[static_cast<size_t>(0 * 3 + c)] = axes[c].x, f.m[static_cast<size_t>(1 * 3 + c)] = axes[c].y, f.m[static_cast<size_t>(2 * 3 + c)] = axes[c].z;
  return f;
}

/** A missile's frame: VeritcalFacingMatchVelocity turns the effect's vertical axis (+y) along its velocity. The data
 *  agrees: Ashe's arrow mesh lies along z and its emitter turns it 90 degrees about x (onto y), her trail is born at
 *  -y (behind), Lux's crescent moves at +y. Local x stays horizontal (the right), z = x cross y. */
VfxFrame missile_frame(float3 p, float3 velocity) {
  VfxFrame f = frame_at(p, velocity);  // columns: right, up, forward
  for (size_t r = 0; r < 3; ++r) {
    const float up = f.m[r * 3 + 1], fwd = f.m[r * 3 + 2];
    f.m[r * 3 + 1] = fwd, f.m[r * 3 + 2] = -up;
  }
  return f;
}

/** The attack effects alive: missiles in flight (their mMissileEffectKey moving as FixedSpeedMovement says) and hit
 *  effects (mHitEffectKey on the target's mHitBoneName). */
struct CombatFx {
  std::unique_ptr<VfxInstance> inst;
  bool flying = false;  // a missile still on its way
  uint32_t from = 0, to = 0;
  std::string spell;
  const AttackSlot* slot = nullptr;
  float3 pos;
  uint32_t on_unit = 0;  // stuck to this unit's bone
  std::string bone;
  float3 forward{0, 0, 1};
  // an animation event's or a skin's idle effect: it turns with its unit, and ends when told (`kill`: at once)
  uint64_t serial = 0;
  bool of_unit = false, kill = false;
};
std::vector<CombatFx> g_combat_fx;
uint64_t g_fx_serial = 0;
long long g_frame_no = 0;

/** Starts an effect on one of a unit's bones (its feet without one); `follow`: it stays on the bone. The effect is of
 *  the unit's own skin, or of `owner`'s (a spell's hit effect on its target). */
uint64_t start_unit_fx(uint32_t id, const ClientUnit& u, uint32_t effect, const std::string& bone, bool follow, float scale,
                       const ClientUnit* owner = nullptr) {
  const VfxSystemDef* sys = effect_of(owner ? *owner : u, effect);
  if (!sys) return 0;
  CombatFx fx;
  fx.serial = ++g_fx_serial;
  fx.of_unit = true;
  fx.bone = bone;
  if (!bone_world(id, bone, fx.pos)) fx.pos = {u.x, g_map.ground_height(u.x, u.z), u.z};
  fx.forward = {std::sin(u.facing), 0, std::cos(u.facing)};
  if (follow) fx.on_unit = id;
  fx.inst = std::make_unique<VfxInstance>(*sys, frame_at(fx.pos, fx.forward), scale, std::array<float, 4>{1, 1, 1, 1}, g_vfx.rng());
  g_combat_fx.push_back(std::move(fx));
  return g_fx_serial;
}

/** Ends a unit's effect: it stops making particles and those alive play out, or (`kill`) it is gone at once. */
void end_unit_fx(uint64_t serial, bool kill) {
  for (CombatFx& fx : g_combat_fx)
    if (fx.serial == serial) {
      if (kill) fx.kill = true;
      else fx.inst->stop();
    }
}

/** The ParticleEventData of the clips a unit plays, and its skin's idle effects.
 *  Our reading of the fields [de măsurat]: an event starts its effect when its clip reaches mStartFrame; mIsLoop keeps
 *  it for as long as the clip plays (to mEndFrame when it has one), after which mIsKillEvent removes it at once (else
 *  its particles play out); an effect that is not mIsDetachable stays on its bone. */
struct EventRun {
  float last_t = 0;
  bool fired = false;
  long long seen = -1;
  uint64_t fx = 0;
  bool loop = false, kill = false;
};
std::map<std::tuple<uint32_t, const Clip*, size_t>, EventRun> g_event_runs;
std::map<uint32_t, std::vector<uint64_t>> g_idle_fx;

void drop_idle_fx(uint32_t id, bool kill) {
  auto it = g_idle_fx.find(id);
  if (it == g_idle_fx.end()) return;
  for (uint64_t s : it->second) end_unit_fx(s, kill);
  g_idle_fx.erase(it);
}

void unit_effects(uint32_t id, const ClientUnit& u, const CharacterInstance& ci) {
  const AnimState* states[2] = {ci.layered ? ci.under_state : nullptr, ci.state};
  for (const AnimState* st : states) {
    if (!st) continue;
    for (const auto& [clip, t] : st->playing) {
      const float frame = clip->tick > 0 ? t / clip->tick : 0.f;
      for (size_t i = 0; i < clip->particle_events.size(); ++i) {
        const Clip::ParticleEvent& e = clip->particle_events[i];
        EventRun& run = g_event_runs[{id, clip, i}];
        if (run.seen != g_frame_no - 1 || t + 1e-4f < run.last_t) {
          // the clip starts (again): its events are due again
          if (run.fx && run.loop) end_unit_fx(run.fx, run.kill);
          run.fired = false, run.fx = 0;
        }
        const bool in = frame >= e.start && (e.end < 0 || frame <= e.end || !e.loop);
        if (!run.fired && in) {
          const int j = ci.model->joint_by_name_hash(e.bone);
          const std::string bone = j >= 0 ? ci.model->skeleton.joints[static_cast<size_t>(j)].name : std::string();
          run.fx = start_unit_fx(id, u, e.effect, bone, !e.detachable, e.scale);
          run.fired = true, run.loop = e.loop, run.kill = e.kill;
        } else if (run.fx && e.loop && !in) {
          end_unit_fx(run.fx, e.kill);
          run.fx = 0;
        }
        run.last_t = t, run.seen = g_frame_no;
      }
    }
  }
  // the skin's idle effects, for as long as the unit lives
  if (u.dead) {
    drop_idle_fx(id, false);
  } else if (!ci.model->idle_effects.empty() && !g_idle_fx.count(id)) {
    std::vector<uint64_t>& mine = g_idle_fx[id];
    for (const CharacterModel::IdleEffect& ie : ci.model->idle_effects) mine.push_back(start_unit_fx(id, u, ie.effect, ie.bone, true, 1.f));
  }
}

/** After every unit was drawn: looping event effects whose clip no longer plays end; units gone lose theirs. */
void sweep_unit_effects() {
  for (auto it = g_event_runs.begin(); it != g_event_runs.end();) {
    EventRun& run = it->second;
    if (run.seen == g_frame_no) {
      ++it;
      continue;
    }
    if (run.fx && run.loop) end_unit_fx(run.fx, run.kill), run.fx = 0;
    it = g_frame_no - run.seen > 600 ? g_event_runs.erase(it) : std::next(it);
  }
  for (auto it = g_idle_fx.begin(); it != g_idle_fx.end();) {
    if (g_conn.units.count(it->first)) {
      ++it;
      continue;
    }
    for (uint64_t s : it->second) end_unit_fx(s, false);
    it = g_idle_fx.erase(it);
  }
  ++g_frame_no;
}

/** The target point of a missile: the target's position at its ground height (mUseGroundHeightAtTarget) raised by
 *  mTargetHeightAugment [de măsurat: what mOffsetInitialTargetHeight changes]. */
float3 missile_target(const ClientUnit& t, const AttackSlot& a) {
  const float ground = a.ground_height_at_target ? g_map.ground_height(t.x, t.z) : 0.f;
  return {t.x, ground + a.target_height_augment, t.z};
}

/** Spells' missiles in flight: each one's mMissileEffectKey moving along its line [de măsurat: the height it flies at;
 *  100 over the ground here]. */
struct SkillFx {
  Connection::SkillMissile m;
  uint64_t fx = 0;
};
std::vector<SkillFx> g_skill_fx;
/** Effects the scripts started on units: (unit, key) -> the effect, and when it is to be stopped (-1: it plays out). */
std::map<std::pair<uint32_t, std::string>, std::pair<uint64_t, double>> g_script_fx;
/** Effects the scripts started at places: the effect's id -> the effect, and when it is to be stopped. */
std::map<uint32_t, std::pair<uint64_t, double>> g_ground_fx;

void update_spell_fx(double now) {
  for (const Connection::SkillMissile& m : g_conn.skill_missiles) {
    auto c = g_conn.units.find(m.unit);
    if (c == g_conn.units.end()) continue;
    const auto& spells = spells_of(c->second.skin);
    auto s = spells.find(m.spell);
    const VfxSystemDef* sys = !m.effect.empty() ? effect_of(c->second, fnv1a(m.effect)) : s == spells.end() ? nullptr : effect_of(c->second, s->second.missile_effect);
    SkillFx k;
    k.m = m;
    if (sys) {
      CombatFx fx;
      fx.serial = ++g_fx_serial;
      fx.flying = true;
      fx.pos = {m.x, g_map.ground_height(m.x, m.z) + 100.f, m.z};
      fx.forward = {m.dx, 0, m.dz};
      fx.inst = std::make_unique<VfxInstance>(*sys, missile_frame(fx.pos, fx.forward), 1.f, std::array<float, 4>{1, 1, 1, 1}, g_vfx.rng());
      k.fx = fx.serial;
      g_combat_fx.push_back(std::move(fx));
    }
    g_skill_fx.push_back(k);
  }
  g_conn.skill_missiles.clear();
  for (SkillFx& k : g_skill_fx) {
    // how far it has flown: at its speed, which changes by its acceleration until it reaches the limit
    const float t = std::max(0.f, static_cast<float>(now - k.m.start));
    float flown = t * k.m.speed;
    if (k.m.accel != 0) {
      const float until = std::max(0.f, (k.m.speed_limit - k.m.speed) / k.m.accel), ta = std::min(t, until);
      flown = k.m.speed * ta + 0.5f * k.m.accel * ta * ta + k.m.speed_limit * (t - ta);
    }
    const float along = std::clamp(flown, 0.f, k.m.range);
    const float x = k.m.x + k.m.dx * along, z = k.m.z + k.m.dz * along;
    const bool ended = std::find(g_conn.skill_missiles_ended.begin(), g_conn.skill_missiles_ended.end(), k.m.id) != g_conn.skill_missiles_ended.end();
    for (CombatFx& fx : g_combat_fx)
      if (fx.serial == k.fx && k.fx) {
        fx.pos = {x, g_map.ground_height(x, z) + 100.f, z};
        fx.inst->set_frame(missile_frame(fx.pos, fx.forward));
        if (ended) fx.flying = false, fx.inst->stop();
      }
    if (ended) k.m.id = 0;
  }
  std::erase_if(g_skill_fx, [](const SkillFx& k) { return k.m.id == 0; });
  g_conn.skill_missiles_ended.clear();
  // the scripts' effects
  for (const Connection::EffectChange& e : g_conn.effects) {
    auto u = g_conn.units.find(e.unit);
    const auto key = std::make_pair(e.unit, e.key);
    auto old = g_script_fx.find(key);
    if (old != g_script_fx.end()) {
      end_unit_fx(old->second.first, false);
      g_script_fx.erase(old);
    }
    if (e.stop || u == g_conn.units.end()) continue;
    auto owner = g_conn.units.find(e.owner);
    const uint64_t serial = start_unit_fx(e.unit, u->second, fnv1a(e.key), e.bone, true, 1.f, owner == g_conn.units.end() ? nullptr : &owner->second);
    if (serial) g_script_fx[key] = {serial, e.seconds > 0 ? now + e.seconds : -1.0};
  }
  g_conn.effects.clear();
  for (const Connection::GroundEffect& e : g_conn.ground_effects) {
    if (e.stop) {
      if (auto old = g_ground_fx.find(e.id); old != g_ground_fx.end()) {
        end_unit_fx(old->second.first, false);
        g_ground_fx.erase(old);
      }
      continue;
    }
    auto owner = g_conn.units.find(e.owner);
    const VfxSystemDef* sys = owner == g_conn.units.end() ? nullptr : effect_of(owner->second, fnv1a(e.key));
    if (!sys) continue;
    CombatFx fx;
    fx.serial = ++g_fx_serial;
    fx.pos = {e.x, g_map.ground_height(e.x, e.z) + e.height, e.z};
    fx.forward = {e.tx - e.x, 0, e.tz - e.z};
    fx.inst = std::make_unique<VfxInstance>(*sys, frame_at(fx.pos, fx.forward), 1.f, std::array<float, 4>{1, 1, 1, 1}, g_vfx.rng());
    fx.inst->set_target({e.tx, fx.pos.y, e.tz});
    g_ground_fx[e.id] = {fx.serial, e.seconds > 0 ? now + e.seconds : -1.0};
    g_combat_fx.push_back(std::move(fx));
  }
  g_conn.ground_effects.clear();
  for (auto it = g_ground_fx.begin(); it != g_ground_fx.end();) {
    if (it->second.second >= 0 && now >= it->second.second) {
      end_unit_fx(it->second.first, false);
      it = g_ground_fx.erase(it);
    } else {
      ++it;
    }
  }
  for (auto it = g_script_fx.begin(); it != g_script_fx.end();) {
    if (it->second.second >= 0 && now >= it->second.second) {
      end_unit_fx(it->second.first, false);
      it = g_script_fx.erase(it);
    } else {
      ++it;
    }
  }
}

void update_combat_fx(double now, float dt) {
  // new missiles: their effect leaves the caster's start bone (mStartBoneName); a late message catches up
  for (const Connection::Missile& m : g_conn.missiles) {
    auto a = g_conn.units.find(m.from), b = g_conn.units.find(m.to);
    if (a == g_conn.units.end() || b == g_conn.units.end()) continue;
    const CharacterRecordData* r = record_of(a->second.skin);
    const AttackSlot* slot = r ? find_attack(*r, m.spell) : nullptr;
    const VfxSystemDef* sys = slot ? effect_of(a->second, slot->missile_effect) : nullptr;
    if (!sys) continue;
    CombatFx fx;
    fx.flying = true, fx.from = m.from, fx.to = m.to, fx.spell = m.spell, fx.slot = slot;
    if (!bone_world(m.from, slot->start_bone, fx.pos)) fx.pos = {a->second.x, g_map.ground_height(a->second.x, a->second.z) + 100.f, a->second.z};
    const float3 t = missile_target(b->second, *slot);
    fx.forward = {t.x - fx.pos.x, t.y - fx.pos.y, t.z - fx.pos.z};
    fx.inst = std::make_unique<VfxInstance>(*sys, missile_frame(fx.pos, fx.forward), 1.f, std::array<float, 4>{1, 1, 1, 1}, g_vfx.rng());
    g_combat_fx.push_back(std::move(fx));
  }
  g_conn.missiles.clear();
  // missiles in flight: FixedSpeedMovement toward the target, facing their velocity (VeritcalFacingMatchVelocity)
  for (CombatFx& fx : g_combat_fx) {
    if (!fx.flying || !fx.slot) continue;  // (a spell's missile is moved by update_spell_fx)
    auto t = g_conn.units.find(fx.to);
    if (t == g_conn.units.end()) {
      fx.flying = false, fx.inst->stop();
      continue;
    }
    const float3 goal = missile_target(t->second, *fx.slot);
    const float3 d{goal.x - fx.pos.x, goal.y - fx.pos.y, goal.z - fx.pos.z};
    const float len = std::sqrt(d.x * d.x + d.y * d.y + d.z * d.z);
    const float step = fx.slot->missile_speed * dt;
    if (len > 1e-3f) fx.forward = d;
    if (len <= step) {
      // DestroyOnMovementComplete: the effect stops emitting; RenderParticlesAfterDestroy [meta default true] lets
      // its particles finish
      fx.pos = goal, fx.flying = false;
      fx.inst->set_frame(missile_frame(fx.pos, fx.forward));
      fx.inst->stop();
      continue;
    }
    fx.pos = {fx.pos.x + d.x / len * step, fx.pos.y + d.y / len * step, fx.pos.z + d.z / len * step};
    fx.inst->set_frame(missile_frame(fx.pos, fx.forward));
  }
  // hits: the attack's hit effect on the target's hit bone (else at its feet), facing from the attacker to the target
  // [de măsurat: mHitEffectOrientType 1 / 2, and whether the effect follows the bone]
  for (const Connection::Hit& h : g_conn.hits) {
    auto s = g_conn.units.find(h.source), t = g_conn.units.find(h.target);
    if (s == g_conn.units.end() || t == g_conn.units.end()) continue;
    for (CombatFx& fx : g_combat_fx)
      if (fx.flying && fx.from == h.source && fx.to == h.target && fx.spell == h.spell) fx.flying = false, fx.inst->stop();
    const CharacterRecordData* r = record_of(s->second.skin);
    const AttackSlot* slot = r ? find_attack(*r, h.spell) : nullptr;
    const VfxSystemDef* sys = slot ? effect_of(s->second, slot->hit_effect) : nullptr;
    if (!sys) continue;
    CombatFx fx;
    fx.on_unit = h.target, fx.bone = slot->hit_bone;
    if (!bone_world(h.target, fx.bone, fx.pos)) fx.pos = {t->second.x, g_map.ground_height(t->second.x, t->second.z), t->second.z};
    fx.forward = {t->second.x - s->second.x, 0, t->second.z - s->second.z};
    fx.inst = std::make_unique<VfxInstance>(*sys, frame_at(fx.pos, fx.forward), 1.f, std::array<float, 4>{1, 1, 1, 1}, g_vfx.rng());
    g_combat_fx.push_back(std::move(fx));
  }
  g_conn.hits.clear();
  for (CombatFx& fx : g_combat_fx) {
    if (fx.of_unit && fx.on_unit) {
      // on its unit: at the bone (the unit's feet without one), turned the way the unit faces [de măsurat: whether
      // the effect takes the bone's own orientation]
      auto u = g_conn.units.find(fx.on_unit);
      if (u == g_conn.units.end()) {
        fx.inst->stop(), fx.on_unit = 0;
      } else {
        if (!bone_world(fx.on_unit, fx.bone, fx.pos)) fx.pos = {u->second.x, g_map.ground_height(u->second.x, u->second.z), u->second.z};
        fx.forward = {std::sin(u->second.facing), 0, std::cos(u->second.facing)};
        fx.inst->set_frame(frame_at(fx.pos, fx.forward));
      }
    } else if (fx.on_unit && bone_world(fx.on_unit, fx.bone, fx.pos)) {
      fx.inst->set_frame(frame_at(fx.pos, fx.forward));
    }
    fx.inst->update(std::min(dt, 0.05f));
  }
  std::erase_if(g_combat_fx, [](const CombatFx& fx) { return fx.kill || (!fx.flying && fx.inst->finished()); });
  (void)now;
}

/** The particle effects the map places (MapParticle in the geometry's materials.bin). All of them start with the match
 *  and keep playing; only those near the camera are drawn. */
struct MapEffects {
  struct Slot {
    const VfxSystemDef* sys = nullptr;
    VfxFrame frame;
    float scale = 1;
    std::array<float, 4> tint{1, 1, 1, 1};  // MapParticle colorModulate
    std::unique_ptr<VfxInstance> inst;
  };
  std::vector<Slot> slots;
  float check = 1;
  std::vector<std::string> skip;  // --map-fx-skip a,b: map effects whose system's name holds one of these are not drawn (checks)

  /** Whether a map visibility controller shows its objects in a plain match: flag controllers say DefaultVisible (the
   *  elemental terrains say 0), mutator controllers need an event's mutator (none is on), child controllers combine
   *  their parents (ParentMode 1 taken as "any", others as "all" — the modes are not documented). */
  static bool shown(const PropertyBin& bin, uint32_t controller) { return MapView::controller_shown(bin, controller); }

  void load(const PropertyBin& mats) {
    // chunks (placeable containers) a controller hides: MapContainer's chunk / VisibilityController pairs
    std::vector<uint32_t> hidden_chunks;
    for (const BinEntry& e : mats.entries()) {
      const BinValue* components = e.field("components");
      if (!components) continue;
      for (const BinValue& c : components->items)
        for (const BinField& f : c.fields)
          for (const BinValue& pair : f.value.items) {
            const BinValue* chunk = pair.field("chunk");
            const BinValue* ctl = pair.field("VisibilityController");
            if (chunk && ctl && !shown(mats, static_cast<uint32_t>(ctl->u))) hidden_chunks.push_back(static_cast<uint32_t>(chunk->u));
          }
    }
    for (const BinEntry& e : mats.entries()) {
      const BinValue* items = e.field("items");
      if (!items) continue;
      if (std::find(hidden_chunks.begin(), hidden_chunks.end(), e.name) != hidden_chunks.end()) continue;
      for (const auto& [key, item] : items->pairs) {
        if (item.cls != fnv1a("MapParticle")) continue;
        // only what every Rift shows: no visibility flags, or bit 0 (the others are the elemental terrains)
        if (const BinValue* vf = item.field("mVisibilityFlags"))
          if (!(static_cast<uint32_t>(vf->number()) & 1)) continue;
        if (const BinValue* ctl = item.field("VisibilityController"))
          if (!shown(mats, static_cast<uint32_t>(ctl->u))) continue;
        const BinValue* sys = item.field("system");
        const BinValue* tr = item.field("transform");
        if (!sys || !tr) continue;
        Slot s;
        s.sys = g_vfx.system(static_cast<uint32_t>(sys->u));
        if (!s.sys) continue;
        if (const BinValue* cm = item.field("colorModulate"))
          for (size_t k = 0; k < 4; ++k) s.tint[k] = static_cast<float>(cm->num[k]);
        // League's matrix: row vectors, translation in the last row; its rows carry the scale
        const auto& M = tr->num;
        s.scale = static_cast<float>(std::sqrt(M[0] * M[0] + M[1] * M[1] + M[2] * M[2]));
        const float k = s.scale > 0 ? 1.f / s.scale : 1.f;
        for (int r = 0; r < 3; ++r)
          for (int c = 0; c < 3; ++c) s.frame.m[static_cast<size_t>(r * 3 + c)] = static_cast<float>(M[static_cast<size_t>(c * 4 + r)]) * k;
        s.frame.x = static_cast<float>(M[12]), s.frame.y = static_cast<float>(M[13]), s.frame.z = static_cast<float>(M[14]);
        slots.push_back(std::move(s));
      }
    }
  }

  /** Starts every effect, then plays `seconds` of the match in 30 steps a second (the effects of a match already
   *  under way). */
  void start(float seconds) {
    for (Slot& s : slots) s.inst = std::make_unique<VfxInstance>(*s.sys, s.frame, s.scale, s.tint, g_vfx.rng());
    for (float t = 0; t < seconds; t += 1.f / 30.f)
      for (Slot& s : slots) s.inst->update(1.f / 30.f);
  }

  void update(float dt) {
    for (Slot& s : slots)
      if (s.inst && !s.inst->finished()) s.inst->update(std::min(dt, 0.05f));
  }

  /** The effects whose bounding sphere (the system's visibilityRadius, scaled with the placement) touches the camera's
   *  view: they all run all the time, only what the camera cannot see is not drawn. (A circle around the camera's
   *  target made effects at the screen's edge appear and vanish as the camera moved: the river's lilies, the Baron
   *  pit's glow.) */
  std::vector<VfxInstance*> visible(const float4x4& view, float aspect) {
    std::vector<VfxInstance*> out;
    const float ty = std::tan(kFov * 0.5f), tx = ty * aspect;
    const float cy = 1.f / std::sqrt(1.f + ty * ty), cx = 1.f / std::sqrt(1.f + tx * tx);
    for (Slot& s : slots) {
      if (!s.inst) continue;
      if (std::any_of(skip.begin(), skip.end(), [&](const std::string& k) { return s.sys->name.find(k) != std::string::npos; })) continue;
      const float r = s.sys->visibility_radius * s.scale;
      const float3 v = transform_point(float3{s.frame.x, s.frame.y, s.frame.z}, view);
      // the distance of the centre outside each side plane of the frustum (through the eye): (|x| - z tan a) cos a
      if (v.z < -r) continue;
      if ((std::fabs(v.x) - v.z * tx) * cx > r || (std::fabs(v.y) - v.z * ty) * cy > r) continue;
      out.push_back(s.inst.get());
    }
    return out;
  }
};
MapEffects g_map_fx;

/** The map's level props (GdsMapObject type 10, group "Level Props" of the geometry's materials.bin): characters the
 *  map itself places and animates: every brush (brush_sru_a .. h), the two shopkeepers, the Rift's critters and
 *  banners. Each is drawn as its character's skin at the object's own transform. [observat: a 13.3 replay frame draws
 *  each brush as a skinned mesh (lit_uber, TINTING permutation) whose first bone sits exactly on a placed object] */
struct LevelProps {
  struct Prop {
    const CharacterModel* model = nullptr;
    float4x4 place;
    float3 centre;       // of the sphere the camera test uses
    float radius = 0;
    float tint[3] = {1, 1, 1};
    float phase = 0;     // seconds into its standing clip when the match starts
    std::string name;
  };
  std::vector<Prop> props;
  size_t drawn = 0;

  /** Whether a character is an esports one (its bin's SkinCharacterMetaDataProperties eSportCharacter: the banners
   *  that carry a team's logo in broadcasts). A plain match does not show them. [observat: none among the draws of
   *  the 13.3 replay frames, with the replay's `banners` setting on] */
  static bool esport_character(const std::string& character) {
    const Wad* wad = wad_of(character);
    if (!wad) return false;
    std::string c = character;
    for (char& ch : c) ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
    const auto bytes = wad->read("data/characters/" + c + "/" + c + ".bin");
    if (!bytes) return false;
    try {
      const PropertyBin bin(*bytes);
      for (const BinEntry& e : bin.entries())
        if (const BinValue* v = e.field("eSportCharacter"); v && v->number() != 0) return true;
    } catch (const std::exception&) {
    }
    return false;
  }

  void load(const PropertyBin& mats) {
    for (const MapObject& o : map_objects(mats)) {
      if (o.type != 10 || o.skin.empty() || !o.on_plain_rift()) continue;
      // "Characters/brush_sru_a/Skins/Skin0"
      const size_t a = o.skin.find('/'), b = o.skin.find('/', a + 1), s = o.skin.rfind("Skin");
      if (a == std::string::npos || b == std::string::npos || s == std::string::npos) continue;
      const std::string character = o.skin.substr(a + 1, b - a - 1);
      static std::map<std::string, bool> esport;
      auto known = esport.find(character);
      if (known == esport.end()) known = esport.emplace(character, esport_character(character)).first;
      if (known->second) continue;
      Prop p;
      p.model = model_of(character, std::atoi(o.skin.c_str() + s + 4));
      if (!p.model) continue;
      for (int r = 0; r < 4; ++r)
        for (int c = 0; c < 4; ++c) p.place.m[r][c] = o.matrix[r * 4 + c];
      const bool box = o.box_max[0] > o.box_min[0];
      if (box) {
        p.centre = {(o.box_min[0] + o.box_max[0]) * 0.5f, (o.box_min[1] + o.box_max[1]) * 0.5f, (o.box_min[2] + o.box_max[2]) * 0.5f};
        const float dx = o.box_max[0] - o.box_min[0], dy = o.box_max[1] - o.box_min[1], dz = o.box_max[2] - o.box_min[2];
        p.radius = 0.5f * std::sqrt(dx * dx + dy * dy + dz * dz);
      } else {
        p.centre = {o.x, o.y + 100.f, o.z};
        p.radius = 300.f;  // objects without a box: wide enough for the largest prop (a camera test, not a rule)
      }
      const bool brush = o.name.find("brush") != std::string::npos;
      if (brush) g_map.grass_tint_at(o.x, o.z, p.tint);
      // instances of one brush model are out of step in the real client [observat: same frame, same model, different
      // bone rotations]; where each starts is not in the data: spread by the object's name [de măsurat]
      p.phase = static_cast<float>(fnv1a(o.name) % 10000u) / 10000.f * 20.f;
      p.name = o.name;
      props.push_back(std::move(p));
    }
  }

  void draw(const float4x4& vp, const float4x4& view, float aspect, double now) {
    const float ty = std::tan(kFov * 0.5f), tx = ty * aspect;
    const float cy = 1.f / std::sqrt(1.f + ty * ty), cx = 1.f / std::sqrt(1.f + tx * tx);
    drawn = 0;
    for (const Prop& p : props) {
      const float3 v = transform_point(p.centre, view);
      if (v.z < -p.radius) continue;
      if ((std::fabs(v.x) - v.z * tx) * cx > p.radius || (std::fabs(v.y) - v.z * ty) * cy > p.radius) continue;
      CharacterInstance ci;
      ci.model = p.model;
      ci.place = &p.place;
      ci.clip = "Idle1";
      ci.time = static_cast<float>(now) + p.phase;
      std::memcpy(ci.tint, p.tint, sizeof ci.tint);
      g_chars.draw(g_gpu, vp, ci);
      ++drawn;
    }
  }
};
LevelProps g_level_props;

/** Where each structure stands and how large: its map object's own height and scale (GdsMapObject type 3 barracks,
 *  4 HQ, 5 turret; the transform's rows carry the scale), not the ground's. The Chaos fountain turret
 *  (Turret_ChaosTurretShrine, drawn as SRUAP_MageCrystal) floats at the statue's chest, 466 up, at half size.
 *  [măsurat: the 13.3 replay draws the crystal's root bone at y 466.004 with a 0.5 scale; on the ground and at full
 *  size it was inside the statue's base] */
std::vector<std::array<float, 4>> g_structure_heights;  // x, z, y, scale
bool structure_height(float x, float z, float& y, float& scale) {
  for (const auto& s : g_structure_heights)
    if (std::fabs(s[0] - x) < 2.f && std::fabs(s[1] - z) < 2.f) return y = s[2], scale = s[3], true;
  return false;
}
SpawnPoint g_spawn;  // Order's spawn locator (__Spawn_T1)
Camera g_cam;
bool g_follow = true;
POINT g_mouse{};  // the cursor in the window

/** The enemy under a screen pixel: the eye's ray against each living enemy's selection cylinder (CharacterRecord
 *  selectionRadius / selectionHeight, standing on the ground); the nearest to the eye wins. Only units the server gave
 *  health can be attacked. [de măsurat: League's exact pick shape and priorities] */
uint32_t enemy_under(int px, int py) {
  const auto me = g_conn.units.find(g_conn.my_unit);
  if (me == g_conn.units.end()) return 0;
  const float3 dir = g_cam.ray(px, py, g_gpu.width(), g_gpu.height());
  uint32_t best = 0;
  float best_t = 1e30f;
  for (const auto& [id, u] : g_conn.units) {
    if (u.dead || u.max_hp <= 0 || u.team == me->second.team) continue;
    const CharacterRecordData* r = record_of(u.skin);
    if (!r || r->selection_radius <= 0) continue;
    const float ground = g_map.ground_height(u.x, u.z);
    // the stretch of the ray between the cylinder's bottom and top
    if (std::fabs(dir.y) < 1e-5f) continue;
    float t0 = (ground + r->selection_height - g_cam.eye.y) / dir.y, t1 = (ground - g_cam.eye.y) / dir.y;
    if (t0 > t1) std::swap(t0, t1);
    t0 = std::max(t0, 0.f);
    if (t1 <= t0) continue;
    // the closest horizontal approach to the unit's axis on that stretch
    const float ox = g_cam.eye.x - u.x, oz = g_cam.eye.z - u.z;
    const float a = dir.x * dir.x + dir.z * dir.z;
    const float t = a > 1e-8f ? std::clamp(-(ox * dir.x + oz * dir.z) / a, t0, t1) : t0;
    const float hx = ox + dir.x * t, hz = oz + dir.z * t;
    if (hx * hx + hz * hz <= r->selection_radius * r->selection_radius && t < best_t) best = id, best_t = t;
  }
  return best;
}

/** The nearest living enemy that can be attacked, or the nearest enemy turret (scripted checks). */
uint32_t nearest_enemy(bool turret = false) {
  const auto me = g_conn.units.find(g_conn.my_unit);
  if (me == g_conn.units.end()) return 0;
  uint32_t best = 0;
  float best_d = 1e30f;
  for (const auto& [id, u] : g_conn.units) {
    if (u.dead || u.max_hp <= 0 || u.team == me->second.team) continue;
    if (turret && u.skin != "Turret") continue;
    const float d = std::hypot(u.x - me->second.x, u.z - me->second.z);
    if (d < best_d) best = id, best_d = d;
  }
  return best;
}

uint32_t g_selected_target = 0;

/** Any living unit under a screen pixel (for selection into TargetFrame). */
uint32_t unit_under(int px, int py) {
  const float3 dir = g_cam.ray(px, py, g_gpu.width(), g_gpu.height());
  uint32_t best = 0;
  float best_t = 1e30f;
  for (const auto& [id, u] : g_conn.units) {
    if (u.dead || u.max_hp <= 0) continue;
    const CharacterRecordData* r = record_of(u.skin);
    if (!r || r->selection_radius <= 0) continue;
    const float ground = g_map.ground_height(u.x, u.z);
    if (std::fabs(dir.y) < 1e-5f) continue;
    float t0 = (ground + r->selection_height - g_cam.eye.y) / dir.y, t1 = (ground - g_cam.eye.y) / dir.y;
    if (t0 > t1) std::swap(t0, t1);
    t0 = std::max(t0, 0.f);
    if (t1 <= t0) continue;
    const float ox = g_cam.eye.x - u.x, oz = g_cam.eye.z - u.z;
    const float a = dir.x * dir.x + dir.z * dir.z;
    const float t = a > 1e-8f ? std::clamp(-(ox * dir.x + oz * dir.z) / a, t0, t1) : t0;
    const float hx = ox + dir.x * t, hz = oz + dir.z * t;
    if (hx * hx + hz * hz <= r->selection_radius * r->selection_radius && t < best_t) best = id, best_t = t;
  }
  return best;
}

std::filesystem::path find_data(const std::string& arg) { return find_game_data(arg, std::filesystem::current_path()); }

LRESULT CALLBACK wndproc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
  // while the match loads there is no interface to click and no champion to order
  if (g_loading_on && msg != WM_SIZE && msg != WM_DESTROY) return DefWindowProcW(hwnd, msg, wp, lp);
  switch (msg) {
    case WM_SIZE:
      g_gpu.resize(LOWORD(lp), HIWORD(lp));
      return 0;
    case WM_LBUTTONDOWN: {
      const int mx = GET_X_LPARAM(lp), my = GET_Y_LPARAM(lp);
      float wx = 0, wz = 0;
      if (g_hud_on && g_hud.minimap_hit(g_gpu, mx, my, wx, wz)) {
        g_cam.x = wx;
        g_cam.z = wz;
        g_follow = false;
        return 0;
      }
      // the shop: pick an item, its buttons; the inventory: pick a slot (to sell)
      if (g_hud_on && g_shop_open) {
        int item = 0;
        const int hit = g_hud.shop_hit(g_gpu, mx, my, &item);
        if (item) g_shop_selected = item, g_inv_selected = -1;
        if (hit == Hud::kShopPurchase && g_shop_selected) g_conn.buy_item(static_cast<uint32_t>(g_shop_selected));
        if (hit == Hud::kShopSell && g_inv_selected >= 0) g_conn.sell_item(static_cast<uint8_t>(g_inv_selected)), g_inv_selected = -1;
        if (hit == Hud::kShopClose) g_shop_open = false;
        if (hit != Hud::kShopNothing) return 0;
        const int slot = g_hud.inventory_slot_at(g_gpu, mx, my);
        if (slot >= 0) {
          g_inv_selected = slot, g_shop_selected = 0;
          return 0;
        }
      }
      // a level-up button of the interface
      const int slot = g_hud_on ? g_hud.level_button_at(g_gpu, mx, my) : -1;
      if (slot >= 0) {
        g_conn.level_spell(static_cast<uint8_t>(slot));
        return 0;
      }
      g_selected_target = unit_under(mx, my);
      return 0;
    }
    case WM_RBUTTONDOWN: {
      const int mx = GET_X_LPARAM(lp), my = GET_Y_LPARAM(lp);
      float wx = 0, wz = 0;
      if (g_hud_on && g_hud.minimap_hit(g_gpu, mx, my, wx, wz)) {
        g_conn.move(wx, wz);
        return 0;
      }
      // the shop: a right click buys the item under it, sells the inventory item under it (documented: Shop)
      if (g_hud_on && g_shop_open) {
        int item = 0;
        const int hit = g_hud.shop_hit(g_gpu, mx, my, &item);
        if (item) {
          g_conn.buy_item(static_cast<uint32_t>(item));
          return 0;
        }
        if (hit != Hud::kShopNothing) return 0;
        const int slot = g_hud.inventory_slot_at(g_gpu, mx, my);
        if (slot >= 0) {
          g_conn.sell_item(static_cast<uint8_t>(slot));
          return 0;
        }
      }
      // League's right click: an enemy under the cursor is attacked, anywhere else is walked to
      if (const uint32_t enemy = enemy_under(mx, my)) {
        g_conn.attack(enemy);
        return 0;
      }
      float x = 0, z = 0;
      if (g_cam.pick(mx, my, g_gpu.width(), g_gpu.height(), g_map.ground_height(g_cam.x, g_cam.z), x, z)) g_conn.move(x, z);
      return 0;
    }
    case WM_MOUSEMOVE:
      g_mouse = {GET_X_LPARAM(lp), GET_Y_LPARAM(lp)};
      return DefWindowProcW(hwnd, msg, wp, lp);
    case WM_MOUSEWHEEL:
      // over the shop: its item list scrolls, a row a notch
      if (g_hud_on && g_shop_open && g_hud.shop_hit(g_gpu, g_mouse.x, g_mouse.y, nullptr) != Hud::kShopNothing) {
        g_hud.scroll_shop(GET_WHEEL_DELTA_WPARAM(wp) > 0 ? -1 : 1);
        return 0;
      }
      // [de măsurat: how far one wheel notch zooms]
      g_cam.target = std::clamp(g_cam.target - static_cast<float>(GET_WHEEL_DELTA_WPARAM(wp)) * 0.8f, Camera::kZoomMin, Camera::kZoomMax);
      return 0;
    case WM_KEYDOWN:
      if (wp == 'Y') g_follow = !g_follow;  // League's camera lock
      // P opens and closes the shop (League's default); Esc closes it, else leaves the game
      if (wp == 'P' && !(lp & (1 << 30))) g_shop_open = !g_shop_open, g_inv_selected = -1;
      if (wp == VK_ESCAPE) {
        if (g_shop_open) g_shop_open = false;
        else PostQuitMessage(0);
      }
      if (wp == 'Q' || wp == 'W' || wp == 'E' || wp == 'R') {
        // a spell: with Ctrl a skill point goes into it (League's default), else it is cast at the cursor at once
        // (League's "quick cast") with the enemy under the cursor as its target if there is one
        const uint8_t slot = wp == 'Q' ? 0 : wp == 'W' ? 1 : wp == 'E' ? 2 : 3;
        if (GetKeyState(VK_CONTROL) < 0) {
          g_conn.level_spell(slot);
        } else if (!(lp & (1 << 30))) {  // not the key's auto-repeat
          float x = 0, z = 0;
          if (g_cam.pick(g_mouse.x, g_mouse.y, g_gpu.width(), g_gpu.height(), g_map.ground_height(g_cam.x, g_cam.z), x, z))
            g_conn.cast(slot, x, z, enemy_under(g_mouse.x, g_mouse.y));
        }
      }
      if (wp >= '1' && wp <= '7' && !(lp & (1 << 30))) {
        int item_slot = -1;
        if (wp == '1') item_slot = 0;
        else if (wp == '2') item_slot = 1;
        else if (wp == '3') item_slot = 2;
        else if (wp == '5') item_slot = 3;
        else if (wp == '6') item_slot = 4;
        else if (wp == '7') item_slot = 5;
        else if (wp == '4') item_slot = 6;
        if (item_slot >= 0) {
          float x = 0, z = 0;
          g_cam.pick(g_mouse.x, g_mouse.y, g_gpu.width(), g_gpu.height(), g_map.ground_height(g_cam.x, g_cam.z), x, z);
          uint32_t target = enemy_under(g_mouse.x, g_mouse.y);
          g_conn.use_item(static_cast<uint8_t>(item_slot), x, z, target);
        }
      }
      if (wp == VK_SPACE) {
        if (auto m = g_conn.units.find(g_conn.my_unit); m != g_conn.units.end()) {
          g_cam.x = m->second.x;
          g_cam.z = m->second.z;
        }
      }
      if (wp == 'T') {
        // the Practice Tool's "spawn target dummy" (a button there; the key is our choice) at the cursor
        float x = 0, z = 0;
        if (g_cam.pick(g_mouse.x, g_mouse.y, g_gpu.width(), g_gpu.height(), g_map.ground_height(g_cam.x, g_cam.z), x, z)) g_conn.spawn_dummy(x, z);
      }
      return 0;
    case WM_DESTROY:
      PostQuitMessage(0);
      return 0;
    default:
      return DefWindowProcW(hwnd, msg, wp, lp);
  }
}

}  // namespace

int WINAPI wWinMain(HINSTANCE inst, HINSTANCE, PWSTR, int show) {
  std::string host = "127.0.0.1", name = "Player", data_arg, shot;
  int shot_frames = 120;
  std::string fps_file;
  double fps_seconds = 10;
  bool riot_shaders = true;
  double shot_seconds = -1;  // --shot-seconds S: the shot is taken S seconds after joining the match (checks)
  int shot_count = 1;        // --shot-count N --shot-interval S: N shots S seconds apart (name_0.bmp, name_1.bmp ...)
  double shot_interval = 2;
  int shot_missile = -1;  // --shot-missile N: the shot is taken N frames after the first attack effect (missile or hit) starts (checks)
  bool fxaa = true;  // --fxaa 0: no anti-aliasing (comparisons)
  bool hud = true;   // --hud 0: no interface (comparisons)
  bool dump_light = false;  // --dump-light 1: writes the character light to light.txt and exits
  std::string dump_clip;  // --dump-pose <clip> --dump-time <s>: writes every joint's model-space position and exits
  std::string match_pose;
  int dump_skin = 0;      // --dump-skin <n>: the skin of the --champion character whose pose is written ("bind" as clip: the bind pose)
  float dump_time = 0;
  std::string preview_clip;  // draws Garen at the camera target playing this clip (checks without a server)
  float preview_yaw = 0;
  float auto_x = -1, auto_z = -1;  // sends one move order once connected (end-to-end checks)
  // --moves "t,x,z;t,x,z": move orders sent t seconds after joining; --record <dir> --record-seconds S: every frame as BMP
  struct TimedMove {
    double t;
    float x, z;
    char kind = 'm';  // m: move to x,z; d: target dummy at the champion + (x, z); a: attack the nearest enemy;
                      // l: a skill point into spell x; c: cast spell x at the nearest enemy
  };
  std::vector<TimedMove> moves;
  std::string record_dir;
  double record_seconds = 0;
  // --offline: no server; one champion walks the --moves itself, on a virtual clock of exactly 30 frames a second (clips)
  bool offline = false;
  // --replay <file.barp>: plays a Riot replay's packets (tools/sponge/export_replay.py); --offline-start S seeks to S
  // seconds. With --shot the clock is the virtual one (30 frames a second), otherwise it runs in real time
  std::string replay_path;
  double offline_start = 0;  // --offline-start S: the virtual clock starts at S seconds (structures already standing)
  float spawn_x = -1, spawn_z = -1;  // --spawn-x / -z: offline start (else the team's spawn locator)
  std::string champion = "Garen";      // --champion: who the player plays (Garen, Lux, Ashe, Tryndamere, Zed)
  int summoner_icon = 29;              // --icon: the summoner's icon (29: the one a new account has)
  // --loading-shot <file> --loading-shot-at F: saves the loading screen once its progress reaches F (checks);
  // --load-log <file>: how long each loading stage took
  std::string loading_shot, load_log;
  float loading_shot_at = 0.5f;
  float cam_x = -1, cam_z = -1;
  uint16_t port = net::kDefaultPort;
  // wWinMain: the arguments are wide strings (__wargv); they are plain ASCII here.
  auto narrow = [](const wchar_t* w) {
    std::string s;
    for (; *w; ++w) s.push_back(static_cast<char>(*w));
    return s;
  };
  for (int i = 1; i + 1 < __argc; i += 2) {
    const std::string k = narrow(__wargv[i]);
    const std::string v = narrow(__wargv[i + 1]);
    if (k == "--host") host = v;
    else if (k == "--port") port = static_cast<uint16_t>(std::stoi(v));
    else if (k == "--name") name = v;
    else if (k == "--champion") champion = v;
    else if (k == "--icon") summoner_icon = std::stoi(v);
    else if (k == "--loading-shot") loading_shot = v;
    else if (k == "--loading-shot-at") loading_shot_at = std::stof(v);
    else if (k == "--load-log") load_log = v;
    else if (k == "--map-fx-skip") {
      for (size_t at = 0; at <= v.size();) {
        size_t end = v.find(',', at);
        if (end == std::string::npos) end = v.size();
        if (end > at) g_map_fx.skip.push_back(v.substr(at, end - at));
        at = end + 1;
      }
    }
    else if (k == "--data") data_arg = v;
    else if (k == "--shot") shot = v;  // save a frame as BMP and quit (checks without a screen)
    else if (k == "--shot-frames") shot_frames = std::stoi(v);
    else if (k == "--shot-missile") shot_missile = std::stoi(v);
    else if (k == "--shot-seconds") shot_seconds = std::stod(v);
    else if (k == "--shot-count") shot_count = std::stoi(v);
    else if (k == "--shot-interval") shot_interval = std::stod(v);
    else if (k == "--cam-x") cam_x = std::stof(v);
    else if (k == "--cam-z") cam_z = std::stof(v);
    else if (k == "--zoom") g_cam.distance = g_cam.target = std::stof(v);
    else if (k == "--eye") g_cam.fixed = std::sscanf(v.c_str(), "%f,%f,%f", &g_cam.fixed_eye.x, &g_cam.fixed_eye.y, &g_cam.fixed_eye.z) == 3;
    else if (k == "--preview") preview_clip = v;
    else if (k == "--dump-pose") dump_clip = v;
    else if (k == "--match-pose") match_pose = v;
    else if (k == "--dump-skin") dump_skin = std::stoi(v);
    else if (k == "--dump-light") dump_light = v == "1";
    else if (k == "--fxaa") fxaa = v != "0";
    else if (k == "--hud") hud = v != "0";
    else if (k == "--dump-time") dump_time = std::stof(v);
    else if (k == "--preview-yaw") preview_yaw = std::stof(v);
    else if (k == "--auto-move-x") auto_x = std::stof(v);
    else if (k == "--auto-move-z") auto_z = std::stof(v);
    else if (k == "--record") record_dir = v;
    else if (k == "--offline") offline = v == "1";
    else if (k == "--replay") replay_path = v, offline = true;
    else if (k == "--offline-start") offline_start = std::stod(v);
    else if (k == "--spawn-x") spawn_x = std::stof(v);
    else if (k == "--turret-clip") g_turret_clip_test = v;
    else if (k == "--shop-open") g_shop_open = v == "1", g_shop_selected = v == "1" ? 3031 : 0;  // checks: the shop open (Infinity Edge picked)
    else if (k == "--shop-scroll") g_hud.scroll_shop(std::stoi(v));  // checks: the shop's list scrolled by rows
    else if (k == "--structure-yaw") g_structure_yaw_test = std::sscanf(v.c_str(), "%f,%f", &g_structure_yaw[0], &g_structure_yaw[1]) == 2;
    else if (k == "--spawn-z") spawn_z = std::stof(v);
    else if (k == "--record-seconds") record_seconds = std::stod(v);
    else if (k == "--fps-file") fps_file = v;  // with --fps-seconds S: frames per second over S seconds, then quit
    else if (k == "--fps-seconds") fps_seconds = std::stod(v);
    else if (k == "--env-quality") g_map.low_quality = v != "high";  // low (default, the player's setting) | high
    else if (k == "--riot-shaders") riot_shaders = v != "0";  // 0: the map's fallback shader (comparisons)
    else if (k == "--moves") {
      size_t at = 0;
      while (at < v.size()) {
        size_t end = v.find(';', at);
        if (end == std::string::npos) end = v.size();
        const std::string item = v.substr(at, end - at);
        float t = 0, x = 0, z = 0;
        if (item.rfind("d:", 0) == 0 && std::sscanf(item.c_str() + 2, "%f,%f,%f", &t, &x, &z) == 3) moves.push_back({t, x, z, 'd'});
        else if (item.rfind("a:", 0) == 0 && std::sscanf(item.c_str() + 2, "%f", &t) == 1) moves.push_back({t, 0, 0, 'a'});
        else if (item.rfind("s:", 0) == 0 && std::sscanf(item.c_str() + 2, "%f", &t) == 1) moves.push_back({t, 0, 0, 's'});
        else if (item.rfind("l:", 0) == 0 && std::sscanf(item.c_str() + 2, "%f,%f", &t, &x) == 2) moves.push_back({t, x, 0, 'l'});
        else if (item.rfind("c:", 0) == 0 && std::sscanf(item.c_str() + 2, "%f,%f", &t, &x) == 2) moves.push_back({t, x, 0, 'c'});
        else if (item.rfind("b:", 0) == 0 && std::sscanf(item.c_str() + 2, "%f,%f", &t, &x) == 2) moves.push_back({t, x, 0, 'b'});  // buy item x
        else if (item.rfind("x:", 0) == 0 && std::sscanf(item.c_str() + 2, "%f,%f", &t, &x) == 2) moves.push_back({t, x, 0, 'x'});  // sell slot x
        else if (std::sscanf(item.c_str(), "%f,%f,%f", &t, &x, &z) == 3) moves.push_back({t, x, z});
        at = end + 1;
      }
    }
  }

  WNDCLASSW wc{};
  wc.lpfnWndProc = wndproc;
  wc.hInstance = inst;
  wc.hCursor = LoadCursor(nullptr, IDC_ARROW);
  wc.lpszClassName = L"BattleArenaClient";
  RegisterClassW(&wc);
  HWND hwnd = CreateWindowW(wc.lpszClassName, L"BattleArena", WS_OVERLAPPEDWINDOW, CW_USEDEFAULT, CW_USEDEFAULT, 1600, 900, nullptr, nullptr,
                            inst, nullptr);
  RECT rc{};
  GetClientRect(hwnd, &rc);
  if (!g_gpu.init(hwnd, rc.right - rc.left, rc.bottom - rc.top)) {
    MessageBoxW(hwnd, L"DirectX 11 (feature level 11_0) is not available.", L"BattleArena", MB_ICONERROR);
    return 1;
  }
  ShowWindow(hwnd, shot.empty() && record_dir.empty() ? show : SW_SHOWNOACTIVATE);  // scripted checks do not take the focus

  const std::filesystem::path data = find_data(data_arg) / "DATA" / "FINAL";
  std::unique_ptr<Wad> map_wad;
  static std::unique_ptr<Wad> ui_wad;

  // ---- loading, behind the loading screen. League's client connects to the game server first, shows the loading
  // screen, loads, and tells the server when it is done; the server starts the match once every player is. The order
  // of the stages follows what Riot's own client logs while it loads (r3dlog, client 4.20: the level, the level's
  // objects, the items, the champions, the global effects, the interface; docs/INCARCARE.md). How much of the meter
  // each stage is worth is in no file: the shares below are what the stages took on this project's target PC.
  struct QuitWhileLoading {};
  // the held connection is serviced by a thread of its own while this one loads
  struct NetPump {
    std::atomic<bool> run{false};
    std::thread thread;
    void stop() {
      run = false;
      if (thread.joinable()) thread.join();
    }
    ~NetPump() { stop(); }
  } net_pump;
  const double load_started = seconds_now();
  double load_drawn = -1;
  bool loading_shot_done = false;
  std::vector<std::pair<std::string, double>> stage_times;
  auto load_step = [&](float fraction, bool force = false) {
    if (!g_loading_on) return;
    MSG m{};
    while (PeekMessageW(&m, nullptr, 0, 0, PM_REMOVE)) {
      if (m.message == WM_QUIT) throw QuitWhileLoading{};
      TranslateMessage(&m);
      DispatchMessageW(&m);
    }
    const double t = seconds_now();
    if (!force && t - load_drawn < 1.0 / 30.0) return;  // the spinner's 30 frames a second
    load_drawn = t;
    if (!offline) {
      if (!net_pump.run) g_conn.update(g_conn.my_unit ? static_cast<double>(g_conn.server_tick) + (t - g_conn.server_tick_at) / kTickSeconds : 0.0);
      g_loading.latency(g_conn.ping_ms());
    }
    g_loading.progress(fraction);
    g_gpu.begin(0.f, 0.f, 0.f);
    g_gpu.resolve();
    g_loading.draw(g_gpu, t - load_started);
    if (!loading_shot.empty() && !loading_shot_done && fraction >= loading_shot_at) g_gpu.save_bmp(loading_shot), loading_shot_done = true;
    g_gpu.end();
  };
  double stage_started = load_started;
  auto stage_done = [&](const char* stage, float fraction) {
    const double t = seconds_now();
    stage_times.emplace_back(stage, t - stage_started);
    stage_started = t;
    load_step(fraction, true);
  };

  try {
    map_wad = std::make_unique<Wad>(data / "Maps" / "Shipping" / "Map11.wad.client");
    g_data = data;
    g_map_wad = map_wad.get();
    if (std::filesystem::exists(data / "Global.wad.client")) g_global_wad = std::make_unique<Wad>(data / "Global.wad.client");
    {
      const auto loc = data / "Localized" / "Global.en_US.wad.client";
      if (std::filesystem::exists(loc))
        if (auto st = Wad(loc).read("data/menu/main_en_us.stringtable")) g_strings = StringTable(*st);
    }
    std::unique_ptr<PropertyBin> map_bin;
    if (auto map_bytes = map_wad->read("data/maps/shipping/map11/map11.bin")) map_bin = std::make_unique<PropertyBin>(*map_bytes);

    // the loading screen first: its scenes and atlases (UI.wad), the game mode's background (map11.bin), a card for
    // the player (the skin's loadscreen picture, the champion's name, the summoner's name and icon)
    if (std::filesystem::exists(data / "UI.wad.client")) ui_wad = std::make_unique<Wad>(data / "UI.wad.client");
    if (ui_wad && dump_clip.empty() && !dump_light && g_loading.load(g_gpu, *ui_wad)) {
      g_loading.add_wad(map_wad.get());
      if (g_global_wad) g_loading.add_wad(g_global_wad.get());
      std::string background = "assets/ux/loadingscreen/srbackground.tex";
      if (map_bin)
        for (const BinEntry& e : map_bin->entries()) {
          const BinValue* mode = e.field("mModeName");
          const BinValue* bg = e.field("LoadingScreenBackground");
          if (bg && (!mode || mode->str == "CLASSIC" || mode->u == fnv1a("CLASSIC"))) {
            background = bg->str;
            if (mode) break;
          }
        }
      g_loading.background(g_gpu, background);
      LoadingScreen::Player card;
      card.name = name;
      card.character_name = g_strings.has("game_character_displayname_" + champion) ? g_strings.get("game_character_displayname_" + champion) : champion;
      card.icon = g_loading.image(g_gpu, "assets/ux/summonericons/profileicon" + std::to_string(summoner_icon) + ".dds");
      try {
        // the skin's SkinCharacterDataProperties: loadscreen (CensoredImage) image
        std::string lower = champion;
        for (char& c : lower) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
        const Wad* cw = wad_of(champion);
        if (auto skin = cw ? cw->read("data/characters/" + lower + "/skins/skin0.bin") : std::nullopt) {
          const PropertyBin skin_bin(*skin);
          for (const BinEntry& e : skin_bin.entries())
            if (const BinValue* ls = e.field("loadscreen"))
              if (const BinValue* img = ls->field("image")) {
                g_loading.add_wad(cw);
                card.splash = g_loading.image(g_gpu, img->str);
              }
        }
      } catch (const std::exception&) {
      }
      g_loading.players({card});
      g_loading_on = true;
    }
    // connected from the start, as League's client is (the latency shown while loading is this connection's); the
    // match is joined when the loading is done
    if (!offline && g_loading_on && g_conn.connect(host.c_str(), port, name, champion, true)) {
      net_pump.run = true;
      net_pump.thread = std::thread([&net_pump] {
        while (net_pump.run) {
          g_conn.pump();
          Sleep(2);
        }
      });
    }
    load_step(0.f, true);

    // ---- 1. the level: geometry, materials, their shaders and textures, the navigation grid
    // Riot's shader library and compiled shaders draw the map's materials when the install has them
    static std::unique_ptr<Wad> shader_lib, shader_cache;
    if (riot_shaders && std::filesystem::exists(data / "Shaders" / "Shaders.wad.client")) shader_lib = std::make_unique<Wad>(data / "Shaders" / "Shaders.wad.client");
    if (std::filesystem::exists(data / "ShaderCache.dx11.wad.client")) shader_cache = std::make_unique<Wad>(data / "ShaderCache.dx11.wad.client");
    static std::unique_ptr<Wad> levels;
    if (std::filesystem::exists(data / "Maps" / "Shipping" / "Map11LEVELS.wad.client")) levels = std::make_unique<Wad>(data / "Maps" / "Shipping" / "Map11LEVELS.wad.client");
    const float kLevelShare = 0.83f, kEffectsShare = 0.86f, kObjectsShare = 0.94f, kInterfaceShare = 0.97f, kChampionShare = 0.98f;
    g_map.on_progress = [&](float f) { load_step(f * kLevelShare); };
    if (!g_map.load(g_gpu, *map_wad, shader_lib.get(), shader_cache.get(), levels.get())) throw std::runtime_error("Summoner's Rift could not be read");
    g_map.on_progress = nullptr;
    stage_done("level (geometry, materials, shaders, textures, navigation grid)", kLevelShare);

    // ---- 2. the level's effects: the particle systems of the map and where they play
    if (!g_vfx.init(g_gpu)) throw std::runtime_error("particle shader");
    g_vfx.set_depth_range(Camera::kNear, Camera::kFar);
    if (g_map.nav()) g_vfx.set_navmesh(g_gpu, *g_map.nav());
    std::unique_ptr<PropertyBin> materials_bin;
    if (auto mats = map_wad->read("data/maps/mapgeometry/map11/base_srx.materials.bin")) {
      materials_bin = std::make_unique<PropertyBin>(*mats);
      const PropertyBin& bin = *materials_bin;
      g_vfx.add_systems(bin, {map_wad.get()});
      g_map_fx.load(bin);
      g_level_props.load(bin);
      for (const MapObject& o : map_objects(bin))
        if (o.type == 3 || o.type == 4 || o.type == 5)
          g_structure_heights.push_back({o.x, o.z, o.y, std::sqrt(o.matrix[0] * o.matrix[0] + o.matrix[1] * o.matrix[1] + o.matrix[2] * o.matrix[2])});
      map_spawn_point(bin, 0, g_spawn);
      // the effects of a match under way: as many seconds as the offline clock starts at (at most 10)
      g_map_fx.start(offline ? static_cast<float>(std::min(offline_start, 10.0)) : 0.f);
      if (dump_light) {
        // --dump-light also lists the map's effects (vfx.txt): what runs where, with how many emitters of each kind
        FILE* f = std::fopen("vfx.txt", "w");
        if (f) {
          std::fprintf(f, "%zu systems, %zu placements\n", g_vfx.system_count(), g_map_fx.slots.size());
          for (const auto& s : g_map_fx.slots) {
            int kinds[8] = {};
            for (const VfxEmitterDef& d : s.sys->emitters) ++kinds[static_cast<int>(d.kind)];
            std::fprintf(f, "%.0f %.0f %.0f x%.2f %s  none %d billboard %d dir %d dirground %d fixed %d ground %d mesh %d ray %d\n", s.frame.x,
                         s.frame.y, s.frame.z, s.scale, s.sys->name.c_str(), kinds[0], kinds[1], kinds[2], kinds[3], kinds[4], kinds[5], kinds[6],
                         kinds[7]);
          }
          std::fclose(f);
        }
      }
    }
    stage_done("level effects (particle systems, placements)", kEffectsShare);

    // ---- 3. the level's objects: the characters the map itself puts into a match (turrets, inhibitors, nexuses, the
    // minions of both teams, the Practice Tool's dummy), so that none is read from the disk in the middle of the match
    static Wad garen_wad(data / "Champions" / "Garen.wad.client");
    if (!g_garen.load(g_gpu, garen_wad, "Garen")) throw std::runtime_error("Garen could not be read");
    if (!g_chars.init(g_gpu)) throw std::runtime_error("character shader");
    if (materials_bin && map_bin) {
      MapGame game;
      std::set<std::pair<std::string, int>> wanted;
      if (read_map_game(*materials_bin, *map_bin, std::string(), g_map.nav(), game)) {
        g_map_game = game;
        for (const StructureSpawn& st : game.structures)
          if (st.kind == "turret" && st.position == 3) g_outer_turrets.push_back({st.x, st.z});
        for (const StructureSpawn& st : game.structures) wanted.emplace(st.character, st.skin);
      }
      // the lane minions the level script names (Scripts.wad sr_levelscript's MinionName): read with the map, as the
      // game preloads them (OnLevelInit's PreloadCharacter)
      for (const char* team : {"Order", "Chaos"})
        for (const char* kind : {"Melee", "Ranged", "Siege", "Super"}) wanted.emplace(std::string("SRU_") + team + "Minion" + kind, 0);
      wanted.emplace("PracticeTool_TargetDummy", 0);
      if (!g_loading_on) wanted.clear();
      size_t done = 0;
      for (const auto& [character, skin] : wanted) {
        if (!character.empty()) {
          try {
            model_of(character, skin);
            record_of(character);
          } catch (const std::exception&) {
          }
        }
        load_step(kEffectsShare + (kObjectsShare - kEffectsShare) * static_cast<float>(++done) / static_cast<float>(wanted.size()));
      }
    }
    stage_done("level objects (turrets, inhibitors, nexuses, minions)", kObjectsShare);

    // ---- 4. the items and the interface: the client's own layouts and atlases (UI.wad.client)
    if (hud && ui_wad) {
      g_hud_on = g_hud.load(g_gpu, *ui_wad);
      g_hud.add_wad(map_wad.get());
      // the items and their pictures (Global.wad), what the mode sells (map11.bin), the texts (en_US)
      try {
        if (g_global_wad) {
          g_hud.add_wad(g_global_wad.get());
          if (read_items(*g_global_wad, g_items) && map_bin) read_mode_items(*map_bin, "CLASSIC", g_items);
        }
        g_hud.localize(g_strings);
      } catch (const std::exception& e) {
        std::fprintf(stderr, "items: %s\n", e.what());
      }
    }
    if (g_hud_on && map_bin)
      for (const BinEntry& e : map_bin->entries()) {
        const BinValue* skin_name = e.field("name");
        const BinValue* cfg = e.field("mMinimapBackgroundConfig");
        if (e.cls != fnv1a("MapSkin") || !skin_name || skin_name->str != "Default" || !cfg) continue;
        if (const BinValue* t = cfg->field("mDefaultTextureName")) g_minimap_texture = t->str;
        if (const BinValue* list = cfg->field("mCustomMinimapBackgrounds"))
          for (const auto& [key, bg] : list->pairs) {
            const BinValue* t = bg.field("mTextureName");
            const BinValue* s = bg.field("mSize");
            if (t && s && t->str == g_minimap_texture) g_minimap_size[0] = static_cast<float>(s->num[0]), g_minimap_size[1] = static_cast<float>(s->num[1]);
          }
      }
    stage_done("items and interface (items, texts, HUD scenes and atlases, minimap)", kInterfaceShare);

    // ---- 5. the champions of the match: model, animations, spells, their effects and icons
    if (g_loading_on) {
      try {
        if (const CharacterModel* model = model_of(champion, 0)) icon_of(champion, model->icon_circle);
        if (const CharacterRecordData* r = record_of(champion)) {
          for (size_t i = 0; i < 4; ++i) icon_of(champion, r->spell_icons[i]);
          icon_of(champion, r->passive_icon);
        }
        spells_of(champion);
      } catch (const std::exception&) {
      }
    }
    stage_done("champions (models, animations, spells, effects, icons)", kChampionShare);

    // ---- 6. the global effects and the frame's last pass
    static std::unique_ptr<Wad> global_wad;
    if (std::filesystem::exists(data / "Global.wad.client")) {
      global_wad = std::make_unique<Wad>(data / "Global.wad.client");
      g_vfx.add_global(*global_wad);
    }
    if (fxaa) {
      // League's own anti-aliasing: Shaders/hlsl/fxaa_ps from the shader cache, run as it is. Its options are set by
      // the game at run time and are in no file: NVIDIA FXAA 3.11's defaults (subpix 0.75, edge 0.166, edge min 0.0833).
      static Wad shaders(data / "ShaderCache.dx11.wad.client");
      const float options[4] = {0.75f, 0.166f, 0.0833f, 0};
      // (patch 14.1 names the bundles ".ps.dx11_0", later patches ".ps-dx11_0")
      auto blob = shaders.read("assets/shaders/hlsl/fxaa_ps.ps.dx11_0");
      if (!blob) blob = shaders.read("assets/shaders/hlsl/fxaa_ps.ps-dx11_0");
      if (blob) g_gpu.set_fxaa(*blob, options);
    }
    stage_done("global effects", 1.f);
    if (!load_log.empty())
      if (FILE* f = std::fopen(load_log.c_str(), "w")) {
        double total = 0;
        for (const auto& [stage, secs] : stage_times) total += secs;
        for (const auto& [stage, secs] : stage_times) std::fprintf(f, "%6.2f s  %5.1f%%  %s\n", secs, total > 0 ? secs / total * 100 : 0, stage.c_str());
        std::fprintf(f, "%6.2f s  total\n", total);
        std::fclose(f);
      }
    {
      // the map's light on characters: Summoner's Rift has no light grid, so the ambient cube is the map's sun
      // colours. LIGHTGRID_SCALE would come from lightGridCharacterIntensity / lightGridCharacterFullBrightIntensity,
      // which no file sets (defaults unknown): 1 and 1.
      float cube[6][3];
      const bool sun = g_map.ambient_cube(cube);
      g_chars.set_light(cube, 1.f, 1.f);
      if (dump_light) {
        FILE* f = std::fopen("light.txt", "w");
        if (!f) return 1;
        static const char* kAxes[6] = {"+X", "-X", "+Y", "-Y", "+Z", "-Z"};
        std::fprintf(f, "%s, self illumination %.2f\n", sun ? "ambient cube from the map's sun" : "no sun properties (white)",
                     g_garen.self_illumination);
        for (int i = 0; i < 6; ++i) std::fprintf(f, "%s %.3f %.3f %.3f\n", kAxes[i], cube[i][0], cube[i][1], cube[i][2]);
        std::fclose(f);
        return 0;
      }
    }
    if (!match_pose.empty()) {
      // --match-pose <file of numbers>: the --champion's clip that gives a captured bone palette (pose_match.txt)
      const CharacterModel* who = model_of(champion, dump_skin);
      if (!who) return 1;
      std::vector<float> palette;
      if (FILE* f = std::fopen(match_pose.c_str(), "r")) {
        float v;
        while (std::fscanf(f, "%f", &v) == 1) palette.push_back(v);
        std::fclose(f);
      }
      FILE* f = std::fopen("pose_match.txt", "w");
      if (!f) return 1;
      std::fputs(who->match_pose(palette).c_str(), f);
      std::fclose(f);
      return 0;
    }
    if (!dump_clip.empty()) {
      std::vector<float4x4> world;
      AnimParams params;
      params.move_speed = 340;
      // the --champion's pose (Garen by default)
      const CharacterModel* who = model_of(champion, dump_skin);
      if (!who) return 1;
      who->pose(dump_clip, dump_time, params, world);
      FILE* f = std::fopen("pose.txt", "w");
      if (!f) return 1;
      for (size_t i = 0; i < world.size(); ++i) {
        std::fprintf(f, "%s %.4f %.4f %.4f\n", who->skeleton.joints[i].name.c_str(), world[i].m[3][0], world[i].m[3][1], world[i].m[3][2]);
      }
      std::fclose(f);
      return 0;
    }
  } catch (const QuitWhileLoading&) {
    return 0;  // the window was closed while the match was loading
  } catch (const std::exception& e) {
    // scripted checks (--shot) write the error next to the shot instead of opening a dialog on the player's screen
    if (!shot.empty()) {
      if (FILE* f = std::fopen((shot + ".error.txt").c_str(), "w")) std::fputs(e.what(), f), std::fclose(f);
    } else {
      MessageBoxA(hwnd, e.what(), "BattleArena", MB_ICONERROR);
    }
    return 1;
  }
  if (!replay_path.empty()) {
    Replay::World w;
    w.game = &g_map_game;
    if (g_map.nav()) w.center_x = (g_map.nav()->min_x + g_map.nav()->max_x) * 0.5f, w.center_z = (g_map.nav()->min_z + g_map.nav()->max_z) * 0.5f;
    w.record = [](const std::string& character) { return record_of(character); };
    if (!g_replay.open(replay_path, w)) {
      if (!shot.empty()) {
        if (FILE* f = std::fopen((shot + ".error.txt").c_str(), "w")) std::fputs("the replay could not be opened", f), std::fclose(f);
      } else {
        MessageBoxA(hwnd, "the replay could not be opened", "BattleArena", MB_ICONERROR);
      }
      return 1;
    }
    g_replay.feed(g_conn, offline_start);
    // the spectator looks through the first champion's eyes (the interface needs one)
    for (const auto& [id, u] : g_conn.units)
      if (const CharacterRecordData* r = record_of(u.skin); r && !r->spells[0].empty()) {
        g_conn.my_unit = id;
        break;
      }
    g_follow = false;
  } else if (offline) {
    ClientUnit u;
    u.id = 1;
    u.skin = champion;
    u.x = spawn_x >= 0 ? spawn_x : g_spawn.x;
    u.z = spawn_z >= 0 ? spawn_z : g_spawn.z;
    u.facing = spawn_x >= 0 ? 0.f : g_spawn.facing;
    g_conn.units[1] = u;
    g_conn.my_unit = 1;
    // what the server would spawn: the structures on their footprints
    if (g_map.nav()) {
      uint32_t id = 100;
      for (const MapStructure& s : map_structures(*g_map.nav())) {
        ClientUnit su;
        su.id = id++;
        su.team = s.team;
        su.skin = s.character;
        su.skin_id = static_cast<uint8_t>(s.skin);
        su.x = s.x, su.z = s.z, su.facing = s.facing;
        g_conn.units[su.id] = su;
      }
    }
  } else if (g_loading_on) {
    // loaded: the client tells the server, and the loading screen stays until the server has put the player into the
    // match (League's "waiting for all players", then the spawn packets); a server that never answers is not waited
    // for longer than a few seconds
    net_pump.stop();
    g_conn.ready();
    try {
      for (const double asked = seconds_now(); !g_conn.my_unit && seconds_now() - asked < 8.0;) {
        load_step(1.f);
        Sleep(2);
      }
    } catch (const QuitWhileLoading&) {
      return 0;
    }
  } else {
    g_conn.connect(host.c_str(), port, name, champion);
  }
  g_loading_on = false;
  if (cam_x >= 0) {
    g_cam.x = cam_x;
    g_cam.z = cam_z;
    g_follow = false;
  }

  MSG msg{};
  double last = offline ? offline_start : seconds_now();
  double fps_t = last;
  int frames = 0;
  int frames_total = 0;
  const double time_origin = offline ? offline_start : seconds_now();
  for (;;) {
    while (PeekMessageW(&msg, nullptr, 0, 0, PM_REMOVE)) {
      if (msg.message == WM_QUIT) return 0;
      TranslateMessage(&msg);
      DispatchMessageW(&msg);
    }
    static long long vframe = 0;
    static const double wall0 = seconds_now();
    const bool realtime_replay = g_replay.is_open() && shot.empty() && fps_file.empty();
    const double now = realtime_replay ? offline_start + (seconds_now() - wall0)
                       : offline       ? offline_start + static_cast<double>(vframe++) / 30.0
                                       : seconds_now();
    if (g_replay.is_open()) g_replay.feed(g_conn, now);
    const float dt = static_cast<float>(now - last);
    last = now;
    const double tick = offline ? now / kTickSeconds : static_cast<double>(g_conn.server_tick) + (now - g_conn.server_tick_at) / kTickSeconds;
    g_conn.update(tick);
    static double joined_at = -1;
    if (g_conn.my_unit && joined_at < 0) joined_at = now;
    while (!moves.empty() && joined_at >= 0 && now - joined_at >= moves.front().t) {
      if (moves.front().kind != 'm') {
        const auto me = g_conn.units.find(g_conn.my_unit);
        if (moves.front().kind == 'd' && me != g_conn.units.end())
          g_conn.spawn_dummy(me->second.x + moves.front().x, me->second.z + moves.front().z);
        else if (moves.front().kind == 's' && nearest_enemy(true))
          g_conn.attack(nearest_enemy(true));
        else if (moves.front().kind == 'a' && nearest_enemy())
          g_conn.attack(nearest_enemy());
        else if (moves.front().kind == 'l')
          g_conn.level_spell(static_cast<uint8_t>(moves.front().x));
        else if (moves.front().kind == 'b')
          g_conn.buy_item(static_cast<uint32_t>(moves.front().x));
        else if (moves.front().kind == 'x')
          g_conn.sell_item(static_cast<uint8_t>(moves.front().x));
        else if (moves.front().kind == 'c' && me != g_conn.units.end()) {
          // at the nearest enemy, or straight ahead without one
          const uint32_t enemy = nearest_enemy();
          auto e = g_conn.units.find(enemy);
          const float cx = e != g_conn.units.end() ? e->second.x : me->second.x + std::sin(me->second.facing) * 400.f;
          const float cz = e != g_conn.units.end() ? e->second.z : me->second.z + std::cos(me->second.facing) * 400.f;
          g_conn.cast(static_cast<uint8_t>(moves.front().x), cx, cz, enemy);
        }
      } else if (offline) {
        // what the server would send: a path from where the unit is, starting now
        ClientUnit& u = g_conn.units[1];
        u.path = {net::Point{u.x, u.z}};
        static CharacterRecordData rec = [&] {
          CharacterRecordData r;
          r.move_speed = 340;
          read_character_record(Wad(g_data / "Champions" / (g_conn.units[1].skin + ".wad.client")), g_conn.units[1].skin, r);
          return r;
        }();
        if (g_map.nav())
          for (const auto& [x, z] : g_map.nav()->find_path(u.x, u.z, moves.front().x, moves.front().z, rec.pathfinding_radius))
            u.path.push_back({x, z});
        else
          u.path.push_back({moves.front().x, moves.front().z});
        u.speed = rec.move_speed;  // Garen's CharacterRecord: 340
        u.path_tick = static_cast<int64_t>(now / kTickSeconds);
      } else {
        g_conn.move(moves.front().x, moves.front().z);
      }
      moves.erase(moves.begin());
    }
    if (auto_x >= 0 && g_conn.my_unit) {
      g_conn.move(auto_x, auto_z);
      auto_x = -1;
    }

    // camera: follows the player's champion when locked, arrow keys move it otherwise
    auto me = g_conn.units.find(g_conn.my_unit);
    if (g_follow && me != g_conn.units.end()) {
      g_cam.x = me->second.x;
      g_cam.z = me->second.z;
    }
    const float pan = 2500.f * dt;
    if (GetAsyncKeyState(VK_LEFT) & 0x8000) g_cam.x -= pan, g_follow = false;
    if (GetAsyncKeyState(VK_RIGHT) & 0x8000) g_cam.x += pan, g_follow = false;
    if (GetAsyncKeyState(VK_UP) & 0x8000) g_cam.z += pan, g_follow = false;
    if (GetAsyncKeyState(VK_DOWN) & 0x8000) g_cam.z -= pan, g_follow = false;
    // zoom eases toward its target over mZoomEaseTime [de măsurat: the easing curve; exponential here]
    g_cam.distance += (g_cam.target - g_cam.distance) * std::min(1.f, dt / 0.2f * 3.f);
    g_cam.update(static_cast<float>(g_gpu.width()) / static_cast<float>(g_gpu.height()), g_map.ground_height(g_cam.x, g_cam.z));

    g_gpu.begin(0.f, 0.f, 0.f);
    const float4x4 vp = g_cam.view * g_cam.proj;
    // TIME in float: seconds since the client started, not the clock's own count (a PC up for days would leave floats
    // a few hundredths of a second apart and the brush's sway would step) [de măsurat: the game's own TIME origin]
    g_map.draw(g_gpu, vp, g_cam.eye, static_cast<float>(now - time_origin));
    // relative team colours: a Chaos player sees the bases' effects with the team textures swapped
    if (auto me = g_conn.units.find(g_conn.my_unit); me != g_conn.units.end() && (me->second.team == 1) != g_vfx_swap_team_colors) {
      g_vfx_swap_team_colors = me->second.team == 1;
      for (auto& s : g_map_fx.slots)
        if (s.inst && !s.sys->swapped.empty()) s.inst = std::make_unique<VfxInstance>(*s.sys, s.frame, s.scale, s.tint, g_vfx.rng());
    }
    // effects lying on the ground, right over it, under the units
    g_map_fx.update(dt);
    const std::vector<VfxInstance*> fx = g_map_fx.visible(g_cam.view, static_cast<float>(g_gpu.width()) / static_cast<float>(g_gpu.height()));
    std::vector<VfxInstance*> combat;
    for (CombatFx& c : g_combat_fx) combat.push_back(c.inst.get());
    std::vector<VfxInstance*> ground_fx = fx;
    ground_fx.insert(ground_fx.end(), combat.begin(), combat.end());
    g_vfx.draw(g_gpu, vp, g_cam.view, g_cam.eye, ground_fx, true);
    g_level_props.draw(vp, g_cam.view, static_cast<float>(g_gpu.width()) / static_cast<float>(g_gpu.height()), now - time_origin);
    // champions: every unit the server reports, walking its path (Run) or standing (Idle1), facing where it goes;
    // attacking (the attack slot's mAnimationName) or dead (Death, held on its last frame); a graph that has them
    // also plays Spawn when the unit enters the match and Hit when its health drops (the target dummy's graph has
    // both, with their sounds) [de măsurat: what triggers them in League]
    for (auto& [id, u] : g_conn.units) {
      CharacterInstance ci;
      ci.model = model_of(u.skin, u.skin_id);
      if (!ci.model) continue;
      ci.position = {u.x, g_map.ground_height(u.x, u.z), u.z};
      if (!u.moving) structure_height(u.x, u.z, ci.position.y, ci.scale);
      {
        // units outside the view are neither animated nor drawn (a generous margin: turrets are tall)
        const float3 v = transform_point(ci.position, g_cam.view);
        const float margin = 900.f, half_h = std::tan(kFov * 0.5f) * v.z;
        const float half_w = half_h * static_cast<float>(g_gpu.width()) / static_cast<float>(g_gpu.height());
        if (v.z < -margin || std::fabs(v.x) > half_w + margin || std::fabs(v.y) > half_h + margin) {
          g_poses.erase(id);
          drop_idle_fx(id, true);
          continue;
        }
      }
      const bool moving = u.moving && !u.dashing;  // a dash is not a walk: the spell's own clip plays through it
      ci.yaw = u.facing;
      // test only (--structure-yaw mul,add in degrees): turrets' yaw as mul * facing + add, to compare against footage
      if (g_structure_yaw_test && u.skin.rfind("Turret", 0) == 0) ci.yaw = g_structure_yaw[0] * u.facing + g_structure_yaw[1] * 3.14159265f / 180.f;
      static std::map<uint32_t, AnimState> anim_states, over_states;
      static std::map<uint32_t, int> attack_serials, hit_serials, respawn_serials, cast_serials, forced_serials;
      auto has = [&](const char* clip) { return ci.model->clip(fnv1a(clip)) != nullptr; };
      // what the unit stands in: Run or Idle1. A graph with damage states (the turrets': State2_seq and State3_seq
      // break the turret and show its Stage1 / Stage2 submeshes) goes through them as its health falls [de măsurat:
      // at which health; two thirds and one third here]
      // a clip the server swapped for another (Riot's animation overrides), when the graph has it
      auto swapped = [&](const std::string& clip) {
        for (const auto& [to, from] : u.anim_overrides)
          if (fnv1a(from) == fnv1a(clip) && has(to.c_str())) return to;
        return clip;
      };
      std::string standing = swapped(moving ? "Run" : "Idle1");
      if (!g_replay.is_open() && u.max_hp > 0 && has("State2_seq")) {
        const float left = u.hp / u.max_hp;
        if (left <= 1.f / 3.f && has("State3_seq")) standing = "State3_seq";
        else if (left <= 2.f / 3.f) standing = "State2_seq";
      }
      if (!g_turret_clip_test.empty() && u.skin.rfind("Turret", 0) == 0) standing = g_turret_clip_test;  // test only (--turret-clip)
      // An outer turret's plating (PreSeason_Turret_Shield, a unit of its own on the turret's spot): five plates, one
      // for each fifth of the turret's health. A plate that breaks plays its PartN_Destruction clip and its unbroken
      // submesh is gone; a hit on the turret plays the next plate's PartN_Hit. [observat: a 13.3 replay with one plate
      // gone draws the plating without the submesh Unbroken_Part1 and nothing in its place; the clips' names are the
      // graph's] [dedus: plates break in order 1..5 (the first is measured); a plate = max health / 5]
      std::vector<uint32_t> plates_hidden;
      if (u.skin == "PreSeason_Turret_Shield") {
        static std::map<uint32_t, int> broken_seen;
        static std::map<uint32_t, double> broke_at, hit_at;
        static std::map<uint32_t, float> health_seen;
        const ClientUnit* turret = nullptr;
        for (const auto& [other_id, o] : g_conn.units)
          if (other_id != id && o.max_hp > 0 && std::fabs(o.x - u.x) < 25.f && std::fabs(o.z - u.z) < 25.f && o.skin.rfind("Turret", 0) == 0) turret = &o;
        int broken = 0;
        if (turret) broken = std::clamp(static_cast<int>(std::floor((turret->max_hp - turret->hp) / (turret->max_hp / 5.f))), 0, 5);
        auto seen = broken_seen.find(id);
        if (seen == broken_seen.end()) {
          broken_seen[id] = broken;  // first sight: the plates already gone are simply not there
        } else if (broken > seen->second) {
          seen->second = broken, broke_at[id] = now;
        }
        if (turret) {
          auto hp = health_seen.find(id);
          if (hp != health_seen.end() && turret->hp < hp->second - 0.5f) hit_at[id] = now;
          health_seen[id] = turret->hp;
        }
        for (const CharacterModel::Submesh& sm : ci.model->submeshes)
          for (int part = 1; part <= broken; ++part)
            if (sm.name.find("Unbroken_Part" + std::to_string(part)) != std::string::npos) plates_hidden.push_back(sm.name_hash);
        ci.hide = &plates_hidden;
        // both clips are on additive tracks (mBlendMode 1): they play over the idle, not instead of it
        const std::string destruction = "Part" + std::to_string(broken) + "_Destruction", hit = "Part" + std::to_string(std::min(broken + 1, 5)) + "_Hit";
        if (broke_at.count(id) && has(destruction.c_str()) && now - broke_at[id] < ci.model->duration(fnv1a(destruction), ci.params))
          ci.add_clip = destruction, ci.add_time = static_cast<float>(now - broke_at[id]);
        else if (hit_at.count(id) && broken < 5 && has(hit.c_str()) && now - hit_at[id] < ci.model->duration(fnv1a(hit), ci.params))
          ci.add_clip = hit, ci.add_time = static_cast<float>(now - hit_at[id]);
      }
      ci.clip = standing;
      AnimState& stand = anim_states[id];
      ci.state = &stand;
      // a unit back from the dead starts its animation afresh (no blend out of its death pose)
      if (respawn_serials[id] != u.respawns) respawn_serials[id] = u.respawns, stand = AnimState{};
      if (!stand.request) {
        // a unit seen for the first time has been playing its first clip since the match began (clock 0): the
        // structures were standing before anyone loaded in
        stand.request = fnv1a(ci.clip);
        stand.start = 0;
      }
      ci.params.move_speed = u.speed;
      // asks the graph for `clip` from `start` (a one-shot clip asked for again starts over)
      auto play = [&](const std::string& clip, double start) {
        ci.state->prev_request = ci.state->request, ci.state->request = fnv1a(clip), ci.state->start = start;
      };
      // a clip over the standing one. On the standing clip's own track it takes its place (a champion's attack); on
      // another track, with a mask, it plays in a state of its own over it (a turret's Attack1 over its damage state)
      auto over = [&](const std::string& clip) {
        float t0 = 0, t1 = 0;
        const Clip* top = ci.model->resolve(fnv1a(clip), 0, ci.params, t0);
        const Clip* base = ci.model->resolve(fnv1a(standing), 0, ci.params, t1);
        if (top && base && top->track != base->track && ci.model->masks.count(top->mask)) {
          ci.under_state = &stand, ci.under_clip = standing, ci.under_params = ci.params;
          ci.state = &over_states[id];
        }
        ci.clip = clip;
      };
      // the attack clip is sped up so that its cast moment (the slot's spellCastTime into the clip) comes at the end
      // of the server's windup [de măsurat: League's exact playback rate]
      const ClientUnit::Attack& a = u.attack;
      const double since = now - a.start;
      if (u.dead) {
        // Death, held on its last frame; structures have Destroyed_seq instead (the collapse, then the rubble)
        ci.clip = swapped(has("Death") ? "Death" : has("Destroyed_seq") ? "Destroyed_seq" : "Death");
        ci.params.hold = true;
        if (ci.state->request != fnv1a(ci.clip)) play(ci.clip, u.death_time);
      } else if (a.start >= 0 && since >= 0 && !moving) {
        const float rate = a.windup > 0 && a.cast > 0 ? a.cast / a.windup : 1.f;
        const float length = ci.model->duration(fnv1a(a.animation), ci.params) / rate;
        if (since < length) {
          over(a.animation);
          ci.params.rate = rate;
          // every attack starts its clip over, at the tick the server began it
          if (attack_serials[id] != a.serial || ci.state->request != fnv1a(ci.clip)) {
            attack_serials[id] = a.serial;
            play(ci.clip, a.start);
          }
        }
      }
      // a spell's cast: its mAnimationName from the tick the cast began, when it is newer than the attack's clip. A cast
      // without a cast time does not stop a walking champion, and then its clip does not play either [de măsurat]
      if (!u.dead && u.cast.start >= 0 && now >= u.cast.start && u.cast.start >= a.start && !u.cast.animation.empty() &&
          (!moving || u.cast.cast_time > 0) && ci.model->clip(fnv1a(u.cast.animation))) {
        const float length = ci.model->duration(fnv1a(u.cast.animation), ci.params);
        if (now - u.cast.start < length) {
          ci.params.rate = 1.f;
          over(u.cast.animation);
          if (cast_serials[id] != u.cast.serial || ci.state->request != fnv1a(ci.clip)) cast_serials[id] = u.cast.serial, play(ci.clip, u.cast.start);
        }
      }
      // a clip a spell's script asked for (Garen's spin), over everything, walking or not
      if (!u.dead && !u.forced.clip.empty() && now >= u.forced.start && (u.forced.end < 0 || now < u.forced.end) && ci.model->clip(fnv1a(u.forced.clip)) &&
          (!u.forced.once || now - u.forced.start < ci.model->duration(fnv1a(u.forced.clip), ci.params))) {
        ci.params.rate = 1.f;
        ci.under_state = nullptr;
        ci.state = &stand;
        ci.clip = u.forced.clip;
        if (forced_serials[id] != u.forced.serial || ci.state->request != fnv1a(ci.clip)) forced_serials[id] = u.forced.serial, play(ci.clip, u.forced.start);
      }
      if (!u.dead && ci.clip == standing && !moving) {
        const uint32_t spawn = fnv1a("Spawn"), hit = fnv1a("Hit"), respawn = fnv1a("Respawn");
        if (u.spawn_time >= 0 && ci.model->clip(spawn) && now - u.spawn_time < ci.model->duration(spawn, ci.params)) {
          over("Spawn");
          if (ci.state->request != spawn) play(ci.clip, u.spawn_time);
        } else if (u.respawn_time >= 0 && ci.model->clip(respawn) && now - u.respawn_time < ci.model->duration(respawn, ci.params)) {
          over("Respawn");  // an inhibitor standing again
          if (ci.state->request != respawn) play(ci.clip, u.respawn_time);
        } else if (u.hit_time >= 0 && ci.model->clip(hit) && now - u.hit_time < ci.model->duration(hit, ci.params)) {
          over("Hit");
          if (hit_serials[id] != u.hits || ci.state->request != hit) hit_serials[id] = u.hits, play(ci.clip, u.hit_time);
        }
      }
      ci.now = now;
      g_unit_clips[id] = ci.under_state ? ci.clip + " over " + ci.under_clip : ci.clip;
      UnitPose& pose = g_poses[id];
      pose.model = ci.model;
      ci.joints_out = &pose.joints;
      g_chars.draw(g_gpu, vp, ci);
      unit_effects(id, u, ci);
      // ---- its floating health bar: the skin's unitHealthBarStyle, at the record's healthBarHeight. A turret's bar
      // (healthBarFullParallax) stands at that height in the world; any other is raised on the screen by what that
      // height spans at the unit's depth, not foreshortened by the camera's tilt [dedus: 100 puts a champion's bar at
      // its head, 47 a minion's; as a world height both would sit at the chest; de măsurat]
      if (g_hud_on && u.max_hp > 0 && !u.dead) {
        const CharacterRecordData* r = record_of(u.skin);
        const float height = r ? r->health_bar_height : 100.f;
        const bool parallax = r && r->health_bar_parallax;
        const float3 at{ci.position.x, ci.position.y + (parallax ? height : 0.f), ci.position.z};
        const float3 v = transform_point(at, g_cam.view);
        if (v.z > 1.f) {
          const float w = static_cast<float>(g_gpu.width()), h = static_cast<float>(g_gpu.height());
          const float sx = (v.x * g_cam.proj.m[0][0] / v.z * 0.5f + 0.5f) * w;
          float sy = (0.5f - v.y * g_cam.proj.m[1][1] / v.z * 0.5f) * h;
          if (!parallax) sy -= height * g_cam.proj.m[1][1] / v.z * 0.5f * h;
          const auto me_it = g_conn.units.find(g_conn.my_unit);
          const Hud::Side side = id == g_conn.my_unit                                              ? Hud::Side::Self
                                 : me_it != g_conn.units.end() && me_it->second.team != u.team ? Hud::Side::Enemy
                                                                                               : Hud::Side::Ally;
          struct UnitHealthTrack {
            float prev_hp = -1.f;
            float decay_hp = -1.f;
          };
          static std::map<uint32_t, UnitHealthTrack> s_ht;
          UnitHealthTrack& ht = s_ht[id];
          if (ht.prev_hp < 0) ht.prev_hp = ht.decay_hp = u.hp;
          if (u.hp < ht.prev_hp) {
            const float dmg = ht.prev_hp - u.hp;
            g_hud.add_fct(sx, sy - 20.f, dmg, Hud::FctType::Physical);
          } else if (u.hp > ht.prev_hp) {
            const float heal = u.hp - ht.prev_hp;
            g_hud.add_fct(sx, sy - 20.f, heal, Hud::FctType::Heal);
          }
          ht.prev_hp = u.hp;
          if (ht.decay_hp > u.hp) {
            const float decay_speed = std::max(u.max_hp * 0.6f, 100.f);
            ht.decay_hp = std::max(u.hp, ht.decay_hp - decay_speed * dt);
          } else {
            ht.decay_hp = u.hp;
          }
          const float decay_frac = u.max_hp > 0 ? ht.decay_hp / u.max_hp : 0.f;
          const float shield_frac = u.max_hp > 0 ? u.shield / u.max_hp : 0.f;
          // the bar's ticks: the skin's hpPerTick; an outer turret's plates while it wears them
          float hp_per_tick = ci.model->hp_per_tick;
          const double game_seconds = g_conn.game_start_tick >= 0 ? static_cast<double>(g_conn.server_tick - g_conn.game_start_tick) * kTickSeconds : 0.0;
          if (u.skin.rfind("Turret", 0) == 0 && game_seconds < kPlatingEndsSeconds)
            for (const auto& [tx, tz] : g_outer_turrets)
              if (std::fabs(tx - u.x) < 60.f && std::fabs(tz - u.z) < 60.f) hp_per_tick = 1000.f;
          g_hud.health_bar(ci.model->health_bar_style, sx, sy, u.hp / u.max_hp, u.max_hp, shield_frac, decay_frac, side, hp_per_tick);
        }
      }
    }
    sweep_unit_effects();
    if (!preview_clip.empty()) {
      CharacterInstance ci;
      ci.model = &g_garen;
      ci.position = {g_cam.x, g_map.ground_height(g_cam.x, g_cam.z), g_cam.z};
      ci.yaw = preview_yaw;
      ci.clip = preview_clip;
      ci.time = static_cast<float>(frames_total) / 60.f;
      g_chars.draw(g_gpu, vp, ci);
    }
    // the map's particle effects, after everything solid
    // the attacks' effects (missiles, hits), started and moved with this frame's bones
    update_spell_fx(now);
    update_combat_fx(now, dt);
    std::vector<VfxInstance*> air_fx = fx;
    for (CombatFx& c : g_combat_fx) air_fx.push_back(c.inst.get());
    g_vfx.draw(g_gpu, vp, g_cam.view, g_cam.eye, air_fx, false);
    // the frame onto the screen through League's FXAA
    g_gpu.resolve();
    // the interface over it, sharp: the player's frame, from what the server says of the player's champion
    if (g_hud_on) {
      if (auto m = g_conn.units.find(g_conn.my_unit); m != g_conn.units.end()) {
        const ClientUnit& u = m->second;
        Hud::Player p;
        p.hp = u.hp, p.max_hp = u.max_hp;
        p.level = u.level, p.xp = u.xp;
        p.par = u.par, p.max_par = u.max_par;
        if (const CharacterModel* model = model_of(u.skin, u.skin_id)) p.portrait = icon_of(u.skin, model->icon_circle);
        if (const CharacterRecordData* r = record_of(u.skin)) {
          for (size_t i = 0; i < 4; ++i) p.spells[i] = icon_of(u.skin, r->spell_icons[i]);
          p.passive = icon_of(u.skin, r->passive_icon);
        }
        for (size_t i = 0; i < 4; ++i) {
          p.spell_levels[i] = u.spells[i].level;
          p.cooldown_left[i] = static_cast<float>(std::max(0.0, u.spells[i].ready_at - now));
          p.cooldown_total[i] = u.spells[i].cooldown_total;
          p.costs[i] = u.spells[i].cost;
        }
        p.skill_points = u.skill_points;
        // where a point may go (documented): the last spell at levels 6, 11 and 16; the others up to five ranks, never
        // more than half the champion's level rounded up
        for (size_t i = 0; i < 4; ++i) {
          const int cap = i == 3 ? (u.level >= 16 ? 3 : u.level >= 11 ? 2 : u.level >= 6 ? 1 : 0) : std::min(5, (u.level + 1) / 2);
          p.can_level[i] = u.skill_points > 0 && u.spells[i].level < cap;
        }
        p.gold = u.gold;
        p.ad = u.ad, p.armor = u.armor, p.spell_block = u.spell_block, p.attack_speed = u.attack_speed, p.move_speed = u.move_speed;
        p.ap = u.ap, p.crit = u.crit, p.ability_haste = u.ability_haste;
        for (size_t k = 0; k < 7; ++k) {
          const ItemDef* d = u.items[k] ? g_items.find(u.items[k]) : nullptr;
          p.item_icons[k] = d && !d->icon.empty() ? g_hud.image(g_gpu, d->icon) : nullptr;
          p.item_stacks[k] = u.item_stacks[k];
        }
        p.selected_slot = g_shop_open ? g_inv_selected : -1;
        // the shop: every item the mode sells in the store, cheapest first within its group [dedus: the order]
        Hud::ShopView sv;
        sv.open = g_shop_open;
        if (g_shop_open) {
          sv.gold = u.gold;
          for (int id : g_items.mode_items) {
            const ItemDef* d = g_items.find(id);
            if (!d || !d->in_store || (!d->required_champion.empty() && d->required_champion != u.skin)) continue;
            Hud::ShopItem si;
            si.id = id;
            si.icon = d->icon.empty() ? nullptr : g_hud.image(g_gpu, d->icon);
            si.cost = cost_now(id, u.items);
            si.epicness = d->epicness;
            si.affordable = static_cast<float>(si.cost) <= u.gold;
            sv.items.push_back(si);
          }
          std::stable_sort(sv.items.begin(), sv.items.end(), [](const Hud::ShopItem& a, const Hud::ShopItem& b) { return a.cost < b.cost; });
          for (const std::string& key : g_hud.shop_group_keys()) sv.group_titles.push_back(g_strings.get(key));
          if (const ItemDef* d = g_shop_selected ? g_items.find(g_shop_selected) : nullptr) {
            sv.selected = g_shop_selected;
            sv.title = g_strings.get(d->name_key);
            sv.cost_text = std::to_string(cost_now(d->id, u.items));
            sv.selected_icon = d->icon.empty() ? nullptr : g_hud.image(g_gpu, d->icon);
          }
        }
        g_hud.shop(sv);
        p.kills = u.kills, p.deaths = u.deaths, p.assists = u.assists, p.minions_killed = u.minions_killed;
        p.fps = g_fps;
        if (g_conn.game_start_tick >= 0) p.game_seconds = (tick - static_cast<double>(g_conn.game_start_tick)) * kTickSeconds;
        // the minimap: every unit by what its record's tags say it is
        std::vector<Hud::MapUnit> on_map;
        for (const auto& [id, o] : g_conn.units) {
          if (o.dead) continue;
          const CharacterRecordData* r = record_of(o.skin);
          if (!r) continue;
          Hud::MapUnit m;
          m.x = o.x, m.z = o.z;
          m.side = id == g_conn.my_unit ? Hud::Side::Self : o.team == u.team ? Hud::Side::Ally : Hud::Side::Enemy;
          if (r->tags.find("Champion") != std::string::npos) {
            m.icon = Hud::kChampion;
            if (const CharacterModel* model = model_of(o.skin, o.skin_id)) m.portrait = icon_of(o.skin, model->icon_circle);
            p.team_kills[o.team == u.team ? 0 : 1] += o.kills;
          } else if (r->tags.find("Structure_Turret_Shrine") != std::string::npos) {
            continue;  // the fountain's turret has no icon
          } else if (r->tags.find("Structure_Turret") != std::string::npos) {
            m.icon = Hud::kTower;
          } else if (r->tags.find("Structure_Inhibitor") != std::string::npos) {
            m.icon = Hud::kInhibitor;
          } else if (r->tags.find("Structure_Nexus") != std::string::npos) {
            m.icon = Hud::kNexus;
          } else if (r->tags.find("Minion") != std::string::npos) {
            m.icon = Hud::kMinion;
          } else {
            continue;
          }
          on_map.push_back(m);
        }
        g_hud.player(p);
        float corners[8];
        const int cw = g_gpu.width(), ch = g_gpu.height();
        const float ground = g_map.ground_height(g_cam.x, g_cam.z);
        const int sx[4] = {0, cw, cw, 0}, sy[4] = {0, 0, ch, ch};
        bool seen = true;
        for (int i = 0; i < 4; ++i) seen = g_cam.pick(sx[i], sy[i], cw, ch, ground, corners[i * 2], corners[i * 2 + 1]) && seen;
        g_hud.minimap(g_minimap_texture.empty() ? nullptr : g_hud.image(g_gpu, g_minimap_texture), 0, 0, g_minimap_size[0], g_minimap_size[1], on_map,
                      seen ? corners : nullptr);
      }
      // ---- TargetFrame: the unit currently targeted
      Hud::TargetInfo ti;
      if (g_selected_target) {
        auto tit = g_conn.units.find(g_selected_target);
        if (tit != g_conn.units.end() && !tit->second.dead && tit->second.max_hp > 0) {
          const ClientUnit& tu = tit->second;
          ti.valid = true;
          ti.name = tu.skin;
          ti.level = tu.level;
          ti.hp = tu.hp;
          ti.max_hp = tu.max_hp;
          ti.par = tu.par;
          ti.max_par = tu.max_par;
          ti.shield = tu.shield;
          ti.ad = tu.ad;
          ti.ap = tu.ap;
          ti.armor = tu.armor;
          ti.spell_block = tu.spell_block;
          ti.attack_speed = tu.attack_speed;
          ti.move_speed = tu.move_speed;
          ti.crit = tu.crit;
          ti.ability_haste = tu.ability_haste;
          ti.kills = tu.kills;
          ti.deaths = tu.deaths;
          ti.assists = tu.assists;
          ti.cs = tu.minions_killed;
          const auto me_it = g_conn.units.find(g_conn.my_unit);
          ti.side = g_selected_target == g_conn.my_unit ? Hud::Side::Self : (me_it != g_conn.units.end() && me_it->second.team != tu.team) ? Hud::Side::Enemy : Hud::Side::Ally;
          if (const CharacterModel* tm = model_of(tu.skin, tu.skin_id)) ti.portrait = icon_of(tu.skin, tm->icon_circle);
          for (int k = 0; k < 7; ++k) {
            const ItemDef* d = tu.items[k] ? g_items.find(tu.items[k]) : nullptr;
            ti.item_icons[k] = d && !d->icon.empty() ? g_hud.image(g_gpu, d->icon) : nullptr;
            ti.item_stacks[k] = tu.item_stacks[k];
          }
        } else {
          g_selected_target = 0;
        }
      }
      g_hud.target(ti);

      // ---- Scoreboard (TAB)
      Hud::ScoreboardView sb;
      sb.open = (GetKeyState(VK_TAB) < 0);
      if (sb.open) {
        for (const auto& [id, u] : g_conn.units) {
          if (u.dead) continue;
          const CharacterRecordData* r = record_of(u.skin);
          if (r && r->tags.find("Champion") != std::string::npos) {
            sb.team_kills[u.team == 0 ? 0 : 1] += u.kills;
          }
        }
        for (const auto& [id, u] : g_conn.units) {
          const CharacterRecordData* r = record_of(u.skin);
          if (!r || r->tags.find("Champion") == std::string::npos) continue;
          auto& slot_vec = (u.team == 0) ? sb.team1 : sb.team2;
          if (slot_vec.size() >= 5) continue;
          Hud::ScoreboardPlayer sp;
          sp.id = id;
          sp.name = u.skin;
          sp.level = u.level;
          sp.kills = u.kills;
          sp.deaths = u.deaths;
          sp.assists = u.assists;
          sp.cs = u.minions_killed;
          sp.dead = u.dead;
          sp.is_self = (id == g_conn.my_unit);
          if (const CharacterModel* tm = model_of(u.skin, u.skin_id)) sp.portrait = icon_of(u.skin, tm->icon_circle);
          for (int k = 0; k < 7; ++k) {
            const ItemDef* d = u.items[k] ? g_items.find(u.items[k]) : nullptr;
            sp.item_icons[k] = d && !d->icon.empty() ? g_hud.image(g_gpu, d->icon) : nullptr;
            sp.item_stacks[k] = u.item_stacks[k];
          }
          slot_vec.push_back(sp);
        }
      }
      g_hud.scoreboard(sb);

      // ---- End of Game (Victory / Defeat)
      if (g_conn.winner >= 0) {
        auto me = g_conn.units.find(g_conn.my_unit);
        Hud::EndOfGame eog;
        eog.shown = true;
        eog.victory = (me != g_conn.units.end() && g_conn.winner == me->second.team);
        g_hud.end_of_game(eog);
      }

      g_hud.update_fct(dt);
      g_hud.draw(g_gpu);
    }
    if (!record_dir.empty() && joined_at >= 0) {
      static int rec = 0;
      static double rec_start = now;
      char name[64];
      std::snprintf(name, sizeof name, "/frame_%05d.bmp", rec++);
      g_gpu.save_bmp(record_dir + name);
      if (now - rec_start >= record_seconds) {
        FILE* f = std::fopen((record_dir + "/fps.txt").c_str(), "w");
        if (f) {
          std::fprintf(f, "%.3f\n", rec / (now - rec_start));
          std::fclose(f);
        }
        return 0;
      }
    }
    static int missile_frames = -1;
    if (missile_frames < 0) {
      if (!g_combat_fx.empty()) missile_frames = 0;
    } else {
      ++missile_frames;
    }
    const bool shot_now = shot_missile >= 0   ? missile_frames >= shot_missile
                          : shot_seconds >= 0 ? joined_at >= 0 && now - joined_at >= shot_seconds
                                              : frames_total >= shot_frames;
    ++frames_total;
    static int shots_taken = 0;
    static double next_shot = -1;
    if (!shot.empty() && shot_now && now >= next_shot) {
      const std::string first = shot;
      if (shot_count > 1) shot = first.substr(0, first.rfind('.')) + "_" + std::to_string(shots_taken) + ".bmp";
      g_gpu.save_bmp(shot);
      if (FILE* f = std::fopen((shot + ".vfx.txt").c_str(), "w")) {
        std::vector<VfxInstance*> report = g_map_fx.visible(g_cam.view, static_cast<float>(g_gpu.width()) / static_cast<float>(g_gpu.height()));
        for (CombatFx& c : g_combat_fx) report.push_back(c.inst.get());
        std::fputs(Vfx::describe(report).c_str(), f);
        for (const std::string& t : g_vfx.missing_textures()) std::fprintf(f, "missing texture: %s\n", t.c_str());
        for (uint32_t k : g_unresolved_effects) std::fprintf(f, "effect key not resolved: %08x\n", k);
        std::fclose(f);
      }
      if (g_replay.is_open()) g_replay.report(shot + ".replay.txt");
      if (FILE* f = std::fopen((shot + ".units.txt").c_str(), "w")) {
        // every unit as it was drawn: who, where, its health and the clip the graph was asked for
        std::fprintf(f, "%d frames, %.1f s after joining\n", frames_total, joined_at >= 0 ? now - joined_at : -1.0);
        for (const auto& [id, u] : g_conn.units)
          std::fprintf(f, "%u team %d %s skin %d at %.0f %.0f hp %.0f/%.0f%s%s clip %s\n", id, u.team, u.skin.c_str(), u.skin_id, u.x, u.z, u.hp, u.max_hp,
                       u.dead ? " dead" : "", u.moving ? " moving" : "", g_unit_clips[id].c_str());
        // the player's champion: its gold, stats and inventory (shop checks)
        if (auto me = g_conn.units.find(g_conn.my_unit); me != g_conn.units.end()) {
          const ClientUnit& u = me->second;
          std::fprintf(f, "me: gold %.1f ad %.1f ap %.1f armor %.1f mr %.1f as %.3f ms %.1f crit %.2f haste %.0f hp %.0f mana %.0f items", u.gold, u.ad, u.ap, u.armor,
                       u.spell_block, u.attack_speed, u.move_speed, u.crit, u.ability_haste, u.max_hp, u.max_par);
          for (int k = 0; k < 7; ++k) std::fprintf(f, " %d%s", u.items[k], u.item_stacks[k] > 1 ? ("x" + std::to_string(u.item_stacks[k])).c_str() : "");
          std::fprintf(f, "\n");
        }
        std::fclose(f);
      }
      if (FILE* f = std::fopen((shot + ".map.txt").c_str(), "w")) {
        std::fputs(g_map.report().c_str(), f);
        std::fprintf(f, "models hidden by their visibility controller: %zu\n", g_map.hidden_models());
        std::fclose(f);
      }
      if (++shots_taken >= shot_count) return 0;
      shot = first;
      next_shot = now + shot_interval;
    }
    g_gpu.end();

    ++frames;
    if (!fps_file.empty()) {
      static long long counted = 0, in_bucket = 0;
      static double since = -1, bucket_start = 0;
      static std::string buckets;  // frames per second in each 5 seconds, and how many units were on the map
      if (since < 0 && g_conn.my_unit) since = bucket_start = now;  // count from when the world is there
      if (since >= 0) ++counted, ++in_bucket;
      if (since >= 0 && now - bucket_start >= 5.0) {
        char line[96];
        std::snprintf(line, sizeof line, "%.0f s: %.2f fps, %zu units\n", now - since, static_cast<double>(in_bucket) / (now - bucket_start), g_conn.units.size());
        buckets += line;
        in_bucket = 0, bucket_start = now;
      }
      if (since >= 0 && now - since >= fps_seconds) {
        if (FILE* f = std::fopen(fps_file.c_str(), "w"))
          std::fprintf(f, "%.2f\n%s", static_cast<double>(counted) / (now - since), buckets.c_str()), std::fclose(f);
        return 0;
      }
    }
    if (now - fps_t >= 1.0) {
      wchar_t title[128];
      // health until the HUD exists: the champion's, and its target's
      float my_hp = 0, my_max = 0, t_hp = 0, t_max = 0;
      if (auto m = g_conn.units.find(g_conn.my_unit); m != g_conn.units.end()) {
        my_hp = m->second.hp, my_max = m->second.max_hp;
        if (auto t = g_conn.units.find(m->second.attack.target); t != g_conn.units.end()) t_hp = t->second.hp, t_max = t->second.max_hp;
      }
      std::swprintf(title, 128, L"BattleArena - %d FPS - HP %.0f/%.0f - target %.0f/%.0f", frames, my_hp, my_max, t_hp, t_max);
      // the end of the match, until the HUD exists
      if (auto m = g_conn.units.find(g_conn.my_unit); g_conn.winner >= 0 && m != g_conn.units.end())
        std::swprintf(title, 128, L"BattleArena - %ls", g_conn.winner == m->second.team ? L"VICTORY" : L"DEFEAT");
      SetWindowTextW(hwnd, title);
      g_fps = frames;
      frames = 0;
      fps_t = now;
    }
  }
}
