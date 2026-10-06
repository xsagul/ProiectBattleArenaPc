#include "Vfx.h"

#include <algorithm>
#include <cmath>
#include <cstring>

#include "ba/Hash.h"
#include "ba/NavGrid.h"
#include "ba/Texture.h"

namespace ba {

namespace {

constexpr float kD2R = 3.14159265f / 180.f;
constexpr size_t kMaxParticles = 320;  // our cap per emitter (League's is not known)
constexpr float kForever = 1e9f;

// ---------------------------------------------------------------- reading bins

/** An Option's value (particleLinger, lifetime ...), or the value itself. */
const BinValue* unwrap(const BinValue* v) {
  if (v && v->type == BinType::Option) return v->items.empty() ? nullptr : &v->items[0];
  return v;
}
const BinValue* field(const BinValue& e, const char* name) { return unwrap(e.field(name)); }
float number(const BinValue* v, float dflt) { return v ? static_cast<float>(v->number()) : dflt; }
std::array<float, 4> numbers(const BinValue& v) {
  return {static_cast<float>(v.num[0]), static_cast<float>(v.num[1]), static_cast<float>(v.num[2]), static_cast<float>(v.num[3])};
}
bool flag(const BinValue& e, const char* name, bool dflt) {
  const BinValue* v = field(e, name);
  return v ? v->number() != 0 : dflt;
}
std::string lower(std::string s) {
  for (char& c : s) c = static_cast<char>(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
  return s;
}
std::string text(const BinValue* v) { return v ? lower(v->str) : std::string(); }
std::array<float, 2> vec2(const BinValue* v, std::array<float, 2> dflt) {
  return v ? std::array<float, 2>{static_cast<float>(v->num[0]), static_cast<float>(v->num[1])} : dflt;
}

// ---------------------------------------------------------------- 3x3 helpers (row-major, acting on column vectors)
using M3 = std::array<float, 9>;
constexpr M3 kI3{1, 0, 0, 0, 1, 0, 0, 0, 1};
M3 mul(const M3& a, const M3& b) {
  M3 o{};
  for (int r = 0; r < 3; ++r)
    for (int c = 0; c < 3; ++c) o[r * 3 + c] = a[r * 3] * b[c] + a[r * 3 + 1] * b[3 + c] + a[r * 3 + 2] * b[6 + c];
  return o;
}
std::array<float, 3> app(const M3& m, float x, float y, float z) {
  return {m[0] * x + m[1] * y + m[2] * z, m[3] * x + m[4] * y + m[5] * z, m[6] * x + m[7] * y + m[8] * z};
}
std::array<float, 3> app_t(const M3& m, float x, float y, float z) {
  return {m[0] * x + m[3] * y + m[6] * z, m[1] * x + m[4] * y + m[7] * z, m[2] * x + m[5] * y + m[8] * z};
}
M3 rot_axis(float ax, float ay, float az, float deg) {
  float l = std::sqrt(ax * ax + ay * ay + az * az);
  if (l == 0) l = 1;
  const float x = ax / l, y = ay / l, z = az / l;
  const float c = std::cos(deg * kD2R), s = std::sin(deg * kD2R), t = 1 - c;
  return {t * x * x + c, t * x * y - s * z, t * x * z + s * y, t * x * y + s * z, t * y * y + c,
          t * y * z - s * x, t * x * z - s * y, t * y * z + s * x, t * z * z + c};
}
/** Euler rotation in degrees, applied z, then x, then y [de măsurat: the order]. */
M3 euler(float rx, float ry, float rz) { return mul(mul(rot_axis(0, 1, 0, ry), rot_axis(1, 0, 0, rx)), rot_axis(0, 0, 1, rz)); }
M3 yaw_only(const M3& m) { return rot_axis(0, 1, 0, std::atan2(m[2], m[8]) * 180.f / 3.14159265f); }

}  // namespace

// ---------------------------------------------------------------- values

VfxValue VfxValue::read(const BinValue* v, std::array<float, 4> dflt) {
  VfxValue out;
  out.constant = dflt;
  v = unwrap(v);
  if (!v) return out;
  if (v->type != BinType::Embed && v->type != BinType::Pointer) {
    out.constant = numbers(*v);
    return out;
  }
  // an embedded Value*: its own constantValue defaults to 0 [meta: ValueFloat constantValue 0]
  out.constant = {};
  if (const BinValue* c = v->field("constantValue")) out.constant = numbers(*c);
  if (const BinValue* d = v->field("dynamics")) {
    if (const BinValue* t = d->field("times"))
      for (const BinValue& x : t->items) out.times.push_back(static_cast<float>(x.number()));
    if (const BinValue* vals = d->field("values"))
      for (const BinValue& x : vals->items) out.values.push_back(numbers(x));
    if (const BinValue* p = d->field("probabilityTables"))
      for (const BinValue& tb : p->items) {
        Table table;
        const BinValue* kt = tb.field("keyTimes");
        const BinValue* kv = tb.field("keyValues");
        if (kt && kv)
          for (size_t i = 0; i < kt->items.size() && i < kv->items.size(); ++i)
            table.keys.emplace_back(static_cast<float>(kt->items[i].number()), static_cast<float>(kv->items[i].number()));
        table.single = number(tb.field("singleValue"), 1);
        out.tables.push_back(std::move(table));
      }
  }
  return out;
}

// the curve over normalized time: linear between keys [de măsurat: interpolation]
std::array<float, 4> VfxValue::curve(float t) const {
  if (!animated()) return constant;
  const size_t n = std::min(times.size(), values.size());
  if (n == 1 || t <= times[0]) return values[0];
  for (size_t i = 1; i < n; ++i)
    if (t <= times[i]) {
      const float k = times[i] == times[i - 1] ? 1.f : (t - times[i - 1]) / (times[i] - times[i - 1]);
      std::array<float, 4> o{};
      for (size_t j = 0; j < 4; ++j) o[j] = values[i - 1][j] + (values[i][j] - values[i - 1][j]) * k;
      return o;
    }
  return values[n - 1];
}

// one factor per component from its probability table: a uniform draw mapped through keyTimes -> keyValues; a table
// without keys gives singleValue [de măsurat: the mapping]
std::array<float, 4> VfxValue::factors(std::mt19937& rng) const {
  std::array<float, 4> f{1, 1, 1, 1};
  std::uniform_real_distribution<float> uni(0.f, 1.f);
  for (size_t i = 0; i < tables.size() && i < 4; ++i) {
    const auto& keys = tables[i].keys;
    if (keys.empty()) {
      f[i] = tables[i].single;
      continue;
    }
    const float u = uni(rng);
    float k = keys.back().second;
    if (u <= keys[0].first) {
      k = keys[0].second;
    } else {
      for (size_t j = 1; j < keys.size(); ++j)
        if (u <= keys[j].first) {
          const float w = keys[j].first == keys[j - 1].first ? 1.f : (u - keys[j - 1].first) / (keys[j].first - keys[j - 1].first);
          k = keys[j - 1].second + (keys[j].second - keys[j - 1].second) * w;
          break;
        }
    }
    f[i] = k;
  }
  return f;
}

std::array<float, 4> VfxValue::sample(float t, const std::array<float, 4>* f) const {
  std::array<float, 4> b = curve(t);
  if (f)
    for (size_t i = 0; i < 4; ++i) b[i] *= (*f)[i];
  return b;
}

// ---------------------------------------------------------------- emitter definitions [meta: names and defaults]

namespace {

constexpr std::array<float, 4> k0{0, 0, 0, 0}, k1{1, 1, 1, 1};

VfxEmitterDef read_emitter(const BinValue& e) {
  VfxEmitterDef d;
  auto value = [&e](const char* name, std::array<float, 4> dflt) { return VfxValue::read(e.field(name), dflt); };
  d.name = e.field("emitterName") ? e.field("emitterName")->str : std::string("?");
  d.importance = static_cast<int>(number(field(e, "importance"), 2));
  d.rate = value("rate", k0);
  d.particle_lifetime = value("particleLifetime", {3, 3, 3, 3});
  d.bind_weight = value("bindWeight", k0);
  d.birth_frame_rate = value("birthFrameRate", k1);
  if (const BinValue* l = field(e, "lifetime")) d.has_lifetime = true, d.lifetime = number(l, 0);
  d.time_before = number(field(e, "timeBeforeFirstEmission"), 0);
  d.particle_linger = number(field(e, "particleLinger"), 0);
  d.emitter_linger = number(field(e, "emitterLinger"), 0);
  d.single = flag(e, "isSingleParticle", false);

  if (const BinValue* sh = field(e, "SpawnShape")) {
    if (sh->cls == fnv1a("VfxShapeLegacy") || sh->cls == 0xee39916fu) {  // 0xee39916f: VfxShapePointDoNotUse (emitOffset only) [meta]
      d.shape = VfxEmitterDef::Shape::Legacy;
      d.emit_offset = VfxValue::read(sh->field("emitOffset"), k0);
      if (const BinValue* a = sh->field("emitRotationAngles"))
        for (const BinValue& x : a->items) d.rotation_angles.push_back(VfxValue::read(&x, k0));
      if (const BinValue* a = sh->field("emitRotationAxes"))
        for (const BinValue& x : a->items) d.rotation_axes.push_back({static_cast<float>(x.num[0]), static_cast<float>(x.num[1]), static_cast<float>(x.num[2])});
    } else if (sh->cls == fnv1a("VfxShapeBox")) {
      d.shape = VfxEmitterDef::Shape::Box;
      if (const BinValue* s = sh->field("Size")) d.box_size = {static_cast<float>(s->num[0]), static_cast<float>(s->num[1]), static_cast<float>(s->num[2])};
    } else if (sh->cls == fnv1a("VfxShapeSphere")) {
      d.shape = VfxEmitterDef::Shape::Sphere;
      d.shape_radius = number(sh->field("radius"), 0);
    } else if (sh->cls == fnv1a("VfxShapeCylinder")) {
      d.shape = VfxEmitterDef::Shape::Cylinder;
      d.shape_radius = number(sh->field("radius"), 0);
      d.shape_height = number(sh->field("height"), 0);
    }
  }
  d.emitter_position = value("EmitterPosition", k0);
  d.birth_velocity = value("birthVelocity", k0);
  d.velocity = value("velocity", k0);
  d.birth_acceleration = value("birthAcceleration", k0);
  d.acceleration = value("acceleration", k0);
  d.world_acceleration = value("worldAcceleration", k0);
  d.birth_drag = value("birthDrag", k0);
  d.drag = value("drag", k0);
  d.birth_orbital_velocity = value("birthOrbitalVelocity", k0);
  d.birth_rotation = value("birthRotation0", k0);
  d.birth_rotational_velocity = value("birthRotationalVelocity0", k0);
  d.birth_rotational_acceleration = value("birthRotationalAcceleration", k0);
  d.rotation = value("rotation0", k0);
  if (const BinValue* fc = field(e, "fieldCollectionDefinition")) {
    using Field = VfxEmitterDef::Field;
    auto list = [&](const char* name, Field::Type type) {
      if (const BinValue* l = fc->field(name))
        for (const BinValue& f : l->items) {
          Field x;
          x.type = type;
          x.position = VfxValue::read(f.field("Position"), k0);
          x.radius = VfxValue::read(f.field("radius"), k0);
          x.frequency = VfxValue::read(f.field("frequency"), k0);
          switch (type) {
            case Field::Type::Acceleration: x.value = VfxValue::read(f.field("acceleration"), k0); break;
            case Field::Type::Attraction: x.value = VfxValue::read(f.field("acceleration"), k0); break;
            case Field::Type::Drag: x.value = VfxValue::read(f.field("strength"), k0); break;
            case Field::Type::Noise: x.value = VfxValue::read(f.field("velocityDelta"), k0); break;
            case Field::Type::Orbital: x.value = VfxValue::read(f.field("direction"), {0, 1, 0, 0}); break;
          }
          if (const BinValue* a = f.field("axisFraction")) x.axis_fraction = {static_cast<float>(a->num[0]), static_cast<float>(a->num[1]), static_cast<float>(a->num[2])};
          x.local = flag(f, "isLocalSpace", true);
          d.fields.push_back(x);
        }
    };
    list("fieldAccelerationDefinitions", Field::Type::Acceleration);
    list("fieldAttractionDefinitions", Field::Type::Attraction);
    list("fieldDragDefinitions", Field::Type::Drag);
    list("fieldNoiseDefinitions", Field::Type::Noise);
    list("fieldOrbitalDefinitions", Field::Type::Orbital);
  }
  d.birth_scale = value("birthScale0", k1);
  d.scale = value("scale0", k1);
  d.birth_color = value("birthColor", k1);
  d.color = value("Color", k1);
  d.birth_uv_offset = value("birthUVOffset", k0);
  d.birth_uv_scroll = value("birthUvScrollRate", k0);
  d.particle_uv_scroll = value("particleUVScrollRate", k0);
  d.uv_scale = value("uvScale", k1);
  d.uv_rotation = value("uvRotation", k0);
  d.birth_uv_rotate_rate = value("birthUvRotateRate", k0);
  d.particle_uv_rotate_rate = value("particleUVRotateRate", k0);
  d.uv_center = vec2(field(e, "uvTransformCenter"), {0.5f, 0.5f});
  d.flip_u = flag(e, "TextureFlipU", false);
  d.flip_v = flag(e, "TextureFlipV", false);
  d.tex_div = vec2(field(e, "texDiv"), {1, 1});
  d.num_frames = static_cast<int>(number(field(e, "numFrames"), 1));
  d.start_frame = static_cast<int>(number(field(e, "startFrame"), 0));
  d.frame_rate = number(field(e, "frameRate"), 0);
  d.random_start_frame = flag(e, "isRandomStartFrame", false);
  d.texture = text(field(e, "texture"));
  d.color_texture = e.field("particleColorTexture") ? text(field(e, "particleColorTexture")) : "assets/shared/particles/defaultcoloroverlifetime.png";
  // 12.23: the mult texture and its uv fields are the emitter's own (textureMult is the path itself; later patches
  // moved them into a VfxTextureMultDefinitionData). [verificat: our draws set against the real client's: without the
  // mult texture the base's waterfalls came out far brighter than the game's]
  if (const BinValue* tm = field(e, "textureMult"); tm && tm->type == BinType::String) {
    d.mult.texture = text(tm);
    d.mult.uv_scale = VfxValue::read(e.field("uvScaleMult"), k1);
    d.mult.birth_uv_offset = VfxValue::read(e.field("birthUVOffsetMult"), k0);
    d.mult.birth_uv_scroll = VfxValue::read(e.field("birthUvScrollRateMult"), k0);
    // birthUvRotateRateMult (4 emitters of the map), texDivMult, uvScrollAlphaMult, uvScrollClampMult: not read yet
    d.mult.center = vec2(field(e, "uvTransformCenterMult"), {0.5f, 0.5f});
  }
  d.lookup_type[0] = static_cast<int>(number(field(e, "colorLookUpTypeX"), 1));
  d.lookup_type[1] = static_cast<int>(number(field(e, "colorLookUpTypeY"), 0));
  const auto ls = vec2(field(e, "colorLookUpScales"), {1, 1});
  const auto lo = vec2(field(e, "colorLookUpOffsets"), {0, 0});
  d.lookup_scale[0] = ls[0], d.lookup_scale[1] = ls[1], d.lookup_offset[0] = lo[0], d.lookup_offset[1] = lo[1];
  d.blend_mode = static_cast<int>(number(field(e, "blendMode"), 0));
  d.uv_mode = static_cast<int>(number(field(e, "uvMode"), 0));
  d.pass = static_cast<int>(number(field(e, "pass"), 0));
  d.alpha_ref = static_cast<int>(number(field(e, "alphaRef"), 5));
  d.depth_push_pull = number(field(e, "DepthPushPull"), 0);
  d.depth_bias = vec2(field(e, "depthBiasFactors"), {0, 0});
  d.uniform = flag(e, "isUniformScale", false);
  d.local_orientation = flag(e, "isLocalOrientation", true);
  d.particle_local_orientation = flag(e, "particleIsLocalOrientation", false);
  d.direction_oriented = flag(e, "isDirectionOriented", false);
  d.direction_velocity_scale = number(field(e, "directionVelocityScale"), 0);
  d.direction_velocity_min_scale = number(field(e, "directionVelocityMinScale"), 1);
  d.ground = flag(e, "isGroundLayer", false);
  d.backface = flag(e, "disableBackfaceCull", false);
  if (const BinValue* rf = field(e, "reflectionDefinition")) {
    if (const BinValue* c = rf->field("fresnelColor")) d.fresnel_color = numbers(*c);
    d.fresnel = number(rf->field("fresnel"), 1);
  }
  if (const BinValue* er = field(e, "alphaErosionDefinition")) {
    d.erosion.map = text(field(*er, "erosionMapName"));
    d.erosion.on = !d.erosion.map.empty();  // without a map there is nothing to erode by [de măsurat]
    d.erosion.drive = VfxValue::read(er->field("erosionDriveCurve"), k1);
    if (const BinValue* m = field(*er, "erosionMapChannelMixer")) d.erosion.mixer = VfxValue::read(m, {0, 0, 0, 1}).curve(0);
    d.erosion.feather_in = number(field(*er, "erosionFeatherIn"), 0.1f);
    d.erosion.feather_out = number(field(*er, "erosionFeatherOut"), 0.1f);
    d.erosion.slice_width = number(field(*er, "erosionSliceWidth"), 1.5f);
  }
  if (const BinValue* sp = field(e, "softParticleParams")) {
    d.soft.on = true;
    d.soft.begin_in = number(field(*sp, "beginIn"), 0);
    d.soft.begin_out = number(field(*sp, "beginOut"), 0);
    d.soft.delta_in = number(field(*sp, "deltaIn"), 0);
    d.soft.delta_out = number(field(*sp, "deltaOut"), 0);
  }
  d.navmesh_mask = flag(e, "useNavmeshMask", false);
  if (const BinValue* cs = field(e, "childParticleSetDefinition")) {
    if (const BinValue* ids = cs->field("childrenIdentifiers"))
      for (const BinValue& id : ids->items)
        if (const BinValue* l = id.field("effect"); l && l->u) d.children.push_back(static_cast<uint32_t>(l->u));
    d.child_on_death = flag(*cs, "childEmitOnDeath", false);
    if (const BinValue* p = cs->field("childrenProbability")) d.has_child_probability = true, d.child_probability = VfxValue::read(p, k0);
  }

  // what it draws: the primitive's class [meta: VfxLegacyPrimitiveBase subclasses]; the quad kinds' orientation rules
  // are our reading of isGroundLayer / isDirectionOriented / VfxPrimitiveArbitraryQuad [de măsurat]
  using Kind = VfxEmitterDef::Kind;
  const BinValue* prim = field(e, "primitive");
  const uint32_t pc = prim ? prim->cls : 0;
  if (flag(e, "disabled", false) || field(e, "distortionDefinition")) {
    d.kind = Kind::None;  // distortion needs a refraction pass we do not have yet
  } else if (pc == fnv1a("VfxPrimitiveMesh") || pc == fnv1a("VfxPrimitiveAttachedMesh")) {
    const BinValue* md = field(*prim, "mMesh");
    d.mesh = md ? text(field(*md, "mSimpleMeshName")) : std::string();
    if (d.mesh.empty() && md) {
      if (const BinValue* v = field(*md, "mMeshName")) d.mesh = text(v);
      else if (const BinValue* v = field(*md, "mSkinnedMeshName")) d.mesh = text(v);
      else if (const BinValue* v = field(*md, "mStaticMeshName")) d.mesh = text(v);
    }
    d.kind = d.mesh.empty() ? Kind::None : Kind::Mesh;
  } else if (d.texture.empty()) {
    d.kind = Kind::None;
  } else if (pc == fnv1a("VfxPrimitiveCameraTrail") || pc == fnv1a("VfxPrimitiveArbitraryTrail")) {
    d.kind = Kind::Trail;
    d.trail_camera = pc == fnv1a("VfxPrimitiveCameraTrail");
    if (const BinValue* t = field(*prim, "mTrail")) {
      d.trail_tiling = VfxValue::read(field(*t, "mBirthTilingSize"), k0).curve(0)[0];
      d.trail_cutoff = number(field(*t, "mCutoff"), 0);
      d.trail_mode = static_cast<int>(number(field(*t, "mMode"), 0));
    }
  } else if (pc == fnv1a("VfxPrimitiveBeam")) {
    d.kind = Kind::Beam;
    if (const BinValue* b = field(*prim, "mBeam")) {
      if (const BinValue* o = field(*b, "mLocalSpaceSourceOffset")) d.beam_source = {static_cast<float>(o->num[0]), static_cast<float>(o->num[1]), static_cast<float>(o->num[2])};
      if (const BinValue* o = field(*b, "mLocalSpaceTargetOffset")) d.beam_target = {static_cast<float>(o->num[0]), static_cast<float>(o->num[1]), static_cast<float>(o->num[2])};
    }
  } else if (pc == fnv1a("VfxPrimitiveRay")) {
    d.kind = d.direction_oriented ? Kind::Dir : Kind::Ray;
  } else if (pc == fnv1a("VfxPrimitiveArbitraryQuad")) {
    d.kind = d.ground && d.direction_oriented ? Kind::DirGround : Kind::Fixed;
  } else if (d.ground) {
    d.kind = d.direction_oriented ? Kind::DirGround : Kind::Ground;
  } else {
    d.kind = d.direction_oriented ? Kind::Dir : Kind::Billboard;
  }
  return d;
}

}  // namespace

// ---------------------------------------------------------------- the emitter at run time

struct VfxParticle {
  float age = 0, life = 1, seed = 0;
  float x = 0, y = 0, z = 0, vx = 0, vy = 0, vz = 0, px = 0, py = 0, pz = 0;
  float ox = 0, oy = 0, oz = 0;  // where the effect was at birth (for bindWeight)
  M3 m = kI3, fm = kI3;
  std::array<float, 3> pivot{};
  std::array<float, 4> acc{}, drag{}, orbit{}, rot0{}, rv{}, ra{}, bs{1, 1, 1, 1}, bc{1, 1, 1, 1};
  std::array<float, 4> f_vel{1, 1, 1, 1}, f_acc{1, 1, 1, 1}, f_drag{1, 1, 1, 1}, f_scale{1, 1, 1, 1}, f_color{1, 1, 1, 1}, f_rot{1, 1, 1, 1};
  std::array<float, 4> rot_int{}, wacc_int{};  // integrated values so far
  float uv_off[2] = {}, uv_scroll[2] = {}, uv_scroll_int[2] = {}, uv_rot_rate = 0, uv_rot_int = 0;
  float mult_off[2] = {}, mult_scroll[2] = {}, mult_int[2] = {};
  float dir_x = 0, dir_y = 1, dir_z = 0, speed = 0;
  int frame0 = 0;
  uint32_t id = 0;
};

namespace {
// the systems child particle sets name (filled by Vfx::add_systems; the map's nodes do not move once inserted)
const std::unordered_map<uint32_t, VfxSystemDef>* g_systems = nullptr;
constexpr int kMaxChildDepth = 4;  // our guard against systems that start themselves
}  // namespace

class VfxEmitter {
 public:
  VfxEmitter(const VfxEmitterDef& d, const VfxFrame& f, const VfxInstance& owner, std::mt19937& rng) : d_(d), f_(f), owner_(owner), rng_(rng) {
    bind_ = d.bind_weight.scalar(0);
    const auto r0 = d.birth_rotation.curve(0);
    flat_ = d.kind == VfxEmitterDef::Kind::Ground || d.kind == VfxEmitterDef::Kind::DirGround ||
            (d.kind == VfxEmitterDef::Kind::Fixed && (d.ground || std::fabs(std::fmod(std::fabs(r0[0]), 180.f) - 90.f) < 1));
  }

