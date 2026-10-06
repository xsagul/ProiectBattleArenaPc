#pragma once
// A champion's spells as its data describes them (data/characters/<name>/<name>.bin, SpellObject mSpell:
// SpellDataResource), read where the game keeps them, never typed in by hand:
//   mDataValues: named numbers by spell rank ("BaseDamage": 0, 30, 60 ...; index = rank)
//   mEffectAmount: the older numbered values
//   mSpellCalculations: named formulas (GameCalculation): a sum of parts (a data value, a stat times a data value or a
//     coefficient, a number, a value by champion level ...), times mMultiplier when it has one
//   cooldownTime, mana, castRange, castRadius by rank; the cast time; the animation; the missile's speed and width;
//   the effects' keys; the icon.
// What a spell does with these numbers is the server's code at Riot and is in no file: here it is in the Lua scripts.

#include <array>
#include <functional>
#include <map>
#include <string>
#include <unordered_map>
#include <vector>

#include "ba/Wad.h"

namespace ba {

/** A character stat as the calculations name it (mStat; the interface's stat panel uses the same numbers). */
enum SpellStat : int {
  kStatAbilityPower = 0, kStatArmor = 1, kStatAttackDamage = 2, kStatAttackSpeed = 3, kStatMagicResist = 5, kStatMoveSpeed = 6,
  kStatCritChance = 8, kStatCritDamage = 9, kStatCritChanceAlt = 7, kStatAbilityHaste = 10, kStatMaxHealth = 11, kStatCurrentHealth = 12, kStatMissingHealthPercent = 13,
};
/** mStatFormula [meta default 0]: the whole stat, its base part (1) or its bonus part (2). */
enum SpellStatFormula : int { kFormulaTotal = 0, kFormulaBase = 1, kFormulaBonus = 2 };

struct CalcPart {
  enum class Kind {
    Number, DataValue, StatByDataValue, StatByCoefficient, EffectValue, LevelBreakpoints, LevelInterpolation, LevelFormula, Product, Sum, StatBySubPart,
    Calculation, CooldownMultiplier, Unknown
  };
  Kind kind = Kind::Unknown;
  uint32_t cls = 0;      // its class (reported when unknown)
  float number = 0;      // Number mNumber; StatByCoefficient mCoefficient
  uint32_t value = 0;    // mDataValue: the hash of a data value's name
  int stat = 0, formula = 0, effect = 0;
  // ByCharLevelBreakpointsCalculationPart: mLevel1Value, mInitialBonusPerLevel, then per breakpoint mLevel,
  // mAdditionalBonusAtThisLevel, mBonusPerLevelAtAndAfter; ByCharLevelInterpolationCalculationPart: mStartValue, mEndValue
  float level1 = 0, per_level = 0, start = 0, end = 0;
  std::vector<std::array<float, 3>> breakpoints;
  std::vector<float> by_level;  // ByCharLevelFormulaCalculationPart mValues: the value at each level (level 1 first)
  std::vector<CalcPart> parts;  // Product (2), Sum
};

struct SpellCalc {
  std::vector<CalcPart> parts;
  bool has_multiplier = false;
  CalcPart multiplier;
  uint32_t modifies = 0;  // GameCalculationModified mModifiedGameCalculation: another calculation of the spell
};

struct SpellData {
  std::string name;       // the entry's last part: "GarenQ"
  std::string path;       // after "Characters/<Name>/Spells/": "GarenQAbility/GarenQ"
  std::string script;     // mScriptName
  bool has_spell = false; // an mSpell (some objects only carry a buff)
  std::unordered_map<uint32_t, std::array<float, 7>> values;  // fnv1a(name) -> by rank
  std::vector<std::string> value_names;
  std::vector<std::array<float, 7>> effects;                  // mEffectAmount
  std::unordered_map<uint32_t, SpellCalc> calcs;
  std::array<float, 7> cooldown{}, range{}, radius{}, mana{};
  float cast_time = 0;          // seconds [dedus: 0.5 x (1 + delayCastOffsetPercent); mCastTime when given]
  uint32_t flags = 0;
  std::string animation;        // mAnimationName
  uint32_t targeting = 0;       // mTargetingTypeData's class: Self, Target, Location, direction, Cone, Area, SelfAoe ...
  std::string targeting_name;
  // the missile: its spec's movementComponent (FixedSpeedMovement mSpeed; AcceleratingMovement mInitialSpeed,
  // mAcceleration, and the speed it stops changing at: mMaxSpeed when it gains speed, mMinSpeed when it loses it), else
  // the older missileSpeed; mMissileWidth / mLineWidth [dedus: half the width: the documented widths of Light Binding
  // (140), Razor Shuriken (100) and Enchanted Crystal Arrow (260) are twice the files' 70, 50 and 130]
  float missile_speed = 0, line_width = 0;
  float missile_accel = 0, missile_speed_limit = 0;
  float cone_angle = 45;        // castConeAngle [meta default 45], degrees
  uint32_t missile_effect = 0, hit_effect = 0;
  std::string hit_bone;
  std::vector<std::string> icons;
  std::vector<std::string> tags;  // mSpellTags
};

/** What a calculation asks of the caster: a stat by its formula, and its level. */
struct SpellCaster {
  std::function<float(int stat, int formula)> stat;
  int level = 1;
  float ability_haste = 0;  // what a cooldown multiplier leaves: 100 / (100 + haste)
};

/** A data value at a rank (0 when the spell has none of that name). */
float spell_value(const SpellData& s, std::string_view name, int rank);
float spell_value(const SpellData& s, uint32_t name_hash, int rank, bool* known = nullptr);
/** The hash of a value's or calculation's name; a name written "{1a2b3c4d}" is the hash itself (the files name some
 *  calculations only by their hash). */
uint32_t spell_name_hash(std::string_view name);
/** A named calculation at a rank for a caster; `known` (when given) tells whether the spell has it. */
float spell_calc(const SpellData& s, std::string_view name, int rank, const SpellCaster& caster, bool* known = nullptr);
float spell_calc(const SpellData& s, uint32_t name_hash, int rank, const SpellCaster& caster, bool* known = nullptr);

/** Every SpellObject of a character, by name ("GarenQ"). */
std::map<std::string, SpellData> read_spells(const Wad& wad, const std::string& character);

}  // namespace ba
