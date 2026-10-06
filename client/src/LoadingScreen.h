#pragma once
// The loading screen, drawn from the client's own data (UI.wad.client), like the match interface:
//   loadingscreen.bin: the view controllers of the "LoadingScreen" client state, per game mode. Summoner's Rift
//     (CLASSIC, PRACTICETOOL ...) loads LoadingScreenClassic, PlayerCards/PlayerCardsClassic and PlayerCardSwitcher.
//   loadingscreen.loadingscreenclassic.bin (LoadingScreenClassicViewController): the background (the game mode's
//     LoadingScreenBackground, map11.bin), the progress meter and its text, the latency icon per threshold and its
//     text, the tips' text, the version text; its scene: clientstates/loadingscreen/ux/loadingscreenclassic/uibase
//     (which also holds the spinner, a 32-frame flipbook at 30 frames a second).
//   loadingscreen.playercardsclassic.bin (LoadingScreenPlayerCardsViewController): the card template (its main scene,
//     its three faces LSPC0 gameplay / LSPC1 mastery / LSPC2 player info, the character splash, the names, the
//     summoner's icon, spells and runes, the ranked frames) and the two regions the cards are laid out in (upper,
//     lower); its scene: clientstates/loadingscreen/ux/playercards/uishared.
//
// What the data does not say [dedus, de măsurat]: the cards of a team stand side by side, each as wide as the
// template's hit region, centred in their region (the upper one for Order, the lower one for Chaos); the regions span
// the screen's width. The meter shows this client's own loading. Tips (LoadScreenTip) are not shown yet.

#include <string>
#include <vector>

#include "Gpu.h"
#include "Ui.h"
#include "ba/Wad.h"

namespace ba {

class LoadingScreen {
 public:
  struct Player {
    std::string name;             // the summoner's name
    std::string character_name;   // the champion's (or its skin's) name, as the texts give it
    int team = 0;                 // 0 Order (upper row), 1 Chaos (lower row)
    ID3D11ShaderResourceView* splash = nullptr;  // the skin's loadscreen picture
    ID3D11ShaderResourceView* icon = nullptr;    // the summoner's icon
  };

  bool load(Gpu& gpu, const Wad& ui);
  /** Another archive to look pictures up in (the map's, for the background; the champions'). */
  void add_wad(const Wad* wad) { ui_.add_wad(wad); }
  ID3D11ShaderResourceView* image(Gpu& gpu, const std::string& path) { return ui_.texture(gpu, path); }
  /** The game mode's LoadingScreenBackground. */
  void background(Gpu& gpu, const std::string& path);
  void players(std::vector<Player> list) { players_ = std::move(list); }
  /** This client's loading, 0..1. */
  void progress(float fraction);
  /** The round trip to the server in milliseconds; negative: not known. */
  void latency(int ms);
  /** Draws the screen onto the bound target; `seconds` runs the spinner. */
  void draw(Gpu& gpu, double seconds);
  bool ok() const { return ok_; }

 private:
  Ui2D ui_;
  UiFonts fonts_;
  bool ok_ = false;
  // LoadingScreenClassic
  UiScene scene_;
  UiElement* background_ = nullptr;
  uint32_t meter_ = 0;
  UiElement* progress_text_ = nullptr;
  UiElement* latency_text_ = nullptr;
  UiElement* spinner_ = nullptr;
  struct Threshold {
    float from = 0;
    float color[4] = {1, 1, 1, 1};
    UiElement* icon = nullptr;
  };
  std::vector<Threshold> thresholds_;
  // the player cards
  UiScene cards_;
  bool cards_ok_ = false;
  std::vector<UiElement*> card_elements_;  // the template's main scene, its gameplay face and its frame, in drawing order
  UiElement* hit_region_ = nullptr;
  UiElement* regions_[2] = {nullptr, nullptr};  // UpperCardRegion, LowerCardRegion
  UiElement* splash_ = nullptr;
  UiElement* character_name_ = nullptr;
  UiElement* summoner_name_ = nullptr;
  UiElement* summoner_icon_ = nullptr;
  std::vector<Player> players_;
};

}  // namespace ba
