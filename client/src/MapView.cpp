#include "MapView.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <optional>
#include <sstream>

#include "ba/Hash.h"
#include "ba/MapGeometry.h"
#include "ba/PropertyBin.h"

namespace ba {

namespace {

// The pixel math is Riot's, read from their compiled shaders (tools/disasm_shaders.py, research/shaders):
//   Shaders/StaticMesh/defaultenv_flat_alphatest: c = tex.rgb * tex.a, then TintColor as an overlay
//     (tint < 0.5: 2 * c * tint, else 1 - 2 * (1 - tint) * (1 - c)), times (SHADOW_COLOR + SHADOW_COLOR_COMPLEMENT)
//   Shaders/StaticMesh/vertexdeform (brush, USE_GRASS_TINT_MAP): the grass tint map looked up at the world position
//     (uv = xz * TERRAIN_XFORM.xy + TERRAIN_XFORM.zw, v flipped), times tex.rgb * TintColor
// Out of shadow SHADOW_COLOR + SHADOW_COLOR_COMPLEMENT is 1.
const char* kShader = R"(
cbuffer Frame : register(b0) { row_major float4x4 view_proj; float4 tint; float4 params; float4 terrain_xform; };
Texture2D diffuse : register(t0);
Texture2D grass_tint : register(t1);
SamplerState samp : register(s0);
SamplerState clamp_samp : register(s1);
struct VSIn { float3 pos : POSITION; float2 uv : TEXCOORD0; };
struct PSIn { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; float2 world : TEXCOORD1; };
PSIn vs_main(VSIn v) { PSIn o; o.pos = mul(float4(v.pos, 1), view_proj); o.uv = v.uv; o.world = v.pos.xz; return o; }
float4 ps_main(PSIn p) : SV_TARGET {
  float4 t = diffuse.Sample(samp, p.uv);
  clip(t.a - params.x);  // AlphaTestValue
  float3 c;
  if (params.w > 0) {
    // VertexDeform (brush)
    float2 g = p.world * terrain_xform.xy + terrain_xform.zw;
    g.y = 1 - g.y;
    c = grass_tint.Sample(clamp_samp, g).rgb * t.rgb * tint.rgb;
  } else {
    float3 pm = t.rgb * t.a;
    c = tint.rgb < 0.5 ? 2 * pm * tint.rgb : 1 - 2 * (1 - tint.rgb) * (1 - pm);
  }
  return float4(c, t.a);
}
)";

struct Vertex {
  float x, y, z, u, v;
};

float half_to_float(uint16_t h) {
  const uint32_t s = (h >> 15) & 1, e = (h >> 10) & 31, m = h & 1023;
  float f;
  if (e == 0) f = std::ldexp(static_cast<float>(m), -24);
  else if (e == 31) f = m ? NAN : INFINITY;
  else f = std::ldexp(static_cast<float>(m | 1024), static_cast<int>(e) - 25);
  return s ? -f : f;
}

/** A League row-vector matrix as a shader constant: register i holds column i (the compiled shaders compute
 *  out.i = dot(v, register i): research/shaders141, srx_blend_ocean's vertex shader). */
void columns(const float* league, float* out) {
  for (int i = 0; i < 4; ++i)
    for (int k = 0; k < 4; ++k) out[i * 4 + k] = league[k * 4 + i];
}

DXGI_FORMAT dxgi(GeoFormat f) {
  switch (f) {
    case GeoFormat::F1: return DXGI_FORMAT_R32_FLOAT;
    case GeoFormat::F2: return DXGI_FORMAT_R32G32_FLOAT;
    case GeoFormat::F3: return DXGI_FORMAT_R32G32B32_FLOAT;
    case GeoFormat::F4: return DXGI_FORMAT_R32G32B32A32_FLOAT;
    case GeoFormat::BGRA8:
    case GeoFormat::ZYXW8: return DXGI_FORMAT_B8G8R8A8_UNORM;
    case GeoFormat::RGBA8: return DXGI_FORMAT_R8G8B8A8_UNORM;
    case GeoFormat::H2: return DXGI_FORMAT_R16G16_FLOAT;
    case GeoFormat::H3:
    case GeoFormat::H4: return DXGI_FORMAT_R16G16B16A16_FLOAT;
  }
  return DXGI_FORMAT_UNKNOWN;
}

/** The mapgeo element a vertex shader input reads (the semantics follow D3D9's vertex declaration usages). */
bool element_of(const std::string& semantic, uint32_t index, GeoElement& out) {
  if (semantic == "POSITION" && index == 0) return out = GeoElement::Position, true;
  if (semantic == "NORMAL" && index == 0) return out = GeoElement::Normal, true;
  if (semantic == "BLENDWEIGHT" && index == 0) return out = GeoElement::BlendWeight, true;
  if (semantic == "BLENDINDICES" && index == 0) return out = GeoElement::BlendIndex, true;
  if (semantic == "COLOR" && index <= 1) return out = index == 0 ? GeoElement::Color0 : GeoElement::Color1, true;
  // TEXCOORD0 .. 7 are elements 7 .. 14 (the brush's layout carries element 12, TEXCOORD5, next to Uv0)
  if (semantic == "TEXCOORD" && index <= 7) return out = static_cast<GeoElement>(static_cast<uint32_t>(GeoElement::Uv0) + index), true;
  return false;
}

// StaticMaterialPassDef enums [dedus din date: premultiplied materials blend ONE / 7, the others 6 / 7, so the factors
// follow the GL order ZERO, ONE, SRC_COLOR, INV_SRC_COLOR, DST_COLOR, INV_DST_COLOR, SRC_ALPHA, INV_SRC_ALPHA, DST_ALPHA,
// INV_DST_ALPHA; only 0, 1, 6, 7 occur on the Rift]
D3D11_BLEND blend_factor(uint32_t f) {
  static const D3D11_BLEND table[] = {D3D11_BLEND_ZERO,       D3D11_BLEND_ONE,           D3D11_BLEND_SRC_COLOR,    D3D11_BLEND_INV_SRC_COLOR,
                                      D3D11_BLEND_DEST_COLOR, D3D11_BLEND_INV_DEST_COLOR, D3D11_BLEND_SRC_ALPHA,    D3D11_BLEND_INV_SRC_ALPHA,
                                      D3D11_BLEND_DEST_ALPHA, D3D11_BLEND_INV_DEST_ALPHA};
  return f < 10 ? table[f] : D3D11_BLEND_ONE;
}
// depthCompareFunc [meta default 3; GL order NEVER, LESS, EQUAL, LEQUAL, GREATER, NOTEQUAL, GEQUAL, ALWAYS: de măsurat]
D3D11_COMPARISON_FUNC compare(uint32_t f) {
  static const D3D11_COMPARISON_FUNC table[] = {D3D11_COMPARISON_NEVER,   D3D11_COMPARISON_LESS,      D3D11_COMPARISON_EQUAL,
                                                D3D11_COMPARISON_LESS_EQUAL, D3D11_COMPARISON_GREATER, D3D11_COMPARISON_NOT_EQUAL,
                                                D3D11_COMPARISON_GREATER_EQUAL, D3D11_COMPARISON_ALWAYS};
  return f < 8 ? table[f] : D3D11_COMPARISON_LESS_EQUAL;
}

double num(const BinValue* v, double dflt) { return v ? v->number() : dflt; }

/** The world box of a model: its mapgeo box (min xyz, max xyz) through its row-vector matrix. */
void world_box(const GeoModel& m, float out[6]) {
  out[0] = out[1] = out[2] = 1e30f, out[3] = out[4] = out[5] = -1e30f;
  for (int i = 0; i < 8; ++i) {
    const float p[3] = {m.bbox[(i & 1) ? 3 : 0], m.bbox[(i & 2) ? 4 : 1], m.bbox[(i & 4) ? 5 : 2]};
    for (int k = 0; k < 3; ++k) {
      const float w = p[0] * m.matrix[static_cast<size_t>(0 * 4 + k)] + p[1] * m.matrix[static_cast<size_t>(1 * 4 + k)] +
                      p[2] * m.matrix[static_cast<size_t>(2 * 4 + k)] + m.matrix[static_cast<size_t>(12 + k)];
      out[k] = std::min(out[k], w), out[k + 3] = std::max(out[k + 3], w);
    }
  }
}

/** Whether a world box can be on screen: not wholly outside one of the view volume's planes (row-vector clip = p * vp). */
bool visible(const float b[6], const float4x4& vp) {
  // planes from the columns of vp: x <= w, -x <= w, y <= w, -y <= w, z >= 0, z <= w
  float planes[6][4];
  for (int k = 0; k < 4; ++k) {
    const float x = vp.m[k][0], y = vp.m[k][1], z = vp.m[k][2], w = vp.m[k][3];
    planes[0][k] = w + x, planes[1][k] = w - x, planes[2][k] = w + y, planes[3][k] = w - y, planes[4][k] = z, planes[5][k] = w - z;
  }
  for (const auto& pl : planes) {
    // the box corner farthest along the plane's normal
    const float px = pl[0] >= 0 ? b[3] : b[0], py = pl[1] >= 0 ? b[4] : b[1], pz = pl[2] >= 0 ? b[5] : b[2];
    if (px * pl[0] + py * pl[1] + pz * pl[2] + pl[3] < 0) return false;
  }
  return true;
}

struct Cb {
  float view_proj[16];
  float tint[4];
  float params[4];
  float terrain_xform[4];
};

}  // namespace

