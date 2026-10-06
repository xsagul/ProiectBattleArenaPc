#include "Character.h"

#include <cstdlib>

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstring>
#include <limits>

#include "ba/Hash.h"
#include "ba/PropertyBin.h"

namespace ba {

namespace {

// Riot's lit_uber shaders, legacy character path (research/shaders/lit_uber_vs 0022, lit_uber_ps 0001):
//   vs: world = sum of weight_i * (pos * BONES[index_i]) (4x3 matrices that already hold the unit's place);
//       vertex light = an ambient cube, n.x^2 * C[n.x < 0] + n.y^2 * C[2 + (n.y < 0)] + n.z^2 * C[4 + (n.z < 0)]
//       with C = LIGHTGRID_COLORS[6] (+X -X +Y -Y +Z -Z), set per draw from the light at the unit
//   ps: discard where alpha == 0; light = saturate(LIGHTGRID_SCALE.y * SELF_ILLUMINATION + vertex light * LIGHTGRID_SCALE.x)
//       (no emissive map); colour = saturate(diffuse * light)
const char* kShader = R"(
cbuffer Frame : register(b0) { row_major float4x4 view_proj; };
cbuffer Bones : register(b1) { float4 bones[256 * 3]; };
cbuffer Light : register(b2) { float4 LIGHTGRID_COLORS[6]; float4 SELF_ILLUMINATION; float4 LIGHTGRID_SCALE; float4 TINT_COLOR; };
Texture2D diffuse : register(t0);
SamplerState samp : register(s0);
struct VSIn { float3 pos : POSITION; uint4 idx : BLENDINDICES; float4 w : BLENDWEIGHT; float3 n : NORMAL; float2 uv : TEXCOORD0; };
struct PSIn { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; float3 n : NORMAL; float3 light : COLOR0; };
float3 bone_point(uint b, float4 p) { return float3(dot(p, bones[b * 3]), dot(p, bones[b * 3 + 1]), dot(p, bones[b * 3 + 2])); }
float3 bone_dir(uint b, float3 d) { return float3(dot(d, bones[b * 3].xyz), dot(d, bones[b * 3 + 1].xyz), dot(d, bones[b * 3 + 2].xyz)); }
PSIn vs_main(VSIn v) {
  float4 p = float4(v.pos, 1);
  float3 w = 0, n = 0;
  [unroll] for (int i = 0; i < 4; ++i) { w += v.w[i] * bone_point(v.idx[i], p); n += v.w[i] * bone_dir(v.idx[i], v.n); }
  PSIn o;
  o.pos = mul(float4(w, 1), view_proj);
  o.uv = v.uv;
  o.n = normalize(n);
  float3 sq = o.n * o.n;
  o.light = sq.x * LIGHTGRID_COLORS[o.n.x < 0 ? 1 : 0].rgb + sq.y * LIGHTGRID_COLORS[o.n.y < 0 ? 3 : 2].rgb +
            sq.z * LIGHTGRID_COLORS[o.n.z < 0 ? 5 : 4].rgb;
  return o;
}
float4 ps_main(PSIn p) : SV_TARGET {
  float4 c = diffuse.Sample(samp, p.uv);
  clip(c.a == 0 ? -1 : 1);  // lit_uber discards fully transparent texels
  float3 light = saturate(LIGHTGRID_SCALE.y * SELF_ILLUMINATION.rgb + p.light * LIGHTGRID_SCALE.x);
  // the TINTING permutation (lit_uber_ps 133 against 123): one more multiply by TINT_COLOR before the saturate
  return float4(saturate(c.rgb * light * TINT_COLOR.rgb), 1);
}
)";

struct Vertex {
  float pos[3];
  uint8_t idx[4];
  float w[4];
  float n[3];
  float uv[2];
};

std::string lower(std::string s) {
  for (char& c : s) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
  return s;
}

/** Row-vector matrix of a translate / rotate (quaternion) / scale. */
float4x4 trs(const Vec3& t, const Quat& q, const Vec3& s) {
  const float x = q[0], y = q[1], z = q[2], w = q[3];
  const float r[3][3] = {{1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w)},
                         {2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w)},
                         {2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y)}};
  float4x4 m;
  for (int i = 0; i < 3; ++i)
    for (int j = 0; j < 3; ++j) m.m[i][j] = r[i][j] * s[static_cast<size_t>(i)];
  m.m[3][0] = t[0];
  m.m[3][1] = t[1];
  m.m[3][2] = t[2];
  return m;
}

}  // namespace

