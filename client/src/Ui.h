#pragma once
// League's interface system, as the client's data describes it (UI.wad.client):
//   a scene file (clientstates/gameplay/ux/.../uibase) holds UISceneData (a layer, a parent, enabled or not) and the
//   elements of each scene: UiElementIconData (a rectangle of a 1600 x 1200 layout showing a cut-out of an atlas),
//   UiElementTextData (a rectangle, a font description, an alignment), UiElementRegionData (a bare rectangle), effects
//   (a fill percentage, a desaturated icon, a cooldown sweep ...) and groups (a meter: its bar elements and its tip).
//   Elements a file does not mark Enabled stay hidden until the view controller that owns them shows them.
//   ux/fonts: GameFontDescription (colour, outline and shadow colours) -> FontType (the font file) and
//   FontResolutionData (size, outline and shadow depth at a reference screen height).
//
// Layout [dedus, de măsurat]: a scene is laid out for its source resolution and scaled by screen height / source
// height; an element keeps its offset from its anchor (AnchorSingle: a point of the screen, 0..1).
// Fonts are drawn by Windows (GDI) from the game's own font files.

#include <array>
#include <map>
#include <memory>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

#include "Gpu.h"
#include "ba/PropertyBin.h"
#include "ba/Wad.h"

namespace ba {

/** An interface colour field as red, green, blue, alpha in 0..1 (the files keep blue first). */
void ui_color(const BinValue* v, float out[4]);

/** Textured, tinted rectangles in screen pixels, drawn in the order they were asked for. */
class Ui2D {
 public:
  bool init(Gpu& gpu);
  /** `saturation` below 1 greys the texture out (UiElementEffectDesaturateData). */
  void quad(ID3D11ShaderResourceView* tex, float x0, float y0, float x1, float y1, float u0, float v0, float u1, float v1, const float color[4],
            float saturation = 1.f);
  /** A convex fan of points around a centre (the cooldown sweep), in one colour over a texture's cut-out. */
  void triangle(ID3D11ShaderResourceView* tex, const float xy[6], const float uv[6], const float color[4], float saturation = 1.f);
  void flush(Gpu& gpu);
  /** A texture of one of the wads given to `add_wad`, by its path (any case); cached. Null when there is none. */
  ID3D11ShaderResourceView* texture(Gpu& gpu, const std::string& path);
  void add_wad(const Wad* wad) { wads_.push_back(wad); }
  ID3D11ShaderResourceView* white() const { return white_.Get(); }

 private:
  struct Vertex {
    float x, y, u, v;
    float r, g, b, a;
    float saturation;
  };
  struct Run {
    ID3D11ShaderResourceView* tex;
    size_t first, count;
  };
  void run(ID3D11ShaderResourceView* tex, size_t count);
  std::vector<Vertex> verts_;
  std::vector<Run> runs_;
  std::vector<const Wad*> wads_;
  std::map<std::string, ComPtr<ID3D11ShaderResourceView>> textures_;
  ComPtr<ID3D11ShaderResourceView> white_;
  ComPtr<ID3D11VertexShader> vs_;
  ComPtr<ID3D11PixelShader> ps_;
  ComPtr<ID3D11InputLayout> layout_;
  ComPtr<ID3D11Buffer> vb_, cb_;
  ComPtr<ID3D11BlendState> blend_;
  ComPtr<ID3D11SamplerState> sampler_;
  ComPtr<ID3D11RasterizerState> raster_;
  ComPtr<ID3D11DepthStencilState> no_depth_;
  size_t vb_capacity_ = 0;
};

/** The game's fonts: descriptions from ux/fonts, glyphs drawn by Windows from the game's own font files. */
class UiFonts {
 public:
  bool load(const Wad& ui);
  struct Desc {
    std::string file;                  // FontType's first locale (en_us): mFontFilePath
    float size = 10, ref_height = 1080;  // FontResolution fontSize at screenHeight [meta defaults 10, 1080]
    float outline = 0, shadow_x = 0, shadow_y = 0;
    float color[4] = {0, 0, 0, 1}, outline_color[4] = {0, 0, 0, 1}, shadow_color[4] = {0, 0, 0, 1};
  };
  const Desc* desc(uint32_t hash) const;
  /** Width in pixels of `text` in a description's font on a screen `screen_h` high. */
  float width(Gpu& gpu, const Desc& d, std::string_view text, float screen_h);
  /** Draws `text` inside a rectangle: `align_h` 0 left, 1 centre, 2 right; `align_v` 0 top, 1 centre, 2 bottom. */
  void draw(Gpu& gpu, Ui2D& out, const Desc& d, std::string_view text, float x0, float y0, float x1, float y1, int align_h, int align_v, float screen_h,
            const float* color = nullptr);

