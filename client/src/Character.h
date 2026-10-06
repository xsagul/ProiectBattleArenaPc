#pragma once
// A League character drawn from its own files: skins/skin<N>.bin names its .skn, .skl, texture and skinScale; its
// animation graph (animations/skin<N>.bin, mClipDataMap) names every clip's .anm and tick duration. Skinning follows
// Riot's lit_uber_vs: up to 256 bones as 4x3 matrices already in world space, four weighted influences per vertex.

#include <cstdint>
#include <cstring>
#include <string>
#include <unordered_map>
#include <vector>

#include "Gpu.h"
#include "Math.h"
#include "ba/Model.h"
#include "ba/Wad.h"

namespace ba {

/** One node of the animation graph (animations/skin<N>.bin, mClipDataMap). The game asks for a clip by name ("Run",
 *  "Idle1") and the graph decides which .anm plays: Garen's "Run" is a ConditionBoolClipData (GarenQ buff -> Run_Spell1,
 *  else a ConditionFloatClipData on move speed: Run_Base, Run_Fast from 341, Run_Haste from 385), his "Idle1" a
 *  SequencerClipData (Idle_Enter_BASE, Idle1_Base, then the looping Idle2 sequence of idle variations). */
struct Clip {
  enum class Kind { Atomic, Sequencer, ConditionBool, ConditionFloat, Parametric, Selector, Parallel, Unknown };
  /** mFlags bits, read off every champion's graph: 2 on what loops (Idle1, Run, Channel, Dance), 8 on lead-ins
   *  played once before a loop (Idle_Enter, Run_Leadin, Taunt, Dance_Base). */
  static constexpr uint32_t kLoop = 2;
  Kind kind = Kind::Unknown;
  uint32_t flags = 0;
  // Atomic
  Animation anim;
  std::string file;  // mAnimationFilePath (checks: naming the clip a captured pose matches)
  float tick = 1.f / 30.f;  // seconds per frame (the graph's mTickDuration overrides the file's fps)
  // Sequencer / Parallel / Selector: child clips (fnv1a names); ConditionBool: {true clip, false clip}
  std::vector<uint32_t> children;
  // ConditionFloat / Parametric: (mValue, clip), sorted by value
  std::vector<std::pair<float, uint32_t>> pairs;
  uint32_t updater = 0;  // class hash of the Updater (MoveSpeedParametricUpdater, ...) or of its bool driver
  // Atomic: the track it plays on (mTrackDataName) and the joints it drives there (mMaskDataName); a clip on another
  // track than the unit's standing clip plays over it (a turret's Attack1 over its damage state)
  uint32_t track = 0, mask = 0;
  // the track's mBlendMode is 1 (TrackData): the clip's values are added to the pose under it (translations added,
  // rotations and scales multiplied), not a pose of their own. The turret plating's PartN_Hit / PartN_Destruction
  // are such: their joints stay near zero, and played alone they fold the plating into one point.
  bool additive = false;
  // Atomic: mEventDataMap. Frames are the animation's own [meta: mStartFrame 0, mEndFrame -1 = to the clip's end]
  struct SubmeshEvent {  // SubmeshVisibilityEventData: submeshes shown / hidden while the clip is in these frames
    float start = 0, end = -1;
    std::vector<uint32_t> show, hide;  // fnv1a of submesh names
  };
  struct ParticleEvent {  // ParticleEventData: an effect of the skin's ResourceResolver on a bone
    uint32_t name = 0;
    float start = 0, end = -1;
    uint32_t effect = 0;            // mEffectKey
    uint32_t bone = 0;              // mParticleEventDataPairList[0].mBoneName (fnv1a of the joint's name)
    bool loop = true, kill = true, detachable = false;  // [meta defaults]
    float scale = 1;
  };
  std::vector<SubmeshEvent> submesh_events;
  std::vector<ParticleEvent> particle_events;
};

/** A unit's place in its animation graph, kept from frame to frame: what was asked for and since when, which atomic
 *  clip plays, and the clip it is blending away from. */
struct AnimState {
  uint32_t request = 0, prev_request = 0;
  double start = 0;
  const struct Clip* cur = nullptr;
  uint32_t cur_name = 0;
  float cur_t = 0;
  const struct Clip* from = nullptr;
  float from_t = 0;      // where the outgoing clip was when the switch happened
  double from_at = 0;    // when it happened
  float blend = 0;       // seconds the switch blends over
  /** The atomic clips playing this frame (the main one, then a ParallelClipData's others) and the time inside each:
   *  their events decide which submeshes show and which effects run. */
  std::vector<std::pair<const struct Clip*, float>> playing;
};

/** What the graph's updaters read from the unit. */
struct AnimParams {
  float rate = 1;     // playback speed (an attack's clip is sped up so its cast moment meets the windup's end)
  bool hold = false;  // stay on the last frame instead of starting over (Death)
  float move_speed = 0;
  bool condition = false;  // the ConditionBool drivers (HasBuffDynamicMaterialBoolDriver, ...): no buffs yet
};

class CharacterModel {
 public:
  /** Loads `character` (e.g. "Garen", "Turret") skin `skin` from the wad that holds it (its champion wad, or the map's
   *  for structures and monsters). `hide` names submeshes to keep hidden besides the skin's initialSubmeshToHide. */
  bool load(Gpu& gpu, const Wad& wad, const std::string& character, int skin = 0, const std::vector<std::string>& hide = {});
  const Clip* clip(uint32_t name) const;
  /** The atomic clip playing `t` seconds after `name` was asked for, and the time inside it. */
  /** `layers` collects the other clips a ParallelClipData plays at the same time (each with its own time). */
  using Layers = std::vector<std::pair<const Clip*, float>>;
  const Clip* resolve(uint32_t name, float t, const AnimParams& p, float& local_t, int depth = 0, uint32_t* atomic = nullptr,
                      Layers* layers = nullptr) const;
  /** Seconds a clip plays before a sequence moves on (infinite for looping clips). */
  float duration(uint32_t name, const AnimParams& p, int depth = 0) const;
  /** Every joint's model-space matrix `t` seconds into `clip` (row vectors: world = local * parent world). */
  void pose(const std::string& clip, float t, const AnimParams& p, std::vector<float4x4>& world) const;
  /** The pose of a unit playing `request` at time `now` (seconds), blending clip switches as the graph's
   *  mBlendDataTable says; `state` carries the unit's animation from one frame to the next. */
  void animate(AnimState& state, const std::string& request, double now, const AnimParams& p, std::vector<float4x4>& world) const;
  /** The same, then an additive clip (see Clip::additive) `add_time` seconds in, added to the pose (0: none). */
  void animate(AnimState& state, const std::string& request, double now, const AnimParams& p, uint32_t add_clip, float add_time,
               std::vector<float4x4>& world) const;
  /** The same with a clip under it: `under` is what the unit stands in (a turret's damage state), `state` a clip that
   *  plays on another track (its Attack1) and drives only the joints of its mask. When the upper clip is on the same
   *  track, or has no mask, it plays alone and `layered` is false. */
  void animate(AnimState& state, const std::string& request, const AnimParams& p, AnimState& under, const std::string& under_request,
               const AnimParams& under_p, double now, std::vector<float4x4>& world, bool& layered) const;
  /** For checks against a capture of the real client: which atomic clip, at which time, gives this bone palette.
   *  `palette` holds, per skin influence, the 4x3 matrix the game uploads (three rows of four: inverse bind * pose *
   *  the unit's place). The place is taken from the first influence and the others must agree with it. One line per
   *  clip, best first: error, time, file. */
  std::string match_pose(const std::vector<float>& palette) const;
  /** Joint index by the fnv1a hash of its name (events name bones that way), -1 when there is none. */
  int joint_by_name_hash(uint32_t hash) const;
  /** Seconds to blend from one clip to another: mBlendDataTable[(from << 32) | to] (TimeBlendData mTime). */
  float blend_time(uint32_t from, uint32_t to) const;
  /** TimeBlendData's mTime default [meta: 0.2]. Pairs the table does not list are taken to blend over it too. */
  static constexpr float kDefaultBlend = 0.2f;

