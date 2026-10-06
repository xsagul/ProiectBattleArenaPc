#pragma once
// League's items as patch 14.1 ships them, read from the data, never typed in by hand:
//   Global.wad: one property bin (path unknown, found by its content: 501 ItemData, 424 item SpellObjects, 224
//   ItemGroup) holds every item: itemID, price (what combining costs on top of the components), recipeItemLinks (the
//   components), the stat mods (mFlat*/mPercent*), mItemGroups (ownership limits and the slot range), maxStack,
//   mCanBeSold, sellBackModifier [meta default 0.7], mItemDataAvailability mInStore, consumed, the icons.
//   map11.bin: the mode's GameModeMapData (CLASSIC) lists its GameModeItemLists: the items the mode sells.
// What an item's passive or active does is the server's code at Riot (its SpellObject only has numbers).

#include <array>
#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <vector>

#include "ba/PropertyBin.h"
#include "ba/Wad.h"

namespace ba {

/** What owning an item adds to a champion (its mFlat* / mPercent* fields; meta default 0 for each). */
struct ItemStats {
  float hp = 0, ad = 0, ap = 0, armor = 0, spell_block = 0, attack_speed_pct = 0, crit = 0, crit_damage = 0;
  float move_speed = 0, move_speed_pct = 0, mana = 0, ability_haste = 0;
  float hp_regen = 0, base_hp_regen_pct = 0, mana_regen = 0, base_mana_regen_pct = 0;
  float life_steal = 0, omnivamp = 0, magic_pen = 0, magic_pen_pct = 0, armor_pen_pct = 0, tenacity = 0, heal_shield = 0, slow_resist = 0;
  ItemStats& operator+=(const ItemStats& o);
};

struct ItemGroupDef {
  uint32_t entry = 0;
  int max_ownable = -1;    // mMaxGroupOwnable [meta default -1: no limit]
  int slot_min = 0, slot_max = 5;  // mInventorySlotMin / Max [meta defaults 0, 5]: the trinkets' group says 6..6
  float purchase_cooldown = 0;     // mPurchaseCooldown [meta default 0]
};

struct ItemDef {
  uint32_t entry = 0;      // its entry's name hash (what recipes and lists link to)
  int id = 0;              // itemID
  std::string name_key;    // mDisplayName: the localisation key
  int price = 0;           // what it costs on top of its components [meta default 0]
  std::vector<int> components;  // recipeItemLinks, as item ids
  std::vector<uint32_t> groups; // mItemGroups
  int max_stack = 1;       // maxStack [meta default 0; 0 and 1 both mean one per slot]
  bool can_be_sold = false;     // mCanBeSold [meta default false]
  float sell_back = 0.7f;       // sellBackModifier [meta default 0.7]
  bool in_store = false;        // mItemDataAvailability mInStore
  bool consumed = false;        // consumed: used up when activated (potions)
  bool consume_on_acquire = false;
  std::string required_champion;  // mRequiredChampion
  std::string icon;             // mItemDataClient inventoryIcon (.dds)
  std::vector<std::string> categories;  // mCategories (the shop's filters)
  int epicness = 2;             // [meta default 2]
  ItemStats stats;
};

struct ItemTable {
  std::map<int, ItemDef> items;               // by itemID
  std::map<uint32_t, int> id_of_entry;        // entry name hash -> itemID
  std::map<uint32_t, ItemGroupDef> groups;    // by entry name hash
  std::set<int> mode_items;                   // what the mode's lists sell (empty: every in-store item)

  /** What buying `id` costs in all: its price plus its components', recursively. */
  int total_cost(int id) const;
  const ItemDef* find(int id) const {
    auto it = items.find(id);
    return it == items.end() ? nullptr : &it->second;
  }
};

/** Reads every item of Global.wad (the bin is found by its content). */
bool read_items(const Wad& global, ItemTable& out);
/** The items the map's game mode sells: its GameModeMapData's itemLists (mode name e.g. "CLASSIC"). */
void read_mode_items(const PropertyBin& map_bin, const std::string& mode, ItemTable& table);

}  // namespace ba
