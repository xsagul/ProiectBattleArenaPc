#pragma once
// League's particle effects (VfxSystemDefinitionData), read from the property bins and played in League's own units and
// axes. Where each rule comes from is marked in Vfx.cpp (see docs/PROVENIENTA.md):
//   [meta]    field names, types and defaults: the game's class metadata (lol-meta-classes, research/meta/*.json)
//   [shader]  Riot's particle shaders from ShaderCache.dx11 (research/shaders/particles)
//   [date]    what the bins themselves show (statistics over the map's 4378 emitters)
//   [de măsurat]  not settled by any of the above: our reading, to be checked against the real game

#include <array>
#include <cstdint>
#include <memory>
#include <random>
#include <string>
#include <unordered_map>
#include <vector>

#include "Gpu.h"
#include "Math.h"
#include "ba/Model.h"
#include "ba/PropertyBin.h"
#include "ba/Wad.h"

namespace ba {

/** ValueFloat / ValueVector2 / ValueVector3 / ValueColor (and their Integrated variants) [meta]: constantValue and
 *  optional dynamics (times, values, probabilityTables). Absent fields hold the class default. */
struct VfxValue {
  std::array<float, 4> constant{};
  std::vector<float> times;
  std::vector<std::array<float, 4>> values;
  struct Table {
    std::vector<std::pair<float, float>> keys;  // keyTimes / keyValues
    float single = 1;                            // singleValue [meta: default 1]
  };
  std::vector<Table> tables;
  bool animated() const { return !times.empty() && !values.empty(); }

