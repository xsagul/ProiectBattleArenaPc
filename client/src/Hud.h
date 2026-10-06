#pragma once
// The match interface, drawn from the client's own interface data (UI.wad.client), never laid out by hand. Each part
// has a view controller entry (gameplay.<part>.bin) that names, by role, the elements of its scene file
// (clientstates/gameplay/ux/lol/<part>/uibase): what the controllers do with them is the game's code, written here
// from what each role is called.
//   floating health bars: gameplay.lolfloatinginfobars.bin, InfoBarStyleSourceMap: a skin's unitHealthBarStyle -> the
//     bar of that kind of unit (its anchor, its border, its health meter; one meter per colour for champions).
//   the player's frame: gameplay.playerframe.bin (PlayerFrameViewController): portrait, level, health and resource
//     meters, experience bar, the spell slots.
//   the stats panel: gameplay.playerstats.bin (PlayerHeroStatsViewController), a text per stat.
//   the inventory: gameplay.playerinventory.bin (PlayerInventoryViewController): the item slots, the gold.
//   the game header: gameplay.lolgameheader.bin (LolGameStateViewController): score, minions killed, game time.
//   the item shop: gameplay.itemshop.bin (ItemShopViewController, HudItemShopData): its scene, the All Items tab's
//     region and groups (by epicness), the item card template (AllItemsIconDefinition) drawn once per item, the
//     purchase / sell buttons, the player's gold, the selected item's details.
//   the minimap: gameplay.lolminimap.bin (MinimapViewController, MinimapData mIcons: an icon per kind of unit with its
//     size and its colour per team); the map's picture is the map skin's mMinimapBackgroundConfig.

#include <array>
#include <map>
#include <string>
#include <vector>

#include "Gpu.h"
#include "Ui.h"
#include "ba/PropertyBin.h"
#include "ba/StringTable.h"
#include "ba/Wad.h"

namespace ba {

class Hud {
 public:
  bool load(Gpu& gpu, const Wad& ui);

  /** Whose bar it is, as the player sees it. */
  enum class Side { Self, Ally, Enemy };
  /** Queues a unit's floating health bar: `style` is its skin's unitHealthBarStyle, (x, y) the screen pixel its anchor
   *  goes to, `fraction` its health. */
  void health_bar(int style, float x, float y, float fraction, Side side);
  /** `hp_per_tick`: a unit bar's tick spacing (the skin's healthBarData hpPerTick; an outer turret's 1000 while it
   *  wears its plates); champions' bars space their ticks by their own tick style. */
  void health_bar(int style, float x, float y, float fraction, float max_hp, float shield_fraction, float decay_fraction, Side side,
                  float hp_per_tick = 0);

  /** Target frame: details of the selected unit. */
  struct TargetInfo {
    bool valid = false;
    uint32_t id = 0;
    std::string name;
    int level = 1;
    float hp = 0, max_hp = 0;
    float par = 0, max_par = 0;
    float shield = 0;
    float ad = 0, ap = 0, armor = 0, spell_block = 0, attack_speed = 0, move_speed = 0, crit = 0, ability_haste = 0;
    ID3D11ShaderResourceView* portrait = nullptr;
    std::array<ID3D11ShaderResourceView*, 7> item_icons{};
    std::array<int, 7> item_stacks{};
    int kills = 0, deaths = 0, assists = 0, cs = 0;
    Side side = Side::Enemy;
  };
  void target(const TargetInfo& t) { target_info_ = t; }

  /** Scoreboard (TAB): team rosters, kills, items, CS. */
  struct ScoreboardPlayer {
    uint32_t id = 0;
    std::string name;
    int level = 1;
    ID3D11ShaderResourceView* portrait = nullptr;
    std::array<ID3D11ShaderResourceView*, 7> item_icons{};
    std::array<int, 7> item_stacks{};
    int kills = 0, deaths = 0, assists = 0, cs = 0;
    bool dead = false;
    bool is_self = false;
  };
  struct ScoreboardView {
    bool open = false;
    int team_kills[2] = {0, 0};
    std::vector<ScoreboardPlayer> team1;
    std::vector<ScoreboardPlayer> team2;
  };
  void scoreboard(const ScoreboardView& s) { scoreboard_view_ = s; }

  /** End of Game (Victory / Defeat banner). */
  struct EndOfGame {
    bool shown = false;
    bool victory = true;
  };
  void end_of_game(const EndOfGame& e) { eog_ = e; }

  /** Floating combat text. */
  enum class FctType { Physical, Magic, True, Crit, Heal };
  void add_fct(float screen_x, float screen_y, float amount, FctType type);
  void update_fct(double dt);