  const VfxEmitterDef& def() const { return d_; }
  void set_frame(const VfxFrame& f) { f_ = f; }
  const std::vector<VfxParticle>& particles() const { return parts_; }
  bool flat() const { return flat_; }
  float bind() const { return bind_; }
  float age() const { return t_; }

  bool done() const {
    return parts_.empty() && children_.empty() && orphans_.empty() &&
           (stopped_ || (d_.has_lifetime && t_ > d_.time_before + d_.lifetime + 0.001f) || (d_.single && spawned_single_));
  }

  // stopped: particles live on for particleLinger seconds, the emitter keeps emitting for emitterLinger [meta names]
  void stop() {
    if (stopped_) return;
    stopped_ = true, stop_t_ = t_;
    for (VfxParticle& p : parts_) p.life = std::min(p.life, p.age + std::max(0.001f, d_.particle_linger));
  }

  void collect(std::vector<const VfxInstance*>& out) const {
    for (const Child& c : children_) c.inst->collect(out);
    for (const auto& o : orphans_) o->collect(out);
  }

  /** Where a particle is in the world (the effect's place, the particle's birth place by bindWeight, its offset). */
  float3 world(const VfxParticle& p) const {
    const float S = owner_.scale(), bw = bind_;
    return {f_.x * bw + p.ox * (1 - bw) + p.x * S, f_.y * bw + p.oy * (1 - bw) + p.y * S, f_.z * bw + p.oz * (1 - bw) + p.z * S};
  }

