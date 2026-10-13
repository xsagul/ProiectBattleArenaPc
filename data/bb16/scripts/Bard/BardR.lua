-- BardR: Tempered Fate
BuffName = "BardR"
TargetExecuteBuildingBlocks = {
  {Function = BBApplyStun, Params = {TargetVar = "Target", AttackerVar = "Owner", Duration = 2.5}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "bardrstasis", BuffType = BUFF_Invulnerability, BuffAddType = BUFF_REPLACE_EXISTING, Duration = 2.5, NumberOfStacks = 1, MaxStack = 1}}
}