bool CharacterModel::load(Gpu& gpu, const Wad& wad, const std::string& character, int skin, const std::vector<std::string>& hide) {
  const std::string base = "data/characters/" + lower(character);
  auto skin_bytes = wad.read(base + "/skins/skin" + std::to_string(skin) + ".bin");
  if (!skin_bytes) return false;
  const PropertyBin skin_bin(*skin_bytes);
  const BinEntry* props = nullptr;
  for (const BinEntry& e : skin_bin.entries())
    if (e.cls == fnv1a("SkinCharacterDataProperties")) props = &e;
  if (!props) return false;
  const BinValue* mesh = props->field("skinMeshProperties");
  if (!mesh) return false;
  const BinValue* skl = mesh->field("skeleton");
  const BinValue* skn = mesh->field("simpleSkin");
  const BinValue* tex = mesh->field("texture");
  if (const BinValue* sc = mesh->field("skinScale")) skin_scale = static_cast<float>(sc->number());
  if (const BinValue* si = mesh->field("selfIllumination")) self_illumination = static_cast<float>(si->number());
  if (const BinValue* ic = props->field("iconCircle")) {
    const BinValue* v = ic->type == BinType::Option || ic->type == BinType::List || ic->type == BinType::List2 ? (ic->items.empty() ? nullptr : &ic->items[0]) : ic;
    if (v) icon_circle = v->str;
  }
  if (const BinValue* hb = props->field("healthBarData"))
    if (const BinValue* st = hb->field("unitHealthBarStyle")) health_bar_style = static_cast<int>(st->u ? st->u : static_cast<uint64_t>(st->number()));
  if (const BinValue* hb = props->field("healthBarData"))
    if (const BinValue* t = hb->field("hpPerTick")) hp_per_tick = static_cast<float>(t->number());
  if (const BinValue* idle = props->field("idleParticlesEffects"))
    for (const BinValue& e : idle->items) {
      IdleEffect ie;
      if (const BinValue* k = e.field("effectKey")) ie.effect = static_cast<uint32_t>(k->u);
      if (const BinValue* b = e.field("boneName")) ie.bone = b->str;
      if (ie.effect) idle_effects.push_back(ie);
    }
  if (!skl || !skn) return false;
  auto path_hash = [](const BinValue* v) { return v->type == BinType::String ? wad_hash(v->str) : v->u; };

  auto skl_bytes = wad.read_hash(path_hash(skl));
  auto skn_bytes = wad.read_hash(path_hash(skn));
  if (!skl_bytes || !skn_bytes) return false;
  skeleton = read_skl(*skl_bytes);
  const SkinMesh m = read_skn(*skn_bytes);

  std::vector<Vertex> verts(m.vertices.size());
  for (size_t i = 0; i < m.vertices.size(); ++i) {
    const SkinVertex& s = m.vertices[i];
    std::memcpy(verts[i].pos, s.position.data(), 12);
    std::memcpy(verts[i].idx, s.bones.data(), 4);
    std::memcpy(verts[i].w, s.weights.data(), 16);
    std::memcpy(verts[i].n, s.normal.data(), 12);
    std::memcpy(verts[i].uv, s.uv.data(), 8);
  }
  D3D11_BUFFER_DESC bd{};
  bd.Usage = D3D11_USAGE_IMMUTABLE;
  bd.BindFlags = D3D11_BIND_VERTEX_BUFFER;
  bd.ByteWidth = static_cast<UINT>(verts.size() * sizeof(Vertex));
  D3D11_SUBRESOURCE_DATA sd{verts.data(), 0, 0};
  if (FAILED(gpu.device()->CreateBuffer(&bd, &sd, &vb))) return false;
  bd.BindFlags = D3D11_BIND_INDEX_BUFFER;
  bd.ByteWidth = static_cast<UINT>(m.indices.size() * 2);
  sd.pSysMem = m.indices.data();
  if (FAILED(gpu.device()->CreateBuffer(&bd, &sd, &ib))) return false;
  auto load_texture = [&](const BinValue* t) -> ComPtr<ID3D11ShaderResourceView> {
    if (!t) return {};
    try {
      // the smaller sizes are made here, not taken from the file [dedus: SRU_OrderMinionSiege's own texture carries
      // near-white mips 1 to 6 (a 512 texture whose 256 to 8 sizes average 252 .. 163 against 46 for the full one), and
      // the game never shows that minion white: it does not draw characters with the files' mips]
      if (auto bytes = wad.read_hash(path_hash(t))) {
        const Texture texture = read_texture(*bytes);
        if (auto own = gpu.texture_own_mips(texture)) return own;
        return gpu.texture(texture);
      }
    } catch (const std::exception&) {
    }
    return {};
  };
  const ComPtr<ID3D11ShaderResourceView> skin_texture = load_texture(tex);
  if (!skin_texture) std::fprintf(stderr, "%s skin %d: its texture could not be read (%s)\n", character.c_str(), skin, tex ? tex->str.c_str() : "none named");

  // ---- submeshes: initialSubmeshToHide (names split by commas or spaces) stays hidden; materialOverride swaps textures
  std::vector<std::string> hidden;
  for (const std::string& h : hide) hidden.push_back(lower(h));
  if (const BinValue* h = mesh->field("initialSubmeshToHide")) {
    std::string word;
    for (char ch : h->str + " ") {
      if (ch == ',' || ch == ' ') {
        if (!word.empty()) hidden.push_back(lower(word));
        word.clear();
      } else {
        word.push_back(ch);
      }
    }
  }
  for (const SkinRange& r : m.ranges) {
    Submesh s;
    s.name = r.material;
    s.name_hash = fnv1a(r.material);
    s.hidden = std::find(hidden.begin(), hidden.end(), lower(r.material)) != hidden.end();
    s.index_start = r.index_start;
    s.index_count = r.index_count;
    s.texture = skin_texture;
    if (const BinValue* overrides = mesh->field("materialOverride"))
      for (const BinValue& o : overrides->items) {
        const BinValue* sub = o.field("submesh");
        if (sub && lower(sub->str) == lower(r.material))
          if (auto t = load_texture(o.field("texture"))) s.texture = t;
      }
    submeshes.push_back(s);
  }

  // ---- the animation graph the skin links to (its .bin's dependency list: Turret Skin35 uses Animations/Skin34), else
  // animations/skin<N>.bin; clip name -> .anm (and its tick duration), and the blend times between clips
  std::string graph_path = base + "/animations/skin" + std::to_string(skin) + ".bin";
  for (const std::string& l : skin_bin.links())
    if (lower(l).find("/animations/") != std::string::npos) graph_path = lower(l);
  if (auto graph_bytes = wad.read(graph_path)) {
    const PropertyBin graph(*graph_bytes);
    for (const BinEntry& e : graph.entries()) {
      if (const BinValue* mask_map = e.field("mMaskDataMap"))
        for (const auto& [key, mask] : mask_map->pairs)
          if (const BinValue* w = mask.field("mWeightList")) {
            std::vector<float>& out = masks[static_cast<uint32_t>(key.u)];
            for (const BinValue& x : w->items) out.push_back(static_cast<float>(x.number()));
          }
      // mTrackDataMap: each track's mBlendMode [meta default 0]; 1 = its clips are added to the pose under them
      std::unordered_map<uint32_t, int> track_modes;
      if (const BinValue* tracks = e.field("mTrackDataMap"))
        for (const auto& [key, track] : tracks->pairs)
          if (const BinValue* mode = track.field("mBlendMode")) track_modes[static_cast<uint32_t>(key.u)] = static_cast<int>(mode->number());
      if (const BinValue* table = e.field("mBlendDataTable"))
        for (const auto& [key, blend] : table->pairs) {
          const BinValue* t = blend.field("mTime");
          if (blend.cls == fnv1a("TimeBlendData")) blends[key.u] = t ? static_cast<float>(t->number()) : kDefaultBlend;
        }
      const BinValue* map = e.field("mClipDataMap");
      if (!map) continue;
      for (const auto& [key, clip] : map->pairs) {
        Clip c;
        if (const BinValue* f = clip.field("mFlags")) c.flags = static_cast<uint32_t>(f->u ? f->u : static_cast<uint64_t>(f->number()));
        auto names = [&c](const BinValue* list) {
          if (list)
            for (const BinValue& v : list->items) c.children.push_back(static_cast<uint32_t>(v.u));
        };
        auto pair_list = [&c](const BinValue* list) {
          if (!list) return;
          for (const BinValue& v : list->items) {
            const BinValue* name = v.field("mClipName");
            const BinValue* value = v.field("mValue");
            if (name) c.pairs.emplace_back(value ? static_cast<float>(value->number()) : 0.f, static_cast<uint32_t>(name->u));
          }
          std::stable_sort(c.pairs.begin(), c.pairs.end(), [](const auto& a, const auto& b) { return a.first < b.first; });
        };
        auto updater = [&c, &clip]() {
          if (const BinValue* u = clip.field("Updater")) {
            c.updater = u->cls;
            if (const BinValue* d = u->field("driver")) c.updater = d->cls;
          }
        };
        if (clip.cls == fnv1a("AtomicClipData")) {
          c.kind = Clip::Kind::Atomic;
          const BinValue* res = clip.field("mAnimationResourceData");
          const BinValue* file = res ? res->field("mAnimationFilePath") : nullptr;
          if (!file) continue;
          auto anm = wad.read_hash(path_hash(file));
          if (!anm) continue;
          try {
            c.anim = read_anm(*anm);
          } catch (const std::exception&) {
            continue;
          }
          c.file = file->str;
          c.tick = 1.f / c.anim.fps;
          if (const BinValue* t = clip.field("mTickDuration")) c.tick = static_cast<float>(t->number());
          if (const BinValue* t = clip.field("mTrackDataName")) c.track = static_cast<uint32_t>(t->u);
          if (auto mode = track_modes.find(c.track); mode != track_modes.end()) c.additive = mode->second == 1;
          if (const BinValue* t = clip.field("mMaskDataName")) c.mask = static_cast<uint32_t>(t->u);
          if (const BinValue* events = clip.field("mEventDataMap"))
            for (const auto& [ek, ev] : events->pairs) {
              const BinValue* sf = ev.field("mStartFrame");
              const BinValue* ef = ev.field("mEndFrame");
              const float start = sf ? static_cast<float>(sf->number()) : 0.f, end = ef ? static_cast<float>(ef->number()) : -1.f;
              if (ev.cls == fnv1a("SubmeshVisibilityEventData")) {
                Clip::SubmeshEvent se;
                se.start = start, se.end = end;
                if (const BinValue* l = ev.field("mShowSubmeshList"))
                  for (const BinValue& x : l->items) se.show.push_back(static_cast<uint32_t>(x.u));
                if (const BinValue* l = ev.field("mHideSubmeshList"))
                  for (const BinValue& x : l->items) se.hide.push_back(static_cast<uint32_t>(x.u));
                c.submesh_events.push_back(std::move(se));
              } else if (ev.cls == fnv1a("ParticleEventData")) {
                Clip::ParticleEvent pe;
                pe.name = static_cast<uint32_t>(ek.u);
                pe.start = start, pe.end = end;
                if (const BinValue* v = ev.field("mEffectKey")) pe.effect = static_cast<uint32_t>(v->u);
                if (const BinValue* v = ev.field("mIsLoop")) pe.loop = v->number() != 0;
                if (const BinValue* v = ev.field("mIsKillEvent")) pe.kill = v->number() != 0;
                if (const BinValue* v = ev.field("mIsDetachable")) pe.detachable = v->number() != 0;
                if (const BinValue* v = ev.field("scale")) pe.scale = static_cast<float>(v->number());
                if (const BinValue* l = ev.field("mParticleEventDataPairList"); l && !l->items.empty())
                  if (const BinValue* b = l->items[0].field("mBoneName")) pe.bone = static_cast<uint32_t>(b->u);
                if (pe.effect) c.particle_events.push_back(pe);
              }
            }
        } else if (clip.cls == fnv1a("SequencerClipData")) {
          c.kind = Clip::Kind::Sequencer;
          names(clip.field("mClipNameList"));
        } else if (clip.cls == fnv1a("ParallelClipData")) {
          c.kind = Clip::Kind::Parallel;
          names(clip.field("mClipNameList"));
        } else if (clip.cls == fnv1a("SelectorClipData")) {
          c.kind = Clip::Kind::Selector;
          if (const BinValue* list = clip.field("mSelectorPairDataList"))
            for (const BinValue& v : list->items)
              if (const BinValue* name = v.field("mClipName")) c.children.push_back(static_cast<uint32_t>(name->u));
        } else if (clip.cls == fnv1a("ConditionBoolClipData")) {
          c.kind = Clip::Kind::ConditionBool;
          const BinValue* t = clip.field("mTrueConditionClipName");
          const BinValue* f = clip.field("mFalseConditionClipName");
          c.children = {t ? static_cast<uint32_t>(t->u) : 0u, f ? static_cast<uint32_t>(f->u) : 0u};
          updater();
        } else if (clip.cls == fnv1a("ConditionFloatClipData")) {
          c.kind = Clip::Kind::ConditionFloat;
          pair_list(clip.field("mConditionFloatPairDataList"));
          updater();
        } else if (clip.cls == fnv1a("ParametricClipData")) {
          c.kind = Clip::Kind::Parametric;
          pair_list(clip.field("mParametricPairDataList"));
          updater();
        }
        clips[static_cast<uint32_t>(key.u)] = std::move(c);
      }
    }
  }
  return true;
}