  static VfxValue read(const BinValue* v, std::array<float, 4> dflt);
  std::array<float, 4> curve(float t) const;
  std::array<float, 4> factors(std::mt19937& rng) const;
  std::array<float, 4> sample(float t, const std::array<float, 4>* f = nullptr) const;
  float scalar(float t, const std::array<float, 4>* f = nullptr) const { return sample(t, f)[0]; }
};

struct VfxEmitterDef {
  enum class Kind { None, Billboard, Dir, DirGround, Fixed, Ground, Mesh, Ray, Trail, Beam };
  std::string name;
  Kind kind = Kind::None;
  // VfxPrimitiveBeam: mBeam's mLocalSpaceSourceOffset / mLocalSpaceTargetOffset
  std::array<float, 3> beam_source{}, beam_target{};
  int importance = 2;
  // emission
  VfxValue rate, particle_lifetime, bind_weight, birth_frame_rate;
  bool has_lifetime = false;
  float lifetime = 0, time_before = 0, particle_linger = 0, emitter_linger = 0;
  bool single = false;
  // spawn shape
  enum class Shape { None, Legacy, Box, Sphere, Cylinder } shape = Shape::None;
  VfxValue emit_offset;
  std::vector<VfxValue> rotation_angles;
  std::vector<std::array<float, 3>> rotation_axes;
  std::array<float, 3> box_size{};
  float shape_radius = 0, shape_height = 0;
  // motion
  VfxValue emitter_position, birth_velocity, velocity, birth_acceleration, acceleration, world_acceleration, birth_drag, drag;
  VfxValue birth_orbital_velocity, birth_rotation, birth_rotational_velocity, birth_rotational_acceleration, rotation;
  struct Field {
    enum class Type { Acceleration, Attraction, Drag, Noise, Orbital } type = Type::Acceleration;
    VfxValue position, value, radius, frequency;
    std::array<float, 3> axis_fraction{};
    bool local = true;
  };
  std::vector<Field> fields;
  // look
  VfxValue birth_scale, scale, birth_color, color;
  VfxValue birth_uv_offset, birth_uv_scroll, particle_uv_scroll, uv_scale, uv_rotation, birth_uv_rotate_rate, particle_uv_rotate_rate;
  std::array<float, 2> uv_center{0.5f, 0.5f};
  bool flip_u = false, flip_v = false;
  std::array<float, 2> tex_div{1, 1};
  int num_frames = 1, start_frame = 0;
  float frame_rate = 0;
  bool random_start_frame = false;
  std::string texture, color_texture, mesh;
  struct Mult {
    std::string texture;
    VfxValue uv_scale, birth_uv_offset, birth_uv_scroll, integrated_scroll, uv_rotation;
    std::array<float, 2> center{0.5f, 0.5f};
    bool flip_u = false, flip_v = false;
  } mult;
  int lookup_type[2] = {1, 0};
  float lookup_scale[2] = {1, 1}, lookup_offset[2] = {0, 0};
  int blend_mode = 0, pass = 0, alpha_ref = 5;
  // uvMode [măsurat: all 28 draws of uvMode 2 emitters in two 13.3 replay frames use the SEPARATE_ALPHA_UV mesh
  // permutation or quad_vs_fixedalphauv, none of the others does]: 2 = the texture's alpha is read where the uv would
  // be without its scroll, so a scrolling texture keeps a still alpha mask (waterfalls)
  int uv_mode = 0;
  float depth_push_pull = 0;
  std::array<float, 2> depth_bias{};
  bool uniform = false, local_orientation = true, particle_local_orientation = false, direction_oriented = false, ground = false;
  float direction_velocity_scale = 0, direction_velocity_min_scale = 1;
  bool backface = false;
  // trails (VfxPrimitiveArbitraryTrail / VfxPrimitiveCameraTrail, mTrail: VfxTrailDefinitionData) [meta names]
  bool trail_camera = false;  // CameraTrail: the ribbon faces the camera; ArbitraryTrail: it lies along the particle's x
  float trail_tiling = 0;     // mBirthTilingSize.x: world units per texture repeat along the ribbon
  float trail_cutoff = 0;     // mCutoff
  int trail_mode = 0;         // mMode
  // reflectionDefinition: mesh_vs's Fresnel rim (fresnelColor, fresnel exponent) [meta defaults 0,0,0,0 and 1]
  std::array<float, 4> fresnel_color{};
  float fresnel = 1;
  // alphaErosionDefinition (VfxAlphaErosionDefinitionData) [meta names and defaults; shader: ALPHA_EROSION]
  struct Erosion {
    bool on = false;
    std::string map;                          // erosionMapName
    VfxValue drive;                           // erosionDriveCurve over the particle's life: 0 whole, 1 gone
    std::array<float, 4> mixer{0, 0, 0, 1};   // erosionMapChannelMixer: which channel of the map is read
    float feather_in = 0.1f, feather_out = 0.1f, slice_width = 1.5f;
  } erosion;
  // softParticleParams (VfxSoftParticleDefinitionData) [meta; shader: SOFT_PARTICLES]
  struct Soft {
    bool on = false;
    float begin_in = 0, begin_out = 0, delta_in = 0, delta_out = 0;
  } soft;
  bool navmesh_mask = false;  // useNavmeshMask [meta; shader: NAVMESH_MASK_TEXTURE]
  // childParticleSetDefinition (VfxChildParticleSetDefinitionData) [meta]: a system started for each particle
  std::vector<uint32_t> children;  // childrenIdentifiers' effect links
  bool child_on_death = false;     // childEmitOnDeath
  bool has_child_probability = false;
  VfxValue child_probability;      // childrenProbability
};

struct VfxSystemDef {
  std::string name;
  float visibility_radius = 250;  // [meta]
  std::vector<VfxEmitterDef> emitters;
  // The same emitters with the system's assetRemappingTable applied (empty when it has none). The map's tables swap
  // the Order and Chaos textures of base effects: the client shows them to a Chaos player, whose own base is drawn in
  // the ally colour ("relative team colours"). [observat: a 13.3 replay (spectator) draws SRU_Chaos_LaserTurret_ChestGlow
  // with the plain texture, not the table's _blue one]
  std::vector<VfxEmitterDef> swapped;
};

/** Set once the player's team is known: effects started afterwards use the team-swapped textures (see VfxSystemDef). */
inline bool g_vfx_swap_team_colors = false;

/** Where an effect is: position and orientation (3x3, row-major, acting on column vectors: League local -> world). */
struct VfxFrame {
  float x = 0, y = 0, z = 0;
  std::array<float, 9> m{1, 0, 0, 0, 1, 0, 0, 0, 1};
};

class VfxEmitter;
class NavGrid;

/** One running effect: its system's emitters at one place, tinted by the placement (MapParticle colorModulate). */
class VfxInstance {
 public:
  VfxInstance(const VfxSystemDef& sys, VfxFrame frame, float scale, std::array<float, 4> tint, std::mt19937& rng);
  ~VfxInstance();
  void update(float dt);
  void stop();
  bool finished() const;
  /** Moves the effect (a missile in flight, an effect on a bone): new particles are born at the new place, and those
   *  alive follow it by their emitter's bindWeight. */
  void set_frame(const VfxFrame& frame);
  /** Where the effect's beams end (VfxPrimitiveBeam: from the effect's place to its target). */
  void set_target(float3 target) { target_ = target, has_target_ = true; }
  bool has_target() const { return has_target_; }
  float3 target() const { return target_; }
  const VfxSystemDef& system() const { return *sys_; }
  const VfxFrame& frame() const { return frame_; }
  float scale() const { return scale_; }
  const std::array<float, 4>& tint() const { return tint_; }
  const std::vector<std::unique_ptr<VfxEmitter>>& emitters() const { return emitters_; }
  /** This instance and the child systems its particles started (childParticleSetDefinition), recursively. */
  void collect(std::vector<const VfxInstance*>& out) const;
  int depth() const { return depth_; }
  void set_depth(int d) { depth_ = d; }

