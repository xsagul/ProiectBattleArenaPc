#include "Hud.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>

#include "ba/Hash.h"
#include "ba/Texture.h"

namespace ba {

namespace {

std::string lower(std::string s) {
  for (char& c : s) c = static_cast<char>(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
  return s;
}

/** The first entry of a class in a view controller's bin, or null. */
const BinEntry* controller(const PropertyBin& bin, const char* cls) {
  for (const BinEntry& e : bin.entries())
    if (e.cls == fnv1a(cls)) return &e;
  return nullptr;
}

}  // namespace

Hud::SpellSlot Hud::slot(UiScene& scene, const BinValue& def) {
  SpellSlot s;
  s.icon = scene.find(def.field("ContentElement"));
  s.hotkey = scene.find(def.field("Hotkey"));
  s.border_on = scene.find(def.field("BorderEnabled"));
  s.border_off = scene.find(def.field("BorderDisabled"));
  s.overlay_off = scene.find(def.field("OverlayDisabled"));
  s.cost = scene.find(def.field("Cost"));
  s.cost_bg = scene.find(def.field("CostBg"));
  s.oom = scene.find(def.field("OverlayOom"));
  if (const BinValue* cd = def.field("CooldownUiData")) {
    s.cooldown_text = scene.find(cd->field("CooldownText"));
    s.cooldown_fx = scene.find(cd->field("RadialEffect"));
  }
  return s;
}

bool Hud::load(Gpu& gpu, const Wad& ui) {
  if (!ui_.init(gpu)) return false;
  ui_.add_wad(&ui);
  fonts_.load(ui);

  // ---- floating health bars
  auto bars_bytes = ui.read("gameplay.lolfloatinginfobars.bin");
  if (!bars_bytes || !bars_scene_.load(ui, "clientstates/gameplay/ux/lol/lolfloatinginfobars/uibase")) return false;
  const PropertyBin bars(*bars_bytes);
  if (const BinEntry* e = controller(bars, "FloatingInfoBarViewController"))
    if (const BinValue* map = e->field("InfoBarStyleSourceMap"))
      for (const auto& [key, link] : map->pairs) {
        const BinEntry* data = bars.entry(static_cast<uint32_t>(link.u));
        if (!data) continue;
        Style s;
        s.anchor = bars_scene_.find(data->field("Anchor"));
        s.border = bars_scene_.find(data->field("border"));
        // champions keep their borders by state: the plain one
        if (const BinValue* borders = data->field("Borders"))
          if (const BinValue* plain = borders->field("DefaultBorder")) s.border = bars_scene_.find(plain->field("border"));
        const BinValue* hb = data->field("Healthbar");
        if (const BinValue* types = hb ? hb->field("Healthbar") : nullptr) {
          s.bar = bars_scene_.find(types->field("DefaultBar"));
          if (const BinValue* more = types->field("AdditionalBarTypes"))
            for (const auto& [name, bar] : more->pairs) s.bars[static_cast<uint32_t>(name.u)] = bars_scene_.find(&bar);
        }
        if (const BinValue* ticks = hb ? hb->field("TickStyle") : nullptr) {
          s.standard_tick = bars_scene_.find(ticks->field("StandardTick"));
          s.micro_tick = bars_scene_.find(ticks->field("MicroTick"));
          s.hero_ticks = ticks->cls == fnv1a("HealthBarTickStyleHero");
          if (const BinValue* v = ticks->field("HealthPerstandardTick")) s.hp_per_standard_tick = static_cast<float>(v->number());
          if (const BinValue* list = ticks->field("MicroTickPerStandardTickData"))
            for (const BinValue& m : list->items) {
              const BinValue* mh = m.field("minHealth");
              const BinValue* mb = m.field("microTicksBetween");
              s.micro_ticks.emplace_back(mh ? static_cast<float>(mh->number()) : 1000.f, mb ? static_cast<int>(mb->number()) : 9);
            }
        }
        if (s.anchor && s.bar) styles_[static_cast<int>(key.u ? key.u : static_cast<uint64_t>(key.number()))] = s;
      }
  if (styles_.empty()) return false;

  // the colours for the white meters: what the champions' blue and red meters look like in the atlas
  for (const auto& [id, s] : styles_) {
    auto blue = s.bars.find(fnv1a("Blue")), red = s.bars.find(fnv1a("Red"));
    if (blue == s.bars.end() || red == s.bars.end() || !blue->second || !red->second) continue;
    try {
      auto bytes = ui.read(blue->second->texture);
      if (!bytes) break;
      const Texture t = read_texture(*bytes);
      const std::vector<uint8_t> px = texture_rgba(t);
      auto average = [&](const UiElement& e, float out[4]) {
        const float kx = static_cast<float>(t.width) / e.tex_w, ky = static_cast<float>(t.height) / e.tex_h;
        double sum[3] = {0, 0, 0};
        size_t n = 0;
        for (uint32_t y = static_cast<uint32_t>(e.v0 * ky) + 1; y + 1 < static_cast<uint32_t>(e.v1 * ky) && y < t.height; ++y)
          for (uint32_t x = static_cast<uint32_t>(e.u0 * kx) + 1; x + 1 < static_cast<uint32_t>(e.u1 * kx) && x < t.width; ++x) {
            const uint8_t* p = &px[(static_cast<size_t>(y) * t.width + x) * 4];
            sum[0] += p[0], sum[1] += p[1], sum[2] += p[2], ++n;
          }
        if (n)
          for (int c = 0; c < 3; ++c) out[c] = static_cast<float>(sum[c] / static_cast<double>(n) / 255.0);
      };
      average(*blue->second, ally_);
      average(*red->second, enemy_);
    } catch (const std::exception&) {
    }
    break;
  }

  // ---- the player's frame: the roles its view controller gives the scene's elements
  auto frame_bytes = ui.read("gameplay.playerframe.bin");
  if (frame_bytes && frame_scene_.load(ui, "clientstates/gameplay/ux/lol/playerframe/uibase")) {
    const PropertyBin frame(*frame_bytes);
    if (const BinEntry* e = controller(frame, "PlayerFrameViewController")) {
      if (const BinValue* p = e->field("PortraitUiData")) {
        portrait_ = frame_scene_.find(p->field("Icon"));
        level_ = frame_scene_.find(p->field("LevelText"));
      }
      if (const BinValue* r = e->field("ResourceBars")) {
        if (const BinValue* hm = r->field("HealthMeter")) {
          if (const BinValue* m = hm->field("Meter")) hp_meter_ = static_cast<uint32_t>(m->u);
          hp_text_ = frame_scene_.find(hm->field("ValueText"));
        }
        if (const BinValue* pm = r->field("ParMeterData")) {
          if (const BinValue* bars_data = pm->field("AbilityResourceBars"))
            if (const BinValue* m = bars_data->field("Meter")) par_meter_ = static_cast<uint32_t>(m->u);
          par_text_ = frame_scene_.find(pm->field("ValueText"));
        }
        xp_bar_ = frame_scene_.find(r->field("ExperienceBar"));
      }
      if (const BinValue* a = e->field("AbilitiesUiData")) {
        if (const BinValue* list = a->field("ChampionSpells"))
          for (size_t i = 0; i < 4 && i < list->items.size(); ++i) spells_[i] = slot(frame_scene_, list->items[i]);
        if (const BinValue* list = a->field("SummonerSpells"))
          for (size_t i = 0; i < 2 && i < list->items.size(); ++i) summoners_[i] = slot(frame_scene_, list->items[i]);
        if (const BinValue* p = a->field("Passive")) passive_ = slot(frame_scene_, *p);
        if (const BinValue* pips = a->field("SpellRankPips"))
          if (const BinValue* list = pips->field("RankPips"))
            for (size_t i = 0; i < 4 && i < list->items.size(); ++i) {
              pip_rects_[i] = frame_scene_.find(list->items[i].field("PipTargetRect"));
              if (const BinValue* l = list->items[i].field("EmptyPips"))
                for (const BinValue& x : l->items) empty_pips_[i].push_back(frame_scene_.find(&x));
              if (const BinValue* l = list->items[i].field("FullPips"))
                for (const BinValue& x : l->items) full_pips_[i].push_back(frame_scene_.find(&x));
            }
      }
      if (const BinValue* lu = e->field("LevelUpDisplay"))
        if (const BinValue* list = lu->field("spells"))
          for (size_t i = 0; i < 4 && i < list->items.size(); ++i) level_buttons_[i] = frame_scene_.find(list->items[i].field("SkillUpButton"));
      frame_ok_ = portrait_ && hp_meter_;
    }
    // the resource meter's bar, as a champion without a resource does not show one
    if (UiElement* g = frame_scene_.find(par_meter_))
      for (uint32_t b : g->bars)
        if (UiElement* bar = frame_scene_.find(b)) par_parts_.push_back(bar);
  }

  // ---- the stats panel
  auto stats_bytes = ui.read("gameplay.playerstats.bin");
  if (stats_bytes && stats_scene_.load(ui, "clientstates/gameplay/ux/lol/playerstats/uibase")) {
    const PropertyBin stats(*stats_bytes);
    if (const BinEntry* e = controller(stats, "PlayerHeroStatsViewController")) {
      // the advanced stats open on demand: closed [de măsurat: the key that opens them]
      if (const BinValue* adv = e->field("AdvancedStats")) stats_scene_.show_scene(static_cast<uint32_t>(adv->u), false);
      if (const BinValue* data = e->field("StatsUiData"))
        if (const BinValue* basic = data->field("BasicStats"))
          for (const auto& [key, stat] : basic->pairs)
            stat_texts_[static_cast<int>(key.u ? key.u : static_cast<uint64_t>(key.number()))] = stats_scene_.find(stat.field("Text"));
    }
  }

  // ---- the inventory: the empty slots' backdrops, the gold
  auto inv_bytes = ui.read("gameplay.playerinventory.bin");
  if (inv_bytes && inventory_scene_.load(ui, "clientstates/gameplay/ux/lol/playerinventory/uibase")) {
    const PropertyBin inv(*inv_bytes);
    if (const BinEntry* e = controller(inv, "PlayerInventoryViewController")) {
      if (const BinValue* slots = e->field("ItemSlotUiData")) {
        size_t k = 0;
        for (const BinValue& s : slots->items) {
          if (UiElement* b = inventory_scene_.find(s.field("Backdrop"))) b->enabled = true;
          // the first seven: the six item slots and the trinket's (the eighth is the recall button) [dedus: order]
          if (k < inv_slots_.size()) {
            InvSlot& is = inv_slots_[k];
            is.icon = inventory_scene_.find(s.field("Icon"));
            is.border = inventory_scene_.find(s.field("BorderDefault"));
            is.selected = inventory_scene_.find(s.field("BorderSelected"));
            is.stack = inventory_scene_.find(s.field("StackText"));
            is.hotkey = inventory_scene_.find(s.field("HotkeyText"));
            is.hit = inventory_scene_.find(s.field("HitArea"));
          }
          ++k;
        }
      }
      if (const BinValue* shop = e->field("ShopButton")) gold_text_ = inventory_scene_.find(shop->field("TextLink"));
    }
  }

  // ---- the item shop: its scene, the All Items tab (groups by epicness, one card per item), buttons, gold, details
  auto shop_bytes = ui.read("gameplay.itemshop.bin");
  const std::string shop_path = "clientstates/gameplay/ux/itemshop/uibase";
  auto scene_bytes = ui.read(shop_path);
  if (shop_bytes && scene_bytes && shop_scene_.load(ui, shop_path)) {
    const PropertyBin shop(*shop_bytes), scene(*scene_bytes);
    if (const BinEntry* vc = controller(shop, "ItemShopViewController"))
      if (const BinValue* sh = vc->field("SceneHandle")) shop_main_scene_ = static_cast<uint32_t>(sh->u);
    if (const BinEntry* d = controller(shop, "HudItemShopData")) {
      shop_region_ = shop_scene_.find(d->field("AllItemsItemRegion"));
      shop_header_ = shop_scene_.find(d->field("AllItemsHeaderText"));
      shop_header_region_ = shop_scene_.find(d->field("AllItemsHeaderRegion"));
      if (const BinValue* pane = d->field("TabViewAllItemsSceneViewPane"))
        if (const BinEntry* pe = scene.entry(static_cast<uint32_t>(pane->u))) shop_area_ = shop_scene_.find(pe->field("scrollRegionElement"));
      shop_gold_text_ = shop_scene_.find(d->field("PlayerGoldText"));
      auto button_hit = [&](const char* field) -> UiElement* {
        UiElement* b = shop_scene_.find(d->field(field));
        return b ? shop_scene_.find(b->hit_region) : nullptr;
      };
      purchase_hit_ = button_hit("PurchaseButtonDefinition");
      sell_hit_ = button_hit("SellButtonDefinition");
      close_hit_ = button_hit("CloseButtonDefinition");
      if (const BinValue* groups = d->field("AllItemGroupDefinitions"))
        for (const BinValue& g : groups->items) {
          ShopGroup sg;
          if (const BinValue* n = g.field("groupName")) sg.key = n->str;
          if (const BinValue* e = g.field("EpicnessesInGroup"))
            for (const BinValue& x : e->items) sg.epicness.push_back(static_cast<int>(x.number()));
          shop_groups_.push_back(sg);
        }
      // the card template: the definition is an entry of the scene file naming its elements
      if (const BinValue* def = d->field("AllItemsIconDefinition"))
        if (const BinEntry* c = scene.entry(static_cast<uint32_t>(def->u))) {
          card_.icon = shop_scene_.find(c->field("ItemIcon"));
          card_.frame = shop_scene_.find(c->field("FrameIcon"));
          card_.selected = shop_scene_.find(c->field("SelectedIcon"));
          card_.unpurchaseable = shop_scene_.find(c->field("UnpurchaseableOverlay"));
          card_.cost = shop_scene_.find(c->field("CostText"));
          card_.cost_unpurchaseable = shop_scene_.find(c->field("CostTextUnpurchaseable"));
          card_.cost_selected = shop_scene_.find(c->field("CostTextSelected"));
          card_.hit = shop_scene_.find(c->field("HitRegion"));
        }
      if (const BinValue* det = d->field("ItemDescriptionDefinition")) {
        detail_title_ = shop_scene_.find(det->field("TitleTextDefinition"));
        detail_cost_ = shop_scene_.find(det->field("CostTextDefinition"));
        detail_icon_ = shop_scene_.find(det->field("ItemIconDefinition"));
      }
    }
    shop_ok_ = shop_main_scene_ != 0 && shop_region_ && shop_area_ && shop_header_region_ && card_.icon;
    shop_scene_.show_button_defaults();
  }

  // ---- the game header
  auto header_bytes = ui.read("gameplay.lolgameheader.bin");
  if (header_bytes && header_scene_.load(ui, "clientstates/gameplay/ux/lol/lolgameheader/uibase")) {
    const PropertyBin header(*header_bytes);
    if (const BinEntry* e = controller(header, "LolGameStateViewController"))
      if (const BinValue* metrics = e->field("Metrics"))
        for (const BinValue& m : metrics->items) {
          if (m.cls == fnv1a("UiMetricKda")) kda_text_ = header_scene_.find(m.field("Text"));
          if (m.cls == fnv1a("UiMetricCreepScore")) cs_text_ = header_scene_.find(m.field("Text"));
          if (m.cls == fnv1a("UiMetricGameTime")) time_text_ = header_scene_.find(m.field("TimeText"));
          if (m.cls == fnv1a("UiMetricFps")) fps_text_ = header_scene_.find(m.field("FpsText"));
          if (m.cls == fnv1a("UiMetricLatencyText")) latency_text_ = header_scene_.find(m.field("LatencyText"));
          if (m.cls == fnv1a("UiMetricTeamKills"))
            team_kills_[0] = header_scene_.find(m.field("Team1KillText")), team_kills_[1] = header_scene_.find(m.field("Team2KillText"));
        }
  }

  // ---- the minimap: its content rectangle, and an icon per kind of unit
  auto map_bytes = ui.read("gameplay.lolminimap.bin");
  if (map_bytes && minimap_scene_.load(ui, "clientstates/gameplay/ux/lol/lolminimap/uibase")) {
    const PropertyBin map(*map_bytes);
    if (const BinEntry* e = controller(map, "MinimapViewController")) {
      minimap_content_ = minimap_scene_.find(e->field("MinimapContent"));
      // the objective bounty's sweeps and the jungle path's "on" state belong to states the match is not in
      if (const BinValue* ob = e->field("ObjectiveBountiesStatus"))
        if (UiElement* bg = minimap_scene_.find(ob->field("Background"))) bg->enabled = false;
    }
    if (const BinEntry* data = controller(map, "MinimapData"))
      if (const BinValue* icons = data->field("mIcons"))
        for (const auto& [key, icon] : icons->pairs) {
          MapIconDef d;
          if (const BinValue* s = icon.field("mSize")) d.size[0] = static_cast<float>(s->num[0]), d.size[1] = static_cast<float>(s->num[1]);
          if (const BinValue* s = icon.field("mMinScale")) d.min_scale = static_cast<float>(s->number());
          if (const BinValue* t = icon.field("mBaseTexture"))
            if (const BinValue* b = t->field("mBase")) d.texture = lower(b->str);
          if (const BinValue* c = icon.field("mBaseColor")) ui_color(c->field("mBase"), d.color);
          if (const BinValue* tc = icon.field("mTeamColors"))
            for (const auto& [team, color] : tc->pairs) {
              const uint64_t t = team.u ? team.u : static_cast<uint64_t>(team.number());
              if (t < 2) ui_color(color.field("mBase"), d.team_color[t]), d.has_team_colors = true;
            }
          map_icons_[static_cast<int>(key.u ? key.u : static_cast<uint64_t>(key.number()))] = d;
        }
  }

  // ---- the target frame
  auto target_bytes = ui.read("gameplay.targetframe.bin");
  if (target_bytes && target_scene_.load(ui, "clientstates/gameplay/ux/lol/targetframe/uibase")) {
    const PropertyBin tf(*target_bytes);
    if (const BinEntry* e = controller(tf, "TargetFrameViewController")) {
      target_portrait_ = target_scene_.find(e->field("Portrait"));
      if (const BinValue* lv = e->field("LevelData")) target_level_ = target_scene_.find(lv->field("LevelText"));
      if (const BinValue* hm = e->field("HealthMeter")) {
        if (const BinValue* m = hm->field("Meter")) target_hp_meter_ = static_cast<uint32_t>(m->u);
        target_hp_text_ = target_scene_.find(hm->field("ValueText"));
      }
      if (const BinValue* hms = e->field("HealthMeterSkins")) {
        if (const BinValue* as = hms->field("MeterAllySkin"))
          if (const BinValue* list = as->field("BarElementList"))
            if (!list->items.empty()) target_hp_bar_ally_ = target_scene_.find(&list->items[0]);
        if (const BinValue* es = hms->field("MeterEnemySkin"))
          if (const BinValue* list = es->field("BarElementList"))
            if (!list->items.empty()) target_hp_bar_enemy_ = target_scene_.find(&list->items[0]);
      }
      if (const BinValue* pb = e->field("ParBarData")) {
        if (const BinValue* r = pb->field("AbilityResourceBars"))
          if (const BinValue* m = r->field("Meter")) target_par_meter_ = static_cast<uint32_t>(m->u);
        target_par_text_ = target_scene_.find(pb->field("ValueText"));
      }
      if (const BinValue* su = e->field("StatsUiData"))
        if (const BinValue* bs = su->field("BasicStats"))
          for (const auto& [k, v] : bs->pairs)
            target_stat_texts_[static_cast<int>(k.u ? k.u : static_cast<uint64_t>(k.number()))] = target_scene_.find(v.field("Text"));
      if (const BinValue* inv = e->field("InventoryData")) {
        for (int i = 0; i < 7; ++i) {
          char key[16];
          std::snprintf(key, sizeof key, "Item%d", i);
          if (const BinValue* it = inv->field(key)) {
            target_item_icons_[i] = target_scene_.find(it->field("Icon"));
            target_item_stacks_[i] = target_scene_.find(it->field("StackText"));
          }
        }
      }
      if (const BinValue* mets = e->field("Metrics")) {
        for (const BinValue& m : mets->items) {
          if (m.cls == fnv1a("UiMetricUnitKda")) target_kda_text_ = target_scene_.find(m.field("Text"));
          else if (m.cls == fnv1a("UiMetricUnitCreepScore")) target_cs_text_ = target_scene_.find(m.field("Text"));
        }
      }
      target_ok_ = target_portrait_ != nullptr;
    }
  }

  // ---- the scoreboard
  if (scoreboard_scene_.load(ui, "clientstates/gameplay/ux/scoreboard/uibase")) {
    sb_team_scores_[0] = scoreboard_scene_.find(fnv1a("ClientStates/Gameplay/UX/Scoreboard/UIBase/Scoreboard_TeamScores/SB_TeamKills_T1Score"));
    sb_team_scores_[1] = scoreboard_scene_.find(fnv1a("ClientStates/Gameplay/UX/Scoreboard/UIBase/Scoreboard_TeamScores/SB_TeamKills_T2Score"));
    for (int t = 1; t <= 2; ++t) {
      auto& rows = (t == 1) ? sb_team1_rows_ : sb_team2_rows_;
      for (int p = 0; p < 5; ++p) {
        char prefix[64];
        std::snprintf(prefix, sizeof prefix, "ClientStates/Gameplay/UX/Scoreboard/UIBase/Scoreboard/SB_T%dP%d_", t, p);
        rows[p].name = scoreboard_scene_.find(fnv1a(std::string(prefix) + "SummonerName"));
        rows[p].kda = scoreboard_scene_.find(fnv1a(std::string(prefix) + "KDA_Text"));
        rows[p].dead = scoreboard_scene_.find(fnv1a(std::string(prefix) + "PlayerSlot_Dead"));
        rows[p].self = scoreboard_scene_.find(fnv1a(std::string(prefix) + "PlayerSlot_Self"));
        for (int i = 0; i < 7; ++i) {
          rows[p].items[i] = scoreboard_scene_.find(fnv1a(std::string(prefix) + "Item" + std::to_string(i) + "_"));
          if (i < 6) rows[p].stacks[i] = scoreboard_scene_.find(fnv1a(std::string(prefix) + "Item" + std::to_string(i) + "_Count"));
        }
      }
    }
    scoreboard_ok_ = true;
  }

  // ---- end of game (victory / defeat)
  if (eog_scene_.load(ui, "clientstates/gameplay/ux/endofgame/uibase")) {
    eog_victory_group_ = eog_scene_.find(fnv1a("ClientStates/Gameplay/UX/EndOfGame/UIBase/EndOfGameMainScene/EOG_VictoryGroup"));
    eog_defeat_group_ = eog_scene_.find(fnv1a("ClientStates/Gameplay/UX/EndOfGame/UIBase/EndOfGameMainScene/EOG_DefeatGroup"));
    victory_banner_tex_ = ui_.texture(gpu, "assets/ux/endofgame/eog_base.tex");
    defeat_banner_tex_ = ui_.texture(gpu, "assets/ux/endofgame/eog_defeat_base.tex");
    eog_ok_ = true;
  }

  return true;
}

void Hud::health_bar(int style, float x, float y, float fraction, Side side) {
  health_bar(style, x, y, fraction, 0.f, 0.f, 0.f, side);
}

void Hud::health_bar(int style, float x, float y, float fraction, float max_hp, float shield_fraction, float decay_fraction, Side side,
                     float hp_per_tick) {
  auto it = styles_.find(style);
  if (it == styles_.end()) it = styles_.find(0);  // unitHealthBarStyle [meta default 0]
  if (it == styles_.end()) return;
  // whole pixels: the bars are drawn 1 : 1 (IgnoreGlobalScale, DisableResolutionDownscale)
  bars_.push_back({&it->second, std::floor(x + 0.5f), std::floor(y + 0.5f), std::clamp(fraction, 0.f, 1.f), max_hp,
                   std::clamp(shield_fraction, 0.f, 1.f), std::clamp(decay_fraction, 0.f, 1.f), side, hp_per_tick});
}

bool Hud::minimap_hit(Gpu& gpu, int screen_x, int screen_y, float& world_x, float& world_z) const {
  if (!map_.shown || !minimap_content_) return false;
  float x0, y0, x1, y1;
  const float w = static_cast<float>(gpu.width()), h = static_cast<float>(gpu.height());
  minimap_scene_.place(*minimap_content_, w, h, x0, y0, x1, y1);
  const float sx = static_cast<float>(screen_x), sy = static_cast<float>(screen_y);
  if (sx < x0 || sx > x1 || sy < y0 || sy > y1) return false;
  world_x = map_.min_x + (sx - x0) / (x1 - x0) * (map_.max_x - map_.min_x);
  world_z = map_.min_z + (y1 - sy) / (y1 - y0) * (map_.max_z - map_.min_z);
  return true;
}

void Hud::add_fct(float screen_x, float screen_y, float amount, FctType type) {
  FctNumber num;
  num.x = screen_x;
  num.y = screen_y;
  char buf[32];
  if (type == FctType::Heal) {
    std::snprintf(buf, sizeof buf, "+%.0f", amount);
  } else {
    std::snprintf(buf, sizeof buf, "%.0f", amount);
  }
  num.text = buf;
  num.is_crit = (type == FctType::Crit);
  switch (type) {
    case FctType::Physical:
      num.color[0] = 1.0f; num.color[1] = 0.4f; num.color[2] = 0.2f; num.color[3] = 1.0f;
      break;
    case FctType::Magic:
      num.color[0] = 0.35f; num.color[1] = 0.65f; num.color[2] = 1.0f; num.color[3] = 1.0f;
      break;
    case FctType::True:
      num.color[0] = 1.0f; num.color[1] = 1.0f; num.color[2] = 1.0f; num.color[3] = 1.0f;
      break;
    case FctType::Crit:
      num.color[0] = 1.0f; num.color[1] = 0.15f; num.color[2] = 0.1f; num.color[3] = 1.0f;
      break;
    case FctType::Heal:
      num.color[0] = 0.2f; num.color[1] = 0.95f; num.color[2] = 0.3f; num.color[3] = 1.0f;
      break;
  }
  fct_numbers_.push_back(num);
}

void Hud::update_fct(double dt) {
  for (size_t i = 0; i < fct_numbers_.size();) {
    fct_numbers_[i].age += static_cast<float>(dt);
    if (fct_numbers_[i].age >= fct_numbers_[i].max_age) {
      fct_numbers_.erase(fct_numbers_.begin() + static_cast<std::ptrdiff_t>(i));
    } else {
      ++i;
    }
  }
}

void Hud::draw_scoreboard(Gpu& gpu, float w, float h) {
  if (!scoreboard_view_.open || !scoreboard_ok_) return;
  char text[64];
  if (sb_team_scores_[0]) sb_team_scores_[0]->text = std::to_string(scoreboard_view_.team_kills[0]);
  if (sb_team_scores_[1]) sb_team_scores_[1]->text = std::to_string(scoreboard_view_.team_kills[1]);

  auto update_rows = [&](const std::vector<ScoreboardPlayer>& team, std::array<SbRow, 5>& rows) {
    for (size_t p = 0; p < rows.size(); ++p) {
      SbRow& r = rows[p];
      if (p >= team.size()) {
        if (r.name) r.name->text.clear();
        if (r.kda) r.kda->text.clear();
        if (r.dead) r.dead->enabled = false;
        if (r.self) r.self->enabled = false;
        for (int i = 0; i < 7; ++i) {
          if (r.items[i]) r.items[i]->enabled = false;
          if (i < 6 && r.stacks[i]) r.stacks[i]->enabled = false;
        }
        continue;
      }
      const ScoreboardPlayer& sp = team[p];
      if (r.name) r.name->text = sp.name;
      if (r.kda) {
        std::snprintf(text, sizeof text, "%d/%d/%d (%d)", sp.kills, sp.deaths, sp.assists, sp.cs);
        r.kda->text = text;
      }
      if (r.dead) r.dead->enabled = sp.dead;
      if (r.self) r.self->enabled = sp.is_self;
      for (int i = 0; i < 7; ++i) {
        if (r.items[i]) {
          r.items[i]->image = sp.item_icons[i];
          r.items[i]->enabled = (sp.item_icons[i] != nullptr);
        }
        if (i < 6 && r.stacks[i]) {
          const bool has_stack = sp.item_stacks[i] > 1;
          r.stacks[i]->enabled = has_stack;
          if (has_stack) r.stacks[i]->text = std::to_string(sp.item_stacks[i]);
          else r.stacks[i]->text.clear();
        }
      }
    }
  };

  update_rows(scoreboard_view_.team1, sb_team1_rows_);
  update_rows(scoreboard_view_.team2, sb_team2_rows_);

  scoreboard_scene_.draw(gpu, ui_, fonts_, w, h);
}

void Hud::player(const Player& p) {
  frame_shown_ = frame_ok_;
  if (!frame_ok_) return;
  char text[64];
  auto number = [&](UiElement* e, const char* format, double v) {
    if (!e) return;
    std::snprintf(text, sizeof text, format, v);
    e->text = text;
  };
  if (portrait_) portrait_->image = p.portrait, portrait_->enabled = p.portrait != nullptr;
  if (level_) level_->text = std::to_string(p.level);
  frame_scene_.meter(hp_meter_, p.max_hp > 0 ? p.hp / p.max_hp : 0.f);
  if (hp_text_) {
    std::snprintf(text, sizeof text, "%.0f / %.0f", std::ceil(p.hp), std::ceil(p.max_hp));
    hp_text_->text = text;
  }
  // the resource meter: empty and without numbers for a champion that has no resource
  const bool has_par = p.max_par > 0;
  frame_scene_.meter(par_meter_, has_par ? p.par / p.max_par : 0.f);
  for (UiElement* e : par_parts_) e->enabled = has_par;
  if (par_text_) {
    std::snprintf(text, sizeof text, "%.0f / %.0f", std::floor(p.par), std::floor(p.max_par));
    par_text_->text = has_par ? text : "";
  }
  if (xp_bar_) xp_bar_->fill_y = std::clamp(p.xp, 0.f, 1.f);
  // the spell slots: the spell's icon; greyed with the "unavailable" border until it is learned; the hotkey
  static const char* kKeys[4] = {"Q", "W", "E", "R"};
  for (size_t i = 0; i < 4; ++i) {
    SpellSlot& s = spells_[i];
    const bool learned = p.spell_levels[i] > 0, cooling = p.cooldown_left[i] > 0;
    if (s.icon) s.icon->image = p.spells[i], s.icon->enabled = p.spells[i] != nullptr, s.icon->saturation = learned && !cooling ? 1.f : s.icon->min_saturation;
    if (s.hotkey) s.hotkey->text = kKeys[i];
    if (s.border_on) s.border_on->enabled = learned;
    if (s.border_off) s.border_off->enabled = !learned;
    if (s.overlay_off) s.overlay_off->enabled = !learned;
    if (s.cooldown_fx) {
      s.cooldown_fx->enabled = cooling;
      s.cooldown_fx->sweep = cooling && p.cooldown_total[i] > 0 ? p.cooldown_left[i] / p.cooldown_total[i] : 0.f;
    }
    if (s.cooldown_text) {
      s.cooldown_text->enabled = cooling;
      std::snprintf(text, sizeof text, p.cooldown_left[i] < 1 ? "%.1f" : "%.0f", p.cooldown_left[i] < 1 ? p.cooldown_left[i] : std::ceil(p.cooldown_left[i]));
      s.cooldown_text->text = cooling ? text : "";
    }
    if (s.cost) {
      s.cost->enabled = learned && p.costs[i] > 0;
      std::snprintf(text, sizeof text, "%.0f", p.costs[i]);
      s.cost->text = text;
    }
    if (s.cost_bg) s.cost_bg->enabled = learned && p.costs[i] > 0;
    if (s.oom) s.oom->enabled = learned && p.costs[i] > p.par;
  }
  // the rank pips under each spell: as many empty ones as it has ranks (3 for the last spell, 5 for the others:
  // documented), the first `level` of them full; and the level-up button over each spell a point may go into
  for (size_t i = 0; i < 4; ++i) {
    const size_t ranks = i == 3 ? 3 : 5;
    // the pips side by side, centred in the spell's PipTargetRect [dedus: the file gives them all one place; the game's
    // controller lays them out]
    auto place_pip = [&](UiElement* pip, size_t k) {
      if (!pip || !pip_rects_[i]) return;
      const float total = static_cast<float>(ranks) * pip->w;
      pip->shift_x = pip_rects_[i]->x + (pip_rects_[i]->w - total) * 0.5f + static_cast<float>(k) * pip->w - pip->x;
    };
    for (size_t k = 0; k < empty_pips_[i].size(); ++k)
      if (empty_pips_[i][k]) empty_pips_[i][k]->enabled = k < ranks, place_pip(empty_pips_[i][k], k);
    for (size_t k = 0; k < full_pips_[i].size(); ++k)
      if (full_pips_[i][k]) full_pips_[i][k]->enabled = static_cast<int>(k) < p.spell_levels[i], place_pip(full_pips_[i][k], k);
    level_shown_[i] = p.can_level[i];
    if (level_buttons_[i])
      for (uint32_t d : level_buttons_[i]->default_display)
        if (UiElement* e = frame_scene_.find(d)) e->enabled = p.can_level[i];
  }
  if (passive_.icon) passive_.icon->image = p.passive, passive_.icon->enabled = p.passive != nullptr;
  // no summoner spells yet: their slots stay empty, without hotkeys
  for (SpellSlot& s : summoners_) {
    if (s.icon) s.icon->enabled = false;
    if (s.hotkey) s.hotkey->text.clear();
  }

  // ---- the stats panel
  auto stat = [&](int key, const char* format, double v) {
    auto it = stat_texts_.find(key);
    if (it != stat_texts_.end()) number(it->second, format, v);
  };
  stat(0, "%.0f", p.ap), stat(1, "%.0f", p.armor), stat(2, "%.0f", p.ad), stat(3, "%.2f", p.attack_speed);
  stat(5, "%.0f", p.spell_block), stat(6, "%.0f", p.move_speed), stat(7, "%.0f%%", p.crit * 100.0), stat(10, "%.0f", p.ability_haste);

  // ---- the inventory: each slot's item icon, its stack, its border; the slot picked in the shop
  static const char* kItemKeys[7] = {"1", "2", "3", "5", "6", "7", "4"};  // [meta: the default item hotkeys]
  for (size_t k = 0; k < inv_slots_.size(); ++k) {
    InvSlot& s = inv_slots_[k];
    const bool has = p.item_icons[k] != nullptr;
    if (s.icon) s.icon->image = p.item_icons[k], s.icon->enabled = has;
    if (s.border) s.border->enabled = has;
    if (s.selected) s.selected->enabled = has && p.selected_slot == static_cast<int>(k);
    if (s.stack) s.stack->enabled = has && p.item_stacks[k] > 1, s.stack->text = p.item_stacks[k] > 1 ? std::to_string(p.item_stacks[k]) : "";
    if (s.hotkey) s.hotkey->enabled = true, s.hotkey->text = kItemKeys[k];
  }

  // ---- the gold
  number(gold_text_, "%.0f", std::floor(p.gold));

  // ---- the game header
  if (kda_text_) {
    std::snprintf(text, sizeof text, "%d/%d/%d", p.kills, p.deaths, p.assists);
    kda_text_->text = text;
  }
  if (cs_text_) cs_text_->text = std::to_string(p.minions_killed);
  if (time_text_) {
    const int secs = static_cast<int>(std::max(0.0, p.game_seconds));
    std::snprintf(text, sizeof text, "%02d:%02d", secs / 60, secs % 60);
    time_text_->text = text;
  }
  for (int t = 0; t < 2; ++t)
    if (team_kills_[t]) team_kills_[t]->text = std::to_string(p.team_kills[t]);
  if (fps_text_) fps_text_->text = std::to_string(p.fps) + " FPS";
  if (latency_text_) latency_text_->text = "0 ms";  // the server runs on this machine
}

int Hud::level_button_at(Gpu& gpu, int x, int y) {
  for (size_t i = 0; i < 4; ++i) {
    if (!level_shown_[i] || !level_buttons_[i]) continue;
    const UiElement* region = frame_scene_.find(level_buttons_[i]->hit_region);
    if (!region) continue;
    float x0, y0, x1, y1;
    frame_scene_.place(*region, static_cast<float>(gpu.width()), static_cast<float>(gpu.height()), x0, y0, x1, y1);
    if (static_cast<float>(x) >= x0 && static_cast<float>(x) <= x1 && static_cast<float>(y) >= y0 && static_cast<float>(y) <= y1) return static_cast<int>(i);
  }
  return -1;
}

void Hud::minimap(ID3D11ShaderResourceView* background, float min_x, float min_z, float max_x, float max_z, const std::vector<MapUnit>& units,
                  const float* view_corners) {
  map_.shown = minimap_content_ != nullptr;
  map_.background = background;
  map_.min_x = min_x, map_.min_z = min_z, map_.max_x = max_x, map_.max_z = max_z;
  map_.units = units;
  map_.has_view = view_corners != nullptr;
  if (view_corners) std::memcpy(map_.view, view_corners, sizeof map_.view);
}

void Hud::draw(Gpu& gpu) {
  const float w = static_cast<float>(gpu.width()), h = static_cast<float>(gpu.height());
  // ---- floating bars: each element keeps its place relative to its scene's anchor; borders under meters (layers)
  struct Item {
    const UiElement* e;
    float x, y, fill;
    const float* tint;
  };
  static const float white[4] = {1, 1, 1, 1};
  std::vector<Item> items;
  for (const Bar& b : bars_) {
    const Style& s = *b.style;
    const float ox = b.x - s.anchor->x, oy = b.y - s.anchor->y;
    if (s.border) items.push_back({s.border, ox, oy, 1.f, white});

    // loss decay bar: if decay_fraction > fraction
    if (b.decay_fraction > b.fraction && s.bar) {
      static const float decay_tint[4] = {1.0f, 0.35f, 0.3f, 0.9f};
      items.push_back({s.bar, ox, oy, b.decay_fraction, decay_tint});
    }

    // a champion's meter has a texture for each colour: green for the player's own, blue for allies, red for enemies
    auto own = s.bars.find(fnv1a(b.side == Side::Self ? "Green" : b.side == Side::Ally ? "Blue" : "Red"));
    const UiElement* health_elem = (own != s.bars.end() && own->second) ? own->second : s.bar;
    const float* health_tint = (own != s.bars.end() && own->second) ? white : (b.side == Side::Enemy ? enemy_ : ally_);
    if (health_elem) items.push_back({health_elem, ox, oy, b.fraction, health_tint});

    // active shield bar overlay: if shield_fraction > 0
    if (b.shield_fraction > 0 && health_elem) {
      static const float shield_tint[4] = {0.9f, 0.95f, 1.0f, 0.85f};
      items.push_back({health_elem, ox, oy, std::min(1.0f, b.fraction + b.shield_fraction), shield_tint});
    }
  }
  std::stable_sort(items.begin(), items.end(), [](const Item& a, const Item& b) { return a.e->layer < b.e->layer; });
  for (const Item& i : items) {
    const UiElement& e = *i.e;
    if (e.texture.empty() || i.fill <= 0) continue;
    const float x0 = i.x + e.x, y0 = i.y + e.y;
    ui_.quad(ui_.texture(gpu, e.texture), x0, y0, x0 + e.w * i.fill, y0 + e.h, e.u0 / e.tex_w, e.v0 / e.tex_h, (e.u0 + (e.u1 - e.u0) * i.fill) / e.tex_w,
             e.v1 / e.tex_h, i.tint);
  }

  // ---- the ticks over the meters, as each style's TickStyle spaces them. A tick element without a picture (the
  // champions' ChampHP_Tick / ChampHP_MicroTick: no TextureData) is drawn dark, as a gap in the meter [dedus: such an
  // element has nothing to draw but its rectangle; de măsurat against the game]; one with a picture (a structure's) as
  // its cut-out. A standard tick is the full height of its element, a micro tick its own (shorter) height.
  for (const Bar& b : bars_) {
    const Style& s = *b.style;
    if (!s.bar || !s.standard_tick || b.max_hp <= 0) continue;
    float standard = 0;
    int between = 0;
    if (s.hero_ticks) {
      standard = s.hp_per_standard_tick;
      between = 9;  // [meta default microTicksBetween]
      for (const auto& [min_health, n] : s.micro_ticks)
        if (b.max_hp >= min_health) between = n;
    } else {
      standard = b.hp_per_tick;
    }
    if (standard <= 0) continue;
    const float ox = b.x - s.anchor->x, oy = b.y - s.anchor->y;
    const float x0 = ox + s.bar->x, bw = s.bar->w;
    auto tick = [&](const UiElement& e, float hp) {
      const float tx = std::floor(x0 + hp / b.max_hp * bw - e.w * 0.5f + 0.5f);
      static const float gap[4] = {0, 0, 0, 1};
      if (e.texture.empty())
        ui_.quad(ui_.white(), tx, oy + e.y, tx + e.w, oy + e.y + e.h, 0, 0, 1, 1, gap);
      else
        ui_.quad(ui_.texture(gpu, e.texture), tx, oy + e.y, tx + e.w, oy + e.y + e.h, e.u0 / e.tex_w, e.v0 / e.tex_h, e.u1 / e.tex_w, e.v1 / e.tex_h, e.color);
    };
    const float step = between > 0 && s.micro_tick ? standard / static_cast<float>(between + 1) : standard;
    for (int i = 1; i * step < b.max_hp - 0.5f && i < 400; ++i) {
      const float hp = static_cast<float>(i) * step;
      const bool is_standard = s.micro_tick == nullptr || between <= 0 || i % (between + 1) == 0;
      tick(is_standard ? *s.standard_tick : *s.micro_tick, hp);
    }
  }
  bars_.clear();

  if (shop_view_.open && shop_ok_) draw_shop(gpu, w, h);
  if (frame_shown_) {
    // ---- the panels around the player's frame, then the frame
    stats_scene_.draw(gpu, ui_, fonts_, w, h);
    inventory_scene_.draw(gpu, ui_, fonts_, w, h);
    frame_scene_.draw(gpu, ui_, fonts_, w, h);
    header_scene_.draw(gpu, ui_, fonts_, w, h);
  }

  // ---- the minimap: the map's picture in the content rectangle, the units' icons, the frame over them
  if (frame_shown_ && map_.shown && minimap_content_) {
    float x0, y0, x1, y1;
    minimap_scene_.place(*minimap_content_, w, h, x0, y0, x1, y1);
    if (map_.background) ui_.quad(map_.background, x0, y0, x1, y1, 0, 0, 1, 1, white);
    const float k = h / std::max(1.f, minimap_content_->src_h);
    auto to_map = [&](float wx, float wz, float& px, float& py) {
      // the world's x to the right, its z up
      px = x0 + (wx - map_.min_x) / (map_.max_x - map_.min_x) * (x1 - x0);
      py = y1 - (wz - map_.min_z) / (map_.max_z - map_.min_z) * (y1 - y0);
    };
    // structures first, then minions, then champions on top
    for (int pass = 0; pass < 3; ++pass)
      for (const MapUnit& u : map_.units) {
        const int rank = u.icon == kChampion ? 2 : u.icon == kMinion ? 1 : 0;
        if (rank != pass) continue;
        auto def = map_icons_.find(u.icon);
        if (def == map_icons_.end()) continue;
        const MapIconDef& d = def->second;
        float px, py;
        to_map(u.x, u.z, px, py);
        // an icon's size is for the largest minimap; mMinScale is the smallest [de măsurat: the scale the game's default
        // minimap size gives; the smallest here]
        const float hw = d.size[0] * d.min_scale * k * 0.5f, hh = d.size[1] * d.min_scale * k * 0.5f;
        const float* tint = d.has_team_colors ? d.team_color[u.side == Side::Enemy ? 1 : 0] : d.color;
        if (ID3D11ShaderResourceView* tex = d.texture.empty() ? nullptr : ui_.texture(gpu, d.texture)) ui_.quad(tex, px - hw, py - hh, px + hw, py + hh, 0, 0, 1, 1, tint);
        // a champion: its round portrait inside the team-coloured disc [de măsurat: how much of the disc shows]
        if (u.portrait) ui_.quad(u.portrait, px - hw * 0.84f, py - hh * 0.84f, px + hw * 0.84f, py + hh * 0.84f, 0, 0, 1, 1, white);
      }
    // what the camera sees: a white rectangle, square with the map, around the ground the camera's corners fall on
    // [măsurat: 14.1 replay H8T525O4zFc at 1:16, the box's height / width is 0.548; the bounding box of the four ground
    // corners gives 0.545 at any zoom, the trapezoid's mean width 0.678; line width de măsurat]
    if (map_.has_view) {
      float lo_x = 1e9f, lo_y = 1e9f, hi_x = -1e9f, hi_y = -1e9f;
      for (int i = 0; i < 4; ++i) {
        float px, py;
        to_map(map_.view[i * 2], map_.view[i * 2 + 1], px, py);
        lo_x = std::min(lo_x, px), hi_x = std::max(hi_x, px), lo_y = std::min(lo_y, py), hi_y = std::max(hi_y, py);
      }
      lo_x = std::clamp(lo_x, x0, x1), hi_x = std::clamp(hi_x, x0, x1), lo_y = std::clamp(lo_y, y0, y1), hi_y = std::clamp(hi_y, y0, y1);
      const float pts[8] = {lo_x, lo_y, hi_x, lo_y, hi_x, hi_y, lo_x, hi_y};
      for (int i = 0; i < 4; ++i) {
        const float ax = pts[i * 2], ay = pts[i * 2 + 1], bx = pts[((i + 1) % 4) * 2], by = pts[((i + 1) % 4) * 2 + 1];
        const float dx = bx - ax, dy = by - ay, len = std::sqrt(dx * dx + dy * dy);
        if (len < 0.5f) continue;
        const float nx = -dy / len * 0.75f, ny = dx / len * 0.75f;
        const float t1[6] = {ax - nx, ay - ny, ax + nx, ay + ny, bx + nx, by + ny}, t2[6] = {ax - nx, ay - ny, bx + nx, by + ny, bx - nx, by - ny};
        const float uv[6] = {0, 0, 0, 0, 0, 0};
        ui_.triangle(ui_.white(), t1, uv, white);
        ui_.triangle(ui_.white(), t2, uv, white);
      }
    }
    minimap_scene_.draw(gpu, ui_, fonts_, w, h);
  }

  // ---- the target frame
  if (target_info_.valid && target_ok_) {
    char text[64];
    auto number = [&](UiElement* e, const char* format, double v) {
      if (!e) return;
      std::snprintf(text, sizeof text, format, v);
      e->text = text;
    };
    if (target_portrait_) {
      target_portrait_->image = target_info_.portrait;
      target_portrait_->enabled = (target_info_.portrait != nullptr);
    }
    if (target_level_) target_level_->text = std::to_string(target_info_.level);
    target_scene_.meter(target_hp_meter_, target_info_.max_hp > 0 ? target_info_.hp / target_info_.max_hp : 0.f);
    if (target_hp_text_) {
      std::snprintf(text, sizeof text, "%.0f / %.0f", std::ceil(target_info_.hp), std::ceil(target_info_.max_hp));
      target_hp_text_->text = text;
    }
    const bool has_par = target_info_.max_par > 0;
    target_scene_.meter(target_par_meter_, has_par ? target_info_.par / target_info_.max_par : 0.f);
    if (target_par_text_) {
      std::snprintf(text, sizeof text, "%.0f / %.0f", std::floor(target_info_.par), std::floor(target_info_.max_par));
      target_par_text_->text = has_par ? text : "";
    }
    auto stat = [&](int key, const char* format, double v) {
      auto it = target_stat_texts_.find(key);
      if (it != target_stat_texts_.end()) number(it->second, format, v);
    };
    stat(0, "%.0f", target_info_.ap), stat(1, "%.0f", target_info_.armor), stat(2, "%.0f", target_info_.ad), stat(3, "%.2f", target_info_.attack_speed);
    stat(5, "%.0f", target_info_.spell_block), stat(6, "%.0f", target_info_.move_speed), stat(7, "%.0f%%", target_info_.crit * 100.0), stat(10, "%.0f", target_info_.ability_haste);
    for (int i = 0; i < 7; ++i) {
      if (target_item_icons_[i]) {
        target_item_icons_[i]->image = target_info_.item_icons[i];
        target_item_icons_[i]->enabled = (target_info_.item_icons[i] != nullptr);
      }
      if (target_item_stacks_[i]) {
        target_item_stacks_[i]->enabled = target_info_.item_stacks[i] > 1;
        if (target_info_.item_stacks[i] > 1) target_item_stacks_[i]->text = std::to_string(target_info_.item_stacks[i]);
        else target_item_stacks_[i]->text.clear();
      }
    }
    if (target_kda_text_) {
      std::snprintf(text, sizeof text, "%d/%d/%d", target_info_.kills, target_info_.deaths, target_info_.assists);
      target_kda_text_->text = text;
    }
    if (target_cs_text_) target_cs_text_->text = std::to_string(target_info_.cs);
    target_scene_.draw(gpu, ui_, fonts_, w, h);
  }

  // ---- the scoreboard (TAB)
  if (scoreboard_view_.open && scoreboard_ok_) {
    draw_scoreboard(gpu, w, h);
  }

  // ---- end of game (Victory / Defeat)
  if (eog_.shown) {
    static const float dim[4] = {0.f, 0.f, 0.f, 0.75f};
    ui_.quad(ui_.white(), 0, 0, w, h, 0, 0, 1, 1, dim);
    ID3D11ShaderResourceView* banner = eog_.victory ? victory_banner_tex_ : defeat_banner_tex_;
    if (banner) {
      const float bw = 640.f, bh = 220.f;
      const float bx0 = (w - bw) * 0.5f, by0 = h * 0.25f;
      ui_.quad(banner, bx0, by0, bx0 + bw, by0 + bh, 0, 0, 1, 1, white);
    }
  }

  // ---- floating combat text
  for (const FctNumber& fct : fct_numbers_) {
    const float y_offset = -fct.age * 55.f;
    const float alpha = std::clamp(1.f - (fct.age / fct.max_age), 0.f, 1.f);
    float col[4] = {fct.color[0], fct.color[1], fct.color[2], fct.color[3] * alpha};
    UiFonts::Desc desc;
    desc.size = fct.is_crit ? 24.f : 16.f;
    std::memcpy(desc.color, col, sizeof col);
    desc.outline = 1.5f;
    desc.outline_color[0] = desc.outline_color[1] = desc.outline_color[2] = 0.f;
    desc.outline_color[3] = alpha;
    fonts_.draw(gpu, ui_, desc, fct.text, fct.x - 60.f, fct.y + y_offset - 15.f, fct.x + 60.f, fct.y + y_offset + 15.f, 1, 1, h, col);
  }

  map_.shown = false;
  frame_shown_ = false;
  ui_.flush(gpu);
}

void Hud::localize(const StringTable& strings) {
  for (UiScene* s : {&bars_scene_, &frame_scene_, &stats_scene_, &inventory_scene_, &header_scene_, &minimap_scene_, &shop_scene_, &target_scene_, &scoreboard_scene_, &eog_scene_}) s->localize(strings);
}

std::vector<std::string> Hud::shop_group_keys() const {
  std::vector<std::string> out;
  for (const ShopGroup& g : shop_groups_) out.push_back(g.key);
  return out;
}

void Hud::draw_shop(Gpu& gpu, float w, float h) {
  shop_scene_.show_scene(shop_main_scene_, true);
  if (shop_gold_text_) shop_gold_text_->text = std::to_string(static_cast<int>(std::floor(shop_view_.gold)));
  if (detail_title_) detail_title_->text = shop_view_.title;
  if (detail_cost_) detail_cost_->text = shop_view_.cost_text;
  if (detail_icon_) detail_icon_->image = shop_view_.selected_icon, detail_icon_->enabled = shop_view_.selected_icon != nullptr;
  // the card template's parts are drawn by hand, once per item: hidden from the scene's own drawing
  for (UiElement* e : {card_.icon, card_.frame, card_.selected, card_.unpurchaseable, card_.cost, card_.cost_unpurchaseable, card_.cost_selected})
    if (e) e->enabled = false;
  if (shop_header_) shop_header_->enabled = false;
  shop_scene_.draw(gpu, ui_, fonts_, w, h);

  // ---- the All Items tab: a title row per group, then its items left to right, wrapping, inside the pane's scroll
  // region. The template's geometry: a title row (AllItemsHeaderRegion), the first cell (AllItemsItemRegion) where the
  // template puts it under the title, cells side by side, rows one cell high [dedus: the game's layout code; the next
  // group's title right under the last row]
  float ax0, ay0, ax1, ay1, cx0, cy0, cx1, cy1, hx0, hy0, hx1, hy1, tx0, ty0, tx1, ty1;
  shop_scene_.place(*shop_area_, w, h, ax0, ay0, ax1, ay1);
  shop_scene_.place(*shop_region_, w, h, cx0, cy0, cx1, cy1);
  shop_scene_.place(*shop_header_region_, w, h, hx0, hy0, hx1, hy1);
  const UiElement* anchor = card_.hit ? card_.hit : card_.frame ? card_.frame : card_.icon;
  shop_scene_.place(*anchor, w, h, tx0, ty0, tx1, ty1);
  const float cw = cx1 - cx0, ch = cy1 - cy0;
  const float cell_dx = cx0 - hx0, cell_dy = cy0 - hy0;  // where the first cell sits from its title row
  placed_cards_.clear();
  float y = ay0 - static_cast<float>(shop_scroll_) * ch;  // scrolled by whole rows
  auto visible = [&](float top, float height) { return top >= ay0 - 0.5f && top + height <= ay1 + 0.5f; };
  for (size_t g = 0; g < shop_groups_.size(); ++g) {
    std::vector<const ShopItem*> in;
    for (const ShopItem& it : shop_view_.items)
      if (std::find(shop_groups_[g].epicness.begin(), shop_groups_[g].epicness.end(), it.epicness) != shop_groups_[g].epicness.end()) in.push_back(&it);
    if (in.empty()) continue;
    if (y > ay1) break;
    if (shop_header_ && visible(y, cell_dy)) {
      shop_header_->text = g < shop_view_.group_titles.size() ? shop_view_.group_titles[g] : shop_groups_[g].key;
      shop_scene_.draw_element(gpu, ui_, fonts_, *shop_header_, w, h, ax0 - hx0, y - hy0);
    }
    float x = ax0 + cell_dx, row = y + cell_dy;
    for (const ShopItem* it : in) {
      if (x + cw > ax1 + 0.5f) x = ax0 + cell_dx, row += ch;
      if (!visible(row, ch)) {
        x += cw;
        continue;
      }
      const float dx = x - tx0, dy = row - ty0;
      const bool selected = it->id == shop_view_.selected;
      if (card_.icon) card_.icon->image = it->icon, card_.icon->saturation = it->affordable ? 1.f : card_.icon->min_saturation;
      if (card_.icon && it->icon) shop_scene_.draw_element(gpu, ui_, fonts_, *card_.icon, w, h, dx, dy);
      if (card_.frame) shop_scene_.draw_element(gpu, ui_, fonts_, *card_.frame, w, h, dx, dy);
      if (!it->affordable && card_.unpurchaseable) shop_scene_.draw_element(gpu, ui_, fonts_, *card_.unpurchaseable, w, h, dx, dy);
      if (selected && card_.selected) shop_scene_.draw_element(gpu, ui_, fonts_, *card_.selected, w, h, dx, dy);
      UiElement* cost = selected && card_.cost_selected ? card_.cost_selected : !it->affordable && card_.cost_unpurchaseable ? card_.cost_unpurchaseable : card_.cost;
      if (cost) {
        cost->text = std::to_string(it->cost);
        shop_scene_.draw_element(gpu, ui_, fonts_, *cost, w, h, dx, dy);
      }
      placed_cards_.push_back({it->id, x, row, x + cw, row + ch});
      x += cw;
    }
    y = row + ch;
  }
}

int Hud::shop_hit(Gpu& gpu, int x, int y, int* item) const {
  if (item) *item = 0;
  if (!shop_view_.open || !shop_ok_) return kShopNothing;
  const float w = static_cast<float>(gpu.width()), h = static_cast<float>(gpu.height()), px = static_cast<float>(x), py = static_cast<float>(y);
  auto inside = [&](const UiElement* e) {
    if (!e) return false;
    float x0, y0, x1, y1;
    shop_scene_.place(*e, w, h, x0, y0, x1, y1);
    return px >= x0 && px <= x1 && py >= y0 && py <= y1;
  };
  for (const PlacedCard& c : placed_cards_)
    if (px >= c.x0 && px <= c.x1 && py >= c.y0 && py <= c.y1) {
      if (item) *item = c.id;
      return kShopInside;
    }
  if (inside(purchase_hit_)) return kShopPurchase;
  if (inside(sell_hit_)) return kShopSell;
  if (inside(close_hit_)) return kShopClose;
  // anywhere on the shop's window [dedus: the All Items pane widened by the details panel beside it]
  float rx0, ry0, rx1, ry1;
  shop_scene_.place(*shop_area_, w, h, rx0, ry0, rx1, ry1);
  const float margin_y = (ry1 - ry0) * 0.35f;
  if (px >= rx0 - 20 && px <= rx1 + (rx1 - rx0) * 0.55f && py >= ry0 - margin_y && py <= ry1 + margin_y * 0.5f) return kShopInside;
  return kShopNothing;
}

int Hud::inventory_slot_at(Gpu& gpu, int x, int y) const {
  const float w = static_cast<float>(gpu.width()), h = static_cast<float>(gpu.height()), px = static_cast<float>(x), py = static_cast<float>(y);
  for (size_t k = 0; k < inv_slots_.size(); ++k) {
    const UiElement* e = inv_slots_[k].hit ? inv_slots_[k].hit : inv_slots_[k].icon;
    if (!e) continue;
    float x0, y0, x1, y1;
    inventory_scene_.place(*e, w, h, x0, y0, x1, y1);
    if (px >= x0 && px <= x1 && py >= y0 && py <= y1) return static_cast<int>(k);
  }
  return -1;
}

}  // namespace ba
