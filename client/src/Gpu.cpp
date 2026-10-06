#include "Gpu.h"

#include <d3dcompiler.h>

#include <algorithm>
#include <cstdio>
#include <cstring>
#include <vector>

namespace ba {

bool Gpu::init(HWND hwnd, int width, int height) {
  width_ = std::max(1, width);
  height_ = std::max(1, height);
  DXGI_SWAP_CHAIN_DESC sd{};
  sd.BufferCount = 2;
  sd.BufferDesc.Width = static_cast<UINT>(width_);
  sd.BufferDesc.Height = static_cast<UINT>(height_);
  sd.BufferDesc.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
  sd.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
  sd.OutputWindow = hwnd;
  sd.SampleDesc.Count = 1;
  sd.Windowed = TRUE;
  sd.SwapEffect = DXGI_SWAP_EFFECT_FLIP_DISCARD;
  const D3D_FEATURE_LEVEL levels[] = {D3D_FEATURE_LEVEL_11_0};
  D3D_FEATURE_LEVEL got{};
  if (FAILED(D3D11CreateDeviceAndSwapChain(nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr, 0, levels, 1, D3D11_SDK_VERSION, &sd, &swap_, &device_,
                                           &got, &ctx_)))
    return false;
  return create_targets();
}

bool Gpu::create_targets() {
  ComPtr<ID3D11Texture2D> back;
  if (FAILED(swap_->GetBuffer(0, IID_PPV_ARGS(&back)))) return false;
  if (FAILED(device_->CreateRenderTargetView(back.Get(), nullptr, &rtv_))) return false;
  D3D11_TEXTURE2D_DESC dd{};
  dd.Width = static_cast<UINT>(width_);
  dd.Height = static_cast<UINT>(height_);
  dd.MipLevels = 1;
  dd.ArraySize = 1;
  // typeless, so a copy of it can be read as a texture (soft particles)
  dd.Format = DXGI_FORMAT_R24G8_TYPELESS;
  dd.SampleDesc.Count = 1;
  dd.BindFlags = D3D11_BIND_DEPTH_STENCIL;
  depth_.Reset(), depth_copy_.Reset(), depth_copy_srv_.Reset();
  if (FAILED(device_->CreateTexture2D(&dd, nullptr, &depth_))) return false;
  D3D11_DEPTH_STENCIL_VIEW_DESC dsvd{};
  dsvd.Format = DXGI_FORMAT_D24_UNORM_S8_UINT;
  dsvd.ViewDimension = D3D11_DSV_DIMENSION_TEXTURE2D;
  if (FAILED(device_->CreateDepthStencilView(depth_.Get(), &dsvd, &dsv_))) return false;
  dd.BindFlags = D3D11_BIND_SHADER_RESOURCE;
  if (FAILED(device_->CreateTexture2D(&dd, nullptr, &depth_copy_))) return false;
  D3D11_SHADER_RESOURCE_VIEW_DESC srvd{};
  srvd.Format = DXGI_FORMAT_R24_UNORM_X8_TYPELESS;
  srvd.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D;
  srvd.Texture2D.MipLevels = 1;
  if (FAILED(device_->CreateShaderResourceView(depth_copy_.Get(), &srvd, &depth_copy_srv_))) return false;
  D3D11_TEXTURE2D_DESC sd{};
  sd.Width = static_cast<UINT>(width_);
  sd.Height = static_cast<UINT>(height_);
  sd.MipLevels = 1;
  sd.ArraySize = 1;
  sd.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
  sd.SampleDesc.Count = 1;
  sd.BindFlags = D3D11_BIND_RENDER_TARGET | D3D11_BIND_SHADER_RESOURCE;
  scene_.Reset(), scene_rtv_.Reset(), scene_srv_.Reset();
  if (FAILED(device_->CreateTexture2D(&sd, nullptr, &scene_))) return false;
  if (FAILED(device_->CreateRenderTargetView(scene_.Get(), nullptr, &scene_rtv_))) return false;
  if (FAILED(device_->CreateShaderResourceView(scene_.Get(), nullptr, &scene_srv_))) return false;
  if (!post_vs_) {
    // a triangle over the whole screen; the uv the pixel shaders read is TEXCOORD0
    const char* src = R"(
struct VSOut { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; };
VSOut vs_main(uint id : SV_VertexID) {
  VSOut o;
  o.uv = float2((id << 1) & 2, id & 2);
  o.pos = float4(o.uv * float2(2, -2) + float2(-1, 1), 0, 1);
  return o;
}
Texture2D tex : register(t0);
SamplerState samp : register(s0);
float4 ps_main(VSOut v) : SV_TARGET { return tex.SampleLevel(samp, v.uv, 0); }
)";
    if (!shader(src, "post", post_vs_, copy_ps_, nullptr)) return false;
    D3D11_SAMPLER_DESC smp{};
    smp.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;
    smp.AddressU = smp.AddressV = smp.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
    smp.MaxLOD = D3D11_FLOAT32_MAX;
    device_->CreateSamplerState(&smp, &post_sampler_);
    D3D11_BUFFER_DESC cbd{};
    cbd.Usage = D3D11_USAGE_DYNAMIC;
    cbd.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
    cbd.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
    cbd.ByteWidth = 32;
    device_->CreateBuffer(&cbd, nullptr, &fxaa_cb_);
  }
  return true;
}

