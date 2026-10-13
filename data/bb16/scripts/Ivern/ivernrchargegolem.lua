-- ivernrchargegolem: written by tools/bb_write16.py from the replays (27 instances, 3 games)
--   slot 0 = IvernQRecast while it lasts (1.00)
--   effect 0ac0f283 at its start (1.00)
BuffName = "ivernrchargegolem"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 0, SlotType = SpellSlots, SpellName = "IvernQRecast", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 180417155, BindObjectVar = "Owner", EffectIDVar = "Fx0ac0f283", EffectIDVarTable = "InstanceVars"}}
}