  /** What the interface shows of the player's champion and of the match this frame. */
  struct Player {
    float hp = 0, max_hp = 0;
    float par = 0, max_par = 0;  // the ability resource (mana, energy ...); max 0: the champion has none
    int level = 1;
    float xp = 0;                // the part of the way to the next level
    ID3D11ShaderResourceView* portrait = nullptr;          // the skin's iconCircle
    std::array<ID3D11ShaderResourceView*, 4> spells{};     // each spell's mImgIconName
    ID3D11ShaderResourceView* passive = nullptr;           // the record's passive1IconName
    std::array<int, 4> spell_levels{};                     // 0: not learned
    std::array<float, 4> cooldown_left{}, cooldown_total{};  // seconds
    std::array<float, 4> costs{};
    int skill_points = 0;        // points waiting to be put into spells
    std::array<bool, 4> can_level{};  // the spells a point may go into now
    float gold = 0;
    float ad = 0, ap = 0, armor = 0, spell_block = 0, attack_speed = 0, move_speed = 0;
    float crit = 0, ability_haste = 0;
    std::array<ID3D11ShaderResourceView*, 7> item_icons{};  // the inventory (slot 6: the trinket); null: empty
    std::array<int, 7> item_stacks{};
    int selected_slot = -1;      // the inventory slot picked in the shop (to sell)
    int kills = 0, deaths = 0, assists = 0, minions_killed = 0;
    int team_kills[2] = {0, 0};  // the player's team, the other
    double game_seconds = 0;
    int fps = 0;
  };
  void player(const Player& p);

  /** The minimap's kinds of icon (MinimapData mIcons keys). */
  enum MapIcon { kChampion = 0, kTower = 1, kInhibitor = 3, kNexus = 5, kMinion = 7 };
  struct MapUnit {
    float x = 0, z = 0;
    int icon = kMinion;
    Side side = Side::Ally;
    ID3D11ShaderResourceView* portrait = nullptr;  // champions: the skin's iconCircle
  };
  /** The minimap this frame: the world rectangle its picture covers, the picture, the units on it, and the corners of
   *  what the camera sees on the ground (4 x, z pairs, or null). */
  void minimap(ID3D11ShaderResourceView* background, float min_x, float min_z, float max_x, float max_z, const std::vector<MapUnit>& units,
               const float* view_corners);

  /** Another archive to look pictures up in (the map's, for its minimap picture). */
  void add_wad(const Wad* wad) { ui_.add_wad(wad); }
  /** A picture of the interface's archives by its path (the minimap's background), or null. */
  ID3D11ShaderResourceView* image(Gpu& gpu, const std::string& path) { return ui_.texture(gpu, path); }

  /** The item shop this frame (when open). */
  struct ShopItem {
    int id = 0;
    ID3D11ShaderResourceView* icon = nullptr;
    int cost = 0;            // what buying it costs the player now (owned components counted)
    int epicness = 2;
    bool affordable = true;
  };
  struct ShopView {
    bool open = false;
    std::vector<ShopItem> items;  // what the mode sells, in the order shown inside each group
    int selected = 0;             // item id (0: none)
    std::string title, cost_text;  // the selected item's name and price
    ID3D11ShaderResourceView* selected_icon = nullptr;
    float gold = 0;
    std::vector<std::string> group_titles;  // one per group (AllItemGroupDefinitions), localised
  };
  void shop(const ShopView& v) { shop_view_ = v; }
  /** Scrolls the shop's All Items pane by whole rows (positive: down). */
  void scroll_shop(int rows) { shop_scroll_ = std::max(0, shop_scroll_ + rows); }
  /** Gives every scene its localised texts (TRAKey). */
  void localize(const StringTable& strings);
  /** The localisation keys of the shop's groups (AllItemGroupDefinitions groupName), in order. */
  std::vector<std::string> shop_group_keys() const;
  /** What is under a screen pixel: an item card (its id), a button, the shop window, an inventory slot. */
  enum ShopHit { kShopNothing = 0, kShopInside, kShopPurchase, kShopSell, kShopClose };
  int shop_hit(Gpu& gpu, int x, int y, int* item) const;
  int inventory_slot_at(Gpu& gpu, int x, int y) const;

  /** The spell whose level-up button is under a screen pixel (0 Q .. 3 R), or -1. */
  int level_button_at(Gpu& gpu, int x, int y);

  /** Hit test for clicking on the minimap, returning world x and z. */
  bool minimap_hit(Gpu& gpu, int screen_x, int screen_y, float& world_x, float& world_z) const;

  /** Draws what was queued onto the bound target (the back buffer, after the scene's anti-aliasing) and forgets it. */
  void draw(Gpu& gpu);
  size_t styles() const { return styles_.size(); }