bool Gpu::set_fxaa(std::span<const uint8_t> dxbc, const float options[4]) {
  // the blob may sit behind a header of Riot's: start at its "DXBC" magic
  size_t at = 0;
  while (at + 4 <= dxbc.size() && std::memcmp(dxbc.data() + at, "DXBC", 4) != 0) ++at;
  if (at + 32 > dxbc.size()) return false;
  uint32_t size = 0;
  std::memcpy(&size, dxbc.data() + at + 24, 4);
  if (at + size > dxbc.size()) return false;
  fxaa_ps_.Reset();
  if (FAILED(device_->CreatePixelShader(dxbc.data() + at, size, nullptr, &fxaa_ps_))) return false;
  std::memcpy(fxaa_options_, options, sizeof fxaa_options_);
  return true;
}

void Gpu::resolve() {
  ctx_->OMSetRenderTargets(1, rtv_.GetAddressOf(), nullptr);
  ctx_->IASetInputLayout(nullptr);
  ctx_->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
  ctx_->VSSetShader(post_vs_.Get(), nullptr, 0);
  if (fxaa_ps_) {
    D3D11_MAPPED_SUBRESOURCE map{};
    if (SUCCEEDED(ctx_->Map(fxaa_cb_.Get(), 0, D3D11_MAP_WRITE_DISCARD, 0, &map))) {
      // $Globals: float2 fxaaQualityRcpFrame at 0, float4 fxaaQualityOptions at 16
      const float cb[8] = {1.f / static_cast<float>(width_), 1.f / static_cast<float>(height_), 0, 0,
                           fxaa_options_[0], fxaa_options_[1], fxaa_options_[2], fxaa_options_[3]};
      std::memcpy(map.pData, cb, sizeof cb);
      ctx_->Unmap(fxaa_cb_.Get(), 0);
    }
    ctx_->PSSetConstantBuffers(0, 1, fxaa_cb_.GetAddressOf());
  }
  ctx_->PSSetShader(fxaa_ps_ ? fxaa_ps_.Get() : copy_ps_.Get(), nullptr, 0);
  ctx_->PSSetShaderResources(0, 1, scene_srv_.GetAddressOf());
  ctx_->PSSetSamplers(0, 1, post_sampler_.GetAddressOf());
  ctx_->OMSetBlendState(nullptr, nullptr, 0xFFFFFFFF);
  ctx_->OMSetDepthStencilState(nullptr, 0);
  ctx_->RSSetState(nullptr);
  ctx_->Draw(3, 0);
  ID3D11ShaderResourceView* none = nullptr;
  ctx_->PSSetShaderResources(0, 1, &none);
}

void Gpu::resize(int width, int height) {
  if (!swap_ || width <= 0 || height <= 0) return;
  width_ = width;
  height_ = height;
  ctx_->OMSetRenderTargets(0, nullptr, nullptr);
  rtv_.Reset();
  dsv_.Reset();
  depth_.Reset(), depth_copy_.Reset(), depth_copy_srv_.Reset();
  scene_rtv_.Reset();
  scene_srv_.Reset();
  scene_.Reset();
  swap_->ResizeBuffers(0, static_cast<UINT>(width), static_cast<UINT>(height), DXGI_FORMAT_UNKNOWN, 0);
  create_targets();
}

