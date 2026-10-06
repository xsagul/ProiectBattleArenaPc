#pragma once
// Riot's own shaders, run as the game ships them: a material (StaticMaterialDef) names a shader definition
// (CustomShaderDef in data/shaders/shaders.bin of Shaders.wad); the definition gives the shader's parameters
// (physical float4 registers ParameterN with the material's named parameters packed into their components),
// static switches, textures and feature defines; the compiled permutation for the resulting defines comes from the
// ShaderCache (ba/ShaderCache.h). Constant buffers, textures and vertex inputs are bound by the names and semantics the
// compiled shaders declare (D3DReflect), so nothing of the shader's math is rewritten here.

#include <d3d11.h>

#include <functional>
#include <map>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

#include "Gpu.h"
#include "ba/PropertyBin.h"
#include "ba/ShaderCache.h"

namespace ba {

/** One shader definition of shaders.bin. */
struct ShaderDef {
  std::string path;  // "shaders/staticmesh/srx_blend_ocean" (lower case: the ShaderCache's names)
  struct Param {
    std::string name;  // Parameter0 ..
    float data[4] = {0, 0, 0, 0};
    std::vector<std::pair<std::string, uint32_t>> logical;  // material parameter name, component mask (1 x, 2 y, 4 z, 8 w)
  };
  std::vector<Param> params;
  std::vector<std::pair<std::string, bool>> switches;  // static switch, on by default
  std::vector<std::pair<std::string, std::string>> textures;  // texture name, default texture path
  Defines feature_defines;
};

class ShaderLibrary {
 public:
  /** Reads data/shaders/shaders.bin from the Shaders wad. */
  bool load(const Wad& shaders_wad);
  /** The definition a material's pass links to (its `shader` field: the definition entry's name hash). */
  const ShaderDef* find(uint32_t link) const;

 private:
  std::unordered_map<uint32_t, ShaderDef> defs_;
};

/** A compiled VS + PS pair and what they declare. */
class RiotProgram {
 public:
  bool create(Gpu& gpu, const std::vector<uint8_t>& vs, const std::vector<uint8_t>& ps);

  struct Var {
    std::string name;
    uint32_t offset = 0, size = 0;
    bool used = false;
  };
  struct CBuffer {
    std::string name;
    int vs_slot = -1, ps_slot = -1;
    uint32_t size = 0;
    std::vector<Var> vars;
    ComPtr<ID3D11Buffer> buffer;
    std::vector<uint8_t> last;  // what the buffer holds: uploads only happen when the content changes
  };
  struct Input {
    std::string semantic;
    uint32_t index = 0;
  };
  std::vector<CBuffer> cbuffers;
  std::vector<std::pair<std::string, int>> ps_textures, ps_samplers, vs_textures, vs_samplers;
  std::vector<Input> inputs;
  std::vector<uint8_t> vs_code;
  ComPtr<ID3D11VertexShader> vs;
  ComPtr<ID3D11PixelShader> ps;

  /** Fills every used constant by name (`fill` writes up to `size` bytes; returns false for names it does not know,
   *  which stay 0) and binds the buffers. */
  void bind_constants(ID3D11DeviceContext* ctx, const std::function<bool(const std::string&, uint8_t*, uint32_t)>& fill);
};

}  // namespace ba