  void update(float dt) {
    t_ += dt;
    if (d_.kind == VfxEmitterDef::Kind::None) return;
    const float te = t_ - d_.time_before;
    const bool emitting = te >= 0 && (!stopped_ || t_ - stop_t_ < d_.emitter_linger) && (!d_.has_lifetime || te <= d_.lifetime);
    if (emitting) {
      if (d_.single) {
        if (!spawned_single_) spawned_single_ = true, spawn(0);
      } else {
        // rate: particles per second over the emitter's normalized life (0 without a lifetime). The first one is born
        // when emission starts [de măsurat: whether it waits a full interval]
        const float tn = d_.has_lifetime && d_.lifetime > 0 ? std::min(1.f, te / d_.lifetime) : 0.f;
        if (!started_) started_ = true, acc_ = 1;
        acc_ += d_.rate.scalar(tn) * dt;
        int guard = 0;
        while (acc_ >= 1 && guard++ < 64) acc_ -= 1, spawn(tn);
      }
    }
    size_t w = 0;
    for (size_t i = 0; i < parts_.size(); ++i) {
      VfxParticle& p = parts_[i];
      p.age += dt;
      if (p.age >= p.life) {
        died(p);
        continue;
      }
      step(p, dt);
      parts_[w++] = p;
    }
    parts_.resize(w);
    // child systems: those started by a living particle follow it [de măsurat: position only, the effect's own
    // orientation]; once their particle is gone they are stopped and play out where they are
    for (size_t i = 0; i < children_.size();) {
      Child& c = children_[i];
      const auto it = std::find_if(parts_.begin(), parts_.end(), [&](const VfxParticle& p) { return p.id == c.pid; });
      if (it == parts_.end()) {
        c.inst->stop();
        orphans_.push_back(std::move(c.inst));
        children_.erase(children_.begin() + static_cast<std::ptrdiff_t>(i));
        continue;
      }
      VfxFrame fr = f_;
      const float3 at = world(*it);
      fr.x = at.x, fr.y = at.y, fr.z = at.z;
      c.inst->set_frame(fr);
      c.inst->update(dt);
      ++i;
    }
    for (auto& o : orphans_) o->update(dt);
    std::erase_if(orphans_, [](const std::unique_ptr<VfxInstance>& o) { return o->finished(); });
  }

 private:
  float rnd() { return std::uniform_real_distribution<float>(0.f, 1.f)(rng_); }
  std::array<float, 4> drawn(const VfxValue& v, float tn) {
    const auto f = v.factors(rng_);
    return v.sample(tn, &f);
  }

  void spawn(float tn) {
    if (parts_.size() >= kMaxParticles) return;
    VfxParticle p;
    p.seed = rnd();
    const float life = drawn(d_.particle_lifetime, tn)[0];
    p.life = life < 0 ? kForever : std::max(0.02f, life);  // [date] -1 is used with single particles that stay

    // ---- where it is born, in the effect's own space
    M3 R = kI3;
    float ox = 0, oy = 0, oz = 0;
    using Shape = VfxEmitterDef::Shape;
    if (d_.shape == Shape::Legacy) {
      const auto off = drawn(d_.emit_offset, tn);
      ox = off[0], oy = off[1], oz = off[2];
      for (size_t i = 0; i < d_.rotation_angles.size(); ++i) {
        const float ang = drawn(d_.rotation_angles[i], tn)[0];
        const auto ax = i < d_.rotation_axes.size() ? d_.rotation_axes[i] : std::array<float, 3>{0, 1, 0};
        const M3 rm = rot_axis(ax[0], ax[1], ax[2], ang);
        R = mul(rm, R);
        const auto o = app(rm, ox, oy, oz);
        ox = o[0], oy = o[1], oz = o[2];
      }
    } else if (d_.shape == Shape::Box) {  // uniform inside [de măsurat]
      ox = (rnd() - 0.5f) * d_.box_size[0], oy = (rnd() - 0.5f) * d_.box_size[1], oz = (rnd() - 0.5f) * d_.box_size[2];
    } else if (d_.shape == Shape::Sphere) {  // uniform inside [de măsurat]
      const float r = d_.shape_radius * std::cbrt(rnd()), u = rnd() * 2 - 1, a = rnd() * 6.2831853f, s = std::sqrt(1 - u * u);
      ox = std::cos(a) * s * r, oy = u * r, oz = std::sin(a) * s * r;
    } else if (d_.shape == Shape::Cylinder) {  // uniform inside, base at 0 [de măsurat]
      const float r = d_.shape_radius * std::sqrt(rnd()), a = rnd() * 6.2831853f;
      ox = std::cos(a) * r, oz = std::sin(a) * r, oy = rnd() * d_.shape_height;
    }
    const auto ep = d_.emitter_position.curve(tn);
    const M3& F = f_.m;
    p.fm = F;
    const auto wpos = app(F, ep[0] + ox, ep[1] + oy, ep[2] + oz);
    p.x = wpos[0], p.y = wpos[1], p.z = wpos[2];
    const auto piv = app(F, ep[0], ep[1], ep[2]);
    p.pivot = {piv[0], piv[1], piv[2]};
    p.m = mul(F, R);
    p.ox = f_.x, p.oy = f_.y, p.oz = f_.z;

    // ---- motion: birth values in the effect's (shape-rotated) space [de măsurat: spaces]
    const auto bv = drawn(d_.birth_velocity, tn);
    const auto v0 = app(p.m, bv[0], bv[1], bv[2]);
    p.vx = v0[0], p.vy = v0[1], p.vz = v0[2];
    p.f_vel = d_.velocity.factors(rng_);
    p.acc = drawn(d_.birth_acceleration, tn);
    p.f_acc = d_.acceleration.factors(rng_);
    p.drag = drawn(d_.birth_drag, tn);
    p.f_drag = d_.drag.factors(rng_);
    p.orbit = drawn(d_.birth_orbital_velocity, tn);
    p.rot0 = drawn(d_.birth_rotation, tn);
    p.rv = drawn(d_.birth_rotational_velocity, tn);
    p.ra = drawn(d_.birth_rotational_acceleration, tn);
    p.f_rot = d_.rotation.factors(rng_);
    p.px = p.x, p.py = p.y, p.pz = p.z;
    p.dir_x = p.vx, p.dir_y = p.vy, p.dir_z = p.vz;
    p.speed = std::sqrt(p.vx * p.vx + p.vy * p.vy + p.vz * p.vz);

    // ---- look
    p.bs = drawn(d_.birth_scale, tn);
    p.f_scale = d_.scale.factors(rng_);
    p.bc = drawn(d_.birth_color, tn);
    p.f_color = d_.color.factors(rng_);
    const auto uo = drawn(d_.birth_uv_offset, tn), us = drawn(d_.birth_uv_scroll, tn);
    p.uv_off[0] = uo[0], p.uv_off[1] = uo[1], p.uv_scroll[0] = us[0], p.uv_scroll[1] = us[1];
    p.uv_rot_rate = drawn(d_.birth_uv_rotate_rate, tn)[0];
    const auto mo = drawn(d_.mult.birth_uv_offset, tn), ms = drawn(d_.mult.birth_uv_scroll, tn);
    p.mult_off[0] = mo[0], p.mult_off[1] = mo[1], p.mult_scroll[0] = ms[0], p.mult_scroll[1] = ms[1];
    p.frame0 = d_.random_start_frame ? static_cast<int>(rnd() * static_cast<float>(d_.num_frames)) % std::max(1, d_.num_frames) : d_.start_frame;
    p.id = ++next_id_;
    parts_.push_back(p);
    if (!d_.child_on_death) start_children(parts_.back(), tn, true);
  }

  /** Starts the particle's child systems (childrenIdentifiers), each with childrenProbability when the set has one
   *  [de măsurat: a set without it is taken as always; the meta default 0 would make it never]. */
  void start_children(const VfxParticle& p, float tn, bool follow) {
    if (d_.children.empty() || !g_systems || owner_.depth() >= kMaxChildDepth) return;
    if (d_.has_child_probability && rnd() >= d_.child_probability.scalar(tn)) return;
    const float3 at = world(p);
    VfxFrame fr = f_;
    fr.x = at.x, fr.y = at.y, fr.z = at.z;
    for (uint32_t h : d_.children) {
      const auto it = g_systems->find(h);
      if (it == g_systems->end()) continue;
      auto inst = std::make_unique<VfxInstance>(it->second, fr, owner_.scale(), owner_.tint(), rng_);
      inst->set_depth(owner_.depth() + 1);
      if (follow) children_.push_back({p.id, std::move(inst)});
      else orphans_.push_back(std::move(inst));
    }
  }

  void died(const VfxParticle& p) {
    if (d_.child_on_death) start_children(p, 1.f, false);
  }

