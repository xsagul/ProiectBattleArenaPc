-- NunuR: written by tools/bb_write16.py from the replays (33 instances, 4 games)
--   given by the cast of NunuR (1.00)
--   slot 3 = NunuR_Recast while it lasts (1.00)
--   spent by the holder's hit (0.70)
--   its hit is nunur (0.61)
BuffName = "NunuR"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "NunuR", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 3.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "nunurshield", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 6.0, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "NunuR_Recast", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "nunur", OwnerVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
