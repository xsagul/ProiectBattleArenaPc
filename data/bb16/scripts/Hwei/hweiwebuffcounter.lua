-- hweiwebuffcounter: written by tools/bb_write16.py from the replays (444 instances, 10 games)
--   slot 47 = HweiWEFoxfireMis while it lasts (1.00)
--   spent by the holder's hit (0.81)
--   its hit is hweiwe (0.44)
BuffName = "hweiwebuffcounter"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 47, SlotType = ExtraSlots, SpellName = "HweiWEFoxfireMis", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "hweiwe", OwnerVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