const Clip* CharacterModel::clip(uint32_t name) const {
  auto it = clips.find(name);
  return it == clips.end() ? nullptr : &it->second;
}

int CharacterModel::joint_by_name_hash(uint32_t hash) const {
  for (size_t i = 0; i < skeleton.joints.size(); ++i)
    if (fnv1a(skeleton.joints[i].name) == hash) return static_cast<int>(i);
  return -1;
}

namespace {

constexpr float kForever = std::numeric_limits<float>::infinity();

/** The child a condition / parametric node picks for the unit's current state. */
uint32_t choose(const Clip& c, const AnimParams& p) {
  switch (c.kind) {
    case Clip::Kind::ConditionBool:
      return p.condition ? c.children[0] : c.children[1];
    case Clip::Kind::ConditionFloat: {
      // the highest threshold the value reaches (Garen at 340 runs Run_Base, from 341 Run_Fast)
      const float v = c.updater == fnv1a("MoveSpeedParametricUpdater") ? p.move_speed : 0.f;
      uint32_t pick = c.pairs.empty() ? 0 : c.pairs.front().second;
      for (const auto& [value, name] : c.pairs)
        if (v >= value) pick = name;
      return pick;
    }
    case Clip::Kind::Parametric: {
      // the entry nearest the updater's value (the game blends the two around it; no updater is fed yet, so 0)
      uint32_t pick = 0;
      float best = kForever;
      for (const auto& [value, name] : c.pairs)
        if (std::fabs(value) < best) best = std::fabs(value), pick = name;
      return pick;
    }
    case Clip::Kind::Selector:  // random pick by mProbability: first one until the game's random stream drives it
    case Clip::Kind::Parallel:  // layered clips: the first layer until tracks are blended
      return c.children.empty() ? 0 : c.children.front();
    default:
      return 0;
  }
}

}  // namespace