  void step(VfxParticle& p, float dt) {
    const float tn = std::min(1.f, p.age / p.life);
    p.px = p.x, p.py = p.y, p.pz = p.z;
    // accelerations: birthAcceleration + acceleration(t) in the effect's space, worldAcceleration (integrated) in the
    // world's [meta names and types; de măsurat: spaces]
    const auto a_life = d_.acceleration.sample(tn, &p.f_acc);
    const auto a = app(p.m, p.acc[0] + a_life[0], p.acc[1] + a_life[1], p.acc[2] + a_life[2]);
    const auto wa = d_.world_acceleration.curve(tn);
    p.vx += (a[0] + wa[0]) * dt, p.vy += (a[1] + wa[1]) * dt, p.vz += (a[2] + wa[2]) * dt;
    using Field = VfxEmitterDef::Field;
    for (const Field& fd : d_.fields) {
      const auto pos = fd.position.curve(tn);
      const auto c = fd.local ? app(p.fm, pos[0], pos[1], pos[2]) : std::array<float, 3>{pos[0], pos[1], pos[2]};
      const float dx = c[0] - p.x, dy = c[1] - p.y, dz = c[2] - p.z;
      const float dist = std::sqrt(dx * dx + dy * dy + dz * dz);
      const float radius = fd.radius.scalar(tn);
      switch (fd.type) {  // [de măsurat: every field's law]
        case Field::Type::Acceleration: {
          const auto v = fd.value.curve(tn);
          const auto w = fd.local ? app(p.fm, v[0], v[1], v[2]) : std::array<float, 3>{v[0], v[1], v[2]};
          p.vx += w[0] * dt, p.vy += w[1] * dt, p.vz += w[2] * dt;
          break;
        }
        case Field::Type::Attraction:
          if (dist > 1 && (radius <= 0 || dist < radius)) {
            const float k = fd.value.scalar(tn) * dt / dist;
            p.vx += dx * k, p.vy += dy * k, p.vz += dz * k;
          }
          break;
        case Field::Type::Drag:
          if (radius <= 0 || dist < radius) {
            const float k = std::exp(-fd.value.scalar(tn) * dt);
            p.vx *= k, p.vy *= k, p.vz *= k;
          }
          break;
        case Field::Type::Noise:
          if (radius <= 0 || dist < radius) {
            const float dv = fd.value.scalar(tn) * dt * std::max(0.f, fd.frequency.scalar(tn));
            p.vx += (rnd() * 2 - 1) * dv * fd.axis_fraction[0], p.vy += (rnd() * 2 - 1) * dv * fd.axis_fraction[1],
                p.vz += (rnd() * 2 - 1) * dv * fd.axis_fraction[2];
          }
          break;
        case Field::Type::Orbital:
          break;  // the orbital field's law is unknown: left out
      }
    }
    // drag: birthDrag + drag(t), per axis of the effect's space, exponential [de măsurat: the law]
    const auto dl = d_.drag.sample(tn, &p.f_drag);
    const float k[3] = {p.drag[0] + dl[0], p.drag[1] + dl[1], p.drag[2] + dl[2]};
    if (k[0] != 0 || k[1] != 0 || k[2] != 0) {
      const auto l = app_t(p.m, p.vx, p.vy, p.vz);
      const auto g = app(p.m, l[0] * std::exp(-k[0] * dt), l[1] * std::exp(-k[1] * dt), l[2] * std::exp(-k[2] * dt));
      p.vx = g[0], p.vy = g[1], p.vz = g[2];
    }
    // velocity(t): an extra velocity over the particle's life, in the effect's space [de măsurat]
    const auto vl = d_.velocity.sample(tn, &p.f_vel);
    const auto vw = app(p.m, vl[0], vl[1], vl[2]);
    p.x += (p.vx + vw[0]) * dt, p.y += (p.vy + vw[1]) * dt, p.z += (p.vz + vw[2]) * dt;
    // birthOrbitalVelocity: turns about the effect's axes through its pivot, in revolutions per second [de măsurat:
    // the unit; the bins hold 0.01-2]
    if (p.orbit[0] != 0 || p.orbit[1] != 0 || p.orbit[2] != 0) {
      float rx = p.x - p.pivot[0], ry = p.y - p.pivot[1], rz = p.z - p.pivot[2];
      for (int axis = 0; axis < 3; ++axis) {
        const float w = p.orbit[static_cast<size_t>(axis)];
        if (w == 0) continue;
        const auto wa2 = app(p.m, axis == 0 ? 1.f : 0.f, axis == 1 ? 1.f : 0.f, axis == 2 ? 1.f : 0.f);
        const auto r = app(rot_axis(wa2[0], wa2[1], wa2[2], w * 360 * dt), rx, ry, rz);
        rx = r[0], ry = r[1], rz = r[2];
      }
      p.x = p.pivot[0] + rx, p.y = p.pivot[1] + ry, p.z = p.pivot[2] + rz;
    }
    // integrated values: rotation0 (degrees per second over life), particleUVScrollRate, particleUVRotateRate and the
    // mult's ParticleIntegratedUvScrollMult add up over time [meta: Integrated* types]
    const auto rr = d_.rotation.sample(tn, &p.f_rot);
    for (size_t i = 0; i < 3; ++i) p.rot_int[i] += rr[i] * dt;
    const auto us = d_.particle_uv_scroll.curve(tn);
    p.uv_scroll_int[0] += us[0] * dt, p.uv_scroll_int[1] += us[1] * dt;
    p.uv_rot_int += d_.particle_uv_rotate_rate.scalar(tn) * dt;
    const auto mi = d_.mult.integrated_scroll.curve(tn);
    p.mult_int[0] += mi[0] * dt, p.mult_int[1] += mi[1] * dt;
    const float mx = p.x - p.px, my = p.y - p.py, mz = p.z - p.pz;
    const float ml = std::sqrt(mx * mx + my * my + mz * mz);
    if (ml > 1e-4f && dt > 0) p.dir_x = mx, p.dir_y = my, p.dir_z = mz, p.speed = ml / dt;
  }

  struct Child {
    uint32_t pid = 0;
    std::unique_ptr<VfxInstance> inst;
  };

