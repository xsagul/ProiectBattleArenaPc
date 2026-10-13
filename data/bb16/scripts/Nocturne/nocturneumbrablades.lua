-- nocturneumbrablades: written by tools/bb_write16.py from the replays (571 instances, 3 games)
--   spent by the holder's hit (0.98)
--   its hit is nocturneumbrabladesattack (0.80)
BuffName = "nocturneumbrablades"
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "nocturneumbrabladesattack", OwnerVar = "Owner"}}
}
