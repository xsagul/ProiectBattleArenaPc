#include "ba/ItemData.h"

#include <cstring>
#include <functional>

#include "ba/Hash.h"

namespace ba {

ItemStats& ItemStats::operator+=(const ItemStats& o) {
  hp += o.hp, ad += o.ad, ap += o.ap, armor += o.armor, spell_block += o.spell_block, attack_speed_pct += o.attack_speed_pct;
  crit += o.crit, crit_damage += o.crit_damage, move_speed += o.move_speed, move_speed_pct += o.move_speed_pct, mana += o.mana;
  ability_haste += o.ability_haste, hp_regen += o.hp_regen, base_hp_regen_pct += o.base_hp_regen_pct, mana_regen += o.mana_regen;
  base_mana_regen_pct += o.base_mana_regen_pct, life_steal += o.life_steal, omnivamp += o.omnivamp, magic_pen += o.magic_pen;
  magic_pen_pct += o.magic_pen_pct, armor_pen_pct += o.armor_pen_pct, tenacity += o.tenacity, heal_shield += o.heal_shield;
  slow_resist += o.slow_resist;
  return *this;
}

namespace {

double num(const BinValue* v, double dflt) { return v ? v->number() : dflt; }

/** Whether a property bin's entry list names a class (read off its header, without parsing the bin). */
bool bin_has_class(const std::vector<uint8_t>& d, uint32_t cls) {
  size_t o = 0;
  if (d.size() < 12) return false;
  if (std::memcmp(d.data(), "PTCH", 4) == 0) o = 16;
  if (o + 8 > d.size() || std::memcmp(d.data() + o, "PROP", 4) != 0) return false;
  o += 4;
  uint32_t version = 0;
  std::memcpy(&version, d.data() + o, 4), o += 4;
  if (version >= 2) {
    uint32_t links = 0;
    if (o + 4 > d.size()) return false;
    std::memcpy(&links, d.data() + o, 4), o += 4;
    for (uint32_t i = 0; i < links; ++i) {
      uint16_t len = 0;
      if (o + 2 > d.size()) return false;
      std::memcpy(&len, d.data() + o, 2), o += 2 + len;
    }
  }
  uint32_t n = 0;
  if (o + 4 > d.size()) return false;
  std::memcpy(&n, d.data() + o, 4), o += 4;
  for (uint32_t i = 0; i < n && o + 4 <= d.size(); ++i, o += 4) {
    uint32_t c = 0;
    std::memcpy(&c, d.data() + o, 4);
    if (c == cls) return true;
  }
  return false;
}

ItemStats read_stats(const BinEntry& e) {
  ItemStats s;
  auto f = [&](const char* name) { return static_cast<float>(num(e.field(name), 0)); };
  s.hp = f("mFlatHPPoolMod"), s.ad = f("mFlatPhysicalDamageMod"), s.ap = f("mFlatMagicDamageMod");
  s.armor = f("mFlatArmorMod"), s.spell_block = f("mFlatSpellBlockMod"), s.attack_speed_pct = f("mPercentAttackSpeedMod");
  s.crit = f("mFlatCritChanceMod"), s.crit_damage = f("mFlatCritDamageMod");
  s.move_speed = f("mFlatMovementSpeedMod"), s.move_speed_pct = f("mPercentMovementSpeedMod");
  s.mana = f("flatMPPoolMod"), s.ability_haste = f("mAbilityHasteMod");
  s.hp_regen = f("mFlatHPRegenMod"), s.base_hp_regen_pct = f("mPercentBaseHPRegenMod");
  s.mana_regen = f("flatMPRegenMod"), s.base_mana_regen_pct = f("percentBaseMPRegenMod");
  s.life_steal = f("mPercentLifeStealMod"), s.omnivamp = f("PercentOmnivampMod");
  s.magic_pen = f("mFlatMagicPenetrationMod"), s.magic_pen_pct = f("mPercentMagicPenetrationMod");
  s.armor_pen_pct = f("mPercentArmorPenetrationMod"), s.tenacity = f("mPercentTenacityItemMod");
  s.heal_shield = f("mPercentHealingAmountMod"), s.slow_resist = f("mPercentSlowResistMod");
  return s;
}

}  // namespace

int ItemTable::total_cost(int id) const {
  const ItemDef* d = find(id);
  if (!d) return 0;
  int cost = d->price;
  for (int c : d->components) cost += total_cost(c);
  return cost;
}

bool read_items(const Wad& global, ItemTable& out) {
  const uint32_t item_cls = fnv1a("ItemData");
  // 14.1's items bin is entry {1d720f4f42640c18} (4.9 MB); another patch's is found by its content, among the big bins
  std::vector<uint64_t> order{0x1d720f4f42640c18ull};
  for (const auto& [h, e] : global.entries())
    if (h != order[0] && e.size > (1u << 20)) order.push_back(h);
  for (uint64_t h : order) {
    if (!global.entries().count(h)) continue;
    std::optional<std::vector<uint8_t>> bytes;
    try {
      bytes = global.read_hash(h);
    } catch (const std::exception&) {
      continue;
    }
    if (!bytes || !bin_has_class(*bytes, item_cls)) continue;
    const PropertyBin bin(*bytes);
    std::vector<std::pair<int, std::vector<uint32_t>>> recipes;  // item id -> component entries
    for (const BinEntry& en : bin.entries()) {
      if (en.cls == fnv1a("ItemGroup")) {
        ItemGroupDef g;
        g.entry = en.name;
        g.max_ownable = static_cast<int>(num(en.field("mMaxGroupOwnable"), -1));
        g.slot_min = static_cast<int>(num(en.field("mInventorySlotMin"), 0));
        g.slot_max = static_cast<int>(num(en.field("mInventorySlotMax"), 5));
        g.purchase_cooldown = static_cast<float>(num(en.field("mPurchaseCooldown"), 0));
        out.groups[g.entry] = g;
        continue;
      }
      if (en.cls != item_cls) continue;
      ItemDef d;
      d.entry = en.name;
      d.id = static_cast<int>(num(en.field("itemID"), 0));
      if (const BinValue* v = en.field("mDisplayName")) d.name_key = v->str;
      d.price = static_cast<int>(num(en.field("price"), 0));
      d.max_stack = static_cast<int>(num(en.field("maxStack"), 0));
      d.can_be_sold = num(en.field("mCanBeSold"), 0) != 0;
      d.sell_back = static_cast<float>(num(en.field("sellBackModifier"), 0.7));
      d.consumed = num(en.field("consumed"), 0) != 0;
      d.consume_on_acquire = num(en.field("consumeOnAcquire"), 0) != 0;
      d.epicness = static_cast<int>(num(en.field("epicness"), 2));
      if (const BinValue* v = en.field("mRequiredChampion")) d.required_champion = v->str;
      if (const BinValue* a = en.field("mItemDataAvailability")) d.in_store = num(a->field("mInStore"), 0) != 0;
      if (const BinValue* g = en.field("mItemGroups"))
        for (const BinValue& x : g->items) d.groups.push_back(static_cast<uint32_t>(x.u));
      if (const BinValue* c = en.field("mCategories"))
        for (const BinValue& x : c->items) d.categories.push_back(x.str);
      if (const BinValue* client = en.field("mItemDataClient"))
        if (const BinValue* icon = client->field("inventoryIcon")) d.icon = icon->str;
      d.stats = read_stats(en);
      std::vector<uint32_t> comps;
      if (const BinValue* r = en.field("recipeItemLinks"))
        for (const BinValue& x : r->items) comps.push_back(static_cast<uint32_t>(x.u));
      recipes.push_back({d.id, comps});
      out.id_of_entry[d.entry] = d.id;
      out.items[d.id] = std::move(d);
    }
    for (const auto& [id, comps] : recipes)
      for (uint32_t c : comps) {
        auto it = out.id_of_entry.find(c);
        if (it != out.id_of_entry.end()) out.items[id].components.push_back(it->second);
      }
    if (!out.items.empty()) return true;
  }
  return false;
}

void read_mode_items(const PropertyBin& map_bin, const std::string& mode, ItemTable& table) {
  for (const BinEntry& e : map_bin.entries()) {
    if (e.cls != fnv1a("GameModeMapData")) continue;
    const BinValue* name = e.field("mModeName");
    if (!name || !(name->str == mode || name->u == fnv1a(mode))) continue;
    if (const BinValue* lists = e.field("itemLists"))
      for (const BinValue& l : lists->items)
        if (const BinEntry* list = map_bin.entry(static_cast<uint32_t>(l.u)))
          if (const BinValue* items = list->field("mItems"))
            for (const BinValue& x : items->items) {
              auto it = table.id_of_entry.find(static_cast<uint32_t>(x.u));
              if (it != table.id_of_entry.end()) table.mode_items.insert(it->second);
            }
    return;
  }
}

}  // namespace ba