bool MapView::controller_shown(const PropertyBin& bin, uint32_t controller, int depth) {
  const BinEntry* c = bin.entry(controller);
  if (!c || depth > 8) return true;
  if (c->cls == fnv1a("MutatorMapVisibilityController")) return false;
  if (c->cls == fnv1a("ChildMapVisibilityController")) {
    const BinValue* parents = c->field("Parents");
    const BinValue* mode = c->field("ParentMode");
    if (!parents || parents->items.empty()) return true;
    const bool any = mode && static_cast<int>(mode->number()) == 1;
    bool result = !any;
    for (const BinValue& p : parents->items) {
      const bool s = controller_shown(bin, static_cast<uint32_t>(p.u), depth + 1);
      result = any ? (result || s) : (result && s);
    }
    return result;
  }
  if (const BinValue* dv = c->field("DefaultVisible")) return dv->number() != 0;
  return true;
}

bool MapView::load(Gpu& gpu, const Wad& wad, const Wad* shaders_wad, const Wad* cache_wad, const Wad* levels_wad) {
  auto geo_bytes = wad.read("data/maps/mapgeometry/map11/base_srx.mapgeo");
  auto mat_bytes = wad.read("data/maps/mapgeometry/map11/base_srx.materials.bin");
  if (!geo_bytes || !mat_bytes) return false;
  const MapGeometry geo = read_mapgeo(*geo_bytes);
  const PropertyBin mats(*mat_bytes);
  auto progress = [&](float f) {
    if (on_progress) on_progress(f);
  };
  progress(0.05f);

  // ---- materials, by name
  std::unordered_map<std::string, Material> materials;
  const uint32_t kStatic = fnv1a("StaticMaterialDef");
  for (const BinEntry& e : mats.entries()) {
    if (e.cls != kStatic) continue;
    const BinValue* name = e.field("name");
    if (!name) continue;
    Material m;
    if (const BinValue* samplers = e.field("samplerValues"))
      for (const BinValue& s : samplers->items) {
        // patch 14.1: samplerName = the shader's slot, TextureName = the file (a .dds path); later patches renamed them
        // to TextureName = the slot, texturePath = the file (a path hash)
        const BinValue* sn = s.field("samplerName");
        const BinValue* tn = sn ? sn : s.field("TextureName");
        const BinValue* tp = sn ? s.field("TextureName") : s.field("texturePath");
        if (!tn || !tp) continue;
        // DiffuseTexture: defaultenv / vertexdeform; Diffuse_Texture: 14.1's srx_blend_* terrain shaders, whose own
        // formula (noise / decal blending) is not reproduced yet [de reprodus din shader-ul 14.1]
        if (tn->str == "DiffuseTexture" || tn->str == "Diffuse_Texture") m.diffuse = tp->type == BinType::String ? wad_hash(tp->str) : tp->u;
      }
    if (const BinValue* params = e.field("paramValues"))
      for (const BinValue& p : params->items) {
        const BinValue* pn = p.field("name");
        const BinValue* pv = p.field("value");
        if (!pn || !pv) continue;
        if (pn->str == "TintColor")
          for (int i = 0; i < 4; ++i) m.tint[i] = static_cast<float>(pv->num[static_cast<size_t>(i)]);
        if (pn->str == "AlphaTestValue") m.alpha_test = static_cast<float>(pv->num[0]);
        // only the brush's VertexDeform shader has wave parameters
        if (pn->str == "WaveFrequency") m.deform = true;
      }
    if (const BinValue* tech = e.field("techniques"))
      if (!tech->items.empty())
        if (const BinValue* passes = tech->items[0].field("passes"))
          if (!passes->items.empty())
            if (const BinValue* be = passes->items[0].field("blendEnable")) m.blend = be->num[0] != 0;
    materials[name->str] = m;
  }

  // ---- Riot's shaders for the materials that have them
  std::unordered_map<std::string, size_t> rmaterial_of;
  std::unordered_map<uint64_t, ComPtr<ID3D11ShaderResourceView>> textures;
  auto texture = [&](uint64_t hash) -> ComPtr<ID3D11ShaderResourceView> {
    auto& t = textures[hash];
    if (t) return t;
    for (const Wad* w : {&wad, shaders_wad, levels_wad}) {
      if (!w) continue;
      if (auto bytes = w->read_hash(hash)) {
        try {
          t = gpu.texture(read_texture(*bytes));
        } catch (const std::exception&) {
        }
        if (t) break;
      }
    }
    return t;
  };
  // textures the engine binds by name (not the material's)
  std::map<std::string, ComPtr<ID3D11ShaderResourceView>> engine_textures;
  auto lower = [](std::string s) {
    for (char& ch : s) ch = static_cast<char>(ch >= 'A' && ch <= 'Z' ? ch - 'A' + 'a' : ch);
    return s;
  };
  auto dds_path = [&](std::string path) {  // the bins name some textures .png while the wads ship .dds
    path = lower(path);
    const size_t dot = path.find_last_of('.');
    if (dot != std::string::npos && path.substr(dot) == ".png") path = path.substr(0, dot) + ".dds";
    return path;
  };
  // GRASS_TINT_MAP: the grass tint of this geometry's MapSkin (mGrassTintTexture), a file of levels/map11/info/ (the
  // name alone is in the bin; Map11LEVELS.wad holds it there). GRASS_TINT_MAP_ALTERNATE is the elemental tint the
  // brush blends to by GRASS_INTERP during a transition: before any, GRASS_INTERP = 0 [dedus: vertexdeform]
  auto use_grass_tint = [&](const std::string& file) {
    const uint64_t tint_hash = wad_hash("levels/map11/info/" + lower(file));
    auto srv = texture(tint_hash);
    if (srv) engine_textures["GRASS_TINT_MAP"] = engine_textures["GRASS_TINT_MAP_ALTERNATE"] = srv;
    for (const Wad* w : {&wad, shaders_wad, levels_wad}) {
      if (!w || !grass_tint_rgba_.empty()) continue;
      if (auto bytes = w->read_hash(tint_hash)) {
        try {
          const Texture t = read_texture(*bytes);
          grass_tint_rgba_ = texture_rgba(t), grass_tint_w_ = t.width, grass_tint_h_ = t.height;
        } catch (const std::exception&) {
        }
      }
    }
  };
  // 12.23: the skins are in map11.bin; the Rift's is the one linked to this geometry's container (mMapContainerLink)
  if (auto map_bytes = wad.read("data/maps/shipping/map11/map11.bin")) {
    const PropertyBin map_bin(*map_bytes);
    for (const BinEntry& e : map_bin.entries()) {
      if (e.cls != fnv1a("MapSkin")) continue;
      const BinValue* link = e.field("mMapContainerLink");
      const BinValue* gt = e.field("mGrassTintTexture");
      if (link && gt && lower(link->str) == "maps/mapgeometry/map11/base_srx") use_grass_tint(gt->str);
    }
  }
  for (const BinEntry& e : mats.entries()) {
    if (e.cls == fnv1a("MapSkin")) {
      const BinValue* n = e.field("name");
      const BinValue* gt = e.field("mGrassTintTexture");
      if (n && gt && n->str == "Default" && grass_tint_rgba_.empty()) use_grass_tint(gt->str);
    }
    // TERRAIN_BLEND: the MapContainer's MapTerrainPaint texture, read at the world position through TERRAIN_XFORM as
    // the srx_blend shaders do [dedus din nume și din eșantionare]
    if (const BinValue* components = e.field("components"))
      for (const BinValue& c : components->items)
        if (const BinValue* tp = c.field("TerrainPaintTexturePath"))
          if (auto srv = texture(wad_hash(dds_path(tp->str)))) engine_textures["TERRAIN_BLEND"] = srv;
  }
  map_constants_["GRASS_INTERP"] = {0, 0, 0, 0};

  if (shaders_wad && cache_wad && library_.load(*shaders_wad)) {
    ShaderCache cache(*cache_wad);
    std::unordered_map<std::string, RiotProgram*> program_of;
    size_t entry_index = 0;
    for (const BinEntry& e : mats.entries()) {
      // the materials' shaders and textures are most of the map's loading
      progress(0.05f + 0.75f * static_cast<float>(entry_index++) / static_cast<float>(mats.entries().size()));
      if (e.cls != kStatic) continue;
      const BinValue* name = e.field("name");
      const BinValue* tech = e.field("techniques");
      if (!name || !tech || tech->items.empty()) continue;
      const BinValue* passes = tech->items[0].field("passes");
      if (!passes || passes->items.empty()) continue;
      const BinValue& pass = passes->items[0];
      const BinValue* link = pass.field("shader");
      RMaterial rm;
      rm.name = name->str;
      rm.def = link ? library_.find(static_cast<uint32_t>(link->u)) : nullptr;
      if (!rm.def) {
        missing_shaders_.insert(link ? "shader link " + std::to_string(link->u) : "no shader link");
        continue;
      }
      // the permutation: the definition's feature defines, its static switches (the material's StaticMaterialSwitchDef,
      // else onByDefault), the material's and the pass's shaderMacros, and the engine's state. Engine state for now:
      // no fog of war and no shadow maps yet (DISABLE_FOW, DISABLE_SHADOWS), the chosen environment quality
      Defines defines = rm.def->feature_defines;
      for (const auto& [sw, on] : rm.def->switches) defines[sw] = on ? "1" : "0";
      if (const BinValue* sws = e.field("switches"))
        for (const BinValue& sw : sws->items) {
          const BinValue* n = sw.field("name");
          const BinValue* on = sw.field("on");  // [meta default true]
          if (n) defines[n->str] = !on || on->number() != 0 ? "1" : "0";
        }
      for (const BinValue* macros : {e.field("shaderMacros"), pass.field("shaderMacros")})
        if (macros)
          for (const auto& [k, v] : macros->pairs) defines[k.str] = v.str;
      defines["DISABLE_FOW"] = "1";
      defines["DISABLE_SHADOWS"] = "1";
      // the environment quality (a shader without the define ignores it: the cache keeps only a table's own defines)
      // [de măsurat: which of the game's Environment Quality steps turn LOW_QUALITY_MODE on; the player plays on Low]
      if (low_quality) defines["LOW_QUALITY_MODE"] = "1";
      std::string key = rm.def->path;
      for (const auto& [k, v] : defines) key += " " + k + "=" + v;
      auto found = program_of.find(key);
      if (found == program_of.end()) {
        auto vs = cache.blob(rm.def->path, 'v', defines);
        auto ps = cache.blob(rm.def->path, 'p', defines);
        RiotProgram* prog = nullptr;
        if (vs && ps) {
          auto p2 = std::make_unique<RiotProgram>();
          if (p2->create(gpu, *vs, *ps)) prog = p2.get(), programs_.push_back(std::move(p2));
        }
        if (!prog) missing_shaders_.insert(key);
        found = program_of.emplace(key, prog).first;
      }
      rm.program = found->second;
      if (!rm.program) continue;
      // constants: each physical ParameterN starts at the definition's data; the material's named values go into the
      // components their logical parameter names (fields: 1 x, 2 y, 4 z, 8 w, taken in that order) [dedus]
      std::map<std::string, std::array<float, 4>> named;
      if (const BinValue* params = e.field("paramValues"))
        for (const BinValue& pv : params->items) {
          const BinValue* pn = pv.field("name");
          const BinValue* v = pv.field("value");
          if (!pn) continue;
          std::array<float, 4> a{0, 0, 0, 0};  // [meta: value default 0,0,0,0]
          if (v)
            for (size_t k = 0; k < 4; ++k) a[k] = static_cast<float>(v->num[k]);
          named[pn->str] = a;
        }
      for (const ShaderDef::Param& p : rm.def->params) {
        std::array<float, 4> reg{p.data[0], p.data[1], p.data[2], p.data[3]};
        for (const auto& [lname, mask] : p.logical) {
          auto it = named.find(lname);
          if (it == named.end()) continue;
          size_t src = 0;
          for (size_t c = 0; c < 4; ++c)
            if (mask & (1u << c)) reg[c] = it->second[src++];
        }
        rm.constants[p.name] = reg;
      }
      for (const auto& [n, v] : named) rm.constants.emplace(n, v);
      // textures and samplers, by the names the compiled shaders declare
      std::map<std::string, const BinValue*> sampler_defs;
      if (const BinValue* samplers = e.field("samplerValues"))
        for (const BinValue& sv : samplers->items) {
          const BinValue* sn = sv.field("samplerName");
          const BinValue* tn = sn ? sn : sv.field("TextureName");
          if (tn) sampler_defs[tn->str] = &sv;
        }
      auto texture_for = [&](const std::string& declared) -> ComPtr<ID3D11ShaderResourceView> {
        // later patches' shaders declare "<name>__TX" for a material's texture and "<name>_SharedTexture" for the
        // engine's; 14.1's use the bare names
        std::string tname = declared;
        for (const char* suffix : {"__TX", "_SharedTexture"}) {
          const std::string sfx = suffix;
          if (tname.size() > sfx.size() && tname.compare(tname.size() - sfx.size(), sfx.size(), sfx) == 0) tname.resize(tname.size() - sfx.size());
        }
        auto it = sampler_defs.find(tname);
        if (it != sampler_defs.end()) {
          const BinValue* sn = it->second->field("samplerName");
          const BinValue* tp = sn ? it->second->field("TextureName") : it->second->field("texturePath");
          if (tp) return texture(tp->type == BinType::String ? wad_hash(tp->str) : tp->u);
        }
        for (const auto& [n, path] : rm.def->textures)
          if (n == tname && !path.empty()) return texture(wad_hash(dds_path(path)));
        auto eng = engine_textures.find(tname);
        return eng != engine_textures.end() ? eng->second : ComPtr<ID3D11ShaderResourceView>{};
      };
      auto sampler_for = [&](const std::string& sname) {
        // addressU / V / W [meta default 0]: 0 wraps, 1 clamps (the Rift's non-tiling rock spikes set 1) [dedus];
        // filtering: linear, with mips [de măsurat: filterMin / filterMag / filterMip]
        D3D11_SAMPLER_DESC sd{};
        sd.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;
        sd.AddressU = sd.AddressV = sd.AddressW = D3D11_TEXTURE_ADDRESS_WRAP;
        sd.MaxLOD = D3D11_FLOAT32_MAX;
        auto it = sampler_defs.find(sname);
        if (it != sampler_defs.end()) {
          auto mode = [](const BinValue* v) { return num(v, 0) == 1 ? D3D11_TEXTURE_ADDRESS_CLAMP : D3D11_TEXTURE_ADDRESS_WRAP; };
          sd.AddressU = mode(it->second->field("addressU"));
          sd.AddressV = mode(it->second->field("addressV"));
          sd.AddressW = mode(it->second->field("addressW"));
        }
        ComPtr<ID3D11SamplerState> st;
        gpu.device()->CreateSamplerState(&sd, &st);
        return st;
      };
      for (const auto& [tname, slot] : rm.program->ps_textures) {
        auto srv = texture_for(tname);
        if (!srv) missing_textures_.insert(rm.def->path + ": " + tname);
        rm.ps_srvs.emplace_back(slot, srv);
      }
      for (const auto& [tname, slot] : rm.program->vs_textures) {
        auto srv = texture_for(tname);
        if (!srv) missing_textures_.insert(rm.def->path + " (vs): " + tname);
        rm.vs_srvs.emplace_back(slot, srv);
      }
      for (const auto& [sname, slot] : rm.program->ps_samplers) rm.ps_samplers.emplace_back(slot, sampler_for(sname));
      for (const auto& [sname, slot] : rm.program->vs_samplers) rm.vs_samplers.emplace_back(slot, sampler_for(sname));
      // render states from the pass [meta defaults]
      D3D11_BLEND_DESC bd{};
      auto& rt = bd.RenderTarget[0];
      rm.blended = num(pass.field("blendEnable"), 0) != 0;
      rt.BlendEnable = rm.blended;
      rt.SrcBlend = blend_factor(static_cast<uint32_t>(num(pass.field("srcColorBlendFactor"), 1)));
      rt.DestBlend = blend_factor(static_cast<uint32_t>(num(pass.field("dstColorBlendFactor"), 0)));
      rt.SrcBlendAlpha = blend_factor(static_cast<uint32_t>(num(pass.field("srcAlphaBlendFactor"), 1)));
      rt.DestBlendAlpha = blend_factor(static_cast<uint32_t>(num(pass.field("dstAlphaBlendFactor"), 0)));
      rt.BlendOp = rt.BlendOpAlpha = D3D11_BLEND_OP_ADD;  // blendEquation 0 [de măsurat: the other values]
      // writeMask [meta default 31]: bits 1 2 4 8 = R G B A, 16 = depth [dedus: 31 = everything]
      const uint32_t mask = static_cast<uint32_t>(num(pass.field("writeMask"), 31));
      rt.RenderTargetWriteMask = static_cast<UINT8>(mask & 15);
      gpu.device()->CreateBlendState(&bd, &rm.blend);
      D3D11_DEPTH_STENCIL_DESC dd{};
      dd.DepthEnable = num(pass.field("depthEnable"), 1) != 0;
      dd.DepthWriteMask = (mask & 16) ? D3D11_DEPTH_WRITE_MASK_ALL : D3D11_DEPTH_WRITE_MASK_ZERO;
      dd.DepthFunc = compare(static_cast<uint32_t>(num(pass.field("depthCompareFunc"), 3)));
      gpu.device()->CreateDepthStencilState(&dd, &rm.depth);
      D3D11_RASTERIZER_DESC rs{};
      rs.FillMode = D3D11_FILL_SOLID;
      // cullEnable [meta default true], windingToCull [meta default 1] [de măsurat: which winding 1 is]
      const bool cull = num(pass.field("cullEnable"), 1) != 0;
      rs.CullMode = !cull ? D3D11_CULL_NONE : num(pass.field("windingToCull"), 1) == 1 ? D3D11_CULL_BACK : D3D11_CULL_FRONT;
      rs.DepthClipEnable = TRUE;
      gpu.device()->CreateRasterizerState(&rs, &rm.raster);
      rmaterial_of[rm.name] = rmaterials_.size();
      rmaterials_.push_back(std::move(rm));
    }
    const float zeros[16] = {};
    D3D11_BUFFER_DESC zb{};
    zb.ByteWidth = sizeof zeros;
    zb.Usage = D3D11_USAGE_IMMUTABLE;
    zb.BindFlags = D3D11_BIND_VERTEX_BUFFER;
    D3D11_SUBRESOURCE_DATA zd{zeros, 0, 0};
    gpu.device()->CreateBuffer(&zb, &zd, &zero_vb_);
    raw_vb_.resize(geo.vertex_buffers.size());
    raw_ib_.resize(geo.index_buffers.size());
  }

  // ---- geometry of the base layer
  std::map<std::pair<const RiotProgram*, uint32_t>, ComPtr<ID3D11InputLayout>> layouts;
  size_t geo_index = 0;
  for (const GeoModel& m : geo.models) {
    progress(0.8f + 0.2f * static_cast<float>(geo_index++) / static_cast<float>(geo.models.size()));
    if (!(m.layers & 1) || m.vertex_buffers.empty()) continue;
    // Riot's shaders: the raw vertex and index buffers, the model's matrix as WORLD_MATRIX
    std::vector<const GeoSubmesh*> rest;
    size_t model_index = SIZE_MAX;
    for (const GeoSubmesh& s : m.submeshes) {
      auto rmi = rmaterial_of.find(s.material);
      if (rmi == rmaterial_of.end()) {
        rest.push_back(&s);
        continue;
      }
      const RMaterial& rm = rmaterials_[rmi->second];
      if (model_index == SIZE_MAX) {
        RModel rmod;
        columns(m.matrix.data(), rmod.world);
        world_box(m, rmod.bounds);
        for (int k = 0; k < 3; ++k) rmod.center[k] = (m.bbox[static_cast<size_t>(k)] + m.bbox[static_cast<size_t>(k) + 3]) * 0.5f;
        rmod.ib = m.index_buffer;
        rmod.layout = m.layout;
        for (size_t slot = 0; slot < m.vertex_buffers.size(); ++slot) {
          const int32_t vb = m.vertex_buffers[slot];
          rmod.vbs.push_back(vb);
          rmod.strides.push_back(geo.layouts.at(m.layout + slot).stride());
          auto& buf = raw_vb_.at(static_cast<size_t>(vb));
          if (!buf) {
            const auto& bytes = geo.vertex_buffers.at(static_cast<size_t>(vb));
            D3D11_BUFFER_DESC bd{};
            bd.ByteWidth = static_cast<UINT>(bytes.size());
            bd.Usage = D3D11_USAGE_IMMUTABLE;
            bd.BindFlags = D3D11_BIND_VERTEX_BUFFER;
            D3D11_SUBRESOURCE_DATA sd{bytes.data(), 0, 0};
            gpu.device()->CreateBuffer(&bd, &sd, &buf);
          }
        }
        auto& ibuf = raw_ib_.at(m.index_buffer);
        if (!ibuf) {
          const auto& bytes = geo.index_buffers.at(m.index_buffer);
          D3D11_BUFFER_DESC bd{};
          bd.ByteWidth = static_cast<UINT>(bytes.size());
          bd.Usage = D3D11_USAGE_IMMUTABLE;
          bd.BindFlags = D3D11_BIND_INDEX_BUFFER;
          D3D11_SUBRESOURCE_DATA sd{bytes.data(), 0, 0};
          gpu.device()->CreateBuffer(&bd, &sd, &ibuf);
        }
        model_index = rmodels_.size();
        rmodels_.push_back(std::move(rmod));
      }
      // the input layout: each input the vertex shader declares, from the stream that has it (zeros otherwise)
      auto& il = layouts[{rm.program, m.layout * 16u + static_cast<uint32_t>(m.vertex_buffers.size())}];
      if (!il) {
        std::vector<D3D11_INPUT_ELEMENT_DESC> elems;
        for (const RiotProgram::Input& in : rm.program->inputs) {
          D3D11_INPUT_ELEMENT_DESC d{};
          d.SemanticName = in.semantic.c_str();
          d.SemanticIndex = in.index;
          d.InputSlotClass = D3D11_INPUT_PER_VERTEX_DATA;
          GeoElement ge{};
          bool found = false;
          if (element_of(in.semantic, in.index, ge))
            for (size_t slot = 0; slot < m.vertex_buffers.size() && !found; ++slot) {
              const GeoVertexLayout& lay = geo.layouts.at(m.layout + slot);
              const int off = lay.offset_of(ge);
              if (off < 0) continue;
              d.InputSlot = static_cast<UINT>(slot);
              d.AlignedByteOffset = static_cast<UINT>(off);
              d.Format = dxgi(lay.format_of(ge));
              found = true;
            }
          if (!found) {
            d.InputSlot = static_cast<UINT>(m.vertex_buffers.size());
            d.AlignedByteOffset = 0;
            d.Format = DXGI_FORMAT_R32G32B32A32_FLOAT;
          }
          elems.push_back(d);
        }
        gpu.device()->CreateInputLayout(elems.data(), static_cast<UINT>(elems.size()), rm.program->vs_code.data(), rm.program->vs_code.size(), &il);
      }
      if (!il) {
        rest.push_back(&s);
        continue;
      }
      RDraw d;
      d.material = rmi->second;
      d.model = model_index;
      d.index_start = s.index_start;
      d.index_count = s.index_count;
      d.layout = il;
      (rm.blended ? rblended_ : ropaque_).push_back(d);
      triangles_ += s.index_count / 3;
      ++riot_submeshes_;
    }
    if (rest.empty()) continue;

    // the fallback: the model transformed to the world on the CPU
    std::vector<Vertex> verts(m.vertex_count);
    bool has_pos = false, has_uv = false;
    for (size_t slot = 0; slot < m.vertex_buffers.size(); ++slot) {
      const GeoVertexLayout& layout = geo.layouts.at(m.layout + slot);
      const auto& vb = geo.vertex_buffers.at(static_cast<size_t>(m.vertex_buffers[slot]));
      const uint32_t stride = layout.stride();
      const int pos_off = layout.offset_of(GeoElement::Position);
      const int uv_off = layout.offset_of(GeoElement::Uv0);
      const GeoFormat uv_fmt = layout.format_of(GeoElement::Uv0);
      for (uint32_t i = 0; i < m.vertex_count; ++i) {
        const uint8_t* p = vb.data() + static_cast<size_t>(i) * stride;
        if (pos_off >= 0) {
          float xyz[3];
          std::memcpy(xyz, p + pos_off, 12);
          // row vector times League's model matrix (translation in the last row)
          const auto& M = m.matrix;
          verts[i].x = xyz[0] * M[0] + xyz[1] * M[4] + xyz[2] * M[8] + M[12];
          verts[i].y = xyz[0] * M[1] + xyz[1] * M[5] + xyz[2] * M[9] + M[13];
          verts[i].z = xyz[0] * M[2] + xyz[1] * M[6] + xyz[2] * M[10] + M[14];
          has_pos = true;
        }
        if (uv_off >= 0) {
          if (uv_fmt == GeoFormat::F2) {
            std::memcpy(&verts[i].u, p + uv_off, 8);
          } else if (uv_fmt == GeoFormat::H2) {
            uint16_t h[2];
            std::memcpy(h, p + uv_off, 4);
            verts[i].u = half_to_float(h[0]);
            verts[i].v = half_to_float(h[1]);
          }
          has_uv = true;
        }
      }
    }
    if (!has_pos || !has_uv) continue;

    const auto& ibytes = geo.index_buffers.at(m.index_buffer);
    std::vector<uint16_t> indices(ibytes.size() / 2);
    std::memcpy(indices.data(), ibytes.data(), indices.size() * 2);

    Mesh mesh;
    world_box(m, mesh.bounds);
    D3D11_BUFFER_DESC bd{};
    bd.Usage = D3D11_USAGE_IMMUTABLE;
    bd.BindFlags = D3D11_BIND_VERTEX_BUFFER;
    bd.ByteWidth = static_cast<UINT>(verts.size() * sizeof(Vertex));
    D3D11_SUBRESOURCE_DATA sd{verts.data(), 0, 0};
    gpu.device()->CreateBuffer(&bd, &sd, &mesh.vb);
    bd.BindFlags = D3D11_BIND_INDEX_BUFFER;
    bd.ByteWidth = static_cast<UINT>(indices.size() * 2);
    sd.pSysMem = indices.data();
    gpu.device()->CreateBuffer(&bd, &sd, &mesh.ib);
    meshes_.push_back(mesh);

    for (const GeoSubmesh* sp : rest) {
      const GeoSubmesh& s = *sp;
      auto it = materials.find(s.material);
      if (it == materials.end() || !it->second.diffuse) continue;
      Draw d;
      d.material = it->second;
      d.index_start = s.index_start;
      d.index_count = s.index_count;
      d.mesh = meshes_.size() - 1;
      auto& tex = textures[d.material.diffuse];
      if (!tex)
        if (auto bytes = wad.read_hash(d.material.diffuse)) {
          try {
            tex = gpu.texture(read_texture(*bytes));
          } catch (const std::exception&) {
          }
        }
      if (!tex) continue;
      d.texture = tex;
      (d.material.blend ? blended_ : opaque_).push_back(d);
      triangles_ += s.index_count / 3;
      ++fallback_submeshes_;
    }
  }

  // ---- TERRAIN_XFORM: the grass tint texture (a top view of the whole map) spans the MapContainer's boundsMin ..
  // boundsMax [meta: boundsMin default 0,0]. Checked on the data: its brush patches line up with the navigation grid's
  // brush cells as well as any fitted placement does (research: score 25.9 against 26.4 for the best free fit).
  for (const BinEntry& e : mats.entries()) {
    const BinValue* mx = e.field("boundsMax");
    if (!mx || !e.field("mapPath")) continue;
    const BinValue* mn = e.field("boundsMin");
    const float x0 = mn ? static_cast<float>(mn->num[0]) : 0.f, z0 = mn ? static_cast<float>(mn->num[1]) : 0.f;
    const float sx = static_cast<float>(mx->num[0]) - x0, sz = static_cast<float>(mx->num[1]) - z0;
    if (sx > 0 && sz > 0) terrain_xform_[0] = 1.f / sx, terrain_xform_[1] = 1.f / sz, terrain_xform_[2] = -x0 / sx, terrain_xform_[3] = -z0 / sz;
  }
  map_constants_["TERRAIN_XFORM"] = {terrain_xform_[0], terrain_xform_[1], terrain_xform_[2], terrain_xform_[3]};

  // ---- the navigation grid this geometry's MapContainer names (MapNavGrid NavGridPath)
  if (auto bytes = read_map_navgrid(wad, levels_wad)) {
    try {
      nav_ = std::make_unique<NavGrid>(*bytes);
    } catch (const std::exception&) {
    }
  }

  // ---- the light characters get. Summoner's Rift has no light grid: its MapBakeProperties sets lightGridSize but no
  // lightGridFileName, so characters follow the map's sun (MapSunProperties): sky above, ground below, horizon around,
  // times skyLightScale. Base_SRX sets all three to white at scale 1.
  for (const BinEntry& e : mats.entries()) {
    const BinValue* components = e.field("components");
    if (!components) continue;
    for (const BinValue& c : components->items) {
      if (c.cls != fnv1a("MapSunProperties")) continue;
      auto rgb = [&c](const char* name, float out[3]) {
        if (const BinValue* v = c.field(name))
          for (int k = 0; k < 3; ++k) out[k] = static_cast<float>(v->num[static_cast<size_t>(k)]);
      };
      float sky[3] = {1, 1, 1}, horizon[3] = {1, 1, 1}, ground[3] = {1, 1, 1};
      rgb("skyLightColor", sky), rgb("horizonColor", horizon), rgb("groundColor", ground);
      // the per-frame constants Riot's shaders read, from the same component [meta defaults]
      auto vec = [&c](const char* name, std::array<float, 4> dflt) {
        if (const BinValue* v = c.field(name))
          for (size_t k = 0; k < 4; ++k) dflt[k] = static_cast<float>(v->num[k]);
        return dflt;
      };
      const auto fog = vec("fogColor", {0.2f, 0.2f, 0.4f, 1});
      const auto fog_alt = vec("fogAlternateColor", {0.1f, 0.1f, 0.2f, 1});
      const auto fog_se = vec("fogStartAndEnd", {0, -2000, 0, 0});
      map_constants_["ENV_FOG_COLOR"] = fog;
      map_constants_["ENV_FOG_ALT_COLOR"] = fog_alt;
      // ENV_FOG_START_END_SCALE_EMISSIVE_REMAP: start, end, [de măsurat: scale], fogEmissiveRemap
      map_constants_["ENV_FOG_START_END_SCALE_EMISSIVE_REMAP"] = {fog_se[0], fog_se[1], 0, static_cast<float>(num(c.field("fogEmissiveRemap"), 1.9))};
      const auto sun = vec("sunDirection", {0, 0.707f, 0.707f, 0});
      map_constants_["SUN_LIGHT_DIRECTION"] = sun;
      map_constants_["SUN_LIGHT_DIRECTION_FOR_SPEC"] = sun;  // OverrideSunSpecDirection unset
      map_constants_["SUN_LIGHT_COLOR"] = vec("sunColor", {1, 1, 1, 1});
      map_constants_["LIGHT_MAP_COLOR_SCALE"] = {static_cast<float>(num(c.field("lightMapColorScale"), 1)), 0, 0, 0};
      map_constants_["HDR_ENV_DIFFUSE_SCALE"] = {static_cast<float>(num(c.field("HdrEnvDiffuseScale"), 3)), 0, 0, 0};
      const BinValue* sc = c.field("skyLightScale");
      const float scale = sc ? static_cast<float>(sc->number()) : 1.f;
      for (int k = 0; k < 3; ++k) {
        ambient_cube_[2][k] = sky[k] * scale;
        ambient_cube_[3][k] = ground[k] * scale;
        ambient_cube_[0][k] = ambient_cube_[1][k] = ambient_cube_[4][k] = ambient_cube_[5][k] = horizon[k] * scale;
      }
      sun_ok_ = true;
    }
  }

  // the Rift before any elemental change: TransitionFactorAndDirection = (0, 1). With it the srx_blend shaders discard
  // nothing and draw their plain look; (x, 0) grows the elemental terrain in circles of x * 8500 .. 15000 units
  // [dedus din shader-ele 14.1: research/shaders141/srx_blend_*]
  map_constants_["TransitionFactorAndDirection"] = {0, 1, 0, 0};

  // ---- pipeline state
  ComPtr<ID3DBlob> code;
  if (!gpu.shader(kShader, "map", vs_, ps_, &code)) return false;
  const D3D11_INPUT_ELEMENT_DESC il[] = {
      {"POSITION", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 0, D3D11_INPUT_PER_VERTEX_DATA, 0},
      {"TEXCOORD", 0, DXGI_FORMAT_R32G32_FLOAT, 0, 12, D3D11_INPUT_PER_VERTEX_DATA, 0},
  };
  gpu.device()->CreateInputLayout(il, 2, code->GetBufferPointer(), code->GetBufferSize(), &layout_);
  D3D11_BUFFER_DESC cbd{};
  cbd.ByteWidth = sizeof(Cb);
  cbd.Usage = D3D11_USAGE_DYNAMIC;
  cbd.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
  cbd.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
  gpu.device()->CreateBuffer(&cbd, nullptr, &cb_);
  D3D11_SAMPLER_DESC smp{};
  smp.Filter = D3D11_FILTER_ANISOTROPIC;
  smp.MaxAnisotropy = 4;
  smp.AddressU = smp.AddressV = smp.AddressW = D3D11_TEXTURE_ADDRESS_WRAP;
  smp.MaxLOD = D3D11_FLOAT32_MAX;
  gpu.device()->CreateSamplerState(&smp, &sampler_);
  smp.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;
  smp.AddressU = smp.AddressV = smp.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
  gpu.device()->CreateSamplerState(&smp, &clamp_);
  // Summoner's Rift's grass tint (MapSkin mGrassTintTexture of the Rift's skins); TERRAIN_XFORM maps the world onto it.
  if (auto bytes = wad.read("assets/maps/info/map11/grasstint_srx.tex")) {
    try {
      grass_tint_ = gpu.texture(read_texture(*bytes));
    } catch (const std::exception&) {
    }
  }
  D3D11_BLEND_DESC bl{};
  bl.RenderTarget[0].BlendEnable = TRUE;
  bl.RenderTarget[0].SrcBlend = D3D11_BLEND_ONE;
  bl.RenderTarget[0].DestBlend = D3D11_BLEND_INV_SRC_ALPHA;
  bl.RenderTarget[0].BlendOp = D3D11_BLEND_OP_ADD;
  bl.RenderTarget[0].SrcBlendAlpha = D3D11_BLEND_ONE;
  bl.RenderTarget[0].DestBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;
  bl.RenderTarget[0].BlendOpAlpha = D3D11_BLEND_OP_ADD;
  bl.RenderTarget[0].RenderTargetWriteMask = D3D11_COLOR_WRITE_ENABLE_ALL;
  gpu.device()->CreateBlendState(&bl, &premultiplied_);
  D3D11_RASTERIZER_DESC rs{};
  rs.FillMode = D3D11_FILL_SOLID;
  rs.CullMode = D3D11_CULL_NONE;
  rs.DepthClipEnable = TRUE;
  gpu.device()->CreateRasterizerState(&rs, &no_cull_);
  D3D11_DEPTH_STENCIL_DESC ds{};
  ds.DepthEnable = TRUE;
  ds.DepthWriteMask = D3D11_DEPTH_WRITE_MASK_ZERO;
  ds.DepthFunc = D3D11_COMPARISON_LESS_EQUAL;
  gpu.device()->CreateDepthStencilState(&ds, &depth_read_);
  return true;
}

