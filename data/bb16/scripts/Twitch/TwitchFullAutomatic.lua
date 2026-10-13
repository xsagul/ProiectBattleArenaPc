-- TwitchFullAutomatic: written by tools/bb_write16.py from the replays (59 instances, 5 games)
--   given by the cast of TwitchFullAutomatic (1.00)
--   slot 45 = TwitchSprayandPrayAttack while it lasts (1.00)
BuffName = "TwitchFullAutomatic"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "TwitchFullAutomatic", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 6.0, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "TwitchSprayandPrayAttack", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
