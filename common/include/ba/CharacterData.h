#pragma once
// What the rules need from a character's data, read where the game keeps it, never typed in by hand:
//   data/characters/<name>/<name>.bin: CharacterRecord (stats, attack slots) and its SpellObjects (attack spells).
// Defaults for fields a bin leaves out are the class defaults from the game's metadata (research/meta/*.json).

#include <array>
#include <string>
#include <vector>

#include "ba/Wad.h"

namespace ba {

/** One attack a character can make (CharacterRecord basicAttack / extraAttacks / critAttacks: AttackSlotData). */
struct AttackSlot {
  std::string name;                   // mAttackName; the basic attack defaults to "<Character>BasicAttack"
  float probability = 1;              // mAttackProbability
  bool has_offset = false;
  float offset = 0;                   // mAttackDelayCastOffsetPercent: windup percent = 0.3 + offset (documented)
  float windup_modifier = 1;          // mAttackDelayCastOffsetPercentAttackSpeedRatio
  bool has_times = false;
  float cast_time = 0, total_time = 0;  // mAttackCastTime / mAttackTotalTime: windup percent = cast / total
  // its SpellObject
  std::string animation = "Attack1";  // mAnimationName [meta default]
  float spell_cast_time = 0.5f;       // spellCastTime [meta default]: when the hit lands in the unscaled animation
  bool missile = false;               // mMissileSpec present: ranged, the hit travels
  float missile_speed = 500;          // missileSpeed [meta default]; FixedSpeedMovement mSpeed when it has one
  bool tracks_target = true;          // movementComponent mTracksTarget [meta default]
  // what the client shows (the rules ignore it)
  uint32_t missile_effect = 0;        // mMissileEffectKey: a key of the skin's ResourceResolver
  uint32_t hit_effect = 0;            // mHitEffectKey
  int hit_effect_orient = 1;          // mHitEffectOrientType [meta default 1]
  std::string hit_bone;               // mHitBoneName, when bHaveHitBone
  std::string start_bone = "R_Hand";  // movementComponent mStartBoneName [meta default]
  float target_height_augment = 0;    // movementComponent mTargetHeightAugment [meta default 0]
  float offset_initial_target_height = 0;  // movementComponent mOffsetInitialTargetHeight
  bool ground_height_at_target = true;     // FixedSpeedMovement mUseGroundHeightAtTarget [meta default]
};

struct CharacterRecordData {
  std::string name;
  std::string tags;                       // unitTagsString: "Minion | Minion_Lane | Minion_Lane_Melee"
  float move_speed = 0;                   // baseMoveSpeedModifiable.baseValue (Garen 340)
  float pathfinding_radius = 0;           // pathfindingCollisionRadius (Garen 35)
  float selection_radius = 0;             // selectionRadius
  float selection_height = 0;             // selectionHeight
  float health_bar_height = 100;          // healthBarHeight [meta default 100]: how high its health bar floats
  bool health_bar_parallax = false;       // healthBarFullParallax [meta default false] (turrets: true)
  // combat [meta defaults: baseHP 100, baseDamage 10, baseArmor 1, attackRange 100, attackSpeed 0, ratio 1]
  float base_hp = 100, base_damage = 10, base_armor = 1, attack_range = 100, attack_speed = 0, attack_speed_ratio = 1;
  float base_spell_block = 0;               // baseSpellBlock [meta default 0]
  float acquisition_range = 0;              // acquisitionRange: how far a unit of its own looks for targets
  // the AI's other ranges, 0 when the record gives none: wakeUpRange (an "asleep" minion of the first wave starts
  // looking once an enemy is this near), firstAcquisitionRange (how far it then looks for its first target)
  float wake_up_range = 0, first_acquisition_range = 0;
  float tower_priority_boost = 0;           // towerTargetingPriorityBoost: caster 1, melee 2, siege 5, super 6
  // what killing it gives [meta defaults 0]
  float exp_given = 0, gold_given = 0, local_gold_given = 0, global_gold_given = 0;
  /** overrideGameplayCollisionRadius, else 65: "most champions have a gameplay radius of 65 units" (LoL Wiki, Range). */
  float gameplay_radius = 65;
  // growth with levels [meta defaults 0]
  float hp_per_level = 0, damage_per_level = 0, armor_per_level = 0, spell_block_per_level = 0;
  float attack_speed_per_level = 0;       // percent of the base attack speed
  float hp_regen = 0, hp_regen_per_level = 0;  // baseStaticHPRegen: health per second
  // primaryAbilityResource (mana, energy ...): arBase 0 = the champion has none
  int ar_type = 0;
  float ar_base = 0, ar_per_level = 0, ar_regen = 0, ar_regen_per_level = 0;
  float ar_increments = 0;                // arIncrements (Tryndamere's fury: 100)
  // the four spells (spellNames: "GarenQAbility/GarenQ"), each one's icon (mImgIconName), and the passive's
  std::array<std::string, 4> spells;
  std::array<std::string, 4> spell_icons;
  std::string passive_icon;               // passive1IconName
  std::vector<AttackSlot> attacks;        // basicAttack then extraAttacks (picked by mAttackProbability)
  std::vector<AttackSlot> crits;          // critAttacks
};

/** The attack slot (in attacks, then crits) whose spell is `spell`, or null. */
const AttackSlot* find_attack(const CharacterRecordData& r, const std::string& spell);

/** The record of `character` ("Garen") from the wad that holds it; false when it is missing. */
bool read_character_record(const Wad& wad, const std::string& character, CharacterRecordData& out);
/** A named record of a character ("Characters/Turret/CharacterRecords/SR_Outer"); the character is the path's second
 *  part. */
bool read_character_record_at(const Wad& wad, const std::string& record_path, CharacterRecordData& out);

}  // namespace ba
