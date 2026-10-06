#pragma once
// Summoner's Rift as League draws its static geometry: every model of the base layer of base_srx.mapgeo, each submesh
// with its StaticMaterialDef from base_srx.materials.bin.
//
// When the install has the shader library (Shaders.wad) and the compiled shaders (ShaderCache.dx11.wad), each material
// is drawn with Riot's own compiled shader for it (RiotShader.h): the permutation its defines select, its parameters,
// textures and render states from the material, the per-frame values from the map's data (MapContainer). Otherwise, or
// for a material whose shader cannot be found, the fallback below reproduces defaultenv_flat_alphatest / vertexdeform.

#include <array>
#include <cstdint>
#include <cstring>
#include <functional>
#include <map>
#include <memory>
#include <set>
#include <string>
#include <unordered_map>
#include <vector>

#include "Gpu.h"
#include "Math.h"
#include "RiotShader.h"
#include "ba/NavGrid.h"
#include "ba/PropertyBin.h"
#include "ba/Wad.h"

namespace ba {

class MapView {
 public:
  /** `shaders_wad` (Shaders/Shaders.wad.client) and `cache_wad` (ShaderCache.dx11.wad.client) enable Riot's shaders. */
  /** The game's environment quality: low compiles every map shader with LOW_QUALITY_MODE (14.1's brush then stands
   *  still: its low permutations never read TIME). Set before load. */
  bool low_quality = true;
  /** Called while `load` works, with the part done (0..1): the loading screen's progress. */
  std::function<void(float)> on_progress;
  bool load(Gpu& gpu, const Wad& map_wad, const Wad* shaders_wad = nullptr, const Wad* cache_wad = nullptr, const Wad* levels_wad = nullptr);
  /** Whether a map visibility controller (an entry of the materials bin) shows what it controls in a plain match: flag
   *  controllers say DefaultVisible (the elemental terrains, the Baron pit's other forms say 0), mutator controllers
   *  need an event's mutator (none is on), child controllers combine their parents (ParentMode 1 taken as "any",
   *  others as "all": the modes are not documented). An unknown controller shows. */
  static bool controller_shown(const PropertyBin& bin, uint32_t controller, int depth = 0);
  /** How many of the base layer's models their visibility controller hid. */
  size_t hidden_models() const { return hidden_models_; }
  void draw(Gpu& gpu, const float4x4& view_proj, float3 eye, float time);
  /** Height of the ground at (x, z): the navigation grid's height samples, what the game stands units on. */
  float ground_height(float x, float z) const;
  /** The map's grass tint at (x, z): the "Default" MapSkin's mGrassTintTexture looked up through TERRAIN_XFORM, as
   *  the brush shaders do. False when the map has none. */
  bool grass_tint_at(float x, float z, float out[3]) const;
  size_t triangles() const { return triangles_; }
  const NavGrid* nav() const { return nav_.get(); }
  /** The ambient cube characters are lit by (+X -X +Y -Y +Z -Z): the map's sun colours (false when it sets none). */
  bool ambient_cube(float out[6][3]) const {
    std::memcpy(out, ambient_cube_, sizeof ambient_cube_);
    return sun_ok_;
  }
  /** What the Riot shaders asked for that the data does not give (constants and textures left at zero), and how many
   *  submeshes each path draws: for the provenance notes. */
  std::string report() const;

 private:
  // ---- fallback pipeline (defaultenv_flat_alphatest / vertexdeform reproduced)
  struct Material {
    uint64_t diffuse = 0;  // path hash of the texture inside the wad
    float tint[4] = {0.5f, 0.5f, 0.5f, 0};
    float alpha_test = 0;
    bool deform = false;  // the brush's VertexDeform shader
    bool blend = false;
  };
  struct Draw {
    ComPtr<ID3D11ShaderResourceView> texture;
    Material material;
    uint32_t index_start = 0, index_count = 0;
    size_t mesh = 0;
  };
  struct Mesh {
    ComPtr<ID3D11Buffer> vb, ib;
    float bounds[6] = {0, 0, 0, 0, 0, 0};  // world box: min xyz, max xyz
  };

