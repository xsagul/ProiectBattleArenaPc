-- sionwshieldstacks: written by tools/bb_write16.py from the replays (182 instances, 4 games)
--   given by the cast of SionW (1.00)
--   slot 1 = SionWDetonate while it lasts (1.00)
--   spent by the holder's hit (0.52)
--   its hit is sionw (0.50)
BuffName = "sionwshieldstacks"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "SionWDetonate", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "sionw", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "SionW", TargetVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "sionwsoundhit", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 0.25, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