float CharacterModel::duration(uint32_t name, const AnimParams& p, int depth) const {
  const Clip* c = clip(name);
  if (!c || depth > 16) return 0;
  if (c->flags & Clip::kLoop) return kForever;
  if (c->kind == Clip::Kind::Atomic) return c->anim.frames * c->tick;
  if (c->kind == Clip::Kind::Sequencer) {
    float sum = 0;
    for (uint32_t child : c->children) sum += duration(child, p, depth + 1);
    return sum;
  }
  return duration(choose(*c, p), p, depth + 1);
}

const Clip* CharacterModel::resolve(uint32_t name, float t, const AnimParams& p, float& local_t, int depth, uint32_t* atomic,
                                    Layers* layers) const {
  const Clip* c = clip(name);
  if (!c || depth > 16) return nullptr;
  t = std::max(t, 0.f);
  switch (c->kind) {
    case Clip::Kind::Atomic: {
      if (atomic) *atomic = name;
      // past its end a clip starts over: it loops (flag 2), or the unit's state asks for it again
      const float len = c->anim.frames * c->tick;
      local_t = len > 0 ? std::fmod(t, len) : 0.f;
      return c;
    }
    case Clip::Kind::Sequencer: {
      // children in turn; a looping child plays on forever, a sequence that runs out starts over
      float cycle = 0;
      for (uint32_t child : c->children) cycle += duration(child, p, depth + 1);
      if (cycle > 0 && cycle < kForever) t = std::fmod(t, cycle);
      for (uint32_t child : c->children) {
        const float d = duration(child, p, depth + 1);
        if (t < d) return resolve(child, t, p, local_t, depth + 1, atomic, layers);
        t -= d;
      }
      return c->children.empty() ? nullptr : resolve(c->children.back(), t, p, local_t, depth + 1, atomic, layers);
    }
    case Clip::Kind::Parallel:
      // every child plays at once; the first is the main one, the others fill in the joints it does not animate
      if (layers)
        for (size_t i = 1; i < c->children.size(); ++i) {
          float lt = 0;
          if (const Clip* lc = resolve(c->children[i], t, p, lt, depth + 1, nullptr, layers)) layers->emplace_back(lc, lt);
        }
      return c->children.empty() ? nullptr : resolve(c->children.front(), t, p, local_t, depth + 1, atomic, layers);
    default:
      return resolve(choose(*c, p), t, p, local_t, depth + 1, atomic, layers);
  }
}

