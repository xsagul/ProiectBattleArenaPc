#include "RiotShader.h"

#include <d3d11shader.h>
#include <d3dcompiler.h>

#include <cstring>

#include "ba/Hash.h"

namespace ba {

namespace {

std::string lower(std::string s) {
  for (char& c : s) c = static_cast<char>(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
  return s;
}

/** Constant buffers, resources and inputs one compiled stage declares. */
void reflect(const std::vector<uint8_t>& code, char stage, RiotProgram& p) {
  ComPtr<ID3D11ShaderReflection> r;
  if (FAILED(D3DReflect(code.data(), code.size(), IID_ID3D11ShaderReflection, reinterpret_cast<void**>(r.GetAddressOf())))) return;
  D3D11_SHADER_DESC sd{};
  r->GetDesc(&sd);
  std::map<std::string, int> cb_slots;
  for (UINT i = 0; i < sd.BoundResources; ++i) {
    D3D11_SHADER_INPUT_BIND_DESC b{};
    r->GetResourceBindingDesc(i, &b);
    const int slot = static_cast<int>(b.BindPoint);
    if (b.Type == D3D_SIT_CBUFFER) cb_slots[b.Name] = slot;
    else if (b.Type == D3D_SIT_TEXTURE) (stage == 'v' ? p.vs_textures : p.ps_textures).emplace_back(b.Name, slot);
    else if (b.Type == D3D_SIT_SAMPLER) (stage == 'v' ? p.vs_samplers : p.ps_samplers).emplace_back(b.Name, slot);
  }
  for (UINT i = 0; i < sd.ConstantBuffers; ++i) {
    ID3D11ShaderReflectionConstantBuffer* cb = r->GetConstantBufferByIndex(i);
    D3D11_SHADER_BUFFER_DESC bd{};
    cb->GetDesc(&bd);
    RiotProgram::CBuffer c;
    c.name = bd.Name;
    c.size = bd.Size;
    auto slot = cb_slots.find(c.name);
    if (slot == cb_slots.end()) continue;
    (stage == 'v' ? c.vs_slot : c.ps_slot) = slot->second;
    for (UINT v = 0; v < bd.Variables; ++v) {
      D3D11_SHADER_VARIABLE_DESC vd{};
      cb->GetVariableByIndex(v)->GetDesc(&vd);
      c.vars.push_back({vd.Name, vd.StartOffset, vd.Size, (vd.uFlags & D3D_SVF_USED) != 0});
    }
    p.cbuffers.push_back(std::move(c));
  }
  if (stage == 'v')
    for (UINT i = 0; i < sd.InputParameters; ++i) {
      D3D11_SIGNATURE_PARAMETER_DESC in{};
      r->GetInputParameterDesc(i, &in);
      p.inputs.push_back({in.SemanticName, in.SemanticIndex});
    }
}

}  // namespace

bool ShaderLibrary::load(const Wad& wad) {
  auto bytes = wad.read("data/shaders/shaders.bin");
  if (!bytes) return false;
  const PropertyBin bin(*bytes);
  for (const BinEntry& e : bin.entries()) {
    const BinValue* path = e.field("objectPath");
    if (!path) continue;
    ShaderDef d;
    d.path = lower(path->str);
    if (const BinValue* params = e.field("parameters"))
      for (const BinValue& pv : params->items) {
        ShaderDef::Param p;
        if (const BinValue* n = pv.field("name")) p.name = n->str;
        if (const BinValue* v = pv.field("data"))
          for (int k = 0; k < 4; ++k) p.data[k] = static_cast<float>(v->num[static_cast<size_t>(k)]);
        if (const BinValue* l = pv.field("logicalParameters"))
          for (const BinValue& lp : l->items) {
            const BinValue* n = lp.field("name");
            const BinValue* f = lp.field("fields");
            if (n) p.logical.emplace_back(n->str, f ? static_cast<uint32_t>(f->number()) : 0u);
          }
        d.params.push_back(std::move(p));
      }
    if (const BinValue* sw = e.field("staticSwitches"))
      for (const BinValue& s : sw->items) {
        const BinValue* n = s.field("name");
        const BinValue* on = s.field("onByDefault");  // [meta default false]
        if (n) d.switches.emplace_back(n->str, on && on->number() != 0);
      }
    if (const BinValue* tx = e.field("textures"))
      for (const BinValue& t : tx->items) {
        const BinValue* n = t.field("name");
        const BinValue* p = t.field("defaultTexturePath");
        if (n) d.textures.emplace_back(n->str, p && p->type == BinType::String ? p->str : std::string());
      }
    if (const BinValue* fd = e.field("featureDefines"))
      for (const auto& [k, v] : fd->pairs) d.feature_defines[k.str] = v.str;
    defs_[e.name] = std::move(d);
  }
  return !defs_.empty();
}

const ShaderDef* ShaderLibrary::find(uint32_t link) const {
  auto it = defs_.find(link);
  return it == defs_.end() ? nullptr : &it->second;
}

bool RiotProgram::create(Gpu& gpu, const std::vector<uint8_t>& vs_blob, const std::vector<uint8_t>& ps_blob) {
  if (FAILED(gpu.device()->CreateVertexShader(vs_blob.data(), vs_blob.size(), nullptr, &vs))) return false;
  if (FAILED(gpu.device()->CreatePixelShader(ps_blob.data(), ps_blob.size(), nullptr, &ps))) return false;
  vs_code = vs_blob;
  reflect(vs_blob, 'v', *this);
  reflect(ps_blob, 'p', *this);
  for (CBuffer& c : cbuffers) {
    D3D11_BUFFER_DESC bd{};
    bd.ByteWidth = (c.size + 15) / 16 * 16;
    bd.Usage = D3D11_USAGE_DYNAMIC;
    bd.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
    bd.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
    if (FAILED(gpu.device()->CreateBuffer(&bd, nullptr, &c.buffer))) return false;
  }
  return true;
}

void RiotProgram::bind_constants(ID3D11DeviceContext* ctx, const std::function<bool(const std::string&, uint8_t*, uint32_t)>& fill) {
  std::vector<uint8_t> bytes;
  for (CBuffer& c : cbuffers) {
    bytes.assign((c.size + 15) / 16 * 16, 0);
    for (const Var& v : c.vars)
      if (v.used && v.offset + v.size <= bytes.size()) fill(v.name, bytes.data() + v.offset, v.size);
    if (bytes != c.last) {
      D3D11_MAPPED_SUBRESOURCE map{};
      if (SUCCEEDED(ctx->Map(c.buffer.Get(), 0, D3D11_MAP_WRITE_DISCARD, 0, &map))) {
        std::memcpy(map.pData, bytes.data(), bytes.size());
        ctx->Unmap(c.buffer.Get(), 0);
        c.last = bytes;
      }
    }
    if (c.vs_slot >= 0) ctx->VSSetConstantBuffers(static_cast<UINT>(c.vs_slot), 1, c.buffer.GetAddressOf());
    if (c.ps_slot >= 0) ctx->PSSetConstantBuffers(static_cast<UINT>(c.ps_slot), 1, c.buffer.GetAddressOf());
  }
}

}  // namespace ba
