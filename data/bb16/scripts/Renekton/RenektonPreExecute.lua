-- RenektonPreExecute: written by tools/bb_write16.py from the replays (256 instances, 7 games)
--   given by the cast of RenektonPreExecute (0.77)
--   spent by the holder's hit (0.88)
--   its hit is renektonexecute (0.40)
BuffName = "RenektonPreExecute"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "RenektonPreExecute", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 6.0, NumberOfStacks = 1, MaxStack = 1}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBOverrideAutoAttack, Params = {SpellName = "renektonexecute", OwnerVar = "Owner"}}
}
