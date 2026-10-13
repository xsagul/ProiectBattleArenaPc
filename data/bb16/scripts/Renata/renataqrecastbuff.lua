-- renataqrecastbuff: written by tools/bb_write16.py from the replays (113 instances, 6 games)
--   given when renataqrecast is spent (1.00)
--   slot 0 = RenataQ while it lasts (1.00)
--   effect 0f6d0c52 at its start (0.99)
BuffName = "renataqrecastbuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "RenataQ", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 258804818, BindObjectVar = "Owner", EffectIDVar = "Fx0f6d0c52", EffectIDVarTable = "InstanceVars"}}
}
