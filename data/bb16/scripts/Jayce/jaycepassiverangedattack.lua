-- jaycepassiverangedattack: written by tools/bb_write16.py from the replays (588 instances, 8 games)
--   given by the cast of JayceStanceHtG (1.00)
--   slot 0 = JayceShockBlast while it lasts (1.00)
--   slot 1 = JayceHyperCharge while it lasts (1.00)
--   slot 2 = JayceAccelerationGate while it lasts (1.00)
--   slot 3 = JayceStanceGtH while it lasts (1.00)
--   spent by the holder's hit (0.56)
--   its hit is jaycerangedattack (0.28)
BuffName = "jaycepassiverangedattack"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "JayceShockBlast", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "JayceHyperCharge", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "JayceAccelerationGate", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 3, SlotType = SpellSlots, SpellName = "JayceStanceGtH", TargetVar = "Owner"}},
  {Function = BBOverrideAutoAttack, Params = {SpellName = "jaycerangedattack", OwnerVar = "Owner"}}
}
BuffOnHitUnitBuildingBlocks = {
  {Function = BBSpellBuffAdd, Params = {TargetVar = "Target", AttackerVar = "Owner", BuffName = "jaycepassivedebuff", BuffType = BUFF_Shred, BuffAddType = BUFF_RENEW_EXISTING, Duration = 5.0, NumberOfStacks = 1, MaxStack = 1}},
  {Function = BBSpellBuffRemoveCurrent, Params = {TargetVar = "Owner"}}
}