bool MapView::grass_tint_at(float x, float z, float out[3]) const {
  if (grass_tint_rgba_.empty()) return false;
  // uv = xz * TERRAIN_XFORM.xy + TERRAIN_XFORM.zw, v flipped (the texture's first row is the map's far edge), bilinear
  // [măsurat: the TINT_COLOR of 85 brush draws of a 13.3 replay frame against the texture: most to 1/255]
  const float u = x * terrain_xform_[0] + terrain_xform_[2], v = 1.f - (z * terrain_xform_[1] + terrain_xform_[3]);
  const float fx = u * static_cast<float>(grass_tint_w_) - 0.5f, fy = v * static_cast<float>(grass_tint_h_) - 0.5f;
  const int x0 = static_cast<int>(std::floor(fx)), y0 = static_cast<int>(std::floor(fy));
  const float ax = fx - static_cast<float>(x0), ay = fy - static_cast<float>(y0);
  auto px = [&](int px_x, int px_y, int k) {
    px_x = std::clamp(px_x, 0, static_cast<int>(grass_tint_w_) - 1), px_y = std::clamp(px_y, 0, static_cast<int>(grass_tint_h_) - 1);
    return static_cast<float>(grass_tint_rgba_[(static_cast<size_t>(px_y) * grass_tint_w_ + static_cast<size_t>(px_x)) * 4 + static_cast<size_t>(k)]) / 255.f;
  };
  for (int k = 0; k < 3; ++k)
    out[k] = (px(x0, y0, k) * (1 - ax) + px(x0 + 1, y0, k) * ax) * (1 - ay) + (px(x0, y0 + 1, k) * (1 - ax) + px(x0 + 1, y0 + 1, k) * ax) * ay;
  return true;
}