void Gpu::begin(float r, float g, float b) {
  const float clear[4] = {r, g, b, 1.f};
  ctx_->ClearRenderTargetView(scene_rtv_.Get(), clear);
  ctx_->ClearDepthStencilView(dsv_.Get(), D3D11_CLEAR_DEPTH | D3D11_CLEAR_STENCIL, 1.f, 0);
  ctx_->OMSetRenderTargets(1, scene_rtv_.GetAddressOf(), dsv_.Get());
  D3D11_VIEWPORT vp{0, 0, static_cast<float>(width_), static_cast<float>(height_), 0, 1};
  ctx_->RSSetViewports(1, &vp);
}

void Gpu::end() { swap_->Present(1, 0); }

ID3D11ShaderResourceView* Gpu::depth_snapshot() {
  if (!depth_ || !depth_copy_) return nullptr;
  ctx_->CopyResource(depth_copy_.Get(), depth_.Get());
  return depth_copy_srv_.Get();
}

bool Gpu::save_bmp(const std::string& path) {
  ComPtr<ID3D11Texture2D> back;
  if (FAILED(swap_->GetBuffer(0, IID_PPV_ARGS(&back)))) return false;
  D3D11_TEXTURE2D_DESC td{};
  back->GetDesc(&td);
  td.Usage = D3D11_USAGE_STAGING;
  td.BindFlags = 0;
  td.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
  td.MiscFlags = 0;
  ComPtr<ID3D11Texture2D> staging;
  if (FAILED(device_->CreateTexture2D(&td, nullptr, &staging))) return false;
  ctx_->CopyResource(staging.Get(), back.Get());
  D3D11_MAPPED_SUBRESOURCE map{};
  if (FAILED(ctx_->Map(staging.Get(), 0, D3D11_MAP_READ, 0, &map))) return false;
  const uint32_t w = td.Width, h = td.Height, row = (w * 3 + 3) & ~3u;
  std::vector<uint8_t> px(static_cast<size_t>(row) * h);
  for (uint32_t y = 0; y < h; ++y) {
    const uint8_t* src = static_cast<const uint8_t*>(map.pData) + static_cast<size_t>(map.RowPitch) * (h - 1 - y);
    for (uint32_t x = 0; x < w; ++x) {
      px[static_cast<size_t>(y) * row + x * 3 + 0] = src[x * 4 + 2];
      px[static_cast<size_t>(y) * row + x * 3 + 1] = src[x * 4 + 1];
      px[static_cast<size_t>(y) * row + x * 3 + 2] = src[x * 4 + 0];
    }
  }
  ctx_->Unmap(staging.Get(), 0);
  FILE* f = std::fopen(path.c_str(), "wb");
  if (!f) return false;
  const uint32_t data_size = static_cast<uint32_t>(px.size());
  uint8_t header[54] = {'B', 'M'};
  auto put32 = [&](int at, uint32_t v) { std::memcpy(header + at, &v, 4); };
  put32(2, 54 + data_size);
  put32(10, 54);
  put32(14, 40);
  put32(18, w);
  put32(22, h);
  header[26] = 1;
  header[28] = 24;
  put32(34, data_size);
  std::fwrite(header, 1, 54, f);
  std::fwrite(px.data(), 1, px.size(), f);
  std::fclose(f);
  return true;
}

bool Gpu::shader(const char* source, const char* name, ComPtr<ID3D11VertexShader>& vs, ComPtr<ID3D11PixelShader>& ps, ComPtr<ID3DBlob>* vs_code) {
  ComPtr<ID3DBlob> vsb, psb, err;
  if (FAILED(D3DCompile(source, std::strlen(source), name, nullptr, nullptr, "vs_main", "vs_5_0", 0, 0, &vsb, &err))) {
    if (err) OutputDebugStringA(static_cast<const char*>(err->GetBufferPointer()));
    return false;
  }
  if (FAILED(D3DCompile(source, std::strlen(source), name, nullptr, nullptr, "ps_main", "ps_5_0", 0, 0, &psb, &err))) {
    if (err) OutputDebugStringA(static_cast<const char*>(err->GetBufferPointer()));
    return false;
  }
  device_->CreateVertexShader(vsb->GetBufferPointer(), vsb->GetBufferSize(), nullptr, &vs);
  device_->CreatePixelShader(psb->GetBufferPointer(), psb->GetBufferSize(), nullptr, &ps);
  if (vs_code) *vs_code = vsb;
  return true;
}

