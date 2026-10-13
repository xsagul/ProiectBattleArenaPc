-- Volley: written by tools/bb_write16.py from the replays (630 instances, 6 games)
--   slot 48 = VolleyAttackWithSound while it lasts (1.00)
--   slot 45 = VolleyAttack while it lasts (1.00)
BuffName = "Volley"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 48, SlotType = ExtraSlots, SpellName = "VolleyAttackWithSound", TargetVar = "Owner"}},
  {Function = BBSetSpell, Params = {SlotNumber = 45, SlotType = ExtraSlots, SpellName = "VolleyAttack", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}},
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
