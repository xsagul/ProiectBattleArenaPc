-- syndrawtooltip: written by tools/bb_write16.py from the replays (1038 instances, 13 games)
--   given by the cast of SyndraW (0.99)
--   slot 1 = SyndraWCast while it lasts (1.00)
--   slot 45 = SyndraWCDTimer while it lasts (1.00)
--   slot 45 = SyndraQSpell while it lasts (1.00)
--   effect 007a7045 at its start (1.00)
BuffName = "syndrawtooltip"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "SyndraWCast", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "SyndraWCDTimer", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "SyndraQSpell", TargetVar = "Owner"}},
  {Function = BBSpellEffectCreate, Params = {EffectKey = 8024133, BindObjectVar = "Owner", EffectIDVar = "Fx007a7045", EffectIDVarTable = "InstanceVars"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 1, SlotType = SpellSlots, SpellName = "SyndraW", TargetVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
