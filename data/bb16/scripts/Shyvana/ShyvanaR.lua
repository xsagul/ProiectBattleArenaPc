-- ShyvanaR: written by tools/bb_write16.py from the replays (46 instances, 5 games)
--   given by the cast of ShyvanaR (0.98)
--   slot 2 = ShyvanaEDragon while it lasts (1.00)
BuffName = "ShyvanaR"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "shyvanarcastjump", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 10.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "shyvanarlockfacing", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 10.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "ShyvanaR", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_RENEW_EXISTING, Duration = 3.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "shyvanartransform", BuffType = BUFF_Aura, BuffAddType = BUFF_RENEW_EXISTING, Duration = 25000.0, NumberOfStacks = 1, MaxStack = 1}}
}
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "ShyvanaEDragon", TargetVar = "Owner"}}
}