float MapView::ground_height(float x, float z) const {
  return nav_ ? nav_->height(x, z) : 0.f;
}

bool MapView::constant(const std::string& name, uint8_t* out, uint32_t size, const RMaterial& m, const RModel& model) {
  auto put = [&](const float* v, uint32_t n) {
    std::memcpy(out, v, std::min<uint32_t>(size, n * 4));
    return true;
  };
  if (name == "WORLD_MATRIX") return put(model.world, 16);
  if (name == "MESH_CENTER") return put(model.center, 3);
  if (name == "VIEW_PROJECTION_MATRIX") {
    float vp[16];
    columns(&view_proj_.m[0][0], vp);
    return put(vp, 16);
  }
  if (name == "vCamera") {
    const float e[3] = {eye_.x, eye_.y, eye_.z};
    return put(e, 3);
  }
  if (name == "TIME") {
    const float t[4] = {time_, 0, 0, 0};  // [de măsurat: TIME.yzw]
    return put(t, 4);
  }
  auto it = m.constants.find(name);
  if (it != m.constants.end()) return put(it->second.data(), 4);
  auto mc = map_constants_.find(name);
  if (mc != map_constants_.end()) return put(mc->second.data(), 4);
  missing_constants_.insert(name);
  return false;
}

std::string MapView::report() const {
  std::ostringstream o;
  o << "submeshes: " << riot_submeshes_ << " with Riot's shaders, " << fallback_submeshes_ << " with the fallback\n";
  for (const auto& s : missing_shaders_) o << "no compiled shader: " << s << "\n";
  for (const auto& s : missing_constants_) o << "constant not in the data (left 0): " << s << "\n";
  for (const auto& s : missing_textures_) o << "texture not in the data (unbound): " << s << "\n";
  return o.str();
}

