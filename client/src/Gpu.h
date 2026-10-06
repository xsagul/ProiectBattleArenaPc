#pragma once
// The Direct3D 11 device and the frame: swap chain, depth buffer, shader compilation, textures straight from League's
// block-compressed data.

#include <d3d11.h>
#include <dxgi.h>
#include <windows.h>
#include <wrl/client.h>

#include <span>
#include <string>

#include "ba/Texture.h"

namespace ba {

using Microsoft::WRL::ComPtr;

class Gpu {
 public:
  bool init(HWND hwnd, int width, int height);
  void resize(int width, int height);
  /** Starts a frame: everything is drawn into the scene target. */
  void begin(float r, float g, float b);
  /** The scene onto the screen: through League's own anti-aliasing pixel shader when one is set, else as it is. */
  void resolve();
  void end();
  /** League's FXAA pixel shader (Shaders/hlsl/fxaa_ps, compiled DXBC from ShaderCache.dx11) and its options
   *  (fxaaQualityOptions: x subpix, y edge threshold, z edge threshold min). */
  bool set_fxaa(std::span<const uint8_t> dxbc, const float options[4]);
  /** A copy of the depth drawn so far, readable as a texture (R24 = the depth buffer's value); null on failure. */
  ID3D11ShaderResourceView* depth_snapshot();
  /** Saves the frame drawn so far (before end()) as a 24-bit BMP. */
  bool save_bmp(const std::string& path);

  ID3D11Device* device() const { return device_.Get(); }
  ID3D11DeviceContext* ctx() const { return ctx_.Get(); }
  int width() const { return width_; }
  int height() const { return height_; }

  /** Compiles HLSL from source (entry points vs_main / ps_main); null on failure (the error goes to the debug output). */
  bool shader(const char* source, const char* name, ComPtr<ID3D11VertexShader>& vs, ComPtr<ID3D11PixelShader>& ps, ComPtr<ID3DBlob>* vs_code);
  /** Uploads a League texture as it is (BC1/BC3 stay compressed on the GPU). */
  ComPtr<ID3D11ShaderResourceView> texture(const Texture& t);
  /** The top level of `t` with mips the graphics card computes from it (RGBA8), the file's own lower levels ignored. */
  ComPtr<ID3D11ShaderResourceView> texture_own_mips(const Texture& t);

 private:
  bool create_targets();
  ComPtr<ID3D11Device> device_;
  ComPtr<ID3D11DeviceContext> ctx_;
  ComPtr<IDXGISwapChain> swap_;
  ComPtr<ID3D11RenderTargetView> rtv_;
  ComPtr<ID3D11DepthStencilView> dsv_;
  ComPtr<ID3D11Texture2D> depth_, depth_copy_;
  ComPtr<ID3D11ShaderResourceView> depth_copy_srv_;
  // the scene is drawn here, then resolved onto the back buffer
  ComPtr<ID3D11Texture2D> scene_;
  ComPtr<ID3D11RenderTargetView> scene_rtv_;
  ComPtr<ID3D11ShaderResourceView> scene_srv_;
  ComPtr<ID3D11VertexShader> post_vs_;
  ComPtr<ID3D11PixelShader> copy_ps_, fxaa_ps_;
  ComPtr<ID3D11Buffer> fxaa_cb_;
  ComPtr<ID3D11SamplerState> post_sampler_;
  float fxaa_options_[4] = {0.75f, 0.166f, 0.0833f, 0};
  int width_ = 1;
  int height_ = 1;
};

}  // namespace ba
