-- AlphaStrike: written by tools/bb_write16.py from the replays (389 instances, 6 games)
--   given by the cast of AlphaStrike (1.00)
--   slot 50 = AlphaStrikeMissile while it lasts (1.00)
--   slot 52 = MasterYi_Q_Reposition while it lasts (1.00)
--   spent by the holder's hit (0.59)
--   its hit is wujustyle (0.28)
BuffName = "AlphaStrike"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "AlphaStrike", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 1.5, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 50, SlotType = ExtraSlots, SpellName = "AlphaStrikeMissile", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "MasterYi_Q_Reposition", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "wujustyle", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