 private:
  struct Glyph {
    float u0 = 0, v0 = 0, u1 = 0, v1 = 0;
    float w = 0, h = 0, left = 0;  // the cell, and how far left of the pen it starts
    float advance = 0;
  };
  struct Face {
    ComPtr<ID3D11ShaderResourceView> tex;
    std::array<Glyph, 256> glyphs{};
    float ascent = 0, height = 0;
  };
  const Face* face(Gpu& gpu, const std::string& file, int px);
  const Wad* ui_ = nullptr;
  std::unordered_map<uint32_t, Desc> descs_;
  std::map<std::string, std::wstring> families_;  // font file -> the family Windows knows it by (empty: not loaded)
  std::map<std::string, int> weights_;
  std::map<std::pair<std::string, int>, std::unique_ptr<Face>> faces_;
};

struct UiElement {
  uint32_t hash = 0, cls = 0, scene = 0;
  std::string name;  // the last part of its path: "PlayerHP_ValueText"
  bool enabled = false;
  int layer = 0;
  int order = 0;
  // UiPositionRect
  float x = 0, y = 0, w = 0, h = 0, src_w = 1600, src_h = 1200;
  float ax = 0, ay = 0;  // AnchorSingle
  bool full_screen = false;  // UiPositionFullScreen: it covers the screen
  bool flip_x = false, flip_y = false;  // FlipX / FlipY: its cut-out mirrored
  // AtlasData
  std::string texture;
  float u0 = 0, v0 = 0, u1 = 0, v1 = 0, tex_w = 1, tex_h = 1;
  float color[4] = {1, 1, 1, 1};
  // text
  uint32_t font = 0;
  int align_h = 0, align_v = 1;  // [meta defaults]
  // UiElementEffectAnimationData: a flipbook, its first frame's cut-out in the atlas data above
  int frames = 0, frames_per_row = 1;  // TotalNumberOfFrames, NumberOfFramesPerRowInAtlas
  float fps = 0;                       // FramesPerSecond
  // groups
  std::vector<uint32_t> bars, tips;  // UiElementGroupMeterData BarElements, TipStyle DirectionalTipElements
  // UiElementGroupButtonData: where it is clicked, and what shows in its plain state
  uint32_t hit_region = 0;
  std::vector<uint32_t> default_display;
  uint32_t default_text = 0;     // DefaultStateElements TextElement
  std::string tra_key;           // TRAKey: the localised text it shows (set by the scene's localize)

  // ---- what its view controller made of it
  std::string text;
  float fill_x = 1, fill_y = 1;   // the part shown, from the left / from the bottom (meters, the experience bar)
  float shift_x = 0;              // moved along x, in layout units (a meter's tip)
  float saturation = 1;
  float min_saturation = 0;       // UiElementEffectDesaturateData MinimumSaturation: how grey an unavailable icon gets
  float sweep = 0;                // a cooldown sweep: the part of the turn still covered (0: none)
  int frame = 0;                  // a flipbook's frame
  ID3D11ShaderResourceView* image = nullptr;  // a picture from elsewhere (a champion's icon, a spell's)
  float iu0 = 0, iv0 = 0, iu1 = 1, iv1 = 1;
  float text_color[4] = {0, 0, 0, 0};          // alpha 0: the font description's own
};

/** One scene file: its scenes and elements, laid out and drawn. */
class UiScene {
 public:
  bool load(const Wad& ui, const std::string& path);
  UiElement* find(uint32_t hash);
  /** The element a link field of a view controller names, or null. */
  UiElement* find(const BinValue* link) { return link ? find(static_cast<uint32_t>(link->u)) : nullptr; }
  /** The element's rectangle on a screen of `w` x `h` pixels. */
  void place(const UiElement& e, float w, float h, float& x0, float& y0, float& x1, float& y1) const;
  /** Shows or hides a whole scene (its view controller's doing). */
  void show_scene(uint32_t scene, bool shown);
  /** Fills a meter (UiElementGroupMeterData): its bars show `fraction` of themselves and its tip sits at their end. */
  void meter(uint32_t group, float fraction);
  void draw(Gpu& gpu, Ui2D& out, UiFonts& fonts, float w, float h);
  /** Fills every element that names a TRAKey with its text (texts a controller sets later win). */
  void localize(const class StringTable& strings);
  /** Shows each button's plain state: its DefaultStateElements (display elements and text). */
  void show_button_defaults();
  /** One element, wherever its scene or state, moved by (dx, dy) pixels (a template drawn for each of many items). */
  void draw_element(Gpu& gpu, Ui2D& out, UiFonts& fonts, const UiElement& e, float w, float h, float dx = 0, float dy = 0) const;
  size_t size() const { return elements_.size(); }
  /** Every element, in the file's order (a controller that draws a template many times picks its own from them). */
  std::vector<UiElement>& elements() { return elements_; }
  /** The layer of a scene (UISceneData Layer), 0 for one the file does not have. */
  int scene_layer(uint32_t scene) const;

 private:
  struct Scene {
    uint32_t parent = 0;
    bool enabled = false;
    int layer = 0;
  };
  bool scene_shown(uint32_t scene, int depth = 0) const;
  std::vector<UiElement> elements_;
  std::unordered_map<uint32_t, size_t> index_;
  std::unordered_map<uint32_t, Scene> scenes_;
};

}  // namespace ba