bool CharacterRenderer::init(Gpu& gpu) {
  ComPtr<ID3DBlob> code;
  if (!gpu.shader(kShader, "character", vs_, ps_, &code)) return false;
  const D3D11_INPUT_ELEMENT_DESC il[] = {
      {"POSITION", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 0, D3D11_INPUT_PER_VERTEX_DATA, 0},
      {"BLENDINDICES", 0, DXGI_FORMAT_R8G8B8A8_UINT, 0, 12, D3D11_INPUT_PER_VERTEX_DATA, 0},
      {"BLENDWEIGHT", 0, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 16, D3D11_INPUT_PER_VERTEX_DATA, 0},
      {"NORMAL", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 32, D3D11_INPUT_PER_VERTEX_DATA, 0},
      {"TEXCOORD", 0, DXGI_FORMAT_R32G32_FLOAT, 0, 44, D3D11_INPUT_PER_VERTEX_DATA, 0},
  };
  gpu.device()->CreateInputLayout(il, 5, code->GetBufferPointer(), code->GetBufferSize(), &layout_);
  D3D11_BUFFER_DESC cbd{};
  cbd.Usage = D3D11_USAGE_DYNAMIC;
  cbd.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
  cbd.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
  cbd.ByteWidth = 64;
  gpu.device()->CreateBuffer(&cbd, nullptr, &frame_cb_);
  cbd.ByteWidth = 256 * 3 * 16;
  gpu.device()->CreateBuffer(&cbd, nullptr, &bones_cb_);
  cbd.ByteWidth = 9 * 16;
  gpu.device()->CreateBuffer(&cbd, nullptr, &light_cb_);
  D3D11_SAMPLER_DESC smp{};
  smp.Filter = D3D11_FILTER_ANISOTROPIC;
  smp.MaxAnisotropy = 4;
  smp.AddressU = smp.AddressV = smp.AddressW = D3D11_TEXTURE_ADDRESS_WRAP;
  smp.MaxLOD = D3D11_FLOAT32_MAX;
  gpu.device()->CreateSamplerState(&smp, &sampler_);
  return true;
}

namespace {

struct LocalPose {
  std::vector<Vec3> t, s;
  std::vector<Quat> r;
};

/** Each joint's local transform `local_t` seconds into an atomic clip, else from the first parallel layer that animates
 *  it, else the bind pose. */
void sample_clip(const Skeleton& sk, const Clip* c, float local_t, LocalPose& out, const CharacterModel::Layers* layers = nullptr) {
  const size_t n = sk.joints.size();
  out.t.resize(n), out.s.resize(n), out.r.resize(n);
  // The track of a joint: the one with its hash. When several joints share a hash (names that differ only in case),
  // the k-th of them takes the k-th such track; with fewer tracks than joints, the last one found.
  auto track_of = [](const Clip* clip, uint32_t hash, size_t nth) -> const Track* {
    const Track* found = nullptr;
    if (clip)
      for (const Track& tr : clip->anim.tracks)
        if (tr.joint_hash == hash) {
          found = &tr;
          if (nth-- == 0) break;
        }
    return found;
  };
  for (size_t i = 0; i < n; ++i) {
    const Joint& j = sk.joints[i];
    out.t[i] = j.translate, out.s[i] = j.scale, out.r[i] = j.rotate;
    size_t nth = 0;
    for (size_t k = 0; k < i; ++k)
      if (sk.joints[k].hash == j.hash) ++nth;
    if (const Track* tr = track_of(c, j.hash, nth)) {
      sample(c->anim, *tr, local_t / c->tick, out.t[i], out.r[i], out.s[i]);
    } else if (layers) {
      for (const auto& [lc, lt] : *layers)
        if (const Track* lt_track = track_of(lc, j.hash, nth)) {
          sample(lc->anim, *lt_track, lt / lc->tick, out.t[i], out.r[i], out.s[i]);
          break;
        }
    }
  }
}

void to_world(const Skeleton& sk, const LocalPose& lp, std::vector<float4x4>& world) {
  const size_t n = sk.joints.size();
  world.assign(n, float4x4{});
  for (size_t i = 0; i < n; ++i) {
    const float4x4 local = trs(lp.t[i], lp.r[i], lp.s[i]);
    const int parent = sk.joints[i].parent;
    world[i] = parent >= 0 ? local * world[static_cast<size_t>(parent)] : local;
  }
}

float clip_time(const Clip* c, float t) {
  const float len = c ? c->anim.frames * c->tick : 0.f;
  return len > 0 ? std::fmod(std::max(t, 0.f), len) : 0.f;
}

}  // namespace

namespace {
/** Inverse of an affine row-vector matrix (rotation / scale in the 3x3, translation in the last row). */
float4x4 affine_inverse(const float4x4& m) {
  const float a = m.m[0][0], b = m.m[0][1], c = m.m[0][2], d = m.m[1][0], e = m.m[1][1], f = m.m[1][2], g = m.m[2][0], h = m.m[2][1], i = m.m[2][2];
  const float det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g);
  float4x4 r;
  if (std::fabs(det) < 1e-12f) return r;
  const float k = 1.f / det;
  r.m[0][0] = (e * i - f * h) * k, r.m[0][1] = (c * h - b * i) * k, r.m[0][2] = (b * f - c * e) * k;
  r.m[1][0] = (f * g - d * i) * k, r.m[1][1] = (a * i - c * g) * k, r.m[1][2] = (c * d - a * f) * k;
  r.m[2][0] = (d * h - e * g) * k, r.m[2][1] = (b * g - a * h) * k, r.m[2][2] = (a * e - b * d) * k;
  for (int col = 0; col < 3; ++col) r.m[3][col] = -(m.m[3][0] * r.m[0][col] + m.m[3][1] * r.m[1][col] + m.m[3][2] * r.m[2][col]);
  return r;
}
}  // namespace