  Skeleton skeleton;
  float skin_scale = 1.f;
  float self_illumination = 0.f;  // skinMeshProperties selfIllumination (Garen: 0.7)
  int health_bar_style = 0;       // healthBarData unitHealthBarStyle [meta default 0]: which floating bar the unit gets
  float hp_per_tick = 0;          // healthBarData hpPerTick [meta default 0: no ticks]: a unit bar's tick spacing
  std::string icon_circle;        // iconCircle: the round portrait of the interface
  std::unordered_map<uint32_t, Clip> clips;  // fnv1a(clip name) -> clip
  std::unordered_map<uint64_t, float> blends;  // mBlendDataTable: (from << 32) | to -> seconds
  std::unordered_map<uint32_t, std::vector<float>> masks;  // mMaskDataMap: name -> weight per joint
  /** The skin's idleParticlesEffects: effects that run on a bone for as long as the unit is alive. */
  struct IdleEffect {
    uint32_t effect = 0;  // effectKey
    std::string bone;     // boneName
  };
  std::vector<IdleEffect> idle_effects;

  // GPU data: one draw per visible submesh (.skn range), with its texture (the skin's, or a materialOverride's)
  struct Submesh {
    std::string name;
    uint32_t name_hash = 0;
    bool hidden = false;  // initialSubmeshToHide: hidden until a clip's event shows it
    uint32_t index_start = 0, index_count = 0;
    ComPtr<ID3D11ShaderResourceView> texture;
  };
  ComPtr<ID3D11Buffer> vb, ib;
  std::vector<Submesh> submeshes;
};

/** One unit drawn with a model: where it stands, where it faces, which clip it plays. */
struct CharacterInstance {
  const CharacterModel* model = nullptr;
  float3 position;
  float yaw = 0;  // radians, 0 = facing +z
  std::string clip = "Idle1";
  float time = 0;  // seconds since the clip was asked for
  AnimParams params;
  AnimState* state = nullptr;  // when set, the unit's graph state: `clip` is asked for at `now` and switches blend
  double now = 0;
  // when set, the clip the unit stands in while `clip` plays over it on its own track (see CharacterModel::animate)
  AnimState* under_state = nullptr;
  std::string under_clip;
  AnimParams under_params;
  mutable bool layered = false;  // set by the draw: the two clips did play one over the other
  std::vector<float4x4>* joints_out = nullptr;  // when set, receives every joint's world matrix (effects on bones)
  // when set, where the unit stands as a whole matrix (a level prop's transform: any rotation, its own scale) instead
  // of position + yaw; the skin's scale still applies
  const float4x4* place = nullptr;
  // lit_uber_ps TINTING: the colour is multiplied by TINT_COLOR (the brush: the map's grass tint where it stands)
  float tint[3] = {1, 1, 1};
  // an additive clip played over the unit's clip (a plate breaking over the plating's idle), and the seconds into it
  std::string add_clip;
  float add_time = 0;
  // submeshes (fnv1a of their names) hidden for this unit alone, whatever the clips say (a turret's broken plates)
  const std::vector<uint32_t>* hide = nullptr;
  float scale = 1;  // on top of the skin's scale: a structure's map object carries its own (the Chaos fountain's crystal 0.5)
};

class CharacterRenderer {
 public:
  bool init(Gpu& gpu);
  /** The light characters stand in: the ambient cube (LIGHTGRID_COLORS) and LIGHTGRID_SCALE (x: grid light, y: self
   *  illumination). */
  void set_light(const float cube[6][3], float grid_scale, float self_scale) {
    std::memcpy(cube_, cube, sizeof cube_);
    scale_[0] = grid_scale, scale_[1] = self_scale;
  }
  void draw(Gpu& gpu, const float4x4& view_proj, const CharacterInstance& c);

 private:
  ComPtr<ID3D11VertexShader> vs_;
  ComPtr<ID3D11PixelShader> ps_;
  ComPtr<ID3D11InputLayout> layout_;
  ComPtr<ID3D11Buffer> frame_cb_, bones_cb_, light_cb_;
  float cube_[6][3] = {{1, 1, 1}, {1, 1, 1}, {1, 1, 1}, {1, 1, 1}, {1, 1, 1}, {1, 1, 1}};
  float scale_[2] = {1, 1};
  ComPtr<ID3D11SamplerState> sampler_;
};

}  // namespace ba