void MapView::draw(Gpu& gpu, const float4x4& view_proj, float3 eye, float time) {
  ID3D11DeviceContext* c = gpu.ctx();
  view_proj_ = view_proj, eye_ = eye, time_ = time;
  auto fallback_state = [&]() {
    c->IASetInputLayout(layout_.Get());
    c->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    c->VSSetShader(vs_.Get(), nullptr, 0);
    c->PSSetShader(ps_.Get(), nullptr, 0);
    c->VSSetConstantBuffers(0, 1, cb_.GetAddressOf());
    c->PSSetConstantBuffers(0, 1, cb_.GetAddressOf());
    ID3D11SamplerState* samplers[2] = {sampler_.Get(), clamp_.Get()};
    c->PSSetSamplers(0, 2, samplers);
    c->RSSetState(no_cull_.Get());
  };
  auto riot = [&](const std::vector<RDraw>& draws) {
    c->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    for (const RDraw& d : draws) {
      const RMaterial& m = rmaterials_[d.material];
      const RModel& model = rmodels_[d.model];
      if (!visible(model.bounds, view_proj)) continue;
      c->IASetInputLayout(d.layout.Get());
      c->VSSetShader(m.program->vs.Get(), nullptr, 0);
      c->PSSetShader(m.program->ps.Get(), nullptr, 0);
      m.program->bind_constants(c, [&](const std::string& n, uint8_t* out, uint32_t size) { return constant(n, out, size, m, model); });
      for (const auto& [slot, srv] : m.ps_srvs) c->PSSetShaderResources(static_cast<UINT>(slot), 1, srv.GetAddressOf());
      for (const auto& [slot, srv] : m.vs_srvs) c->VSSetShaderResources(static_cast<UINT>(slot), 1, srv.GetAddressOf());
      for (const auto& [slot, st] : m.ps_samplers) c->PSSetSamplers(static_cast<UINT>(slot), 1, st.GetAddressOf());
      for (const auto& [slot, st] : m.vs_samplers) c->VSSetSamplers(static_cast<UINT>(slot), 1, st.GetAddressOf());
      c->OMSetBlendState(m.blend.Get(), nullptr, 0xFFFFFFFF);
      c->OMSetDepthStencilState(m.depth.Get(), 0);
      c->RSSetState(m.raster.Get());
      ID3D11Buffer* vbs[8] = {};
      UINT strides[8] = {}, offsets[8] = {};
      size_t n = 0;
      for (; n < model.vbs.size() && n < 7; ++n) vbs[n] = raw_vb_[static_cast<size_t>(model.vbs[n])].Get(), strides[n] = model.strides[n];
      vbs[n] = zero_vb_.Get(), strides[n] = 0;  // inputs the mesh lacks
      c->IASetVertexBuffers(0, static_cast<UINT>(n + 1), vbs, strides, offsets);
      c->IASetIndexBuffer(raw_ib_[model.ib].Get(), DXGI_FORMAT_R16_UINT, 0);
      c->DrawIndexed(d.index_count, d.index_start, 0);
    }
  };
  riot(ropaque_);
  c->IASetInputLayout(layout_.Get());
  c->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
  c->VSSetShader(vs_.Get(), nullptr, 0);
  c->PSSetShader(ps_.Get(), nullptr, 0);
  c->VSSetConstantBuffers(0, 1, cb_.GetAddressOf());
  c->PSSetConstantBuffers(0, 1, cb_.GetAddressOf());
  ID3D11SamplerState* samplers[2] = {sampler_.Get(), clamp_.Get()};
  c->PSSetSamplers(0, 2, samplers);
  c->RSSetState(no_cull_.Get());

  auto run = [&](const std::vector<Draw>& draws, bool blended) {
    fallback_state();
    c->OMSetBlendState(blended ? premultiplied_.Get() : nullptr, nullptr, 0xFFFFFFFF);
    c->OMSetDepthStencilState(blended ? depth_read_.Get() : nullptr, 0);
    for (const Draw& d : draws) {
      if (!visible(meshes_[d.mesh].bounds, view_proj)) continue;
      D3D11_MAPPED_SUBRESOURCE map{};
      if (FAILED(c->Map(cb_.Get(), 0, D3D11_MAP_WRITE_DISCARD, 0, &map))) continue;
      Cb cb{};
      std::memcpy(cb.view_proj, view_proj.m, sizeof cb.view_proj);
      std::memcpy(cb.tint, d.material.tint, sizeof cb.tint);
      cb.params[0] = d.material.alpha_test;
      cb.params[3] = d.material.deform ? 1.f : 0.f;
      std::memcpy(cb.terrain_xform, terrain_xform_, sizeof cb.terrain_xform);
      std::memcpy(map.pData, &cb, sizeof cb);
      c->Unmap(cb_.Get(), 0);
      const Mesh& m = meshes_[d.mesh];
      const UINT stride = sizeof(Vertex), offset = 0;
      c->IASetVertexBuffers(0, 1, m.vb.GetAddressOf(), &stride, &offset);
      c->IASetIndexBuffer(m.ib.Get(), DXGI_FORMAT_R16_UINT, 0);
      ID3D11ShaderResourceView* srvs[2] = {d.texture.Get(), grass_tint_.Get()};
      c->PSSetShaderResources(0, 2, srvs);
      c->DrawIndexed(d.index_count, d.index_start, 0);
    }
  };
  run(opaque_, false);
  riot(rblended_);
  run(blended_, true);
  c->OMSetBlendState(nullptr, nullptr, 0xFFFFFFFF);
  c->OMSetDepthStencilState(nullptr, 0);
  c->RSSetState(nullptr);
}

}  // namespace ba
