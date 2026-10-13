-- evelynnqdebuff: written by tools/bb_write16.py from the replays (689 instances, 5 games)
--   slot 52 = EvelynnQDebuffCircleMissile while it lasts (1.00)
BuffName = "evelynnqdebuff"
OnBuffActivateBuildingBlocks = {
  {Function = BBSetSpell, Params = {SlotNumber = 52, SlotType = ExtraSlots, SpellName = "EvelynnQDebuffCircleMissile", TargetVar = "Owner"}}
}
OnBuffDeactivateBuildingBlocks = {
  {Function = BBRemoveOverrideAutoAttack, Params = {OwnerVar = "Owner"}}
}