ComPtr<ID3D11ShaderResourceView> Gpu::texture_own_mips(const Texture& t) {
  const std::vector<uint8_t> rgba = texture_rgba(t);
  D3D11_TEXTURE2D_DESC td{};
  td.Width = t.width, td.Height = t.height, td.MipLevels = 0, td.ArraySize = 1;  // 0: the whole chain
  td.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
  td.SampleDesc.Count = 1;
  td.Usage = D3D11_USAGE_DEFAULT;
  td.BindFlags = D3D11_BIND_SHADER_RESOURCE | D3D11_BIND_RENDER_TARGET;
  td.MiscFlags = D3D11_RESOURCE_MISC_GENERATE_MIPS;
  ComPtr<ID3D11Texture2D> tex;
  ComPtr<ID3D11ShaderResourceView> srv;
  if (FAILED(device_->CreateTexture2D(&td, nullptr, &tex))) return nullptr;
  ctx_->UpdateSubresource(tex.Get(), 0, nullptr, rgba.data(), t.width * 4, 0);
  if (FAILED(device_->CreateShaderResourceView(tex.Get(), nullptr, &srv))) return nullptr;
  ctx_->GenerateMips(srv.Get());
  return srv;
}

ComPtr<ID3D11ShaderResourceView> Gpu::texture(const Texture& t) {
  // DirectX 11 wants block-compressed textures whose sides are multiples of 4: smaller ones (14.1 ships 2x2 BC1 like
  // shared/particles/black) go up decoded, as RGBA8, mip 0 only
  if (t.format != TexFormat::BGRA8 && (t.width % 4 || t.height % 4)) {
    const std::vector<uint8_t> rgba = texture_rgba(t);
    D3D11_TEXTURE2D_DESC td{};
    td.Width = t.width, td.Height = t.height, td.MipLevels = 1, td.ArraySize = 1;
    td.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    td.SampleDesc.Count = 1;
    td.Usage = D3D11_USAGE_IMMUTABLE;
    td.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    D3D11_SUBRESOURCE_DATA sd{rgba.data(), t.width * 4, 0};
    ComPtr<ID3D11Texture2D> tex;
    ComPtr<ID3D11ShaderResourceView> srv;
    if (FAILED(device_->CreateTexture2D(&td, &sd, &tex))) return nullptr;
    device_->CreateShaderResourceView(tex.Get(), nullptr, &srv);
    return srv;
  }
  D3D11_TEXTURE2D_DESC td{};
  td.Width = t.width;
  td.Height = t.height;
  td.MipLevels = static_cast<UINT>(t.mips.size());
  td.ArraySize = 1;
  td.Format = t.format == TexFormat::BC1   ? DXGI_FORMAT_BC1_UNORM
              : t.format == TexFormat::BC2 ? DXGI_FORMAT_BC2_UNORM
              : t.format == TexFormat::BC3 ? DXGI_FORMAT_BC3_UNORM
                                           : DXGI_FORMAT_B8G8R8A8_UNORM;
  td.SampleDesc.Count = 1;
  td.Usage = D3D11_USAGE_IMMUTABLE;
  td.BindFlags = D3D11_BIND_SHADER_RESOURCE;
  std::vector<D3D11_SUBRESOURCE_DATA> sub(t.mips.size());
  for (size_t i = 0; i < t.mips.size(); ++i) {
    const uint32_t w = std::max(t.width >> i, 1u);
    sub[i].pSysMem = t.mips[i].data();
    sub[i].SysMemPitch = t.row_pitch(w);
  }
  ComPtr<ID3D11Texture2D> tex;
  ComPtr<ID3D11ShaderResourceView> srv;
  if (FAILED(device_->CreateTexture2D(&td, sub.data(), &tex))) return nullptr;
  device_->CreateShaderResourceView(tex.Get(), nullptr, &srv);
  return srv;
}

}  // namespace ba
