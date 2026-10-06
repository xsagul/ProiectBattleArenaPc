#include "LoadingScreen.h"

#include <algorithm>
#include <cmath>
#include <cstdio>

#include "ba/Hash.h"
#include "ba/PropertyBin.h"

namespace ba {

namespace {

const BinEntry* controller(const PropertyBin& bin, const char* cls) {
  for (const BinEntry& e : bin.entries())
    if (e.cls == fnv1a(cls)) return &e;
  return nullptr;
}

uint32_t link(const BinValue* v) { return v ? static_cast<uint32_t>(v->u) : 0; }

/** The element a list of links names at `index` (a card keeps one element per face), or null. */
UiElement* at(UiScene& scene, const BinValue* list, size_t index) {
  return list && index < list->items.size() ? scene.find(static_cast<uint32_t>(list->items[index].u)) : nullptr;
}

}  // namespace

bool LoadingScreen::load(Gpu& gpu, const Wad& ui) {
  if (!ui_.init(gpu)) return false;
  ui_.add_wad(&ui);
  fonts_.load(ui);

  // ---- LoadingScreenClassic: background, progress meter, latency, spinner
  auto classic_bytes = ui.read("loadingscreen.loadingscreenclassic.bin");
  if (!classic_bytes || !scene_.load(ui, "clientstates/loadingscreen/ux/loadingscreenclassic/uibase")) return false;
  const PropertyBin classic(*classic_bytes);
  const BinEntry* c = controller(classic, "LoadingScreenClassicViewController");
  if (!c) return false;
  if (const BinValue* bg = c->field("Background")) background_ = scene_.find(bg->field("Background"));
  if (const BinValue* pm = c->field("ProgressMeter")) {
    meter_ = link(pm->field("Meter"));
    progress_text_ = scene_.find(pm->field("Text"));
  }
  if (const BinValue* lat = c->field("Latency")) {
    latency_text_ = scene_.find(lat->field("Text"));
    if (const BinValue* list = lat->field("Thresholds"))
      for (const BinValue& t : list->items) {
        Threshold th;
        if (const BinValue* v = t.field("Threshold")) th.from = static_cast<float>(v->number());
        ui_color(t.field("textColor"), th.color);
        th.icon = scene_.find(t.field("image"));
        thresholds_.push_back(th);
      }
  }
  for (UiElement& e : scene_.elements())
    if (e.cls == fnv1a("UiElementEffectAnimationData")) spinner_ = &e;
  ok_ = true;
  progress(0);
  latency(-1);

  // ---- the player cards
  auto cards_bytes = ui.read("loadingscreen.playercardsclassic.bin");
  if (!cards_bytes || !cards_.load(ui, "clientstates/loadingscreen/ux/playercards/uishared")) return true;
  const PropertyBin cards(*cards_bytes);
  const BinEntry* pc = controller(cards, "LoadingScreenPlayerCardsViewController");
  const BinValue* card = pc ? pc->field("CardTemplate") : nullptr;
  if (!card) return true;
  regions_[0] = cards_.find(pc->field("UpperCardRegion"));
  regions_[1] = cards_.find(pc->field("LowerCardRegion"));
  hit_region_ = cards_.find(card->field("HitRegion"));
  splash_ = cards_.find(card->field("CharacterSplash"));
  // the gameplay face is the first of the card's state scenes (LSPC0, the one the file enables)
  const uint32_t main_scene = link(card->field("MainScene"));
  uint32_t face = 0;
  if (const BinValue* states = card->field("StateScenes"); states && !states->items.empty()) face = static_cast<uint32_t>(states->items[0].u);
  character_name_ = at(cards_, card->field("CharacterSkinName"), 0);
  if (const BinValue* n = card->field("SummonerName")) summoner_name_ = at(cards_, n->field("SummonerName"), 0);
  summoner_icon_ = at(cards_, card->field("SummonerIcon"), 0);
  // the frame around the card: unranked players of both teams share the default one
  UiElement* frame = nullptr;
  if (const BinEntry* frames = cards.entry(link(card->field("RankedFrames")))) frame = cards_.find(frames->field("DefaultFrame"));
  for (UiElement& e : cards_.elements())
    if ((e.enabled && (e.scene == main_scene || e.scene == face)) || &e == frame) card_elements_.push_back(&e);
  std::stable_sort(card_elements_.begin(), card_elements_.end(), [&](const UiElement* a, const UiElement* b) {
    const int sa = cards_.scene_layer(a->scene), sb = cards_.scene_layer(b->scene);
    if (sa != sb) return sa < sb;
    if (a->layer != b->layer) return a->layer < b->layer;
    return a->order < b->order;
  });
  cards_ok_ = hit_region_ && regions_[0] && regions_[1] && splash_ && !card_elements_.empty();
  return true;
}

void LoadingScreen::background(Gpu& gpu, const std::string& path) {
  if (background_) background_->image = ui_.texture(gpu, path);
}

void LoadingScreen::progress(float fraction) {
  fraction = std::clamp(fraction, 0.f, 1.f);
  scene_.meter(meter_, fraction);
  if (progress_text_) {
    // the texts' own form: "@NUMBER@%"
    char buf[16];
    std::snprintf(buf, sizeof buf, "%d%%", static_cast<int>(fraction * 100.f));
    progress_text_->text = buf;
  }
}

void LoadingScreen::latency(int ms) {
  // the icon and the text colour of the last threshold the latency reaches; not known: the last one (grey)
  const Threshold* now = nullptr;
  for (const Threshold& t : thresholds_) {
    if (t.icon) t.icon->enabled = false;
    if (ms >= 0 && static_cast<float>(ms) >= t.from) now = &t;
  }
  if (ms < 0 && !thresholds_.empty()) now = &thresholds_.back();
  if (now && now->icon) now->icon->enabled = true;
  if (latency_text_) {
    // the texts' own form: "@MS@ ms"
    latency_text_->text = ms >= 0 ? std::to_string(ms) + " ms" : std::string();
    if (now)
      for (int i = 0; i < 4; ++i) latency_text_->text_color[i] = now->color[i];
  }
}

void LoadingScreen::draw(Gpu& gpu, double seconds) {
  if (!ok_) return;
  const float w = static_cast<float>(gpu.width()), h = static_cast<float>(gpu.height());
  if (spinner_ && spinner_->frames > 0) spinner_->frame = static_cast<int>(seconds * spinner_->fps) % spinner_->frames;
  scene_.draw(gpu, ui_, fonts_, w, h);
  if (cards_ok_) {
    const float k = h / std::max(1.f, hit_region_->src_h);
    const float card_w = hit_region_->w * k;
    for (int team = 0; team < 2; ++team) {
      std::vector<const Player*> row;
      for (const Player& p : players_)
        if (p.team == team) row.push_back(&p);
      const float y = regions_[team]->y * k;
      const float left = (w - card_w * static_cast<float>(row.size())) * 0.5f;
      for (size_t i = 0; i < row.size(); ++i) {
        const Player& p = *row[i];
        splash_->image = p.splash;
        if (character_name_) character_name_->text = p.character_name;
        if (summoner_name_) summoner_name_->text = p.name;
        if (summoner_icon_) summoner_icon_->image = p.icon;
        const float x = std::floor(left + card_w * static_cast<float>(i));
        for (const UiElement* e : card_elements_) {
          if (e == summoner_icon_ && !p.icon) continue;
          cards_.draw_element(gpu, ui_, fonts_, *e, w, h, x, y);
        }
      }
    }
  }
  ui_.flush(gpu);
}

}  // namespace ba
