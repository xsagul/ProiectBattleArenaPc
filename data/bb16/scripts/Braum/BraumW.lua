-- BraumW: Stand Behind Me
BuffName = "BraumW"
SelfExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "braumwdash", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_REPLACE_EXISTING, Duration = 2.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Owner", AttackerVar = "Owner", BuffName = "braumwpassivestatsdoubler", BuffType = BUFF_CombatEnchancer, BuffAddType = BUFF_REPLACE_EXISTING, Duration = 3.0, NumberOfStacks = 1, MaxStack = 1}}
}
