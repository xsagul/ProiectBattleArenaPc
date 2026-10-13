-- ambessapassiveattackempower: written by tools/bb_write16.py from the replays (1451 instances, 8 games)
--   spent by the holder's hit (0.58)
--   its hit is ambessabasicattackchained2 (0.21)
--   its hit is ambessabasicattackchained1 (0.21)
BuffName = "ambessapassiveattackempower"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "ambessabasicattackchained2", OwnerVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "ambessabasicattackchained1", OwnerVar = "Owner"}}
}