 private:
  int depth_ = 0;  // 0 for an effect, n for a child n levels down
  const VfxSystemDef* sys_;
  VfxFrame frame_;
  float scale_;
  std::array<float, 4> tint_;
  float3 target_{};
  bool has_target_ = false;
  std::vector<std::unique_ptr<VfxEmitter>> emitters_;
};

/** Reads systems from bins, loads their textures and meshes, draws running instances. */
class Vfx {
 public:
  bool init(Gpu& gpu);
  /** Reads every VfxSystemDefinitionData of a bin; `wads` are searched in order for textures and meshes. */
  void add_systems(const PropertyBin& bin, std::vector<const Wad*> wads);
  /** A skin's effects: the VfxSystemDefinitionData in its skin bin and the bins it links, and its ResourceResolver
   *  (the keys spells name effects by, e.g. mMissileEffectKey "Ashe_BA_mis" -> Ashe_Base_BA_mis). Loaded once. */
  const std::unordered_map<uint32_t, uint32_t>& skin_effects(const Wad& wad, const std::string& character, int skin, const Wad* shared);
  const VfxSystemDef* system(uint32_t entry_hash) const;
  /** Draws instances. `ground`: only the emitters that lie on the ground (drawn right after the map), else the rest. */
  void draw(Gpu& gpu, const float4x4& view_proj, const float4x4& view, float3 eye, const std::vector<VfxInstance*>& instances,
            bool ground);
  /** The camera's near and far planes (soft particles turn depth back into distance). */
  void set_depth_range(float near_z, float far_z) { near_ = near_z, far_ = far_z; }
  /** NAVMESH_MASK_TEXTURE: 1 over the navigation grid's walkable cells, 0 over its walls (useNavmeshMask). */
  void set_navmesh(Gpu& gpu, const NavGrid& nav);
  std::mt19937& rng() { return rng_; }
  size_t system_count() const { return systems_.size(); }
  /** The game-wide effects: Global.wad's "shared" bin holds the systems every map and character may use and the
   *  GlobalResourceResolver that names them by key (a turret's break effects, the minions' death effects). */
  void add_global(const Wad& global);
  /** A key of the GlobalResourceResolver, or null. */
  const VfxSystemDef* global_effect(uint32_t key) const;
  /** A report of running instances: each emitter's kind, particle count and its first particle (checks). */
  static std::string describe(const std::vector<VfxInstance*>& instances);

 private:
  struct Mesh {
    StaticMesh data;
    bool flat = false;  // its height is a hundredth of its width or less: it lies on the ground like a decal
  };
  ComPtr<ID3D11ShaderResourceView> texture(Gpu& gpu, const std::string& path);
  const Mesh* mesh(const std::string& path);

  std::unordered_map<uint32_t, VfxSystemDef> systems_;
  std::unordered_map<std::string, std::unordered_map<uint32_t, uint32_t>> resolvers_;
  std::vector<std::string> loaded_bins_;
  std::unordered_map<uint32_t, uint32_t> global_resolver_;
  std::vector<const Wad*> wads_;
  std::unordered_map<std::string, ComPtr<ID3D11ShaderResourceView>> textures_;
 public:
  /** Texture paths that could not be loaded (drawn white), for checks. */
  std::vector<std::string> missing_textures() const {
    std::vector<std::string> out;
    for (const auto& [p, t] : textures_)
      if (!t) out.push_back(p);
    return out;
  }
 private:
  std::unordered_map<std::string, std::unique_ptr<Mesh>> meshes_;
  std::mt19937 rng_{12345};

  ComPtr<ID3D11VertexShader> vs_;
  ComPtr<ID3D11PixelShader> ps_;
  ComPtr<ID3D11InputLayout> layout_;
  ComPtr<ID3D11Buffer> vb_, frame_cb_, draw_cb_;
  ComPtr<ID3D11BlendState> additive_, alpha_, add_one_;
  ComPtr<ID3D11DepthStencilState> depth_test_, depth_off_, depth_write_;
  ComPtr<ID3D11RasterizerState> cull_none_, cull_back_, ground_bias_;
  ComPtr<ID3D11SamplerState> sampler_, clamp_;
  ComPtr<ID3D11ShaderResourceView> white_, navmask_;
  std::array<float, 4> nav_xform_{0, 0, 0, 0};  // NAV_GRID_XFORM: uv = xy * world xz + zw
  float near_ = 50, far_ = 20000;
  size_t vb_capacity_ = 0;
};

}  // namespace ba
