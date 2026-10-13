-- leesinqtwodash: written by tools/bb_write16.py from the replays (785 instances, 9 games)
--   slot 0 = LeeSinQOne while it lasts (1.00)
--   spent by the holder's hit (0.97)
--   its hit is leesinqtwo (0.92)
BuffName = "leesinqtwodash"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "LeeSinQOne", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "leesinqtwo", OwnerVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
