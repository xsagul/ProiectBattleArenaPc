-- oriannapself: written by tools/bb_write16.py from the replays (180 instances, 3 games)
--   spent by the holder's hit (0.59)
--   its hit is oriannap (0.56)
BuffName = "oriannapself"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "oriannap", OwnerVar = "Owner"}}
}
