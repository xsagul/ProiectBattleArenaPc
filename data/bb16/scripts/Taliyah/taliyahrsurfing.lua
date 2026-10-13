-- taliyahrsurfing: written by tools/bb_write16.py from the replays (18 instances, 4 games)
--   slot 50 = TaliyahRMis while it lasts (1.00)
--   slot 60 = WASD_R_Reposition while it lasts (1.00)
BuffName = "taliyahrsurfing"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 50, SlotType = ExtraSlots, SpellName = "TaliyahRMis", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 60, SlotType = ExtraSlots, SpellName = "WASD_R_Reposition", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
