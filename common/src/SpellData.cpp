#include "ba/SpellData.h"

#include <algorithm>

#include "ba/Hash.h"
#include "ba/PropertyBin.h"

namespace ba {

namespace {

const BinValue* unwrap(const BinValue* v) {
  if (v && v->type == BinType::Option) return v->items.empty() ? nullptr : &v->items[0];
  return v;
}

float num(const BinValue* v, float dflt = 0) {
  v = unwrap(v);
  return v ? static_cast<float>(v->number()) : dflt;
}

void ranks(const BinValue* list, std::array<float, 7>& out, size_t shift = 0) {
  if (!list) return;
  for (size_t i = 0; i < list->items.size() && i + shift < 7; ++i) out[i + shift] = static_cast<float>(list->items[i].number());
}

CalcPart read_part(const BinValue& v) {
  CalcPart p;
  p.cls = v.cls;
  p.stat = static_cast<int>(num(v.field("mStat")));          // [meta default 0: ability power]
  p.formula = static_cast<int>(num(v.field("mStatFormula")));  // [meta default 0: total]
  if (const BinValue* d = v.field("mDataValue")) p.value = static_cast<uint32_t>(d->u);
  if (v.cls == fnv1a("NumberCalculationPart")) {
    p.kind = CalcPart::Kind::Number, p.number = num(v.field("mNumber"));
  } else if (v.cls == fnv1a("NamedDataValueCalculationPart")) {
    p.kind = CalcPart::Kind::DataValue;
  } else if (v.cls == fnv1a("StatByNamedDataValueCalculationPart")) {
    p.kind = CalcPart::Kind::StatByDataValue;
  } else if (v.cls == fnv1a("StatByCoefficientCalculationPart")) {
    p.kind = CalcPart::Kind::StatByCoefficient, p.number = num(v.field("mCoefficient"));
  } else if (v.cls == fnv1a("EffectValueCalculationPart")) {
    p.kind = CalcPart::Kind::EffectValue, p.effect = static_cast<int>(num(v.field("mEffectIndex")));
  } else if (v.cls == fnv1a("ByCharLevelBreakpointsCalculationPart")) {
    p.kind = CalcPart::Kind::LevelBreakpoints;
    p.level1 = num(v.field("mLevel1Value")), p.per_level = num(v.field("mInitialBonusPerLevel"));
    if (const BinValue* list = v.field("mBreakpoints"))
      for (const BinValue& b : list->items)
        p.breakpoints.push_back({num(b.field("mLevel"), 1), num(b.field("mAdditionalBonusAtThisLevel")), num(b.field("mBonusPerLevelAtAndAfter"))});
  } else if (v.cls == fnv1a("ByCharLevelInterpolationCalculationPart")) {
    p.kind = CalcPart::Kind::LevelInterpolation, p.start = num(v.field("mStartValue")), p.end = num(v.field("mEndValue"));
  } else if (v.cls == fnv1a("ByCharLevelFormulaCalculationPart")) {
    p.kind = CalcPart::Kind::LevelFormula;
    if (const BinValue* list = v.field("mValues"))
      for (const BinValue& x : list->items) p.by_level.push_back(static_cast<float>(x.number()));
  } else if (v.cls == fnv1a("StatBySubPartCalculationPart")) {
    p.kind = CalcPart::Kind::StatBySubPart;
    if (const BinValue* s = v.field("mSubpart")) p.parts.push_back(read_part(*s));
  } else if (v.cls == 0xf3cbe7b2u) {
    // (a class the name list does not have: one field, mSpellCalculationKey: another calculation of the spell)
    p.kind = CalcPart::Kind::Calculation;
    if (const BinValue* k = v.field("mSpellCalculationKey")) p.value = static_cast<uint32_t>(k->u);
  } else if (v.cls == fnv1a("CooldownMultiplierCalculationPart")) {
    p.kind = CalcPart::Kind::CooldownMultiplier;
  } else if (v.cls == fnv1a("ProductOfSubPartsCalculationPart")) {
    p.kind = CalcPart::Kind::Product;
    for (const char* f : {"mPart1", "mPart2"})
      if (const BinValue* s = v.field(f)) p.parts.push_back(read_part(*s));
  } else if (v.cls == fnv1a("SumOfSubPartsCalculationPart")) {
    p.kind = CalcPart::Kind::Sum;
    if (const BinValue* list = v.field("mSubparts"))
      for (const BinValue& s : list->items) p.parts.push_back(read_part(s));
  }
  return p;
}

float eval_part(const SpellData& s, const CalcPart& p, int rank, const SpellCaster& c) {
  const size_t r = static_cast<size_t>(std::clamp(rank, 0, 6));
  auto value = [&](uint32_t hash) {
    auto it = s.values.find(hash);
    return it == s.values.end() ? 0.f : it->second[r];
  };
  const float stat = c.stat ? c.stat(p.stat, p.formula) : 0.f;
  switch (p.kind) {
    case CalcPart::Kind::Number: return p.number;
    case CalcPart::Kind::DataValue: return value(p.value);
    case CalcPart::Kind::StatByDataValue: return stat * value(p.value);
    case CalcPart::Kind::StatByCoefficient: return stat * p.number;
    case CalcPart::Kind::EffectValue:
      return p.effect >= 1 && static_cast<size_t>(p.effect) <= s.effects.size() ? s.effects[static_cast<size_t>(p.effect) - 1][r] : 0.f;
    case CalcPart::Kind::LevelBreakpoints: {
      // the value at level 1, then each level adds the bonus in force: the initial one, replaced from a breakpoint's
      // level on by its own; a breakpoint may add a one-time amount at its level
      float v = p.level1;
      for (int level = 2; level <= c.level; ++level) {
        float bonus = p.per_level;
        for (const auto& b : p.breakpoints) {
          if (level >= static_cast<int>(b[0])) bonus = b[2] != 0 ? b[2] : bonus;
          if (level == static_cast<int>(b[0])) v += b[1];
        }
        v += bonus;
      }
      return v;
    }
    case CalcPart::Kind::LevelInterpolation:
      // from the value at level 1 to the value at level 18, evenly
      return p.start + (p.end - p.start) * static_cast<float>(std::clamp(c.level, 1, 18) - 1) / 17.f;
    case CalcPart::Kind::LevelFormula:
      // [dedus: Lux's Illumination lists 20, 30 ... and is documented as 20 at level 1 to 190 at level 18]
      return p.by_level.empty() ? 0.f : p.by_level[static_cast<size_t>(std::clamp(c.level - 1, 0, static_cast<int>(p.by_level.size()) - 1))];
    case CalcPart::Kind::StatBySubPart:
      return p.parts.empty() ? 0.f : stat * eval_part(s, p.parts[0], rank, c);
    case CalcPart::Kind::Calculation:
      return spell_calc(s, p.value, rank, c);
    case CalcPart::Kind::CooldownMultiplier:
      return 100.f / (100.f + std::max(0.f, c.ability_haste));  // what ability haste leaves of a cooldown (documented)
    case CalcPart::Kind::Product: {
      float v = 1;
      for (const CalcPart& x : p.parts) v *= eval_part(s, x, rank, c);
      return v;
    }
    case CalcPart::Kind::Sum: {
      float v = 0;
      for (const CalcPart& x : p.parts) v += eval_part(s, x, rank, c);
      return v;
    }
    default: return 0;
  }
}

}  // namespace

uint32_t spell_name_hash(std::string_view name) {
  if (name.size() == 10 && name.front() == '{' && name.back() == '}') return static_cast<uint32_t>(std::stoul(std::string(name.substr(1, 8)), nullptr, 16));
  return fnv1a(name);
}

float spell_value(const SpellData& s, uint32_t name_hash, int rank, bool* known) {
  auto it = s.values.find(name_hash);
  if (known) *known = it != s.values.end();
  return it == s.values.end() ? 0.f : it->second[static_cast<size_t>(std::clamp(rank, 0, 6))];
}

float spell_value(const SpellData& s, std::string_view name, int rank) { return spell_value(s, spell_name_hash(name), rank); }

float spell_calc(const SpellData& s, uint32_t name_hash, int rank, const SpellCaster& caster, bool* known) {
  auto it = s.calcs.find(name_hash);
  if (known) *known = it != s.calcs.end();
  if (it == s.calcs.end()) return 0;
  const SpellCalc& c = it->second;
  float v = 0;
  if (c.modifies) v = spell_calc(s, c.modifies, rank, caster);
  for (const CalcPart& p : c.parts) v += eval_part(s, p, rank, caster);
  if (c.has_multiplier) v *= eval_part(s, c.multiplier, rank, caster);
  return v;
}

float spell_calc(const SpellData& s, std::string_view name, int rank, const SpellCaster& caster, bool* known) {
  return spell_calc(s, spell_name_hash(name), rank, caster, known);
}

std::map<std::string, SpellData> read_spells(const Wad& wad, const std::string& character) {
  std::map<std::string, SpellData> out;
  std::string lower = character;
  for (char& c : lower) c = static_cast<char>(c >= 'A' && c <= 'Z' ? c - 'A' + 'a' : c);
  auto bytes = wad.read("data/characters/" + lower + "/" + lower + ".bin");
  if (!bytes) return out;
  const PropertyBin bin(*bytes);
  for (const BinEntry& e : bin.entries()) {
    if (e.cls != fnv1a("SpellObject")) continue;
    SpellData s;
    // [meta defaults: cooldownTime 10, castRange 400, a plain unit target]
    s.cooldown.fill(10), s.range.fill(400);
    s.targeting_name = "Target";
    if (const BinValue* v = e.field("mScriptName")) s.script = v->str;
    if (const BinValue* v = e.field("objectPath"); v && !v->str.empty()) s.path = v->str;
    s.name = s.script;
    const BinValue* d = e.field("mSpell");
    s.has_spell = d != nullptr;
    if (d) {
      const BinValue* list = d->field("mDataValues");
      if (!list) list = d->field("DataValues");
      if (list) {
        for (const BinValue& dv : list->items) {
          const BinValue* n = dv.field("mName");
          if (!n) n = dv.field("name");
          if (!n) continue;
          std::array<float, 7> v{};
          const BinValue* val_field = dv.field("mValues");
          if (!val_field) val_field = dv.field("values");
          ranks(val_field, v);
          s.values[fnv1a(n->str)] = v;
          s.value_names.push_back(n->str);
        }
      }
      const BinValue* ea_list = d->field("mEffectAmount");
      if (!ea_list) ea_list = d->field("EffectAmount");
      if (ea_list) {
        for (const BinValue& ea : ea_list->items) {
          std::array<float, 7> v{};
          const BinValue* val_field = ea.field("value");
          if (!val_field) val_field = ea.field("mValue");
          ranks(val_field, v);
          s.effects.push_back(v);
        }
      }
      const BinValue* map = d->field("mSpellCalculations");
      if (!map) map = d->field("SpellCalculations");
      if (map) {
        for (const auto& [key, calc] : map->pairs) {
          SpellCalc c;
          if (const BinValue* m = calc.field("mModifiedGameCalculation")) c.modifies = static_cast<uint32_t>(m->u);
          if (const BinValue* m = calc.field("mMultiplier")) c.has_multiplier = true, c.multiplier = read_part(*m);
          if (const BinValue* parts = calc.field("mFormulaParts"))
            for (const BinValue& p : parts->items) c.parts.push_back(read_part(p));
          s.calcs[static_cast<uint32_t>(key.u)] = std::move(c);
        }
      }
      ranks(d->field("cooldownTime"), s.cooldown);
      ranks(d->field("castRange"), s.range);
      ranks(d->field("castRadius"), s.radius);
      // mana has one entry per rank from rank 1 on (6 of them)
      ranks(d->field("mana"), s.mana, 1);
      // the cast time: half a second scaled by delayCastOffsetPercent (-0.5 gives the usual quarter second) [dedus: the
      // game's formula is in its code; this is the community's reading and matches the documented cast times]
      s.cast_time = 0.5f * (1.f + num(d->field("delayCastOffsetPercent")));
      if (const BinValue* v = d->field("mCastTime")) s.cast_time = num(v);
      // flags bit 4: cast at once, without stopping the caster [dedus: set on exactly the spells documented as having
      // no cast time: Garen's Q, W and E, Ashe's Q, Tryndamere's Q, E and R, Zed's W, E and R]
      s.flags = static_cast<uint32_t>(num(d->field("flags")));
      if (s.flags & 4u) s.cast_time = 0;
      if (const BinValue* v = d->field("mAnimationName")) s.animation = v->str;
      if (const BinValue* v = d->field("mTargetingTypeData")) {
        s.targeting = v->cls;
        for (const char* n : {"Self", "Target", "Location", "direction", "Cone", "Area", "SelfAoe", "TargetOrLocation", "LocationClamped", "TerrainLocation",
                              "TerrainType", "WallFollow", "DragDirection", "AreaClamped", "MySelf"})
          if (fnv1a(n) == v->cls) s.targeting_name = n;
      }
      s.missile_speed = num(d->field("missileSpeed"));
      s.line_width = num(d->field("mLineWidth"));
      if (const BinValue* spec = d->field("mMissileSpec")) {
        if (const BinValue* w = spec->field("mMissileWidth")) s.line_width = num(w);
        if (const BinValue* move = spec->field("movementComponent")) {
          if (const BinValue* v = move->field("mSpeed")) s.missile_speed = num(v);
          if (const BinValue* v = move->field("mInitialSpeed")) {
            s.missile_speed = num(v);
            s.missile_accel = num(move->field("mAcceleration"));
            s.missile_speed_limit = num(move->field(s.missile_accel < 0 ? "mMinSpeed" : "mMaxSpeed"), s.missile_speed);
          }
        }
      }
      s.cone_angle = num(d->field("castConeAngle"), 45);
      if (const BinValue* v = d->field("mMissileEffectKey")) s.missile_effect = static_cast<uint32_t>(v->u);
      if (const BinValue* v = d->field("mHitEffectKey")) s.hit_effect = static_cast<uint32_t>(v->u);
      if (const BinValue* v = d->field("mHitBoneName")) s.hit_bone = v->str;
      if (const BinValue* list = d->field("mImgIconName"))
        for (const BinValue& i : list->items) s.icons.push_back(i.str);
      if (const BinValue* list = d->field("mSpellTags"))
        for (const BinValue& t : list->items) s.tags.push_back(t.str);
    }
    if (!s.name.empty()) out[s.name] = std::move(s);
  }
  return out;
}

}  // namespace ba