  // ---- Riot pipeline
  struct RMaterial {
    std::string name;
    const ShaderDef* def = nullptr;
    RiotProgram* program = nullptr;
    std::map<std::string, std::array<float, 4>> constants;  // ParameterN and named values, packed at load
    std::vector<std::pair<int, ComPtr<ID3D11ShaderResourceView>>> ps_srvs, vs_srvs;
    std::vector<std::pair<int, ComPtr<ID3D11SamplerState>>> ps_samplers, vs_samplers;
    ComPtr<ID3D11BlendState> blend;
    ComPtr<ID3D11DepthStencilState> depth;
    ComPtr<ID3D11RasterizerState> raster;
    bool blended = false;
  };
  struct RModel {
    float center[4] = {0, 0, 0, 0};  // MESH_CENTER: the middle of the model's bounding box
    float world[16];  // the model's matrix as a constant: register i = column i of League's row-vector matrix
    std::vector<int32_t> vbs;
    std::vector<uint32_t> strides;
    uint32_t ib = 0, layout = 0;
    float bounds[6] = {0, 0, 0, 0, 0, 0};  // world box: min xyz, max xyz
  };
  struct RDraw {
    size_t material = 0, model = 0;
    uint32_t index_start = 0, index_count = 0;
    ComPtr<ID3D11InputLayout> layout;
  };
  bool constant(const std::string& name, uint8_t* out, uint32_t size, const RMaterial& m, const RModel& model);

  std::vector<Mesh> meshes_;
  std::vector<Draw> opaque_, blended_;
  ComPtr<ID3D11VertexShader> vs_;
  ComPtr<ID3D11PixelShader> ps_;
  ComPtr<ID3D11InputLayout> layout_;
  ComPtr<ID3D11Buffer> cb_;
  ComPtr<ID3D11SamplerState> sampler_, clamp_;
  ComPtr<ID3D11ShaderResourceView> grass_tint_;
  std::vector<uint8_t> grass_tint_rgba_;  // the Default skin's grass tint, mip 0
  uint32_t grass_tint_w_ = 0, grass_tint_h_ = 0;
  float terrain_xform_[4] = {1.f / 15000.f, 1.f / 15000.f, 0, 0};  // set from MapContainer bounds at load
  ComPtr<ID3D11BlendState> premultiplied_;
  ComPtr<ID3D11RasterizerState> no_cull_;
  ComPtr<ID3D11DepthStencilState> depth_read_;
  size_t triangles_ = 0;
  size_t hidden_models_ = 0;
  std::unique_ptr<NavGrid> nav_;
  float ambient_cube_[6][3] = {{1, 1, 1}, {1, 1, 1}, {1, 1, 1}, {1, 1, 1}, {1, 1, 1}, {1, 1, 1}};
  bool sun_ok_ = false;

  ShaderLibrary library_;
  std::vector<std::unique_ptr<RiotProgram>> programs_;
  std::vector<RMaterial> rmaterials_;
  std::vector<RModel> rmodels_;
  std::vector<RDraw> ropaque_, rblended_;
  std::vector<ComPtr<ID3D11Buffer>> raw_vb_, raw_ib_;
  ComPtr<ID3D11Buffer> zero_vb_;  // vertex inputs a mesh lacks read zeros from here
  // per frame, and the map's own values (MapSunProperties)
  float4x4 view_proj_;
  float3 eye_;
  float time_ = 0;
  std::map<std::string, std::array<float, 4>> map_constants_;
  std::set<std::string> missing_constants_, missing_textures_, missing_shaders_;
  size_t riot_submeshes_ = 0, fallback_submeshes_ = 0;
};

}  // namespace ba
