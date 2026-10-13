-- zileanpassivechannel: written by tools/bb_write16.py from the replays (54 instances, 7 games)
--   slot 52 = ZileanPassiveChannel while it lasts (1.00)
--   effect 04afea23 at its start (1.78)
--   effect 04afea23 gone with it (0.94)
BuffName = "zileanpassivechannel"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "ZileanPassiveChannel", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 78637603, BindObjectVar = "Owner", EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBSpellEffectRemove, Params = {EffectIDVar = "Fx04afea23", EffectIDVarTable = "InstanceVars"}}
}