 private:
  struct Style {
    const UiElement* anchor = nullptr;
    const UiElement* border = nullptr;
    const UiElement* bar = nullptr;
    std::map<uint32_t, const UiElement*> bars;  // AdditionalBarTypes: fnv1a("Blue" / "Green" / "Red" / "Yellow") -> meter
    // healthBarData TickStyle: HealthBarTickStyleUnit (StandardTick, spaced by the unit's hpPerTick) or
    // HealthBarTickStyleHero (StandardTick every HealthPerstandardTick, MicroTick between them: microTicksBetween of
    // the last MicroTickPerStandardTickData whose minHealth the maximum health reaches) [meta defaults 1000, 9]
    const UiElement* standard_tick = nullptr;
    const UiElement* micro_tick = nullptr;
    bool hero_ticks = false;
    float hp_per_standard_tick = 1000;
    std::vector<std::pair<float, int>> micro_ticks;  // minHealth -> microTicksBetween
  };
  struct Bar {
    const Style* style;
    float x, y, fraction;
    float max_hp = 0;
    float shield_fraction = 0;
    float decay_fraction = 0;
    Side side;
    float hp_per_tick = 0;
  };
  struct SpellSlot {
    UiElement* icon = nullptr;       // ContentElement
    UiElement* hotkey = nullptr;
    UiElement* border_on = nullptr;  // BorderEnabled
    UiElement* border_off = nullptr; // BorderDisabled
    UiElement* overlay_off = nullptr;  // OverlayDisabled
    UiElement* cooldown_text = nullptr;
    UiElement* cooldown_fx = nullptr;  // CooldownUiData RadialEffect
    UiElement* cost = nullptr;
    UiElement* cost_bg = nullptr;
    UiElement* oom = nullptr;          // OverlayOom: shown when the resource does not cover the cost
  };
  static SpellSlot slot(UiScene& scene, const BinValue& def);
  /** An icon of the minimap (MinimapIcon). */
  struct MapIconDef {
    float size[2] = {16, 16};
    float min_scale = 1;
    std::string texture;
    float color[4] = {1, 1, 1, 1};
    float team_color[2][4] = {{1, 1, 1, 1}, {1, 1, 1, 1}};  // mTeamColors 0 / 1 (allies / enemies)
    bool has_team_colors = false;
  };

