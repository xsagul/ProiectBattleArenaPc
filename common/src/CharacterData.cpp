#include "ba/CharacterData.h"

#include "ba/Hash.h"
#include "ba/PropertyBin.h"

namespace ba {

namespace {

const BinValue* unwrap(const BinValue* v) {
  if (v && v->type == BinType::Option) return v->items.empty() ? nullptr : &v->items[0];
  return v;
}

/** A stat: patch 14.1 stores it as a plain number (`baseHP`), later patches as a struct (`baseHPModifiable.baseValue`). */
float stat(const BinEntry& e, const char* plain, const char* modifiable, float dflt) {
  if (const BinValue* v = e.field(plain)) return static_cast<float>(v->number());
  const BinValue* m = e.field(modifiable);
  const BinValue* v = m ? m->field("baseValue") : nullptr;
  return v ? static_cast<float>(v->number()) : dflt;
}

AttackSlot read_slot(const BinValue& s, const std::string& default_name) {
  AttackSlot a;
  a.name = default_name;
  if (const BinValue* v = unwrap(s.field("mAttackName"))) a.name = v->str;
  if (const BinValue* v = unwrap(s.field("mAttackProbability"))) a.probability = static_cast<float>(v->number());
  if (const BinValue* v = unwrap(s.field("mAttackDelayCastOffsetPercent"))) a.has_offset = true, a.offset = static_cast<float>(v->number());
  if (const BinValue* v = unwrap(s.field("mAttackDelayCastOffsetPercentAttackSpeedRatio"))) a.windup_modifier = static_cast<float>(v->number());
  const BinValue* ct = unwrap(s.field("mAttackCastTime"));
  const BinValue* tt = unwrap(s.field("mAttackTotalTime"));
  if (ct && tt) a.has_times = true, a.cast_time = static_cast<float>(ct->number()), a.total_time = static_cast<float>(tt->number());
  return a;
}

}  // namespace

bool read_character_record(const Wad& wad, const std::string& character, CharacterRecordData& out) {
  return read_character_record_at(wad, "Characters/" + character + "/CharacterRecords/Root", out);
}

bool read_character_record_at(const Wad& wad, const std::string& record_path, CharacterRecordData& out) {
  const size_t a = record_path.find('/'), b = a == std::string::npos ? a : record_path.find('/', a + 1);
  if (b == std::string::npos) return false;
  const std::string character = record_path.substr(a + 1, b - a - 1);
  std::string lower = character;
  for (char& c : lower) c = static_cast<char>(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
  auto bytes = wad.read("data/characters/" + lower + "/" + lower + ".bin");
  if (!bytes) return false;
  const PropertyBin bin(*bytes);
  const BinEntry* record = bin.entry(record_path);
  const bool root = record_path.size() > 5 && record_path.compare(record_path.size() - 5, 5, "/Root") == 0;
  if (!record && root)  // a few characters name their only record otherwise
    for (const BinEntry& e : bin.entries())
      if (e.cls == fnv1a("CharacterRecord")) record = &e;
  if (!record) return false;
  out.name = character;
  if (const BinValue* t = record->field("unitTagsString")) out.tags = t->str;
  out.move_speed = stat(*record, "baseMoveSpeed", "baseMoveSpeedModifiable", 100);
  if (const BinValue* r = record->field("pathfindingCollisionRadius")) out.pathfinding_radius = static_cast<float>(r->number());
  if (const BinValue* r = record->field("selectionRadius")) out.selection_radius = static_cast<float>(r->number());
  if (const BinValue* r = record->field("selectionHeight")) out.selection_height = static_cast<float>(r->number());
  if (const BinValue* r = record->field("healthBarHeight")) out.health_bar_height = static_cast<float>(r->number());
  if (const BinValue* r = record->field("healthBarFullParallax")) out.health_bar_parallax = r->number() != 0;
  out.base_hp = stat(*record, "baseHP", "baseHPModifiable", 100);
  out.base_damage = stat(*record, "baseDamage", "baseDamageModifiable", 10);
  out.base_armor = stat(*record, "baseArmor", "baseArmorModifiable", 1);
  out.attack_range = stat(*record, "attackRange", "attackRangeModifiable", 100);
  out.attack_speed = stat(*record, "attackSpeed", "attackSpeedModifiable", 0);
  out.attack_speed_ratio = stat(*record, "attackSpeedRatio", "attackSpeedRatioModifiable", 1);
  if (const BinValue* r = unwrap(record->field("overrideGameplayCollisionRadius"))) out.gameplay_radius = static_cast<float>(r->number());
  out.base_spell_block = stat(*record, "baseSpellBlock", "baseSpellBlockModifiable", 0);
  auto num = [&](const char* f, float d) {
    const BinValue* v = unwrap(record->field(f));
    return v ? static_cast<float>(v->number()) : d;
  };
  out.acquisition_range = num("acquisitionRange", 750);  // [meta defaults: 750, 48, 25, 0, 0]
  out.wake_up_range = num("wakeUpRange", 0), out.first_acquisition_range = num("firstAcquisitionRange", 0);
  out.tower_priority_boost = num("towerTargetingPriorityBoost", 0);
  out.exp_given = num("expGivenOnDeath", 48);
  out.gold_given = num("goldGivenOnDeath", 25);
  out.local_gold_given = num("localGoldGivenOnDeath", 0);
  out.global_gold_given = num("globalGoldGivenOnDeath", 0);
  out.hp_per_level = num("hpPerLevel", 0), out.damage_per_level = num("damagePerLevel", 0), out.armor_per_level = num("armorPerLevel", 0);
  out.spell_block_per_level = num("spellBlockPerLevel", 0), out.attack_speed_per_level = num("attackSpeedPerLevel", 0);
  out.hp_regen = num("baseStaticHPRegen", 0), out.hp_regen_per_level = num("hpRegenPerLevel", 0);
  if (const BinValue* ar = record->field("primaryAbilityResource")) {
    auto f = [ar](const char* name) {
      const BinValue* v = ar->field(name);
      return v ? static_cast<float>(v->number()) : 0.f;
    };
    out.ar_type = static_cast<int>(f("arType"));
    out.ar_base = f("arBase"), out.ar_per_level = f("arPerLevel"), out.ar_regen = f("arBaseStaticRegen"), out.ar_regen_per_level = f("arRegenPerLevel");
    out.ar_increments = f("arIncrements");
  }
  if (const BinValue* p = record->field("passive1IconName")) out.passive_icon = p->str;
  if (const BinValue* names = record->field("spellNames"))
    for (size_t i = 0; i < 4 && i < names->items.size(); ++i) {
      out.spells[i] = names->items[i].str;
      const BinEntry* spell = bin.entry("Characters/" + character + "/Spells/" + out.spells[i]);
      const BinValue* data = spell ? spell->field("mSpell") : nullptr;
      if (const BinValue* icons = data ? data->field("mImgIconName") : nullptr; icons && !icons->items.empty()) out.spell_icons[i] = icons->items[0].str;
    }

  // attack slots, then each one's SpellObject (Characters/<Name>/Spells/<AttackName>)
  out.attacks.clear(), out.crits.clear();
  if (const BinValue* b = record->field("basicAttack")) out.attacks.push_back(read_slot(*b, character + "BasicAttack"));
  if (const BinValue* l = record->field("extraAttacks"))
    for (const BinValue& s : l->items) out.attacks.push_back(read_slot(s, character + "BasicAttack"));
  if (const BinValue* l = record->field("critAttacks"))
    for (const BinValue& s : l->items) out.crits.push_back(read_slot(s, character + "CritAttack"));
  if (out.attacks.empty()) out.attacks.push_back(AttackSlot{character + "BasicAttack"});
  for (std::vector<AttackSlot>* list : {&out.attacks, &out.crits})
    for (AttackSlot& a : *list) {
      const BinEntry* spell = bin.entry("Characters/" + character + "/Spells/" + a.name);
      const BinValue* data = spell ? spell->field("mSpell") : nullptr;
      if (!data) continue;
      if (const BinValue* v = data->field("mAnimationName")) a.animation = v->str;
      if (const BinValue* v = data->field("spellCastTime")) a.spell_cast_time = static_cast<float>(v->number());
      if (const BinValue* v = data->field("missileSpeed")) a.missile_speed = static_cast<float>(v->number());
      const BinValue* spec = data->field("mMissileSpec");
      a.missile = spec != nullptr;
      if (const BinValue* mv = spec ? spec->field("movementComponent") : nullptr) {
        if (const BinValue* v = mv->field("mSpeed")) a.missile_speed = static_cast<float>(v->number());
        if (const BinValue* v = mv->field("mTracksTarget")) a.tracks_target = v->number() != 0;
        if (const BinValue* v = mv->field("mStartBoneName")) a.start_bone = v->str;
        if (const BinValue* v = mv->field("mTargetHeightAugment")) a.target_height_augment = static_cast<float>(v->number());
        if (const BinValue* v = mv->field("mOffsetInitialTargetHeight")) a.offset_initial_target_height = static_cast<float>(v->number());
        if (const BinValue* v = mv->field("mUseGroundHeightAtTarget")) a.ground_height_at_target = v->number() != 0;
      }
      if (const BinValue* v = data->field("mMissileEffectKey")) a.missile_effect = static_cast<uint32_t>(v->u);
      if (const BinValue* v = data->field("mHitEffectKey")) a.hit_effect = static_cast<uint32_t>(v->u);
      if (const BinValue* v = data->field("mHitEffectOrientType")) a.hit_effect_orient = static_cast<int>(v->number());
      const BinValue* has_bone = data->field("bHaveHitBone");
      if (const BinValue* v = data->field("mHitBoneName"); v && has_bone && has_bone->number() != 0) a.hit_bone = v->str;
    }
  return true;
}

const AttackSlot* find_attack(const CharacterRecordData& r, const std::string& spell) {
  for (const std::vector<AttackSlot>* list : {&r.attacks, &r.crits})
    for (const AttackSlot& a : *list)
      if (a.name == spell) return &a;
  return nullptr;
}

}  // namespace ba
