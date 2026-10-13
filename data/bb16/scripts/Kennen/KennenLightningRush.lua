-- KennenLightningRush: written by tools/bb_write16.py from the replays (935 instances, 11 games)
--   given by the cast of KennenLightningRush (1.00)
--   slot 2 = KennenLRCancel while it lasts (1.00)
BuffName = "KennenLightningRush"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "KennenLightningRush", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 2.0, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "KennenLRCancel", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "KennenLightningRush", TargetVar = "Owner"}}
}
