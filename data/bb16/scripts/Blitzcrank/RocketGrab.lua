-- RocketGrab: Rocket Grab
BuffName = "RocketGrab"
TargetExecuteBuildingBlocks = {
  {Function = BBApplyDamage, Params = {AttackerVar = "Owner", TargetVar = "Target", SpellName = "RocketGrab", DamageFromData = true}},
  {Function = BBApplyStun, Params = {TargetVar = "Target", AttackerVar = "Owner", Duration = 0.65}},
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "rocketgrab2", BuffType = BUFF_Stun, BuffAddType = BUFF_REPLACE_EXISTING, Duration = 0.65, NumberOfStacks = 1, MaxStack = 1}}
}