std::string CharacterModel::match_pose(const std::vector<float>& palette) const {
  const size_t count = std::min(palette.size() / 12, skeleton.influences.size());
  if (count < 2) return "too few bones\n";
  std::vector<float4x4> real(count);
  for (size_t b = 0; b < count; ++b)
    for (int row = 0; row < 3; ++row)
      for (int col = 0; col < 4; ++col) real[b].m[col][row] = palette[b * 12 + static_cast<size_t>(row) * 4 + static_cast<size_t>(col)];
  struct Hit {
    float error, time;
    const Clip* clip;
    float4x4 place;
  };
  std::vector<Hit> hits;
  for (const auto& [name, clip] : clips) {
    if (clip.kind != Clip::Kind::Atomic || clip.tick <= 0) continue;
    Hit best{1e30f, 0, &clip, {}};
    const float len = clip.anim.frames * clip.tick;
    for (float t = 0; t <= len + 1e-4f; t += clip.tick * 0.5f) {
      LocalPose lp;
      sample_clip(skeleton, &clip, t, lp);
      std::vector<float4x4> world;
      to_world(skeleton, lp, world);
      auto bone = [&](size_t b) {
        const Joint& j = skeleton.joints[skeleton.influences[b]];
        return trs(j.ibind_translate, j.ibind_rotate, j.ibind_scale) * world[skeleton.influences[b]];
      };
      const float4x4 place = affine_inverse(bone(0)) * real[0];
      float err = 0;
      for (size_t b = 1; b < count; ++b) {
        const float4x4 ours = bone(b) * place;
        for (int r = 0; r < 4; ++r)
          for (int col = 0; col < 3; ++col) err = std::max(err, std::fabs(ours.m[r][col] - real[b].m[r][col]) * (r == 3 ? 0.01f : 1.f));
      }
      if (err < best.error) best.error = err, best.time = t, best.place = place;
    }
    hits.push_back(best);
  }
  std::sort(hits.begin(), hits.end(), [](const Hit& a, const Hit& b) { return a.error < b.error; });
  std::string out;
  char line[512];
  if (!hits.empty()) {
    // the unit's place under the best clip: its scale, its yaw (atan2 of the +z axis' x and z) and where it stands
    const float4x4& pl = hits.front().place;
    const float scale = std::sqrt(pl.m[0][0] * pl.m[0][0] + pl.m[0][1] * pl.m[0][1] + pl.m[0][2] * pl.m[0][2]);
    std::snprintf(line, sizeof line, "place: scale %.4f yaw %.2f deg at %.2f %.2f %.2f (skin scale %.3f)%c", scale,
                  std::atan2(pl.m[2][0], pl.m[2][2]) * 57.29578f, pl.m[3][0], pl.m[3][1], pl.m[3][2], skin_scale, 10);
    out += line;
  }
  for (const Hit& h : hits) {
    std::snprintf(line, sizeof line, "%10.4f  t %6.3f of %6.3f s  %s\n", h.error, h.time, h.clip->anim.frames * h.clip->tick, h.clip->file.c_str());
    out += line;
  }
  return out;
}

void CharacterModel::pose(const std::string& name, float time, const AnimParams& p, std::vector<float4x4>& world) const {
  float local_t = 0;
  Layers layers;
  const Clip* c = resolve(fnv1a(name), time, p, local_t, 0, nullptr, &layers);
  LocalPose lp;
  sample_clip(skeleton, c, local_t, lp, &layers);
  to_world(skeleton, lp, world);
}

float CharacterModel::blend_time(uint32_t from, uint32_t to) const {
  auto it = blends.find(static_cast<uint64_t>(from) << 32 | to);
  return it == blends.end() ? -1.f : it->second;
}

namespace {

/** The unit's local pose from its graph state at `now` (see CharacterModel::animate). */
void animate_local(const CharacterModel& m, AnimState& s, const std::string& request, double now, const AnimParams& p, LocalPose& lp);

}  // namespace

void CharacterModel::animate(AnimState& s, const std::string& request, double now, const AnimParams& p, std::vector<float4x4>& world) const {
  LocalPose lp;
  animate_local(*this, s, request, now, p, lp);
  to_world(skeleton, lp, world);
}

void CharacterModel::animate(AnimState& s, const std::string& request, double now, const AnimParams& p, uint32_t add_clip, float add_time,
                             std::vector<float4x4>& world) const {
  LocalPose lp;
  animate_local(*this, s, request, now, p, lp);
  float local_t = 0;
  const Clip* add = add_clip ? resolve(add_clip, add_time, p, local_t) : nullptr;
  if (add && add->kind == Clip::Kind::Atomic && add->additive) {
    const float len = add->anim.frames * add->tick;
    const float frame = std::min(local_t, len) / add->tick;
    for (size_t i = 0; i < skeleton.joints.size(); ++i) {
      size_t nth = 0;
      for (size_t k = 0; k < i; ++k)
        if (skeleton.joints[k].hash == skeleton.joints[i].hash) ++nth;
      const Track* found = nullptr;
      for (const Track& tr : add->anim.tracks)
        if (tr.joint_hash == skeleton.joints[i].hash) {
          found = &tr;
          if (nth-- == 0) break;
        }
      if (!found) continue;
      Vec3 dt{0, 0, 0}, ds{1, 1, 1};
      Quat dr{0, 0, 0, 1};
      sample(add->anim, *found, frame, dt, dr, ds);
      const Quat a = lp.r[i];
      // the joint's rotation, then the clip's on top (Hamilton product a * dr, both x y z w)
      lp.r[i] = {a[3] * dr[0] + a[0] * dr[3] + a[1] * dr[2] - a[2] * dr[1], a[3] * dr[1] - a[0] * dr[2] + a[1] * dr[3] + a[2] * dr[0],
                 a[3] * dr[2] + a[0] * dr[1] - a[1] * dr[0] + a[2] * dr[3], a[3] * dr[3] - a[0] * dr[0] - a[1] * dr[1] - a[2] * dr[2]};
      for (size_t k = 0; k < 3; ++k) lp.t[i][k] += dt[k], lp.s[i][k] *= ds[k];
    }
  }
  to_world(skeleton, lp, world);
}

void CharacterModel::animate(AnimState& s, const std::string& request, const AnimParams& p, AnimState& under, const std::string& under_request,
                             const AnimParams& under_p, double now, std::vector<float4x4>& world, bool& layered) const {
  LocalPose top, base;
  animate_local(*this, s, request, now, p, top);
  const Clip* tc = s.cur;
  auto mask = tc ? masks.find(tc->mask) : masks.end();
  // the standing clip goes on only while the upper one is on another track and names the joints it drives
  animate_local(*this, under, under_request, now, under_p, base);
  layered = tc && under.cur && tc->track != under.cur->track && mask != masks.end();
  if (layered) {
    for (size_t i = 0; i < base.t.size() && i < top.t.size(); ++i)
      if (i < mask->second.size() && mask->second[i] > 0) base.t[i] = top.t[i], base.r[i] = top.r[i], base.s[i] = top.s[i];
    to_world(skeleton, base, world);
  } else {
    to_world(skeleton, top, world);
  }
}

