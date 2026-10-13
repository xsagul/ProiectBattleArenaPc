-- shyvanaqlockout: written by tools/bb_write16.py from the replays (636 instances, 5 games)
--   given by the cast of ShyvanaQ (0.70)
--   slot 0 = ShyvanaQ2 while it lasts (0.90)
--   spent by the holder's hit (0.64)
--   its hit is shyvanaqpassive (0.62)
BuffName = "shyvanaqlockout"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "ShyvanaQ2", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "shyvanaqpassive", OwnerVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
