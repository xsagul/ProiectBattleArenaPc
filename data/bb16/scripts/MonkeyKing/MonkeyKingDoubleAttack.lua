-- MonkeyKingDoubleAttack: written by tools/bb_write16.py from the replays (3059 instances, 14 games)
--   given by the cast of MonkeyKingDoubleAttack (0.99)
--   slot 47 = MonkeyKingQAttack while it lasts (1.00)
BuffName = "MonkeyKingDoubleAttack"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 47, SlotType = ExtraSlots, SpellName = "MonkeyKingQAttack", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
TargetExecuteBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "monkeykingdoubleattackdebuff", BuffType = BUFF_Shred, BuffAddType = BUFF_RENEW_EXISTING, Duration = 3.0, NumberOfStacks = 1, MaxStack = 1}}
}