namespace {

void animate_local(const CharacterModel& m, AnimState& s, const std::string& request, double now, const AnimParams& p, LocalPose& lp) {
  const Skeleton& skeleton = m.skeleton;
  using Layers = CharacterModel::Layers;
  const float kDefaultBlend = CharacterModel::kDefaultBlend;
  auto duration = [&m](uint32_t name, const AnimParams& ap) { return m.duration(name, ap); };
  auto resolve = [&m](uint32_t name, float t, const AnimParams& ap, float& local_t, int depth, uint32_t* atomic, Layers* layers) {
    return m.resolve(name, t, ap, local_t, depth, atomic, layers);
  };
  auto blend_time = [&m](uint32_t from, uint32_t to) { return m.blend_time(from, to); };
  const uint32_t want = fnv1a(request);
  if (want != s.request) s.prev_request = s.request, s.request = want, s.start = now;
  float local_t = 0;
  uint32_t atomic = 0;
  Layers layers;
  float t = static_cast<float>(now - s.start) * p.rate;
  if (p.hold) {
    const float d = duration(want, p);
    if (d > 0 && d < 1e30f && t > d) t = d - 1e-3f;
  }
  const Clip* c = resolve(want, t, p, local_t, 0, &atomic, &layers);
  if (c != s.cur && s.cur) {
    // a switch: the table is keyed by the clips themselves, or by the names asked for ("Run" -> "Spell1")
    float b = blend_time(s.cur_name, atomic);
    if (b < 0) b = blend_time(s.prev_request ? s.prev_request : s.cur_name, want);
    if (b < 0) b = blend_time(s.cur_name, want);
    if (b < 0) b = blend_time(s.prev_request, atomic);
    s.blend = b < 0 ? kDefaultBlend : b;
    s.from = s.cur, s.from_t = s.cur_t, s.from_at = now;
  }
  s.cur = c, s.cur_name = atomic, s.cur_t = local_t;
  s.playing.clear();
  if (c) s.playing.emplace_back(c, local_t);
  for (const auto& l : layers) s.playing.push_back(l);

  sample_clip(skeleton, c, local_t, lp, &layers);
  const float since = static_cast<float>(now - s.from_at);
  if (s.from && s.blend > 0 && since < s.blend) {
    // the outgoing clip plays on while its weight goes to 0
    LocalPose old;
    sample_clip(skeleton, s.from, clip_time(s.from, s.from_t + since), old);
    const float w = since / s.blend;
    for (size_t i = 0; i < lp.t.size(); ++i) {
      for (size_t k = 0; k < 3; ++k) {
        lp.t[i][k] = old.t[i][k] + (lp.t[i][k] - old.t[i][k]) * w;
        lp.s[i][k] = old.s[i][k] + (lp.s[i][k] - old.s[i][k]) * w;
      }
      const Quat& a = old.r[i];
      Quat& q = lp.r[i];
      const float sign = a[0] * q[0] + a[1] * q[1] + a[2] * q[2] + a[3] * q[3] < 0 ? -1.f : 1.f;
      float len = 0;
      for (size_t k = 0; k < 4; ++k) q[k] = a[k] + (sign * q[k] - a[k]) * w, len += q[k] * q[k];
      len = std::sqrt(len);
      if (len > 1e-9f)
        for (float& x : q) x /= len;
    }
  } else {
    s.from = nullptr;
  }
}

}  // namespace

