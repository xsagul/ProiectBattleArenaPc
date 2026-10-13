-- swainpassivepullmovebuff: written by tools/bb_write16.py from the replays (84 instances, 5 games)
--   given when swainppullready is spent (1.00)
--   slot 2 = SwainE while it lasts (1.00)
--   slot 48 = SwainPSoulTrail while it lasts (1.00)
--   effect 04afea23 at its start (1.09)
BuffName = "swainpassivepullmovebuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 2, SlotType = SpellSlots, SpellName = "SwainE", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 48, SlotType = ExtraSlots, SpellName = "SwainPSoulTrail", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 78637603, BindObjectVar = "Owner", EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