  Ui2D ui_;
  UiFonts fonts_;
  // floating health bars
  UiScene bars_scene_;
  std::map<int, Style> styles_;
  std::vector<Bar> bars_;
  // minions' and structures' meters are white in the atlas: they take the colours of the champions' own blue and red
  // meters [dedus: the data names no colour for them; de măsurat]
  float ally_[4] = {0.3f, 0.6f, 1, 1}, enemy_[4] = {0.9f, 0.25f, 0.2f, 1};
  // the player's frame
  UiScene frame_scene_;
  bool frame_ok_ = false, frame_shown_ = false;
  UiElement* portrait_ = nullptr;
  UiElement* level_ = nullptr;
  UiElement* hp_text_ = nullptr;
  UiElement* par_text_ = nullptr;
  UiElement* xp_bar_ = nullptr;
  uint32_t hp_meter_ = 0, par_meter_ = 0;
  std::vector<UiElement*> par_parts_;  // the resource meter's own elements (hidden for champions without one)
  std::array<SpellSlot, 4> spells_;
  SpellSlot passive_;
  std::array<SpellSlot, 2> summoners_;
  // the level-up buttons (LevelUpDisplay: SkillUpButton) and the rank pips under each spell (SpellRankPips)
  std::array<UiElement*, 4> level_buttons_{};
  std::array<bool, 4> level_shown_{};
  std::array<std::vector<UiElement*>, 4> empty_pips_, full_pips_;
  std::array<UiElement*, 4> pip_rects_{};  // PipTargetRect: where a spell's pips are laid out
  // the stats panel: BasicStats key -> its text (0 ability power, 1 armor, 2 attack damage, 3 attack speed, 5 magic
  // resist, 6 move speed, 7 critical chance, 10 ability haste)
  UiScene stats_scene_;
  std::map<int, UiElement*> stat_texts_;
  // the inventory
  UiScene inventory_scene_;
  UiElement* gold_text_ = nullptr;
  struct InvSlot {
    UiElement* icon = nullptr;
    UiElement* border = nullptr;    // BorderDefault
    UiElement* selected = nullptr;  // BorderSelected
    UiElement* stack = nullptr;     // StackText
    UiElement* hotkey = nullptr;
    UiElement* hit = nullptr;       // HitArea
  };
  std::array<InvSlot, 7> inv_slots_{};
  // the item shop
  UiScene shop_scene_;
  bool shop_ok_ = false;
  uint32_t shop_main_scene_ = 0;
  UiElement* shop_region_ = nullptr;   // AllItemsItemRegion: one item's cell (57 x 76 in 14.1)
  UiElement* shop_area_ = nullptr;     // the All Items pane's scrollRegionElement: where the cells go (597 x 538)
  UiElement* shop_header_region_ = nullptr;  // AllItemsHeaderRegion: a group title's row
  UiElement* shop_header_ = nullptr;   // AllItemsHeaderText: a group's title is drawn with it
  struct Card {
    UiElement *icon = nullptr, *frame = nullptr, *selected = nullptr, *unpurchaseable = nullptr;
    UiElement *cost = nullptr, *cost_unpurchaseable = nullptr, *cost_selected = nullptr, *hit = nullptr;
  } card_;
  struct ShopGroup {
    std::vector<int> epicness;
    std::string key;
  };
  std::vector<ShopGroup> shop_groups_;
  UiElement* shop_gold_text_ = nullptr;
  UiElement *purchase_hit_ = nullptr, *sell_hit_ = nullptr, *close_hit_ = nullptr;
  UiElement *detail_title_ = nullptr, *detail_cost_ = nullptr, *detail_icon_ = nullptr;
  ShopView shop_view_;
  int shop_scroll_ = 0;  // rows of the All Items pane scrolled past
  struct PlacedCard {
    int id;
    float x0, y0, x1, y1;
  };
  mutable std::vector<PlacedCard> placed_cards_;
  void draw_shop(Gpu& gpu, float w, float h);
  // the game header
  UiScene header_scene_;
  UiElement* kda_text_ = nullptr;
  UiElement* cs_text_ = nullptr;
  UiElement* time_text_ = nullptr;
  UiElement* fps_text_ = nullptr;
  UiElement* latency_text_ = nullptr;
  UiElement* team_kills_[2] = {nullptr, nullptr};
  // the minimap
  UiScene minimap_scene_;
  UiElement* minimap_content_ = nullptr;
  std::map<int, MapIconDef> map_icons_;
  struct MapState {
    bool shown = false;
    ID3D11ShaderResourceView* background = nullptr;
    float min_x = 0, min_z = 0, max_x = 1, max_z = 1;
    std::vector<MapUnit> units;
    bool has_view = false;
    float view[8] = {};
  } map_;

  // target frame
  UiScene target_scene_;
  bool target_ok_ = false;
  TargetInfo target_info_;
  UiElement* target_portrait_ = nullptr;
  UiElement* target_level_ = nullptr;
  UiElement* target_hp_text_ = nullptr;
  UiElement* target_par_text_ = nullptr;
  uint32_t target_hp_meter_ = 0, target_par_meter_ = 0;
  std::map<int, UiElement*> target_stat_texts_;
  std::array<UiElement*, 7> target_item_icons_{};
  std::array<UiElement*, 7> target_item_stacks_{};
  UiElement* target_kda_text_ = nullptr;
  UiElement* target_cs_text_ = nullptr;
  UiElement* target_hp_bar_ally_ = nullptr;
  UiElement* target_hp_bar_enemy_ = nullptr;

  // scoreboard
  UiScene scoreboard_scene_;
  bool scoreboard_ok_ = false;
  ScoreboardView scoreboard_view_;
  UiElement* sb_team_scores_[2]{};
  struct SbRow {
    UiElement* portrait = nullptr;
    UiElement* name = nullptr;
    UiElement* level = nullptr;
    UiElement* kda = nullptr;
    UiElement* cs = nullptr;
    UiElement* dead = nullptr;
    UiElement* self = nullptr;
    std::array<UiElement*, 7> items{};
    std::array<UiElement*, 7> stacks{};
  };
  std::array<SbRow, 5> sb_team1_rows_{};
  std::array<SbRow, 5> sb_team2_rows_{};
  void draw_scoreboard(Gpu& gpu, float w, float h);

  // end of game (victory / defeat)
  UiScene eog_scene_;
  bool eog_ok_ = false;
  EndOfGame eog_;
  UiElement* eog_victory_group_ = nullptr;
  UiElement* eog_defeat_group_ = nullptr;
  ID3D11ShaderResourceView* victory_banner_tex_ = nullptr;
  ID3D11ShaderResourceView* defeat_banner_tex_ = nullptr;

  // floating combat text
  struct FctNumber {
    float x, y;
    std::string text;
    float color[4];
    float age = 0;
    float max_age = 0.8f;
    bool is_crit = false;
  };
  std::vector<FctNumber> fct_numbers_;
};

}  // namespace ba