void CharacterRenderer::draw(Gpu& gpu, const float4x4& view_proj, const CharacterInstance& ci) {
  const CharacterModel& m = *ci.model;
  const size_t n = m.skeleton.joints.size();
  std::vector<float4x4> world;
  bool layered = false;
  if (ci.state && ci.under_state)
    m.animate(*ci.state, ci.clip, ci.params, *ci.under_state, ci.under_clip, ci.under_params, ci.now, world, layered);
  else if (ci.state && !ci.add_clip.empty())
    m.animate(*ci.state, ci.clip, ci.now, ci.params, fnv1a(ci.add_clip), ci.add_time, world);
  else if (ci.state)
    m.animate(*ci.state, ci.clip, ci.now, ci.params, world);
  else
    m.pose(ci.clip, ci.time, ci.params, world);
  // ---- which submeshes show: the skin's initialSubmeshToHide, then the SubmeshVisibilityEventData of the clips that
  // play (the standing clip's first, the upper clip's over them)
  std::vector<char> hidden(m.submeshes.size());
  for (size_t i = 0; i < m.submeshes.size(); ++i) hidden[i] = m.submeshes[i].hidden;
  auto apply = [&](const AnimState& st) {
    for (const auto& [clip, t] : st.playing) {
      const float frame = clip->tick > 0 ? t / clip->tick : 0.f;
      for (const Clip::SubmeshEvent& e : clip->submesh_events) {
        if (frame < e.start || (e.end >= 0 && frame > e.end)) continue;
        for (size_t i = 0; i < m.submeshes.size(); ++i) {
          const uint32_t h = m.submeshes[i].name_hash;
          if (std::find(e.show.begin(), e.show.end(), h) != e.show.end()) hidden[i] = 0;
          if (std::find(e.hide.begin(), e.hide.end(), h) != e.hide.end()) hidden[i] = 1;
        }
      }
    }
  };
  ci.layered = layered;
  if (ci.under_state && layered) apply(*ci.under_state);
  if (ci.state) apply(*ci.state);
  if (!ci.add_clip.empty())
    if (const Clip* add = m.clip(fnv1a(ci.add_clip)); add && add->kind == Clip::Kind::Atomic) {
      // the additive clip's own events (a breaking plate shows its broken pieces while they fall)
      AnimState added;
      added.playing.push_back({add, ci.add_time});
      apply(added);
    }
  if (ci.hide)
    for (size_t i = 0; i < m.submeshes.size(); ++i)
      if (std::find(ci.hide->begin(), ci.hide->end(), m.submeshes[i].name_hash) != ci.hide->end()) hidden[i] = 1;
  // ---- the unit's place: skinScale, facing, position
  float4x4 place;
  const float c = std::cos(ci.yaw), sn = std::sin(ci.yaw), k = m.skin_scale * ci.scale;
  place.m[0][0] = c * k, place.m[0][2] = -sn * k;
  place.m[1][1] = k;
  place.m[2][0] = sn * k, place.m[2][2] = c * k;
  place.m[3][0] = ci.position.x, place.m[3][1] = ci.position.y, place.m[3][2] = ci.position.z;
  if (ci.place) {
    place = *ci.place;
    for (int r = 0; r < 3; ++r)
      for (int col = 0; col < 3; ++col) place.m[r][col] *= k;
  }
  if (ci.joints_out) {
    ci.joints_out->resize(n);
    for (size_t i = 0; i < n && i < world.size(); ++i) (*ci.joints_out)[i] = world[i] * place;
  }

  // ---- bones: inverse bind * pose * place, for each skin influence, as 4x3 (transposed rows for the shader's dot)
  D3D11_MAPPED_SUBRESOURCE map{};
  ID3D11DeviceContext* ctx = gpu.ctx();
  if (SUCCEEDED(ctx->Map(bones_cb_.Get(), 0, D3D11_MAP_WRITE_DISCARD, 0, &map))) {
    float* out = static_cast<float*>(map.pData);
    const size_t count = std::min<size_t>(m.skeleton.influences.size(), 256);
    for (size_t b = 0; b < count; ++b) {
      const size_t ji = m.skeleton.influences[b];
      if (ji >= n) continue;
      const Joint& j = m.skeleton.joints[ji];
      const float4x4 bone = trs(j.ibind_translate, j.ibind_rotate, j.ibind_scale) * world[ji] * place;
      for (int row = 0; row < 3; ++row)
        for (int col = 0; col < 4; ++col) out[b * 12 + static_cast<size_t>(row) * 4 + static_cast<size_t>(col)] = bone.m[col][row];
    }
    ctx->Unmap(bones_cb_.Get(), 0);
  }
  if (SUCCEEDED(ctx->Map(frame_cb_.Get(), 0, D3D11_MAP_WRITE_DISCARD, 0, &map))) {
    std::memcpy(map.pData, view_proj.m, 64);
    ctx->Unmap(frame_cb_.Get(), 0);
  }
  if (SUCCEEDED(ctx->Map(light_cb_.Get(), 0, D3D11_MAP_WRITE_DISCARD, 0, &map))) {
    float* l = static_cast<float*>(map.pData);
    for (int i = 0; i < 6; ++i) l[i * 4] = cube_[i][0], l[i * 4 + 1] = cube_[i][1], l[i * 4 + 2] = cube_[i][2], l[i * 4 + 3] = 0;
    l[24] = l[25] = l[26] = m.self_illumination, l[27] = 0;
    l[28] = scale_[0], l[29] = scale_[1], l[30] = l[31] = 0;
    l[32] = ci.tint[0], l[33] = ci.tint[1], l[34] = ci.tint[2], l[35] = 1;
    ctx->Unmap(light_cb_.Get(), 0);
  }
  ctx->IASetInputLayout(layout_.Get());
  ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
  ctx->VSSetShader(vs_.Get(), nullptr, 0);
  ctx->PSSetShader(ps_.Get(), nullptr, 0);
  ctx->VSSetConstantBuffers(0, 1, frame_cb_.GetAddressOf());
  ctx->VSSetConstantBuffers(1, 1, bones_cb_.GetAddressOf());
  ctx->VSSetConstantBuffers(2, 1, light_cb_.GetAddressOf());
  ctx->PSSetConstantBuffers(2, 1, light_cb_.GetAddressOf());
  ctx->PSSetSamplers(0, 1, sampler_.GetAddressOf());

  ctx->OMSetBlendState(nullptr, nullptr, 0xFFFFFFFF);
  ctx->OMSetDepthStencilState(nullptr, 0);
  {
    // test only: BA_CHAR_CULL = none | front | back (default: the device default, back faces of clockwise fronts culled)
    static Microsoft::WRL::ComPtr<ID3D11RasterizerState> test_rs;
    static const char* mode = std::getenv("BA_CHAR_CULL");
    if (mode && !test_rs) {
      D3D11_RASTERIZER_DESC rd{};
      rd.FillMode = D3D11_FILL_SOLID, rd.DepthClipEnable = TRUE;
      rd.CullMode = std::string(mode) == "none" ? D3D11_CULL_NONE : std::string(mode) == "front" ? D3D11_CULL_FRONT : D3D11_CULL_BACK;
      gpu.device()->CreateRasterizerState(&rd, &test_rs);
    }
    ctx->RSSetState(test_rs.Get());
  }
  const UINT stride = sizeof(Vertex), offset = 0;
  ctx->IASetVertexBuffers(0, 1, m.vb.GetAddressOf(), &stride, &offset);
  ctx->IASetIndexBuffer(m.ib.Get(), DXGI_FORMAT_R16_UINT, 0);
  for (size_t i = 0; i < m.submeshes.size(); ++i) {
    const CharacterModel::Submesh& s = m.submeshes[i];
    if (hidden[i]) continue;
    ctx->PSSetShaderResources(0, 1, s.texture.GetAddressOf());
    ctx->DrawIndexed(s.index_count, s.index_start, 0);
  }
}

}  // namespace ba
