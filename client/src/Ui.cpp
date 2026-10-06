#include "Ui.h"

#include <algorithm>
#include <cmath>
#include <cstring>

#include "ba/Hash.h"
#include "ba/StringTable.h"
#include "ba/Texture.h"

namespace ba {

namespace {

const char* kShader = R"(
cbuffer Frame : register(b0) { float2 screen; float2 pad; };
Texture2D tex : register(t0);
SamplerState smp : register(s0);
struct VSIn { float2 pos : POSITION; float2 uv : TEXCOORD0; float4 color : COLOR0; float saturation : TEXCOORD1; };
struct VSOut { float4 pos : SV_Position; float2 uv : TEXCOORD0; float4 color : COLOR0; float saturation : TEXCOORD1; };
VSOut vs_main(VSIn i) {
  VSOut o;
  o.pos = float4(i.pos.x / screen.x * 2 - 1, 1 - i.pos.y / screen.y * 2, 0, 1);
  o.uv = i.uv;
  o.color = i.color;
  o.saturation = i.saturation;
  return o;
}
float4 ps_main(VSOut i) : SV_Target {
  float4 c = tex.Sample(smp, i.uv);
  float grey = dot(c.rgb, float3(0.299, 0.587, 0.114));
  c.rgb = lerp(float3(grey, grey, grey), c.rgb, i.saturation);
  return c * i.color;
}
)";

std::string lower(std::string s) {
  for (char& c : s) c = static_cast<char>(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
  return s;
}

}  // namespace

/** An interface colour: the files keep blue first (HUD_ShopButton's gold reads [153, 247, 255], an allied tower's
 *  light blue [239, 199, 72]). */
void ui_color(const BinValue* v, float out[4]) {
  if (!v) return;
  out[0] = static_cast<float>(v->num[2]) / 255.f, out[1] = static_cast<float>(v->num[1]) / 255.f;
  out[2] = static_cast<float>(v->num[0]) / 255.f, out[3] = static_cast<float>(v->num[3]) / 255.f;
}

namespace {

void rgba(const BinValue* v, float out[4]) { ui_color(v, out); }

}  // namespace

// ---------------------------------------------------------------- Ui2D

bool Ui2D::init(Gpu& gpu) {
  ComPtr<ID3DBlob> code;
  if (!gpu.shader(kShader, "ui", vs_, ps_, &code)) return false;
  const D3D11_INPUT_ELEMENT_DESC il[] = {
      {"POSITION", 0, DXGI_FORMAT_R32G32_FLOAT, 0, 0, D3D11_INPUT_PER_VERTEX_DATA, 0},
      {"TEXCOORD", 0, DXGI_FORMAT_R32G32_FLOAT, 0, 8, D3D11_INPUT_PER_VERTEX_DATA, 0},
      {"COLOR", 0, DXGI_FORMAT_R32G32B32A32_FLOAT, 0, 16, D3D11_INPUT_PER_VERTEX_DATA, 0},
      {"TEXCOORD", 1, DXGI_FORMAT_R32_FLOAT, 0, 32, D3D11_INPUT_PER_VERTEX_DATA, 0},
  };
  if (FAILED(gpu.device()->CreateInputLayout(il, 4, code->GetBufferPointer(), code->GetBufferSize(), &layout_))) return false;
  D3D11_BUFFER_DESC cbd{};
  cbd.Usage = D3D11_USAGE_DYNAMIC;
  cbd.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
  cbd.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
  cbd.ByteWidth = 16;
  gpu.device()->CreateBuffer(&cbd, nullptr, &cb_);
  D3D11_BLEND_DESC bd{};
  bd.RenderTarget[0].BlendEnable = TRUE;
  bd.RenderTarget[0].SrcBlend = D3D11_BLEND_SRC_ALPHA;
  bd.RenderTarget[0].DestBlend = D3D11_BLEND_INV_SRC_ALPHA;
  bd.RenderTarget[0].BlendOp = D3D11_BLEND_OP_ADD;
  bd.RenderTarget[0].SrcBlendAlpha = D3D11_BLEND_ONE;
  bd.RenderTarget[0].DestBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;
  bd.RenderTarget[0].BlendOpAlpha = D3D11_BLEND_OP_ADD;
  bd.RenderTarget[0].RenderTargetWriteMask = D3D11_COLOR_WRITE_ENABLE_ALL;
  gpu.device()->CreateBlendState(&bd, &blend_);
  D3D11_SAMPLER_DESC smp{};
  smp.Filter = D3D11_FILTER_MIN_MAG_LINEAR_MIP_POINT;
  smp.AddressU = smp.AddressV = smp.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
  smp.MaxLOD = 0;  // the atlases as drawn, never a smaller level
  gpu.device()->CreateSamplerState(&smp, &sampler_);
  D3D11_RASTERIZER_DESC rd{};
  rd.FillMode = D3D11_FILL_SOLID;
  rd.CullMode = D3D11_CULL_NONE;
  rd.DepthClipEnable = FALSE;
  gpu.device()->CreateRasterizerState(&rd, &raster_);
  D3D11_DEPTH_STENCIL_DESC dd{};
  dd.DepthEnable = FALSE;
  gpu.device()->CreateDepthStencilState(&dd, &no_depth_);
  Texture one;
  one.format = TexFormat::BGRA8;
  one.width = one.height = 1;
  one.mips.push_back({255, 255, 255, 255});
  white_ = gpu.texture(one);
  return true;
}

ID3D11ShaderResourceView* Ui2D::texture(Gpu& gpu, const std::string& path) {
  const std::string key = lower(path);
  auto it = textures_.find(key);
  if (it != textures_.end()) return it->second.Get();
  ComPtr<ID3D11ShaderResourceView> srv;
  for (const Wad* w : wads_) {
    try {
      auto bytes = w->read(key);
      // an interface file names a .png or .dds the archives keep as .tex or .dds
      for (const char* ext : {".tex", ".dds"}) {
        if (bytes) break;
        const size_t dot = key.rfind('.');
        if (dot != std::string::npos) bytes = w->read(key.substr(0, dot) + ext);
      }
      if (bytes) {
        srv = gpu.texture(read_texture(*bytes));
        break;
      }
    } catch (const std::exception&) {
    }
  }
  textures_[key] = srv;
  return srv.Get();
}

void Ui2D::run(ID3D11ShaderResourceView* tex, size_t count) {
  if (!runs_.empty() && runs_.back().tex == tex) runs_.back().count += count;
  else runs_.push_back({tex, verts_.size() - count, count});
}

void Ui2D::quad(ID3D11ShaderResourceView* tex, float x0, float y0, float x1, float y1, float u0, float v0, float u1, float v1, const float c[4],
                float saturation) {
  if (!tex) return;
  const Vertex v[4] = {{x0, y0, u0, v0, c[0], c[1], c[2], c[3], saturation},
                       {x1, y0, u1, v0, c[0], c[1], c[2], c[3], saturation},
                       {x0, y1, u0, v1, c[0], c[1], c[2], c[3], saturation},
                       {x1, y1, u1, v1, c[0], c[1], c[2], c[3], saturation}};
  for (int i : {0, 1, 2, 2, 1, 3}) verts_.push_back(v[i]);
  run(tex, 6);
}

void Ui2D::triangle(ID3D11ShaderResourceView* tex, const float xy[6], const float uv[6], const float c[4], float saturation) {
  if (!tex) return;
  for (int i = 0; i < 3; ++i) verts_.push_back({xy[i * 2], xy[i * 2 + 1], uv[i * 2], uv[i * 2 + 1], c[0], c[1], c[2], c[3], saturation});
  run(tex, 3);
}

void Ui2D::flush(Gpu& gpu) {
  if (verts_.empty()) return;
  ID3D11DeviceContext* ctx = gpu.ctx();
  if (verts_.size() > vb_capacity_) {
    vb_capacity_ = std::max<size_t>(verts_.size() * 2, 6 * 1024);
    D3D11_BUFFER_DESC bd{};
    bd.Usage = D3D11_USAGE_DYNAMIC;
    bd.BindFlags = D3D11_BIND_VERTEX_BUFFER;
    bd.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
    bd.ByteWidth = static_cast<UINT>(vb_capacity_ * sizeof(Vertex));
    vb_.Reset();
    gpu.device()->CreateBuffer(&bd, nullptr, &vb_);
  }
  D3D11_MAPPED_SUBRESOURCE map{};
  if (SUCCEEDED(ctx->Map(vb_.Get(), 0, D3D11_MAP_WRITE_DISCARD, 0, &map))) {
    std::memcpy(map.pData, verts_.data(), verts_.size() * sizeof(Vertex));
    ctx->Unmap(vb_.Get(), 0);
    if (SUCCEEDED(ctx->Map(cb_.Get(), 0, D3D11_MAP_WRITE_DISCARD, 0, &map))) {
      const float cb[4] = {static_cast<float>(gpu.width()), static_cast<float>(gpu.height()), 0, 0};
      std::memcpy(map.pData, cb, sizeof cb);
      ctx->Unmap(cb_.Get(), 0);
    }
    ctx->IASetInputLayout(layout_.Get());
    ctx->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    const UINT stride = sizeof(Vertex), offset = 0;
    ctx->IASetVertexBuffers(0, 1, vb_.GetAddressOf(), &stride, &offset);
    ctx->VSSetShader(vs_.Get(), nullptr, 0);
    ctx->PSSetShader(ps_.Get(), nullptr, 0);
    ctx->VSSetConstantBuffers(0, 1, cb_.GetAddressOf());
    ctx->PSSetSamplers(0, 1, sampler_.GetAddressOf());
    ctx->OMSetBlendState(blend_.Get(), nullptr, 0xFFFFFFFF);
    ctx->OMSetDepthStencilState(no_depth_.Get(), 0);
    ctx->RSSetState(raster_.Get());
    for (const Run& r : runs_) {
      ctx->PSSetShaderResources(0, 1, &r.tex);
      ctx->Draw(static_cast<UINT>(r.count), static_cast<UINT>(r.first));
    }
    ID3D11ShaderResourceView* none = nullptr;
    ctx->PSSetShaderResources(0, 1, &none);
    ctx->OMSetBlendState(nullptr, nullptr, 0xFFFFFFFF);
    ctx->OMSetDepthStencilState(nullptr, 0);
    ctx->RSSetState(nullptr);
  }
  verts_.clear();
  runs_.clear();
}

// ---------------------------------------------------------------- fonts

namespace {

uint16_t be16(const uint8_t* p) { return static_cast<uint16_t>(p[0] << 8 | p[1]); }
uint32_t be32(const uint8_t* p) { return static_cast<uint32_t>(p[0]) << 24 | static_cast<uint32_t>(p[1]) << 16 | static_cast<uint32_t>(p[2]) << 8 | p[3]; }

/** A font file's family name (the 'name' table's name 1, as Windows names it) and weight (OS/2 usWeightClass). */
bool font_names(const std::vector<uint8_t>& f, std::wstring& family, int& weight) {
  if (f.size() < 12) return false;
  const uint16_t tables = be16(&f[4]);
  weight = 400;
  for (uint16_t i = 0; i < tables; ++i) {
    const size_t rec = 12 + static_cast<size_t>(i) * 16;
    if (rec + 16 > f.size()) break;
    const uint32_t off = be32(&f[rec + 8]), len = be32(&f[rec + 12]);
    if (off + len > f.size()) continue;
    if (std::memcmp(&f[rec], "OS/2", 4) == 0 && len >= 6) weight = be16(&f[off + 4]);
    if (std::memcmp(&f[rec], "name", 4) == 0 && len >= 6) {
      const uint16_t count = be16(&f[off + 2]), strings = be16(&f[off + 4]);
      for (uint16_t n = 0; n < count; ++n) {
        const size_t r = off + 6 + static_cast<size_t>(n) * 12;
        if (r + 12 > f.size()) break;
        // Windows platform, name 1 (family); English first
        if (be16(&f[r]) != 3 || be16(&f[r + 6]) != 1) continue;
        const uint16_t language = be16(&f[r + 4]), nlen = be16(&f[r + 8]), noff = be16(&f[r + 10]);
        if (!family.empty() && language != 0x409) continue;
        const size_t at = off + strings + noff;
        if (at + nlen > f.size()) continue;
        family.clear();
        for (size_t k = 0; k + 1 < nlen; k += 2) family.push_back(static_cast<wchar_t>(be16(&f[at + k])));
      }
    }
  }
  return !family.empty();
}

}  // namespace

bool UiFonts::load(const Wad& ui) {
  ui_ = &ui;
  auto bytes = ui.read("ux/fonts");
  if (!bytes) return false;
  const PropertyBin bin(*bytes);
  for (const BinEntry& e : bin.entries()) {
    if (e.cls != fnv1a("GameFontDescription")) continue;
    Desc d;
    rgba(e.field("Color"), d.color);
    rgba(e.field("outlineColor"), d.outline_color);
    rgba(e.field("shadowColor"), d.shadow_color);
    if (const BinValue* t = e.field("typeData"))
      if (const BinEntry* type = bin.entry(static_cast<uint32_t>(t->u)))
        if (const BinValue* locales = type->field("localeTypes"); locales && !locales->items.empty())
          if (const BinValue* path = locales->items[0].field("mFontFilePath")) d.file = lower(path->str);
    if (const BinValue* r = e.field("resolutionData"))
      if (const BinEntry* res = bin.entry(static_cast<uint32_t>(r->u)))
        if (const BinValue* locales = res->field("localeResolutions"); locales && !locales->items.empty())
          if (const BinValue* list = locales->items[0].field("resolutions"); list && !list->items.empty()) {
            const BinValue& fr = list->items[0];
            if (const BinValue* v = fr.field("fontSize")) d.size = static_cast<float>(v->number());
            if (const BinValue* v = fr.field("screenHeight")) d.ref_height = static_cast<float>(v->number());
            if (const BinValue* v = fr.field("outlineSize")) d.outline = static_cast<float>(v->number());
            if (const BinValue* v = fr.field("shadowDepthX")) d.shadow_x = static_cast<float>(v->number());
            if (const BinValue* v = fr.field("shadowDepthY")) d.shadow_y = static_cast<float>(v->number());
          }
    descs_[e.name] = d;
  }
  return !descs_.empty();
}

const UiFonts::Desc* UiFonts::desc(uint32_t hash) const {
  auto it = descs_.find(hash);
  return it == descs_.end() ? nullptr : &it->second;
}

const UiFonts::Face* UiFonts::face(Gpu& gpu, const std::string& file, int px) {
  auto key = std::make_pair(file, px);
  auto it = faces_.find(key);
  if (it != faces_.end()) return it->second.get();
  auto& slot = faces_[key];
  // ---- the font file, handed to Windows for this process only
  if (!families_.count(file)) {
    std::wstring family;
    int weight = 400;
    try {
      if (auto bytes = ui_ ? ui_->read(file) : std::nullopt) {
        DWORD count = 0;
        if (font_names(*bytes, family, weight) && !AddFontMemResourceEx(bytes->data(), static_cast<DWORD>(bytes->size()), nullptr, &count)) family.clear();
      }
    } catch (const std::exception&) {
      family.clear();
    }
    families_[file] = family;
    weights_[file] = weight;
  }
  const std::wstring& family = families_[file];
  if (family.empty() || px < 4) return nullptr;

  // ---- every glyph of Latin-1 drawn white on black into a cell; the red channel is its coverage
  HDC dc = CreateCompatibleDC(nullptr);
  HFONT font = CreateFontW(-px, 0, 0, 0, weights_[file], FALSE, FALSE, FALSE, DEFAULT_CHARSET, OUT_TT_PRECIS, CLIP_DEFAULT_PRECIS, ANTIALIASED_QUALITY,
                           DEFAULT_PITCH | FF_DONTCARE, family.c_str());
  const int pad = px / 3 + 2, cell_w = px * 3 + pad * 2, cell_h = px * 2 + 4;
  BITMAPINFO bi{};
  bi.bmiHeader.biSize = sizeof bi.bmiHeader;
  bi.bmiHeader.biWidth = cell_w;
  bi.bmiHeader.biHeight = -cell_h;
  bi.bmiHeader.biPlanes = 1;
  bi.bmiHeader.biBitCount = 32;
  void* bits = nullptr;
  HBITMAP bmp = CreateDIBSection(dc, &bi, DIB_RGB_COLORS, &bits, nullptr, 0);
  if (!dc || !font || !bmp) {
    if (bmp) DeleteObject(bmp);
    if (font) DeleteObject(font);
    if (dc) DeleteDC(dc);
    return nullptr;
  }
  HGDIOBJ old_bmp = SelectObject(dc, bmp), old_font = SelectObject(dc, font);
  SetBkMode(dc, TRANSPARENT);
  SetTextColor(dc, RGB(255, 255, 255));
  TEXTMETRICW tm{};
  GetTextMetricsW(dc, &tm);
  auto face = std::make_unique<Face>();
  face->ascent = static_cast<float>(tm.tmAscent);
  face->height = static_cast<float>(tm.tmHeight);
  const int glyph_h = std::min<int>(cell_h, tm.tmHeight + 2);
  const int atlas_w = 1024;
  std::vector<uint8_t> atlas;
  int pen_x = 1, pen_y = 1, atlas_h = glyph_h + 2;
  atlas.assign(static_cast<size_t>(atlas_w) * static_cast<size_t>(atlas_h) * 4, 0);
  for (int ch = 32; ch < 256; ++ch) {
    const wchar_t wc = static_cast<wchar_t>(ch);
    ABCFLOAT abc{};
    if (!GetCharABCWidthsFloatW(dc, static_cast<UINT>(ch), static_cast<UINT>(ch), &abc)) continue;
    const float advance = abc.abcfA + abc.abcfB + abc.abcfC;
    const int w = std::min(cell_w, pad * 2 + static_cast<int>(std::ceil(std::max(advance, abc.abcfA + abc.abcfB))) + 1);
    std::memset(bits, 0, static_cast<size_t>(cell_w) * static_cast<size_t>(cell_h) * 4);
    TextOutW(dc, pad, 0, &wc, 1);
    GdiFlush();
    if (pen_x + w + 1 > atlas_w) {
      pen_x = 1, pen_y += glyph_h + 1;
      atlas_h = pen_y + glyph_h + 2;
      atlas.resize(static_cast<size_t>(atlas_w) * static_cast<size_t>(atlas_h) * 4, 0);
    }
    const uint8_t* src = static_cast<const uint8_t*>(bits);
    for (int y = 0; y < glyph_h; ++y)
      for (int x = 0; x < w; ++x) {
        uint8_t* o = &atlas[(static_cast<size_t>(pen_y + y) * atlas_w + static_cast<size_t>(pen_x + x)) * 4];
        o[0] = o[1] = o[2] = 255;
        o[3] = src[(static_cast<size_t>(y) * cell_w + static_cast<size_t>(x)) * 4 + 2];
      }
    Glyph& g = face->glyphs[static_cast<size_t>(ch)];
    g.w = static_cast<float>(w), g.h = static_cast<float>(glyph_h), g.left = static_cast<float>(pad), g.advance = advance;
    g.u0 = static_cast<float>(pen_x), g.v0 = static_cast<float>(pen_y);  // pixels for now
    pen_x += w + 1;
  }
  SelectObject(dc, old_font);
  SelectObject(dc, old_bmp);
  DeleteObject(bmp);
  DeleteObject(font);
  DeleteDC(dc);
  for (Glyph& g : face->glyphs) {
    g.u1 = (g.u0 + g.w) / static_cast<float>(atlas_w), g.v1 = (g.v0 + g.h) / static_cast<float>(atlas_h);
    g.u0 /= static_cast<float>(atlas_w), g.v0 /= static_cast<float>(atlas_h);
  }
  Texture t;
  t.format = TexFormat::BGRA8;
  t.width = static_cast<uint32_t>(atlas_w), t.height = static_cast<uint32_t>(atlas_h);
  t.mips.push_back(std::move(atlas));
  face->tex = gpu.texture(t);
  slot = std::move(face);
  return slot.get();
}

float UiFonts::width(Gpu& gpu, const Desc& d, std::string_view text, float screen_h) {
  // FontResolutionData autoScale [meta default true]: the size is for the reference height
  const Face* f = face(gpu, d.file, static_cast<int>(std::lround(d.size * screen_h / std::max(1.f, d.ref_height))));
  if (!f) return 0;
  float w = 0;
  for (char c : text) w += f->glyphs[static_cast<uint8_t>(c)].advance;
  return w;
}

void UiFonts::draw(Gpu& gpu, Ui2D& out, const Desc& d, std::string_view text, float x0, float y0, float x1, float y1, int align_h, int align_v,
                   float screen_h, const float* color) {
  const float k = screen_h / std::max(1.f, d.ref_height);
  const Face* f = face(gpu, d.file, static_cast<int>(std::lround(d.size * k)));
  if (!f || text.empty()) return;
  float w = 0;
  for (char c : text) w += f->glyphs[static_cast<uint8_t>(c)].advance;
  const float x = std::floor(align_h == 1 ? (x0 + x1 - w) * 0.5f : align_h == 2 ? x1 - w : x0);
  const float y = std::floor(align_v == 1 ? (y0 + y1 - f->height) * 0.5f : align_v == 2 ? y1 - f->height : y0);
  auto pass = [&](float dx, float dy, const float c[4]) {
    float pen = x + dx;
    for (char ch : text) {
      const Glyph& g = f->glyphs[static_cast<uint8_t>(ch)];
      if (g.w > 0) out.quad(f->tex.Get(), pen - g.left, y + dy, pen - g.left + g.w, y + dy + g.h, g.u0, g.v0, g.u1, g.v1, c);
      pen += g.advance;
    }
  };
  // the shadow, the outline (the text again around itself, in the outline's colour), then the text
  const float sx = std::round(d.shadow_x * k), sy = std::round(d.shadow_y * k);
  if (sx != 0 || sy != 0) pass(sx, sy, d.shadow_color);
  const float o = d.outline > 0 ? std::max(1.f, std::round(d.outline * k)) : 0.f;
  if (o > 0)
    for (int dy = -1; dy <= 1; ++dy)
      for (int dx = -1; dx <= 1; ++dx)
        if (dx || dy) pass(static_cast<float>(dx) * o, static_cast<float>(dy) * o, d.outline_color);
  pass(0, 0, color ? color : d.color);
}

// ---------------------------------------------------------------- scenes

bool UiScene::load(const Wad& ui, const std::string& path) {
  auto bytes = ui.read(path);
  if (!bytes) return false;
  const PropertyBin bin(*bytes);
  int order = 0;
  for (const BinEntry& e : bin.entries()) {
    if (e.cls == fnv1a("UISceneData")) {
      Scene s;
      if (const BinValue* p = e.field("ParentScene")) s.parent = static_cast<uint32_t>(p->u);
      if (const BinValue* en = e.field("Enabled")) s.enabled = en->number() != 0;  // [meta default false]
      if (const BinValue* l = e.field("Layer")) s.layer = static_cast<int>(l->number());
      scenes_[e.name] = s;
      continue;
    }
    UiElement el;
    el.hash = e.name, el.cls = e.cls, el.order = order++;
    if (const BinValue* n = e.field("name")) {
      const size_t slash = n->str.rfind('/');
      el.name = slash == std::string::npos ? n->str : n->str.substr(slash + 1);
    }
    if (const BinValue* s = e.field("Scene")) el.scene = static_cast<uint32_t>(s->u);
    if (const BinValue* en = e.field("Enabled")) el.enabled = en->number() != 0;
    if (const BinValue* l = e.field("Layer")) el.layer = static_cast<int>(l->number());
    if (const BinValue* pos = e.field("Position")) {
      el.full_screen = pos->cls == fnv1a("UiPositionFullScreen");
      if (const BinValue* rect = pos->field("UIRect")) {
        if (const BinValue* p = rect->field("Position")) el.x = static_cast<float>(p->num[0]), el.y = static_cast<float>(p->num[1]);
        if (const BinValue* s = rect->field("Size")) el.w = static_cast<float>(s->num[0]), el.h = static_cast<float>(s->num[1]);
        if (const BinValue* v = rect->field("SourceResolutionWidth")) el.src_w = static_cast<float>(v->number());
        if (const BinValue* v = rect->field("SourceResolutionHeight")) el.src_h = static_cast<float>(v->number());
      }
      if (const BinValue* anchors = pos->field("Anchors"))
        if (const BinValue* a = anchors->field("Anchor")) el.ax = static_cast<float>(a->num[0]), el.ay = static_cast<float>(a->num[1]);
    }
    const BinValue* tex = e.field("TextureData");
    if (!tex) tex = e.field("mAtlas");
    if (tex) {
      if (const BinValue* n = tex->field("mTextureName")) el.texture = lower(n->str);
      if (const BinValue* n = tex->field("TextureName")) el.texture = lower(n->str);  // LooseUiTextureData: a whole picture
      if (const BinValue* v = tex->field("mTextureSourceResolutionWidth")) el.tex_w = static_cast<float>(v->number());
      if (const BinValue* v = tex->field("mTextureSourceResolutionHeight")) el.tex_h = static_cast<float>(v->number());
      el.u1 = el.tex_w, el.v1 = el.tex_h;
      if (const BinValue* uv = tex->field("mTextureUV"))
        el.u0 = static_cast<float>(uv->num[0]), el.v0 = static_cast<float>(uv->num[1]), el.u1 = static_cast<float>(uv->num[2]), el.v1 = static_cast<float>(uv->num[3]);
    }
    rgba(e.field("Color"), el.color);
    if (const BinValue* f = e.field("FlipX")) el.flip_x = f->number() != 0;
    if (const BinValue* f = e.field("FlipY")) el.flip_y = f->number() != 0;
    if (const BinValue* f = e.field("TotalNumberOfFrames")) el.frames = static_cast<int>(f->number());
    if (const BinValue* f = e.field("NumberOfFramesPerRowInAtlas")) el.frames_per_row = std::max(1, static_cast<int>(f->number()));
    if (const BinValue* f = e.field("FramesPerSecond")) el.fps = static_cast<float>(f->number());
    if (const BinValue* m = e.field("MinimumSaturation")) el.min_saturation = static_cast<float>(m->number());
    if (const BinValue* f = e.field("FontDescription")) el.font = static_cast<uint32_t>(f->u);
    if (const BinValue* a = e.field("TextAlignmentHorizontal")) el.align_h = static_cast<int>(a->number());
    if (const BinValue* a = e.field("TextAlignmentVertical")) el.align_v = static_cast<int>(a->number());
    if (const BinValue* bars = e.field("BarElements"))
      for (const BinValue& b : bars->items) el.bars.push_back(static_cast<uint32_t>(b.u));
    if (const BinValue* h = e.field("HitRegionElement")) el.hit_region = static_cast<uint32_t>(h->u);
    if (const BinValue* st = e.field("DefaultStateElements")) {
      if (const BinValue* list = st->field("DisplayElements"))
        for (const BinValue& d : list->items) el.default_display.push_back(static_cast<uint32_t>(d.u));
      if (const BinValue* t = st->field("TextElement")) el.default_text = static_cast<uint32_t>(t->u);
    }
    if (const BinValue* k = e.field("TRAKey")) el.tra_key = k->str;
    if (const BinValue* tip = e.field("TipStyle"))
      if (const BinValue* tips = tip->field("DirectionalTipElements"))
        for (const BinValue& t : tips->items) el.tips.push_back(static_cast<uint32_t>(t.u));
    index_[el.hash] = elements_.size();
    elements_.push_back(std::move(el));
  }
  return !elements_.empty();
}

UiElement* UiScene::find(uint32_t hash) {
  auto it = index_.find(hash);
  return it == index_.end() ? nullptr : &elements_[it->second];
}

void UiScene::show_scene(uint32_t scene, bool shown) {
  auto it = scenes_.find(scene);
  if (it != scenes_.end()) it->second.enabled = shown;
}

bool UiScene::scene_shown(uint32_t scene, int depth) const {
  auto it = scenes_.find(scene);
  if (it == scenes_.end() || depth > 8) return true;
  return it->second.enabled && (!it->second.parent || scene_shown(it->second.parent, depth + 1));
}

int UiScene::scene_layer(uint32_t scene) const {
  auto it = scenes_.find(scene);
  return it == scenes_.end() ? 0 : it->second.layer;
}

void UiScene::place(const UiElement& e, float w, float h, float& x0, float& y0, float& x1, float& y1) const {
  if (e.full_screen) {
    x0 = y0 = 0, x1 = w, y1 = h;
    return;
  }
  const float k = h / std::max(1.f, e.src_h);
  x0 = e.ax * w + (e.x + e.shift_x - e.ax * e.src_w) * k;
  y0 = e.ay * h + (e.y - e.ay * e.src_h) * k;
  x1 = x0 + e.w * k;
  y1 = y0 + e.h * k;
}

void UiScene::meter(uint32_t group, float fraction) {
  UiElement* g = find(group);
  if (!g) return;
  fraction = std::clamp(fraction, 0.f, 1.f);
  float width = 0;
  for (uint32_t b : g->bars)
    if (UiElement* bar = find(b)) bar->fill_x = fraction, width = std::max(width, bar->w);
  for (uint32_t t : g->tips)
    if (UiElement* tip = find(t)) tip->shift_x = -(1.f - fraction) * width;
}

void UiScene::localize(const StringTable& strings) {
  for (UiElement& e : elements_)
    if (!e.tra_key.empty() && e.text.empty()) e.text = strings.get(e.tra_key);
}

void UiScene::show_button_defaults() {
  for (size_t i = 0; i < elements_.size(); ++i) {
    if (elements_[i].cls != fnv1a("UiElementGroupButtonData")) continue;
    const std::vector<uint32_t> shown = elements_[i].default_display;
    const uint32_t text = elements_[i].default_text;
    for (uint32_t d : shown)
      if (UiElement* e = find(d)) e->enabled = true;
    if (UiElement* t = text ? find(text) : nullptr) t->enabled = true;
  }
}

void UiScene::draw(Gpu& gpu, Ui2D& out, UiFonts& fonts, float w, float h) {
  std::vector<const UiElement*> shown;
  for (const UiElement& e : elements_)
    if (e.enabled && (e.w > 0 || e.h > 0 || e.full_screen) && scene_shown(e.scene)) shown.push_back(&e);
  auto scene_layer = [&](const UiElement* e) {
    auto it = scenes_.find(e->scene);
    return it == scenes_.end() ? 0 : it->second.layer;
  };
  std::stable_sort(shown.begin(), shown.end(), [&](const UiElement* a, const UiElement* b) {
    const int sa = scene_layer(a), sb = scene_layer(b);
    if (sa != sb) return sa < sb;
    if (a->layer != b->layer) return a->layer < b->layer;
    // within a layer: a full-screen backdrop lies under the rest [dedus: the loading screen's background and its
    // latency text share layer 0, the text first in the file], then the file's order
    if (a->full_screen != b->full_screen) return a->full_screen;
    return a->order < b->order;
  });
  for (const UiElement* e : shown) draw_element(gpu, out, fonts, *e, w, h);
}

void UiScene::draw_element(Gpu& gpu, Ui2D& out, UiFonts& fonts, const UiElement& element, float w, float h, float dx, float dy) const {
  const UiElement* e = &element;
  float x0, y0, x1, y1;
  place(*e, w, h, x0, y0, x1, y1);
  x0 += dx, x1 += dx, y0 += dy, y1 += dy;
  if (e->font) {
    if (e->text.empty()) return;
    if (const UiFonts::Desc* d = fonts.desc(e->font))
      fonts.draw(gpu, out, *d, e->text, x0, y0, x1, y1, e->align_h, e->align_v, h, e->text_color[3] > 0 ? e->text_color : nullptr);
    return;
  }
  // sweeps (cooldowns, ammo, bounties) show only while their controller runs them
  const bool sweeps = e->cls == fnv1a("UiElementEffectCooldownRadialData") || e->cls == fnv1a("UiElementEffectCooldownData") ||
                      e->cls == fnv1a("UiElementEffectAmmoData");
  if (sweeps && e->sweep <= 0) return;
  ID3D11ShaderResourceView* tex = e->image ? e->image : e->texture.empty() ? nullptr : out.texture(gpu, e->texture);
  if (!tex) return;
  float u0 = e->u0 / e->tex_w, v0 = e->v0 / e->tex_h, u1 = e->u1 / e->tex_w, v1 = e->v1 / e->tex_h;
  if (e->image) u0 = e->iu0, v0 = e->iv0, u1 = e->iu1, v1 = e->iv1;
  if (e->frames > 0 && !e->image) {
    // a flipbook: the cut-out is frame 0's; the frames follow it in rows that share the atlas evenly
    const int rows = (e->frames + e->frames_per_row - 1) / e->frames_per_row;
    const int f = ((e->frame % e->frames) + e->frames) % e->frames;
    const float du = static_cast<float>(f % e->frames_per_row) / static_cast<float>(e->frames_per_row);
    const float dv = static_cast<float>(f / e->frames_per_row) / static_cast<float>(rows);
    u0 += du, u1 += du, v0 += dv, v1 += dv;
  }
  if (e->flip_x) std::swap(u0, u1);
  if (e->flip_y) std::swap(v0, v1);
  if (e->cls == fnv1a("UiElementEffectCircleMaskDesaturateData")) {
    // a picture cut to the circle inside its rectangle (a summoner's icon): a fan of triangles around the centre
    const float cx = (x0 + x1) * 0.5f, cy = (y0 + y1) * 0.5f, cu = (u0 + u1) * 0.5f, cv = (v0 + v1) * 0.5f;
    const int steps = 48;
    for (int i = 0; i < steps; ++i) {
      const float a = 6.2831853f * static_cast<float>(i) / steps, b = 6.2831853f * static_cast<float>(i + 1) / steps;
      const float xy[6] = {cx, cy, cx + std::cos(a) * (x1 - x0) * 0.5f, cy + std::sin(a) * (y1 - y0) * 0.5f,
                           cx + std::cos(b) * (x1 - x0) * 0.5f, cy + std::sin(b) * (y1 - y0) * 0.5f};
      const float uv[6] = {cu, cv, cu + std::cos(a) * (u1 - u0) * 0.5f, cv + std::sin(a) * (v1 - v0) * 0.5f,
                           cu + std::cos(b) * (u1 - u0) * 0.5f, cv + std::sin(b) * (v1 - v0) * 0.5f};
      out.triangle(tex, xy, uv, e->color);
    }
    return;
  }
  if (e->sweep > 0) {
    // a cooldown sweep: what is left of the turn, clockwise from the top, as a fan of triangles around the centre
    // [de măsurat: the direction and where it starts]
    const float cx = (x0 + x1) * 0.5f, cy = (y0 + y1) * 0.5f, cu = (u0 + u1) * 0.5f, cv = (v0 + v1) * 0.5f;
    auto edge = [&](float turn, float& px, float& py, float& pu, float& pv) {
      // the point of the rectangle's border at `turn` (0..1 of a turn, clockwise from the top)
      const float a = turn * 6.2831853f, dx = std::sin(a), dy = -std::cos(a);
      const float t = 1.f / std::max(std::fabs(dx), std::fabs(dy));
      px = cx + dx * t * (x1 - x0) * 0.5f, py = cy + dy * t * (y1 - y0) * 0.5f;
      pu = cu + dx * t * (u1 - u0) * 0.5f, pv = cv + dy * t * (v1 - v0) * 0.5f;
    };
    const float from = 1.f - std::clamp(e->sweep, 0.f, 1.f);
    const int steps = 32;
    for (int i = 0; i < steps; ++i) {
      const float a = from + (1.f - from) * static_cast<float>(i) / steps, b = from + (1.f - from) * static_cast<float>(i + 1) / steps;
      float xy[6] = {cx, cy}, uv[6] = {cu, cv};
      edge(a, xy[2], xy[3], uv[2], uv[3]);
      edge(b, xy[4], xy[5], uv[4], uv[5]);
      out.triangle(tex, xy, uv, e->color, e->saturation);
    }
    return;
  }
  // the part shown: from the left (meters), from the bottom (the experience bar)
  if (e->fill_x < 1) x1 = x0 + (x1 - x0) * e->fill_x, u1 = u0 + (u1 - u0) * e->fill_x;
  if (e->fill_y < 1) y0 = y1 - (y1 - y0) * e->fill_y, v0 = v1 - (v1 - v0) * e->fill_y;
  if (x1 <= x0 || y1 <= y0) return;
  out.quad(tex, x0, y0, x1, y1, u0, v0, u1, v1, e->color, e->saturation);
}

}  // namespace ba
