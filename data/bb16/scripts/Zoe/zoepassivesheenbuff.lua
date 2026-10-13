-- zoepassivesheenbuff: written by tools/bb_write16.py from the replays (1307 instances, 8 games)
--   slot 54 = ZoeBasicAttackSpecial while it lasts (1.00)
--   spent by the holder's hit (0.63)
BuffName = "zoepassivesheenbuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 54, SlotType = ExtraSlots, SpellName = "ZoeBasicAttackSpecial", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