  const VfxEmitterDef& d_;
  VfxFrame f_;
  const VfxInstance& owner_;
  std::mt19937& rng_;
  std::vector<VfxParticle> parts_;
  std::vector<Child> children_;
  std::vector<std::unique_ptr<VfxInstance>> orphans_;
  uint32_t next_id_ = 0;
  float t_ = 0, acc_ = 0, bind_ = 0, stop_t_ = 0;
  bool started_ = false, stopped_ = false, spawned_single_ = false, flat_ = false;
};

// ---------------------------------------------------------------- instances

VfxInstance::VfxInstance(const VfxSystemDef& sys, VfxFrame frame, float scale, std::array<float, 4> tint, std::mt19937& rng)
    : sys_(&sys), frame_(frame), scale_(scale), tint_(tint) {
  const auto& defs = g_vfx_swap_team_colors && !sys.swapped.empty() ? sys.swapped : sys.emitters;
  for (const VfxEmitterDef& d : defs) emitters_.push_back(std::make_unique<VfxEmitter>(d, frame_, *this, rng));
}
VfxInstance::~VfxInstance() = default;
void VfxInstance::collect(std::vector<const VfxInstance*>& out) const {
  out.push_back(this);
  for (const auto& e : emitters_) e->collect(out);
}
void VfxInstance::update(float dt) {
  for (auto& e : emitters_) e->update(dt);
}
void VfxInstance::set_frame(const VfxFrame& frame) {
  frame_ = frame;
  for (auto& e : emitters_) e->set_frame(frame);
}
void VfxInstance::stop() {
  for (auto& e : emitters_) e->stop();
}
bool VfxInstance::finished() const {
  for (const auto& e : emitters_)
    if (!e->done()) return false;
  return true;
}

std::string Vfx::describe(const std::vector<VfxInstance*>& instances) {
  std::string out;
  char line[512];
  for (const VfxInstance* inst : instances) {
    std::snprintf(line, sizeof line, "%s at %.0f %.0f %.0f x%.2f\n", inst->system().name.c_str(), inst->frame().x, inst->frame().y, inst->frame().z,
                  inst->scale());
    out += line;
    for (const auto& e : inst->emitters()) {
      const auto& ps = e->particles();
      std::snprintf(line, sizeof line, "  %-20s kind %d particles %zu", e->def().name.c_str(), static_cast<int>(e->def().kind), ps.size());
      out += line;
      if (!ps.empty()) {
        const VfxParticle& p = ps[0];
        const float tn = std::min(1.f, p.age / p.life);
        const auto s0 = e->def().scale.sample(tn, &p.f_scale);
        const auto c0 = e->def().color.sample(tn, &p.f_color);
        std::snprintf(line, sizeof line, "  first: pos %.0f %.0f %.0f size %.1f %.1f color %.2f %.2f %.2f %.2f life %.2f/%.2f", p.x, p.y, p.z,
                      p.bs[0] * s0[0], p.bs[1] * s0[1], p.bc[0] * c0[0], p.bc[1] * c0[1], p.bc[2] * c0[2], p.bc[3] * c0[3], p.age, p.life);
        out += line;
      }
      out += "\n";
    }
  }
  return out;
}

// ---------------------------------------------------------------- library

void Vfx::add_systems(const PropertyBin& bin, std::vector<const Wad*> wads) {
  for (const Wad* w : wads)
    if (std::find(wads_.begin(), wads_.end(), w) == wads_.end()) wads_.push_back(w);
  g_systems = &systems_;
  for (const BinEntry& e : bin.entries()) {
    if (e.cls != fnv1a("VfxSystemDefinitionData")) continue;
    // a system already read stays: running effects hold its emitters (a second bin naming the same entry, e.g. a skin's
    // linked bins sharing it, used to replace it under them)
    if (systems_.count(e.name)) continue;
    VfxSystemDef s;
    if (const BinValue* n = e.field("particleName")) s.name = n->str;
    s.visibility_radius = number(unwrap(e.field("visibilityRadius")), 250);
    // assetRemappingTable (VfxAssetRemap): oldAsset is the FNV-1a of a texture path, newAsset the path shown instead
    std::vector<std::pair<uint32_t, std::string>> remap;
    if (const BinValue* t = e.field("assetRemappingTable"))
      for (const BinValue& r : t->items)
        if (const BinValue* old = r.field("oldAsset")) remap.emplace_back(static_cast<uint32_t>(old->u), text(r.field("newAsset")));
    for (const char* list : {"complexEmitterDefinitionData", "simpleEmitterDefinitionData"})
      if (const BinValue* l = e.field(list))
        for (const BinValue& em : l->items) s.emitters.push_back(read_emitter(em));
    if (!remap.empty()) {
      s.swapped = s.emitters;
      for (VfxEmitterDef& d : s.swapped)
        for (const auto& [from, to] : remap)
          for (std::string* tex : {&d.texture, &d.mult.texture, &d.erosion.map})
            if (!tex->empty() && fnv1a(*tex) == from) *tex = to;
    }
    systems_[e.name] = std::move(s);
  }
}

const std::unordered_map<uint32_t, uint32_t>& Vfx::skin_effects(const Wad& wad, const std::string& character, int skin, const Wad* shared) {
  const std::string key = character + "/" + std::to_string(skin);
  auto it = resolvers_.find(key);
  if (it != resolvers_.end()) return it->second;
  auto& map = resolvers_[key];
  auto lower = [](std::string s) {
    for (char& c : s) c = static_cast<char>(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
    return s;
  };
  std::vector<const Wad*> wads{&wad};
  if (shared) wads.push_back(shared);
  const std::string skin_path = "data/characters/" + lower(character) + "/skins/skin" + std::to_string(skin) + ".bin";
  auto bytes = wad.read(skin_path);
  if (!bytes) return map;
  const PropertyBin skin_bin(*bytes);
  add_systems(skin_bin, wads);
  // the bins the skin links (the character's own bin, the shared particle bins of its skin line)
  for (const std::string& link : skin_bin.links()) {
    const std::string path = lower(link);
    if (std::find(loaded_bins_.begin(), loaded_bins_.end(), path) != loaded_bins_.end()) continue;
    loaded_bins_.push_back(path);
    if (auto b = wad.read(path)) add_systems(PropertyBin(*b), wads);
  }
  // SkinCharacterDataProperties mResourceResolver -> ResourceResolver resourceMap {key: system}
  for (const BinEntry& e : skin_bin.entries()) {
    const BinValue* link = e.field("mResourceResolver");
    if (!link) continue;
    const BinEntry* rr = skin_bin.entry(static_cast<uint32_t>(link->u));
    const BinValue* rmap = rr ? rr->field("resourceMap") : nullptr;
    if (!rmap) continue;
    for (const auto& [k, v] : rmap->pairs) map[static_cast<uint32_t>(k.u)] = static_cast<uint32_t>(v.u);
  }
  return map;
}

void Vfx::add_global(const Wad& global) {
  auto bytes = global.read("shared");
  if (!bytes) return;
  const PropertyBin bin(*bytes);
  add_systems(bin, {&global});
  for (const BinEntry& e : bin.entries()) {
    if (e.cls != fnv1a("GlobalResourceResolver")) continue;
    if (const BinValue* rmap = e.field("resourceMap"))
      for (const auto& [k, v] : rmap->pairs) global_resolver_[static_cast<uint32_t>(k.u)] = static_cast<uint32_t>(v.u);
  }
}

const VfxSystemDef* Vfx::global_effect(uint32_t key) const {
  auto it = global_resolver_.find(key);
  return it == global_resolver_.end() ? nullptr : system(it->second);
}

const VfxSystemDef* Vfx::system(uint32_t entry_hash) const {
  auto it = systems_.find(entry_hash);
  return it == systems_.end() ? nullptr : &it->second;
}

ComPtr<ID3D11ShaderResourceView> Vfx::texture(Gpu& gpu, const std::string& path) {
  if (path.empty()) return {};
  auto it = textures_.find(path);
  if (it == textures_.end()) {
    ComPtr<ID3D11ShaderResourceView> srv;
    // bins name some textures .png / .dds while the wads ship them as .tex
    std::vector<std::string> names{path};
    const size_t dot = path.find_last_of('.');
    if (dot != std::string::npos) names.push_back(path.substr(0, dot) + ".tex"), names.push_back(path.substr(0, dot) + ".dds");  // 14.1 ships .dds
    for (const std::string& name : names) {
      for (const Wad* w : wads_) {
        auto bytes = w->read(name);
        if (!bytes) continue;
        try {
          const Texture tx = read_texture(*bytes);
          // patch 14.1's .dds particle textures carry mip chains the game cannot be showing: Garen_Base_AA_slash.dds has
          // a white box in mips 1-5 (its later .tex has proper ones). Their lower levels are made from the top one
          // instead [de măsurat: what 14.1 itself did with them]
          const bool dds = bytes->size() >= 4 && (*bytes)[0] == 'D' && (*bytes)[1] == 'D' && (*bytes)[2] == 'S';
          srv = dds && tx.mips.size() > 1 ? gpu.texture_own_mips(tx) : gpu.texture(tx);
        } catch (const std::exception&) {
        }
        break;
      }
      if (srv) break;
    }
    it = textures_.emplace(path, srv).first;
  }
  return it->second;
}

const Vfx::Mesh* Vfx::mesh(const std::string& path) {
  auto it = meshes_.find(path);
  if (it == meshes_.end()) {
    std::unique_ptr<Mesh> m;
    for (const Wad* w : wads_) {
      auto bytes = w->read(path);
      if (!bytes) continue;
      try {
        m = std::make_unique<Mesh>();
        if (path.ends_with(".skn") || path.find(".skn") != std::string::npos) {
          SkinMesh sk = read_skn(*bytes);
          m->data.positions.reserve(sk.indices.size());
          m->data.uvs.reserve(sk.indices.size());
          m->data.normals.reserve(sk.indices.size());
          m->data.colors.resize(sk.indices.size(), {255, 255, 255, 255});
          for (uint16_t idx : sk.indices) {
            if (idx < sk.vertices.size()) {
              m->data.positions.push_back(sk.vertices[idx].position);
              m->data.uvs.push_back(sk.vertices[idx].uv);
              m->data.normals.push_back(sk.vertices[idx].normal);
            }
          }
        } else {
          m->data = read_scb(*bytes);
        }
        if (m && !m->data.positions.empty()) {
          float lo[3] = {1e30f, 1e30f, 1e30f}, hi[3] = {-1e30f, -1e30f, -1e30f};
          for (const auto& p : m->data.positions)
            for (int k = 0; k < 3; ++k) lo[k] = std::min(lo[k], p[k]), hi[k] = std::max(hi[k], p[k]);
          m->flat = hi[1] - lo[1] <= 0.01f * std::max(hi[0] - lo[0], hi[2] - lo[2]);
        }
      } catch (const std::exception&) {
        m.reset();
      }
      break;
    }
    it = meshes_.emplace(path, std::move(m)).first;
  }
  return it->second.get();
}

// ---------------------------------------------------------------- drawing [shader: quad_vs / quad_ps]

namespace {

struct VfxVertex {
  float pos[3];
  float uv[2];   // TEXCOORD0: the texture's uv (offset, scroll, scale, rotation, flipbook cell)
  float uv2[2];  // TEXCOORD1: the mult texture's uv when there is one, else where the colour ramp is read
  float color[4];
  float rim[3];  // mesh_vs's Fresnel colour (0 for quads)
  float erosion; // TEXCOORD3.z of Riot's particle vertex shaders: the particle's erosion value
  float uv3[2];  // SEPARATE_ALPHA_UV: the texture's uv without its scroll (mesh_vs: uv through the 2x2 part of
                 // vParticleUVTransform only), where the alpha is read when the emitter's uvMode is 2
};

const char* kShader = R"(
cbuffer Frame : register(b0) { row_major float4x4 view_proj; };
cbuffer Draw : register(b1) {
  float4 alpha_ref;    // x: alphaRef / 255 (ALPHA_TEST); y: 1 erosion, 2 soft, 4 navmesh mask, 8 ONE-ONE blend, 16 separate alpha uv (bits)
  float4 ero;          // cAlphaErosionParams: y slice width, z 1 / feather in, w 1 / feather out
  float4 ero_mix;      // cAlphaErosionTextureMixer
  float4 soft;         // cSoftParticleParams: begin in, begin out, 1 / delta in, 1 / delta out
  float4 depth_conv;   // cDepthConversionParams: distance = 1 / (z * y + x)
  float4 nav;          // NAV_GRID_XFORM: navmesh uv = xy * world xz + zw
};
Texture2D tex : register(t0);
Texture2D mult : register(t1);
Texture2D color_tex : register(t2);
Texture2D ero_tex : register(t3);
Texture2D depth_tex : register(t4);
Texture2D nav_tex : register(t5);
SamplerState samp : register(s0);
SamplerState clamp_samp : register(s1);
struct VSIn { float3 pos : POSITION; float2 uv : TEXCOORD0; float2 uv2 : TEXCOORD1; float4 color : COLOR0; float3 rim : COLOR1; float erosion : TEXCOORD2;
              float2 uv3 : TEXCOORD4; };
struct PSIn { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; float2 uv2 : TEXCOORD1; float4 color : COLOR0; float3 rim : COLOR1;
              float erosion : TEXCOORD2; float2 nav_uv : TEXCOORD3; float2 uv3 : TEXCOORD4; };
PSIn vs_main(VSIn v) {
  PSIn o;
  o.pos = mul(float4(v.pos, 1), view_proj);
  o.uv = v.uv;
  o.uv2 = v.uv2;
  o.color = v.color;
  o.rim = v.rim;
  o.erosion = v.erosion;
  o.uv3 = v.uv3;
  o.nav_uv = nav.xy * v.pos.xz + nav.zw;
  return o;
}
// quad_ps / mesh_ps: TEXTURE * TEXTUREMULT * PARTICLE_COLOR_TEXTURE * colour; ALPHA_TEST drops colour.a * texture.a < ref;
// mesh_ps then adds the Fresnel rim weighted by alpha: rgb = saturate(rgb + rim * a)
float4 ps_main(PSIn p) : SV_TARGET {
  uint flags = (uint)alpha_ref.y;
  float4 t = tex.Sample(samp, p.uv);
  if (flags & 16) t.a = tex.Sample(samp, p.uv3).a;  // mesh_ps SEPARATE_ALPHA_UV: alpha from the unscrolled uv
  t *= mult.Sample(samp, p.uv2);
  t *= color_tex.Sample(clamp_samp, p.uv2);
  // flag 8: the plain additive blend (ONE, ONE). The colour's alpha takes no part: the game sends alpha 1 in every
  // vertex of these draws
  float va = (flags & 8) ? 1 : p.color.a;
  clip(va * t.a - alpha_ref.x);
  float4 c = t * float4(p.color.rgb, va);
  c.rgb = saturate(c.rgb + p.rim * c.a);
  float a0 = c.a;
  if (flags & 1) {
    // ALPHA_EROSION: the erosion map read with the texture's uv, through the channel mixer; alpha keeps the band
    // between the particle's erosion value and that value plus the slice width, feathered on both sides
    float e = saturate(dot(ero_tex.Sample(samp, p.uv), ero_mix));
    float2 r = saturate((p.erosion.xx - float2(e - ero.y, e)) * ero.zw);
    c.a *= r.x - r.y;
  }
  if (flags & 2) {
    // SOFT_PARTICLES: fades by the distance between the particle and the scene behind it (two smoothsteps)
    float scene = 1 / (depth_tex.Load(int3(p.pos.xy, 0)).r * depth_conv.y + depth_conv.x);
    float self = 1 / (p.pos.z * depth_conv.y + depth_conv.x);
    float2 s = saturate((scene - self - soft.xy) * soft.zw);
    s = s * s * (3 - 2 * s);
    if (flags & 8) c.a *= s.x - s.y; else c *= s.x - s.y;
  }
  if (flags & 4) c.a = min(c.a, nav_tex.Sample(clamp_samp, p.nav_uv).r);  // NAVMESH_MASK_TEXTURE
  // ONE, ONE: what erosion, soft edges and the navmesh mask took from alpha is taken from the colour instead (alpha
  // itself is not read by the blend) [dedus: the plain permutation is the measured one]
  if (flags & 8) return float4(c.rgb * (a0 > 1e-5 ? c.a / a0 : 0), 1);
  return c;
}
)";

struct DrawCall {
  uint32_t first = 0, count = 0;
  ComPtr<ID3D11ShaderResourceView> tex, mult, color, erosion;
  enum class Blend { Add, Alpha, Opaque, AddOne } blend = Blend::Add;
  bool depth = true, cull = false, ground = false;
  float alpha_ref = 0;
  int pass = 0;
  uint32_t flags = 0;  // 1 erosion, 2 soft, 4 navmesh mask
  std::array<float, 4> ero{}, ero_mix{}, soft{};
};

}  // namespace

bool Vfx::init(Gpu& gpu) {
  ComPtr<ID3DBlob> code;
  if (!gpu.shader(kShader, "vfx", vs_, ps_, &code)) return false;
  const D3D11_INPUT_ELEMENT_DESC il[] = {
      {"POSITION", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 0, D3D11_INPUT_PER_VERTEX_DATA, 0},
      {"TEXCOORD", 0, DXGI_FORMAT_R32G32_FLOAT, 0, 12, D3D11_INPUT_PER_VERTEX_DATA, 0},
      {"TEXCOORD", 1, DXGI_FORMAT_R32G32_FLOAT, 0, 20, D3D11_INPUT_PER_VERTEX_DATA, 0},
      {"COLOR", 0, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 28, D3D11_INPUT_PER_VERTEX_DATA, 0},
      {"COLOR", 1, DXGI_FORMAT_R32G32B32_FLOAT, 0, 44, D3D11_INPUT_PER_VERTEX_DATA, 0},
      {"TEXCOORD", 2, DXGI_FORMAT_R32_FLOAT, 0, 56, D3D11_INPUT_PER_VERTEX_DATA, 0},
      {"TEXCOORD", 4, DXGI_FORMAT_R32G32_FLOAT, 0, 60, D3D11_INPUT_PER_VERTEX_DATA, 0},
  };
  if (FAILED(gpu.device()->CreateInputLayout(il, 7, code->GetBufferPointer(), code->GetBufferSize(), &layout_))) return false;
  D3D11_BUFFER_DESC cbd{};
  cbd.Usage = D3D11_USAGE_DYNAMIC;
  cbd.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
  cbd.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
  cbd.ByteWidth = 64;
  gpu.device()->CreateBuffer(&cbd, nullptr, &frame_cb_);
  cbd.ByteWidth = 96;
  gpu.device()->CreateBuffer(&cbd, nullptr, &draw_cb_);
  D3D11_BLEND_DESC bl{};
  bl.RenderTarget[0].BlendEnable = TRUE;
  bl.RenderTarget[0].SrcBlend = D3D11_BLEND_SRC_ALPHA;
  bl.RenderTarget[0].DestBlend = D3D11_BLEND_ONE;
  bl.RenderTarget[0].BlendOp = D3D11_BLEND_OP_ADD;
  bl.RenderTarget[0].SrcBlendAlpha = D3D11_BLEND_ZERO;
  bl.RenderTarget[0].DestBlendAlpha = D3D11_BLEND_ONE;
  bl.RenderTarget[0].BlendOpAlpha = D3D11_BLEND_OP_ADD;
  bl.RenderTarget[0].RenderTargetWriteMask = D3D11_COLOR_WRITE_ENABLE_ALL;
  gpu.device()->CreateBlendState(&bl, &additive_);
  bl.RenderTarget[0].DestBlend = D3D11_BLEND_INV_SRC_ALPHA;
  gpu.device()->CreateBlendState(&bl, &alpha_);
  bl.RenderTarget[0].SrcBlend = D3D11_BLEND_ONE;
  bl.RenderTarget[0].DestBlend = D3D11_BLEND_ONE;
  gpu.device()->CreateBlendState(&bl, &add_one_);
  D3D11_DEPTH_STENCIL_DESC ds{};
  ds.DepthEnable = TRUE;
  ds.DepthWriteMask = D3D11_DEPTH_WRITE_MASK_ZERO;
  ds.DepthFunc = D3D11_COMPARISON_LESS_EQUAL;
  gpu.device()->CreateDepthStencilState(&ds, &depth_test_);
  ds.DepthWriteMask = D3D11_DEPTH_WRITE_MASK_ALL;
  gpu.device()->CreateDepthStencilState(&ds, &depth_write_);
  ds.DepthWriteMask = D3D11_DEPTH_WRITE_MASK_ZERO;
  ds.DepthEnable = FALSE;
  gpu.device()->CreateDepthStencilState(&ds, &depth_off_);
  D3D11_RASTERIZER_DESC rs{};
  rs.FillMode = D3D11_FILL_SOLID;
  rs.CullMode = D3D11_CULL_NONE;
  rs.DepthClipEnable = TRUE;
  gpu.device()->CreateRasterizerState(&rs, &cull_none_);
  rs.CullMode = D3D11_CULL_BACK;
  gpu.device()->CreateRasterizerState(&rs, &cull_back_);
  // ground decals: pulled in front of the ground they lie on [alegere proprie; League's way is not in its shaders]
  rs.CullMode = D3D11_CULL_NONE;
  rs.DepthBias = -2000;
  rs.SlopeScaledDepthBias = -2.f;
  gpu.device()->CreateRasterizerState(&rs, &ground_bias_);
  D3D11_SAMPLER_DESC smp{};
  smp.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;
  smp.AddressU = smp.AddressV = smp.AddressW = D3D11_TEXTURE_ADDRESS_WRAP;
  smp.MaxLOD = D3D11_FLOAT32_MAX;
  gpu.device()->CreateSamplerState(&smp, &sampler_);
  smp.AddressU = smp.AddressV = smp.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
  gpu.device()->CreateSamplerState(&smp, &clamp_);
  Texture white;
  white.format = TexFormat::BGRA8;
  white.width = white.height = 1;
  white.mips = {{255, 255, 255, 255}};
  white_ = gpu.texture(white);
  return true;
}

void Vfx::draw(Gpu& gpu, const float4x4& view_proj, const float4x4& view, float3 eye, const std::vector<VfxInstance*>& instances,
               bool ground_pass) {
  using Kind = VfxEmitterDef::Kind;
  std::vector<VfxVertex> verts;
  std::vector<DrawCall> calls;
  // the camera's axes in the world (row-vector view matrix: its columns)
  const float3 right{view.m[0][0], view.m[1][0], view.m[2][0]};
  const float3 up{view.m[0][1], view.m[1][1], view.m[2][1]};

  std::vector<const VfxInstance*> all;
  for (const VfxInstance* inst : instances) inst->collect(all);
  bool any_soft = false;
  for (const VfxInstance* inst : all) {
    const VfxFrame& f = inst->frame();
    const float S = inst->scale();
    const auto& tint = inst->tint();
    for (const auto& em : inst->emitters()) {
      const VfxEmitterDef& d = em->def();
      if (d.kind == Kind::None || em->particles().empty()) continue;
      const Mesh* mesh_data = d.kind == Kind::Mesh ? mesh(d.mesh) : nullptr;
      if (d.kind == Kind::Mesh && !mesh_data) continue;
      // a mesh lying flat on the ground (the Baron pit's river streaks) is drawn with the ground's decals: drawn
      // level with the ground, its depth fought the ground's and it flickered in bands as the camera moved
      const bool on_ground = em->flat() || (mesh_data && mesh_data->flat);
      if (on_ground != ground_pass) continue;
      DrawCall call;
      call.ground = on_ground;
      call.tex = texture(gpu, d.texture);
      if (!call.tex) call.tex = white_;
      // blend modes [măsurat: the blend state of 98 particle draws of two 13.3 replay frames, each matched by its
      // texture to the map's emitter]: none given -> ONE, ONE; 1 -> SRC_ALPHA, INV_SRC_ALPHA; 3 -> no blending, depth
      // written; 4 -> SRC_ALPHA, ONE. In the ONE, ONE draws every vertex carries alpha 255 and the colour's own alpha
      // is not folded into rgb (an emitter with birthColor [1, 1, 1, 0.8] sends 255, 255, 255, 255): the colour's
      // alpha does nothing there. Other values (2, 5) were not seen: left adding by alpha [de măsurat]
      call.blend = d.blend_mode == 1   ? DrawCall::Blend::Alpha
                   : d.blend_mode == 3 ? DrawCall::Blend::Opaque
                   : d.blend_mode == 0 ? DrawCall::Blend::AddOne
                                       : DrawCall::Blend::Add;
      if (call.blend == DrawCall::Blend::AddOne) call.flags |= 8;
      if (d.uv_mode == 2) call.flags |= 16;
      call.depth = d.pass < 500;  // [de măsurat]
      call.cull = d.kind == Kind::Mesh && !d.backface;
      if (std::getenv("BA_VFX_NOCULL")) call.cull = false;  // diagnostic
      if (std::getenv("BA_VFX_NODEPTH")) call.depth = false;  // diagnostic
      if (static const char* only = std::getenv("BA_VFX_ONLY"); only && inst->system().name.find(only) == std::string::npos) continue;  // diagnostic
      call.pass = d.pass;
      call.alpha_ref = static_cast<float>(d.alpha_ref) / 255.f;
      call.mult = d.mult.texture.empty() ? white_ : texture(gpu, d.mult.texture);
      call.color = texture(gpu, d.color_texture);
      if (!call.mult) call.mult = white_;
      if (!call.color) call.color = white_;
      const bool has_mult = !d.mult.texture.empty();
      if (d.erosion.on) {
        // cAlphaErosionParams / Mixer [dedus: the engine fills them; y = erosionSliceWidth, z and w = 1 / the feathers]
        call.erosion = texture(gpu, d.erosion.map);
        if (call.erosion) {
          call.flags |= 1;
          call.ero = {0, d.erosion.slice_width, 1.f / std::max(1e-4f, d.erosion.feather_in), 1.f / std::max(1e-4f, d.erosion.feather_out)};
          call.ero_mix = d.erosion.mixer;
        }
      }
      if (d.soft.on) {
        // cSoftParticleParams [dedus]: (beginIn, beginOut, 1 / deltaIn, 1 / deltaOut); a missing fade-out (both 0) adds
        // nothing, a fade-in without a width is a hard step [de măsurat]
        call.flags |= 2, any_soft = true;
        const bool out = d.soft.begin_out != 0 || d.soft.delta_out != 0;
        call.soft = {d.soft.begin_in, out ? d.soft.begin_out : 0.f, d.soft.delta_in > 0 ? 1.f / d.soft.delta_in : 1e6f,
                     !out ? 0.f : d.soft.delta_out > 0 ? 1.f / d.soft.delta_out : 1e6f};
      }
      if (d.navmesh_mask && navmask_) call.flags |= 4;
      call.first = static_cast<uint32_t>(verts.size());

      const float bw = em->bind();
      const M3 F = d.local_orientation ? f.m : kI3;
      const bool grid = d.tex_div[0] * d.tex_div[1] > 1;
      const auto uvs = d.uv_scale.curve(0);
      const auto mult_scale = d.mult.uv_scale.curve(0);
      const float mult_rot = d.mult.uv_rotation.scalar(0) * kD2R;
      // a trail is one ribbon through its particles in birth order (each particle is a point of it, left where it was
      // born); u runs along the ribbon from the newest point, one repeat per mTrail mBirthTilingSize.x world units, or
      // once over the whole ribbon without one [de măsurat: u's direction and origin, mCutoff, mMode]
      struct TrailPoint {
        float3 pos, side;
        float color[4];
        float u = 0;
      };
      std::vector<TrailPoint> trail;
      float trail_len = 0;
      if (d.kind == Kind::Trail) {
        const auto& ps = em->particles();
        float3 last{};
        for (size_t i = 0; i < ps.size(); ++i) {
          const VfxParticle& p = ps[i];
          const float3 g{f.x * bw + p.ox * (1 - bw) + p.x * S, f.y * bw + p.oy * (1 - bw) + p.y * S, f.z * bw + p.oz * (1 - bw) + p.z * S};
          if (i) trail_len += std::sqrt(dot(g - last, g - last));
          last = g;
        }
      }
      float trail_walked = 0;
      float3 trail_last{};
      for (const VfxParticle& p : em->particles()) {
        const float tn = std::min(1.f, p.age / p.life);
        float gx = f.x * bw + p.ox * (1 - bw) + p.x * S;
        float gy = f.y * bw + p.oy * (1 - bw) + p.y * S;
        float gz = f.z * bw + p.oz * (1 - bw) + p.z * S;
        const auto s0 = d.scale.sample(tn, &p.f_scale);
        float sx = p.bs[0] * s0[0], sy = p.bs[1] * s0[1], sz = p.bs[2] * s0[2];
        if (d.uniform) sy = sx, sz = sx;
        const auto c0 = d.color.sample(tn, &p.f_color);
        // the erosion value: erosionDriveCurve over the particle's life (0 whole, 1 gone), stretched by the fade-out
        // feather so 0 leaves every texel and 1 none [dedus: the engine's mapping is not in its shaders]
        const float erosion_value = d.erosion.on ? d.erosion.drive.scalar(tn) * (1.f + d.erosion.feather_out) : 0.f;
        // birthColor * Color(t) * the placement's colorModulate, sent as 8-bit colour [shader: COLOR0.zyxw]
        float col[4];
        for (size_t k = 0; k < 4; ++k) col[k] = std::clamp(p.bc[k] * c0[k] * tint[k], 0.f, 1.f);
        // rotation: birth + velocity * age + acceleration * age^2 / 2 + integrated rotation0 [meta names; de măsurat]
        float rot[3];
        for (size_t k = 0; k < 3; ++k) rot[k] = p.rot0[k] + p.rv[k] * p.age + 0.5f * p.ra[k] * p.age * p.age + p.rot_int[k];
        const float rx = rot[0], ry = rot[1], rz = rot[2];
        // flipbook: frameRate if set, else birthFrameRate (default 1) [meta defaults]
        const float fps = d.frame_rate > 0 ? d.frame_rate : d.birth_frame_rate.scalar(0);
        const int frame = d.num_frames > 1 ? (p.frame0 + static_cast<int>(p.age * fps)) % d.num_frames : 0;
        // the colour ramp is read along each axis by colorLookUpType [dedus din date: research/lookup_stats.py]:
        //   1 (X's default) the particle's life: looping emitters use it with fade curves (color-bellcurve,
        //     Fade_in_fade_out) that only make sense per particle
        //   3 random per particle: SparksRandomRamp / FlickerColor textures, half-texture picks through the scales
        //   0 (Y's default) none: the ramps are one row high
        //   2 the emitter's life [de măsurat: unused on the map]
        auto lookup = [&](int axis) {
          const int type = d.lookup_type[axis];
          const float v = type == 1 ? tn : type == 3 ? p.seed : type == 2 ? std::min(1.f, d.has_lifetime && d.lifetime > 0 ? em->age() / d.lifetime : 0.f) : 0.f;
          return v * d.lookup_scale[axis] + d.lookup_offset[axis];
        };
        const float look[2] = {lookup(0), lookup(1)};
        const float uv_rot = (d.uv_rotation.scalar(tn) + p.uv_rot_rate * p.age + p.uv_rot_int) * kD2R;
        const float scroll_x = p.uv_off[0] + p.uv_scroll[0] * p.age + p.uv_scroll_int[0];
        const float scroll_y = p.uv_off[1] + p.uv_scroll[1] * p.age + p.uv_scroll_int[1];
        const float mscroll_x = p.mult_off[0] + p.mult_scroll[0] * p.age + p.mult_int[0];
        const float mscroll_y = p.mult_off[1] + p.mult_scroll[1] * p.age + p.mult_int[1];

        auto uv_of = [&](float u0, float v0, float out[2], float out2[2], float out3[2]) {
          float u = d.flip_u ? 1 - u0 : u0, v = d.flip_v ? 1 - v0 : v0;
          if (std::fabs(uv_rot) > 1e-5f) {  // about uvTransformCenter [meta name]
            const float cr = std::cos(uv_rot), sr = std::sin(uv_rot), du = u - d.uv_center[0], dv = v - d.uv_center[1];
            u = cr * du - sr * dv + d.uv_center[0], v = sr * du + cr * dv + d.uv_center[1];
          }
          float tu = u * uvs[0] + scroll_x, tv = v * uvs[1] + scroll_y;
          out3[0] = u * uvs[0], out3[1] = v * uvs[1];
          if (grid) {
            // quad_vs: row = floor(frame / columns), column = frame - row * columns; uv = (uv + cell) / (columns, rows)
            const float row = std::floor(static_cast<float>(frame) / d.tex_div[0]), colm = static_cast<float>(frame) - row * d.tex_div[0];
            tu = (tu + colm) / d.tex_div[0], tv = (tv + row) / d.tex_div[1];
          }
          out[0] = tu, out[1] = tv;
          if (has_mult) {
            float mu = d.mult.flip_u ? 1 - u0 : u0, mv = d.mult.flip_v ? 1 - v0 : v0;
            if (std::fabs(mult_rot) > 1e-5f) {
              const float cr = std::cos(mult_rot), sr = std::sin(mult_rot), du = mu - d.mult.center[0], dv = mv - d.mult.center[1];
              mu = cr * du - sr * dv + d.mult.center[0], mv = sr * du + cr * dv + d.mult.center[1];
            }
            out2[0] = mu * mult_scale[0] + mscroll_x, out2[1] = mv * mult_scale[1] + mscroll_y;
          } else {
            out2[0] = look[0], out2[1] = look[1];
          }
        };
        auto vertex = [&](float x, float y, float z, float u0, float v0, const float* vtint = nullptr, const Vec3* normal = nullptr) {
          VfxVertex vv;
          vv.rim[0] = vv.rim[1] = vv.rim[2] = 0;
          vv.erosion = erosion_value;
          if (normal && (d.fresnel_color[0] != 0 || d.fresnel_color[1] != 0 || d.fresnel_color[2] != 0)) {
            // mesh_vs: rim = fresnelColor.rgb * (1 - saturate(dot(towards the camera, normal)) ^ fresnel)
            const float3 to_eye = normalize(eye - float3{x, y, z});
            const float facing = std::clamp(to_eye.x * (*normal)[0] + to_eye.y * (*normal)[1] + to_eye.z * (*normal)[2], 0.f, 1.f);
            const float k = 1.f - std::pow(facing, d.fresnel);
            for (int c = 0; c < 3; ++c) vv.rim[c] = d.fresnel_color[static_cast<size_t>(c)] * k;
          }
          if (d.depth_push_pull != 0) {
            // [shader: quad_vs] PARTICLE_DEPTH_PUSH_PULL (DepthPushPull): along the line from the camera
            const float3 dir = normalize(float3{x, y, z} - eye);
            x += dir.x * d.depth_push_pull, y += dir.y * d.depth_push_pull, z += dir.z * d.depth_push_pull;
          }
          vv.pos[0] = x, vv.pos[1] = y, vv.pos[2] = z;
          uv_of(u0, v0, vv.uv, vv.uv2, vv.uv3);
          for (int k = 0; k < 4; ++k) vv.color[k] = col[k] * (vtint ? vtint[k] : 1.f);
          verts.push_back(vv);
        };
        auto quad = [&](float3 c, float3 ax, float3 ay) {
          const float3 p00 = c - ax * 0.5f + ay * 0.5f, p10 = c + ax * 0.5f + ay * 0.5f;
          const float3 p01 = c - ax * 0.5f - ay * 0.5f, p11 = c + ax * 0.5f - ay * 0.5f;
          vertex(p00.x, p00.y, p00.z, 0, 0), vertex(p01.x, p01.y, p01.z, 0, 1), vertex(p10.x, p10.y, p10.z, 1, 0);
          vertex(p10.x, p10.y, p10.z, 1, 0), vertex(p01.x, p01.y, p01.z, 0, 1), vertex(p11.x, p11.y, p11.z, 1, 1);
        };
        auto mat_quad = [&](const M3& R, float w, float h) {
          const auto ax = app(R, w, 0, 0), ay = app(R, 0, h, 0);
          quad({gx, gy, gz}, {ax[0], ax[1], ax[2]}, {ay[0], ay[1], ay[2]});
        };

        // orientation per kind [de măsurat: our reading; the billboard roll is rotation.x, which the bins spin most]
        switch (d.kind) {
          case Kind::Billboard: {
            const float roll = rx * kD2R, c = std::cos(roll), s = std::sin(roll);
            quad({gx, gy, gz}, (right * c + up * s) * (std::fabs(sx) * S), (right * -s + up * c) * (std::fabs(sy) * S));
            break;
          }
          case Kind::Dir:
          case Kind::Ray: {
            float3 dir;
            float len;
            if (d.kind == Kind::Ray) {
              const M3 r = mul(F, euler(rx, ry, rz));
              dir = {r[2], r[5], r[8]};
              len = std::fabs(sy) * S;
              gx += dir.x * len / 2, gy += dir.y * len / 2, gz += dir.z * len / 2;
            } else {
              dir = normalize({p.dir_x, p.dir_y, p.dir_z});
              // directionVelocityScale / directionVelocityMinScale: the quad lengthens with speed [de măsurat: the law]
              const float stretch = d.direction_velocity_scale != 0 ? std::max(d.direction_velocity_min_scale, p.speed * d.direction_velocity_scale) : 1.f;
              len = std::fabs(sx) * stretch * S;
            }
            const float3 to_cam = normalize(eye - float3{gx, gy, gz});
            float3 side = cross(dir, to_cam);
            side = dot(side, side) > 1e-8f ? normalize(side) : float3{0, 1, 0};
            quad({gx, gy, gz}, dir * len, side * ((d.kind == Kind::Ray ? std::fabs(sx) : std::fabs(sy)) * S));
            break;
          }
          case Kind::DirGround: {
            const float3 dir = normalize({p.dir_x, 0.0001f, p.dir_z});
            const float3 side = normalize(cross(dir, {0, 1, 0}));
            quad({gx, gy, gz}, dir * (std::fabs(sx) * S), side * (std::fabs(sy) * S));
            break;
          }
          case Kind::Fixed:
            mat_quad(mul(F, euler(rx, ry, rz)), std::fabs(sx) * S, std::fabs(sy) * S);
            break;
          case Kind::Ground:
            mat_quad(mul(mul(yaw_only(F), rot_axis(1, 0, 0, 90)), rot_axis(0, 0, 1, rx)), std::fabs(sx) * S, std::fabs(sy) * S);
            break;
          case Kind::Mesh: {
            M3 R;
            if (d.direction_oriented && p.speed > 1) {
              const float3 to = normalize({p.dir_x, p.dir_y, p.dir_z});
              const float3 axis = cross({0, 0, 1}, to);
              const float al = std::sqrt(dot(axis, axis));
              R = al > 1e-6f ? rot_axis(axis.x, axis.y, axis.z, std::atan2(al, to.z) / kD2R) : (to.z < 0 ? rot_axis(0, 1, 0, 180) : kI3);
            } else {
              R = mul(F, euler(rx, ry, rz));
            }
            const StaticMesh& md = mesh_data->data;
            for (size_t i = 0; i < md.positions.size(); ++i) {
              const auto& v = md.positions[i];
              const auto w = app(R, v[0] * sx * S, v[1] * sy * S, v[2] * sz * S);
              const float vt[4] = {md.colors[i][0] / 255.f, md.colors[i][1] / 255.f, md.colors[i][2] / 255.f, md.colors[i][3] / 255.f};
              const auto wn = app(R, md.normals[i][0], md.normals[i][1], md.normals[i][2]);
              const Vec3 n{wn[0], wn[1], wn[2]};
              vertex(gx + w[0], gy + w[1], gz + w[2], md.uvs[i][0], md.uvs[i][1], vt, &n);
            }
            break;
          }
          case Kind::Beam: {
            // a strip from the effect's place to its target, each end moved by its offset in the beam's own axes (z along
            // the beam), as wide as the particle's scale x, turned to the camera
            // [de măsurat: the texture's v runs along the beam; mBirthTilingSize, mSegments and the beam's modes unread]
            if (!inst->has_target()) break;
            const float3 a0{f.x, f.y, f.z}, b0 = inst->target();
            float3 along = b0 - a0;
            const float span = std::sqrt(dot(along, along));
            if (span < 1.f) break;
            along = along * (1.f / span);
            float3 across = cross({0, 1, 0}, along);
            across = dot(across, across) > 1e-8f ? normalize(across) : float3{1, 0, 0};
            const float3 over = cross(along, across);
            const auto moved = [&](float3 at, const std::array<float, 3>& o) { return at + across * (o[0] * S) + over * (o[1] * S) + along * (o[2] * S); };
            const float3 a = moved(a0, d.beam_source), b = moved(b0, d.beam_target);
            const float3 seg = b - a, mid = (a + b) * 0.5f;
            const float seg_len = std::sqrt(dot(seg, seg));
            if (seg_len < 1.f) break;
            float3 side = cross(seg * (1.f / seg_len), normalize(eye - mid));
            side = dot(side, side) > 1e-8f ? normalize(side) : float3{0, 1, 0};
            quad(mid, side * (std::fabs(sx) * S), seg);
            break;
          }
          case Kind::Trail: {
            TrailPoint tp;
            tp.pos = {gx, gy, gz};
            if (!trail.empty()) trail_walked += std::sqrt(dot(tp.pos - trail_last, tp.pos - trail_last));
            trail_last = tp.pos;
            const float from_head = trail_len - trail_walked;
            tp.u = d.trail_tiling > 0 ? from_head / d.trail_tiling : (trail_len > 0 ? from_head / trail_len : 0.f);
            const float width = std::fabs(sx) * S;
            if (d.trail_camera) {
              tp.side = {width * 0.5f, 0, 0};  // half width, turned to face the camera per segment below
            } else {
              const auto ax = app(mul(p.m, euler(rx, ry, rz)), 1, 0, 0);
              tp.side = float3{ax[0], ax[1], ax[2]} * (width * 0.5f);
            }
            for (size_t k = 0; k < 4; ++k) tp.color[k] = col[k];
            // the ribbon's segment from the previous point to this one, as two triangles
            if (!trail.empty()) {
              TrailPoint a = trail.back(), b = tp;
              const float3 seg = b.pos - a.pos;
              const float seg_len = std::sqrt(dot(seg, seg));
              if (d.trail_cutoff <= 0 || seg_len <= d.trail_cutoff) {
                if (d.trail_camera && seg_len > 1e-4f) {
                  const float3 to_cam = normalize(eye - b.pos);
                  float3 s = cross(seg * (1.f / seg_len), to_cam);
                  s = dot(s, s) > 1e-8f ? normalize(s) : float3{0, 1, 0};
                  a.side = s * a.side.x, b.side = s * b.side.x;
                }
                auto emit = [&](const TrailPoint& t, float v0) {
                  const float3 q = t.pos + t.side * (v0 * 2 - 1);
                  const float saved[4] = {col[0], col[1], col[2], col[3]};
                  for (size_t k = 0; k < 4; ++k) col[k] = t.color[k];
                  vertex(q.x, q.y, q.z, t.u, v0);
                  for (size_t k = 0; k < 4; ++k) col[k] = saved[k];
                };
                emit(a, 0), emit(a, 1), emit(b, 0);
                emit(b, 0), emit(a, 1), emit(b, 1);
              }
            }
            trail.push_back(tp);
            break;
          }
          default:
            break;
        }
      }
      call.count = static_cast<uint32_t>(verts.size()) - call.first;
      if (call.count) calls.push_back(call);
      // BA_VFX_DUMP=<file> (checks): every draw of the last frame with what the GPU gets, to set against the draws of
      // the real client (tools/sponge)
      if (static const char* dump = std::getenv("BA_VFX_DUMP"); dump && call.count) {
        if (FILE* f = std::fopen(dump, ground_pass && calls.size() == 1 ? "w" : "a")) {
          std::fprintf(f, "%s / %s: %u vertices, blend %d, flags %u, cull %d, depth %d, pass %d, alpha ref %.4f, blendMode %d uvMode %d, texture %s\n",
                       inst->system().name.c_str(), d.name.c_str(), call.count, static_cast<int>(call.blend), call.flags, call.cull ? 1 : 0, call.depth ? 1 : 0,
                       call.pass, call.alpha_ref, d.blend_mode, d.uv_mode, d.texture.c_str());
          for (uint32_t k = 0; k < std::min<uint32_t>(call.count, 3); ++k) {
            const VfxVertex& v = verts[call.first + k];
            std::fprintf(f, "   pos %.1f %.1f %.1f  uv %.3f %.3f  uv2 %.3f %.3f  uv3 %.3f %.3f  color %.3f %.3f %.3f %.3f\n", v.pos[0], v.pos[1], v.pos[2], v.uv[0],
                         v.uv[1], v.uv2[0], v.uv2[1], v.uv3[0], v.uv3[1], v.color[0], v.color[1], v.color[2], v.color[3]);
          }
          std::fclose(f);
        }
      }
    }
  }
  if (verts.empty()) return;

  if (verts.size() > vb_capacity_) {
    vb_capacity_ = std::max<size_t>(verts.size() * 2, 65536);
    D3D11_BUFFER_DESC bd{};
    bd.Usage = D3D11_USAGE_DYNAMIC;
    bd.BindFlags = D3D11_BIND_VERTEX_BUFFER;
    bd.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
    bd.ByteWidth = static_cast<UINT>(vb_capacity_ * sizeof(VfxVertex));
    vb_.Reset();
    if (FAILED(gpu.device()->CreateBuffer(&bd, nullptr, &vb_))) return;
  }
  ID3D11DeviceContext* ctx = gpu.ctx();
  D3D11_MAPPED_SUBRESOURCE map{};
  if (FAILED(ctx->Map(vb_.Get(), 0, D3D11_MAP_WRITE_DISCARD, 0, &map))) return;
  std::memcpy(map.pData, verts.data(), verts.size() * sizeof(VfxVertex));
  ctx->Unmap(vb_.Get(), 0);
  if (SUCCEEDED(ctx->Map(frame_cb_.Get(), 0, D3D11_MAP_WRITE_DISCARD, 0, &map))) {
    std::memcpy(map.pData, view_proj.m, 64);
    ctx->Unmap(frame_cb_.Get(), 0);
  }
  // League's pass order, lower first [meta: pass]
  std::stable_sort(calls.begin(), calls.end(), [](const DrawCall& a, const DrawCall& b) { return a.pass < b.pass; });
  const UINT stride = sizeof(VfxVertex), offset = 0;
  ctx->IASetInputLayout(layout_.Get());
  ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
  ctx->IASetVertexBuffers(0, 1, vb_.GetAddressOf(), &stride, &offset);
  ctx->VSSetShader(vs_.Get(), nullptr, 0);
  ctx->PSSetShader(ps_.Get(), nullptr, 0);
  ctx->VSSetConstantBuffers(0, 1, frame_cb_.GetAddressOf());
  ctx->PSSetConstantBuffers(1, 1, draw_cb_.GetAddressOf());
  ctx->VSSetConstantBuffers(1, 1, draw_cb_.GetAddressOf());  // the vertex shader reads NAV_GRID_XFORM from it
  ID3D11SamplerState* samplers[2] = {sampler_.Get(), clamp_.Get()};
  ctx->PSSetSamplers(0, 2, samplers);
  // the scene's depth so far, for soft particles (a copy: the depth buffer itself stays bound for testing)
  ID3D11ShaderResourceView* depth = any_soft ? gpu.depth_snapshot() : nullptr;
  // cDepthConversionParams for our projection (perspective_lh): 1 / distance = 1 / near - z * (far - near) / (near * far)
  const float conv[4] = {1.f / near_, -(far_ - near_) / (near_ * far_), 0, 0};
  for (const DrawCall& c : calls) {
    if (SUCCEEDED(ctx->Map(draw_cb_.Get(), 0, D3D11_MAP_WRITE_DISCARD, 0, &map))) {
      const uint32_t flags = c.flags & (depth ? 7u : 5u);
      float cb[24] = {c.alpha_ref, static_cast<float>(flags), 0, 0};
      std::memcpy(cb + 4, c.ero.data(), 16);
      std::memcpy(cb + 8, c.ero_mix.data(), 16);
      std::memcpy(cb + 12, c.soft.data(), 16);
      std::memcpy(cb + 16, conv, 16);
      std::memcpy(cb + 20, nav_xform_.data(), 16);
      std::memcpy(map.pData, cb, sizeof cb);
      ctx->Unmap(draw_cb_.Get(), 0);
    }
    ID3D11ShaderResourceView* srvs[6] = {c.tex.Get(), c.mult.Get(), c.color.Get(), c.erosion ? c.erosion.Get() : white_.Get(), depth,
                                         navmask_ ? navmask_.Get() : white_.Get()};
    ctx->PSSetShaderResources(0, 6, srvs);
    ctx->OMSetBlendState(c.blend == DrawCall::Blend::Opaque   ? nullptr
                         : c.blend == DrawCall::Blend::Alpha  ? alpha_.Get()
                         : c.blend == DrawCall::Blend::AddOne ? add_one_.Get()
                                                              : additive_.Get(),
                         nullptr, 0xFFFFFFFF);
    ctx->OMSetDepthStencilState(!c.depth ? depth_off_.Get() : c.blend == DrawCall::Blend::Opaque ? depth_write_.Get() : depth_test_.Get(), 0);
    ctx->RSSetState(c.ground ? ground_bias_.Get() : c.cull ? cull_back_.Get() : cull_none_.Get());
    ctx->Draw(c.count, c.first);
  }
  ID3D11ShaderResourceView* none[6] = {};
  ctx->PSSetShaderResources(0, 6, none);
  ctx->OMSetBlendState(nullptr, nullptr, 0xFFFFFFFF);
  ctx->OMSetDepthStencilState(nullptr, 0);
  ctx->RSSetState(nullptr);
}

void Vfx::set_navmesh(Gpu& gpu, const NavGrid& nav) {
  // NAVMESH_MASK_TEXTURE is the engine's own; the particles that use it (river lilies, ground pools, area markers) only
  // make sense kept off the walls, so it is read as walkable 1 / wall 0, one texel per cell [dedus]
  if (!nav.cells_x || !nav.cells_z || nav.cell_size <= 0) return;
  Texture t;
  t.format = TexFormat::BGRA8;
  t.width = nav.cells_x, t.height = nav.cells_z;
  std::vector<uint8_t> px(static_cast<size_t>(nav.cells_x) * nav.cells_z * 4);
  for (uint32_t z = 0; z < nav.cells_z; ++z)
    for (uint32_t x = 0; x < nav.cells_x; ++x) {
      const uint8_t v = nav.walkable(static_cast<int>(x), static_cast<int>(z)) ? 255 : 0;
      uint8_t* p = &px[(static_cast<size_t>(z) * nav.cells_x + x) * 4];
      p[0] = p[1] = p[2] = v, p[3] = 255;
    }
  t.mips = {std::move(px)};
  navmask_ = gpu.texture(t);
  // NAV_GRID_XFORM: texel centres on cell centres
  const float sx = 1.f / (static_cast<float>(nav.cells_x) * nav.cell_size), sz = 1.f / (static_cast<float>(nav.cells_z) * nav.cell_size);
  nav_xform_ = {sx, sz, -nav.min_x * sx, -nav.min_z * sz};
}

}  // namespace ba
